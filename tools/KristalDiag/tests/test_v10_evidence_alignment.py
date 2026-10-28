"""Regression checks for v10 evidence verification and safe C1/C2 handoff posture."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from kristaldiag.cli import main
from kristaldiag.config import load_config
from kristaldiag.evidence import verify_run
from kristaldiag.runner import run

ROOT = Path(__file__).resolve().parents[1]


def _evidence(tmp_path, monkeypatch, *, profile='V7-Projection'):
    monkeypatch.setenv('KRISTALDIAG_TEST_IN_PROCESS', '1')
    target = tmp_path / 'fixture'
    shutil.copytree(ROOT / 'examples/reference-kristall', target)
    cfg = load_config(ROOT, target, control_dir=tmp_path / 'evidence')
    summary, code, current = run(target, cfg, profile=profile, repo_root=ROOT)
    assert (current / 'summary.json').is_file()
    return summary, code, current


def test_v10_evidence_schema_accepts_K25_through_K32():
    import jsonschema
    schema = json.loads((ROOT / 'schemas/level-result.schema.json').read_text())
    for level in ['K25', 'K26', 'K27', 'K28', 'K29', 'K30', 'K31', 'K32']:
        payload = {
            'schema': 'kristaldiag.level-result.v1', 'standard': 'KristalDiag',
            'standard_version': '1.0.0-alpha.4', 'run_id': 'demo',
            'level_id': level, 'level_name': 'test', 'target_root': '/tmp',
            'verdict': 'BLOCKED', 'findings': [],
        }
        jsonschema.Draft202012Validator(schema).validate(payload)
    bad = dict(payload, level_id='K33')
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_verification_of_persisted_v10_levels(tmp_path, monkeypatch):
    # Run-level emits a K25 file; verify-run must not reject it based on the old schema.
    monkeypatch.setenv('KRISTALDIAG_TEST_IN_PROCESS', '1')
    target = tmp_path / 'fixture'
    target.mkdir()
    cfg = load_config(ROOT, target, control_dir=tmp_path / 'evidence')
    summary, code, current = run(target, cfg, levels=['K25'], repo_root=ROOT)
    assert any(x['id'] == 'K25' for x in summary['levels'])
    ok, detail = verify_run(current / 'summary.json', ROOT)
    assert ok, detail


def test_verify_run_rejects_manifest_traversal_without_reading_outside(tmp_path, monkeypatch):
    _, _, current = _evidence(tmp_path, monkeypatch)
    outside = tmp_path / 'not-evidence.txt'
    outside.write_text('private external file', encoding='utf-8')
    manifest = current / 'evidence-manifest.json'
    data = json.loads(manifest.read_text())
    data['files']['../not-evidence.txt'] = '0' * 64
    manifest.write_text(json.dumps(data))
    valid, detail = verify_run(current / 'summary.json', ROOT)
    assert not valid
    assert any(e['kind'] == 'unsafe-manifest-file-path' for e in detail['problems'])


def test_verify_run_rejects_level_path_traversal(tmp_path, monkeypatch):
    _, _, current = _evidence(tmp_path, monkeypatch)
    summary_path = current / 'summary.json'
    summary = json.loads(summary_path.read_text())
    summary['levels'][0]['result'] = '../../private.json'
    summary_path.write_text(json.dumps(summary))
    valid, detail = verify_run(summary_path, ROOT)
    assert not valid
    assert any(e['kind'] == 'unsafe-level-result-path' for e in detail['problems'])


def test_verify_run_rejects_symlink_evidence(tmp_path, monkeypatch):
    _, _, current = _evidence(tmp_path, monkeypatch)
    original = current / 'levels/K00/result.json'
    dst = tmp_path / 'outside-copy.json'
    dst.write_bytes(original.read_bytes())
    original.unlink()
    try:
        original.symlink_to(dst)
    except OSError:
        pytest.skip('Symlinks not supported on this platform')
    valid, detail = verify_run(current / 'summary.json', ROOT)
    assert not valid
    assert any(e['kind'] in {'unsafe-level-result-path', 'evidence-symlink', 'unsafe-manifest-file-path'} for e in detail['problems'])


def test_verify_run_require_pass_rejects_valid_partial(tmp_path, monkeypatch, capsys):
    summary, _, current = _evidence(tmp_path, monkeypatch, profile='V7-Kristall')
    assert summary['verdict'] == 'PARTIAL'
    assert verify_run(current / 'summary.json', ROOT)[0]
    assert main(['verify-run', str(current / 'summary.json')]) == 0
    assert main(['verify-run', str(current / 'summary.json'), '--require-pass']) == 20
    assert 'NOT QUALIFIED' in capsys.readouterr().out


def test_verify_run_require_pass_succeeds_on_valid_pass(tmp_path, monkeypatch):
    summary, _, current = _evidence(tmp_path, monkeypatch)
    assert summary['verdict'] == 'PASS'
    assert main(['verify-run', str(current / 'summary.json'), '--require-pass']) == 0
