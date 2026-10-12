"""Local-first Kristal inventory and integrity checks.

The alpha.12 recovery deliberately does not attempt remote Git synchronization.
Existing mutation entry points fail closed until a separately qualified backend is
restored. Local metadata is never evidence of domain validity or publication.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile

CURRENT_LOCAL_FORMAT = 'kristal.local-workspace/3.2.0'
REGISTRY_FORMAT = 'kristal-local-registry/2.0'
PUBLISH_REQUEST_FORMAT = 'kristal.publication-request/1.0'

class ManagerError(RuntimeError):
    pass

def _read_json(path: Path) -> dict:
    try:
        value=json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError):
        return {}
    return value if isinstance(value, dict) else {}

def _sha(data: bytes) -> str:
    return 'sha256:'+hashlib.sha256(data).hexdigest()

def _path(p: str|Path) -> Path:
    return Path(p).expanduser().resolve()

def state_candidates(folder: str|Path) -> list[dict]:
    """List current/release/legacy state representations without rewriting them."""
    root=_path(folder)
    candidates=[]
    fixed=(('state-export','current','state/state-snapshot.json'),
           ('build-v9','current','build/v9/state-snapshot.json'),
           ('node-v9','legacy','.kristal/v9/state-snapshot.json'))
    for source,role,relative in fixed:
        file=root/relative
        if not file.is_file():continue
        blob=file.read_bytes()
        state=_read_json(file)
        candidates.append(dict(source=source,role=role,path=str(file),
           state_ref=state.get('state_ref'),
           logical_commitment=(state.get('logical_commitment') or {}).get('digest'),
           state_blob_digest=_sha(blob)))
    release_dir=root/'release/v9'
    if release_dir.is_dir():
        for file in sorted(release_dir.rglob('state-snapshot.json')):
            state=_read_json(file)
            candidates.append(dict(source='release-v9',role='release',path=str(file),
                  state_ref=state.get('state_ref'),
                  logical_commitment=(state.get('logical_commitment') or {}).get('digest'),
                  state_blob_digest=_sha(file.read_bytes())))
        for file in sorted(release_dir.glob('states/*.json')):
            state=_read_json(file)
            candidates.append(dict(source='release-v9',role='release',path=str(file),
                  state_ref=state.get('state_ref'),
                  logical_commitment=(state.get('logical_commitment') or {}).get('digest'),
                  state_blob_digest=_sha(file.read_bytes())))
    order={'state-export':0,'build-v9':1,'release-v9':2,'node-v9':3}
    return sorted(candidates,key=lambda x:(order[x['source']],x['path']))

def detect_kristal(path: str|Path) -> dict|None:
    folder=_path(path)
    ws=folder/'kristal.workspace.json'
    auxiliary=not ws.exists() and (folder/'canon').exists() and (folder/'README.md').exists()
    state_only=not ws.exists() and not auxiliary and any((folder/relative).is_file() for relative in ('state/state-snapshot.json','build/v9/state-snapshot.json'))
    if not ws.is_file() and not auxiliary and not state_only:return None
    data=_read_json(ws) if ws.is_file() else {}
    states=state_candidates(folder)
    current=[x for x in states if x['role']=='current']
    selected=current[0] if current else (states[0] if states else None)
    declaration=data.get('state_ref')
    reasons=[]
    if len({(s['state_ref'],s['logical_commitment']) for s in current})>1:
        reasons.append('Current state surfaces disagree.')
    if selected and declaration and selected['state_ref']!=declaration:
        reasons.append('Workspace declares a different state_ref from the current state snapshot.')
    if auxiliary:status='AUXILIARY'
    elif state_only:status='STATE CONFLICT' if reasons else 'STATE-ONLY'
    elif data.get('format')!=CURRENT_LOCAL_FORMAT: status='MIGRATE'
    elif reasons: status='STATE CONFLICT'
    elif current:status='READY'
    elif states:status='LEGACY STATE'
    else:status='NO STATE'
    profile=data.get('profile')
    meta=dict(path=str(folder),kind='local' if ws.exists() else 'auxiliary',
       title=data.get('title') or folder.name,slug=data.get('slug') or folder.name,
       workspace_format=data.get('format'),profile=profile,status=data.get('status'),
       declared_state_ref=declaration,state_ref=selected['state_ref'] if selected else declaration,
       state_source=selected['source'] if selected else None,
       state_commitment=selected['logical_commitment'] if selected else None,
       state_blob_digest=selected['state_blob_digest'] if selected else None,
       state_candidates=states,state_conflict=bool(reasons),state_conflict_reasons=reasons,
       needs_migration=bool(ws.exists() and data.get('format')!=CURRENT_LOCAL_FORMAT),
       readiness=status,hidden_auxiliary=auxiliary,
       hosted_network_baseline=(data.get('target') or {}).get('hosted_network_baseline'),
       portable_ai_enabled=(data.get('portable_ai') or {}).get('enabled') is True,
       ai_entrypoint_present=(folder/'AI_START_HERE.md').is_file(),
       ai_manifest_present=(folder/'AI_MANIFEST.json').is_file(),
       native_kind=(data.get('native_model') or {}).get('kind'),
       registered_artifacts=len((_read_json(folder/'canon/state.index.json')).get('artifacts') or
                                _read_json(folder/'canon/state.index.json').get('canonical_artifacts') or []))
    return meta

def scan_roots(roots: Iterable[Path|str]) -> list[dict]:
    rows=[];seen=set()
    for root in roots:
        p=_path(root)
        if not p.is_dir(): continue
        parents=[p,*sorted((x for x in p.rglob('*') if x.is_dir() and not x.is_symlink()),key=str)]
        for parent in parents:
            if parent in seen:continue
            seen.add(parent)
            row=detect_kristal(parent)
            if row:rows.append(row)
    entries={Path(r['path']):r for r in rows}
    for p,r in entries.items():
        r['nested_under']=next((str(a) for a in p.parents if a in entries),None)
    return sorted(rows,key=lambda x:x['path'])

def scan_roots_quick(roots, previous=None):
    # Deep scan is intentionally retained for accurate state changes.
    fresh=scan_roots(roots)
    old={x['path']:x for x in previous or []}
    for row in fresh:
        prior=old.get(row['path'])
        row['scan_cached']=bool(prior and all(prior.get(k)==row.get(k) for k in
           ('state_ref','state_commitment','state_blob_digest','workspace_format','readiness')))
    return fresh

def merge_scan(config: dict, rows: list[dict]) -> dict:
    old={str(_path(x['path'])):x for x in config.get('entries',[]) if x.get('path')}
    merged=[]
    for row in rows:
        prior=old.get(row['path'],{})
        record={**prior,**row}
        if prior and any(prior.get(k)!=row.get(k) for k in
              ('state_ref','state_commitment','state_blob_digest','state_conflict','workspace_format')):
            for key in ('last_validation','last_validation_result','last_validation_cache_key'):
                record[key]=None
        merged.append(record)
    return {**config,'format':REGISTRY_FORMAT,'entries':merged}

def load_manager_config(path: Path|str, workspace_root: Path|str) -> dict:
    data=_read_json(_path(path))
    return {'format':REGISTRY_FORMAT,'roots':[str(_path(workspace_root)/'locals')],
            'entries':[],**data,'format':REGISTRY_FORMAT}

def sanitize_repo_name(title: str) -> str:
    return re.sub(r'-+','-',re.sub(r'[^\w-]+','-',title.strip(),flags=re.ASCII)).strip('-')

def scan_sensitive_files(root: Path|str) -> list[str]:
    root=_path(root)
    hits=[]
    for p in root.rglob('*'):
        if not p.is_file() or p.is_symlink():continue
        rel=p.relative_to(root).as_posix()
        if p.name.lower() in ('.env','id_rsa','id_ed25519','credentials.json','secrets.json') or re.search(r'\.(?:pem|p12|pfx|key)$',p.name,re.I):
            hits.append(rel)
    return sorted(hits)

def validation_cache_key(record: dict, *,workspace_root=None,network_config=None) -> str:
    stable={k:record.get(k) for k in ('path','workspace_format','state_ref','state_commitment',
             'state_blob_digest','readiness','state_conflict')}
    return _sha(json.dumps(stable,sort_keys=True,default=str).encode())

def validate_local_cached(path, *,previous=None,workspace_root=None,network_config=None,progress=None):
    p=_path(path);rec=detect_kristal(p)
    if not rec:raise ManagerError('Not a recognized local Kristal.')
    key=validation_cache_key(rec,workspace_root=workspace_root,network_config=network_config)
    if previous and previous.get('last_validation_result')=='VALID' and previous.get('last_validation_cache_key')==key:
        return dict(result='VALID',cached=True,validation_cache_key=key)
    if progress:progress(f'{p.name}: inspecting local workspace')
    return dict(result='VALID' if rec['readiness']=='READY' else 'BLOCKED',
                cached=False,validation_cache_key=key,readiness=rec['readiness'],
                note='Structural inspection only; not independent domain qualification.')

def validate_entries_parallel(entries, *,workspace_root,network_config,max_workers=4,progress=None):
    if progress:progress(f'Validating entries using {max_workers} parallel worker(s).')
    def one(e):
        try:
            v=validate_local_cached(Path(e['path']),previous=e,workspace_root=workspace_root,
                                  network_config=network_config,progress=progress)
            return {'path':e['path'],'title':e.get('title'),'ok':v['result']=='VALID','validation':v}
        except Exception as exc:return {'path':e['path'],'title':e.get('title'),'ok':False,'error':str(exc)}
    with ThreadPoolExecutor(max_workers=max(1,min(max_workers,4))) as executor:
        result=list(executor.map(one,entries))
    if progress:
        for i in range(len(entries)):progress(f'[{i+1}/{len(entries)}] completed')
    return result

def _quiet_subprocess_kwargs():
    return {'creationflags':getattr(subprocess,'CREATE_NO_WINDOW',0x08000000)} if os.name=='nt' else {}

def _locate(root:Path,dir_pattern:str,relative:str):
    if not root.is_dir():return None
    candidates=[]
    for p in [root,*root.iterdir()]:
        if p.is_dir() and dir_pattern.lower() in p.name.lower():
            file=p/relative
            if file.is_file():candidates.append(file)
    return sorted(candidates,key=lambda x:x.as_posix().lower())[-1] if candidates else None

def find_local_tool(root):return _locate(_path(root),'Kristal-Authoring-Kit','tools/kristal.py')
def find_github_setup(root):return _locate(_path(root),'Kristal-GitHub-Bootstrap','Kristal-GitHub-Setup.pyw')
def find_kompiler(root):return _locate(_path(root),'Kompiler','Kompiler.pyw')
def find_framework_cli(root,network_config=None):
    ref=None
    if network_config and Path(network_config).is_file():
        try:ref=(tomllib.loads(Path(network_config).read_text('utf8')).get('framework') or {}).get('ref')
        except Exception:pass
    return _locate(_path(root),'Kristal-Framework','reference/js/bin/kristal-ref.mjs') or _locate(_path(root),'KristalV10','reference/js/bin/kristal-ref.mjs'),ref

def framework_supports_v10(path):
    p=Path(path)
    cli=p.parent.parent/'src/cli.mjs'
    return cli.is_file() and all(t in cli.read_text('utf8') for t in ('v10-capabilities','verify-node-v10','verify-github-binding-v10'))

def import_local(archive, destination):
    """Safe local-only ZIP import with traversal and overwrite protection."""
    destination=_path(destination);destination.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        targets=[]
        for e in z.infolist():
            raw=Path(e.filename)
            if raw.is_absolute() or '..' in raw.parts or not raw.parts:
                raise ManagerError('ZIP path traversal is not permitted.')
            if ((e.external_attr >> 16) & 0o170000)==0o120000:
                raise ManagerError('ZIP symbolic links are not permitted.')
            name=re.sub(r'-v\d+(?:\.\d+)*$','',raw.parts[0])
            result=destination/name
            if result.exists():raise ManagerError('Destination exists; import would overwrite files.')
            targets.append((e,result.joinpath(*raw.parts[1:])))
        for e,p in targets:
            if e.is_dir():p.mkdir(parents=True,exist_ok=True)
            else:
                p.parent.mkdir(parents=True,exist_ok=True)
                with z.open(e) as inp,p.open('wb') as out:shutil.copyfileobj(inp,out)
    return sorted({p for _,p in targets if p.parent==destination}) or sorted({destination / re.sub(r'-v\d+(?:\.\d+)*$','',Path(e.filename).parts[0]) for e,_ in targets})

# The old remote sync/backup/migration implementation was not present in the
# supplied source OR the GitHub default branch. Do not recreate an unreviewed
# publisher in a fallback patch.
def _disabled(operation):
    raise ManagerError(f'{operation} is blocked: the previous operational backend is missing. '
                       'Use the local inventory; restore and qualify the backend separately.')
def migrate_local(*args,**kwargs):return _disabled('Migration')
def prepare_publication_request(*args,**kwargs):return _disabled('Publication preparation')
def prepare_github_read_surface(*args,**kwargs):return _disabled('GitHub read-surface preparation')
def sync_local_to_github(*args,**kwargs):return _disabled('GitHub sync')
def sync_entries_batch(*args,**kwargs):return _disabled('Batch GitHub sync')
def _sync_prepared_collection(*args,**kwargs):return _disabled('GitHub sync blocked before checkout')
def backup_local(*args,**kwargs):return _disabled('Public full-workspace backup disabled')
def resolve_publication_collection(*args,**kwargs):return _disabled('Hosting target lookup')
def ensure_collection_checkout(*args,**kwargs):return _disabled('Collection checkout')
def github_remote_json_file(*args,**kwargs):return _disabled('GitHub remote query')
def _apply_prepared_surface(*args,**kwargs):return _disabled('Collection modification')
def _build_collection_index(*args,**kwargs):return _disabled('Collection index modification')

def readiness_for_record(record: dict) -> str:
    """Report observed local state readiness; never assert domain qualification."""
    return record.get('readiness') or 'NOT EVALUATED'

from .publication_gate import verify_public_write  # Explicit C2 gate, no remote write enabled.

def ensure_backup_repo(*args,**kwargs):
    return _disabled('Full-workspace backup')
