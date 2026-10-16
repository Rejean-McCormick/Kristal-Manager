"""Offline-first console. Remote mutation features are intentionally unavailable."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .core import scan_roots, detect_kristal, ManagerError
from .inventory import inventory,save_private_inventory,konstellation_preview
from .operational import assess_local

def main(argv=None):
    parser=argparse.ArgumentParser(prog='kristal-manager',description='Read-only local Kristal inventory and Konstellation metadata export')
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('scan','export'):
        p=sub.add_parser(name,help='Inspect local workspaces without modifying their content')
        p.add_argument('roots',nargs='+',type=Path,help='Existing roots to scan recursively')
        p.add_argument('--verify-sources',action='store_true',help='Verify registered source bytes for each workspace')
        if name=='export':
            p.add_argument('--output',type=Path,required=True,help='Local restricted JSON output file')
            p.add_argument('--overwrite',action='store_true',help='Replace existing file (explicit approval)')
            p.add_argument('--include-paths',action='store_true',help='Include absolute local paths (sensitive)')
    p=sub.add_parser('export-konstellation',help='Explicit local KNAV preview (not a signed access grant)')
    p.add_argument('roots',nargs='+',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--principal-id',action='append',required=True,help='Explicitly authorized local principal (repeat as needed)')
    p.add_argument('--overwrite',action='store_true')
    p=sub.add_parser('verify',help='Read-only operational assessment: Discovery bytes and optionally Framework v9 state')
    p.add_argument('workspace',type=Path)
    p.add_argument('--framework-root',type=Path,help='Explicit path to a TRUSTED exact Framework v10 reference checkout')
    p.add_argument('--node',default='node',help='Node.js executable for explicit Framework verification')
    p=sub.add_parser('inspect',help='Inspect one local workspace (no domain file contents)')
    p.add_argument('workspace',type=Path)
    p.add_argument('--verify-discovery',action='store_true',help='Read source bytes to verify Kit 3.3 fingerprint (can be slow)')
    args=parser.parse_args(argv)
    try:
        if args.command=='scan':
            result=inventory(args.roots,verify_sources=args.verify_sources)
        elif args.command=='export':
            result=inventory(args.roots,include_paths=args.include_paths,verify_sources=args.verify_sources)
            dest=save_private_inventory(result,args.output,overwrite=args.overwrite)
            print(f'Saved {result["record_count"]} local inventory records to {dest} (not published).')
            return 0
        elif args.command=='export-konstellation':
            result=konstellation_preview(args.roots,allowed_principals=args.principal_id)
            dest=save_private_inventory(result,args.output,overwrite=args.overwrite)
            print(f'Saved {len(result["entries"])} KNAV preview entries to {dest} (private, not published).')
            return 0
        elif args.command=='verify':
            result=assess_local(args.workspace,framework_root=args.framework_root,node_executable=args.node)
        else:
            result=detect_kristal(args.workspace)
            if result is None:raise ManagerError('No local Kristal workspace found at this path.')
            if args.verify_discovery:
                from .discovery import inspect_discovery
                result['discovery']=inspect_discovery(args.workspace,verify_sources=True,
                    state_ref=result.get('declared_state_ref') or result.get('state_ref'))
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if args.command=='verify' and result['operational_result'] in ('BLOCKED','ATTENTION_REQUIRED'):
            return 3
        return 0
    except (ManagerError,OSError,ValueError) as e:
        parser.exit(2,f'ERROR: {e}\n')

if __name__=='__main__':
    raise SystemExit(main())
