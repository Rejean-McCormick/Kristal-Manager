"""Persisted, *advisory* review overlay for Kristal Manager's scan.

No edits to Kristal workspaces.  State_ref is the only lookup key. The seed is
immutable; user decisions are kept separately in catalogue/ and never overwritten
by future overlay extraction. Historical checks are NOT current verification.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile

MANAGER_ROOT = Path(__file__).resolve().parent.parent
SEED_PATH = MANAGER_ROOT / 'data' / 'revue_initiale_14_kristals.json'
REGISTRY_PATH = MANAGER_ROOT / 'catalogue' / 'registre_revue_kristals.json'
FORMAT = 'kristal.manager-review-registry/1.0'
MAX_ANCHOR = 32 * 1024 * 1024  # hash only tiny metadata/index JSON, never canon graphs
STATES = ('proposed', 'needs_discussion', 'approved_locally', 'rejected_locally')


def _read_json(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj, dict):
        raise ValueError('Racine de registre JSON invalide')
    return obj


def _validate(obj: dict) -> dict:
    if obj.get('format') != FORMAT or not isinstance(obj.get('entries'), list):
        raise ValueError('Version ou entrées du registre non reconnues')
    found=set()
    for row in obj['entries']:
        if not isinstance(row, dict) or not isinstance(row.get('state_ref'),str) or not row['state_ref'].strip():
            raise ValueError('Identifiant de revue invalide')
        if row['state_ref'] in found:
            raise ValueError('Identité state_ref dupliquée dans le registre')
        found.add(row['state_ref'])
        decision=row.get('archetype_review',{})
        if not isinstance(decision,dict) or decision.get('status') not in STATES:
            raise ValueError('Statut ARK de revue invalide : '+row['state_ref'])
        proposed=decision.get('recommended_primary_candidates',[])
        if not isinstance(proposed,list) or any(not isinstance(x,str) for x in proposed):
            raise ValueError('Candidats de revue invalides')
        chosen=decision.get('review_selected_primary')
        if chosen is not None and chosen not in proposed:
            raise ValueError('Choix primaire inconnu : '+row['state_ref'])
        if decision['status']=='approved_locally' and (not chosen or not decision.get('local_human_approval') or not row.get('decision_log')):
            raise ValueError('Approbation sans choix et décision humaine tracés : '+row['state_ref'])
    return obj


def _seed_document() -> dict:
    seed=_read_json(SEED_PATH)
    if seed.get('format')!='kristal.manager-review-seed/1.0':
        raise ValueError('Format du seed inconnu')
    doc={'format':FORMAT,'created_utc':datetime.now(timezone.utc).isoformat(),
         'seed_source':'data/revue_initiale_14_kristals.json','entries':seed['entries']}
    return _validate(doc)


def _atomic_json(path:Path, obj:dict) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_symlink():
        raise ValueError('Registre via lien symbolique interdit')
    fd,name=tempfile.mkstemp(prefix='.revue-',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as out:
            json.dump(obj,out,ensure_ascii=False,indent=2)
            out.write('\n');out.flush();os.fsync(out.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


def load_registry(path:Path|str|None=None, *, initialize:bool=True) ->dict:
    """Never overwrite an existing registry, even if corrupt or incompatible."""
    target=Path(path) if path is not None else REGISTRY_PATH
    if target.is_symlink():raise ValueError('Registre via lien symbolique interdit')
    if not target.exists():
        if not initialize:
            raise FileNotFoundError(target)
        seed=_seed_document()
        _atomic_json(target,seed)
    existing=_validate(_read_json(target))
    # Later packs can be seeded by replacing only the immutable seed file.
    # Preserve every prior decision, note and decision_log by state_ref.
    if initialize and path is None:
        additions=[r for r in _seed_document()['entries']
                   if r['state_ref'] not in {x['state_ref'] for x in existing['entries']}]
        if additions:
            existing['entries'].extend(additions)
            existing['entries'].sort(key=lambda x:x['state_ref'])
            _validate(existing)
            _atomic_json(target,existing)
    return existing


def _anchor_status(workspace:Path, anchors:dict) ->dict:
    statuses={}
    for rel,digest in anchors.items():
        if not isinstance(rel,str) or rel not in ('kristal.workspace.json','canon/state.index.json'):
            statuses[str(rel)]='INVALID_ANCHOR';continue
        target=workspace / rel
        try:
            if target.is_symlink() or not target.is_file():
                statuses[rel]='MISSING';continue
            if target.stat().st_size>MAX_ANCHOR:
                statuses[rel]='TOO_LARGE';continue
            current=hashlib.sha256(target.read_bytes()).hexdigest()
            statuses[rel]='MATCH' if current==digest else 'DIFFERENT'
        except OSError:
            statuses[rel]='UNREADABLE'
    label='MATCH' if len(statuses)==2 and all(v=='MATCH' for v in statuses.values()) else (
         'CHANGED' if any(v=='DIFFERENT' for v in statuses.values()) else 'UNVERIFIED')
    return {'status':label,'metadata_anchors':statuses,
            'meaning':'Compare seulement workspace + index. Ne prouve pas une intégrité canonique complète.'}


def annotate_entries(entries:list[dict], *, source:Path|str, registry_path:Path|str|None=None) ->dict:
    """Attach reviews to live scan results; never alter priority or operational_result.

    If the persistent registry is broken, continue technical scan but surface a
    registry error. The corrupted file is NEVER recreated.
    """
    source=Path(source).resolve()
    try:
        reg=load_registry(registry_path)
    except (OSError,ValueError,TypeError) as exc:
        for entry in entries:
            entry['registered_review']=None
            entry['review_registry_status']='UNAVAILABLE'
        return {'available':False,'error':type(exc).__name__+': '+str(exc),
            'matched':0,'not_found':len(entries),'anchor_changed':0,'anchor_unverified':0,
            'approved_locally':0,'proposed':0,'needs_discussion':0}
    index={r['state_ref']:r for r in reg['entries']}
    counts={'available':True,'path':str(Path(registry_path) if registry_path is not None else REGISTRY_PATH),
        'registered':len(index),'matched':0,'not_found':0,'anchor_changed':0,'anchor_unverified':0,
        'approved_locally':0,'proposed':0,'needs_discussion':0,'rejected_locally':0}
    for entry in entries:
        row=index.get(entry.get('state_ref'))
        if row is None:
            entry['registered_review']=None
            entry['review_registry_status']='NOT_REGISTERED'
            counts['not_found']+=1
            continue
        counts['matched']+=1
        # Path is not an authority. Never read an arbitrary external directory based
        # on catalog cache. Only workspaces strictly inside the current source root.
        try:
            folder=Path(entry['path']).resolve(strict=True)
            if folder==source or not folder.is_relative_to(source):raise ValueError('hors de la racine scannée')
            anchors=_anchor_status(folder,row.get('provenance',{}).get('anchors_sha256',{}))
        except (OSError,ValueError,TypeError,KeyError):
            anchors={'status':'UNVERIFIED','metadata_anchors':{},'meaning':'Le chemin du Kristal n’a pas pu être vérifié sous la racine courante.'}
        status=anchors['status']
        if status=='CHANGED':counts['anchor_changed']+=1
        elif status=='UNVERIFIED':counts['anchor_unverified']+=1
        review=row['archetype_review']
        review_state=review['status']
        counts[review_state]+=1
        # Current health derives ONLY from this scan, not from historical snapshot.
        op=entry.get('operational_result')
        current_health=('BLOCKER' if entry.get('priority')=='blocker' else
             'WARNING' if entry.get('priority')=='warning' else
             'CHECKS_PASSED' if op=='LOCAL_CHECKS_PASSED' else 'NOT_VERIFIED_IN_THIS_SCAN')
        entry['registered_review']={
            'source_batch':row['batch'], 'historical_technical':row['technical_snapshot'],
            'archetype_recommendations':review['recommended_primary_candidates'],
            'archetype_review_status':review_state,
            'archetype_rationale':review['rationale'],
            'explicit_human_decision':review.get('local_human_approval',False),
            'locally_selected_archetype':review.get('review_selected_primary'),
            'snapshot_date':row['snapshot_date'],
            'provenance_status':anchors,
            'current_scan_technical_health':current_health,
            'limitations':'Historique sur snapshot sélectif; ARK proposé ≠ tag déclaré; non certification Framework.'}
        entry['review_registry_status']=status
    return counts


def update_decision(state_ref:str, status:str, note:str, *, author:str='Utilisateur Manager',
                    path:Path|str|None=None, selected_primary:str|None=None)->dict:
    """Manual local decision only: no modifications to any Kristal or tag."""
    if status not in STATES:raise ValueError('Statut de décision non autorisé')
    note=note.strip()
    if not note or len(note)>2000:raise ValueError('Une justification courte est obligatoire (2000 caractères maximum).')
    reg=load_registry(path)
    row=next((x for x in reg['entries'] if x['state_ref']==state_ref),None)
    if row is None:raise KeyError(state_ref)
    options=row['archetype_review']['recommended_primary_candidates']
    if selected_primary is not None and selected_primary not in options:
        raise ValueError('Le choix primaire ne figure pas dans les propositions de revue.')
    if status=='approved_locally':
        if len(options)>1 and not selected_primary:
            raise ValueError('Il faut départager les candidats avant acceptation.')
        selected_primary=selected_primary or options[0]
    old=row['archetype_review']['status']
    decision={'utc':datetime.now(timezone.utc).isoformat(), 'author':author[:120],
              'old_status':old, 'new_status':status, 'note':note,
              'selected_primary':selected_primary if status=='approved_locally' else None}
    row.setdefault('decision_log',[]).append(decision)
    row['archetype_review']['status']=status
    row['archetype_review']['local_human_approval']=status=='approved_locally'
    row['archetype_review']['review_selected_primary']=selected_primary if status=='approved_locally' else None
    _validate(reg)
    _atomic_json(Path(path) if path is not None else REGISTRY_PATH,reg)
    return decision
