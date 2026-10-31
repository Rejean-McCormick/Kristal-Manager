"""Regression checks: no Git commits/pushes within Kristal Manager distribution."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_old_gitsink_shortcut_is_harmless():
    code = (ROOT / 'GitSink.bat').read_text(encoding='ascii').lower()
    assert 'exit /b 1' in code
    for forbidden in ('call git', 'git push origin', 'git add .', 'git commit -m'):
        assert forbidden not in code


def test_launch_only_starts_local_python():
    code = (ROOT / 'Launch-Kristal-Manager.cmd').read_text(encoding='utf-8').lower()
    assert 'kristal-manager.pyw' in code
    for forbidden in ('git push', 'git commit', 'git add', 'curl ', 'wget '):
        assert forbidden not in code


def test_generated_artifacts_ignored_for_future_tracking():
    ignore = (ROOT / '.gitignore').read_text(encoding='utf-8')
    assert '/catalogue/**' in ignore
    assert '/rapports/**' in ignore


def test_application_code_has_no_git_invocations():
    import re
    paths = list((ROOT / 'kristal_manager').glob('*.py'))
    for path in paths:
        code = path.read_text(encoding='utf-8')
        # No subprocess invocation of Git or shell commands with git mutators
        assert not re.search(r'(?i)subprocess\.\w+\([^\n]*(?:[\"\']git[\"\']|git\s+(?:add|push|commit))', code), path
