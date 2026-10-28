#!/usr/bin/env python3
from pathlib import Path
root=Path(__file__).resolve().parents[1]
pkg=root/'kristaldiag/resources'
pairs=[
 (root/'contracts/v7',pkg/'contracts/v7'),(root/'contracts/v6',pkg/'contracts/v6'),
 (root/'contracts/v8',pkg/'contracts/v8'),(root/'contracts/v9',pkg/'contracts/v9'),
 (root/'contracts/v10',pkg/'contracts/v10'),(root/'contracts/github',pkg/'contracts/github'),
 (root/'tck/v7',pkg/'tck/v7'),(root/'tck/v6',pkg/'tck/v6'),(root/'tck/v8',pkg/'tck/v8'),
 (root/'tck/v9/vectors',pkg/'tck/v9/vectors'),(root/'tck/v9/workloads',pkg/'tck/v9/workloads'),
 (root/'tck/v10/vectors',pkg/'tck/v10/vectors'),(root/'tck/v10/bundle',pkg/'tck/v10/bundle'),(root/'tck/v10/github',pkg/'tck/v10/github'),
 (root/'tck/jcs',pkg/'tck/jcs')]
bad=[]
for a,b in pairs:
    an={p.name:p.read_bytes() for p in a.iterdir() if p.is_file()};bn={p.name:p.read_bytes() for p in b.iterdir() if p.is_file()}
    if an!=bn:bad.append((str(a),str(b),sorted(set(an)^set(bn))))
if bad:
    print('MIRROR MISMATCH',bad);raise SystemExit(1)
print('KristalDiag contract/TCK mirrors: PASS')
