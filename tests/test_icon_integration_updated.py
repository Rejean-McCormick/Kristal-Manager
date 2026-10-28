"""Icons layered onto Manager 19:24 without changing inventory/Diag/renaming behavior."""
import json
import os
from pathlib import Path
import struct
import time
import zlib

import pytest
from kristal_manager.icon_bridge import discover_icon, png_from_ico, read_registry_icon_index


def _png_square(w=32):
    def chunk(tag, payload):
        return struct.pack('>I', len(payload)) + tag + payload + struct.pack('>I', zlib.crc32(tag + payload))
    raw = b''.join(b'\x00' + bytes((30, 104, 100, 255)) * w for _ in range(w))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, w, 8, 6, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def _ico_with_png(path):
    data = _png_square()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'\x00\x00\x01\x00\x01\x00' + struct.pack('<BBBBHHII',32,32,0,0,1,32,len(data),22) + data)


def _folder(folder):
    folder.mkdir(parents=True, exist_ok=True)
    ico = folder / '.kristal' / 'KR-REF-02-M2.ico'
    _ico_with_png(ico)
    ini = '[.ShellClassInfo]\r\nIconResource=.kristal\\KR-REF-02-M2.ico,0\r\n[Kristal]\r\nNature=REF\r\nDomain1=02\r\nMaturity=2\r\n'
    (folder / 'desktop.ini').write_bytes(b'\xff\xfe' + ini.encode('utf-16le'))
    return ico


def test_read_windows_desktop_ini_preserves_original(tmp_path):
    root = tmp_path / 'Kristal-Icons'
    ico = _folder(root)
    before = {p: p.read_bytes() for p in (ico, root/'desktop.ini')}
    info = discover_icon(root)
    assert info.source == 'desktop.ini' and info.ico == ico.resolve()
    assert (info.nature, info.domains, info.maturity) == ('REF', ('02',), 2)
    assert png_from_ico(ico) == _png_square()
    assert all(p.read_bytes() == blob for p, blob in before.items())


def test_reject_escape_and_display_profile(tmp_path):
    root = tmp_path / 'crystal'; root.mkdir()
    escaped = tmp_path / 'outside.ico'; _ico_with_png(escaped)
    (root/'desktop.ini').write_text('[.ShellClassInfo]\nIconResource=..\\outside.ico,0\n')
    assert discover_icon(root).ico is None
    (root/'.kristal').mkdir()
    (root/'.kristal'/'icon-profile.json').write_text(json.dumps({
        'profile': 'kristal-icon/1.0', 'nature': 'MOD', 'maturity': 3,
        'domains': [{'code':'06'}], 'rendering':{'filename':'KR-MOD-06-M3.ico'}}))
    info = discover_icon(root)
    assert info.source == 'icon-profile.json' and info.ico is None


def test_registry_cache_exact_folder_only(tmp_path):
    col = tmp_path/'Kollection'
    icon = col/'_registry'/'icons'/'ico'/'KR-MOD-06-M3.ico'
    _ico_with_png(icon)
    reg = col/'_registry'/'knowledge-base'/'registry'/'kristal-registry.catalog.json'
    reg.parent.mkdir(parents=True)
    reg.write_text(json.dumps({'entries':[{'locator':'domains/Kristal-Agriculture',
        'presentation':{'icon':{'nature':'MOD','maturity':3,
            'domains':[{'code':'06'}], 'rendering':{'filename':'KR-MOD-06-M3.ico'}}}}]}))
    icons = read_registry_icon_index(col)
    target = tmp_path/'locals'/'Kristal-Agriculture'; target.mkdir(parents=True)
    assert discover_icon(target, registry_icons=icons).source == 'registry-présentation'
    another = tmp_path/'locals'/'Kristal-Agriculture-X'; another.mkdir()
    assert discover_icon(another, registry_icons=icons).ico is None


def test_original_windows_generator_unchanged_and_available():
    root = Path(__file__).resolve().parents[1]/'tools'/'icon-generator'
    assert (root/'Ouvrir_Generateur.cmd').is_file()
    assert (root/'server.mjs').is_file()
    assert (root/'index.html').is_file()
    assert (root/'VERSION').read_text(encoding='utf-8').strip() == '2.5.0'


@pytest.mark.skipif(os.name != 'nt' and not os.environ.get('DISPLAY'), reason='Tk display required')
def test_gui_icons_preserve_categories_sort_and_diag(tmp_path, monkeypatch):
    from kristal_manager import gui
    root = tmp_path/'locals'; crystal = root/'Kristal-Icons'
    _folder(crystal)
    (crystal/'kristal.workspace.json').write_text(json.dumps({
        'format':'kristal.local-workspace/3.2.0','title':'Kristal-Icons','slug':'kristal-icons'}))
    monkeypatch.setattr(gui,'save_settings',lambda *_:None)
    app = gui.ManagerWindow()
    try:
        app.path_var.set(str(root))
        app.start_scan()
        limit=time.monotonic()+10
        while app.busy and time.monotonic()<limit:
            app.update();time.sleep(.015)
        app.update()
        assert not app.busy and len(app.rows)==1
        row=app._selected_row()
        assert row['title']=='Kristal-Icons'
        assert row['path'] in app.icon_images
        assert app.icons[row['path']].nature == 'REF'
        item=app.tree.selection()[0]
        assert app.tree.item(item,'image')
        assert any('REF' in str(v) for v in app.tree.item(item,'values'))
        assert app.tree.heading('#0')['text'] == 'Kristal (icône)'
        assert 'Icône : desktop.ini' in app._text(app.summary_text)
        assert json.loads(app._text(app.details))['manager_icon']['source']=='desktop.ini'
        app.change_sort('icon_nature')
        assert app._selected_row()['title'] == 'Kristal-Icons'
        app.category_var.set('Toutes catégories'); app.refresh()
        app.refresh_icons()
        assert row['path'] in app.icon_images
        assert str(app.diag_button['state']) == 'normal'
        app.log('TEST', 'exemple')
        app.copy_log(); assert 'exemple' in app.clipboard_get()
        app.clear_log(); assert not app._text(app.journal)
    finally:
        app.destroy()
