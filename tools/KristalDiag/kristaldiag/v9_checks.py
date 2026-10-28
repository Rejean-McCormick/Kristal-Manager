from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from .models import Finding, LevelResult
from .schemas import V8_SCHEMAS, V9_SCHEMAS, ARTIFACT_SCHEMAS
from .utils import read_json, sha256_file, utc_now
from .verdicts import combine
from .v9 import (
    LOGICAL_PROFILE,
    STATE_PROFILE,
    artifact_logical_projection,
    is_mutable_selector,
    logical_artifact_commitment,
    state_commitment,
    verify_declared_logical_artifact,
    verify_declared_state,
)

LEVEL_NAMES={
 'K15':'V9 Machine Contracts',
 'K16':'V9 Independent Logical Commitments',
 'K17':'V9 State Snapshot Semantics',
 'K18':'V9 Derivations & Reproducibility',
 'K19':'V9 Materialization Binding',
 'K20':'V9 Exchange Binding',
 'K21':'V9 Build / Publish / Activate',
 'K22':'V9 Polymorphism Workloads',
 'K23':'V9 Negative & Invariance Corpus',
 'K24':'V9 Inherited Compatibility Substrate',
}

DIGEST_RE=re.compile(r'^sha256:[0-9a-f]{64}$')
V9_PROFILES={'V9-State-Reader','V9-Builder','V9-Materializer','V9-Publisher','V9-Full'}


def _f(fid, verdict, message, **kw):
    return Finding(fid, verdict, kw.pop('category','v9'), message, **kw)


def _result(level, findings, metadata=None, started=None):
    verdict=combine([x.verdict for x in findings]) if findings else 'SKIP'
    return LevelResult(level, LEVEL_NAMES[level], verdict, findings, [], started or utc_now(), utc_now(), 0.0, metadata or {})


def _v9_artifacts(ctx):
    out=[]
    for typ in V9_SCHEMAS:
        out.extend(ctx.inv.get(typ))
    return out


def _resource(ctx, *parts):
    return ctx.resource_root.joinpath(*parts)


def k15(ctx):
    s=utc_now();fs=[];arts=_v9_artifacts(ctx)
    if not arts:
        verdict='BLOCKED' if ctx.claimed_profile in V9_PROFILES else 'SKIP'
        fs.append(_f('K15-V9-000',verdict,'No Kristal v9 machine artifact was discovered in the target.'))
        return _result('K15',fs,started=s)
    failures=[];counts={}
    for a in arts:
        counts[a.artifact_type]=counts.get(a.artifact_type,0)+1
        ok,errs=ctx.schemas.validate_v9(a.data)
        if not ok:
            failures.append({'path':a.rel,'artifact_type':a.artifact_type,'errors':errs[:20]})
    fs.append(_f('K15-SCHEMA-001','FAIL' if failures else 'PASS',
                 'V9 machine artifacts validate against their normative schemas.' if not failures else 'One or more V9 artifacts fail their normative schemas.',
                 evidence=failures or counts,standard_ref='Kristal v9: schemas/v9/'))
    for a in ctx.inv.get('kristal_v9_capabilities'):
        reads=set((a.data.get('compatibility') or {}).get('reads') or [])
        required={'kristal_state/6.0','kristall/7.0','kristall/8.0','kristal.state/9.0'}
        missing=sorted(required-reads)
        fs.append(_f('K15-CAP-002','FAIL' if missing else 'PASS','V9 capabilities preserve inherited read boundaries.' if not missing else 'V9 capabilities omit required inherited read boundaries.',path=a.rel,evidence={'missing':missing} if missing else {'reads':sorted(reads)}))
    return _result('K15',fs,metadata={'counts':counts},started=s)


def k16(ctx):
    s=utc_now();fs=[];root=_resource(ctx,'v9','vectors')
    vectors=read_json(root/'logical-commitment-vectors.json');fail=[]
    for v in vectors.get('vectors',[]):
        d=read_json(root/v['file'])
        try:
            got=logical_artifact_commitment(d)['digest'] if v['kind']=='logical_artifact' else state_commitment(d)['digest']
        except Exception as exc:
            fail.append({'id':v['id'],'error':str(exc)});continue
        if got!=v['expected_digest']:
            fail.append({'id':v['id'],'expected':v['expected_digest'],'observed':got})
    fs.append(_f('K16-GOLDEN-001','FAIL' if fail else 'PASS','Independent Python implementation reproduces all normative v9 golden commitments.' if not fail else 'Independent Python implementation disagrees with v9 golden commitments.',evidence=fail or {'vectors':len(vectors.get('vectors',[]))},impact='A disagreement here blocks v9 hash-profile freeze.'))
    target_fail=[];checked=0
    for a in ctx.inv.get('kristal_logical_artifact'):
        checked+=1;ok,actual,errs=verify_declared_logical_artifact(a.data)
        if not ok:target_fail.append({'path':a.rel,'errors':errs,'actual':actual})
    for a in ctx.inv.get('kristal_state_snapshot'):
        checked+=1;ok,actual,errs=verify_declared_state(a.data)
        if not ok:target_fail.append({'path':a.rel,'errors':errs,'actual':actual})
    if checked:
        fs.append(_f('K16-TARGET-002','FAIL' if target_fail else 'PASS','Declared target logical commitments match independent recomputation.' if not target_fail else 'Target contains mismatched declared logical commitments.',evidence=target_fail or {'checked':checked}))
    else:
        fs.append(_f('K16-TARGET-002','BLOCKED' if ctx.claimed_profile in V9_PROFILES else 'SKIP','No target logical artifact/state commitment was available for recomputation.'))
    return _result('K16',fs,started=s)


def k17(ctx):
    s=utc_now();fs=[];states=ctx.inv.get('kristal_state_snapshot')
    if not states:
        fs.append(_f('K17-STATE-000','BLOCKED' if ctx.claimed_profile in V9_PROFILES else 'SKIP','No v9 State Snapshot discovered.'))
        return _result('K17',fs,started=s)
    failures=[];warnings=[]
    for a in states:
        d=a.data;owned=set();external=set()
        for i,m in enumerate(d.get('members') or []):
            aid=m.get('artifact_id')
            if aid in owned:failures.append({'path':a.rel,'field':f'members[{i}]','reason':'duplicate_owned_artifact_id','value':aid})
            owned.add(aid)
            c=m.get('logical_commitment') or {}
            if not DIGEST_RE.fullmatch(str(c.get('digest',''))):failures.append({'path':a.rel,'field':f'members[{i}].logical_commitment','reason':'invalid_digest'})
        for i,r in enumerate(d.get('references') or []):
            key=r.get('artifact_id') or r.get('state_ref')
            if isinstance(key,str) and is_mutable_selector(key):failures.append({'path':a.rel,'field':f'references[{i}]','reason':'mutable_selector','value':key})
            if 'artifact_id' in r:external.add(r.get('artifact_id'))
        overlap=sorted(x for x in (owned & external) if x)
        if overlap:warnings.append({'path':a.rel,'reason':'same_artifact_owned_and_external','artifact_ids':overlap})
        for i,p in enumerate(d.get('parents') or []):
            key=p.get('state_ref')
            if isinstance(key,str) and is_mutable_selector(key):failures.append({'path':a.rel,'field':f'parents[{i}]','reason':'mutable_parent_selector','value':key})
        ok,_,errs=verify_declared_state(d)
        if not ok:failures.append({'path':a.rel,'reason':'commitment_mismatch','errors':errs})
    fs.append(_f('K17-PINNING-001','FAIL' if failures else 'PASS','State membership and external references are immutable/pinned and commitments verify.' if not failures else 'State snapshot pinning or commitment invariants failed.',evidence=failures or {'states':len(states)},standard_ref='Kristal v9 State Snapshots'))
    if warnings:fs.append(_f('K17-BOUNDARY-002','WARN','A state both owns and externally references the same artifact identity.',evidence=warnings,impact='This may blur ownership boundaries even when content remains pinned.'))
    else:fs.append(_f('K17-BOUNDARY-002','PASS','Owned membership and external-reference roles are not conflated in discovered states.'))
    return _result('K17',fs,started=s)


def _local_artifacts_by_id(ctx):
    out={}
    for a in ctx.inv.get('kristal_logical_artifact'):
        if a.data.get('artifact_id'):out.setdefault(a.data['artifact_id'],[]).append(a)
    return out


def k18(ctx):
    s=utc_now();fs=[];arts=ctx.inv.get('kristal_derivation')
    if not arts:
        fs.append(_f('K18-DERIVATION-000','BLOCKED' if ctx.claimed_profile in {'V9-Builder','V9-Full'} else 'SKIP','No v9 Derivation record discovered.'))
        return _result('K18',fs,started=s)
    local=_local_artifacts_by_id(ctx);fail=[];warn=[]
    for a in arts:
        ok,errs=ctx.schemas.validate_v9(a.data)
        if not ok:fail.append({'path':a.rel,'reason':'schema','errors':errs[:20]});continue
        for where in ('inputs','outputs'):
            for i,r in enumerate(a.data.get(where) or []):
                sr=r.get('state_ref')
                if isinstance(sr,str) and is_mutable_selector(sr):fail.append({'path':a.rel,'field':f'{where}[{i}].state_ref','reason':'mutable_selector','value':sr})
                aid=r.get('artifact_id')
                if aid and aid in local:
                    expected=(r.get('logical_commitment') or {}).get('digest')
                    if expected and not any((x.data.get('logical_commitment') or {}).get('digest')==expected for x in local[aid]):
                        fail.append({'path':a.rel,'field':f'{where}[{i}]','reason':'local_commitment_disagrees','artifact_id':aid,'digest':expected})
        det=a.data.get('determinism') or {}
        if det.get('claimed') is True:
            tr=a.data.get('transform') or {}
            if not tr.get('digest'):warn.append({'path':a.rel,'reason':'deterministic_transform_without_digest','transform':tr})
            if not a.data.get('toolchain'):warn.append({'path':a.rel,'reason':'deterministic_build_without_toolchain_record'})
    fs.append(_f('K18-DECLARED-001','FAIL' if fail else 'PASS','Derivations use pinned logical inputs/outputs and are internally consistent.' if not fail else 'Derivation reference or schema invariants failed.',evidence=fail or {'derivations':len(arts)}))
    fs.append(_f('K18-REPRO-002','WARN' if warn else 'PASS','Determinism claims have explicit transform/toolchain evidence.' if not warn else 'Some deterministic claims are structurally valid but underspecified for strong reproducibility.',evidence=warn or None))
    return _result('K18',fs,started=s)


def k19(ctx):
    s=utc_now();fs=[];arts=ctx.inv.get('kristal_materialization_manifest')
    if not arts:
        fs.append(_f('K19-MAT-000','BLOCKED' if ctx.claimed_profile in {'V9-Materializer','V9-Full'} else 'SKIP','No v9 Materialization Manifest discovered.'))
        return _result('K19',fs,started=s)
    local=_local_artifacts_by_id(ctx);fail=[]
    for a in arts:
        ok,errs=ctx.schemas.validate_v9(a.data)
        if not ok:fail.append({'path':a.rel,'reason':'schema','errors':errs[:20]});continue
        src=a.data.get('source') or {};aid=src.get('artifact_id');expected=(src.get('logical_commitment') or {}).get('digest')
        if aid in local and expected and not any((x.data.get('logical_commitment') or {}).get('digest')==expected for x in local[aid]):
            fail.append({'path':a.rel,'reason':'source_commitment_disagrees','artifact_id':aid,'digest':expected})
        keys=[]
        for seg in a.data.get('segments') or []:
            if seg.get('segment_key') is not None:keys.append(seg.get('segment_key'))
        if len(keys)!=len(set(keys)):fail.append({'path':a.rel,'reason':'duplicate_segment_key','keys':keys})
        if (a.data.get('reconstructability') or {}).get('lossless') is not True:fail.append({'path':a.rel,'reason':'lossless_not_true'})
    fs.append(_f('K19-BINDING-001','FAIL' if fail else 'PASS','Materializations bind to exact logical source commitments and preserve lossless reconstructability.' if not fail else 'Materialization binding/reconstructability failed.',evidence=fail or {'manifests':len(arts)},standard_ref='Kristal v9 Materialization'))
    return _result('K19',fs,started=s)


def k20(ctx):
    s=utc_now();fs=[];arts=ctx.inv.get('kristal_exchange')
    if not arts:
        fs.append(_f('K20-EXCHANGE-000','SKIP','No v9 Exchange manifest discovered.'))
        return _result('K20',fs,started=s)
    states={}
    for a in ctx.inv.get('kristal_state_snapshot'):states.setdefault(a.data.get('state_ref'),[]).append(a.data)
    known_artifacts=set(_local_artifacts_by_id(ctx));fail=[];warn=[]
    for a in arts:
        ok,errs=ctx.schemas.validate_v9(a.data)
        if not ok:fail.append({'path':a.rel,'reason':'schema','errors':errs[:20]});continue
        ref=a.data.get('state') or {};sid=ref.get('state_ref');dig=(ref.get('logical_commitment') or {}).get('digest')
        if sid in states and dig and not any((x.get('logical_commitment') or {}).get('digest')==dig for x in states[sid]):fail.append({'path':a.rel,'reason':'state_commitment_disagrees','state_ref':sid,'digest':dig})
        for m in a.data.get('materializations') or []:
            if known_artifacts and m.get('artifact_id') not in known_artifacts:warn.append({'path':a.rel,'reason':'materialization_artifact_not_local','artifact_id':m.get('artifact_id')})
    fs.append(_f('K20-STATE-001','FAIL' if fail else 'PASS','Exchange manifests bind to exact state commitments.' if not fail else 'Exchange state binding failed.',evidence=fail or {'exchanges':len(arts)}))
    if warn:fs.append(_f('K20-LOCALITY-002','WARN','Some Exchange materializations refer to artifacts not present locally; this is allowed but cannot be cross-checked.',evidence=warn))
    else:fs.append(_f('K20-LOCALITY-002','PASS','Locally resolvable Exchange artifact bindings are consistent.'))
    return _result('K20',fs,started=s)


def _activation_transition(current: dict[str,Any] | None, activation: dict[str,Any]) -> tuple[bool,str]:
    expected=activation.get('expected_previous')
    if expected:
        got=((current or {}).get('active_state') or {}).get('logical_commitment',{}).get('digest')
        want=(expected.get('logical_commitment') or {}).get('digest')
        if got!=want:return False,f'compare-and-swap expected {want}, found {got}'
    if current is not None and activation.get('channel_id')==current.get('channel_id'):
        if int(activation.get('sequence',-1)) <= int(current.get('sequence',-1)):
            return False,'sequence must increase on the same channel'
    return True,'ok'


def k21(ctx):
    s=utc_now();fs=[];arts=ctx.inv.get('kristal_activation');fail=[]
    for a in arts:
        ok,errs=ctx.schemas.validate_v9(a.data)
        if not ok:fail.append({'path':a.rel,'reason':'schema','errors':errs[:20]})
        if a.data.get('previous_state') and a.data.get('expected_previous'):
            p=(a.data['previous_state'].get('logical_commitment') or {}).get('digest');e=(a.data['expected_previous'].get('logical_commitment') or {}).get('digest')
            if p!=e:fail.append({'path':a.rel,'reason':'previous_expected_previous_disagree','previous':p,'expected':e})
    fs.append(_f('K21-ACTIVATION-001','FAIL' if fail else ('PASS' if arts else 'SKIP'),'Activation records are structurally coherent.' if not fail and arts else ('Activation records contain lifecycle inconsistencies.' if fail else 'No target activation record discovered.'),evidence=fail or ({'activations':len(arts)} if arts else None)))
    # Independent protocol test: successful first activation, CAS-protected advance, stale CAS rejection.
    fixture=read_json(_resource(ctx,'v9','vectors','activation.example.json'))
    first=copy.deepcopy(fixture);first['sequence']=1
    ok1,_=_activation_transition(None,first)
    second=copy.deepcopy(fixture);second['sequence']=2;second['expected_previous']=copy.deepcopy(first['active_state'])
    second['previous_state']=copy.deepcopy(first['active_state'])
    ok2,_=_activation_transition(first,second)
    stale=copy.deepcopy(second);stale['sequence']=3;stale['expected_previous']['logical_commitment']['digest']='sha256:'+'0'*64
    ok3,_=_activation_transition(second,stale)
    protocol_ok=ok1 and ok2 and not ok3
    fs.append(_f('K21-CAS-002','PASS' if protocol_ok else 'FAIL','Independent lifecycle model accepts monotonic/CAS activation and rejects stale compare-and-swap.' if protocol_ok else 'Independent lifecycle model failed its activation/CAS corpus.',evidence={'initial':ok1,'advance':ok2,'stale_rejected':not ok3},standard_ref='Kristal v9 Build / Publish / Activate'))
    return _result('K21',fs,started=s)


def k22(ctx):
    s=utc_now();fs=[];root=_resource(ctx,'v9','workloads');fail=[];shapes=[]
    for p in sorted(root.glob('*.json')):
        d=read_json(p);typ=d.get('artifact_type');shapes.append({'file':p.name,'artifact_type':typ,'contract':d.get('logical_contract')})
        ok,errs=ctx.schemas.validate_v9(d)
        if not ok:fail.append({'file':p.name,'reason':'schema','errors':errs[:20]});continue
        if typ=='kristal_logical_artifact':
            ok2,actual,errs2=verify_declared_logical_artifact(d)
        elif typ=='kristal_state_snapshot':
            ok2,actual,errs2=verify_declared_state(d)
        else:
            ok2=False;actual=None;errs2=['unexpected workload artifact_type']
        if not ok2:fail.append({'file':p.name,'reason':'commitment','errors':errs2,'actual':actual})
    fs.append(_f('K22-POLY-001','FAIL' if fail else 'PASS','All v9 polymorphic workload vectors validate without being converted to a universal data shape.' if not fail else 'One or more polymorphic workload vectors fail schema/commitment qualification.',evidence=fail or shapes,standard_ref='Kristal v9 polymorphism gate'))
    required_names={'relation.logical-artifact.json','procedure-dag.logical-artifact.json','multiplex-graph.logical-artifact.json','formula-ast.logical-artifact.json','epistemic-corpus.logical-artifact.json','federation.state-snapshot.json'}
    present={p.name for p in root.glob('*.json')};missing=sorted(required_names-present)
    fs.append(_f('K22-COVERAGE-002','FAIL' if missing else 'PASS','Reference polymorphism corpus covers relation, procedure DAG, multiplex graph, formal AST, epistemic corpus and federation.' if not missing else 'Reference polymorphism corpus is incomplete.',evidence={'missing':missing} if missing else {'workloads':len(present)}))
    return _result('K22',fs,started=s)


def k23(ctx):
    s=utc_now();fs=[];root=_resource(ctx,'v9','vectors');base=read_json(root/'logical-artifact.example.json');state=read_json(root/'state-snapshot.example.json');fail=[]
    c0=logical_artifact_commitment(base)['digest']
    # semantic identifiers and authority are excluded
    for field,value in [('artifact_id','urn:changed:identity'),('authority_ref','urn:changed:authority')]:
        m=copy.deepcopy(base);m[field]=value
        if logical_artifact_commitment(m)['digest']!=c0:fail.append(f'{field} unexpectedly changes artifact logical commitment')
    # logical payload and extensions are included
    m=copy.deepcopy(base);m['payload']['steps'][0]['action']='changed'
    if logical_artifact_commitment(m)['digest']==c0:fail.append('payload mutation did not change artifact logical commitment')
    m=copy.deepcopy(base);m['extensions']={'domain_semantics':{'x':1}}
    if logical_artifact_commitment(m)['digest']==c0:fail.append('extensions mutation did not change artifact logical commitment')
    # Arrays remain order-significant unless domain normalization has happened before profile application.
    m=copy.deepcopy(base);m['payload']['steps']=list(reversed(m['payload']['steps']))
    if logical_artifact_commitment(m)['digest']==c0:fail.append('ordered payload array reversal did not change artifact logical commitment')
    # Dependencies are sorted by the profile.
    dep1={'artifact_id':'urn:b','logical_contract':{'id':'x','version':'1'},'logical_commitment':{'profile':LOGICAL_PROFILE,'digest':'sha256:'+'1'*64}}
    dep2={'artifact_id':'urn:a','logical_contract':{'id':'x','version':'1'},'logical_commitment':{'profile':LOGICAL_PROFILE,'digest':'sha256:'+'2'*64}}
    a1=copy.deepcopy(base);a1['dependencies']=[dep1,dep2]
    a2=copy.deepcopy(base);a2['dependencies']=[dep2,dep1]
    if logical_artifact_commitment(a1)['digest']!=logical_artifact_commitment(a2)['digest']:fail.append('dependency order changes logical commitment')
    s0=state_commitment(state)['digest']
    for field,value in [('state_ref','urn:changed:state'),('authority_ref','urn:changed:authority'),('created_at','2030-01-01T00:00:00Z')]:
        m=copy.deepcopy(state);m[field]=value
        if state_commitment(m)['digest']!=s0:fail.append(f'{field} unexpectedly changes state logical commitment')
    m=copy.deepcopy(state);m['parents']=[{'state_ref':'urn:parent','logical_commitment':{'profile':STATE_PROFILE,'digest':'sha256:'+'3'*64}}]
    if state_commitment(m)['digest']!=s0:fail.append('parent lineage unexpectedly changes state logical commitment')
    m=copy.deepcopy(state);m['scope']={'domain':'different'}
    if state_commitment(m)['digest']==s0:fail.append('state scope mutation did not change state logical commitment')
    fs.append(_f('K23-INVARIANTS-001','FAIL' if fail else 'PASS','Independent adversarial corpus confirms v9 commitment inclusion/exclusion and ordering rules.' if not fail else 'Commitment invariance/adversarial corpus found contradictions.',evidence=fail or {'artifact_profile':LOGICAL_PROFILE,'state_profile':STATE_PROFILE},impact='A failure blocks profile freeze.'))
    # Declared commitment mismatch must be rejected.
    bad=copy.deepcopy(base);bad['logical_commitment']['digest']='sha256:'+'0'*64
    ok,_,errs=verify_declared_logical_artifact(bad)
    fs.append(_f('K23-MISMATCH-002','PASS' if not ok else 'FAIL','A syntactically valid but false declared logical commitment is rejected.' if not ok else 'False logical commitment was accepted.',evidence=errs if not ok else None))
    return _result('K23',fs,started=s)


def k24(ctx):
    s=utc_now();fs=[];fail=[];counts={'v6':0,'v7':0,'v8':0}
    # The examiner carries an exact copy of the inherited substrate pinned by the
    # v9 compatibility lock. This baseline is deliberately separate from the
    # legacy V7-profile fixtures used by KristalDiag itself.
    import jsonschema
    base=Path(__file__).resolve().parent/'resources'/'baseline'/'9.0.0-draft.1'
    def validate_file(schema_path:Path, data:dict):
        schema=read_json(schema_path)
        validator=jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker())
        errs=sorted(validator.iter_errors(data),key=lambda e:list(e.absolute_path))
        return [('/'+'/'.join(str(x) for x in e.absolute_path) if e.absolute_path else '/')+': '+e.message for e in errs]
    # Frozen v6 positive vector.
    p=base/'tck'/'v6'/'kristal-state.example.json';d=read_json(p);errs=validate_file(base/'schemas'/'v6'/'kristal-state.schema.json',d);counts['v6']+=1
    if errs:fail.append({'surface':'v6','file':p.name,'errors':errs[:20]})
    # Frozen v7 vectors: schema-level compatibility baseline.
    for p in sorted((base/'tck'/'v7').glob('*.json')):
        d=read_json(p);typ=d.get('artifact_type')
        if typ in ARTIFACT_SCHEMAS:
            counts['v7']+=1;errs=validate_file(base/'schemas'/'v7'/ARTIFACT_SCHEMAS[typ],d)
            if errs:fail.append({'surface':'v7','file':p.name,'errors':errs[:20]})
        elif typ=='kristal_state':
            counts['v6']+=1;errs=validate_file(base/'schemas'/'v6'/'kristal-state.schema.json',d)
            if errs:fail.append({'surface':'v6-v7-projection','file':p.name,'errors':errs[:20]})
    # Frozen v8 vectors.
    for p in sorted((base/'tck'/'v8').glob('*.json')):
        d=read_json(p);typ=d.get('artifact_type')
        if typ in V8_SCHEMAS:
            counts['v8']+=1;errs=validate_file(base/'schemas'/'v8'/V8_SCHEMAS[typ],d)
            if errs:fail.append({'surface':'v8','file':p.name,'errors':errs[:20]})
    fs.append(_f('K24-FROZEN-001','FAIL' if fail else 'PASS','Vendored v9 compatibility baseline validates under the exact inherited v6/v7/v8 schemas.' if not fail else 'Inherited frozen TCK/schema qualification failed.',evidence=fail or counts,standard_ref='Kristal v9 compatibility contract'))

    # For a Standard repository, independently verify every byte listed in the
    # compatibility lock and then apply semantic integrity checks that a byte
    # lock alone cannot provide.
    lock=ctx.scan_root/'contracts'/'v9-compatibility-lock.json' if ctx.scan_root.is_dir() else None
    if lock and lock.is_file():
        try:
            target_lock=read_json(lock);vendored=read_json(base/'contracts'/'v9-compatibility-lock.json')
            drift=[]
            if target_lock.get('release')!=vendored.get('release') or target_lock.get('format')!=vendored.get('format'):
                drift.append({'reason':'lock_header_mismatch','target':{'format':target_lock.get('format'),'release':target_lock.get('release')},'expected':{'format':vendored.get('format'),'release':vendored.get('release')}})
            errata_doc=None;errata_by_path={};errata_fail=[];accepted_errata=[]
            ep=ctx.scan_root/'contracts'/'compatibility-errata.json'
            if ep.is_file():
                try:
                    errata_doc=read_json(ep)
                    if errata_doc.get('format')!='kristal.compatibility-errata/v1':
                        errata_fail.append({'reason':'format','observed':errata_doc.get('format')})
                    entries=errata_doc.get('entries') or []
                    for e in entries:
                        rel=e.get('path') if isinstance(e,dict) else None
                        if not rel or rel in errata_by_path:errata_fail.append({'reason':'invalid_or_duplicate_path','path':rel})
                        else:errata_by_path[rel]=e
                except Exception as exc:errata_fail.append({'reason':'parse_error','error':f'{type(exc).__name__}: {exc}'})
            lock_paths=set()
            for row in target_lock.get('files') or []:
                rel=row.get('path');lock_paths.add(rel);q=ctx.scan_root/rel if rel else None
                if not q or not q.is_file():drift.append({'path':rel,'reason':'missing'});continue
                hx='sha256:'+sha256_file(q);size=q.stat().st_size
                if hx==row.get('sha256') and size==row.get('bytes'):continue
                e=errata_by_path.get(rel)
                if not e:
                    drift.append({'path':rel,'reason':'digest_or_size_mismatch','expected_sha256':row.get('sha256'),'observed_sha256':hx,'expected_bytes':row.get('bytes'),'observed_bytes':size});continue
                problems=[]
                if e.get('locked_sha256')!=row.get('sha256') or e.get('locked_bytes')!=row.get('bytes'):problems.append('historical_lock_binding')
                if e.get('corrected_sha256')!=hx or e.get('corrected_bytes')!=size:problems.append('corrected_bytes_binding')
                if e.get('semantic_change') is not False:problems.append('semantic_change_must_be_false')
                mirror=e.get('mirror')
                if mirror:
                    m=ctx.scan_root/mirror
                    if not m.is_file() or m.read_bytes()!=q.read_bytes():problems.append('mirror_mismatch')
                if problems:drift.append({'path':rel,'reason':'invalid_compatibility_erratum','problems':problems})
                else:accepted_errata.append({'id':e.get('id'),'path':rel,'locked_sha256':row.get('sha256'),'corrected_sha256':hx})
            for rel in sorted(set(errata_by_path)-lock_paths):errata_fail.append({'path':rel,'reason':'erratum_path_not_in_v9_lock'})
            if errata_fail:drift.extend({'reason':'compatibility_errata_invalid',**x} for x in errata_fail)
            fs.append(_f('K24-LOCK-002','FAIL' if drift else 'PASS','Target v9 compatibility lock and any explicit compatibility errata bind inherited v6/v7/v8 bytes exactly.' if not drift else 'Target compatibility lock/errata drift was detected.',evidence=drift or {'entries':len(target_lock.get('files') or []),'accepted_errata':accepted_errata}))
            fs.append(_f('K24-ERRATA-004','FAIL' if errata_fail else ('PASS' if errata_doc else 'SKIP'),'Explicit compatibility errata are independently bound to historical lock bytes and corrected active bytes.' if errata_doc and not errata_fail else ('Compatibility errata validation failed.' if errata_fail else 'No compatibility errata declared.'),evidence=errata_fail or accepted_errata or None))
        except Exception as exc:
            fs.append(_f('K24-LOCK-002','ERROR','Could not verify target v9 compatibility lock.',evidence=f'{type(exc).__name__}: {exc}'))

        identity_fail=[]
        # Portable-state artifacts inside inherited TCKs must still satisfy the
        # frozen v6 identity rule, not merely the JSON Schema.
        candidates=[]
        for rel in ('tck/v6/vectors/kristal-state/kristal-state.example.json','tck/v7/vectors/v6-compatible-projection.example.json'):
            q=ctx.scan_root/rel
            if q.is_file():candidates.append((rel,q))
        from .jcs import digest as _jcs_digest
        for rel,q in candidates:
            d=read_json(q);target=copy.deepcopy(d)
            for key in ('state_id','content_hash','signatures'):target.pop(key,None)
            _,hx,sid=_jcs_digest(target)
            declared=d.get('state_id');ch=d.get('content_hash') or {}
            if declared!=sid or ch.get('alg')!='sha256' or ch.get('value')!=hx:
                identity_fail.append({'path':rel,'declared_state_id':declared,'expected_state_id':sid,'declared_content_hash':ch,'expected_sha256':hx})
            e=errata_by_path.get(rel) if 'errata_by_path' in locals() else None
            if e and e.get('declared_identity_after') and e.get('declared_identity_after')!=sid:
                identity_fail.append({'path':rel,'reason':'errata_declared_identity_after_mismatch','errata':e.get('declared_identity_after'),'expected_state_id':sid})
        fs.append(_f('K24-IDENTITY-003','FAIL' if identity_fail else 'PASS','Inherited portable-state TCK artifacts preserve the frozen v6 canonical identity rule.' if not identity_fail else 'An inherited portable-state TCK artifact is schema-valid but has a stale canonical identity.',evidence=identity_fail or {'checked':len(candidates)},impact='A frozen invalid identity vector must be resolved explicitly before final v9 qualification.'))
    else:
        caps=ctx.inv.get('kristal_v9_capabilities')
        if caps:fs.append(_f('K24-LOCK-002','PASS','Non-Standard target exposes v9 capabilities; byte-level compatibility locks apply to the Standard repository.'))
        else:fs.append(_f('K24-LOCK-002','SKIP','No Standard compatibility-lock file is applicable to this target.'))
    return _result('K24',fs,started=s)


V9_CHECKS={f'K{i:02d}':globals()[f'k{i:02d}'] for i in range(15,25)}
