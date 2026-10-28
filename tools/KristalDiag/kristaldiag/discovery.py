from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from .utils import json_files,read_json,relpath

@dataclass
class JsonArtifact:
    path:Path
    rel:str
    data:dict[str,Any]
    artifact_type:str|None
    schema_version:str|None

@dataclass
class Inventory:
    root:Path
    artifacts:list[JsonArtifact]=field(default_factory=list)
    parse_errors:list[tuple[str,str]]=field(default_factory=list)
    by_type:dict[str,list[JsonArtifact]]=field(default_factory=dict)
    manifests:list[JsonArtifact]=field(default_factory=list)
    implementation_manifest:JsonArtifact|None=None
    is_standard_repo:bool=False
    scan_limit_reached:bool=False
    def get(self,typ):return self.by_type.get(typ,[])

def discover(root:Path, *, max_files:int=10000)->Inventory:
    root=root.resolve(); inv=Inventory(root=root)
    scan_root=root if root.is_dir() else root.parent
    inv.is_standard_repo=(scan_root/'schemas'/'v7').is_dir() and (scan_root/'schemas'/'v9').is_dir() and (scan_root/'schemas'/'v6'/'kristal-state.schema.json').is_file()
    scanned=0
    for p in json_files(root,max_files=max_files+1):
        scanned+=1
        if scanned>max_files:
            inv.scan_limit_reached=True
            break
        try:data=read_json(p)
        except Exception as e:
            inv.parse_errors.append((relpath(p,scan_root),f'{type(e).__name__}: {e}'));continue
        if not isinstance(data,dict):continue
        art=JsonArtifact(p,relpath(p,scan_root),data,data.get('artifact_type'),str(data.get('schema_version')) if data.get('schema_version') is not None else None)
        inv.artifacts.append(art)
        if art.artifact_type:inv.by_type.setdefault(art.artifact_type,[]).append(art)
        if art.artifact_type=='kristall_manifest':inv.manifests.append(art)
        if data.get('schema')=='kristaldiag.implementation.v1':inv.implementation_manifest=art
    return inv


def inventory_to_data(inv: Inventory, scan_root: Path) -> dict[str, Any]:
    return {
        'schema': 'kristaldiag.inventory-cache.v1',
        'scan_root': str(scan_root.resolve()),
        'root': str(inv.root.resolve()),
        'parse_errors': inv.parse_errors,
        'is_standard_repo': inv.is_standard_repo,
        'scan_limit_reached': inv.scan_limit_reached,
        'artifacts': [
            {
                'rel': a.rel,
                'data': a.data,
                'artifact_type': a.artifact_type,
                'schema_version': a.schema_version,
            }
            for a in inv.artifacts
        ],
    }


def inventory_from_data(data: dict[str, Any], root: Path) -> Inventory:
    root = root.resolve()
    scan_root = root if root.is_dir() else root.parent
    inv = Inventory(root=root)
    inv.parse_errors = [(str(x[0]), str(x[1])) for x in (data.get('parse_errors') or []) if isinstance(x, (list, tuple)) and len(x) >= 2]
    inv.is_standard_repo = bool(data.get('is_standard_repo'))
    inv.scan_limit_reached = bool(data.get('scan_limit_reached'))
    for row in data.get('artifacts') or []:
        if not isinstance(row, dict) or not isinstance(row.get('rel'), str) or not isinstance(row.get('data'), dict):
            continue
        rel = row['rel']
        p = scan_root / Path(*rel.split('/'))
        art = JsonArtifact(p, rel, row['data'], row.get('artifact_type'), row.get('schema_version'))
        inv.artifacts.append(art)
        if art.artifact_type:
            inv.by_type.setdefault(art.artifact_type, []).append(art)
        if art.artifact_type == 'kristall_manifest':
            inv.manifests.append(art)
        if art.data.get('schema') == 'kristaldiag.implementation.v1':
            inv.implementation_manifest = art
    return inv
