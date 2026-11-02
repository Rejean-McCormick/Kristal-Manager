"""Complete, conservative metadata coverage audit across local Kristal workspaces.

PRESENT ≠ semantic validity; fields are never invented. No content/canon writes.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import csv,json
from ..core import native_v9_declared_historical

FIELDS = (
    ('format','format','required'),('title','title','required'),
    ('slug','slug','required'),('state_ref','state_ref','required'),
    ('status','status','required'),('profile','profile','recommended'),
    ('authority_ref','authority_ref','optional'),
    ('subject.id','subject.id','recommended'),('subject.label','subject.label','recommended'),
    ('subject.domain','subject.domain','recommended'),
    ('subject.orientation','subject.orientation','recommended'),
    ('native_model.kind','native_model.kind','recommended'),
    ('native_model.description','native_model.description','recommended'),
    ('native_model.canonical_paths','native_model.canonical_paths','recommended'),
    ('semantic_ownership.owns','semantic_ownership.owns','recommended'),
    ('semantic_ownership.does_not_own','semantic_ownership.does_not_own','recommended'),
    ('epistemic_model','epistemic_model','recommended'),
    ('release_policy','release_policy','recommended'),
    ('target','target','recommended'),
    ('portable_ai','portable_ai','optional'),
    ('state_scope','state_scope','optional'),
    ('classification.primary_archetype','classification.primary_archetype','review'),
    ('classification.verification_status','classification.verification_status','review'),
    ('classification.primary_usage','classification.primary_usage','review'),
    ('classification.unesco_thesaurus','classification.unesco_thesaurus','review'),
    ('classification.unesco_thesaurus.microthesauri','classification.unesco_thesaurus.microthesauri','review'),
    ('classification.unesco_thesaurus.verification_status','classification.unesco_thesaurus.verification_status','review'),
    ('semantic_mapping.file','semantic_mapping.file','review'),
    ('semantic_mapping.authority','semantic_mapping.authority','review'),
    ('semantic_mapping.requires_independent_semantic_validation','semantic_mapping.requires_independent_semantic_validation','review'),
)
ARTIFACTS = ('kristal.workspace.json','canon/state.index.json',
             'state/state-snapshot.json','build/v9/state-snapshot.json',
             '.kristal/v9/states/current.state-snapshot.json','.kristal/v9/state-snapshot.json',
             '.kristal/v9/capabilities.json','.kristal/v11/semantic-graph.json',
             'derived/reader-inventory.json','derived/reader-profile.json',
             'AI_START_HERE.md','AI_MANIFEST.json')


def read_key(obj,path):
    value=obj
    for step in path.split('.'):
        if not isinstance(value,dict) or step not in value:return None
        value=value[step]
    return value


def is_present(x):
    return x is not None and x!='' and x!=[] and x!={}


def _short_value(value):
    if isinstance(value,(dict,list)):
        serialized=json.dumps(value,ensure_ascii=False,default=str)
        if len(serialized)<2400:return value
        if isinstance(value,list):return {'kind':'list','count':len(value),'sample':value[:2] if len(str(value[:2]))<250 else []}
        return {'kind':'object','keys':list(value)[:25]}
    return value if not isinstance(value,str) or len(value)<240 else value[:237]+'...'


def _safe_reference(root, rel):
    if not isinstance(rel,str) or not rel or '\x00' in rel:return 'INVALID_REFERENCE'
    p=Path(rel)
    if p.is_absolute() or '..' in p.parts:return 'INVALID_REFERENCE'
    full=(root/p).resolve()
    if not full.is_relative_to(root.resolve()):return 'INVALID_REFERENCE'
    return 'PRESENT' if full.exists() else 'BROKEN_REFERENCE'



# Native V9 state detection (Manager read-only coverage, not cryptographic verification).
_NATIVE_STATE_PATHS = (
    'state/state-snapshot.json',
    'build/v9/state-snapshot.json',
    '.kristal/v9/states/current.state-snapshot.json',
    '.kristal/v9/state-snapshot.json',  # Legacy path; never an implied current attestation.
)


def _observe_native_v9_state(root: Path, expected_ref) -> dict:
    """Check only file identity and V9 snapshot shape; never claim hash proof."""
    import re
    candidates = []
    for rel in _NATIVE_STATE_PATHS:
        path = root / rel
        if not path.exists() and not path.is_symlink():
            continue
        try:
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
                raise ValueError('Non-regular, symlinked or escaping file')
            if path.stat().st_size > 3 * 1024 * 1024:
                raise ValueError('Snapshot metadata exceeds 3 MiB limit')
            obj = json.loads(path.read_text(encoding='utf-8-sig'))
            if not isinstance(obj, dict) or obj.get('schema_version') != '9.0' or obj.get('artifact_type') != 'kristal_state_snapshot':
                raise ValueError('Not a declared V9 state snapshot')
            if not isinstance(expected_ref, str) or not expected_ref or obj.get('state_ref') != expected_ref:
                raise ValueError('Workspace state_ref mismatch')
            if not isinstance(obj.get('members'), list) or not obj['members']:
                raise ValueError('No declared logical members')
            commit = obj.get('logical_commitment')
            if not isinstance(commit, dict) or not re.fullmatch(r'sha256:[0-9a-f]{64}', str(commit.get('digest', ''))):
                raise ValueError('Invalid logical commitment digest syntax')
            candidates.append({'path': rel, 'status': 'OBSERVED', 'state_ref': expected_ref,
                               'digest': commit['digest'], 'commitment_recomputed': False})
        except (OSError, UnicodeError, ValueError) as exc:
            candidates.append({'path': rel, 'status': 'REVIEW', 'problem': str(exc)[:160]})
    valid = [v for v in candidates if v['status'] == 'OBSERVED']
    if any(v['status'] == 'REVIEW' for v in candidates):
        return {'status': 'REVIEW', 'path': None, 'candidates': candidates,
                'detail': 'A state candidate failed structural checks; review before claiming coverage.'}
    if not valid:
        return {'status': 'NOT_FOUND', 'path': None, 'candidates': [],
                'detail': 'No recognized V9 state snapshot path; review the native format.'}
    # An earlier native V9 state can be preserved under .kristal/v9 while
    # build/v9 is the newer candidate. Only a canonical *explicit* historical
    # declaration authorizes excluding that native path from current conflicts.
    historical_native = native_v9_declared_historical(root)
    current = [v for v in valid if v['path'] != '.kristal/v9/state-snapshot.json'
               and not (historical_native and
                        v['path'] == '.kristal/v9/states/current.state-snapshot.json')]
    current_digests = {v['digest'] for v in current}
    if len(current_digests)>1:
        return {'status': 'REVIEW', 'path': None, 'candidates': candidates,
                'detail': 'Current V9 state surfaces disagree on their declared digests.'}
    if not current:
        return {'status': 'HISTORICAL_ONLY', 'path': None, 'candidates': candidates,
                'detail': 'Only historical V9 state surfaces were observed.'}
    return {'status': 'OBSERVED', 'path': current[0]['path'], 'candidates': candidates,
            'detail': 'V9 snapshot structure observed; commitments not recomputed.'}

def inspect_workspace(path: str|Path, *, diagnostic=None, analysis=None, arketype=None):
    root=Path(path).expanduser().resolve()
    ws=root/'kristal.workspace.json'
    issues=[]
    try:
        if ws.stat().st_size>3*1024*1024:raise ValueError('workspace descriptor too large')
        obj=json.loads(ws.read_text('utf-8-sig'))
        if not isinstance(obj,dict):raise ValueError('workspace JSON is not an object')
    except (OSError,ValueError) as exc:
        obj={};issues.append({'kind':'INVALID_WORKSPACE','detail':type(exc).__name__})
    fields={};counts=Counter()
    for label,key,requirement in FIELDS:
        val=read_key(obj,key)
        status='PRESENT' if is_present(val) else ('MISSING_REQUIRED' if requirement=='required' else
                                                'MISSING_RECOMMENDED' if requirement=='recommended' else
                                                'NOT_DECLARED_REVIEW' if requirement=='review' else 'OPTIONAL_ABSENT')
        if val is False and label=='semantic_mapping.requires_independent_semantic_validation':
            status='DECLARED_UNVERIFIED'  # False is an explicit declaration, not a missing value.
        if is_present(val) and requirement=='review':
            status='DECLARED_UNVERIFIED'
        if label=='format' and is_present(val) and val!='kristal.local-workspace/3.2.0':
            status='FORMAT_REVIEW'
        if label=='classification.primary_archetype' and isinstance(val,str) and not val.startswith('ARK-'):
            status='FORMAT_REVIEW'
        fields[label]={'status':status,'requirement':requirement,'value':_short_value(val) if is_present(val) else None}
        counts[status]+=1
    # Strict existence verification for file references (not semantic validity).
    references=[]
    native=read_key(obj,'native_model.canonical_paths')
    if isinstance(native,list):
        for rel in native[:1000]:
            status=_safe_reference(root,rel)
            references.append({'source':'native_model.canonical_paths','path':rel,'status':status})
            if status!='PRESENT':issues.append({'kind':status,'field':'native_model.canonical_paths','path':rel})
    elif native is not None:
        issues.append({'kind':'INVALID_FIELD_TYPE','field':'native_model.canonical_paths'})
    semantic_file=read_key(obj,'semantic_mapping.file')
    if semantic_file is not None:
        status=_safe_reference(root,semantic_file)
        references.append({'source':'semantic_mapping.file','path':semantic_file,'status':status})
        if status!='PRESENT':issues.append({'kind':status,'field':'semantic_mapping.file','path':semantic_file})
    artifacts={rel:bool((root/rel).is_file()) for rel in ARTIFACTS}
    # An observed structure is not a V9 PASS or a signed commitment proof.
    native_state = _observe_native_v9_state(root, obj.get('state_ref'))
    if native_state['status'] != 'OBSERVED':
        issues.append({'kind': 'STATE_PROFILE_REVIEW', 'detail': native_state['detail'],
                       'native_snapshot_status': native_state['status']})
    return {'path':str(root),'title':obj.get('title') or root.name,
            'state_ref':obj.get('state_ref'),'fields':fields,'field_counts':dict(counts),
            'artifacts':artifacts,'native_state_snapshot':native_state,
            'references':references,'issues':issues,
            'diagnostic':diagnostic,'analysis':analysis,'arketype':arketype,
            'limits':['PRESENT means a nonempty declaration, not a verification.',
                      'DECLARED_UNVERIFIED is not an approved classification.',
                      'Absent optional fields are not violations.',
                      'File existence does not validate semantic references or canonical hashes.']}


def write_coverage(root, workspaces, output_dir, *, db=None):
    from . import repository
    source=Path(root).expanduser().resolve(strict=True)
    target=Path(output_dir).expanduser().resolve()
    if target==source or target.is_relative_to(source):raise ValueError('Reports must be outside locals')
    target.mkdir(parents=True,exist_ok=True)
    entries=[]; totals=Counter()
    for row in workspaces:
        path=row['path']
        if Path(path).parent!=source:continue
        diag=repository.latest_observation(path,'diagnostic',db=db)
        analysis=repository.latest_observation(path,'analysis',db=db)
        ark=repository.latest_observation(path,'arketype',db=db)
        observed=inspect_workspace(path,diagnostic={
                      'verdict':diag['verdict'],'freshness':diag['freshness'],'profile':diag['profile'],
                      'findings':(diag.get('payload') or {}).get('findings',[])[:100]
                          if isinstance((diag.get('payload') or {}).get('findings',[]),list) else []
                    } if diag else None,
                                  analysis={'priority':analysis['verdict'],'freshness':analysis['freshness']} if analysis else None,
                                  arketype={'comparison':ark['verdict'],'freshness':ark['freshness']} if ark else None)
        entries.append(observed)
        totals.update(observed['field_counts'])
    data={'format':'kristal.manager-global-field-coverage/1.0',
          'generated_at':datetime.now(timezone.utc).isoformat(),'source_root':str(source),
          'kristals':len(entries),'field_totals':dict(totals),
          'field_catalog':[{'name':label,'requirement':req} for label,_,req in FIELDS],
          'entries':entries,'qualification':'NOT_ESTABLISHED'}
    (target/'CHAMPS-127-COMPLETS.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    with (target/'CHAMPS-127-STATUTS.csv').open('w',encoding='utf-8-sig',newline='') as f:
        columns=['kristal','path','field','status','requirement','value']
        writer=csv.DictWriter(f,fieldnames=columns,delimiter=';');writer.writeheader()
        for item in entries:
            for field,detail in item['fields'].items():
                writer.writerow({'kristal':item['title'],'path':item['path'],'field':field,
                                 'status':detail['status'],'requirement':detail['requirement'],
                                 'value':json.dumps(detail['value'],ensure_ascii=False,default=str) if detail['value'] is not None else ''})
    with (target/'CHAMPS-127-MANQUANTS.csv').open('w',encoding='utf-8-sig',newline='') as f:
        cols=['kristal','field','status','path'];writer=csv.DictWriter(f,fieldnames=cols,delimiter=';');writer.writeheader()
        for item in entries:
            for key,value in item['fields'].items():
                if value['status'] in ('MISSING_REQUIRED','MISSING_RECOMMENDED','NOT_DECLARED_REVIEW','FORMAT_REVIEW'):
                    writer.writerow({'kristal':item['title'],'field':key,'status':value['status'],'path':item['path']})
            for issue in item['issues']:
                writer.writerow({'kristal':item['title'],'field':issue.get('field') or issue.get('detail') or 'file',
                                'status':issue['kind'],'path':item['path']})
    return {'count':len(entries),'field_totals':dict(totals),'directory':str(target),
            'files':['CHAMPS-127-COMPLETS.json','CHAMPS-127-STATUTS.csv','CHAMPS-127-MANQUANTS.csv']}
