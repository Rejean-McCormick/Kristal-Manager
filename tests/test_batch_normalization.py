"""Batch rename workflow and English UI: safety and rollback regressions."""
import json
import os
from pathlib import Path
import time
import pytest
from kristal_manager.batch_rename import preview_batch, run_batch, undo_batch
from kristal_manager.core import ManagerError
from kristal_manager.gui import display_state_id


def sample(root, folder, title):
    directory = root / folder
    directory.mkdir(parents=True)
    (directory / 'kristal.workspace.json').write_text(json.dumps({
        'format': 'kristal.local-workspace/3.2.0',
        'title': title,
        'slug': title.lower().replace(' ', '-')}), encoding='utf-8')
    (directory / 'original.txt').write_text('Source data unchanged', encoding='utf-8')
    return directory


def test_clean_state_identity_keeps_raw_urn_in_json():
    assert display_state_id('urn:kristal:state:agriculture') == 'agriculture'
    assert display_state_id('urn:kristal:architecture:state') == 'architecture'
    assert display_state_id(None) == '—'


def test_preview_excludes_historical_and_detects_destinations(tmp_path):
    root = tmp_path / 'locals'; root.mkdir()
    a = sample(root, 'A-Kristal-Agriculture', 'Kristal Agriculture')
    sample(root, 'Kristal-Architecture', 'Kristal Architecture')
    snapshots = a / 'archive' / 'original-snapshot-before-activation'
    snapshots.mkdir(parents=True)
    (snapshots / 'kristal.workspace.json').write_text('{}')
    # Name already used, this rename must be blocked.
    sample(root, 'A-Kristal-Architecture', 'Kristal Architecture')
    items = preview_batch(root)
    assert len(items) == 3
    assert {i.source.name: i.status for i in items} == {
        'A-Kristal-Agriculture': 'rename',
        'A-Kristal-Architecture': 'blocked',
        'Kristal-Architecture': 'unchanged',
    }
    assert a.is_dir() and snapshots.is_dir()


def test_batch_backups_journal_and_guarded_undo(tmp_path):
    root = tmp_path / 'locals'; root.mkdir()
    a = sample(root, 'A-Kristal-Foo', 'Kristal Foo')
    b = sample(root, 'B-Kristal-Bar', 'Kristal Bar')
    orig = [(p / 'original.txt').read_bytes() for p in (a,b)]
    out = tmp_path / 'reports'
    report = run_batch(root, [a,b], out)
    assert report['status'] == 'completed'
    assert not a.exists() and not b.exists()
    assert (root/'Kristal-Foo').is_dir() and (root/'Kristal-Bar').is_dir()
    for record in report['entries']:
        assert Path(record['backup']).is_file()
        assert Path(record['destination']).is_dir()
    journal = Path(report['journal_file'])
    assert journal.is_file() and not journal.is_relative_to(root)
    undone = undo_batch(journal, scan_root=root)
    assert undone['status'] == 'undone'
    assert a.is_dir() and b.is_dir()
    assert [(p/'original.txt').read_bytes() for p in (a,b)] == orig


def test_disallow_reporting_within_sources_and_reject_modified_metadata(tmp_path):
    root = tmp_path / 'locals'; root.mkdir()
    a = sample(root, 'A-Kristal-Bar', 'Kristal Bar')
    with pytest.raises(ManagerError):
        run_batch(root, [a], root/'reports')
    assert a.exists()
    result = run_batch(root, [a], tmp_path/'external')
    target = root/'Kristal-Bar'
    assert target.exists()
    (target/'kristal.workspace.json').write_text('{"title":"changed"}')
    with pytest.raises(ManagerError):
        undo_batch(result['journal_file'], scan_root=root)
    assert target.exists()


@pytest.mark.skipif(os.name != 'nt' and not os.environ.get('DISPLAY'), reason='Tk display needed')
def test_gui_batch_preview_and_icon_beside_text(tmp_path, monkeypatch):
    from kristal_manager import gui
    root = tmp_path / 'locals'; root.mkdir()
    sample(root, 'A-Kristal-Test', 'Kristal Test')
    monkeypatch.setattr(gui,'save_settings',lambda *_:None)
    app = gui.ManagerWindow()
    try:
        app.path_var.set(str(root))
        app.start_scan()
        deadline=time.monotonic()+8
        while app.busy and time.monotonic()<deadline:
            app.update();time.sleep(.02)
        app.update()
        assert not app.busy
        assert app.tree.heading('title')['text']=='Kristal'
        assert 'icon_nature' not in app.tree['columns']
        assert 'State ID'==app.tree.heading('state_ref')['text']
        assert app.selected_icon_label.winfo_exists()
        app.open_batch_rename()
        panel=next(w for w in app.winfo_children() if w.winfo_class()=='Toplevel' and
                   w.title().startswith('Batch folder normalization'))
        assert len(panel.items)==1
        assert panel.selected==set()  # No preselected dangerous mutations.
        panel._all()
        assert len(panel.selected)==1
        panel._none()
        assert panel.selected==set()
        panel._close()
    finally:
        app.destroy()
