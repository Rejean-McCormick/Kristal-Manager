"""Manual select-and-copy workflow: never mutates Git or the originals."""
import json
from pathlib import Path
import subprocess
import pytest

from kristal_manager.core import ManagerError
from kristal_manager.manual_sync import plan_copies, apply_copies


def git(root, *args):
    p=subprocess.run(['git','-C',str(root),*args],text=True,capture_output=True)
    assert p.returncode==0,p.stderr
    return p.stdout.strip()


def init(repo,name,slug,origin=None):
    repo.mkdir()
    git(repo,'init','-b','main')
    git(repo,'config','user.email','test@example.invalid')
    git(repo,'config','user.name','Test')
    if origin:git(repo,'remote','add','origin',origin)
    (repo/'kristal.workspace.json').write_text(json.dumps({'slug':slug}),encoding='utf8')
    (repo/'canon').mkdir()
    (repo/'canon'/'value.json').write_text('{"a":1}',encoding='utf8')
    git(repo,'add','--','kristal.workspace.json','canon/value.json')
    git(repo,'commit','-m','initial')
    return git(repo,'rev-parse','HEAD')


@pytest.fixture
def roots(tmp_path):
    src=tmp_path/'locals';src.mkdir()
    dst=tmp_path/'copies';dst.mkdir()
    a=src/'Kristal-Alpha';b=src/'Kristal-Beta'
    ha=init(a,'a','kristal-alpha');hb=init(b,'b','kristal-beta')
    return src,dst,a,b,ha,hb


def test_dry_run_selected_and_new_copy(roots):
    src,dst,a,b,ha,hb=roots
    (a/'untracked.txt').write_text('secret/untracked')
    plan=plan_copies(locals_root=src,destination_root=dst,slugs=['kristal-alpha'],mode='new')
    assert plan['project_count']==1 and plan['copy_files']==2
    assert not (dst/'Kristal-Alpha').exists()
    result=apply_copies(locals_root=src,destination_root=dst,slugs=['kristal-alpha'],mode='new')
    assert result['status']=='COPIES_LOCALES_TERMINEES'
    out=dst/'Kristal-Alpha'
    assert (out/'canon/value.json').read_text()=='{"a":1}'
    assert not (out/'.git').exists() and not (out/'untracked.txt').exists()
    assert not (dst/'Kristal-Beta').exists()
    assert git(a,'rev-parse','HEAD')==ha
    assert (Path(result['backup_folder'])/'BILAN-COPIES.json').is_file()


def test_existing_clean_github_clone_copy_no_git_actions(roots):
    src,dst,a,b,ha,hb=roots
    t=dst/'Kristal-Alpha'
    h=init(t,'a','kristal-alpha','git@github.com:someone/Kristal-Alpha.git')
    (a/'canon/value.json').write_text('{"a":2}')
    plan=plan_copies(locals_root=src,destination_root=dst,slugs=['kristal-alpha'],mode='clones')
    assert plan['copy_files']==1
    info=apply_copies(locals_root=src,destination_root=dst,slugs=['kristal-alpha'],mode='clones')
    assert info['git_push'] is False and info['git_commit'] is False
    assert git(t,'rev-parse','HEAD')==h
    assert 'canon/value.json' in git(t,'status','--porcelain')
    assert (t/'canon/value.json').read_text()=='{"a":2}'


def test_wrong_remote_or_dirty_target_blocked(roots):
    src,dst,a,*_=roots
    t=dst/'Kristal-Alpha'
    init(t,'a','kristal-alpha','https://github.com/other/Unrelated.git')
    with pytest.raises(ManagerError,match='ne correspond'):
        plan_copies(locals_root=src,destination_root=dst,slugs=['kristal-alpha'],mode='clones')
    git(t,'remote','set-url','origin','https://github.com/me/Kristal-Alpha.git')
    (t/'junk.txt').write_text('dirty')
    with pytest.raises(ManagerError,match='modifications locales'):
        apply_copies(locals_root=src,destination_root=dst,slugs=['kristal-alpha'],mode='clones')


def test_unexpected_existing_copy_and_bad_selection(roots):
    src,dst,*_=roots
    (dst/'Kristal-Alpha').mkdir()
    with pytest.raises(ManagerError,match='déjà existante'):
        apply_copies(locals_root=src,destination_root=dst,slugs=['kristal-alpha'],mode='new')
    with pytest.raises(ManagerError,match='sélection|Sélection'):
        plan_copies(locals_root=src,destination_root=dst,slugs=[],mode='new')
    with pytest.raises(ManagerError,match='uniques'):
        plan_copies(locals_root=src,destination_root=dst,slugs=['kristal-alpha']*2,mode='new')


def test_sensitive_git_tracked_file_blocks_without_copy(roots):
    src,dst,a,*_=roots
    (a/'.env').write_text('TOKEN=example')
    git(a,'add','-f','--','.env')
    with pytest.raises(ManagerError,match='potentiellement secret'):
        apply_copies(locals_root=src,destination_root=dst,slugs=['kristal-alpha'],mode='new')
    assert not (dst/'Kristal-Alpha').exists()


def test_no_symlinks_and_cross_source_destination(roots):
    src,dst,a,*_=roots
    with pytest.raises(ManagerError,match='séparée'):
        plan_copies(locals_root=src,destination_root=src,slugs=['kristal-alpha'],mode='new')
    link=a/'canon'/'alias'
    try:link.symlink_to(a/'canon'/'value.json')
    except (NotImplementedError,OSError):pytest.skip('symlink not supported')
    git(a,'add','--','canon/alias')
    with pytest.raises(ManagerError,match='symbolique'):
        plan_copies(locals_root=src,destination_root=dst,slugs=['kristal-alpha'],mode='new')
