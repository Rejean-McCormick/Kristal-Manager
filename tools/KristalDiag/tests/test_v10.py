from __future__ import annotations
import copy,json,shutil
from pathlib import Path

from kristaldiag.config import load_config
from kristaldiag.runner import run
from kristaldiag.schemas import SchemaStore
from kristaldiag.v10 import (
    publication_identity, verify_publication_bundle,
    verify_github_read_surface, verify_github_sync_manifest, verify_github_collection_index,
    verify_hosted_github_read_surface, verify_hosted_github_collection,
    github_read_surface_digest, github_collection_index_digest,
)

ROOT=Path(__file__).resolve().parents[1]
RES=ROOT/'kristaldiag'/'resources'


def _fixture(tmp_path:Path)->Path:
    target=tmp_path/'v10';target.mkdir()
    for q in sorted((RES/'tck/v9/vectors').glob('*.json')):
        if q.name!='logical-commitment-vectors.json':shutil.copy2(q,target/q.name)
    for q in sorted((RES/'tck/v9/workloads').glob('*.json')):shutil.copy2(q,target/q.name)
    kr=target/'.kristal';(kr/'bindings').mkdir(parents=True)
    shutil.copy2(RES/'tck/v10/vectors/node-manifest.example.json',kr/'node.json')
    shutil.copy2(RES/'tck/v10/vectors/github-binding.example.json',kr/'bindings/github.json')
    shutil.copy2(RES/'tck/v10/vectors/v10-capabilities.example.json',kr/'capabilities.json')
    shutil.copy2(RES/'tck/v10/vectors/directory.example.json',kr/'directory.json')
    shutil.copytree(RES/'tck/v10/bundle',target/'publication')
    return target


def test_v10_vectors_validate_against_examiner_contracts():
    store=SchemaStore(ROOT)
    for p in sorted((ROOT/'tck/v10/vectors').glob('*.json')):
        d=json.loads(p.read_text())
        ok,errors=store.validate_v10(d)
        assert ok,(p.name,errors)
        if d.get('artifact_type')=='kristal_host_binding':
            ok,errors=store.validate_github_binding(d);assert ok,errors


def test_v10_bundle_verifies_and_tamper_is_detected(tmp_path):
    src=RES/'tck/v10/bundle';dst=tmp_path/'bundle';shutil.copytree(src,dst)
    good=verify_publication_bundle(dst);assert good['ok'],good
    (dst/'state-snapshot.json').write_bytes((dst/'state-snapshot.json').read_bytes()+b' ')
    bad=verify_publication_bundle(dst)
    assert not bad['ok']
    assert any(x['code'] in {'DIGEST_MISMATCH','SIZE_MISMATCH','STATE_COMMITMENT_MISMATCH'} for x in bad['issues'])


def test_publication_identity_binds_bundle_manifest_digest():
    pub=json.loads((RES/'tck/v10/bundle/publication.json').read_text())
    state=pub['state']
    a=publication_identity(node_id=pub['node_id'],binding_id=pub['binding_id'],state=state,bundle_manifest_digest='sha256:'+'1'*64)
    b=publication_identity(node_id=pub['node_id'],binding_id=pub['binding_id'],state=state,bundle_manifest_digest='sha256:'+'2'*64)
    assert a!=b


def test_negative_contract_cases_fail_structured_validation():
    store=SchemaStore(ROOT)
    node=json.loads((ROOT/'tck/v10/vectors/node-manifest.example.json').read_text());node['roles']=['bad'];node['bindings']=[None]
    ok,errors=store.validate_v10(node);assert not ok and errors
    pub=json.loads((ROOT/'tck/v10/vectors/publication.example.json').read_text());pub['resources']=[{}]
    ok,errors=store.validate_v10(pub);assert not ok and errors
    directory=json.loads((ROOT/'tck/v10/vectors/directory.example.json').read_text());directory['entries']={}
    ok,errors=store.validate_v10(directory);assert not ok and errors


def test_v10_full_reference_fixture_passes(tmp_path,monkeypatch):
    monkeypatch.setenv('KRISTALDIAG_TEST_IN_PROCESS','1')
    target=_fixture(tmp_path);cfg=load_config(ROOT,target,control_dir=tmp_path/'evidence')
    summary,code,current=run(target,cfg,profile='V10-Full',repo_root=ROOT)
    assert code==0, (summary,(current/'summary.txt').read_text())
    assert summary['verdict']=='PASS'
    ids={x['id'] for x in summary['levels']}
    for lid in ('K25','K26','K27','K28','K30','K31'):assert lid in ids


def test_v10_github_host_reference_fixture_passes(tmp_path,monkeypatch):
    monkeypatch.setenv('KRISTALDIAG_TEST_IN_PROCESS','1')
    target=_fixture(tmp_path);cfg=load_config(ROOT,target,control_dir=tmp_path/'evidence')
    summary,code,current=run(target,cfg,profile='V10-GitHub-Host',repo_root=ROOT)
    assert code==0,(summary,(current/'summary.txt').read_text())
    assert next(x for x in summary['levels'] if x['id']=='K29')['verdict']=='PASS'

def test_v10_standard_profile_checks_release_contract_set(tmp_path,monkeypatch):
    monkeypatch.setenv('KRISTALDIAG_TEST_IN_PROCESS','1')
    target=_fixture(tmp_path)
    contracts=target/'contracts';contracts.mkdir()
    shutil.copy2(RES/'locks/release.json',contracts/'release.json')
    shutil.copy2(RES/'locks/contract-set.json',contracts/'contract-set.json')
    cfg=load_config(ROOT,target,control_dir=tmp_path/'evidence-standard')
    summary,code,current=run(target,cfg,profile='V10-Standard',repo_root=ROOT)
    assert code==0,(summary,(current/'summary.txt').read_text())
    assert next(x for x in summary['levels'] if x['id']=='K32')['verdict']=='PASS'



def _hosted_collection_fixture(tmp_path:Path)->Path:
    import hashlib
    target=_fixture(tmp_path)
    root=target/'kristals'/'recipes';(root/'.kristal').mkdir(parents=True);(root/'ai').mkdir();(root/'state').mkdir()
    state=json.loads((RES/'tck/v9/vectors/state-snapshot.example.json').read_text())
    state_bytes=(json.dumps(state,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    (root/'state/state-snapshot.json').write_bytes(state_bytes)
    commitment=state['logical_commitment'];state_ref=state['state_ref']
    (root/'AI_START_HERE.md').write_text('# Start here\nRead AI_MANIFEST.json and ai/INDEX.json.\n',encoding='utf-8')
    ai_manifest={
      'format':'kristal.portable-ai/1.0','kit_version':'3.2.4','title':'Recipes','slug':'recipes','languages':[],
      'state_ref':state_ref,'state_logical_commitment':commitment,'entrypoint':'AI_START_HERE.md',
      'read_order':['AI_START_HERE.md','AI_MANIFEST.json','ai/INDEX.json','state/state-snapshot.json'],
      'state_snapshot':'state/state-snapshot.json','canonical_root':'canon/','sources_root':'sources/','documentation_root':'docs/',
      'ai_read_model_root':'ai/','index':'ai/INDEX.json','context':'ai/CONTEXT.md','coverage':'ai/COVERAGE.json','glossary':'ai/GLOSSARY.md','relations':'ai/RELATIONS.json','questions':'ai/QUESTIONS.md',
      'materializations':{'manifest_count':0,'local_blob_count':0,'external_locator_count':0,'missing_local_locator_count':0,'unlocated_blob_count':0,'indexed':True,'blob_transport':'host_policy'},
      'github_read_surface':{'contract':'kristal.github-read-surface/1.0','target_root_template':'kristals/<slug>/','entrypoint':'AI_START_HERE.md','note':'Operational projection only; never part of the v9 logical commitment.'},
      'portable_reading':{'offline':True,'github_required':False,'network_required':False,'python_required':False,'node_required':False,'executable_tools_required':False},
      'external_dependencies':[],'rules':{'canonical_content':'canon/','derived_ai_content_is_authoritative':False,'ai_output_is_canonical':False,'absence_implies_false':False}
    }
    (root/'AI_MANIFEST.json').write_text(json.dumps(ai_manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    state_digest='sha256:'+hashlib.sha256(state_bytes).hexdigest()
    ai_index={'format':'kristal.ai-index/1.0','state_ref':state_ref,'state_logical_commitment':commitment,'files':[{'path':'state/state-snapshot.json','role':'state_snapshot','media_type':'application/vnd.kristal.state-snapshot+json','size':len(state_bytes),'sha256':state_digest,'state_ref':state_ref,'logical_commitment':commitment}],'materialization_blobs':[]}
    (root/'ai/INDEX.json').write_text(json.dumps(ai_index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    rows=[]
    roles={'AI_START_HERE.md':'ai_entrypoint','AI_MANIFEST.json':'ai_manifest','ai/INDEX.json':'ai_index','state/state-snapshot.json':'state_snapshot'}
    for rel in sorted(roles,key=lambda x:x.encode('utf-8')):
        data=(root/rel).read_bytes();rows.append({'path':rel,'role':roles[rel],'size':len(data),'sha256':'sha256:'+hashlib.sha256(data).hexdigest()})
    surface={'format':'kristal.github-read-surface/1.0','kit_version':'3.2.4','slug':'recipes','target_root':'kristals/recipes','entrypoint':'AI_START_HERE.md','state_ref':state_ref,'state_logical_commitment':commitment,'ready':True,'errors':[],'surface_digest':'','file_count':len(rows),'total_bytes':sum(x['size'] for x in rows),'files':rows,'materialization_object_count':0,'materialization_objects':[]}
    surface['surface_digest']=github_read_surface_digest(surface)
    manifest={'format':'kristal.github-sync-manifest/1.0','manager_version':'0.1.0-alpha.11','read_surface_format':surface['format'],'local_kit_version':'3.2.4','slug':'recipes','title':'Recipes','target_root':'kristals/recipes','entrypoint':'AI_START_HERE.md','state_ref':state_ref,'state_logical_commitment':commitment,'surface_digest':surface['surface_digest'],'file_count':len(rows),'total_bytes':sum(x['size'] for x in rows),'materialization_object_count':0,'files':rows,'policy':{'derived_read_surface':True,'sync_is_not_publication':True,'activation_is_separate':True,'materialization_blobs_are_not_implicitly_copied':True}}
    (root/'.kristal/sync-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    row={'slug':'recipes','title':'Recipes','path':'kristals/recipes','entrypoint':'kristals/recipes/AI_START_HERE.md','state_ref':state_ref,'state_logical_commitment':commitment,'surface_digest':surface['surface_digest'],'file_count':manifest['file_count'],'total_bytes':manifest['total_bytes'],'materialization_object_count':0}
    index={'format':'kristal.github-collection-index/1.0','kristals':[row],'count':1,'index_digest':github_collection_index_digest([row]),'note':'Derived navigation index for GitHub/AI discovery; not semantic authority.'}
    (target/'kristals/index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return target


def test_draft3_github_operational_contracts_validate_and_digest():
    store=SchemaStore(ROOT)
    g=RES/'tck/v10/github'
    surface=json.loads((g/'github-read-surface.example.json').read_text())
    sync=json.loads((g/'github-sync-manifest.example.json').read_text())
    index=json.loads((g/'github-collection-index.example.json').read_text())
    ok,e=store.validate_github_read_surface(surface);assert ok,e
    ok,e=store.validate_github_sync_manifest(sync);assert ok,e
    ok,e=store.validate_github_collection_index(index);assert ok,e
    assert verify_github_read_surface(surface)['ok']
    assert verify_github_sync_manifest(sync)['ok']
    assert verify_github_collection_index(index)['ok']


def test_hosted_github_collection_is_independently_verified_and_tamper_detected(tmp_path):
    target=_hosted_collection_fixture(tmp_path)
    good=verify_hosted_github_collection(target,jobs=4);assert good['ok'],good
    assert verify_hosted_github_read_surface(target,'kristals/recipes')['ok']
    p=target/'kristals/recipes/AI_START_HERE.md';p.write_text(p.read_text()+'tamper\n',encoding='utf-8')
    bad=verify_hosted_github_collection(target,jobs=4)
    assert not bad['ok']
    assert any(x['code'] in {'DIGEST_MISMATCH','SIZE_MISMATCH'} for x in bad['issues'])


def test_v10_github_host_profile_checks_draft3_hosted_collection(tmp_path,monkeypatch):
    monkeypatch.setenv('KRISTALDIAG_TEST_IN_PROCESS','1')
    target=_hosted_collection_fixture(tmp_path);cfg=load_config(ROOT,target,control_dir=tmp_path/'evidence-hosted')
    summary,code,current=run(target,cfg,profile='V10-GitHub-Host',repo_root=ROOT)
    assert code==0,(summary,(current/'summary.txt').read_text())
    k29=next(x for x in summary['levels'] if x['id']=='K29');assert k29['verdict']=='PASS'
    detail=json.loads((current/'levels/K29/result.json').read_text())
    assert any(f['id']=='K29-READ-003' and f['verdict']=='PASS' for f in detail['findings'])
