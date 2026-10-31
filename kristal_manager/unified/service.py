"""One application service for inventory, content, diagnostic and structural evidence.

No Git, publishing, activation, or modification to source workspaces.
"""
from __future__ import annotations
from pathlib import Path
import json
from . import repository as store
from .. import central_store
from ..workspace_tools import is_historical


def inventory(root: str | Path, *,db=None) -> dict:
    from ..core import scan_roots
    target=Path(root).expanduser().resolve(strict=True)
    run=store.start_run('Discovery',root=target,db=db)
    try:
        rows=[r for r in scan_roots([target]) if not r.get('hidden_auxiliary') and not is_historical(r)]
        central_store.remember_workspaces(rows,db=db)
        for index,row in enumerate(rows,1):
            payload={'format':'kristal.manager-inventory/2.0',
                     'title':row.get('title'),'readiness':row.get('readiness'),
                     'state_ref':row.get('state_ref'),'discovery':row.get('discovery'),
                     'qualification':'NOT_ESTABLISHED'}
            central_store.record(row['path'],'inventory',payload,
                 profile='local',status=str(row.get('readiness') or 'UNKNOWN'),db=db,run_id=run)
            store.set_progress(run,index,db=db)
        store.finish_run(run,'COMPLETED',processed=len(rows),db=db)
        return {'run_id':run,'workspaces':len(rows),'index':str(store._dbpath(db))}
    except Exception as exc:
        store.finish_run(run,'FAILED',error=str(exc),db=db)
        raise


def analyze(root: str | Path, *,db=None,update_catalogue=True,verify_locally=False) -> dict:
    from ..global_analysis import analyze_all
    target=Path(root).expanduser().resolve(strict=True)
    run=store.start_run('GlobalAnalysis',root=target,db=db)
    try:
        result=analyze_all(target,update_catalogue=update_catalogue,
                           verify_locally=verify_locally)
        central_store.remember_workspaces(result['inventory'],db=db)
        count=central_store.record_analysis(result['global_report'],db=db,run_id=run)
        store.finish_run(run,'COMPLETED',processed=count,
                         directory=result['report_directory'],db=db)
        return {'run_id':run,'workspaces':count,'counts':result['global_report'].get('counts',{}),
                'report_directory':result['report_directory'],
                'problem_archive':result.get('problem_archive')}
    except Exception as exc:
        store.finish_run(run,'FAILED',error=str(exc),db=db)
        raise


def diagnose(root: str | Path, *,db=None,limit=None,on_progress=None,output_dir=None,cancel_event=None) -> dict:
    from ..diagnostics_batch import run_folder
    return run_folder(root,db=db,limit=limit,on_progress=on_progress,output_dir=output_dir,cancel_event=cancel_event)


def import_arketype(file: str | Path, *,db=None) -> dict:
    target=Path(file).expanduser().resolve(strict=True)
    if not target.is_file() or target.stat().st_size>32*1024*1024:
        raise ValueError('Rapport ARK absent ou trop grand')
    report=json.loads(target.read_text('utf-8-sig'))
    if not isinstance(report,dict) or not isinstance(report.get('results'),list):
        raise ValueError('Format Arketype structural-batch attendu')
    run=store.start_run('ArketypeStructure',root=target.parent,db=db,total=len(report['results']))
    try:
        count=central_store.record_arketype_batch(report,db=db,run_id=run)
        store.finish_run(run,'COMPLETED',processed=count,directory=target.parent,db=db)
        return {'run_id':run,'imported':count,'qualification':'NOT_ESTABLISHED'}
    except Exception as exc:
        store.finish_run(run,'FAILED',error=str(exc),db=db)
        raise


def overview(root: str | Path | None=None, *,db=None) -> dict:
    store.backfill_v1(db=db)
    rows=store.dashboard(root=root,db=db)
    return {'format':'kristal.manager-unified-dashboard/2.0',
            'source':str(Path(root).resolve()) if root else None,
            'count':len(rows),'workspaces':rows,
            'runs':store.list_runs(limit=30,db=db),
            'integrity':store.integrity_check(db=db),
            'limits':['Verdicts are engine/profile-specific, not C1/C2/C3 certifications.',
                      'PARTIAL_SCOPE means some sources were not fingerprinted.',
                      'NOT_APPLICABLE does not mean PASS.',
                      'No canonical changes or publication performed.']}


def export(root: str | Path | None, output: str | Path, *,db=None) -> str:
    target=Path(output).expanduser().resolve()
    base=Path(root).expanduser().resolve() if root else None
    if base and (target==base or target.is_relative_to(base)):
        raise ValueError('Rapport refusé à l’intérieur du dossier source')
    target.parent.mkdir(parents=True,exist_ok=True)
    content=json.dumps(overview(root,db=db),ensure_ascii=False,indent=2)+'\n'
    tmp=target.with_name(target.name+'.tmp')
    tmp.write_text(content,encoding='utf-8');tmp.replace(target)
    return str(target)


def import_diagnostic_report(file: str | Path, root: str | Path, *, db=None) -> dict:
    """Import an old Manager/KristalDiag JSON as *unverified historical evidence*.

    The imported file cannot self-assert CURRENT merely by carrying a matching
    fingerprint. Authoritative CURRENT evidence only comes from a trusted local run.
    """
    source=Path(root).expanduser().resolve(strict=True)
    target=Path(file).expanduser().resolve(strict=True)
    if not target.is_file() or target.stat().st_size > 16*1024*1024:
        raise ValueError('Rapport absent ou trop volumineux')
    data=json.loads(target.read_text('utf-8-sig'))
    if not isinstance(data,dict):raise ValueError('JSON objet attendu')
    fmt=data.get('format') or data.get('schema')
    if fmt=='kristal.manager-diagnostic-batch/1.0':
        records=data.get('results')
        if not isinstance(records,list) or len(records)>1000:raise ValueError('Bilan invalide')
    elif fmt in ('kristal.manager-kristaldiag/1.0','kristaldiag.summary.v1'):
        records=[data]
    else:raise ValueError('Format de diagnostic non pris en charge')
    run=store.start_run('DiagnosticImport',root=source,version=str(fmt),total=len(records),db=db)
    count=0;skipped=0
    try:
        for row in records:
            if not isinstance(row,dict):skipped+=1;continue
            candidate=row.get('workspace') or row.get('path') or row.get('target_root')
            if not candidate:skipped+=1;continue
            workspace=Path(candidate).expanduser().resolve()
            if workspace.parent!=source or not (workspace/'kristal.workspace.json').is_file():
                skipped+=1;continue
            profile=str(row.get('profile') or data.get('profile') or '')
            evidence={'format':'kristal.manager-legacy-diagnostic/0.2',
                      'workspace':str(workspace),
                      'verdict':row.get('verdict') or 'UNKNOWN',
                      'profile':profile,'executed_at':store.utcnow(),
                      'process_status':'IMPORTED_UNVERIFIED',
                      'raw_report_ref':str(target),
                      'external_report':row if fmt!='kristal.manager-diagnostic-batch/1.0' else None,
                      'original_execution_date':row.get('executed_at') or data.get('created_at'),
                      'input_fingerprint':{},'qualification':'NOT_ESTABLISHED',
                      'explanation':'Import historique, source non authentifiée : jamais CURRENT automatiquement'}
            central_store.record_diagnostic(workspace,evidence,db=db,run_id=run)
            count+=1
            store.set_progress(run,count,db=db)
        store.finish_run(run,'COMPLETED',processed=count,directory=target.parent,db=db)
        return {'run_id':run,'imported':count,'skipped':skipped,'freshness':'UNVERIFIED'}
    except Exception as exc:
        store.finish_run(run,'FAILED',processed=count,error=str(exc),db=db)
        raise
