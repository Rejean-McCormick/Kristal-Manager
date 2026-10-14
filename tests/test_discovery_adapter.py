"""Alpha.13 Discovery and KNAV preview regressions. No network, no workspace edits."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import pytest

from kristal_manager.discovery import inspect_discovery, _canonicalize
from kristal_manager.inventory import konstellation_preview, inventory, KONSTELLATION_PREVIEW_FORMAT
from kristal_manager.core import detect_kristal, ManagerError
from kristal_manager.cli import main


def setup_workspace(parent: Path, title='Alpha',ref='urn:kristal:state:alpha') -> Path:
    root=parent/title;root.mkdir()
    (root/'kristal.workspace.json').write_text(json.dumps({'format':'kristal.local-workspace/3.2.0',
      'title':title,'state_ref':ref,'native_model':{'kind':'graph'}}),encoding='utf8')
    (root/'canon').mkdir()
    (root/'canon/state.index.json').write_text('{"canonical_artifacts":[]}',encoding='utf8')
    (root/'state').mkdir()
    (root/'state/state-snapshot.json').write_text(json.dumps({'state_ref':ref,'logical_commitment':{'digest':'sha256:'+'1'*64}}),encoding='utf8')
    return root


def add_discovery(root: Path, classification=None):
    ref=json.loads((root/'kristal.workspace.json').read_text())['state_ref']
    inventory_doc={'format':'kristal.reader-inventory/1.0','state_ref':ref,
      'source_fingerprint':'', 'size_class':'tiny',
      'measurement':{'status':'measured_referenced_local_files'},
      'storage':{'tracked_local_bytes':0}, 'cardinality':{},'files':[], 'segments':[]}
    files=[]
    for p in ('kristal.workspace.json','canon/state.index.json'):
        files.append([p,hashlib.sha256((root/p).read_bytes()).hexdigest()])
    payload={'inputs':files,'physical_files':[], 'segments':[]}
    fingerprint='sha256:'+hashlib.sha256(_canonicalize(payload).encode('utf8')).hexdigest()
    inventory_doc['source_fingerprint']=fingerprint
    reader={'format':'kristal.reader-profile/1.0','state_ref':ref,'source_fingerprint':fingerprint,
       'specialization':'kristal.reader/generic-v1','configuration_status':'advisory_only',
       'access_pattern':'generic','materialization_profiles':[], 'artifact_strategies':[],
       'parser_candidates':[], 'constraints':[]}
    discovery={'format':'kristal.discovery/1.0', 'state_ref':ref,
      'classification':classification or {}, 'source_fingerprint':fingerprint,
      'authority':'noncanonical_derived_metadata_not_access_or_publication_authority',
      'data_layout':{'state_architecture':'kristal.state/9.0','native_kind':'graph',
        'organization':'unknown','inventory_ref':'derived/reader-inventory.json','materialization_profiles':[]},
      'reader':{'profile':reader['specialization'],'hints_ref':'derived/reader-profile.json'},
      'size':{'class':'tiny','tracked_local_bytes':0,'completeness':'measured_referenced_local_files'}}
    (root/'derived').mkdir(exist_ok=True)
    (root/'kristal.discovery.json').write_text(json.dumps(discovery))
    (root/'derived/reader-inventory.json').write_text(json.dumps(inventory_doc))
    (root/'derived/reader-profile.json').write_text(json.dumps(reader))
    return discovery, inventory_doc, reader


def test_old_workspace_falls_back_without_discovery(tmp_path):
    p=setup_workspace(tmp_path)
    rec=detect_kristal(p)
    assert rec['readiness']=='READY'
    assert rec['discovery']['status']=='absent'
    assert inventory([tmp_path])['records'][0]['archetype']=='UNDECLARED'


def test_discovery_is_read_only_and_does_not_change_state(tmp_path):
    p=setup_workspace(tmp_path)
    add_discovery(p,{'arketype_version':'1.4.0','primary_archetype':'ARK-08','primary_usage':'PRF-15'})
    before={f:f.read_bytes() for f in p.rglob('*') if f.is_file()}
    observed=detect_kristal(p)
    assert observed['readiness']=='READY'
    assert observed['discovery']['status']=='consistent_unverified'
    assert observed['discovery']['classification']['primary_archetype']=='ARK-08'
    assert inspect_discovery(p,verify_sources=True)['status']=='verified_registered_sources'
    assert {f:f.read_bytes() for f in p.rglob('*') if f.is_file()}==before


def test_inconsistent_fingerprint_and_identity_fail_closed(tmp_path):
    p=setup_workspace(tmp_path)
    add_discovery(p)
    d=p/'derived/reader-profile.json';json_obj=json.loads(d.read_text());json_obj['state_ref']='other'
    d.write_text(json.dumps(json_obj))
    assert inspect_discovery(p)['status']=='invalid'
    assert 'derived state identities disagree' in inspect_discovery(p)['issues']
    assert detect_kristal(p)['readiness']=='READY'


def test_partial_and_symlinked_sources_are_rejected(tmp_path):
    p=setup_workspace(tmp_path)
    add_discovery(p)
    (p/'derived/reader-profile.json').unlink()
    assert inspect_discovery(p)['status']=='incomplete'
    add_discovery(p)
    other=tmp_path/'outside';other.write_text('{}')
    (p/'kristal.discovery.json').unlink()
    (p/'kristal.discovery.json').symlink_to(other)
    assert inspect_discovery(p)['status']=='invalid'


def test_explicit_registered_sources_fingerprint_rejects_edits(tmp_path):
    p=setup_workspace(tmp_path)
    add_discovery(p)
    assert inspect_discovery(p,verify_sources=True)['status']=='verified_registered_sources'
    ws=p/'kristal.workspace.json';ws.write_text(ws.read_text()+'\n')
    assert inspect_discovery(p)['status']=='consistent_unverified'
    result=inspect_discovery(p,verify_sources=True)
    assert result['status']=='stale'
    assert result['integrity']=='mismatch'


def test_konstellation_preview_is_opt_in_and_stays_private(tmp_path):
    p=setup_workspace(tmp_path)
    add_discovery(p,{'primary_archetype':'ARK-08'})
    with pytest.raises(ManagerError,match='Default-deny'):
        konstellation_preview([tmp_path],allowed_principals=[])
    doc=konstellation_preview([tmp_path],allowed_principals=['local-user'])
    assert doc['format']==KONSTELLATION_PREVIEW_FORMAT
    row=doc['entries'][0]
    assert row['archetype']=='ARK-08'
    assert row['visibility']=='private' and row['availability']=='unknown'
    assert row['readiness']=='not_checked'
    assert row['allowed_principals']==['local-user']
    assert set(row)<=set(('id','title','visibility','readiness','availability',
       'allowed_principals','allowed_roles','state_ref','state_commitment','archetype'))
    assert str(p) not in json.dumps(doc)
    assert 'local_path' not in json.dumps(doc)
    assert 'discovery' not in json.dumps(doc)


def test_duplicate_state_ref_is_never_merged(tmp_path):
    setup_workspace(tmp_path,'Alpha')
    setup_workspace(tmp_path,'Beta')
    preview=konstellation_preview([tmp_path],allowed_principals=['local-user'])
    assert len(preview['entries'])==2
    assert len(set(e['id'] for e in preview['entries']))==2
    assert all(x['readiness']=='blocked' for x in preview['entries'])


def test_cli_export_konstellation(tmp_path,capsys):
    setup_workspace(tmp_path)
    out=tmp_path/'knav.json'
    assert main(['export-konstellation',str(tmp_path),'--principal-id','local-user',
                 '--output',str(out)])==0
    doc=json.loads(out.read_text())
    assert len(doc['entries'])==1
    assert doc['entries'][0]['availability']=='unknown'
