"""Use Manager's *existing, bundled* KristalDiag for the folder workflow.

No shell, no re-run on UI refresh, no source writes. V9 is skipped when absent;
there is no invented V9 compliance on native-only workspaces.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import csv
import json
import os
import uuid

from .central_store import record_diagnostic, remember_workspaces
from .unified.repository import start_run, finish_run, set_progress
from .core import scan_roots
from .diag_bridge import run_official_diagnostic, evidence_directory, _fingerprint
from .workspace_tools import is_historical

class BatchCancelled(RuntimeError):
    """Cooperative cancellation. Existing evidence remains intact."""
    pass


def applicable_v9(workspace: str | Path) -> bool:
    root = Path(workspace)
    return any((root / name).is_file() for name in (
        '.kristal/v9/capabilities.json', '.kristal/v9/state-snapshot.json',
        '.kristal/v9/activation.json', '.kristal/v9/logical-artifact.json',
        'build/v9/state-snapshot.json', 'state/state-snapshot.json'))


def _stamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _save_json_atomic(path: Path, payload: dict) -> None:
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def run_folder(root: str | Path, *, profile: str = 'V9-State-Reader',
               limit: int | None = None, output_dir: str | Path | None = None,
               on_progress=None, diag_runner=None, db=None, cancel_event=None) -> dict:
    """Run at most one diagnostic per Kristal, persisting every result immediately."""
    source = Path(root).expanduser().resolve(strict=True)
    if not source.is_dir():
        raise ValueError('Folder not found')
    if profile != 'V9-State-Reader':
        raise ValueError('Only V9-State-Reader is supported for folder diagnostics')
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValueError('limit must be a positive integer')
    output_base = Path(output_dir or (evidence_directory() / 'batch')).expanduser().resolve()
    if output_base == source or output_base.is_relative_to(source):
        raise ValueError('Output folder must be outside Kristal source folder')
    rows = [r for r in scan_roots([source]) if not r.get('hidden_auxiliary') and not is_historical(r)
            and (Path(r['path']) / 'kristal.workspace.json').is_file()]
    rows.sort(key=lambda r: r['path'].casefold())
    if limit:
        rows = rows[:limit]
    remember_workspaces(rows, db=db)
    run_dir = output_base / ('diag-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
    run_dir.mkdir(parents=True, exist_ok=False)
    runner = diag_runner or run_official_diagnostic
    if diag_runner is None and any(applicable_v9(Path(row['path'])) for row in rows):
        from .diag_bridge import bundled_kristaldiag
        import importlib.util
        if not bundled_kristaldiag().is_file():
            raise RuntimeError('KristalDiag intégré absent : tools/KristalDiag/kristaldiag.py')
        if importlib.util.find_spec('jsonschema') is None:
            raise RuntimeError('Dépendance jsonschema manquante. Installer ce prérequis avant le batch.')
    results = []
    run_id = start_run('KristalDiag', profile=profile, root=source, total=len(rows), db=db)
    try:
        for index, row in enumerate(rows, 1):
            if cancel_event is not None and cancel_event.is_set():
                raise BatchCancelled('Batch interrompu à la demande de l’opérateur')
            workspace = Path(row['path'])
            if not applicable_v9(workspace):
                result = {
                    'format': 'kristal.manager-kristaldiag/1.0', 'workspace': str(workspace),
                    'profile': profile, 'executed_at': _stamp(),
                    'verdict': 'NOT_APPLICABLE', 'process_status': 'NOT_EXECUTED',
                    'explanation': 'Aucun état V9 reconnu : diagnostic V9 non applicable, contrat natif à vérifier séparément.',
                    'input_fingerprint': _fingerprint(workspace), 'input_changed_during_run': False,
                    'qualification': 'NOT_ESTABLISHED', 'attestation': 'NOT_VERIFIED',
                }
            else:
                try:
                    result = runner(workspace, profile=profile)
                except Exception as exc:
                    result = {
                        'format': 'kristal.manager-kristaldiag/1.0', 'workspace': str(workspace),
                        'profile': profile, 'executed_at': _stamp(),
                        'verdict': 'EXECUTION_ERROR', 'process_status': 'ERROR',
                        'explanation': (type(exc).__name__ + ': ' + str(exc))[:1000],
                        'input_fingerprint': _fingerprint(workspace), 'input_changed_during_run': False,
                        'qualification': 'NOT_ESTABLISHED', 'attestation': 'NOT_VERIFIED',
                    }
            record_diagnostic(workspace, result, db=db, run_id=run_id)
            set_progress(run_id,index,db=db)
            results.append({'kristal': row.get('title') or workspace.name, 'path': str(workspace),
                            'verdict': result.get('verdict') or 'UNDETERMINED',
                            'process_status': result.get('process_status'),
                            'profile': profile, 'executed_at': result.get('executed_at'),
                            'evidence': result.get('evidence_directory') or '',
                            'explanation': result.get('explanation') or ''})
            if on_progress:
                on_progress(index, len(rows), row.get('title') or workspace.name,
                            str(result.get('verdict') or 'UNDETERMINED'))
        counts = dict(Counter(row['verdict'] for row in results))
        summary = {'format': 'kristal.manager-diagnostic-batch/1.0', 'created_at': _stamp(),
                   'source': str(source), 'profile': profile, 'run_id': run_id, 'total': len(rows),
                   'counts': counts, 'qualification': 'NOT_ESTABLISHED',
                   'report_directory': str(run_dir), 'results': results}
        _save_json_atomic(run_dir / 'BILAN-DIAGNOSTICS.json', summary)
        with (run_dir / 'BILAN-DIAGNOSTICS.csv').open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=('kristal', 'path', 'verdict', 'process_status',
                                                     'profile', 'executed_at', 'evidence', 'explanation'),
                                    delimiter=';')
            writer.writeheader(); writer.writerows(results)
        finish_run(run_id,'COMPLETED',processed=len(rows),directory=run_dir,db=db)
        return summary
    except BaseException as exc:
        # Interrupted/failed batches remain visible in the run journal.
        try:
            finish_run(run_id,'INTERRUPTED' if isinstance(exc,(KeyboardInterrupt,BatchCancelled)) else 'FAILED',
                       processed=len(results),directory=run_dir,error=str(exc),db=db)
        except (OSError,ValueError,RuntimeError):
            pass
        raise
