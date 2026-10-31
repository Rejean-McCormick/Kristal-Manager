"""Bundle inventory tests; no project files should be modified."""
import json
from pathlib import Path
import pytest

from kristal_manager.bundle_inventory import scan_inventory, format_brief


def _make(root: Path, name: str, body: bytes=b'hello') -> Path:
    project=root/name
    (project/'canon'/'domain').mkdir(parents=True)
    (project/'.git'/'objects').mkdir(parents=True)
    (project/'canon'/'domain'/'state.bin').write_bytes(body)
    (project/'.git'/'objects'/'one').write_bytes(b'12345')
    (project/'image.png').write_bytes(b'abc')
    (project/'kristal.workspace.json').write_text(json.dumps({
        'state_ref':'urn:test:'+name,
        'classification':{'primary_archetype':'ARK-04','structure_mode':'hybrid'}}),encoding='utf-8')
    return project


def test_complete_bytes_and_declared_tag_and_no_mutation(tmp_path):
    source=tmp_path/'locals';source.mkdir()
    a=_make(source,'Kristal-Alpha')
    b=_make(source,'Kristal-Beta',b'x'*1024)
    old={str(p.relative_to(source)):p.read_bytes() for p in source.rglob('*') if p.is_file()}
    output=scan_inventory(source)
    assert output['format']=='kristal.manager-bundle-inventory/1.0'
    assert output['counts']['projects']==2
    rows={r['project']:r for r in output['projects']}
    assert rows['Kristal-Alpha']['bytes_canon']==5
    assert rows['Kristal-Beta']['bytes_canon']==1024
    for r in rows.values():
        assert r['file_count']==4
        assert r['measurement_complete'] is True
        assert r['declaration']['primary_archetype']=='ARK-04'
        assert r['declaration']['structure_mode']=='hybrid'
        assert r['bytes_total']==sum(r['top_level_bytes'].values())
        assert r['bytes_noncanon']==r['bytes_total']-r['bytes_canon']
        assert '.git' in r['top_level_bytes']
    assert 'Kristal-Alpha' in format_brief(output)
    assert old=={str(p.relative_to(source)):p.read_bytes() for p in source.rglob('*') if p.is_file()}


def test_symlink_not_followed(tmp_path):
    source=tmp_path/'locals';source.mkdir()
    p=_make(source,'Kristal-Liens')
    outside=tmp_path/'sensitive.txt';outside.write_bytes(b'outside content')
    try:(p/'outside-link').symlink_to(outside)
    except (OSError,NotImplementedError):pytest.skip('platform does not allow symlink')
    out=scan_inventory(source)['projects'][0]
    assert out['links_skipped']==1
    assert out['measurement_complete'] is False
    assert out['file_count']==4
    assert b'outside content' not in (p/'canon'/'domain'/'state.bin').read_bytes()


def test_single_project_root_and_malformed_metadata(tmp_path):
    p=_make(tmp_path,'Kristal-Alone')
    (p/'kristal.workspace.json').write_text('not json',encoding='utf-8')
    obj=scan_inventory(p)
    assert obj['counts']['projects']==1
    assert obj['projects'][0]['measurement_complete'] is True
    assert obj['projects'][0]['declaration']['primary_archetype'] is None
    assert obj['projects'][0]['declaration']['note']


def test_empty_root_errors(tmp_path):
    with pytest.raises(ValueError):scan_inventory(tmp_path)
