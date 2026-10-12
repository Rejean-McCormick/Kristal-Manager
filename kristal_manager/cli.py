"""Offline-first console. Remote mutation features are intentionally unavailable."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .core import scan_roots, detect_kristal, ManagerError
from .inventory import inventory,save_private_inventory

def main(argv=None):
    parser=argparse.ArgumentParser(prog='kristal-manager',description='Read-only local Kristal inventory and Konstellation metadata export')
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('scan','export'):
        p=sub.add_parser(name,help='Inspect local workspaces without modifying their content')
        p.add_argument('roots',nargs='+',type=Path,help='Existing roots to scan recursively')
        if name=='export':
            p.add_argument('--output',type=Path,required=True,help='Local restricted JSON output file')
            p.add_argument('--overwrite',action='store_true',help='Replace existing file (explicit approval)')
            p.add_argument('--include-paths',action='store_true',help='Include absolute local paths (sensitive)')
    p=sub.add_parser('inspect',help='Inspect one local workspace (no domain file contents)')
    p.add_argument('workspace',type=Path)
    args=parser.parse_args(argv)
    try:
        if args.command=='scan':
            result=inventory(args.roots)
        elif args.command=='export':
            result=inventory(args.roots,include_paths=args.include_paths)
            dest=save_private_inventory(result,args.output,overwrite=args.overwrite)
            print(f'Saved {result["record_count"]} local inventory records to {dest} (not published).')
            return 0
        else:
            result=detect_kristal(args.workspace)
            if result is None:raise ManagerError('No local Kristal workspace found at this path.')
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (ManagerError,OSError,ValueError) as e:
        parser.exit(2,f'ERROR: {e}\n')

if __name__=='__main__':
    raise SystemExit(main())
