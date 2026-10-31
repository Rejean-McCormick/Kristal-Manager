"""Central, derived operational state for Kristal Manager.

The 127 Kristal workspaces remain authoritative. This separate *small* SQLite
read model survives content-catalog rebuilds and never writes to a workspace.
Every observation retains source, profile, timestamp, evidence and freshness.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
import hashlib
import json
import sqlite3

SCHEMA_VERSION = 2
MAX_RECORD_BYTES = 2 * 1024 * 1024
KINDS = frozenset({'diagnostic', 'analysis', 'inventory', 'arketype', 'verification'})


def database_path() -> Path:
    return Path(__file__).resolve().parents[1] / 'catalogue' / 'kristal-manager-operations.sqlite3'


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _key(root: str | Path) -> str:
    return str(Path(root).expanduser().resolve()).casefold()


def _json(value) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(',', ':'))
    if len(encoded.encode('utf-8')) > MAX_RECORD_BYTES:
        raise ValueError('Observation too large for operational index; keep evidence in its report file.')
    return encoded


def _decode(value):
    try:
        return json.loads(value) if value is not None else None
    except (ValueError, TypeError):
        return None


def _fingerprint(workspace: str | Path) -> dict[str, str]:
    # Reuse the official bridge's limited, explicit state-fingerprint boundary.
    from .diag_bridge import _fingerprint as source_fingerprint
    path = Path(workspace)
    return source_fingerprint(path) if path.is_dir() else {}


@contextmanager
def _connection(db: str | Path | None = None):
    target = Path(db or database_path()).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(target, timeout=20.0) as conn:
        conn.execute('PRAGMA busy_timeout=20000')
        conn.execute('PRAGMA foreign_keys=ON')
        existing_version = conn.execute('PRAGMA user_version').fetchone()[0]
        if existing_version > SCHEMA_VERSION:
            raise RuntimeError('Index Manager créé par une version plus récente : migration nécessaire.')
        # Before the first schema upgrade, snapshot any real v1 database.
        # The source Kristals and heavy content catalogue are not involved.
        if existing_version < SCHEMA_VERSION and conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='observations'").fetchone():
            from .unified.repository import backup_database
            backup_database(db=target, destination=target.with_name(target.name+'.before-v2.backup'))
        conn.execute('''CREATE TABLE IF NOT EXISTS workspaces (
           path_key TEXT PRIMARY KEY, path TEXT NOT NULL, state_ref TEXT,
           title TEXT, readiness TEXT, profile TEXT, observed_at TEXT NOT NULL
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS observations (
           event_id TEXT PRIMARY KEY, path_key TEXT NOT NULL, kind TEXT NOT NULL,
           profile TEXT NOT NULL DEFAULT '', status TEXT, observed_at TEXT NOT NULL,
           source_fingerprint TEXT NOT NULL, payload TEXT NOT NULL,
           FOREIGN KEY (path_key) REFERENCES workspaces(path_key)
        )''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_observations_lookup ON observations(path_key, kind, observed_at DESC)')
        from .unified.repository import ensure_schema
        ensure_schema(conn)
        yield conn


def remember_workspaces(rows: list[dict], *, db: str | Path | None = None) -> int:
    """Idempotent observation; does not erase missing or archived workspaces."""
    count = 0
    with _connection(db) as conn:
        for row in rows:
            path = row.get('path')
            if not isinstance(path, str) or not path or row.get('hidden_auxiliary'):
                continue
            if not Path(path).is_dir():
                continue
            conn.execute('''INSERT INTO workspaces(path_key,path,state_ref,title,readiness,profile,observed_at)
                 VALUES(?,?,?,?,?,?,?) ON CONFLICT(path_key) DO UPDATE SET
                 path=excluded.path, state_ref=excluded.state_ref,
                 title=excluded.title,readiness=excluded.readiness,
                 profile=excluded.profile,observed_at=excluded.observed_at''',
                 (_key(path), str(Path(path).resolve()), row.get('state_ref'),
                  row.get('title'), row.get('readiness'), row.get('profile'), _now()))
            count += 1
    return count


def record(workspace: str | Path, kind: str, payload: dict, *, profile: str = '',
           status: str | None = None, fingerprint: dict | None = None,
           db: str | Path | None = None, run_id: str | None = None) -> bool:
    """Persist evidence idempotently, without replacing any previous result."""
    if kind not in KINDS:
        raise ValueError('Unknown observation kind: ' + kind)
    root = Path(workspace).expanduser().resolve()
    if not root.is_dir():
        raise ValueError('Workspace no longer exists: ' + str(root))
    if not isinstance(payload, dict):
        raise ValueError('Expected a JSON object')
    source = fingerprint if fingerprint is not None else _fingerprint(root)
    encoded = _json(payload)
    serialized_fingerprint = _json(source)
    obs = str(payload.get('executed_at') or payload.get('generated_at') or _now())
    # Identity excludes a changing imported timestamp when the same result is replayed.
    identity = _json([_key(root), kind, profile, serialized_fingerprint, hashlib.sha256(encoded.encode('utf-8')).hexdigest()])
    event_id = hashlib.sha256(identity.encode('utf-8')).hexdigest()
    with _connection(db) as conn:
        conn.execute('''INSERT INTO workspaces(path_key,path,observed_at)
            VALUES(?,?,?) ON CONFLICT(path_key) DO NOTHING''', (_key(root), str(root), _now()))
        cur = conn.execute('''INSERT OR IGNORE INTO observations
           (event_id,path_key,kind,profile,status,observed_at,source_fingerprint,payload)
           VALUES(?,?,?,?,?,?,?,?)''',
           (event_id, _key(root), kind, profile, status, obs, serialized_fingerprint, encoded))
        # Atomic v1 compatibility + v2 journal write in the same SQLite transaction.
        from .unified.repository import put_event
        put_event(conn, event_id=event_id, workspace=root, kind=kind,
                  profile=profile, verdict=status, fingerprint=source, payload=payload,
                  observed_at=obs, run_id=run_id)
        return cur.rowcount == 1


def record_diagnostic(workspace: str | Path, report: dict, *, db: str | Path | None = None,
                      run_id: str | None = None) -> bool:
    return record(workspace, 'diagnostic', report,
                  profile=str(report.get('profile') or ''),
                  status=str(report.get('verdict') or report.get('process_status') or 'UNKNOWN'),
                  fingerprint=report.get('input_fingerprint') if isinstance(report.get('input_fingerprint'), dict) else None,
                  db=db, run_id=run_id)


def record_analysis(report: dict, *, db: str | Path | None = None,
                    run_id: str | None = None) -> int:
    """Read the existing global-analysis structure; keep just the per-Kristal result."""
    entries = report.get('entries') or []
    count = 0
    for item in entries:
        if not isinstance(item, dict) or not item.get('path'):
            continue
        record(item['path'], 'analysis', item, status=str(item.get('priority') or 'UNKNOWN'), db=db, run_id=run_id)
        count += 1
    return count


def latest(workspace: str | Path, kind: str, *, db: str | Path | None = None) -> dict | None:
    if kind not in KINDS:
        raise ValueError('Unknown observation kind')
    with _connection(db) as conn:
        result = conn.execute('''SELECT status,observed_at,source_fingerprint,payload,profile
            FROM observations WHERE path_key=? AND kind=?
            ORDER BY CASE WHEN source_fingerprint='{}' THEN 1 ELSE 0 END ASC, observed_at DESC, rowid DESC LIMIT 1''', (_key(workspace), kind)).fetchone()
    if not result:
        return None
    status, when, fingerprint, raw, profile = result
    source = _decode(fingerprint)
    current = _fingerprint(workspace)
    payload = _decode(raw)
    freshness = 'CURRENT' if source and current == source and not (payload or {}).get('input_changed_during_run') else 'STALE_OR_UNVERIFIED'
    return {'status': status, 'observed_at': when, 'profile': profile,
            'freshness': freshness, 'payload': payload, 'fingerprint': source}


def restore_rows(rows: list[dict], *, db: str | Path | None = None) -> list[dict]:
    """Hydrate current diagnostics; stale evidence is visible but never PASS."""
    for row in rows:
        path = row.get('path')
        if not path:
            continue
        evidence = latest(path, 'diagnostic', db=db)
        if evidence:
            row['diag_last_seen'] = evidence['observed_at']
            row['diag_freshness'] = evidence['freshness']
            if evidence['freshness'] == 'CURRENT':
                row['diag_report'] = evidence['payload']
            else:
                row.pop('diag_report', None)
        else:
            row.pop('diag_report', None)
            row.pop('diag_freshness', None)
        verification = latest(path, 'verification', db=db)
        if verification:
            row['local_verify_freshness'] = verification['freshness']
            if verification['freshness'] == 'CURRENT':
                row['operational_assessment'] = verification['payload']
            else:
                row.pop('operational_assessment', None)
    return rows


def status_counts(root: str | Path | None = None, *, db: str | Path | None = None) -> dict:
    with _connection(db) as conn:
        if root is None:
            rows = conn.execute('SELECT path FROM workspaces').fetchall()
        else:
            scope = Path(root).expanduser().resolve()
            rows = [(p,) for (p,) in conn.execute('SELECT path FROM workspaces').fetchall()
                    if Path(p).parent == scope]
    counts = {'workspaces': len(rows), 'current_diagnostics': 0,
              'stale_diagnostics': 0, 'not_run': 0, 'verdicts': {}}
    for (path,) in rows:
        result = latest(path, 'diagnostic', db=db)
        if result is None:
            counts['not_run'] += 1
        elif result['freshness'] != 'CURRENT':
            counts['stale_diagnostics'] += 1
        else:
            counts['current_diagnostics'] += 1
            verdict = result['status']
            counts['verdicts'][verdict] = counts['verdicts'].get(verdict, 0) + 1
    return counts


def record_arketype_batch(report: dict, *, db: str | Path | None = None,
                          run_id: str | None = None) -> int:
    """Persist Arketype's *structural* findings, never a canonical ARK decision."""
    count = 0
    for item in report.get('results', []) or []:
        if not isinstance(item, dict) or not item.get('path'):
            continue
        observed = {
            'format': item.get('format'), 'project': item.get('project'),
            'declared': item.get('declaration'), 'comparison': item.get('comparison'),
            'declared_level': item.get('declared_level'),
            'declared_evidence': item.get('declared_evidence'),
            'suggestions': item.get('suggestions'), 'ambiguity': item.get('ambiguity'),
            'structure': {'counts': (item.get('structure') or {}).get('counts'),
                          'observation_complete': (item.get('structure') or {}).get('observation_complete'),
                          'skipped': (item.get('structure') or {}).get('skipped')},
            'limits': item.get('limits') or [], 'qualification': 'NOT_ESTABLISHED'
        }
        record(item['path'], 'arketype', observed,
               status=str(item.get('comparison') or 'OBSERVED'), db=db, run_id=run_id)
        count += 1
    return count


def import_legacy_diagnostic_csv(csv_path: str | Path, root: str | Path,
                                 *, db: str | Path | None = None) -> dict:
    """Import an earlier batch summary as *historical/unverified*, never current.

    Reports from a pre-integration script lack a trustworthy source fingerprint.
    Therefore they must never become current PASS merely because a CSV says PASS.
    """
    import csv
    source = Path(root).expanduser().resolve(strict=True)
    file = Path(csv_path).expanduser().resolve(strict=True)
    if file.stat().st_size > 10 * 1024 * 1024:
        raise ValueError('Legacy diagnostic CSV too large')
    count, skipped = 0, 0
    with file.open('r', encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream, delimiter=';')
        if not {'Kristal', 'Profil', 'Verdict'}.issubset(set(reader.fieldnames or [])):
            raise ValueError('CSV batch format not recognized')
        for entry in reader:
            name = str(entry.get('Kristal') or '')
            if not name or name in ('.', '..') or name != Path(name).name or '\\' in name:
                skipped += 1; continue
            workspace = (source / name).resolve()
            if workspace.parent != source or not (workspace/'kristal.workspace.json').is_file():
                skipped += 1; continue
            report = {
                'format':'kristal.manager-legacy-diagnostic/0.1',
                'workspace':str(workspace), 'profile':str(entry.get('Profil') or ''),
                'verdict':str(entry.get('Verdict') or 'UNKNOWN'),
                'executed_at':_now(), 'process_status':'IMPORTED_UNVERIFIED',
                'evidence_directory':str(entry.get('Rapport') or ''),
                'explanation':'Import historique : empreinte source inconnue, résultat non actuel',
                'qualification':'NOT_ESTABLISHED', 'input_fingerprint':{},
            }
            record(workspace,'diagnostic',report,profile=report['profile'],
                   status=report['verdict'],fingerprint={},db=db)
            count += 1
    return {'imported':count,'skipped':skipped,'freshness':'STALE_OR_UNVERIFIED'}
