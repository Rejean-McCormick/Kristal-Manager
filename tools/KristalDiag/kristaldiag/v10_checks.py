from __future__ import annotations

import copy
import json
import re
import tempfile
from pathlib import Path
from typing import Any

from .models import Finding, LevelResult
from .schemas import V10_SCHEMAS
from .utils import read_json, sha256_file, utc_now
from .verdicts import combine
from .v9 import is_mutable_selector, state_commitment, verify_declared_state
from .v10 import (
    find_publication_bundles, publication_identity, sha256_bytes, verify_publication_bundle,
    verify_github_read_surface, verify_github_sync_manifest, verify_github_collection_index,
    verify_hosted_github_read_surface, verify_hosted_github_collection,
    GITHUB_READ_SURFACE_FORMAT, GITHUB_SYNC_MANIFEST_FORMAT, GITHUB_COLLECTION_INDEX_FORMAT,
)

LEVEL_NAMES = {
    'K25': 'V10 Machine Contracts & Capabilities',
    'K26': 'V10 Node / Binding Relations',
    'K27': 'V10 Publication Bundle Integrity',
    'K28': 'V10 Directory & Discovery Semantics',
    'K29': 'V10 GitHub Host Profile',
    'K30': 'V10 Semantic / Hosting Separation',
    'K31': 'V10 Negative & Adversarial Corpus',
    'K32': 'V10 Standard / Contract-Set Alignment',
}

V10_PROFILES = {'V10-Node-Reader', 'V10-Publisher', 'V10-Directory', 'V10-GitHub-Host', 'V10-Full'}
PUBLISHER_PROFILES = {'V10-Publisher', 'V10-Full'}
DIRECTORY_PROFILES = {'V10-Directory', 'V10-Full'}
GITHUB_PROFILES = {'V10-GitHub-Host'}
DIGEST_RE = re.compile(r'^sha256:[0-9a-f]{64}$')
CREDENTIAL_KEY = re.compile(r'(token|password|passwd|secret|private[_-]?key|api[_-]?key|credential)', re.I)


def _f(fid: str, verdict: str, message: str, **kw) -> Finding:
    return Finding(fid, verdict, kw.pop('category', 'v10'), message, **kw)


def _result(level: str, findings: list[Finding], metadata: dict[str, Any] | None = None, started: str | None = None) -> LevelResult:
    verdict = combine([x.verdict for x in findings]) if findings else 'SKIP'
    return LevelResult(level, LEVEL_NAMES[level], verdict, findings, [], started or utc_now(), utc_now(), 0.0, metadata or {})


def _v10_artifacts(ctx):
    out = []
    for typ in V10_SCHEMAS:
        out.extend(ctx.inv.get(typ))
    return out


def _by_rel(ctx):
    return {a.rel.replace('\\', '/'): a for a in ctx.inv.artifacts}


def _state_ref_exact(value: dict[str, Any] | None) -> bool:
    if not isinstance(value, dict) or not isinstance(value.get('state_ref'), str):
        return False
    c = value.get('logical_commitment')
    return isinstance(c, dict) and isinstance(c.get('profile'), str) and bool(c.get('profile')) and bool(DIGEST_RE.fullmatch(str(c.get('digest', '')))) and not is_mutable_selector(value['state_ref'])


def _credential_paths(value: Any, prefix: str = '$') -> list[str]:
    out: list[str] = []
    if isinstance(value, dict):
        for k, v in value.items():
            p = f'{prefix}.{k}'
            if CREDENTIAL_KEY.search(str(k)):
                out.append(p)
            out.extend(_credential_paths(v, p))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            out.extend(_credential_paths(v, f'{prefix}[{i}]'))
    return out


def k25(ctx):
    s = utc_now(); fs = []; arts = _v10_artifacts(ctx)
    if not arts:
        verdict = 'BLOCKED' if ctx.claimed_profile in V10_PROFILES else 'SKIP'
        fs.append(_f('K25-V10-000', verdict, 'No Kristal v10 machine artifact was discovered in the target.'))
        return _result('K25', fs, started=s)
    failures = []; counts: dict[str, int] = {}
    for a in arts:
        counts[a.artifact_type] = counts.get(a.artifact_type, 0) + 1
        ok, errs = ctx.schemas.validate_v10(a.data)
        if not ok:
            failures.append({'path': a.rel, 'artifact_type': a.artifact_type, 'errors': errs[:30]})
        if a.artifact_type == 'kristal_host_binding' and (a.data.get('profile') or {}).get('id') == 'kristal.host/github':
            ok2, errs2 = ctx.schemas.validate_github_binding(a.data)
            if not ok2:
                failures.append({'path': a.rel, 'artifact_type': 'kristal.host/github/1.0', 'errors': errs2[:30]})
    fs.append(_f('K25-SCHEMA-001', 'FAIL' if failures else 'PASS',
                 'V10 machine artifacts validate against the frozen examiner contracts.' if not failures else 'One or more v10 artifacts fail their machine contracts.',
                 evidence=failures or counts, standard_ref='Kristal v10 machine contracts'))
    required_reads = {'kristal_state/6.0','kristall/7.0','kristall/8.0','kristal.state/9.0','kristal.hosting/10.0'}
    caps_fail = []
    for a in ctx.inv.get('kristal_v10_capabilities'):
        comp = a.data.get('compatibility') if isinstance(a.data.get('compatibility'), dict) else {}
        reads = set(comp.get('reads') or [])
        missing = sorted(required_reads - reads)
        if missing or comp.get('semantic_state_baseline') != 'kristal.state/9.0' or comp.get('hosted_network_baseline') != 'kristal.hosting/10.0':
            caps_fail.append({'path':a.rel,'missing_reads':missing,'compatibility':comp})
    if ctx.inv.get('kristal_v10_capabilities'):
        fs.append(_f('K25-CAP-002','FAIL' if caps_fail else 'PASS','V10 capabilities preserve the inherited semantic/query baselines.' if not caps_fail else 'V10 capabilities misstate inherited compatibility.',evidence=caps_fail or {'descriptors':len(ctx.inv.get('kristal_v10_capabilities'))}))
    return _result('K25', fs, {'counts': counts}, s)


def k26(ctx):
    s=utc_now();fs=[];nodes=ctx.inv.get('kristal_node_manifest');bindings=ctx.inv.get('kristal_host_binding')
    if not nodes:
        fs.append(_f('K26-NODE-000','BLOCKED' if ctx.claimed_profile in V10_PROFILES else 'SKIP','No v10 node manifest discovered.'))
        return _result('K26',fs,started=s)
    failures=[];seen_nodes=set();binding_map={}
    for b in bindings:
        bid=b.data.get('binding_id');nid=b.data.get('node_id')
        if isinstance(bid,str) and isinstance(nid,str): binding_map.setdefault((nid,bid),[]).append(b)
    relmap=_by_rel(ctx)
    for a in nodes:
        d=a.data;nid=d.get('node_id')
        if nid in seen_nodes:failures.append({'path':a.rel,'reason':'duplicate_node_id','node_id':nid})
        seen_nodes.add(nid)
        if 'kristal.state/9.0' not in (d.get('semantic_state_contracts') or []):
            failures.append({'path':a.rel,'reason':'missing_v9_semantic_state_contract'})
        ids=set()
        for i,ref in enumerate(d.get('bindings') or []):
            bid=ref.get('binding_id') if isinstance(ref,dict) else None
            if bid in ids:failures.append({'path':a.rel,'field':f'bindings[{i}]','reason':'duplicate_binding_id','binding_id':bid})
            ids.add(bid)
            matches=binding_map.get((nid,bid),[])
            desc=ref.get('descriptor') if isinstance(ref,dict) else None
            if isinstance(desc,str) and not (desc.startswith(('github://','http://','https://','file://','oci://'))):
                normalized=desc.replace('\\','/'); normalized=normalized[2:] if normalized.startswith('./') else normalized
                candidate=relmap.get(normalized)
                if candidate is None:
                    failures.append({'path':a.rel,'field':f'bindings[{i}].descriptor','reason':'local_descriptor_missing','descriptor':desc})
                elif candidate.artifact_type!='kristal_host_binding' or candidate.data.get('node_id')!=nid or candidate.data.get('binding_id')!=bid:
                    failures.append({'path':a.rel,'field':f'bindings[{i}]','reason':'local_descriptor_relation_mismatch','descriptor':desc})
            elif not matches and bindings:
                failures.append({'path':a.rel,'field':f'bindings[{i}]','reason':'declared_binding_not_observed','binding_id':bid})
    for (nid,bid),rows in binding_map.items():
        if len(rows)>1:failures.append({'reason':'duplicate_binding_identity','node_id':nid,'binding_id':bid,'paths':[x.rel for x in rows]})
    fs.append(_f('K26-REL-001','FAIL' if failures else 'PASS','Node/binding identities and local descriptors are relationally coherent.' if not failures else 'Node/binding relation failures were found.',evidence=failures or {'nodes':len(nodes),'bindings':len(bindings)},standard_ref='Kristal v10 Nodes and Host Bindings'))
    return _result('K26',fs,started=s)


def k27(ctx):
    s=utc_now();fs=[];pubs=ctx.inv.get('kristal_publication');bundles=find_publication_bundles(ctx.scan_root)
    if not pubs and not bundles:
        fs.append(_f('K27-PUB-000','BLOCKED' if ctx.claimed_profile in PUBLISHER_PROFILES else 'SKIP','No v10 Publication Record or local publication bundle was discovered.'))
        return _result('K27',fs,started=s)
    relation_fail=[]
    states={a.data.get('state_ref'):a for a in ctx.inv.get('kristal_state_snapshot') if isinstance(a.data.get('state_ref'),str)}
    for p in pubs:
        d=p.data;st=d.get('state') if isinstance(d.get('state'),dict) else {}
        if not _state_ref_exact(st):relation_fail.append({'path':p.rel,'reason':'publication_state_not_exact'})
        local=states.get(st.get('state_ref'))
        if local:
            ok,actual,errs=verify_declared_state(local.data)
            if not ok or st.get('logical_commitment')!=actual:
                relation_fail.append({'path':p.rel,'reason':'publication_local_state_mismatch','state_path':local.rel,'errors':errs,'actual':actual})
        for i,r in enumerate(d.get('resources') or []):
            if not isinstance(r,dict) or not DIGEST_RE.fullmatch(str(r.get('blob_digest',''))) or not isinstance(r.get('size'),int) or r.get('size')<0:
                relation_fail.append({'path':p.rel,'field':f'resources[{i}]','reason':'resource_not_byte_verifiable'})
    fs.append(_f('K27-RECORD-001','FAIL' if relation_fail else 'PASS','Publication Records bind exact state commitments and byte-verifiable resources.' if not relation_fail else 'Publication Record binding failures were found.',evidence=relation_fail or {'publication_records':len(pubs)}))
    bundle_fail=[];verified=[]
    for b in bundles:
        r=verify_publication_bundle(b)
        if not r['ok']:bundle_fail.append({'bundle':str(b.relative_to(ctx.scan_root)) if b.is_relative_to(ctx.scan_root) else str(b),'issues':r['issues'][:50]})
        else:verified.append({'bundle':str(b.relative_to(ctx.scan_root)) if b.is_relative_to(ctx.scan_root) else str(b),'publication_id':r.get('publication_id'),'manifest_digest':r.get('bundle_manifest_digest')})
    if bundles:
        fs.append(_f('K27-BUNDLE-002','FAIL' if bundle_fail else 'PASS','Independent Python verification accepts all local v10 publication bundles.' if not bundle_fail else 'At least one local publication bundle fails independent byte verification.',evidence=bundle_fail or verified,standard_ref='Kristal v10 Publication and Discovery'))
    elif pubs:
        fs.append(_f('K27-BUNDLE-002','PARTIAL' if ctx.claimed_profile in PUBLISHER_PROFILES else 'SKIP','Publication Records are present but no local/retrieved bundle bytes are available for independent retry/idempotence verification.',remediation='Provide downloaded Release bundle bytes containing publication.json, bundle-manifest.json and state-snapshot.json.'))
    return _result('K27',fs,started=s)


def k28(ctx):
    s=utc_now();fs=[];dirs=ctx.inv.get('kristal_directory')
    if not dirs:
        fs.append(_f('K28-DIR-000','BLOCKED' if ctx.claimed_profile in DIRECTORY_PROFILES else 'SKIP','No v10 directory discovered.'))
        return _result('K28',fs,started=s)
    fail=[]
    for a in dirs:
        seen=set()
        entries=a.data.get('entries') or []
        if not isinstance(entries,list):
            fail.append({'path':a.rel,'reason':'entries_not_array'});continue
        for i,e in enumerate(entries):
            if not isinstance(e,dict):fail.append({'path':a.rel,'field':f'entries[{i}]','reason':'entry_not_object'});continue
            nid=e.get('node_id')
            if nid in seen:fail.append({'path':a.rel,'field':f'entries[{i}].node_id','reason':'duplicate_node_id','node_id':nid})
            seen.add(nid)
            for j,st in enumerate(e.get('advertised_states') or []):
                if not _state_ref_exact(st):fail.append({'path':a.rel,'field':f'entries[{i}].advertised_states[{j}]','reason':'state_not_exact'})
            channels=e.get('channels') or {}
            if isinstance(channels,dict):
                for name,st in channels.items():
                    if not _state_ref_exact(st):fail.append({'path':a.rel,'field':f'entries[{i}].channels.{name}','reason':'channel_not_exact'})
    fs.append(_f('K28-DISCOVERY-001','FAIL' if fail else 'PASS','Directories advertise exact states/channels without redefining semantic federation.' if not fail else 'Directory discovery invariants failed.',evidence=fail or {'directories':len(dirs)},standard_ref='Kristal v10 Directories and Federation',impact='Directory data is routing/discovery evidence only; omission is not semantic negation.'))
    return _result('K28',fs,started=s)


def k29(ctx):
    s=utc_now();fs=[]
    github=[a for a in ctx.inv.get('kristal_host_binding') if (a.data.get('profile') or {}).get('id')=='kristal.host/github']
    if not github:
        fs.append(_f('K29-GH-000','BLOCKED' if ctx.claimed_profile in GITHUB_PROFILES else 'SKIP','No kristal.host/github/1.0 binding discovered.'))
        return _result('K29',fs,started=s)
    fail=[];warnings=[]
    for a in github:
        d=a.data;ok,errs=ctx.schemas.validate_github_binding(d)
        if not ok:fail.append({'path':a.rel,'reason':'schema','errors':errs[:30]});continue
        creds=_credential_paths(d)
        if creds:fail.append({'path':a.rel,'reason':'credential_shaped_fields','fields':creds})
        host=d.get('host') or {};scope=host.get('account_scope') or {};owner=scope.get('owner')
        resource=d.get('resource') or {};locator=resource.get('locator');pc=d.get('profile_configuration') or {};repo=pc.get('repository')
        if owner and repo and locator!=f'github://{owner}/{repo}':
            fail.append({'path':a.rel,'reason':'resource_locator_mismatch','expected':f'github://{owner}/{repo}','observed':locator})
        surfaces=d.get('surfaces') or {}
        expected={'source':'git','publication':'github-release','automation':'github-actions','discovery':'repository-file'}
        for name,kind in expected.items():
            got=(surfaces.get(name) or {}).get('kind')
            if got!=kind:fail.append({'path':a.rel,'field':f'surfaces.{name}.kind','reason':'profile_surface_mismatch','expected':kind,'observed':got})
        if 'materialization' not in surfaces:warnings.append({'path':a.rel,'surface':'materialization','reason':'not_advertised'})
        if 'attestation' not in surfaces:warnings.append({'path':a.rel,'surface':'attestation','reason':'not_advertised'})
    fs.append(_f('K29-PROFILE-001','FAIL' if fail else 'PASS','GitHub host bindings satisfy the reference profile without embedded reusable credentials.' if not fail else 'GitHub host-profile violations were found.',evidence=fail or {'bindings':len(github)},standard_ref='kristal.host/github/1.0'))
    if warnings:fs.append(_f('K29-CAP-002','WARN','Some optional GitHub surfaces are not advertised; this is capability absence, not semantic nonconformance.',evidence=warnings))
    else:fs.append(_f('K29-CAP-002','PASS','Observed GitHub bindings advertise the optional materialization/attestation surfaces they use.'))

    # Draft.3: independently validate the operational AI/read surfaces when present.
    # These documents are derived hosting/navigation evidence, never semantic authority.
    read_fail=[];read_counts={'read_surface_documents':0,'sync_manifests':0,'collection_indexes':0,'hosted_surfaces':0}
    for a in ctx.inv.artifacts:
        fmt=a.data.get('format')
        if fmt==GITHUB_READ_SURFACE_FORMAT:
            read_counts['read_surface_documents']+=1
            ok,errs=ctx.schemas.validate_github_read_surface(a.data);r=verify_github_read_surface(a.data)
            if not ok or not r.get('ok'):read_fail.append({'path':a.rel,'kind':'read_surface','schema_errors':errs[:30],'issues':r.get('issues',[])[:50]})
        elif fmt==GITHUB_SYNC_MANIFEST_FORMAT:
            read_counts['sync_manifests']+=1
            ok,errs=ctx.schemas.validate_github_sync_manifest(a.data);r=verify_github_sync_manifest(a.data)
            if not ok or not r.get('ok'):read_fail.append({'path':a.rel,'kind':'sync_manifest','schema_errors':errs[:30],'issues':r.get('issues',[])[:50]})
        elif fmt==GITHUB_COLLECTION_INDEX_FORMAT:
            read_counts['collection_indexes']+=1
            ok,errs=ctx.schemas.validate_github_collection_index(a.data);r=verify_github_collection_index(a.data)
            if not ok or not r.get('ok'):read_fail.append({'path':a.rel,'kind':'collection_index','schema_errors':errs[:30],'issues':r.get('issues',[])[:50]})

    root=ctx.scan_root if ctx.scan_root.is_dir() else ctx.scan_root.parent
    index_file=root/'kristals'/'index.json'
    if index_file.is_file():
        result=verify_hosted_github_collection(root,jobs=8)
        read_counts['hosted_surfaces']=result.get('verified_surfaces',0)
        if not result.get('ok'):read_fail.append({'path':'kristals/index.json','kind':'hosted_collection','issues':result.get('issues',[])[:200]})
    else:
        roots=[]
        kristals=root/'kristals'
        if kristals.is_dir():
            for child in sorted((x for x in kristals.iterdir() if x.is_dir()),key=lambda x:x.name.encode('utf-8')):
                if (child/'.kristal'/'sync-manifest.json').is_file():roots.append(child)
        if roots:
            from concurrent.futures import ThreadPoolExecutor
            workers=min(8,len(roots))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futs=[(x,pool.submit(verify_hosted_github_read_surface,root,f'kristals/{x.name}')) for x in roots]
                for child,fut in futs:
                    result=fut.result();read_counts['hosted_surfaces']+=1
                    if not result.get('ok'):read_fail.append({'path':f'kristals/{child.name}','kind':'hosted_read_surface','issues':result.get('issues',[])[:100]})
    observed=sum(read_counts.values())
    if observed:
        fs.append(_f('K29-READ-003','FAIL' if read_fail else 'PASS','GitHub draft.3.1 read surfaces, sync manifests and collection navigation are independently byte/digest verified.' if not read_fail else 'GitHub AI/read-surface integrity failures were found.',evidence=read_fail or read_counts,standard_ref='Kristal v10 GitHub Reference Profile draft.3.1',impact='The collection index and AI/read surface are derived discovery surfaces; failures do not redefine the v9 State Commitment.'))
    else:
        fs.append(_f('K29-READ-003','SKIP','No draft.3.1 GitHub AI/read-surface document or hosted collection subtree was discovered.'))
    return _result('K29',fs,metadata={'read_surface_counts':read_counts},started=s)

def k30(ctx):
    s=utc_now();fs=[];fail=[];checked=0
    states={a.data.get('state_ref'):a for a in ctx.inv.get('kristal_state_snapshot') if isinstance(a.data.get('state_ref'),str)}
    for p in ctx.inv.get('kristal_publication'):
        ref=p.data.get('state') if isinstance(p.data.get('state'),dict) else {}
        local=states.get(ref.get('state_ref'))
        if local:
            checked+=1;ok,actual,errs=verify_declared_state(local.data)
            if not ok or actual!=ref.get('logical_commitment'):
                fail.append({'publication':p.rel,'state':local.rel,'errors':errs,'actual':actual,'declared':ref.get('logical_commitment')})
    # Independent invariant using a frozen v9 state: two distinct host/publication identities
    # can bind the same semantic state without changing its v9 commitment.
    base=Path(__file__).resolve().parent/'resources'/'tck'/'v9'/'vectors'/'state-snapshot.example.json'
    if base.is_file():
        state=read_json(base);before=state_commitment(state)
        exact={'state_ref':state.get('state_ref'),'logical_commitment':before}
        p1=publication_identity(node_id='urn:kristal:node:host-a',binding_id='github-a',state=exact,bundle_manifest_digest='sha256:'+'1'*64)
        p2=publication_identity(node_id='urn:kristal:node:host-b',binding_id='github-b',state=exact,bundle_manifest_digest='sha256:'+'2'*64)
        after=state_commitment(state);checked+=1
        if before!=after:fail.append({'reason':'host_move_changed_v9_commitment','before':before,'after':after})
        if p1==p2:fail.append({'reason':'distinct_publication_contexts_collapsed','publication_id':p1})
    fs.append(_f('K30-SEPARATION-001','FAIL' if fail else 'PASS','V10 hosting/publication metadata remains outside independently recomputed v9 semantic commitments.' if not fail else 'Hosting/semantic separation failed.',evidence=fail or {'checks':checked},standard_ref='Kristal v10 core rule: SEMANTIC STATE != HOSTING != PUBLICATION LOCATION != DISCOVERY DIRECTORY != READ SURFACE'))
    return _result('K30',fs,started=s)


def k31(ctx):
    s=utc_now();fs=[];fail=[]
    # Schema negative corpus: ordinary malformed input must fail as data, not crash the examiner.
    try:
        node=read_json(Path(__file__).resolve().parent/'resources'/'tck'/'v10'/'vectors'/'node-manifest.example.json')
        bad=copy.deepcopy(node);bad['roles']=['not-a-role'];bad['bindings']=[None]
        ok,errs=ctx.schemas.validate_v10(bad)
        if ok or not errs:fail.append({'case':'invalid-role-null-binding','reason':'accepted'})
    except Exception as exc:fail.append({'case':'invalid-role-null-binding','reason':'exception','error':str(exc)})
    try:
        pub=read_json(Path(__file__).resolve().parent/'resources'/'tck'/'v10'/'vectors'/'publication.example.json')
        bad=copy.deepcopy(pub);bad['resources']=[{}]
        ok,errs=ctx.schemas.validate_v10(bad)
        if ok or not errs:fail.append({'case':'empty-publication-resource','reason':'accepted'})
    except Exception as exc:fail.append({'case':'empty-publication-resource','reason':'exception','error':str(exc)})
    try:
        directory=read_json(Path(__file__).resolve().parent/'resources'/'tck'/'v10'/'vectors'/'directory.example.json')
        bad=copy.deepcopy(directory);bad['entries']={}
        ok,errs=ctx.schemas.validate_v10(bad)
        if ok or not errs:fail.append({'case':'directory-entries-object','reason':'accepted'})
    except Exception as exc:fail.append({'case':'directory-entries-object','reason':'exception','error':str(exc)})
    # Bundle tamper corpus is generated locally from the built-in reference fixture.
    try:
        fixture=Path(__file__).resolve().parent/'resources'/'tck'/'v10'/'bundle'
        if fixture.is_dir():
            import shutil
            with tempfile.TemporaryDirectory(prefix='kristaldiag-v10-negative-') as td:
                dst=Path(td)/'bundle';shutil.copytree(fixture,dst)
                state=dst/'state-snapshot.json';state.write_bytes(state.read_bytes()+b' ')
                r=verify_publication_bundle(dst)
                if r.get('ok') or not any(x.get('code') in {'DIGEST_MISMATCH','SIZE_MISMATCH','STATE_COMMITMENT_MISMATCH'} for x in r.get('issues',[])):
                    fail.append({'case':'tampered-bundle','reason':'not-detected','result':r})
    except Exception as exc:fail.append({'case':'tampered-bundle','reason':'exception','error':str(exc)})
    # Draft.3 operational surfaces: exact digest and deterministic-order failures must fail closed.
    try:
        surface=read_json(Path(__file__).resolve().parent/'resources'/'tck'/'v10'/'github'/'github-read-surface.example.json')
        bad=copy.deepcopy(surface);bad['surface_digest']='sha256:'+'0'*64
        ok,errs=ctx.schemas.validate_github_read_surface(bad);r=verify_github_read_surface(bad)
        if not ok or r.get('ok') or not any(x.get('code')=='DIGEST_MISMATCH' for x in r.get('issues',[])):
            fail.append({'case':'tampered-read-surface-digest','reason':'not-detected','schema_errors':errs,'result':r})
    except Exception as exc:fail.append({'case':'tampered-read-surface-digest','reason':'exception','error':str(exc)})
    try:
        index=read_json(Path(__file__).resolve().parent/'resources'/'tck'/'v10'/'github'/'github-collection-index.example.json')
        bad=copy.deepcopy(index);bad['index_digest']='sha256:'+'0'*64
        ok,errs=ctx.schemas.validate_github_collection_index(bad);r=verify_github_collection_index(bad)
        if not ok or r.get('ok') or not any(x.get('code')=='DIGEST_MISMATCH' for x in r.get('issues',[])):
            fail.append({'case':'tampered-collection-index-digest','reason':'not-detected','schema_errors':errs,'result':r})
    except Exception as exc:fail.append({'case':'tampered-collection-index-digest','reason':'exception','error':str(exc)})
    fs.append(_f('K31-NEGATIVE-001','FAIL' if fail else 'PASS','Independent v10 negative corpus rejects malformed contracts, tampered publication bytes and draft.3.1 GitHub read-surface digest drift.' if not fail else 'V10 negative/adversarial corpus failures were found.',evidence=fail or {'cases':6},standard_ref='Kristal v10 Conformance draft.3.1'))
    return _result('K31',fs,started=s)

def k32(ctx):
    s=utc_now();fs=[];root=ctx.scan_root
    release=root/'contracts'/'release.json' if root.is_dir() else None
    contract_set=root/'contracts'/'contract-set.json' if root.is_dir() else None
    if not release or not release.is_file() or not contract_set or not contract_set.is_file():
        fs.append(_f('K32-STANDARD-000','SKIP','Target is not a Kristal Standard repository with contracts/release.json and contracts/contract-set.json.'))
        return _result('K32',fs,started=s)
    fail=[]
    try:
        rel=read_json(release);cs=read_json(contract_set)
        if rel.get('version')!='10.0.0-draft.3.1':fail.append({'path':'contracts/release.json','reason':'version','observed':rel.get('version'),'expected':'10.0.0-draft.3.1'})
        v10=rel.get('v10') if isinstance(rel.get('v10'),dict) else {}
        required_profiles={
          'semantic_state_baseline':'kristal.state/9.0',
          'hosted_network_baseline':'kristal.hosting/10.0',
          'reference_host_profile':'kristal.host/github/1.0',
          'github_read_surface_profile':'kristal.github-read-surface/1.0',
          'github_sync_manifest_profile':'kristal.github-sync-manifest/1.0',
          'github_collection_index_profile':'kristal.github-collection-index/1.0',
        }
        mismatch={k:{'expected':v,'observed':v10.get(k)} for k,v in required_profiles.items() if v10.get(k)!=v}
        if mismatch:fail.append({'path':'contracts/release.json','reason':'v10_baseline_mismatch','fields':mismatch})
        if cs.get('version')!='10.0.0-draft.3.1':fail.append({'path':'contracts/contract-set.json','reason':'version','observed':cs.get('version'),'expected':'10.0.0-draft.3.1'})
        required={
          'schemas/v10/kristal-node-manifest.schema.json','schemas/v10/kristal-host-binding.schema.json','schemas/v10/kristal-publication.schema.json','schemas/v10/kristal-directory.schema.json','schemas/v10/kristal-v10-capabilities.schema.json',
          'profiles/github/schemas/kristal-github-binding.schema.json','profiles/github/schemas/kristal-github-read-surface.schema.json','profiles/github/schemas/kristal-github-sync-manifest.schema.json','profiles/github/schemas/kristal-github-collection-index.schema.json'
        }
        listed=set(((cs.get('normative') or {}).get('schemas') or []));missing=sorted(required-listed)
        if missing:fail.append({'path':'contracts/contract-set.json','reason':'missing_v10_schemas','missing':missing})
    except Exception as exc:fail.append({'reason':'exception','error':f'{type(exc).__name__}: {exc}'})
    fs.append(_f('K32-ALIGN-001','FAIL' if fail else 'PASS','Standard release metadata and contract set advertise the v10 draft.3.1 hosted-network/read-surface baseline consistently.' if not fail else 'Standard release/contract-set alignment failures were found.',evidence=fail or {'release':'10.0.0-draft.3.1'}))
    return _result('K32',fs,started=s)


V10_CHECKS={f'K{i:02d}':globals()[f'k{i:02d}'] for i in range(25,33)}
