"""UI regression for a full scan → batch diag → reopen, without real sources."""
import json
import os
from pathlib import Path
import time
import pytest


@pytest.mark.skipif(os.name!='nt' and not os.environ.get('DISPLAY'),reason='GUI display unavailable')
def test_ui_batch_and_reopen_saved_diag(tmp_path,monkeypatch):
    from kristal_manager import gui, central_store, diagnostics_batch
    import tkinter.messagebox as boxes
    source=tmp_path/'locals'
    root=source/'Kristal-Test';(root/'.kristal/v9').mkdir(parents=True)
    (root/'kristal.workspace.json').write_text(json.dumps({
        'format':'kristal.local-workspace/3.2.0',
        'title':'Kristal-Test','slug':'test','state_ref':'urn:kristal:test:state'}),encoding='utf-8')
    (root/'.kristal/v9/capabilities.json').write_text('{}',encoding='utf-8')
    monkeypatch.setattr(central_store,'database_path',lambda:tmp_path/'ops.sqlite3')
    monkeypatch.setattr(diagnostics_batch,'evidence_directory',lambda:tmp_path/'evidence')
    calls=[]
    def fake_runner(path,*,profile):
        calls.append(path)
        return {'format':'kristal.manager-kristaldiag/1.0','workspace':str(path),
                'profile':profile,'verdict':'PASS','process_status':'EXECUTED_EXIT_0',
                'executed_at':'2026-10-31T14:00:00Z',
                'input_fingerprint':central_store._fingerprint(path),
                'input_changed_during_run':False,'qualification':'NOT_ESTABLISHED'}
    actual=diagnostics_batch.run_folder
    monkeypatch.setattr(diagnostics_batch,'run_folder',
                        lambda folder,**kwargs:actual(folder,diag_runner=fake_runner,**kwargs))
    monkeypatch.setattr(boxes,'askyesno',lambda *a,**k:True)
    monkeypatch.setattr(gui,'save_settings',lambda *_:None)

    def drain(app):
        deadline=time.monotonic()+20
        while app.busy and time.monotonic()<deadline:
            app.update();time.sleep(.02)
        app.update()
        assert not app.busy

    app=gui.ManagerWindow()
    try:
        app.path_var.set(str(source));app.start_scan();drain(app)
        assert len(app.rows)==1
        app.open_global_center()
        assert app._global_dialog is not None
        app.start_batch_diagnostics();drain(app)
        assert app.rows[0]['diag_report']['verdict']=='PASS'
        assert app.rows[0]['diag_freshness']=='CURRENT'
        assert len(calls)==1
        # All source files are untouched; the store is outside the Kristal.
    finally:
        app.destroy()
    reopened=gui.ManagerWindow()
    try:
        reopened.path_var.set(str(source));reopened.start_scan();drain(reopened)
        assert reopened.rows[0]['diag_report']['verdict']=='PASS'
        reopened.advanced_columns_var.set(True)
        reopened._toggle_technical_columns()
        assert reopened.tree['displaycolumns'] == ('#all',) or len(reopened.tree['displaycolumns'])>8
    finally:
        reopened.destroy()
