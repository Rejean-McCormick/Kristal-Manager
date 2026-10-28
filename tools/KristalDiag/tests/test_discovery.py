from pathlib import Path
from kristaldiag.discovery import discover
ROOT=Path(__file__).resolve().parents[1]

def test_reference_inventory():
    inv=discover(ROOT/'examples/reference-kristall')
    assert inv.manifests
    assert inv.get('kristall_mesh')
    assert inv.get('kristal_state')
    assert not inv.parse_errors

def test_discovery_limit_is_reported(tmp_path):
    for i in range(3):(tmp_path/f'{i}.json').write_text('{"x":1}',encoding='utf-8')
    inv=discover(tmp_path,max_files=2)
    assert inv.scan_limit_reached is True
