import os,json,shutil,subprocess,sys
from pathlib import Path
from kristaldiag.config import load_config
from kristaldiag.manifest import CAMPAIGNS
from kristaldiag.profiles import PROFILES
from kristaldiag.runner import run
ROOT=Path(__file__).resolve().parents[1]

def fixture(tmp_path):
    dst=tmp_path/'fixture';shutil.copytree(ROOT/'examples/reference-kristall',dst);return dst

def test_profiles_include_neutral_harness():
    for levels in PROFILES.values():
        for lid in ('N00','N01','N02','N03','N04','N06'): assert lid in levels

def test_baseline_campaign_is_neutral(tmp_path):
    t=fixture(tmp_path);cfg=load_config(ROOT,t,control_dir=tmp_path/'evidence')
    summary,code,current=run(t,cfg,campaign='baseline',repo_root=ROOT)
    assert code in (0,10)
    ids=[x['id'] for x in summary['levels']]
    assert all(x in ids for x in CAMPAIGNS['baseline'])
    assert not any(x.startswith('K0') for x in ids if x!='K14')

def test_declared_validator_requires_allow_exec(tmp_path):
    t=fixture(tmp_path);cfg=load_config(ROOT,t,control_dir=tmp_path/'evidence')
    cfg.data['validators']=[{'id':'probe','required':True,'command':[sys.executable,'-c','print(1)']}]
    summary,code,current=run(t,cfg,campaign='deep',repo_root=ROOT)
    n05=json.loads((current/'levels/N05/result.json').read_text())
    assert n05['verdict']=='BLOCKED'

def test_default_scheduler_uses_isolated_worker(tmp_path,monkeypatch):
    monkeypatch.delenv('KRISTALDIAG_TEST_IN_PROCESS',raising=False)
    t=fixture(tmp_path);cfg=load_config(ROOT,t,control_dir=tmp_path/'evidence')
    # Keep this small while still proving a child worker is used.
    summary,code,current=run(t,cfg,levels=['N00'],repo_root=ROOT,jobs=1)
    assert summary['verdict']=='PASS'
    assert json.loads((current/'levels/N00/result.json').read_text())['verdict']=='PASS'

def test_release_campaign_adds_r_levels(tmp_path):
    t=fixture(tmp_path);cfg=load_config(ROOT,t,control_dir=tmp_path/'evidence')
    summary,code,current=run(t,cfg,campaign='release',repo_root=ROOT)
    ids=[x['id'] for x in summary['levels']]
    for lid in ('R00','R01','R02','R03','R04'): assert lid in ids
    assert (current/'levels/R04/result.json').is_file()

def test_levelup_compatibility_shim_lists_campaigns(tmp_path):
    cp=subprocess.run([sys.executable,str(ROOT/'levelupdiag.py'),'list'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=False)
    assert cp.returncode==0
    assert 'baseline' in cp.stdout and 'release' in cp.stdout
    assert 'compatibility shim' in cp.stderr

def test_v10_campaign_contains_hosted_network_checks():
    for lid in ('K25','K26','K27','K28','K29','K30','K31'):
        assert lid in CAMPAIGNS['v10']

def test_v10_profiles_are_declared():
    for profile in ('V10-Node-Reader','V10-Publisher','V10-Directory','V10-GitHub-Host','V10-Full','V10-Standard'):
        assert profile in PROFILES
    assert 'K29' not in PROFILES['V10-Full']  # GitHub host support is optional for generic V10-Full.
