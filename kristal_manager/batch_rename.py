"""Preview-first batch folder normalization for local Kristals.

Only direct child workspaces with declared metadata are candidates. By default
full ZIP backups are completed before any path mutation. Every operation is
journaled outside the managed root, and a guarded undo is available later.
Never edits files inside a workspace and never overwrites existing names.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import uuid

from .core import ManagerError
from .workspace_tools import plan_rename, standard_folder_name, export_workspace

FORMAT = 'kristal.manager-batch-rename/1.0'


def _now():
    return datetime.now(timezone.utc).isoformat()


def _hash_metadata(folder: Path) -> str:
    return hashlib.sha256((folder / 'kristal.workspace.json').read_bytes()).hexdigest()


@dataclass(frozen=True)
class BatchItem:
    source: Path
    destination: Path | None
    title: str
    status: str      # rename | unchanged | blocked
    reason: str
    metadata_sha256: str | None = None


def preview_batch(scan_root: str | Path) -> list[BatchItem]:
    raw = Path(scan_root).expanduser()
    if raw.is_symlink() or not raw.is_dir():
        raise ManagerError('Root folder is missing or is a symbolic link.')
    root = raw.resolve(strict=True)
    if (root / 'kristal.workspace.json').exists():
        raise ManagerError('Select the parent locals folder, not a single Kristal.')
    result: list[BatchItem] = []
    for path in sorted(root.iterdir(), key=lambda p: p.name.casefold()):
        # Only *direct* workspaces; no recursive traversal of archive/ and snapshots.
        if not path.is_dir() or not (path / 'kristal.workspace.json').is_file():
            continue
        if path.is_symlink() or (path / 'kristal.workspace.json').is_symlink():
            result.append(BatchItem(path, None, path.name, 'blocked', 'Symbolic link not allowed'))
            continue
        try:
            title_data = json.loads((path / 'kristal.workspace.json').read_text(encoding='utf-8'))
            title = str(title_data.get('title') or title_data.get('slug') or path.name)
            dest = path.with_name(standard_folder_name(path))
            digest = _hash_metadata(path)
            if dest.name == path.name:
                result.append(BatchItem(path, dest, title, 'unchanged', 'Already standardized', digest))
            else:
                plan = plan_rename(path, root)
                result.append(BatchItem(path, plan.destination, title, 'rename', '', digest))
        except (ManagerError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            result.append(BatchItem(path, None, path.name, 'blocked', str(exc)))
    # Guard against two declarations resolving to the same target, regardless of FS semantics.
    by_target = {}
    for item in result:
        if item.status == 'rename':
            by_target.setdefault(item.destination.name.casefold(), []).append(item)
    clashes = {name for name, items in by_target.items() if len(items) > 1}
    if clashes:
        result = [BatchItem(i.source, i.destination, i.title, 'blocked', 'Duplicate destination name', i.metadata_sha256)
                  if i.status == 'rename' and i.destination.name.casefold() in clashes else i for i in result]
    return result


def _ensure_reports_dir(output_dir: str | Path, root: Path) -> Path:
    folder = Path(output_dir).expanduser()
    if folder.is_symlink():
        raise ManagerError('Report folder cannot be a symbolic link.')
    folder = folder.resolve(strict=False)
    if folder == root or folder.is_relative_to(root) or root.is_relative_to(folder):
        raise ManagerError('Choose a report folder outside the managed locals folder.')
    folder.mkdir(parents=True, exist_ok=True)
    if not folder.is_dir():
        raise ManagerError('Report folder is inaccessible.')
    return folder


def _save_journal(file: Path, report: dict):
    tmp = file.with_name('.' + file.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with tmp.open('x', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, file)
    finally:
        tmp.unlink(missing_ok=True)


def run_batch(scan_root: str | Path, selected: list[str | Path], report_dir: str | Path,
              *, backup: bool = True) -> dict:
    """Revalidate entire selection and export all ZIP backups *before* first rename.

    A failure during rename attempts guarded automatic rollback of completed moves.
    The durable journal records each step for recovery in another application run.
    """
    if not backup:
        raise ManagerError('ZIP backups are mandatory for batch renaming.')
    raw = Path(scan_root)
    if raw.is_symlink() or not raw.is_dir():
        raise ManagerError('Root folder inaccessible or symbolic link.')
    root = raw.resolve(strict=True)
    names = [str(Path(p).resolve(strict=False)) for p in selected]
    if not names or len(names) != len(set(names)):
        raise ManagerError('Empty selection or duplicate folder names.')
    preview = {str(item.source): item for item in preview_batch(root)}
    picked = []
    for source_name in names:
        item = preview.get(source_name)
        if item is None or item.status != 'rename':
            raise ManagerError(f'Stale preview or ineligible folder: {source_name}')
        picked.append(item)
    # Strict revalidation before any writes.
    for item in picked:
        plan = plan_rename(item.source, root)
        if plan.destination != item.destination or _hash_metadata(item.source) != item.metadata_sha256:
            raise ManagerError(f'Metadata or destination changed: {item.source.name}')
    out = _ensure_reports_dir(report_dir, root)
    run_id = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
    folder = out / f'normalisation-{run_id}'
    folder.mkdir(exist_ok=False)
    report_path = folder / 'journal.json'
    records = [dict(source=str(i.source), destination=str(i.destination), title=i.title,
                    metadata_sha256=i.metadata_sha256, status='pending', backup=None, error=None)
               for i in picked]
    report = dict(format=FORMAT, operation='rename', created_at=_now(), root=str(root),
                  backup_requested=backup, status='preparing', entries=records,
                  warning='Les références absolues externes ne sont pas réécrites.')
    _save_journal(report_path, report)
    try:
        if backup:
            backups_folder = folder / 'backups'
            backups_folder.mkdir()
            for record in records:
                src = Path(record['source'])
                # Export refuses symlinks and non-local source writes.
                dest = backups_folder / (src.name + '.zip')
                export_workspace(src, dest, format='zip')
                record['backup'] = str(dest)
                record['status'] = 'backed_up'
                _save_journal(report_path, report)
        # Backups may take minutes; revalidate all once more before first move.
        for item in picked:
            fresh = plan_rename(item.source, root)
            if fresh.destination != item.destination or _hash_metadata(item.source) != item.metadata_sha256:
                raise ManagerError(f'Kristal changed since backup: {item.source.name}')
        report['status'] = 'running'
        _save_journal(report_path, report)
        for record in records:
            src, dst = Path(record['source']), Path(record['destination'])
            # Persist intent in case the machine shuts down mid-rename.
            record['status'] = 'moving'
            _save_journal(report_path, report)
            fresh = plan_rename(src, root)
            if fresh.destination != dst or _hash_metadata(src) != record['metadata_sha256']:
                raise ManagerError(f'Kristal changed: {src.name}')
            src.rename(dst)
            record['status'] = 'renamed'
            record['renamed_at'] = _now()
            _save_journal(report_path, report)
        report['status'] = 'completed'
    except Exception as exc:
        report['status'] = 'failed'
        report['error'] = str(exc)
        # Recover even a rename that completed just before the journal update.
        for record in reversed(records):
            src, dst = Path(record['source']), Path(record['destination'])
            if record['status'] in ('renamed', 'moving') and dst.is_dir() and not src.exists():
                try:
                    if dst.is_symlink() or _hash_metadata(dst) != record['metadata_sha256']:
                        raise ManagerError('Metadata changed; manual recovery required')
                    dst.rename(src)
                    record['status'] = 'rolled_back'
                except Exception as undo_exc:
                    record['status'] = 'rollback_failed'
                    record['error'] = str(undo_exc)
        _save_journal(report_path, report)
    else:
        _save_journal(report_path, report)
    report['journal_file'] = str(report_path)
    return report


def undo_batch(journal_file: str | Path, *, scan_root: str | Path) -> dict:
    """Rollback known renamed directories; never overwrite or edit source files."""
    path = Path(journal_file).expanduser().resolve(strict=True)
    report = json.loads(path.read_text(encoding='utf-8'))
    root = Path(scan_root).resolve(strict=True)
    if report.get('format') != FORMAT or report.get('operation') != 'rename' or report.get('root') != str(root):
        raise ManagerError('Journal does not match the scanned root.')
    if path.is_relative_to(root):
        raise ManagerError('Journal cannot be inside the source folders.')
    rows = report.get('entries')
    if not isinstance(rows, list):
        raise ManagerError('Journal has no valid list of renames.')
    applicable = []
    # Preflight all paths before any undo, and reject manipulated journal paths.
    for record in reversed(rows):
        if record.get('status') != 'renamed':
            continue
        src, dst = Path(record['source']), Path(record['destination'])
        if src.parent != root or dst.parent != root or src == dst:
            raise ManagerError('Journal paths are outside the authorized root.')
        if src.exists() or not dst.is_dir() or dst.is_symlink():
            raise ManagerError(f'Undo blocked: {src.name} ou {dst.name} existe / manque.')
        if _hash_metadata(dst) != record.get('metadata_sha256'):
            raise ManagerError(f'Métadonnées modifiées depuis le renommage : {dst.name}')
        applicable.append(record)
    if not applicable:
        raise ManagerError('No eligible renamed folders to restore.')
    for record in applicable:
        src, dst = Path(record['source']), Path(record['destination'])
        if src.exists() or not dst.is_dir() or _hash_metadata(dst) != record['metadata_sha256']:
            record['error'] = 'Conflict between preflight and restoration'
            report['status'] = 'undo_partial'
            _save_journal(path, report)
            return report | {'journal_file': str(path)}
        try:
            dst.rename(src)
        except OSError as exc:
            record['error'] = str(exc)
            report['status'] = 'undo_partial'
            _save_journal(path, report)
            return report | {'journal_file': str(path)}
        record['status'] = 'undone'
        record['undone_at'] = _now()
        _save_journal(path, report)
    report['status'] = 'undone'
    _save_journal(path, report)
    return report | {'journal_file': str(path)}
