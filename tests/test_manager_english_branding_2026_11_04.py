"""UI language and provided-logo regression; no local Kristal is modified."""
from __future__ import annotations

import ast
from pathlib import Path

from kristal_manager import gui, global_panel

ROOT = Path(gui.__file__).resolve().parent


def test_main_and_secondary_buttons_have_english_labels():
    expected = {
        'gui.py': ['Global analysis…', 'Transfer Kristals…', 'Manage local folder icons…'],
        'global_panel.py': ['Scan and analyze Kristals', 'Run folder diagnostics (V9)',
                            'Copy results for ChatGPT', 'Review register…'],
        'review_panel.py': ['Record a local decision…', 'Review status'],
        'publication_panel.py': ['Local transfer — selected Kristals', 'PUBLIC · Verify C1/C2'],
        'archetype_panel.py': ['Inspect selected Kristal'],
        'bundle_panel.py': ['Measure all Kristals'],
    }
    for filename, labels in expected.items():
        source = (ROOT / filename).read_text(encoding='utf-8')
        ast.parse(source)
        for label in labels:
            assert label in source, (filename, label)
    forbidden = ['Centre de contrôle', 'Scanner et analyser les Kristals',
                 'Copier résultats pour ChatGPT', 'Transférer les Kristals']
    source = (ROOT / 'global_panel.py').read_text(encoding='utf-8') + (ROOT / 'gui.py').read_text(encoding='utf-8')
    assert all(label not in source for label in forbidden)


def test_chatgpt_report_headers_and_counts_are_english():
    report = {'source': r'C:\mycode\Kristal\locals', 'verification_mode': 'inventory_only',
              'counts': {'kristals': 127, 'blocker': 0, 'warning': 0, 'review': 127,
                         'graph_content_observed': 111, 'native_contract_observed': 16},
              'entries': [], 'limits': ['Not C1/C2/C3 qualification.']}
    output = global_panel.format_chatgpt_summary(report)
    assert 'Totals: 127 Kristals; 0 blockers; 0 warnings' in output
    assert 'Canonical reading: 111 graphs/states recognized' in output
    assert 'ENTRIES (0)' in output
    assert 'Totaux' not in output
    assert 'non interprétés' not in output


def test_user_logo_is_packaged_for_tk_and_windows():
    import struct
    assets = ROOT / 'assets'
    assert '#1e6864' in (assets / 'logo_k.svg').read_text(encoding='utf-8').lower()
    for name in ('logo_header.png', 'logo_large.png', 'app_icon.png'):
        data = (assets / name).read_bytes()
        assert data[:8] == b'\x89PNG\r\n\x1a\n'
    header = (assets / 'logo_header.png').read_bytes()
    assert struct.unpack('>II', header[16:24]) == (112, 49)
    for name in ('app_icon.ico', 'window.ico'):
        assert (assets / name).read_bytes()[:4] == b'\x00\x00\x01\x00'


def test_generated_analysis_html_is_english():
    text = (ROOT / 'semantic_triage.py').read_text(encoding='utf-8')
    assert '<html lang="en">' in text
    assert '<th>Content</th>' in text
    assert '<h1>Classification proposals — not validated</h1>' in text
    assert '<html lang="fr">' not in text
