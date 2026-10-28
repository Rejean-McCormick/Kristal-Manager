import json,shutil
from pathlib import Path
from kristaldiag.config import load_config
from kristaldiag.runner import run
ROOT=Path(__file__).resolve().parents[1]

def copy_fixture(tmp_path):
    dst=tmp_path/'fixture';shutil.copytree(ROOT/'examples/reference-kristall',dst);return dst

def test_v7_projection_reference_passes(tmp_path):
    target=copy_fixture(tmp_path);control=tmp_path/'evidence';cfg=load_config(ROOT,target,control_dir=control)
    summary,code,current=run(target,cfg,profile='V7-Projection',repo_root=ROOT)
    assert summary['verdict']=='PASS';assert code==0
    assert (current/'conformance-verdict.json').is_file()
    verdict=json.loads((current/'conformance-verdict.json').read_text())
    assert verdict['authority_granted'] is False
    assert verdict['qualification_only'] is True

def test_v7_kristall_without_driver_is_partial(tmp_path):
    target=copy_fixture(tmp_path);cfg=load_config(ROOT,target,control_dir=tmp_path/'evidence')
    summary,code,_=run(target,cfg,profile='V7-Kristall',repo_root=ROOT)
    assert summary['verdict']=='PARTIAL';assert code==10

def test_bad_axis_identity_fails_projection(tmp_path):
    target=copy_fixture(tmp_path);p=target/'axis-registry.example.json';d=json.loads(p.read_text());d['axes'][0]['axis_id']='AXIS-BAD';p.write_text(json.dumps(d),encoding='utf-8')
    cfg=load_config(ROOT,target,control_dir=tmp_path/'evidence');summary,code,current=run(target,cfg,profile='V7-Projection',repo_root=ROOT)
    assert summary['verdict']=='FAIL';assert code==20
    k07=json.loads((current/'levels/K07/result.json').read_text());assert any(f['id']=='K07-KQ-001' and f['verdict']=='FAIL' for f in k07['findings'])

def test_malformed_projection_lineage_fails(tmp_path):
    target=copy_fixture(tmp_path);p=target/'v6-compatible-projection.example.json';d=json.loads(p.read_text());d['extensions']['kristal_v7']['generated_from']['source_state_refs'].append('sha256:unknown');p.write_text(json.dumps(d),encoding='utf-8')
    cfg=load_config(ROOT,target,control_dir=tmp_path/'evidence');summary,code,current=run(target,cfg,profile='V7-Projection',repo_root=ROOT)
    assert summary['verdict']=='FAIL';assert code==20
    k09=json.loads((current/'levels/K09/result.json').read_text());assert any(f['id']=='K09-LINEAGE-002' and f['verdict']=='FAIL' for f in k09['findings'])

def test_emitted_reports_validate_against_kristaldiag_schemas(tmp_path):
    import jsonschema
    target=copy_fixture(tmp_path);cfg=load_config(ROOT,target,control_dir=tmp_path/'evidence')
    _,_,current=run(target,cfg,profile='V7-Projection',repo_root=ROOT)
    pairs=[('summary.json','summary.schema.json'),('conformance-verdict.json','conformance-verdict.schema.json')]
    for data_name,schema_name in pairs:
        data=json.loads((current/data_name).read_text());schema=json.loads((ROOT/'schemas'/schema_name).read_text())
        jsonschema.Draft202012Validator(schema).validate(data)
    level=json.loads((current/'levels/K00/result.json').read_text());schema=json.loads((ROOT/'schemas/level-result.schema.json').read_text())
    jsonschema.Draft202012Validator(schema).validate(level)

def test_verify_run_detects_tampered_evidence(tmp_path):
    from kristaldiag.evidence import verify_run
    target=copy_fixture(tmp_path);cfg=load_config(ROOT,target,control_dir=tmp_path/'evidence')
    _,_,current=run(target,cfg,profile='V7-Projection',repo_root=ROOT)
    ok,detail=verify_run(current/'summary.json',ROOT)
    assert ok, detail
    p=current/'levels/K07/result.json'
    p.write_text(p.read_text(encoding='utf-8')+'\n',encoding='utf-8')
    ok,detail=verify_run(current/'summary.json',ROOT)
    assert not ok
    assert any(x['kind']=='manifest-hash-mismatch' for x in detail['problems'])


def test_read_only_guard_detects_non_json_mutation(tmp_path):
    import sys
    target=copy_fixture(tmp_path)
    note=target/'note.txt';note.write_text('before',encoding='utf-8')
    driver={
      'schema':'kristaldiag.driver.v1',
      'actions':{
        'self_test':{'argv':[sys.executable,'-c',"from pathlib import Path;Path('note.txt').write_text('after');print('{}')"]}
      }
    }
    (target/'kristaldiag-driver.json').write_text(json.dumps(driver),encoding='utf-8')
    cfg=load_config(ROOT,target,control_dir=tmp_path/'evidence')
    summary,code,current=run(target,cfg,profile='V7-Kristall',repo_root=ROOT,allow_exec=True)
    assert summary['verdict']=='ERROR';assert code==30
    k14=json.loads((current/'levels/K14/result.json').read_text())
    assert any(f['id']=='K14-MUTATION-003' for f in k14['findings'])

def test_required_skip_blocks_profile_conformance(tmp_path):
    target=tmp_path/'empty';target.mkdir()
    cfg=load_config(ROOT,target,control_dir=tmp_path/'evidence')
    summary,code,current=run(target,cfg,profile='V7-Reader',repo_root=ROOT)
    assert summary['verdict']=='BLOCKED';assert code==20
    k14=json.loads((current/'levels/K14/result.json').read_text())
    gate=next(f for f in k14['findings'] if f['id']=='K14-GATE-002')
    assert any(x.get('effective_verdict')=='BLOCKED' for x in gate['evidence'])
