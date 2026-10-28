#!/usr/bin/env python3
"""Compatibility shim for former levelupdiag_kristal users.

LevelUpDiag's Kristal-specific harness was consolidated into KristalDiag v7.
This wrapper preserves the common doctor/list/show-config/run/verify-run surface.
"""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from kristaldiag.cli import main as kristal_main
from kristaldiag.config import load_config

def main(argv=None):
    p=argparse.ArgumentParser(prog='levelupdiag',description='Compatibility shim: LevelUpDiag Kristal -> KristalDiag v7')
    p.add_argument('--target')
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('doctor');sub.add_parser('list');sub.add_parser('show-config')
    r=sub.add_parser('run');r.add_argument('selection',nargs='?',default='standard');r.add_argument('--jobs',type=int);r.add_argument('--fail-fast',action='store_true');r.add_argument('--allow-exec',action='store_true')
    v=sub.add_parser('verify-run');v.add_argument('summary')
    a=p.parse_args(argv);target=a.target or '.'
    print('NOTE: levelupdiag_kristal is consolidated into KristalDiag v7; this command is a compatibility shim.',file=sys.stderr)
    if a.cmd=='doctor':return kristal_main(['doctor','--target',target])
    if a.cmd=='list':return kristal_main(['list'])
    if a.cmd=='show-config':
        root=Path(__file__).resolve().parent;cfg=load_config(root,Path(target));print(json.dumps(cfg.data,indent=2,ensure_ascii=False));return 0
    if a.cmd=='run':
        selection=a.selection
        if selection not in {'baseline','standard','deep','release'}:
            print(f'Unknown migrated campaign/level selection: {selection}',file=sys.stderr);return 30
        args=['run',selection,target]
        if a.jobs:args+=['--jobs',str(a.jobs)]
        if a.fail_fast:args+=['--fail-fast']
        if a.allow_exec:args+=['--allow-exec']
        return kristal_main(args)
    if a.cmd=='verify-run':return kristal_main(['verify-run',a.summary])
    return 64

if __name__=='__main__':raise SystemExit(main())
