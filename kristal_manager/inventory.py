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
        fields=('title','slug','state_ref','workspace_format','native_kind','profile','discovery',
                'readiness','state_source','state_commitment','state_conflict',
                'hosted_network_baseline','portable_ai_enabled','ai_entrypoint_present',
                'ai_manifest_present','registered_artifacts')
        record={k:row.get(k) for k in fields}
        record['availability']='local'
        record['qualification']='NOT_ESTABLISHED'
        record['publication']='NOT_ESTABLISHED'
        record['archetype']=((row.get('discovery') or {}).get('classification') or {}).get('primary_archetype') or 'UNDECLARED'
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
           'Arketype identity is displayed only when explicitly declared in consistent Kit metadata.',
           'Discovery fingerprint consistency does not verify current source bytes.',
           'Reader hints do not authorize access, execution, qualification or publication.'
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

# Experimental, explicitly operator-authorized adapter for the *existing* KNAV
# consumer. This is not a grant issuer or a public/hosted inventory format.
KONSTELLATION_PREVIEW_FORMAT = 'konstellation.manager-inventory-preview/0.1'


def konstellation_preview(roots: list[str|Path], *, allowed_principals: list[str],
                          allowed_roles: list[str] | None = None) -> dict:
    """Opt-in local adapter: no paths, sources, authorization inference or network calls.

    Caller must independently authenticate the principals and ensure they are
    authorized for *all* entries supplied. In particular this function cannot
    inspect private workspace policies and does not claim to do so.
    """
    import hashlib
    import re
    principals=list(dict.fromkeys(allowed_principals))
    roles=list(dict.fromkeys(allowed_roles or []))
    if not principals and not roles:
        raise ManagerError('Default-deny: specify an explicitly authorized principal or role.')
    for item in [*principals,*roles]:
        if not isinstance(item,str) or not (1 <= len(item) <= 128) or not item.isprintable() or item.strip()!=item:
            raise ManagerError('Invalid principal / role identifier.')
    if len(principals)>32 or len(roles)>32:
        raise ManagerError('At most 32 principals or roles are allowed.')
    rows=[row for row in scan_roots(roots) if not row['hidden_auxiliary']]
    if len(rows)>1000:
        raise ManagerError('Konstellation preview limit: no more than 1,000 Kristals.')
    entries=[]
    by_ref={}
    for row in rows:
        ref=row.get('state_ref')
        if ref: by_ref[ref]=by_ref.get(ref,0)+1
    for row in rows:
        ref=row.get('state_ref')
        collision=bool(ref and by_ref[ref]>1)
        src=(row['path']+'\0'+str(ref or '')).encode('utf-8')
        key='local-'+hashlib.sha256(src).hexdigest()[:32]
        title=row.get('title')
        # The preview consumer requires a bounded text label. Do not fall back to paths.
        if not isinstance(title,str) or len(title)>200 or not title.isprintable():
            title='Local Kristal '+key[-8:]
        status=row.get('readiness')
        if collision or row.get('state_conflict'):
            readiness='blocked'
        elif status in ('READY','STATE-ONLY','LEGACY STATE'):
            readiness='not_checked'   # no verified Konstellation reader readiness
        elif status in ('NO STATE','MIGRATE'):
            readiness='not_ready'
        else:
            readiness='blocked'
        entry={'id':key,'title':title, 'visibility':'private',
               'readiness':readiness,'availability':'unknown',
               'allowed_principals':principals,'allowed_roles':roles}
        if isinstance(ref,str) and 0<len(ref)<=512 and ref.isprintable():
            entry['state_ref']=ref
        commitment=row.get('state_commitment')
        if isinstance(commitment,str) and re.fullmatch(r'sha256:[0-9a-f]{64}',commitment):
            entry['state_commitment']=commitment   # reported, not verified
        discovery=row.get('discovery') or {}
        if discovery.get('status') in ('consistent_unverified','verified_registered_sources'):
            archetype=(discovery.get('classification') or {}).get('primary_archetype')
            if isinstance(archetype,str) and len(archetype)<=100 and re.fullmatch(r'ARK-[0-9]{2,}',archetype):
                entry['archetype']=archetype
        entries.append(entry)
    preview={'format':KONSTELLATION_PREVIEW_FORMAT,'entries':entries}
    if len(json.dumps(preview,ensure_ascii=False).encode('utf-8')) > 1024 * 1024:
        raise ManagerError('KNAV preview would exceed 1 MiB consumer limit.')
    return preview
