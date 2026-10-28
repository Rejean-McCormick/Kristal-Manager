from __future__ import annotations
import hashlib, json, os, shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IGNORE_DIRS={'.git','.kristaldiag','node_modules','.venv','venv','__pycache__','.pytest_cache','.mypy_cache','dist','build'}

def utc_now()->str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

def run_id()->str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+os.urandom(4).hex()

def read_json(path:Path)->Any:
    return json.loads(path.read_text(encoding='utf-8'))

def write_json(path:Path, data:Any):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,sort_keys=False)+'\n',encoding='utf-8')

def sha256_bytes(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def relpath(path:Path, root:Path)->str:
    try:return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:return str(path)

def json_files(root:Path, *, max_files:int=10000):
    if root.is_file():
        if root.suffix.lower()=='.json': yield root
        return
    count=0
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:]=[d for d in dirs if d not in IGNORE_DIRS and not Path(base,d).is_symlink()]
        for name in files:
            if not name.lower().endswith('.json'):continue
            p=Path(base,name)
            if p.is_symlink(): continue
            yield p
            count+=1
            if count>=max_files:return

def safe_copytree(src:Path,dst:Path):
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(src,dst)


def fingerprint_tree(root:Path, *, exclude_roots:tuple[Path,...]=(), max_files:int=50000):
    """Content fingerprint of a target tree for read-only mutation detection.

    Symlinks and common generated/control directories are ignored. The return
    value is ``(mapping, limit_reached)`` where mapping keys are paths relative
    to the scanned target root (or the filename for a single-file target).
    """
    root=root.resolve()
    excludes=tuple(x.resolve() for x in exclude_roots)
    def excluded(p:Path)->bool:
        rp=p.resolve()
        for x in excludes:
            try:
                rp.relative_to(x);return True
            except ValueError:
                pass
        return False
    if root.is_file():
        if root.is_symlink() or excluded(root):return {},False
        return {root.name:sha256_file(root)},False
    out={};count=0;limit=False
    for base,dirs,files in os.walk(root,followlinks=False):
        b=Path(base)
        kept=[]
        for d in dirs:
            q=b/d
            if d in IGNORE_DIRS or q.is_symlink() or excluded(q):continue
            kept.append(d)
        dirs[:]=kept
        for name in sorted(files):
            q=b/name
            if q.is_symlink() or excluded(q):continue
            if count>=max_files:
                limit=True;return out,limit
            try:out[relpath(q,root)]=sha256_file(q)
            except (OSError,PermissionError):out[relpath(q,root)]='<unreadable>'
            count+=1
    return out,limit
