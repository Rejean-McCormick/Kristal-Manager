"""Fail-closed tests for Manager's local candidate preparation."""
from pathlib import Path
import json
import pytest
from kristal_manager.core import ManagerError
from kristal_manager.publication_stage import prepare_private_collection

@pytest.fixture
def fixture(tmp_path):
    locals_root=tmp_path/'locals';locals_root.mkdir()
    ws=locals_root/'Kristal-Test';ws.mkdir()
    (ws/'kristal.workspace.json').write_text(json.dumps({'slug':'kristal-test'}))
    kit=tmp_path/'kit.py';kit.write_text('print("test")')
    return locals_root,kit,tmp_path/'private-stage'

def test_dry_run_does_not_create(fixture):
    root,kit,out=fixture
    result=prepare_private_collection(locals_root=root,kit_script=kit,output=out,slugs=['kristal-test'])
    assert result['status']=='DRY_RUN'
    assert result['authorization']=='NOT_ESTABLISHED'
    assert not out.exists()

def test_refuse_output_in_git_checkout(fixture):
    root,kit,_=fixture
    git=root.parent/'checkout';git.mkdir();(git/'.git').mkdir()
    with pytest.raises(ManagerError,match='Git checkout'):
        prepare_private_collection(locals_root=root,kit_script=kit,
                                   output=git/'candidate',slugs=['kristal-test'],write_private=True)

def test_refuse_source_collisions_and_traversal(fixture):
    root,kit,out=fixture
    with pytest.raises(ManagerError):
        prepare_private_collection(locals_root=root,kit_script=kit,output=out,slugs=['../secret'])
    with pytest.raises(ManagerError):
        prepare_private_collection(locals_root=root,kit_script=kit,output=out,
                                   slugs=['kristal-test','kristal-test'])
    assert not out.exists()

def test_missing_kit_fails_without_writes(fixture):
    root,kit,out=fixture
    kit.unlink()
    with pytest.raises(ManagerError,match='Kit script missing'):
        prepare_private_collection(locals_root=root,kit_script=kit,output=out,
                                   slugs=['kristal-test'],write_private=True)
    assert not out.exists()


def test_dry_run_allows_nonexistent_private_parent(fixture):
    root,kit,out=fixture
    path=out.parent/'private-candidates'/'future-candidate'
    result=prepare_private_collection(locals_root=root,kit_script=kit,output=path,
                                      slugs=['kristal-test'],write_private=False)
    assert result['status']=='DRY_RUN'
    assert not path.parent.exists()
