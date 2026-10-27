"""Local-only organization behavior and export safety. No production sources changed."""
import json
from pathlib import Path
from zipfile import ZipFile
import pytest
from kristal_manager.core import ManagerError, scan_roots
from kristal_manager.workspace_tools import (
    category_of, is_historical, standard_folder_name, plan_rename, apply_rename, export_workspace,
)


def sample(tmp_path, name='A-Kristal-Architecture', title='Kristal-Architecture'):
    root = tmp_path / 'locals'
    path = root / name
    path.mkdir(parents=True)
    (path / 'kristal.workspace.json').write_text(json.dumps({
        'format': 'kristal.local-workspace/3.2.0',
        'title': title, 'slug': 'kristal-architecture',
        'subject': {'domain': 'architecture'},
    }), encoding='utf-8')
    (path / 'readme.txt').write_text('contenu original', encoding='utf-8')
    return path


def test_historical_snapshot_is_not_a_second_primary_kristal(tmp_path):
    main = sample(tmp_path)
    old = main / 'archive' / 'original-snapshot-before-activation'
    (old / 'state').mkdir(parents=True)
    (old / 'state' / 'state-snapshot.json').write_text('{"state_ref":"urn:kristal:architecture:state"}')
    rows = scan_roots([main.parent])
    assert len(rows) == 2
    primary = next(r for r in rows if r['path'] == str(main.resolve()))
    snapshot = next(r for r in rows if r['path'] == str(old.resolve()))
    assert not is_historical(primary)
    assert is_historical(snapshot)
    assert category_of(primary) == 'architecture'
    assert category_of(snapshot) == 'Archive historique'


def test_rename_is_preview_first_and_preserves_internal_bytes(tmp_path):
    path = sample(tmp_path)
    original = (path / 'kristal.workspace.json').read_bytes()
    plan = plan_rename(path, path.parent)
    assert plan.destination.name == 'Kristal-Architecture'
    assert path.is_dir()  # preview is read-only
    assert not plan.destination.exists()
    new = apply_rename(plan, scan_root=path.parent)
    assert new == plan.destination
    assert not path.exists()
    assert (new / 'kristal.workspace.json').read_bytes() == original
    assert (new / 'readme.txt').read_text() == 'contenu original'


def test_rename_collision_and_nested_archive_refused(tmp_path):
    path = sample(tmp_path)
    (path.parent / 'Kristal-Architecture').mkdir()
    with pytest.raises(ManagerError, match='déjà utilisé'):
        plan_rename(path, path.parent)
    (path.parent / 'Kristal-Architecture').rmdir()
    with pytest.raises(ManagerError, match='directement sous'):
        plan_rename(path, tmp_path)
    with pytest.raises(ManagerError, match='métadonnées'):
        standard_folder_name(path.parent)


def test_export_is_reopenable_and_does_not_modify_sources(tmp_path):
    path = sample(tmp_path)
    original = {p.relative_to(path).as_posix(): p.read_bytes() for p in path.rglob('*') if p.is_file()}
    for fmt in ('zip', 'kristal'):
        dest = tmp_path / f'export.{fmt}'
        result = export_workspace(path, dest, format=fmt)
        assert dest.exists() and result['files'] == len(original)
        assert not result['official_framework_package']
        with ZipFile(dest) as z:
            assert z.testzip() is None
            for name, blob in original.items():
                assert z.read(path.name + '/' + name) == blob
            if fmt == 'kristal':
                fmt_meta = json.loads(z.read(path.name + '/kristal-manager-export.json'))
                assert fmt_meta['format'].endswith('/0.1-experimental')
                assert 'Not an official' in fmt_meta['warning']
            else:
                assert path.name + '/kristal-manager-export.json' not in z.namelist()
    assert {p.relative_to(path).as_posix(): p.read_bytes() for p in path.rglob('*') if p.is_file()} == original


def test_export_refuses_source_destination_symlink_and_overwrite(tmp_path):
    path = sample(tmp_path)
    with pytest.raises(ManagerError, match='à l’intérieur'):
        export_workspace(path, path / 'archive.zip')
    dest = tmp_path / 'archive.zip'
    dest.write_bytes(b'original')
    with pytest.raises(ManagerError, match='existe déjà'):
        export_workspace(path, dest)
    assert dest.read_bytes() == b'original'
    try:
        (path / 'private-link').symlink_to(tmp_path / 'other.txt')
    except OSError:
        pytest.skip('Symlinks not available')
    with pytest.raises(ManagerError, match='symbolique'):
        export_workspace(path, tmp_path / 'new.zip')


@pytest.mark.skipif(__import__('os').name != 'nt' and not __import__('os').environ.get('DISPLAY'), reason='needs desktop')
def test_gui_category_toggle_sort_and_export(tmp_path, monkeypatch):
    from kristal_manager.gui import ManagerWindow
    from kristal_manager import gui
    import time
    main = sample(tmp_path)
    history = main / 'archive' / 'original-snapshot-before-activation'
    (history / 'state').mkdir(parents=True)
    (history / 'state' / 'state-snapshot.json').write_text('{"state_ref":"urn:kristal:architecture:state"}')
    monkeypatch.setattr(gui, 'save_settings', lambda settings: None)
    app = ManagerWindow()
    try:
        app.path_var.set(str(main.parent))
        app.start_scan()
        deadline = time.monotonic() + 10
        while app.busy and time.monotonic() < deadline:
            app.update()
            time.sleep(.01)
        app.update()
        assert not app.busy
        assert len(app.rows) == 2
        assert len(app.tree.get_children()) == 1
        assert 'architecture' in app.category_choice['values']
        app.category_var.set('architecture')
        app.refresh()
        assert len(app.tree.get_children()) == 1
        app.category_var.set('Toutes catégories')
        app.show_history_var.set(True)
        app.refresh()
        assert len(app.tree.get_children()) == 2
        app.change_sort('category')
        assert app.sort_field == 'category'
        # Avoid Windows file dialogs; confirm selected scope.
        app.show_history_var.set(False)
        app.refresh()
        called=[]
        monkeypatch.setattr(gui.filedialog,'asksaveasfilename',lambda **kwargs: str(tmp_path/'out.zip'))
        monkeypatch.setattr(app,'_start',lambda label,fn,folder,job: called.append((folder,job,fn())))
        app.export_selected('zip')
        assert called[0][0] == main.resolve()
        assert called[0][1] == 'archive_export'
        assert (tmp_path / 'out.zip').exists()
    finally:
        app.destroy()
