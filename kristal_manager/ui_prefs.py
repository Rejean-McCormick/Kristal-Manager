"""Local UI preferences only; never written inside source Kristals."""
from __future__ import annotations
import json
import os
from pathlib import Path

WINDOWS_LOCALS = r'C:\mycode\Kristal\locals'


def settings_path() -> Path:
    if os.name == 'nt' and os.environ.get('LOCALAPPDATA'):
        return Path(os.environ['LOCALAPPDATA']) / 'Kristal-Manager' / 'preferences.json'
    return Path.home() / '.config' / 'kristal-manager' / 'preferences.json'


def load_settings(path: Path | None = None) -> dict:
    try:
        data = json.loads((path or settings_path()).read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (ValueError, OSError, TypeError):
        return {}


def default_root(settings: dict | None = None, *, windows: bool | None = None,
                 exists=None, home: Path | None = None) -> str:
    """Remember actual working folder; prefer user's C:\\mycode tree on Windows."""
    settings = settings if settings is not None else load_settings()
    win = (os.name == 'nt') if windows is None else windows
    exists = exists or (lambda p: Path(p).is_dir())
    home = Path.home() if home is None else home
    override = os.environ.get('KRISTAL_LOCALS')
    if override and exists(override):
        return str(Path(override))
    recent = settings.get('last_root')
    if isinstance(recent, str) and recent and exists(recent):
        return recent
    if win:
        if exists(WINDOWS_LOCALS):
            return WINDOWS_LOCALS
        for fallback in (home / 'mycode' / 'Kristal' / 'locals',):
            if exists(fallback):
                return str(fallback)
        return WINDOWS_LOCALS
    for fallback in (home / 'mycode' / 'Kristal' / 'locals', home):
        if exists(fallback):
            return str(fallback)
    return str(home)


def save_settings(settings: dict, path: Path | None = None) -> None:
    target = path or settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    import uuid
    tmp = target.with_name(target.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        tmp.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(target)
    finally:
        tmp.unlink(missing_ok=True)


def preserve_rows(old_rows: list[dict], fresh_rows: list[dict], *, scanned_paths: set[str] | None = None) -> list[dict]:
    """Keep existing local checks and catalogue records, scoped to their exact path."""
    old = {r['path']: r for r in old_rows}
    output = []
    for row in fresh_rows:
        merged = dict(row)
        previous = old.get(row['path'])
        if previous:
            unchanged = all(previous.get(k) == row.get(k) for k in
                            ('state_ref', 'state_commitment', 'state_blob_digest', 'workspace_format'))
            if unchanged and 'operational_assessment' in previous:
                merged['operational_assessment'] = previous['operational_assessment']
            if 'content_summary' in previous and (scanned_paths is None or row['path'] not in scanned_paths):
                merged['content_summary'] = previous['content_summary']
        output.append(merged)
    return output
