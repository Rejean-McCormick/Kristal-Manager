import json,shutil,sys
from pathlib import Path
from kristaldiag.config import load_config
from kristaldiag.runner import run
ROOT=Path(__file__).resolve().parents[1]

def test_driver_blocked_without_allow_exec(tmp_path):
    target=tmp_path/'impl';target.mkdir()
    (target/'kristaldiag.implementation.json').write_text(json.dumps({'schema':'kristaldiag.implementation.v1','name':'x','claimed_profile':'V7-Kristall','standard_target':'7.0.0-draft.2'}))
    (target/'kristaldiag-driver.json').write_text(json.dumps({'schema':'kristaldiag.driver.v1','implementation':'x','claimed_profile':'V7-Kristall','actions':{'self_test':{'argv':[sys.executable,'-c','print(1)']}}}))
    cfg=load_config(ROOT,target,control_dir=tmp_path/'ev');summary,_,current=run(target,cfg,profile='V7-Kristall',repo_root=ROOT,allow_exec=False)
    k11=json.loads((current/'levels/K11/result.json').read_text())
    assert k11['verdict']=='BLOCKED'
