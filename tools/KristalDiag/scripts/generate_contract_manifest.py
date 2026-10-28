#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from kristaldiag import VERSION,STANDARD_TARGET
RES=ROOT/'kristaldiag'/'resources'
INCLUDE=('contracts','tck','locks','baseline')
files={}
for top in INCLUDE:
    d=RES/top
    if not d.exists():continue
    for p in sorted(d.rglob('*')):
        if p.is_file() and p.name!='contract-manifest.json':
            files[p.relative_to(RES).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
manifest={'schema':'kristaldiag.contract-manifest.v2','tool_version':VERSION,'kristal_standard_target':STANDARD_TARGET,'files':files}
text=json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=False)+'\n'
(RES/'contract-manifest.json').write_text(text,encoding='utf-8')
(ROOT/'contracts'/'contract-manifest.json').write_text(text,encoding='utf-8')
print(f'KristalDiag contract manifest: {len(files)} files')
