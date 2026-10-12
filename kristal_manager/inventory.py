"""Read-only, disclosure-minimized local discovery for an authorized Konstellation client.

Non-normative provisional export. Data must remain on the operator machine and is
never hosted or transmitted by this module. Separate authorization is needed for
any network-facing reader. Do not infer archetypes or qualification.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
import json
import os
from .core import scan_roots, ManagerError

FORMAT='kristal.manager-local-inventory/0.1-candidate'


def inventory(roots: list[str|Path], *, include_paths: bool=False) -> dict:
    """Fresh scan without domain file contents; local-only, may reveal metadata."""
    entries=[]
    for row in scan_roots(roots):
        if row['hidden_auxiliary']:
            continue
        fields=('title','slug','state_ref','workspace_format','native_kind','profile',
                'readiness','state_source','state_commitment','state_conflict',
                'hosted_network_baseline','portable_ai_enabled','ai_entrypoint_present',
                'ai_manifest_present','registered_artifacts')
        record={k:row.get(k) for k in fields}
        record['availability']='local'
        record['qualification']='NOT_ESTABLISHED'
        record['publication']='NOT_ESTABLISHED'
        record['archetype']='UNDECLARED'
        if include_paths:
            record['local_path']=row['path']
        entries.append(record)
    # A slug alone is not a state identity; conflicts must be explicit.
    known={}
    for e in entries:
        ref=e.get('state_ref')
        if ref:
            known.setdefault(ref,[]).append(e)
    for members in known.values():
        if len(members)>1:
            for member in members:
                member['identity_collision']=True
                member['readiness']='IDENTITY COLLISION'
    return {
       'format':FORMAT,'mode':'local-read-only',
       'generated_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
       'identity_rule':'state_ref is the identity; slug is not authoritative',
       'semantic_authority':False,'validated_domain_facts':False,
       'record_count':len(entries),'records':entries,
       'warnings':[
           'Inventory metadata is sensitive; use only in a trusted local process.',
           'READY indicates a structurally present local state, not C1 qualification.',
           'The declared v10 baseline does not prove a hosted or published state.',
           'Arketype type is not inferred from native_kind or filename.'
       ]
    }


def save_private_inventory(payload: dict, output: Path, *,overwrite: bool=False) -> Path:
    path=Path(output).expanduser().absolute()
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_symlink() or (path.exists() and not overwrite):
        raise ManagerError('Refusing to overwrite inventory output or follow a symlink.')
    # Use an exclusive private file by default; no automatic exposure over HTTP.
    data=(json.dumps(payload,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    flags=os.O_WRONLY|os.O_CREAT|(0 if overwrite else os.O_EXCL)|getattr(os,'O_NOFOLLOW',0)
    if overwrite:
        flags|=os.O_TRUNC
    fd=os.open(path,flags,0o600)
    try:
        os.fchmod(fd,0o600) if hasattr(os,'fchmod') else None
        with os.fdopen(fd,'wb') as f:
            fd=-1
            f.write(data)
    finally:
        if fd>=0:os.close(fd)
    return path
