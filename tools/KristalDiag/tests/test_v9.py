import copy
import json
import shutil
from pathlib import Path

from kristaldiag.config import load_config
from kristaldiag.runner import run
from kristaldiag.schemas import SchemaStore, V9_SCHEMAS
from kristaldiag.v9 import logical_artifact_commitment, state_commitment

ROOT=Path(__file__).resolve().parents[1]


def _v9_fixture(tmp_path:Path):
    target=tmp_path/'v9-fixture';target.mkdir()
    for p in sorted((ROOT/'tck/v9/vectors').glob('*.json')):
        if p.name!='logical-commitment-vectors.json':shutil.copy2(p,target/p.name)
    for p in sorted((ROOT/'tck/v9/workloads').glob('*.json')):shutil.copy2(p,target/p.name)
    return target


def test_v9_golden_commitments_are_independent_and_exact():
    vectors=json.loads((ROOT/'tck/v9/vectors/logical-commitment-vectors.json').read_text(encoding='utf-8'))
    for v in vectors['vectors']:
        d=json.loads((ROOT/'tck/v9/vectors'/v['file']).read_text(encoding='utf-8'))
        got=logical_artifact_commitment(d)['digest'] if v['kind']=='logical_artifact' else state_commitment(d)['digest']
        assert got==v['expected_digest'],v['id']


def test_v9_identity_and_authority_do_not_change_artifact_commitment():
    p=ROOT/'tck/v9/vectors/logical-artifact.example.json';d=json.loads(p.read_text(encoding='utf-8'));base=logical_artifact_commitment(d)['digest']
    x=copy.deepcopy(d);x['artifact_id']='urn:other';assert logical_artifact_commitment(x)['digest']==base
    x=copy.deepcopy(d);x['authority_ref']='urn:other-authority';assert logical_artifact_commitment(x)['digest']==base
    x=copy.deepcopy(d);x['payload']['steps'][0]['action']='different';assert logical_artifact_commitment(x)['digest']!=base


def test_v9_state_lineage_identity_and_authority_are_excluded():
    p=ROOT/'tck/v9/vectors/state-snapshot.example.json';d=json.loads(p.read_text(encoding='utf-8'));base=state_commitment(d)['digest']
    for field,value in [('state_ref','urn:other'),('authority_ref','urn:authority:other'),('created_at','2030-01-01T00:00:00Z')]:
        x=copy.deepcopy(d);x[field]=value;assert state_commitment(x)['digest']==base
    x=copy.deepcopy(d);x['parents']=[{'state_ref':'urn:p','logical_commitment':{'profile':'kristal.state-commitment/jcs-sha256-v1','digest':'sha256:'+'1'*64}}]
    assert state_commitment(x)['digest']==base
    x=copy.deepcopy(d);x['scope']={'domain':'other'};assert state_commitment(x)['digest']!=base


def test_v9_positive_vectors_validate():
    store=SchemaStore(ROOT)
    for p in sorted((ROOT/'tck/v9/vectors').glob('*.json')):
        if p.name=='logical-commitment-vectors.json':continue
        d=json.loads(p.read_text(encoding='utf-8'));assert d['artifact_type'] in V9_SCHEMAS
        ok,errs=store.validate_v9(d);assert ok,(p.name,errs)
    for p in sorted((ROOT/'tck/v9/workloads').glob('*.json')):
        d=json.loads(p.read_text(encoding='utf-8'));ok,errs=store.validate_v9(d);assert ok,(p.name,errs)


def test_v9_full_reference_fixture_passes(tmp_path):
    target=_v9_fixture(tmp_path);cfg=load_config(ROOT,target,control_dir=tmp_path/'evidence')
    summary,code,current=run(target,cfg,profile='V9-Full',repo_root=ROOT)
    assert summary['verdict']=='PASS';assert code==0
    k16=json.loads((current/'levels/K16/result.json').read_text());assert k16['verdict']=='PASS'
    k22=json.loads((current/'levels/K22/result.json').read_text());assert k22['verdict']=='PASS'


def test_v9_false_declared_commitment_fails(tmp_path):
    target=_v9_fixture(tmp_path);p=target/'logical-artifact.example.json';d=json.loads(p.read_text());d['logical_commitment']['digest']='sha256:'+'0'*64;p.write_text(json.dumps(d),encoding='utf-8')
    cfg=load_config(ROOT,target,control_dir=tmp_path/'evidence');summary,code,current=run(target,cfg,profile='V9-State-Reader',repo_root=ROOT)
    assert summary['verdict']=='FAIL';assert code==20
    k16=json.loads((current/'levels/K16/result.json').read_text());assert any(f['id']=='K16-TARGET-002' and f['verdict']=='FAIL' for f in k16['findings'])
