"""Regression: no implicit Git publication, even with opt-in GitSink utility."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def test_launch_only_starts_local_python():
    code=(ROOT/'Launch-Kristal-Manager.cmd').read_text(encoding='utf8').lower()
    assert 'kristal-manager.pyw' in code
    for forbidden in ('git push','git commit','git add','curl ','wget '):
        assert forbidden not in code


def test_gitsink_is_independent_opt_in_tool():
    code=(ROOT/'GitSink.bat').read_text(encoding='ascii').lower()
    assert 'git push' in code and 'git add --all' in code
    # The publication GUI does not invoke the catch-all GitSink tool.
    panel=(ROOT/'kristal_manager/publication_panel.py').read_text(encoding='utf8').lower()
    assert 'gitsink' not in panel


def test_only_explicit_flow_can_invoke_git_for_publication():
    for p in (ROOT/'kristal_manager').glob('*.py'):
        if p.name=='publication_flow.py':continue
        code=p.read_text(encoding='utf8').lower()
        assert 'git push origin' not in code
        assert 'git add --all' not in code


def test_generated_artifacts_are_not_tracked():
    ignore=(ROOT/'.gitignore').read_text(encoding='utf8')
    assert '/catalogue/**' in ignore and '/rapports/**' in ignore
