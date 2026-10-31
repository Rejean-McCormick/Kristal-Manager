"""Public headless entrypoint: python -m kristal_manager.unified.cli ..."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from . import service,repository

def main(argv=None) -> int:
    p=argparse.ArgumentParser(prog='kristal-manager-next',description='Manager vNext: journal unifié, sans publication')
    p.add_argument('--db',type=Path,help='Base opérationnelle facultative')
    commands=p.add_subparsers(dest='action',required=True)
    for name in ('inventorier','analyser','diagnostiquer','etat','exporter'):
        q=commands.add_parser(name);q.add_argument('--root',type=Path,required=True)
        if name=='diagnostiquer':q.add_argument('--max',type=int)
        if name=='exporter':q.add_argument('--out',type=Path,required=True)
    q=commands.add_parser('importer-arketype');q.add_argument('rapport',type=Path)
    q=commands.add_parser('importer-diag');q.add_argument('rapport',type=Path);q.add_argument('--root',type=Path,required=True)
    q=commands.add_parser('historique');q.add_argument('workspace',type=Path);q.add_argument('--type',dest='kind');q.add_argument('--profile');q.add_argument('--max',type=int,default=100)
    q=commands.add_parser('executions');q.add_argument('--max',type=int,default=50)
    commands.add_parser('integrite')
    commands.add_parser('migrer-index')
    q=commands.add_parser('sauvegarder-index');q.add_argument('--out',type=Path,required=True)
    opts=p.parse_args(argv)
    try:
        kws={'db':opts.db}
        if opts.action=='inventorier':result=service.inventory(opts.root,**kws)
        elif opts.action=='analyser':result=service.analyze(opts.root,**kws)
        elif opts.action=='diagnostiquer':result=service.diagnose(opts.root,limit=opts.max,**kws)
        elif opts.action=='etat':result=service.overview(opts.root,**kws)
        elif opts.action=='exporter':result={'file':service.export(opts.root,opts.out,**kws)}
        elif opts.action=='importer-arketype':result=service.import_arketype(opts.rapport,**kws)
        elif opts.action=='importer-diag':result=service.import_diagnostic_report(opts.rapport,opts.root,**kws)
        elif opts.action=='historique':result=repository.history(opts.workspace,kind=opts.kind,profile=opts.profile,limit=opts.max,**kws)
        elif opts.action=='executions':result=repository.list_runs(limit=opts.max,**kws)
        elif opts.action=='integrite':result=repository.integrity_check(**kws)
        elif opts.action=='migrer-index':
            backup=repository.backup_database(**kws)
            result={'backup':backup,'imported':repository.backfill_v1(**kws),
                    'integrity':repository.integrity_check(**kws)}
        elif opts.action=='sauvegarder-index':result={'backup':repository.backup_database(destination=opts.out,**kws)}
        else:raise AssertionError(opts.action)
        print(json.dumps(result,ensure_ascii=False,indent=2,default=str))
        return 0
    except (OSError,RuntimeError,ValueError,TypeError) as exc:
        p.exit(1,'Erreur : '+str(exc)+'\n')
if __name__=='__main__':raise SystemExit(main())
