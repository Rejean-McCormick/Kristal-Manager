from __future__ import annotations
import json,tempfile
from pathlib import Path
from .driver import load_driver,run_action
from .jcs import digest
from .schemas import SchemaStore,ARTIFACT_SCHEMAS
from .utils import utc_now,write_json,run_id

def _extract_artifact(result,target:Path):
    payload=result.get('json')
    if isinstance(payload,dict) and isinstance(payload.get('artifact'),dict):return payload['artifact']
    if isinstance(payload,dict) and payload.get('artifact_path'):
        p=(target/payload['artifact_path']).resolve();p.relative_to(target.resolve());return json.loads(p.read_text(encoding='utf-8'))
    if isinstance(payload,dict) and payload.get('artifact_type'):return payload
    raise ValueError('interop_export must emit JSON artifact, {artifact:{...}}, or {artifact_path:"..."}')

def _validate(store,artifact):
    typ=artifact.get('artifact_type')
    if typ=='kristal_state':return store.validate_v6(artifact)
    if typ in ARTIFACT_SCHEMAS:return store.validate_v7(artifact)
    return False,[f'unsupported exported artifact_type: {typ}']

def _identity(artifact):
    if artifact.get('artifact_type')=='kristal_state' and artifact.get('state_id'):return artifact['state_id']
    return digest(artifact)[2]

def run_interop(producer:Path,consumer:Path,*,repo_root:Path,output:Path,allow_exec:bool=False):
    rid=run_id();report={'schema':'kristaldiag.interop-evidence.v1','run_id':rid,'producer':str(producer.resolve()),'consumer':str(consumer.resolve()),'started_at':utc_now(),'verdict':'ERROR','steps':[]}
    if not allow_exec:
        report['verdict']='BLOCKED';report['message']='Cross-implementation execution requires --allow-exec.';write_json(output,report);return report
    pa=producer.resolve();pb=consumer.resolve();da=load_driver(pa);db=load_driver(pb)
    if not da or not db:
        report['verdict']='BLOCKED';report['message']='Both implementations require kristaldiag-driver.json.';write_json(output,report);return report
    store=SchemaStore(repo_root)
    try:
        exa=run_action(pa,da,'interop_export');report['steps'].append({'step':'A.export','returncode':None if exa is None else exa['returncode']})
        if exa is None or exa['returncode']!=0:raise ValueError('producer interop_export failed or missing')
        art_a=_extract_artifact(exa,pa);ok,errs=_validate(store,art_a)
        if not ok:raise ValueError('producer exported invalid artifact: '+'; '.join(errs[:5]))
        with tempfile.TemporaryDirectory(prefix='kristaldiag-interop-') as td:
            p=Path(td)/'a.json';write_json(p,art_a)
            imb=run_action(pb,db,'interop_import',input_path=p);report['steps'].append({'step':'B.import(A)','returncode':None if imb is None else imb['returncode']})
            if imb is None or imb['returncode']!=0:raise ValueError('consumer interop_import failed or missing')
            exb=run_action(pb,db,'interop_export');report['steps'].append({'step':'B.export','returncode':None if exb is None else exb['returncode']})
            if exb is None or exb['returncode']!=0:raise ValueError('consumer interop_export failed or missing')
            art_b=_extract_artifact(exb,pb);ok,errs=_validate(store,art_b)
            if not ok:raise ValueError('consumer exported invalid artifact: '+'; '.join(errs[:5]))
            q=Path(td)/'b.json';write_json(q,art_b)
            ima=run_action(pa,da,'interop_import',input_path=q);report['steps'].append({'step':'A.import(B)','returncode':None if ima is None else ima['returncode']})
            if ima is None or ima['returncode']!=0:raise ValueError('producer interop_import failed or missing')
        ia,ib=_identity(art_a),_identity(art_b);report['artifact']={'artifact_type':art_a.get('artifact_type'),'schema_version':art_a.get('schema_version'),'producer_identity':ia,'consumer_identity':ib}
        if art_a.get('artifact_type')!=art_b.get('artifact_type') or art_a.get('schema_version')!=art_b.get('schema_version'):raise ValueError('round-trip changed artifact type/version')
        if ia!=ib:raise ValueError(f'round-trip semantic identity mismatch: {ia} != {ib}')
        report['verdict']='PASS';report['message']='A -> B -> A exchange preserved a valid artifact and semantic identity.'
    except Exception as e:
        report['verdict']='FAIL';report['message']=f'{type(e).__name__}: {e}'
    report['ended_at']=utc_now();write_json(output,report);return report
