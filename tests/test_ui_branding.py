"""Branding assets use standard-library-only Tk images at runtime."""
from pathlib import Path
import os
import pytest

from kristal_manager import gui


def test_embedded_assets_exist_and_match_primary_color():
    root = Path(gui.__file__).parent / 'assets'
    assert (root / 'logo_k.svg').is_file()
    svg = (root / 'logo_k.svg').read_text(encoding='utf-8').lower()
    assert '#1e6864' in svg
    for name in ('logo_header.png', 'logo_large.png', 'app_icon.png'):
        assert (root / name).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    assert (root / 'app_icon.ico').read_bytes()[:4] == b'\x00\x00\x01\x00'
    assert gui.BRAND.lower() == '#1e6864'


def test_offline_viewer_has_inline_logo():
    viewer = Path(__file__).resolve().parents[1] / 'kristal-manager.html'
    html = viewer.read_text(encoding='utf-8')
    assert 'data:image/png;base64,' in html
    assert '--green:#1e6864' in html.lower()


@pytest.mark.skipif(os.name != 'nt' and not os.environ.get('DISPLAY'), reason='needs graphical display')
def test_gui_shows_logo_and_primary_button():
    app = gui.ManagerWindow()
    try:
        app.update_idletasks()
        assert app._logo_image is not None
        assert app._logo_image.width() == 112
        assert app._app_icon_image is not None
        from tkinter import ttk
        style = ttk.Style(app)
        assert style.configure('Primary.TButton')['background'].lower() == '#1e6864'
    finally:
        app.destroy()


def test_generated_catalog_html_has_brand(tmp_path):
    import json
    from kristal_manager.content_catalog import build_catalog, write_overview
    folder = tmp_path / 'A-Kristal-Architecture'
    folder.mkdir()
    (folder / 'kristal.workspace.json').write_text(json.dumps({
        'format': 'kristal.local-workspace/3.2.0',
        'title': 'Architecture', 'slug': 'architecture'}), encoding='utf-8')
    db = tmp_path / 'catalog.sqlite3'
    build_catalog([folder], db, direct_only=True)
    html_path = tmp_path / 'catalog.html'
    write_overview(db, html_path)
    html = html_path.read_text(encoding='utf-8')
    assert 'data:image/png;base64,' in html
    assert 'color:#1E6864' in html
