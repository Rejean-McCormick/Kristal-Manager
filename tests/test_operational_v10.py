"""Manager v10 operational assessment; no publication or canonical mutation."""
from __future__ import annotations
import json
from pathlib import Path
import pytest

from kristal_manager.operational import assess_local, REPORT_FORMAT
from kristal_manager.cli import main
from kristal_manager.core import validate_local_cached
from kristal_manager.inventory import inventory
from test_discovery_adapter import setup_workspace, add_discovery


def test_legacy_without_discovery_is_not_invalid(tmp_path):
    k=setup_workspace(tmp_path)
    r=assess_local(k)
    assert r['format']==REPORT_FORMAT
    assert r['operational_result']=='LOCAL_STRUCTURE_ONLY'
    assert r['discovery']['status']=='absent'
    assert r['framework_state_verification']['status']=='NOT_EVALUATED'
    assert r['qualification']==r['publication']==r['reader_authorization']=='NOT_ESTABLISHED'


def test_verified_registered_sources_not_equivalent_to_framework_or_publication(tmp_path):
    k=setup_workspace(tmp_path)
    add_discovery(k)
    before={p.relative_to(k).as_posix():p.read_bytes() for p in k.rglob('*') if p.is_file()}
    r=assess_local(k)
    assert r['operational_result']=='LOCAL_CHECKS_PASSED'
    assert r['discovery']['integrity']=='verified'
    assert r['framework_state_verification']['status']=='NOT_EVALUATED'
    assert r['hosting_verification']=='NOT_ESTABLISHED'
    assert {p.relative_to(k).as_posix():p.read_bytes() for p in k.rglob('*') if p.is_file()}==before


def test_stale_discovery_is_warning_not_canonical_invalidation(tmp_path):
    k=setup_workspace(tmp_path)
    add_discovery(k)
    (k/'kristal.workspace.json').write_text((k/'kristal.workspace.json').read_text()+'\n')
    r=assess_local(k)
    assert r['operational_result']=='ATTENTION_REQUIRED'
    assert r['local_readiness']=='READY'
    assert r['discovery']['status']=='stale'
    assert any(i['code']=='DISCOVERY_STALE' and i['severity']=='warning' for i in r['issues'])
    # Invalidation cannot be cached merely by comparing state_ref and digest.
    assert validate_local_cached(k,previous={'last_validation_result':'VALID','last_validation_cache_key':'bogus'})['cached'] is False
    assert validate_local_cached(k)['result']=='ATTENTION_REQUIRED'


def test_conflicting_current_states_are_blocked(tmp_path):
    k=setup_workspace(tmp_path)
    (k/'build/v9').mkdir(parents=True)
    state=json.loads((k/'state/state-snapshot.json').read_text())
    state['state_ref']='urn:kristal:state:other'
    (k/'build/v9/state-snapshot.json').write_text(json.dumps(state))
    r=assess_local(k)
    assert r['operational_result']=='BLOCKED'
    assert r['structural_status']=='NEEDS_ATTENTION'
    assert any(i['code']=='STATE_CONFLICT' for i in r['issues'])


def test_explicit_framework_checkout_version_is_not_silently_accepted(tmp_path):
    k=setup_workspace(tmp_path)
    ref=tmp_path/'framework'
    (ref/'reference/js/bin').mkdir(parents=True)
    (ref/'contracts').mkdir()
    (ref/'reference/js/bin/kristal-ref.mjs').write_text('throw new Error("should not execute")')
    (ref/'contracts/contract-set.json').write_text('{"version":"9.0"}')
    r=assess_local(k,framework_root=ref)
    assert r['framework_state_verification']['status']=='NOT_EVALUATED'
    assert r['operational_result']=='ATTENTION_REQUIRED'


def test_cli_verify_reports_proof_and_exit_codes(tmp_path,capsys):
    k=setup_workspace(tmp_path)
    assert main(['verify',str(k)])==0
    doc=json.loads(capsys.readouterr().out)
    assert doc['reader_authorization']=='NOT_ESTABLISHED'
    add_discovery(k)
    (k/'canon/state.index.json').write_text('{}\n')
    assert main(['verify',str(k)])==3
    doc=json.loads(capsys.readouterr().out)
    assert doc['discovery']['status']=='stale'
    assert main(['scan',str(tmp_path),'--verify-sources'])==0
    scan=json.loads(capsys.readouterr().out)
    assert scan['records'][0]['operational_result']=='ATTENTION_REQUIRED'
    assert str(k) not in json.dumps(scan)


def test_inventory_verify_is_opt_in_and_keeps_no_absolute_paths(tmp_path):
    k=setup_workspace(tmp_path)
    add_discovery(k)
    plain=inventory([tmp_path])['records'][0]
    assert 'operational_result' not in plain
    result=inventory([tmp_path],verify_sources=True)['records'][0]
    assert result['operational_result']=='LOCAL_CHECKS_PASSED'
    assert str(k) not in json.dumps(result)


def test_untrusted_framework_missing_fails_without_executing(tmp_path):
    k=setup_workspace(tmp_path)
    result=assess_local(k,framework_root=tmp_path/'no-source')
    assert result['operational_result']=='ATTENTION_REQUIRED'
    assert result['framework_state_verification']['status']=='NOT_EVALUATED'
