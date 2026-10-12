"""Export authentic historical Manager runtime files for REVIEW ONLY.

Requires a local Git clone with the historical objects. Does not write back to the
working repository, overwrite files, fetch from remote, or authorize sync.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import hashlib
import subprocess
import sys

COMMIT='237b1b539332da5d87bed4b185ea03794aad1057'
BLOBS={
 'kristal_manager/__init__.py':'eff04c667b15b9e50315502ae9042b6bb926891f',
 'kristal_manager/core.py':'425db76cfb59e257c778b8ec448dbe722ffe0c42',
 'kristal_manager/gui.py':'4524ef59b3131ba743501b39c9076a1d5671832f',
 'kristal_manager/publication_gate.py':'1470c0416e17c6158d4543d3bc9d84d741d067f1',
}

def git(repo:Path,*args) -> bytes:
    r=subprocess.run(['git','-C',str(repo),*args],capture_output=True,timeout=30)
    if r.returncode:
        raise RuntimeError('Local Git object unavailable or invalid. '+r.stderr.decode(errors='replace')[:220])
    return r.stdout

def export(repo:Path,destination:Path):
    repo=repo.expanduser().resolve()
    dest=destination.expanduser().absolute()
    if not (repo/'.git').exists():raise RuntimeError('The source must be a local Git clone with history, not an extracted ZIP.')
    if dest.exists():raise RuntimeError('Destination already exists. Refusing to overwrite.')
    payload={}
    for path,sha in BLOBS.items():
        value=git(repo,'show',f'{COMMIT}:{path}')
        actual=hashlib.sha1(f'blob {len(value)}\0'.encode()+value).hexdigest()
        if actual!=sha:raise RuntimeError(f'Unexpected historical blob: {path}')
        payload[path]=value
    for path,data in payload.items():
        target=dest/path
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
    print(f'Exported {len(payload)} verified historical files to {dest}')
    print('The original Git repository was not modified. Review and test before integration.')


def main(argv=None):
    ap=argparse.ArgumentParser(description='Export known historical Manager backend from a local Git clone; no remote activity')
    ap.add_argument('--repository',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args(argv)
    try:export(args.repository,args.output)
    except Exception as e:ap.exit(2,f'ERROR: {e}\n')

if __name__=='__main__':main()
