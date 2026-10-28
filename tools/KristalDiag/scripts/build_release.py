#!/usr/bin/env python3
from __future__ import annotations
import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from kristaldiag import VERSION, STANDARD_TARGET

EXCLUDED_PARTS = {
    '.git', '.pytest_cache', '__pycache__', '.kristaldiag', '.levelupdiag',
    '.venv', 'venv', 'build', 'dist'
}
EXCLUDED_NAMES = {'SMARTDUMP_INDEX.txt'}
FIXED_DT = (2026, 10, 6, 0, 0, 0)


def included_files():
    for p in sorted(ROOT.rglob('*'), key=lambda x: x.relative_to(ROOT).as_posix()):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if p.name in EXCLUDED_NAMES:
            continue
        if any(part in EXCLUDED_PARTS or part.endswith('.egg-info') for part in rel.parts):
            continue
        if p.suffix == '.pyc':
            continue
        yield p, rel


def add_bytes(zf: zipfile.ZipFile, arcname: str, data: bytes, executable: bool = False):
    zi = zipfile.ZipInfo(arcname, FIXED_DT)
    zi.create_system = 3
    mode = 0o755 if executable else 0o644
    zi.external_attr = (stat.S_IFREG | mode) << 16
    zi.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(zi, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build(output: Path):
    prefix = f'KristalDiag-{VERSION}'
    entries = list(included_files())
    with zipfile.ZipFile(output, 'w') as zf:
        for p, rel in entries:
            executable = p.suffix == '.py' and (rel.parts[0] == 'scripts' or rel.name in {'kristaldiag.py', 'levelupdiag.py'})
            add_bytes(zf, f'{prefix}/{rel.as_posix()}', p.read_bytes(), executable)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return {'version': VERSION, 'standard_target': STANDARD_TARGET, 'files': len(entries), 'sha256': digest, 'bytes': output.stat().st_size}


def main():
    ap = argparse.ArgumentParser(description='Build a deterministic KristalDiag source release ZIP.')
    ap.add_argument('output', nargs='?', default=str(ROOT / 'dist' / f'KristalDiag-{VERSION}.zip'))
    args = ap.parse_args()
    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    result = build(out)
    print(json.dumps({'output': str(out), **result}, indent=2))

if __name__ == '__main__':
    main()
