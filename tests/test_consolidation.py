"""Ensure the guided diagnostic and Windows icon integrations survive together."""
import json
import os
from pathlib import Path
import time
import pytest

from kristal_manager.diag_bridge import bundled_kristaldiag
from kristal_manager.workspace_tools import is_historical


def test_bundled_diag_and_icon_sources_present():
    root = Path(__file__).resolve().parents[1]
    assert bundled_kristaldiag().is_file()
    assert (root / 'kristal_manager' / 'icon_bridge.py').is_file()
    assert (root / 'tools' / 'icon-generator' / 'Ouvrir_Generateur.cmd').is_file()
    assert (root / 'kristal_manager' / 'assets' / 'window.ico').is_file()


def test_legacy_history_is_not_a_main_kristal(tmp_path):
    historical = tmp_path / 'Kristal-Demography' / '_HISTORIQUE_AVANT_KRISTALIZER'
    historical.mkdir(parents=True)
    assert is_historical({'path': str(historical), 'nested_under': str(historical.parent)})


@pytest.mark.skipif(os.name != 'nt' and not os.environ.get('DISPLAY'), reason='needs Tk display')
def test_gui_guided_diag_and_icon_column_on_same_window(tmp_path, monkeypatch):
    from kristal_manager import gui
    root = tmp_path / 'locals'
    work = root / 'Kristal-Test'
    work.mkdir(parents=True)
    (work / 'kristal.workspace.json').write_text(json.dumps({
        'title':'Kristal-Test','slug':'kristal-test',
        'format':'kristal.local-workspace/3.2.0'}), encoding='utf-8')
    monkeypatch.setattr(gui,'save_settings',lambda *args:None)
    monkeypatch.setattr(gui,'run_official_diagnostic',lambda path, *, profile:{
        'process_status':'EXECUTED_EXIT_0','profile':profile,'verdict':'PASS',
        'counts':{'PASS':14},'findings':[],'input_changed_during_run':False,
        'external_report':{'schema':'kristaldiag.summary.v1','tool':'KristalDiag','verdict':'PASS'},
        'evidence_directory':str(tmp_path/'evidence')
    })
    app=gui.ManagerWindow()
    try:
        app.path_var.set(str(root))
        app.start_scan()
        until=time.monotonic()+10
        while app.busy and time.monotonic()<until:
            app.update()
            time.sleep(.01)
        app.update()
        assert not app.busy
        assert app.tree.heading('title')['text']=='Kristal'
        assert 'icon_nature' not in app.tree['columns']
        assert hasattr(app, 'refresh_icons')
        app.start_diag_selected()
        panel=app._diag_dialog
        assert panel is not None and panel.winfo_exists()
        panel._run()
        until=time.monotonic()+10
        while app.busy and time.monotonic()<until:
            app.update()
            time.sleep(.01)
        app.update()
        assert app._selected_row()['diag_report']['verdict']=='PASS'
        assert 'PASS' in app._text(panel.summary)
        assert 'icon_nature' not in app.tree['columns']
        panel._close()
    finally:
        app.destroy()
