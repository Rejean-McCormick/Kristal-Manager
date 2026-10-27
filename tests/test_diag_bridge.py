"""Contract-neutral, local-only KristalDiag bridge tests."""
import json
import sys
import textwrap
from pathlib import Path
import pytest

from kristal_manager.diag_bridge import validate_config, run_diagnostic, DiagConfigurationError


def workspace(tmp_path):
    root = tmp_path / 'locals' / 'Kristal-Architecture'
    root.mkdir(parents=True)
    (root / 'kristal.workspace.json').write_text(json.dumps({
        'title':'Kristal-Architecture','slug':'kristal-architecture',
        'format':'kristal.local-workspace/3.2.0'}), encoding='utf-8')
    return root


def runner(tmp_path, code):
    script = tmp_path / 'trusted_kristaldiag_stub.py'
    script.write_text(textwrap.dedent(code), encoding='utf-8')
    return script


def test_explicit_command_is_substituted_and_report_is_observed(tmp_path):
    root=workspace(tmp_path)
    exe=runner(tmp_path, '''
        import json, pathlib, sys
        assert sys.argv[1] == '--folder'
        assert pathlib.Path(sys.argv[2]).is_dir()
        assert sys.argv[3] == '--out'
        pathlib.Path(sys.argv[4]).write_text(json.dumps({'status':'pass', 'mode':'stub'}))
    ''')
    report=run_diagnostic(root, program=exe,
       arguments='--folder {workspace} --out {report}', source_root=root.parent)
    assert report['process_status'] == 'EXECUTED_EXIT_0'
    assert report['external_report'] == {'status':'pass', 'mode':'stub'}
    assert report['report_source'] == 'output_file'
    assert report['qualification'] == 'NOT_ESTABLISHED'
    assert report['attestation'] == 'NOT_VERIFIED'
    assert report['input_changed_during_run'] is False
    assert report['input_fingerprint']['kristal.workspace.json'].startswith('sha256:')


def test_stdout_json_is_accepted_but_not_certified(tmp_path):
    root=workspace(tmp_path)
    exe=runner(tmp_path, '''
        import json
        print(json.dumps({'valid':True, 'issuer':'test'}))
    ''')
    report=run_diagnostic(root,program=exe, arguments='{workspace}')
    assert report['external_report']['valid'] is True
    assert report['report_source'] == 'stdout'
    assert report['qualification'] == 'NOT_ESTABLISHED'


def test_nonzero_and_untrusted_cli_text_is_not_authority(tmp_path):
    root=workspace(tmp_path)
    exe=runner(tmp_path, '''
        import sys
        print('C1 CERTIFIED but only text')
        sys.exit(3)
    ''')
    report=run_diagnostic(root,program=exe, arguments='{workspace}')
    assert report['process_status'] == 'EXECUTED_NONZERO'
    assert report['returncode'] == 3
    assert report['qualification'] == 'NOT_ESTABLISHED'


def test_candidate_mutation_is_detected(tmp_path):
    root=workspace(tmp_path)
    exe=runner(tmp_path, '''
        import pathlib, sys
        p=pathlib.Path(sys.argv[1])/'kristal.workspace.json'
        p.write_text('{}')
    ''')
    report=run_diagnostic(root,program=exe, arguments='{workspace}')
    assert report['input_changed_during_run'] is True
    assert report['qualification'] == 'NOT_ESTABLISHED'


def test_unsafe_program_and_arguments_blocked(tmp_path):
    root=workspace(tmp_path)
    script=runner(tmp_path, 'print(1)')
    with pytest.raises(DiagConfigurationError, match='doivent contenir'):
        validate_config(script, '--workspace unknown')
    with pytest.raises(DiagConfigurationError, match='autonome'):
        validate_config(script, '--path={workspace}')
    nested=root/'diag.py'
    nested.write_text('print(1)')
    with pytest.raises(DiagConfigurationError, match='hors des Kristals'):
        validate_config(nested,'{workspace}',root=root.parent)
    batch=tmp_path/'diag.cmd'
    batch.write_text('echo hello')
    with pytest.raises(DiagConfigurationError, match='shell'):
        validate_config(batch,'{workspace}')


def test_missing_workspace_descriptor_refused(tmp_path):
    root=tmp_path/'empty'
    root.mkdir()
    exe=runner(tmp_path,'print(1)')
    with pytest.raises(DiagConfigurationError, match='principal'):
        run_diagnostic(root,program=exe,arguments='{workspace}')


@pytest.mark.skipif(sys.platform != 'win32' and not __import__('os').environ.get('DISPLAY'), reason='needs display')
def test_ui_diag_action_updates_fiche(tmp_path, monkeypatch):
    from kristal_manager.gui import ManagerWindow
    from kristal_manager import gui
    from time import monotonic, sleep
    root=workspace(tmp_path)
    stub=runner(tmp_path, '''
        import json
        print(json.dumps({'validation':'stub-only'}))
    ''')
    monkeypatch.setattr(gui, 'save_settings', lambda settings: None)
    app=ManagerWindow()
    try:
        app.path_var.set(str(root.parent))
        app.start_scan()
        deadline=monotonic()+10
        while app.busy and monotonic()<deadline:
            app.update()
            sleep(.01)
        app.update()
        assert not app.busy
        assert app._selected_row()['title']=='Kristal-Architecture'
        assert 'KristalDiag' in app.tree['columns'] or 'diag' in app.tree['columns']
        assert str(app.diag_button['state'])=='normal'
        app.settings['diag_program'] = str(stub)
        app.settings['diag_arguments'] = '{workspace}'
        monkeypatch.setattr(gui.messagebox, 'askyesno', lambda *a,**k: True)
        app.start_diag_selected()
        deadline=monotonic()+10
        while app.busy and monotonic()<deadline:
            app.update()
            sleep(.01)
        app.update()
        assert not app.busy
        assert app._selected_row()['diag_report']['process_status']=='EXECUTED_EXIT_0'
        assert 'Attestation C1 vérifiée : non' in app._text(app.summary_text)
        assert 'stub-only' in app._text(app.details)
    finally:
        app.destroy()
