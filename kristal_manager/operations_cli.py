"""Headless entrypoint for the same workflows as the Manager control center."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from .central_store import (database_path, remember_workspaces, record_analysis,
                            restore_rows, status_counts, record_arketype_batch,
                            import_legacy_diagnostic_csv)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Kristal Manager — index local consolidé (aucune publication)')
    actions = parser.add_subparsers(dest='action', required=True)
    for name in ('inventorier','diagnostiquer','analyser','etat'):
        p = actions.add_parser(name)
        p.add_argument('--root', type=Path, required=True, help='Dossier locals')
        if name=='diagnostiquer':p.add_argument('--max', type=int, default=None, dest='limit')
    p=actions.add_parser('importer-arketype');p.add_argument('rapport',type=Path)
    p=actions.add_parser('importer-anciens-diag');p.add_argument('bilan',type=Path);p.add_argument('--root',type=Path,required=True)
    opts=parser.parse_args(argv)
    try:
        if opts.action=='inventorier':
            from .core import scan_roots
            rows=scan_roots([opts.root])
            remember_workspaces(rows)
            restore_rows(rows)
            result={'kristals':len(rows),'index':str(database_path()),
                    'diagnostics_actuels':sum(bool(x.get('diag_report')) for x in rows)}
        elif opts.action=='diagnostiquer':
            from .diagnostics_batch import run_folder
            result=run_folder(opts.root,limit=opts.limit,
                              on_progress=lambda n,total,name,status:print(f'{n}/{total} {name}: {status}',flush=True))
            result={key:result[key] for key in ('total','counts','report_directory','qualification')}
        elif opts.action=='analyser':
            from .global_analysis import analyze_all
            result=analyze_all(opts.root)
            remember_workspaces(result['inventory'])
            record_analysis(result['global_report'])
            result={'counts':result['global_report'].get('counts'),
                    'report_directory':str(result.get('report_directory')),
                    'index':str(database_path())}
        elif opts.action=='etat':
            result=status_counts(opts.root)
            result['index']=str(database_path())
        elif opts.action=='importer-arketype':
            if opts.rapport.stat().st_size > 20*1024*1024:
                raise ValueError('Rapport Arketype trop volumineux')
            data=json.loads(opts.rapport.read_text('utf-8-sig'))
            result={'observations_arketype_importees':record_arketype_batch(data),'index':str(database_path()),
                    'qualification':'NOT_ESTABLISHED'}
        elif opts.action=='importer-anciens-diag':
            result=import_legacy_diagnostic_csv(opts.bilan,opts.root)
        else:
            parser.error('Action inconnue')
        print(json.dumps(result,ensure_ascii=False,indent=2,default=str))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, 'Erreur : ' + str(exc) + '\n')

if __name__=='__main__':
    raise SystemExit(main())
