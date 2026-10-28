#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from kristaldiag import VERSION,STANDARD_TARGET
EXCLUDE={'.git','.pytest_cache','__pycache__','.kristaldiag','.levelupdiag','.venv','venv','build','dist'}
files={}
for p in sorted(ROOT.rglob('*'),key=lambda x:x.relative_to(ROOT).as_posix()):
    if not p.is_file() or p.name=='REPO_MANIFEST.json':continue
    rel=p.relative_to(ROOT)
    if any(x in EXCLUDE or x.endswith('.egg-info') for x in rel.parts):continue
    b=p.read_bytes();files[rel.as_posix()]={'sha256':hashlib.sha256(b).hexdigest(),'size':len(b)}
out={'schema':'kristaldiag.repo-manifest.v1','name':'KristalDiag','version':VERSION,'kristal_standard_target':STANDARD_TARGET,'file_count':len(files),'files':files}
(ROOT/'REPO_MANIFEST.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(f'REPO_MANIFEST.json: {len(files)} files')
