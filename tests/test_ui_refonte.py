"""UX safety regressions for the local desktop UI."""
import json
import os
from pathlib import Path
import time

import pytest

from kristal_manager.ui_prefs import WINDOWS_LOCALS, default_root, load_settings, save_settings
from kristal_manager.content_catalog import candidates, build_catalog, summaries


def test_default_windows_path_when_no_last_folder(monkeypatch, tmp_path):
    monkeypatch.delenv('KRISTAL_LOCALS', raising=False)
    assert default_root({}, windows=True, exists=lambda _: False, home=tmp_path) == WINDOWS_LOCALS
    assert default_root({'last_root': 'D:/mes-cristaux'}, windows=True,
                        exists=lambda p: str(p) == 'D:/mes-cristaux', home=tmp_path) == 'D:/mes-cristaux'


def test_preferences_stay_outside_source(tmp_path):
    preferences = tmp_path / 'settings' / 'preferences.json'
    expected = {'last_root': 'C:/mycode/Kristal/locals'}
    save_settings(expected, preferences)
    assert load_settings(preferences) == expected
    assert load_settings(tmp_path / 'missing.json') == {}


def test_direct_only_catalog_scope(tmp_path):
    root = tmp_path / 'principal'
    inner = root / 'archive' / 'ancien'
    inner.mkdir(parents=True)
    for path in (root, inner):
        (path / 'kristal.workspace.json').write_text(json.dumps({
            'format': 'kristal.local-workspace/3.2.0',
            'title': path.name, 'slug': path.name}), encoding='utf-8')
    assert list(candidates([root], direct_only=True)) == [root]
    assert list(candidates([root])) == [root, inner]
    db = tmp_path / 'catalogue.sqlite3'
    result = build_catalog([root], db, direct_only=True)
    assert result['workspaces'] == 1
    assert [r['title'] for r in summaries(db)['records']] == ['principal']


@pytest.mark.skipif(os.name != 'nt' and not os.environ.get('DISPLAY'), reason='needs a graphical display')
def test_gui_log_actions_and_selected_scope(tmp_path, monkeypatch):
    from kristal_manager.gui import ManagerWindow
    from kristal_manager import gui
    root = tmp_path / 'locals'
    crystal = root / 'Architecture'
    crystal.mkdir(parents=True)
    (crystal / 'kristal.workspace.json').write_text(json.dumps({
        'format': 'kristal.local-workspace/3.2.0',
        'title': 'Kristal-Architecture', 'slug': 'kristal-architecture'}), encoding='utf-8')
    monkeypatch.setattr(gui, 'save_settings', lambda settings: None)
    app = ManagerWindow()
    try:
        app.path_var.set(str(root))
        app.start_scan()
        timeout = time.monotonic() + 8
        while app.busy and time.monotonic() < timeout:
            app.update()
            time.sleep(0.02)
        assert not app.busy
        app.update()
        assert len(app.rows) == 1
        assert app._selected_row()['title'] == 'Kristal-Architecture'
        assert str(app.verify_button['state']) == 'normal'
        assert str(app.selected_catalog_button['state']) == 'normal'
        app.tabs.select(2)
        app.log('TEST', 'preuve de journal')
        app.copy_log()
        assert 'preuve de journal' in app.clipboard_get()
        app.clear_log()
        assert not app._text(app.journal)
        called = []
        monkeypatch.setattr(app, '_catalog_destination', lambda _: tmp_path / 'journal-test.sqlite3')
        monkeypatch.setattr(app, '_run_catalog', lambda folder, database, mode: called.append((folder, database, mode)))
        app.start_catalog_selected()
        assert called == [(crystal.resolve(), tmp_path / 'journal-test.sqlite3', 'selected')]
    finally:
        app.destroy()
