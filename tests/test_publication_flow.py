"""Targeted security regressions: no public write or Git push without evidence."""
from pathlib import Path
import json
import subprocess
import pytest

from kristal_manager.core import ManagerError
from kristal_manager.publication_flow import (_assert_checkout, prepare_local_commit,
    publish_approved_commit, plan_commit)
from kristal_manager.publication_panel import selected_slugs


def _git(root,*args):
    done=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True)
    assert done.returncode==0,done.stderr
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path):
    repo=tmp_path/'kristal-public'
    repo.mkdir()
    _git(repo,'init','-b','main')
    _git(repo,'config','user.name','Unit Test')
    _git(repo,'config','user.email','test@example.invalid')
    _git(repo,'remote','add','origin','https://github.com/Rejean-McCormick/kristal-public.git')
    (repo/'README.md').write_text('test')
    _git(repo,'add','--','README.md')
    _git(repo,'commit','-m','test')
    return repo


def test_slug_selection_from_locals_only(tmp_path):
    root=tmp_path/'locals';root.mkdir()
    for n,s in [('Alpha','kristal-ai'),('Beta','kristal-agriculture')]:
        p=root/n;p.mkdir();(p/'kristal.workspace.json').write_text(json.dumps({'slug':s}))
    (root/'invalid').mkdir();(root/'invalid'/'kristal.workspace.json').write_text('{')
    assert selected_slugs(root)==['kristal-agriculture','kristal-ai']


def test_prepare_refuses_unstaged_candidate(repo,tmp_path):
    unknown=tmp_path/'candidate';unknown.mkdir()
    with pytest.raises(ManagerError,match='candidat privé'):
        plan_commit(candidate=unknown,checkout=repo)


def test_prepare_does_not_touch_git_without_write(repo,tmp_path,monkeypatch):
    candidate=tmp_path/'candidate';candidate.mkdir()
    (candidate/'STAGING_ONLY.txt').write_text('private')
    from kristal_manager import publication_flow as f
    monkeypatch.setattr(f,'_candidate',lambda *args,**kwargs:(['kristal-ai'],['kristals/index.json']))
    before=_git(repo,'rev-parse','HEAD')
    result=prepare_local_commit(candidate=candidate,checkout=repo,write=False)
    assert result['status']=='DRY_RUN'
    assert before==_git(repo,'rev-parse','HEAD')
    assert not (repo/'kristals').exists()


def test_no_push_without_public_evidence(repo,tmp_path):
    from kristal_manager import publication_flow as f
    (repo/'tools').mkdir()
    (repo/'tools/c123_offline.py').write_text('raise SystemExit(3)')
    with pytest.raises(ManagerError):
        publish_approved_commit(checkout=repo,trust=tmp_path/'trust',
                c1_dir=tmp_path/'c1',c2_dir=tmp_path/'c2',policy_dir=tmp_path/'policy',
                external_approval_confirmed=True,push=True)


def test_fail_closed_on_wrong_remote(repo):
    _git(repo,'remote','set-url','origin','https://github.com/attacker/public.git')
    with pytest.raises(ManagerError,match='origin inattendu'):
        _assert_checkout(repo,require_clean=True)


def test_dirty_checkout_blocks_before_staging(repo,tmp_path):
    (repo/'untracked.txt').write_text('left alone')
    with pytest.raises(ManagerError,match='Git doit être propre'):
        prepare_local_commit(candidate=tmp_path,checkout=repo,write=True)
    assert (repo/'untracked.txt').read_text()=='left alone'
