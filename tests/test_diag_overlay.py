"""Simple workflow guardrails for bundled KristalDiag."""
import json
from pathlib import Path
import pytest
from kristal_manager.diag_bridge import (bundled_kristaldiag, evidence_directory,
                                        run_official_diagnostic, DiagConfigurationError)
from kristal_manager.workspace_tools import is_historical


def test_bundled_diagnostic_is_present():
    assert bundled_kristaldiag().is_file()
    assert 'tools' in bundled_kristaldiag().parts


def test_guided_diag_rejects_unsupported_profile_and_output_inside_sources(tmp_path):
    ws = tmp_path / 'Kristal-A'
    ws.mkdir()
    (ws / 'kristal.workspace.json').write_text(json.dumps({'title': 'Kristal-A'}))
    with pytest.raises(DiagConfigurationError, match='Profil'):
        run_official_diagnostic(ws, profile='V11-Certified', output_root=tmp_path)
    with pytest.raises(DiagConfigurationError, match='hors des sources'):
        run_official_diagnostic(ws, output_root=ws)


def test_old_historique_folder_is_hidden_without_modifying_it(tmp_path):
    folder = tmp_path / 'Kristal-Demography' / '_HISTORIQUE_AVANT_KRISTALIZER'
    folder.mkdir(parents=True)
    assert is_historical({'path': str(folder), 'nested_under': str(folder.parent)})
    assert folder.is_dir()
