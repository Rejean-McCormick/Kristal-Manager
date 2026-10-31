"""Graphical acceptance test; run with xvfb-run on Linux or normal Tk on Windows."""
from __future__ import annotations
from pathlib import Path
import json
import os
import time
import pytest

@pytest.mark.skipif(os.name!='nt' and not os.environ.get('DISPLAY'),reason='Tk display unavailable')
def test_unified_center_scan_reopen(tmp_path,monkeypatch):
    from kristal_manager import central_store
    from kristal_manager.unified.dashboard_ui import UnifiedControlCenter
    import tkinter as tk
    root=tmp_path/'locals';root.mkdir()
    ws=root/'Kristal-Example';ws.mkdir()
    (ws/'kristal.workspace.json').write_text(json.dumps({'format':'kristal.local-workspace/3.2.0',
                        'title':'Kristal-Example','state_ref':'urn:kristal:test:state'}),encoding='utf8')
    monkeypatch.setattr(central_store,'database_path',lambda:tmp_path/'operations.sqlite3')
    tk_root=tk.Tk();tk_root.withdraw()
    try:
        center=UnifiedControlCenter(tk_root,root)
        def wait():
            deadline=time.monotonic()+8
            while center.busy and time.monotonic()<deadline:
                tk_root.update();time.sleep(.02)
            tk_root.update()
            assert not center.busy
        wait()
        assert not center.rows
        center.inventory();wait()
        assert len(center.rows)==1
        assert center.table.get_children()
        center.destroy()
        reopened=UnifiedControlCenter(tk_root,root)
        center=reopened
        wait()
        assert len(center.rows)==1
        assert center.rows[str(ws)]['diagnostic_verdict']=='NOT_RUN'
        center.destroy()
    finally:
        tk_root.destroy()
