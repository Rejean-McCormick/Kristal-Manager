"""Private, explicit, non-publishing Kit -> GitHub collection *candidate*.

Never writes into a Git checkout or to a local Kristal. There is no network,
Git invocation, publication authority, or implicit selection of all workspaces.
Operator must independently qualify and approve every exposed byte before
moving anything from private staging into a PUBLIC repository.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile

from .core import ManagerError

SHA = re.compile(r'^sha256:[0-9a-f]{64}$')
SLUG = re.compile(r'^[a-z0-9][a-z0-9._-]*$')
POLICY = {k:True for k in ('derived_read_surface', 'sync_is_not_publication',
         'activation_is_separate','materialization_blobs_are_not_implicitly_copied')}


def _hash(blob: bytes) -> str:
    return 'sha256:' + hashlib.sha256(blob).hexdigest()


def _canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf8')


def _json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding='utf8'))
    except (OSError, ValueError) as exc:
        raise ManagerError(f'Invalid metadata: {path.name}') from exc
    if not isinstance(data,dict):
        raise ManagerError(f'Metadata must be an object: {path.name}')
    return data


def _rel(raw: object) -> str:
    if not isinstance(raw,str) or not raw or '\\' in raw or ':' in raw:
        raise ManagerError('Unsafe read-surface path')
    path=PurePosixPath(raw)
    if path.is_absolute() or raw!=path.as_posix() or any(x in ('..','.') for x in path.parts):
        raise ManagerError('Unsafe read-surface path: '+raw)
    return raw


def _safe_tree(root: Path) -> None:
    if not root.is_dir() or root.is_symlink():
        raise ManagerError('Source folder missing or symlinked')
    for base, dirs, names in os.walk(root,followlinks=False):
        for name in dirs + names:
            if (Path(base)/name).is_symlink():
                raise ManagerError('Source has a symlink; copy refused: '+name)


def _inside_git_tree(path: Path) -> bool:
    return any((parent/'.git').exists() for parent in (path,*path.parents))


def _run_kit(kit: Path, command: str, root: Path, extra: list[str] | None = None) -> str:
    args=[sys.executable,str(kit),command,str(root),*(extra or [])]
    try:
        result=subprocess.run(args,capture_output=True,text=True,timeout=300,
                              encoding='utf8',errors='replace',check=False)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise ManagerError(f'Kit operation {command} unavailable: {type(exc).__name__}') from exc
    if result.returncode:
        raise ManagerError(f'Kit {command} rejected workspace {root.name}: '
                           + (result.stderr or result.stdout)[-700:])
    return result.stdout


def _surface(kit: Path, workspace: Path) -> dict:
    text=_run_kit(kit,'read-surface',workspace,['--require-ready','--compact'])
    try:surface=json.loads(text)
    except ValueError as exc:raise ManagerError('Kit did not return read-surface JSON') from exc
    if surface.get('format')!='kristal.github-read-surface/1.0' or surface.get('ready') is not True:
        raise ManagerError('Kit read-surface not ready')
    if not isinstance(surface.get('files'),list) or not surface['files']:
        raise ManagerError('Kit supplied empty read surface')
    return surface


def _make_one(kit: Path, workspace: Path, output: Path, slug: str, *,build_copy: bool) -> dict:
    prepared=workspace
    if build_copy:
        copy=output.parent.parent/'work-copy'/slug
        shutil.copytree(workspace,copy,symlinks=False)
        _run_kit(kit,'check',copy)
        _run_kit(kit,'build-v9',copy,['--with-ai'])
        prepared=copy
    surface=_surface(kit,prepared)
    if surface.get('slug') != slug or surface.get('target_root') != 'kristals/'+slug:
        raise ManagerError('Kit slug/target mismatch; no implicit renaming')
    # A derived rebuild may not silently replace an existing current v9 state.
    for relative in ('state/state-snapshot.json', 'build/v9/state-snapshot.json'):
        previous=workspace/relative
        if previous.is_file():
            recorded=_json(previous)
            if recorded.get('state_ref') != surface.get('state_ref') or \
               recorded.get('logical_commitment') != surface.get('state_logical_commitment'):
                raise ManagerError('A derived build changed the existing v9 semantic commitment; independent review required')

    target=output/slug
    target.mkdir(parents=True,exist_ok=False)
    entries=[]
    bad={'.env','id_rsa','id_ed25519','credentials.json','secrets.json'}
    seen=set()
    for item in surface['files']:
        rel=_rel(item.get('path'))
        if rel in seen:raise ManagerError('Duplicate surface path')
        seen.add(rel)
        if any(part.lower() in ('.git','.ssh','node_modules','__pycache__','.venv') for part in PurePosixPath(rel).parts) or \
           PurePosixPath(rel).name.lower() in bad or \
           PurePosixPath(rel).name.lower().endswith(('.pem','.key','.p12','.pfx','.sqlite','.sqlite3','.db')):
            raise ManagerError('Sensitive file proposed for public surface: '+rel)
        src=prepared.joinpath(*PurePosixPath(rel).parts)
        if src.is_symlink() or not src.is_file() or not src.resolve().is_relative_to(prepared.resolve()):
            raise ManagerError('Unsafe Kit source path '+rel)
        data=src.read_bytes()
        if _hash(data)!=item.get('sha256') or len(data)!=item.get('size'):
            raise ManagerError('Kit surface has changed since assessment: '+rel)
        dst=target.joinpath(*PurePosixPath(rel).parts)
        dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(data)
        entries.append({'path':rel,'role':item['role'],'size':len(data),'sha256':_hash(data)})
    for required in ('AI_MANIFEST.json','AI_START_HERE.md','ai/INDEX.json','state/state-snapshot.json'):
        if required not in seen:raise ManagerError('Mandatory read file missing: '+required)
    ordered=sorted(entries,key=lambda x:x['path'].encode('utf8'))
    obj=_json(target/'ai/INDEX.json').get('materialization_blobs',[])
    if not isinstance(obj,list) or obj!=surface.get('materialization_objects') or len(obj)!=surface.get('materialization_object_count'):
        raise ManagerError('Materialization inventory does not match Kit')
    projection={'format':surface['format'],'slug':slug,'state_ref':surface['state_ref'],
                'state_logical_commitment':surface['state_logical_commitment'],
                'entrypoint':surface['entrypoint'],'files':ordered,
                'materialization_objects':obj}
    digest=_hash(_canonical(projection))
    if digest!=surface['surface_digest']:
        raise ManagerError('Kit digest mismatch; do not stage')
    workspace_info=_json(workspace/'kristal.workspace.json')
    manifest={'format':'kristal.github-sync-manifest/1.0',
              'manager_version':'0.1.0a15.post2','read_surface_format':surface['format'],
              'local_kit_version':surface.get('kit_version'),
              'slug':slug,'title':workspace_info.get('title') or slug,
              'target_root':'kristals/'+slug, 'entrypoint':'AI_START_HERE.md',
              'state_ref':surface['state_ref'],
              'state_logical_commitment':surface['state_logical_commitment'],
              'surface_digest':digest,'file_count':len(ordered),
              'total_bytes':sum(x['size'] for x in ordered),
              'materialization_object_count':len(obj),'files':ordered,'policy':POLICY}
    path=target/'.kristal/sync-manifest.json'
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return {'slug':slug,'title':manifest['title'],'path':'kristals/'+slug,
            'entrypoint':'kristals/'+slug+'/AI_START_HERE.md',
            'state_ref':manifest['state_ref'],
            'state_logical_commitment':manifest['state_logical_commitment'],
            'surface_digest':digest,'file_count':len(ordered),
            'total_bytes':manifest['total_bytes'],
            'materialization_object_count':len(obj)}


def prepare_private_collection(*, locals_root: Path, kit_script: Path, output: Path,
                               slugs: list[str], write_private: bool=False,
                               build_on_copy: bool=False) -> dict:
    """Dry by default. With write_private, creates new independent output only.

    This is NOT a publish, C1 approval, C2 grant, or upload/commit to GitHub.
    """
    locals_root=Path(locals_root).expanduser().resolve()
    kit_script=Path(kit_script).expanduser().resolve()
    output=Path(output).expanduser().resolve()
    if not locals_root.is_dir() or not kit_script.is_file():
        raise ManagerError('Locals root / trusted Kit script missing')
    if not slugs or len(set(slugs))!=len(slugs) or any(not SLUG.fullmatch(s) for s in slugs):
        raise ManagerError('Select unique explicit lowercase slugs')
    if output.exists() or _inside_git_tree(output):
        raise ManagerError('Output must be NEW and outside every Git checkout')
    if (write_private and not output.parent.is_dir()) or output.is_relative_to(locals_root) or locals_root.is_relative_to(output):
        raise ManagerError('Output must be outside the source root and have an existing parent')
    sources=[]
    for slug in slugs:
        matches=[p for p in locals_root.iterdir() if p.is_dir() and not p.is_symlink() and
                 _json(p/'kristal.workspace.json').get('slug')==slug and (p/'kristal.workspace.json').is_file()]
        if len(matches)!=1:raise ManagerError('Exactly one workspace is required for slug: '+slug)
        _safe_tree(matches[0]);sources.append(matches[0])
    report={'status':'DRY_RUN' if not write_private else 'PRIVATE_CANDIDATE_ONLY',
            'authorization':'NOT_ESTABLISHED','public_write':False,
            'output':str(output),'slugs':slugs,'build_on_temporary_copies':build_on_copy}
    if not write_private:return report
    with tempfile.TemporaryDirectory(prefix='kristal-private-candidate-',dir=output.parent) as td:
        temp=Path(td)
        collection=temp/'payload'
        indexed=collection/'kristals';indexed.mkdir(parents=True)
        rows=[_make_one(kit_script,folder,indexed,slug,build_copy=build_on_copy)
              for folder,slug in zip(sources,slugs)]
        rows.sort(key=lambda x:(x['slug'].encode('utf8'),x['path'].encode('utf8')))
        projection={'format':'kristal.github-collection-index/1.0','kristals':rows}
        index={**projection,'count':len(rows),'index_digest':_hash(_canonical(projection)),
               'note':'Derived navigation index for GitHub/AI discovery; not semantic authority.'}
        (indexed/'index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        (collection/'STAGING_ONLY.txt').write_text(
            'PRIVATE CANDIDATE. NOT C1/C2 APPROVED. NEVER PUSH OR COPY TO A PUBLIC REPOSITORY WITHOUT INDEPENDENT AUTHORIZATION.\n',encoding='utf8')
        # C3 does not scan STAGING_ONLY at repository root; review it and strip it
        # only after a genuine independent C1/C2 approval before public intake.
        collection.rename(output)
    report['index_digest']=index['index_digest']
    report['files_count']=sum(x['file_count'] for x in rows)
    return report
