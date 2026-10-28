from __future__ import annotations
import copy, json, os, re, time
from pathlib import Path
from typing import Any
from .models import Finding,Artifact,LevelResult
from .verdicts import combine
from .utils import utc_now,sha256_file,relpath,read_json
from .jcs import canonicalize,digest
from .schemas import SchemaStore,ARTIFACT_SCHEMAS
from .driver import load_driver,run_action

LEVEL_NAMES={
 'K00':'Control & Discovery','K01':'Repository & Static Integrity','K02':'Kristal State v6','K03':'Kristall v7 Metadata',
 'K04':'Canonicalization & Identity','K05':'Assertion Families','K06':'Mesh','K07':'Axes & Subjects','K08':'Surfaces & Projection Readiness',
 'K09':'Projection','K10':'Semantic Resonance','K11':'Interoperability','K12':'Determinism & Reproducibility','K13':'Negative & Adversarial Corpus','K14':'Conformance & Release Gate'
}

def _result(level, findings, artifacts=None, metadata=None, started=None):
    verdict=combine([f.verdict for f in findings]) if findings else 'SKIP'
    return LevelResult(level,LEVEL_NAMES[level],verdict,findings,artifacts or [],started or utc_now(),utc_now(),0.0,metadata or {})

def _f(id,verdict,message,**kw): return Finding(id,verdict,kw.pop('category','conformance'),message,**kw)

def k00(ctx):
    s=utc_now(); inv=ctx.inv; fs=[]; arts=[]
    # Diagnostic integrity: verify the exact vendored contracts/TCK before trusting results.
    rroot=Path(__file__).resolve().parent/'resources'
    manifest_path=rroot/'contract-manifest.json'
    integrity=[]
    try:
        cm=read_json(manifest_path)
        for rel,hx in (cm.get('files') or {}).items():
            p=rroot/rel
            if not p.is_file():integrity.append((rel,'missing'))
            elif sha256_file(p)!=hx:integrity.append((rel,'hash_mismatch'))
    except Exception as e:integrity.append(('contract-manifest',str(e)))
    fs.append(_f('K00-INTEGRITY-000','FAIL' if integrity else 'PASS','KristalDiag vendored contract/TCK integrity '+('failed.' if integrity else 'verified.'),evidence=integrity or {'manifest':str(manifest_path)},impact='A damaged diagnostic contract invalidates downstream conformance evidence.'))
    if ctx.target.exists(): fs.append(_f('K00-TARGET-001','PASS','Target exists.',path=str(ctx.target)))
    else: fs.append(_f('K00-TARGET-001','CONFIG_ERROR','Target does not exist.',path=str(ctx.target))); return _result('K00',fs,started=s)
    if inv.scan_limit_reached:
        fs.append(_f('K00-SCAN-LIMIT-006','WARN','JSON discovery reached max_json_files; inventory may be incomplete.',evidence={'max_json_files':ctx.config.data.get('max_json_files')},remediation='Increase max_json_files or narrow the diagnostic target.'))
    if inv.parse_errors:
        for p,e in inv.parse_errors[:25]:fs.append(_f('K00-JSON-002','WARN','JSON parse error discovered.',path=p,evidence=e,remediation='Repair or exclude the malformed JSON artifact.'))
    kinds={k:len(v) for k,v in inv.by_type.items()}
    fs.append(_f('K00-DISCOVERY-003','PASS',f'Discovered {len(inv.artifacts)} JSON objects across {len(kinds)} artifact types.',evidence=kinds))
    if inv.manifests:fs.append(_f('K00-KRISTALL-004','PASS',f'Discovered {len(inv.manifests)} Kristall manifest(s).',evidence=[a.rel for a in inv.manifests]))
    if inv.get('kristal_state'):fs.append(_f('K00-V6-005','PASS',f'Discovered {len(inv.get("kristal_state"))} portable v6 state(s).'))
    v9_count=sum(len(inv.get(t)) for t in ('kristal_logical_artifact','kristal_state_snapshot','kristal_derivation','kristal_materialization_manifest','kristal_exchange','kristal_activation','kristal_v9_capabilities'))
    if v9_count:fs.append(_f('K00-V9-007','PASS',f'Discovered {v9_count} Kristal v9 machine artifact(s).'))
    v10_count=sum(len(inv.get(t)) for t in ('kristal_node_manifest','kristal_host_binding','kristal_publication','kristal_directory','kristal_v10_capabilities'))
    if v10_count:fs.append(_f('K00-V10-008','PASS',f'Discovered {v10_count} Kristal v10 hosted-network artifact(s).'))
    if inv.implementation_manifest:fs.append(_f('K00-IMPL-006','PASS','Discovered KristalDiag implementation declaration.',path=inv.implementation_manifest.rel))
    meta={'artifact_types':kinds,'is_standard_repo':inv.is_standard_repo,'claimed_profile':ctx.claimed_profile,'target_kind':ctx.target_kind}
    return _result('K00',fs,arts,meta,s)

def k01(ctx):
    s=utc_now(); fs=[]; root=ctx.scan_root
    # Read-only static integrity: JSON parseability and symlink escape detection.
    if ctx.inv.parse_errors:
        fs.extend(_f('K01-JSON-001','FAIL','Malformed JSON is part of the diagnostic target.',path=p,evidence=e,remediation='Repair malformed JSON before conformance qualification.') for p,e in ctx.inv.parse_errors)
    else:fs.append(_f('K01-JSON-001','PASS','All discovered JSON artifacts are parseable.'))
    escaped=[]
    if root.is_dir():
        for base,dirs,files in os.walk(root,followlinks=False):
            for name in dirs+files:
                p=Path(base,name)
                if not p.is_symlink():continue
                try:p.resolve().relative_to(root.resolve())
                except Exception:escaped.append(relpath(p,root))
    if escaped:fs.append(_f('K01-SYMLINK-002','WARN','Symlinks escape the diagnostic root.',evidence=escaped,impact='External content is intentionally not traversed; repository shape may be incomplete.'))
    else:fs.append(_f('K01-SYMLINK-002','PASS','No escaping symlink was discovered.'))
    if ctx.inv.is_standard_repo:
        expected=['README.md','contracts/contract-set.json','contracts/v9-compatibility-lock.json','schemas/v6/kristal-state.schema.json','schemas/v7','schemas/v8','schemas/v9','tck/v9']
        missing=[x for x in expected if not (root/x).exists()]
        fs.append(_f('K01-STANDARD-003','FAIL' if missing else 'PASS','Kristal Standard repository surface '+('is incomplete.' if missing else 'is present.'),evidence={'missing':missing}))
    return _result('K01',fs,started=s)

def _verify_v6_identity(data):
    target=copy.deepcopy(data)
    for key in ('state_id','content_hash','signatures'):target.pop(key,None)
    _,hx,sid=digest(target)
    declared=data.get('state_id')
    ch=data.get('content_hash') or {}
    hash_ok=(not ch) or (ch.get('alg')=='sha256' and ch.get('value')==hx)
    return sid,declared==sid,hash_ok,hx

def k02(ctx):
    s=utc_now(); fs=[]; arts=ctx.inv.get('kristal_state')
    if not arts:
        # A Kristall may reference external source states. This is not a v6 reader failure by itself.
        verdict='PARTIAL' if ctx.claimed_profile else 'SKIP'
        fs.append(_f('K02-V6-000',verdict,'No local kristal_state/6.0 artifact was discovered.',impact='Source acceptance cannot be demonstrated from local artifacts alone.'))
        return _result('K02',fs,started=s)
    for a in arts:
        ok,errs=ctx.schemas.validate_v6(a.data)
        if not ok:
            fs.append(_f('K02-SCHEMA-001','FAIL','v6 state fails kristal-state.schema.json.',path=a.rel,evidence=errs[:25],standard_ref='Kristal v6 portable state contract'))
            continue
        fs.append(_f('K02-SCHEMA-001','PASS','v6 state validates against the unchanged portable schema.',path=a.rel))
        sid,id_ok,hash_ok,hx=_verify_v6_identity(a.data)
        if re.fullmatch(r'sha256:[0-9a-f]{64}',str(a.data.get('state_id','')) or ''):
            fs.append(_f('K02-ID-002','PASS' if id_ok else 'FAIL','v6 state identity matches RFC8785/SHA-256 hash target.' if id_ok else 'v6 state_id does not match canonical hash target.',path=a.rel,expected=sid,observed=a.data.get('state_id'),standard_ref='Kristal v6 § Identity and canonicalization'))
            fs.append(_f('K02-HASH-003','PASS' if hash_ok else 'FAIL','v6 content_hash matches canonical hash target.' if hash_ok else 'v6 content_hash does not match canonical hash target.',path=a.rel,expected=hx,observed=(a.data.get('content_hash') or {}).get('value')))
    return _result('K02',fs,started=s)

def k03(ctx):
    s=utc_now(); fs=[]; v7=[]
    for typ in ARTIFACT_SCHEMAS:
        for a in ctx.inv.get(typ):
            v7.append(a);ok,errs=ctx.schemas.validate_v7(a.data)
            fs.append(_f('K03-SCHEMA-001','PASS' if ok else 'FAIL',f'{typ} '+('validates.' if ok else 'fails its v7 schema.'),path=a.rel,evidence=None if ok else errs[:25]))
    if not v7:
        fs.append(_f('K03-V7-000','SKIP','No v7 meta-artifact was discovered.'));return _result('K03',fs,started=s)
    # Manifest registry references and namespace agreement.
    # Draft.2 semantic identity namespace checks.
    for a in ctx.inv.get('kristall_property_registry'):
        bad=[x.get('property_id') for x in a.data.get('properties',[]) if not str(x.get('property_id','')).startswith('KP')]
        if bad:fs.append(_f('K03-KP-004','FAIL','Property registry contains identifiers outside KP namespace.',path=a.rel,evidence=bad))
    for a in ctx.inv.get('kristall_source_registry'):
        bad=[x.get('source_id') for x in a.data.get('sources',[]) if not str(x.get('source_id','')).startswith('KS')]
        if bad:fs.append(_f('K03-KS-005','FAIL','Source registry contains identifiers outside KS namespace.',path=a.rel,evidence=bad))
    for m in ctx.inv.manifests:
        base=m.path.parent; ns=m.data.get('namespace_id')
        refs=m.data.get('registries') or {}
        for name,ref in refs.items():
            p=(base/ref).resolve()
            if not p.is_file():fs.append(_f('K03-REF-002','FAIL',f'Manifest registry reference {name} is missing.',path=m.rel,observed=ref,remediation='Restore the referenced registry or update the manifest.'));continue
            try:d=read_json(p)
            except Exception as e:fs.append(_f('K03-REF-002','FAIL',f'Manifest registry reference {name} is unreadable.',path=m.rel,evidence=str(e)));continue
            if d.get('namespace_id') is not None and d.get('namespace_id')!=ns:
                fs.append(_f('K03-NS-003','FAIL','Registry namespace_id differs from manifest namespace_id.',path=relpath(p,ctx.scan_root),expected=ns,observed=d.get('namespace_id')))
            else:fs.append(_f('K03-REF-002','PASS',f'Manifest registry reference {name} resolves.',path=relpath(p,ctx.scan_root)))
    return _result('K03',fs,metadata={'v7_artifact_count':len(v7)},started=s)

def k04(ctx):
    s=utc_now(); fs=[]
    vec=ctx.resource_root/'jcs'/'vectors.json'
    data=read_json(vec);fails=[]
    for v in data.get('vectors',[]):
        try:canon,hx,_=digest(v['input'],v.get('content_boundary',{}).get('exclude_json_pointers',[]))
        except Exception as e:fails.append((v['id'],str(e)));continue
        if canon!=v['expected_canonical'] or hx!=v['expected_sha256_hex']:fails.append((v['id'],{'canonical':canon,'hash':hx}))
    if fails:fs.append(_f('K04-JCS-001','FAIL','RFC8785/JCS golden vectors failed.',evidence=fails,impact='Semantic identities may drift across implementations.'))
    else:fs.append(_f('K04-JCS-001','PASS',f'All {len(data.get("vectors",[]))} RFC8785/JCS golden vectors pass.'))
    # Declared v7 canonicalization profile
    for m in ctx.inv.manifests:
        observed=m.data.get('canonicalization_profile')
        fs.append(_f('K04-PROFILE-002','PASS' if observed in {None,'kristal.v7:jcs-rfc8785'} else 'FAIL','Kristall canonicalization profile is compatible with draft2.',path=m.rel,observed=observed,expected='kristal.v7:jcs-rfc8785'))
    return _result('K04',fs,started=s)

def _ids(inv,typ,field,list_field):
    out=set()
    for a in inv.get(typ):
        for x in a.data.get(list_field,[]):
            if isinstance(x,dict) and x.get(field):out.add(x[field])
    return out

def k05(ctx):
    s=utc_now();fs=[]
    assertions=_ids(ctx.inv,'kristall_assertion_registry','assertion_id','assertions')
    family_arts=ctx.inv.get('kristall_assertion_family_registry')
    if not family_arts and not assertions:
        fs.append(_f('K05-FAMILY-000','SKIP','No assertion registries/families discovered.'));return _result('K05',fs,started=s)
    bad_ids=[x for x in assertions if not str(x).startswith('KA')]
    fs.append(_f('K05-KA-001','FAIL' if bad_ids else 'PASS','Global assertion identifiers use KA namespace.',evidence=bad_ids or None))
    for a in family_arts:
        for fam in a.data.get('families',[]):
            members=fam.get('members',[]); gids={m.get('global_assertion_id') for m in members if isinstance(m,dict)}
            missing=sorted(x for x in gids if x and x not in assertions)
            if missing:fs.append(_f('K05-MEMBER-002','FAIL','Assertion family references unknown global assertions.',path=a.rel,evidence={'family_id':fam.get('family_id'),'missing':missing}))
            rep=fam.get('representative') or {}; rg=rep.get('global_assertion_id')
            if rg and rg not in gids:fs.append(_f('K05-REP-003','FAIL','Family representative is not one of its members.',path=a.rel,evidence=fam.get('family_id')))
    if not any(f.verdict=='FAIL' for f in fs):fs.append(_f('K05-FAMILY-004','PASS','Assertion families preserve explicit membership/representative structure.'))
    return _result('K05',fs,started=s)

def k06(ctx):
    s=utc_now();fs=[]; meshes=ctx.inv.get('kristall_mesh')
    if not meshes:fs.append(_f('K06-MESH-000','SKIP','No Kristall Mesh discovered.'));return _result('K06',fs,started=s)
    ent=_ids(ctx.inv,'kristall_entity_registry','entity_id','entities');axes=_ids(ctx.inv,'kristall_axis_registry','axis_id','axes');props=_ids(ctx.inv,'kristall_property_registry','property_id','properties');ass=_ids(ctx.inv,'kristall_assertion_registry','assertion_id','assertions')
    subjects=set();sources=set();families=set()
    for m in ctx.inv.manifests:
        subjects.update(x.get('subject_id') for x in m.data.get('subjects',[]) if isinstance(x,dict));sources.update(x.get('source_id') for x in m.data.get('sources',[]) if isinstance(x,dict))
    for a in ctx.inv.get('kristall_assertion_family_registry'):families.update(x.get('family_id') for x in a.data.get('families',[]) if isinstance(x,dict))
    ids={'entity':ent,'axis':axes,'assertion':ass,'subject':subjects,'source_kristal':sources,'assertion_family':families}
    for a in meshes:
        seen=set()
        for e in a.data.get('edges',[]):
            eid=e.get('edge_id')
            if eid in seen:fs.append(_f('K06-EDGE-001','FAIL','Duplicate Mesh edge_id.',path=a.rel,observed=eid))
            seen.add(eid)
            rel=e.get('relation')
            if rel and not str(rel).startswith('KP'):fs.append(_f('K06-KP-002','FAIL','Mesh relation is not a KP semantic identity.',path=a.rel,observed=rel))
            elif rel and props and rel not in props:fs.append(_f('K06-KP-002','PASS','Mesh relation uses a valid KP identity outside the local property registry; local registries may be partial.',path=a.rel,observed=rel))
            for side in ('from','to'):
                ref=e.get(side) or {};kind=ref.get('kind');rid=ref.get('id')
                if kind in ids and ids[kind] and rid not in ids[kind]:fs.append(_f('K06-ENDPOINT-003','FAIL',f'Mesh {side} endpoint is unresolved.',path=a.rel,evidence={'kind':kind,'id':rid,'edge_id':eid}))
            if e.get('edge_semantics')=='path' and e.get('status')=='accepted':
                fs.append(_f('K06-PATH-004','WARN','Accepted path edge requires careful consumer semantics; PATH must not become ASSERTION.',path=a.rel,evidence=eid,standard_ref='Kristal v7: PATH ≠ ASSERTION'))
    if not any(f.verdict=='FAIL' for f in fs):fs.append(_f('K06-MESH-005','PASS','Mesh edges are referentially consistent with discovered registries.'))
    return _result('K06',fs,started=s)

def k07(ctx):
    s=utc_now();fs=[]; axis_arts=ctx.inv.get('kristall_axis_registry')
    if not axis_arts:fs.append(_f('K07-AXIS-000','SKIP','No axis registry discovered.'));return _result('K07',fs,started=s)
    subjects=set();max_axes=[]
    for m in ctx.inv.manifests:
        subjects.update(x.get('subject_id') for x in m.data.get('subjects',[]) if isinstance(x,dict));max_axes.append((m.data.get('policies') or {}).get('max_orientation_axes'))
    axes=[]
    for a in axis_arts:
        for x in a.data.get('axes',[]):
            axes.append(x); aid=x.get('axis_id')
            if not str(aid).startswith('KQ'):fs.append(_f('K07-KQ-001','FAIL','Axis identifier must be in KQ semantic identity namespace.',path=a.rel,observed=aid))
            sid=((x.get('scope') or {}).get('subject_id'))
            if sid and subjects and sid not in subjects:fs.append(_f('K07-SUBJECT-002','FAIL','Axis scope references unknown subject.',path=a.rel,observed=sid))
    if any(x not in (None,2) for x in max_axes):fs.append(_f('K07-POLICY-003','WARN','Manifest max_orientation_axes differs from v7 projection contract ceiling of two.',evidence=max_axes))
    if not any(f.verdict=='FAIL' for f in fs):fs.append(_f('K07-AXIS-004','PASS',f'{len(axes)} axis definition(s) are structurally consistent.'))
    return _result('K07',fs,started=s)

def k08(ctx):
    s=utc_now();fs=[];recipes=ctx.inv.get('kristall_projection_recipe')
    if not recipes:fs.append(_f('K08-RECIPE-000','SKIP','No projection recipe discovered.'));return _result('K08',fs,started=s)
    axes=_ids(ctx.inv,'kristall_axis_registry','axis_id','axes');subjects=set()
    for m in ctx.inv.manifests:subjects.update(x.get('subject_id') for x in m.data.get('subjects',[]) if isinstance(x,dict))
    for a in recipes:
        d=a.data;ori=d.get('orientation') or {};used=[ori.get('primary_axis'),ori.get('secondary_axis')];used=[x for x in used if x]
        if not ori.get('primary_axis'):fs.append(_f('K08-ORIENT-001','FAIL','Projection recipe has no primary axis.',path=a.rel))
        if len(used)>2:fs.append(_f('K08-ORIENT-002','FAIL','Projection recipe uses more than two orientation axes.',path=a.rel,evidence=used))
        missing=[x for x in used if axes and x not in axes]
        if missing:fs.append(_f('K08-ORIENT-003','FAIL','Projection recipe references unknown axis.',path=a.rel,evidence=missing))
        sid=(d.get('subject') or {}).get('subject_id')
        if sid and subjects and sid not in subjects:fs.append(_f('K08-SUBJECT-004','FAIL','Projection recipe references unknown subject.',path=a.rel,observed=sid))
        out=d.get('output') or {}
        expected={'artifact_type':'kristal_state','schema_version':'6.0','profile':'v6_compatible'}
        if out!=expected:fs.append(_f('K08-OUTPUT-005','FAIL','Projection output contract is not v6-compatible.',path=a.rel,expected=expected,observed=out))
    if not any(f.verdict=='FAIL' for f in fs):fs.append(_f('K08-SURFACE-006','PASS','Projection recipes are ready to select subject-oriented Surfaces.'))
    return _result('K08',fs,started=s)

def k09(ctx):
    s=utc_now();fs=[];projs=[]
    for a in ctx.inv.get('kristal_state'):
        ext=(a.data.get('extensions') or {}).get('kristal_v7')
        if ext is not None:projs.append((a,ext))
    if not projs:
        verdict='PARTIAL' if ctx.claimed_profile in {'V7-Projection','V7-Kristall'} else 'SKIP'
        fs.append(_f('K09-PROJECTION-000',verdict,'No materialized v6-compatible v7 projection discovered.',impact='Projection materialization cannot be evidenced from the target alone.'))
        return _result('K09',fs,started=s)
    source_states=set()
    for m in ctx.inv.manifests:source_states.update(x.get('state_id') for x in m.data.get('sources',[]) if isinstance(x,dict) and x.get('state_id'))
    for a,ext in projs:
        ok,errs=ctx.schemas.validate_extension(ext)
        fs.append(_f('K09-EXT-001','PASS' if ok else 'FAIL','extensions.kristal_v7 '+('validates.' if ok else 'fails schema.'),path=a.rel,evidence=None if ok else errs))
        refs=((ext.get('generated_from') or {}).get('source_state_refs') or [])
        missing=[x for x in refs if source_states and x not in source_states]
        if missing:fs.append(_f('K09-LINEAGE-002','FAIL','Projection lineage references source states absent from the Kristall manifest.',path=a.rel,evidence=missing))
        elif refs:fs.append(_f('K09-LINEAGE-002','PASS','Projection lineage resolves to declared source states.',path=a.rel))
    return _result('K09',fs,started=s)

def k10(ctx):
    s=utc_now();fs=[];arts=ctx.inv.get('semantic_resonance_set')
    if not arts:fs.append(_f('K10-RESONANCE-000','SKIP','No semantic resonance set discovered.'));return _result('K10',fs,started=s)
    res_ids=set()
    for a in arts:
        for o in a.data.get('observations',[]):
            rid=o.get('resonance_id');res_ids.add(rid)
            agg=o.get('aggregate') or {}
            if agg and agg.get('non_authoritative') is not True:fs.append(_f('K10-AUTH-001','FAIL','Resonance aggregate must remain explicitly non-authoritative.',path=a.rel,evidence=rid,standard_ref='Kristal v7 semantic resonance contract'))
            for dim in o.get('dimensions',[]):
                for key in ('value','confidence'):
                    if key in dim and not (0<=dim[key]<=1):fs.append(_f('K10-BOUND-002','FAIL',f'Resonance {key} is outside [0,1].',path=a.rel,evidence={'resonance_id':rid,key:dim[key]}))
    for mesh in ctx.inv.get('kristall_mesh'):
        for e in mesh.data.get('edges',[]):
            missing=[r for r in e.get('resonance_refs',[]) if r not in res_ids]
            if missing:fs.append(_f('K10-REF-003','FAIL','Mesh edge references unknown resonance observations.',path=mesh.rel,evidence={'edge_id':e.get('edge_id'),'missing':missing}))
    if not any(f.verdict=='FAIL' for f in fs):fs.append(_f('K10-RESONANCE-004','PASS','Resonance remains bounded and non-authoritative.'))
    return _result('K10',fs,started=s)

def k11(ctx):
    s=utc_now();fs=[];driver=ctx.driver
    if ctx.interop_evidence and ctx.interop_evidence.is_file():
        try:
            ev=read_json(ctx.interop_evidence)
            if ev.get('schema')=='kristaldiag.interop-evidence.v1' and ev.get('verdict')=='PASS':
                fs.append(_f('K11-INTEROP-EXT-000','PASS','Independent A -> B -> A interoperability evidence passed.',path=str(ctx.interop_evidence),evidence={'producer':ev.get('producer'),'consumer':ev.get('consumer'),'artifact':ev.get('artifact')}))
                return _result('K11',fs,started=s)
            fs.append(_f('K11-INTEROP-EXT-000','FAIL','Supplied interoperability evidence is not a passing KristalDiag interop record.',path=str(ctx.interop_evidence),evidence=ev))
            return _result('K11',fs,started=s)
        except Exception as e:
            fs.append(_f('K11-INTEROP-EXT-000','ERROR','Could not read supplied interoperability evidence.',path=str(ctx.interop_evidence),evidence=str(e)));return _result('K11',fs,started=s)
    if not driver:
        fs.append(_f('K11-INTEROP-000','PARTIAL','No kristaldiag-driver.json is present; external implementation interoperability was not executed.',remediation='Provide a conformance driver or run cross-implementation fixtures manually.'))
        return _result('K11',fs,started=s)
    if not ctx.allow_exec:
        fs.append(_f('K11-INTEROP-001','BLOCKED','Driver exists but target execution is disabled.',remediation='Re-run with --allow-exec only when the target implementation is trusted.'))
        return _result('K11',fs,started=s)
    actions=['self_test']
    for act in actions:
        try:r=run_action(ctx.scan_root,driver,act)
        except Exception as e:fs.append(_f('K11-DRIVER-002','ERROR',f'Driver action {act} failed to execute.',evidence=str(e)));continue
        if r is None:fs.append(_f('K11-DRIVER-003','PARTIAL',f'Driver does not declare action {act}.'));continue
        fs.append(_f('K11-DRIVER-004','PASS' if r['returncode']==0 else 'FAIL',f'Driver action {act} '+('passed.' if r['returncode']==0 else 'failed.'),evidence={'returncode':r['returncode'],'stderr':r['stderr'][-2000:]}))
    return _result('K11',fs,started=s)

def k12(ctx):
    s=utc_now();fs=[]
    # Discovery determinism and canonical determinism across a second pass.
    from .discovery import discover
    inv2=discover(ctx.target)
    a=[(x.rel,x.artifact_type,x.schema_version) for x in ctx.inv.artifacts];b=[(x.rel,x.artifact_type,x.schema_version) for x in inv2.artifacts]
    fs.append(_f('K12-DISCOVERY-001','PASS' if a==b else 'FAIL','Artifact discovery is deterministic across repeated scans.',evidence=None if a==b else {'first':a[:50],'second':b[:50]}))
    samples=[x.data for x in ctx.inv.artifacts[:50]]
    bad=[]
    for i,x in enumerate(samples):
        try:
            c1=canonicalize(x);c2=canonicalize(copy.deepcopy(x))
            if c1!=c2:bad.append(i)
        except Exception as e:bad.append((i,str(e)))
    fs.append(_f('K12-JCS-002','PASS' if not bad else 'FAIL','Canonicalization is deterministic on sampled target artifacts.',evidence=bad or None))
    return _result('K12',fs,started=s)

def k13(ctx):
    s=utc_now();fs=[]
    # Internal adversarial TCK: mutate required fields in one positive fixture per schema.
    pairs={
      'kristall-manifest.example.json':'kristall_manifest','entity-registry.example.json':'kristall_entity_registry','property-registry.example.json':'kristall_property_registry',
      'assertion-registry.example.json':'kristall_assertion_registry','source-registry.example.json':'kristall_source_registry','assertion-family-registry.example.json':'kristall_assertion_family_registry',
      'mesh.example.json':'kristall_mesh','axis-registry.example.json':'kristall_axis_registry','projection-recipe.example.json':'kristall_projection_recipe','crystallization-record.example.json':'kristall_crystallization_record','resonance.example.json':'semantic_resonance_set'}
    failures=[]
    for fn,typ in pairs.items():
        p=ctx.resource_root/'v7'/fn
        if not p.is_file():failures.append((fn,'missing fixture'));continue
        d=read_json(p);ok,_=ctx.schemas.validate_v7(d)
        if not ok:failures.append((fn,'positive fixture rejected'));continue
        mut=copy.deepcopy(d); mut.pop('artifact_type',None)
        bad,_=ctx.schemas.validate_v7(mut)
        if bad:failures.append((fn,'missing artifact_type unexpectedly accepted'))
    # Projection extension negative
    p=ctx.resource_root/'v7'/'v6-compatible-projection.example.json'
    if p.is_file():
        d=read_json(p);ext=copy.deepcopy((d.get('extensions') or {}).get('kristal_v7') or {});ext.pop('orientation',None)
        bad,_=ctx.schemas.validate_extension(ext)
        if bad:failures.append(('kristal-v7-extension','missing orientation accepted'))
    fs.append(_f('K13-NEGATIVE-001','PASS' if not failures else 'FAIL','Negative/adversarial schema corpus '+('rejects invalid mutations.' if not failures else 'has unexpected acceptances.'),evidence=failures or None))
    return _result('K13',fs,started=s)

CHECKS={f'K{i:02d}':globals()[f'k{i:02d}'] for i in range(14)}
