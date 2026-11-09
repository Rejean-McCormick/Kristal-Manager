"""One *current* editorial decision per workspace, stored outside the Kristals.

Not a historical ledger and never a C1/C2/C3 or publishing authorization.
Decisions become obsolete when the workspace's anchor sources change.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
import uuid

SCHEMA = 'kristal-manager/current-editorial-decisions/1.0'
STATES = ('Ready', 'Needs work', 'Not assessed')
ANCHORS = ('kristal.workspace.json', 'docs/00_INTENT_AND_SCOPE.md',
           'docs/01_SEMANTIC_BOUNDARY.md', 'docs/02_NATIVE_MODEL.md',
           'canon/state.index.json', 'sources/source-catalog.json')
MAX_SOURCE = 128 * 1024 * 1024
MAX_CANON_ARTIFACTS = 2048
MAX_REGISTRY = 2 * 1024 * 1024


def registry_path() -> Path:
    if os.name == 'nt' and os.environ.get('LOCALAPPDATA'):
        return Path(os.environ['LOCALAPPDATA']) / 'Kristal-Manager' / 'editorial-decisions.json'
    return Path.home() / '.config' / 'kristal-manager' / 'editorial-decisions.json'


def _key(row: dict) -> str:
    identity = row.get('state_ref')
    name = row.get('path')
    if not isinstance(identity, str) or not identity or not isinstance(name, str) or not name:
        raise ValueError('A current state identity and workspace path are required')
    return identity + ' | ' + os.path.normcase(os.path.normpath(os.path.abspath(name)))


def source_fingerprint(row: dict) -> str:
    """Digest the current model, scope, index and provenance without writing them."""
    root = Path(str(row.get('path') or ''))
    if not root.is_dir() or root.is_symlink():
        raise ValueError('Workspace unavailable or symlinked')
    h = hashlib.sha256()
    index = root / 'canon' / 'state.index.json'
    if not index.is_file() or index.is_symlink() or index.stat().st_size > MAX_SOURCE:
        raise ValueError('Canonical index unavailable')
    manifest = json.loads(index.read_text('utf-8'))
    artifacts = manifest.get('canonical_artifacts')
    if not isinstance(artifacts, list) or len(artifacts) > MAX_CANON_ARTIFACTS:
        raise ValueError('Canonical artifact list unavailable or too large')
    registered = []
    for item in artifacts:
        rel = item.get('path') if isinstance(item, dict) else None
        if not isinstance(rel, str) or not rel or '\\' in rel or ':' in rel:
            raise ValueError('Unsafe canonical artifact reference')
        parts = Path(rel).parts
        if any(x in ('.', '..', '') for x in parts) or Path(rel).is_absolute():
            raise ValueError('Invalid canonical artifact path')
        registered.append(rel)
    if len(set(registered)) != len(registered):
        raise ValueError('Duplicate canonical artifact reference')
    for rel in (*ANCHORS, *sorted(registered)):
        p = root.joinpath(*rel.split('/'))
        if any(parent.is_symlink() for parent in (p, *p.parents)):
            raise ValueError('Symlinked source is not accepted')
        if not p.is_file() or p.stat().st_size > MAX_SOURCE:
            raise ValueError('Required source missing or oversized: ' + rel)
        h.update(rel.encode('utf-8')); h.update(b'\0')
        with p.open('rb') as file:
            for block in iter(lambda: file.read(1048576), b''):
                h.update(block)
        h.update(b'\0')
    workspace = json.loads((root / ANCHORS[0]).read_text('utf-8'))
    if workspace.get('state_ref') != row.get('state_ref'):
        raise ValueError('State identity does not match live metadata')
    return h.hexdigest()


def load_decisions(path: Path | None = None) -> dict:
    path = path or registry_path()
    if not path.exists():
        return {}
    if path.is_symlink() or path.stat().st_size > MAX_REGISTRY:
        raise ValueError('Unsafe editorial decision file')
    data = json.loads(path.read_text('utf-8'))
    if not isinstance(data, dict) or data.get('schema') != SCHEMA or not isinstance(data.get('decisions'), dict):
        raise ValueError('Invalid editorial decision registry')
    return data['decisions']


def decision_for_row(row: dict, decisions: dict) -> dict | None:
    try:
        item = decisions.get(_key(row))
        if not isinstance(item, dict) or item.get('status') not in STATES:
            return None
        if item.get('fingerprint') != source_fingerprint(row):
            return {'status': 'Not assessed', 'reason': 'Editorial decision outdated — sources changed',
                    'next_action': 'Re-evaluate the current workspace.', 'outdated': True}
        return {'status': item['status'], 'reason': item.get('note') or 'Current editorial decision',
                'next_action': ('Revisit only if the source changes.' if item['status'] == 'Ready'
                                else item.get('note') or 'Review the noted issue.'),
                'outdated': False}
    except (ValueError, OSError, TypeError, json.JSONDecodeError):
        return {'status': 'Not assessed', 'reason': 'Editorial decision could not be verified',
                'next_action': 'Check current workspace files.', 'outdated': True}


def current_editorial_state(row: dict, decisions: dict | None = None) -> dict:
    from .editorial_state import assess_editorial_state
    automated = assess_editorial_state(row)
    if not decisions:
        return automated
    manual = decision_for_row(row, decisions)
    if manual is None:
        return automated
    # Never let a manual "Ready" mask an actual structural/source defect or a
    # workspace explicitly marked as building. Also never promote Framework levels.
    if manual['status'] == 'Ready' and automated['status'] in ('Needs work', 'Building'):
        return automated
    return {**automated, **manual, 'framework_qualification': 'NOT_ESTABLISHED',
            'human_approved': False, 'canonical_changed': False,
            'decision_source': 'current_editorial_note' if not manual.get('outdated') else 'outdated_note'}


def set_decision(row: dict, status: str, note: str = '', *, path: Path | None = None) -> None:
    if status not in STATES:
        raise ValueError('Unsupported editorial status')
    if not isinstance(note, str) or len(note) > 350:
        raise ValueError('Decision note must contain at most 350 characters')
    from .editorial_state import assess_editorial_state
    if status == 'Ready' and assess_editorial_state(row)['status'] in ('Needs work', 'Building'):
        raise ValueError('Cannot mark a building or demonstrably faulty Kristal as ready')
    fingerprint = source_fingerprint(row)
    target = path or registry_path()
    decisions = load_decisions(target)  # invalid existing data must not be overwritten
    decisions[_key(row)] = {'status': status, 'note': note.strip(), 'fingerprint': fingerprint,
                             'saved_utc': datetime.now(timezone.utc).isoformat()}
    _save(target, decisions)


def clear_decision(row: dict, *, path: Path | None = None) -> None:
    target = path or registry_path()
    decisions = load_decisions(target)
    decisions.pop(_key(row), None)
    _save(target, decisions)


def _save(target: Path, decisions: dict) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        raise ValueError('Symlinked editorial registry')
    data = json.dumps({'schema': SCHEMA, 'decisions': decisions}, ensure_ascii=False, indent=2)
    if len(data.encode('utf-8')) > MAX_REGISTRY:
        raise ValueError('Editorial registry exceeds safe size')
    tmp = target.with_name(target.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        tmp.write_text(data, encoding='utf-8')
        tmp.replace(target)
    finally:
        tmp.unlink(missing_ok=True)
