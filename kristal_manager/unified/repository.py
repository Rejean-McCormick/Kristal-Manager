"""Versioned, append-only operational journal within Manager's SQLite database.

Supports migration from v1 without losing prior observations, long-running runs,
profile-scoped queries, decisions as separate local records, and read-only views.
No changes to source workspaces are permitted here.
"""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import os
import sqlite3
import uuid
from .domain import Freshness, safe_object

DB_VERSION = 2
KINDS = frozenset({'inventory','analysis','diagnostic','arketype','verification','classification'})

def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def pathkey(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve()).casefold()

def _dbpath(db=None) -> Path:
    from ..central_store import database_path
    return Path(db if db is not None else database_path()).expanduser().resolve()

def ensure_schema(conn: sqlite3.Connection) -> None:
    """Idempotent, additive schema; v1 tables and indexes remain compatible."""
    previous = conn.execute('PRAGMA user_version').fetchone()[0]
    if previous > DB_VERSION:
        raise RuntimeError('Base de données plus récente que cette version de Manager')
    statements = '''
    CREATE TABLE IF NOT EXISTS runs_v2 (
       run_id TEXT PRIMARY KEY, engine TEXT NOT NULL, engine_version TEXT,
       profile TEXT, source_root TEXT, requested_at TEXT NOT NULL,
       started_at TEXT, ended_at TEXT, status TEXT NOT NULL,
       processed INTEGER NOT NULL DEFAULT 0, total INTEGER,
       report_directory TEXT, error TEXT
    );
    CREATE TABLE IF NOT EXISTS observations_v2 (
       event_id TEXT PRIMARY KEY,
       path_key TEXT NOT NULL, path TEXT NOT NULL, run_id TEXT,
       kind TEXT NOT NULL, engine TEXT NOT NULL, profile TEXT NOT NULL DEFAULT '',
       verdict TEXT, observed_at TEXT NOT NULL,
       source_scope TEXT NOT NULL, source_fingerprint TEXT NOT NULL,
       payload TEXT NOT NULL, evidence_uri TEXT, evidence_sha256 TEXT,
       process_status TEXT, qualification TEXT NOT NULL DEFAULT 'NOT_ESTABLISHED',
       FOREIGN KEY (run_id) REFERENCES runs_v2(run_id)
    );
    CREATE INDEX IF NOT EXISTS idx_obs_v2_lookup
      ON observations_v2(path_key,kind,profile,observed_at DESC);
    CREATE INDEX IF NOT EXISTS idx_obs_v2_run ON observations_v2(run_id);
    CREATE TABLE IF NOT EXISTS decisions_v2 (
      decision_id TEXT PRIMARY KEY, path_key TEXT NOT NULL, path TEXT NOT NULL,
      taxonomy TEXT NOT NULL, code TEXT NOT NULL, status TEXT NOT NULL,
      evidence_ref TEXT, actor TEXT, decided_at TEXT NOT NULL, supersedes TEXT,
      note TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_decisions_v2_path
      ON decisions_v2(path_key,taxonomy,decided_at DESC);
    '''
    # execute(), unlike executescript(), never commits an open legacy transaction.
    # Legacy and normalized entries must be written atomically.
    for statement in statements.split(';'):
        if statement.strip(): conn.execute(statement)
    if previous < DB_VERSION:
        conn.execute('PRAGMA user_version=2')

@contextmanager
def connection(db=None):
    target=_dbpath(db)
    target.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(target,timeout=20.0) as conn:
        conn.execute('PRAGMA busy_timeout=20000')
        conn.execute('PRAGMA foreign_keys=ON')
        version=conn.execute('PRAGMA user_version').fetchone()[0]
        if version < DB_VERSION and conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='observations'").fetchone():
            backup_database(db=target,destination=target.with_name(target.name+'.before-v2.backup'))
        ensure_schema(conn)
        yield conn

def backup_database(db=None, *, destination: str | Path | None = None) -> str | None:
    target=_dbpath(db)
    if not target.is_file():return None
    dest=Path(destination).expanduser().resolve() if destination else target.with_name(
        target.name+'.backup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    if dest==target:raise ValueError('La sauvegarde doit être ailleurs que la base')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(target) as source, sqlite3.connect(dest) as backup:
        source.backup(backup)
    return str(dest)

def start_run(engine: str, *, profile: str='', root: str | Path | None=None,
              version: str | None=None, total: int | None=None, db=None) -> str:
    if not engine or len(engine)>100:raise ValueError('Moteur invalide')
    if total is not None and total<0:raise ValueError('Total invalide')
    run_id=str(uuid.uuid4())
    with connection(db) as conn:
        conn.execute('''INSERT INTO runs_v2(run_id,engine,engine_version,profile,source_root,
          requested_at,started_at,status,total) VALUES (?,?,?,?,?,?,?,?,?)''',
          (run_id,engine,version,profile,str(Path(root).resolve()) if root else None,
           utcnow(),utcnow(),'RUNNING',total))
    return run_id

def finish_run(run_id: str, status: str, *, processed: int | None=None,
               directory: str | Path | None=None, error: str | None=None,db=None) -> None:
    if status not in ('COMPLETED','FAILED','INTERRUPTED'):
        raise ValueError('Statut de fin invalide')
    with connection(db) as conn:
        old=conn.execute('SELECT status,processed FROM runs_v2 WHERE run_id=?',(run_id,)).fetchone()
        if old is None:raise ValueError('Run introuvable')
        if old[0]!='RUNNING':raise ValueError('Run déjà terminé')
        conn.execute('''UPDATE runs_v2 SET status=?,processed=?,ended_at=?,report_directory=?,error=?
                        WHERE run_id=?''',
                     (status,processed if processed is not None else old[1],utcnow(),
                      str(directory) if directory else None,(error or '')[:2000],run_id))

def set_progress(run_id: str, processed: int, *, db=None) -> None:
    with connection(db) as conn:
        conn.execute('UPDATE runs_v2 SET processed=? WHERE run_id=? AND status=?',
                     (processed,run_id,'RUNNING'))

def put_event(conn: sqlite3.Connection, *, event_id: str, workspace: str | Path,
              kind: str, profile: str, verdict: str | None, fingerprint: dict,
              payload: dict, observed_at: str, run_id: str | None=None,
              engine: str | None=None, scope: str | None=None) -> bool:
    """Called *inside* central_store's existing transaction to ensure atomic dual writes."""
    if kind not in KINDS:raise ValueError('Observation inconnue: '+kind)
    ensure_schema(conn)
    path=str(Path(workspace).expanduser().resolve())
    fp=safe_object(fingerprint)
    report=safe_object(payload)
    if run_id is not None:
        if conn.execute('SELECT 1 FROM runs_v2 WHERE run_id=?',(run_id,)).fetchone() is None:
            raise ValueError('run_id inconnu')
    reference=payload.get('evidence_directory') or payload.get('report_directory') or payload.get('raw_report_ref')
    digest=payload.get('evidence_sha256')
    if reference is not None:reference=str(reference)[:2000]
    if digest is not None:digest=str(digest)[:100]
    cur=conn.execute('''INSERT OR IGNORE INTO observations_v2
      (event_id,path_key,path,run_id,kind,engine,profile,verdict,observed_at,
       source_scope,source_fingerprint,payload,evidence_uri,evidence_sha256,process_status,qualification)
       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
       (event_id,pathkey(path),path,run_id,kind,engine or kind,profile,verdict,observed_at,
        scope or ('bounded-v9' if kind in ('diagnostic','verification','inventory') else 'limited-source'),
        fp,report,reference,digest,str(payload.get('process_status') or '')[:100],
        str(payload.get('qualification') or 'NOT_ESTABLISHED')[:100]))
    return cur.rowcount==1

def backfill_v1(*, db=None) -> int:
    """Migrate previous events without changing a verdict or fabricating a run."""
    count=0
    with connection(db) as conn:
        exists=conn.execute("SELECT 1 FROM sqlite_master WHERE name='observations' AND type='table'").fetchone()
        if not exists:return 0
        entries=conn.execute('''SELECT o.event_id,w.path,o.kind,o.profile,o.status,
                  o.observed_at,o.source_fingerprint,o.payload
                  FROM observations o JOIN workspaces w USING(path_key)''').fetchall()
        for eid,path,kind,profile,status,stamp,fp,payload in entries:
            if kind not in KINDS:continue
            try:
                source=json.loads(fp);data=json.loads(payload)
                if not isinstance(source,dict) or not isinstance(data,dict):continue
            except (ValueError,TypeError):continue
            count+=int(put_event(conn,event_id=eid,workspace=path,kind=kind,
                     profile=profile or '',verdict=status,fingerprint=source,
                     payload=data,observed_at=stamp,engine='import-legacy-v1',
                     scope='legacy-bounded'))
    return count

def _freshness(path: str, scope: str, fingerprint: dict, payload: dict, kind: str='') -> str:
    if not fingerprint or payload.get('input_changed_during_run'):
        return Freshness.UNVERIFIED.value
    if not Path(path).is_dir():return Freshness.STALE.value
    try:
        from ..diag_bridge import _fingerprint
        current=_fingerprint(Path(path))
    except (OSError,ValueError):return Freshness.UNVERIFIED.value
    if current!=fingerprint:return Freshness.STALE.value
    # Fingerprint of V9-known surfaces never certifies semantic/canonical observations.
    if scope in ('bounded-v9','legacy-bounded') and kind in ('diagnostic','verification','inventory'):
        return Freshness.CURRENT.value
    return Freshness.PARTIAL.value

def history(workspace: str | Path, kind: str | None=None, *, profile: str | None=None,
            limit: int=100, db=None) -> list[dict]:
    if not 1<=limit<=1000:raise ValueError('limit hors plage')
    sql='''SELECT event_id,kind,engine,profile,verdict,observed_at,source_scope,
                  source_fingerprint,payload,evidence_uri,run_id,qualification
           FROM observations_v2 WHERE path_key=?'''
    params=[pathkey(workspace)]
    if kind is not None:
        if kind not in KINDS:raise ValueError('Type inconnu')
        sql+=' AND kind=?';params.append(kind)
    if profile is not None:
        sql+=' AND profile=?';params.append(profile)
    sql+=' ORDER BY observed_at DESC, rowid DESC LIMIT ?';params.append(limit)
    with connection(db) as conn:
        entries=conn.execute(sql,params).fetchall()
    output=[]
    for eid,kind,engine,profile,verdict,stamp,scope,fp,payload,uri,run_id,qualification in entries:
        try:input_fp=json.loads(fp);report=json.loads(payload)
        except (TypeError,ValueError):input_fp={};report={}
        output.append({'event_id':eid,'kind':kind,'engine':engine,'profile':profile,
                       'verdict':verdict,'observed_at':stamp,'source_scope':scope,
                       'freshness':_freshness(str(workspace),scope,input_fp,report,kind),
                       'payload':report,'evidence_uri':uri,'run_id':run_id,
                       'qualification':qualification})
    return output

def latest_observation(workspace: str | Path, kind: str, *, profile: str | None=None,db=None):
    values=history(workspace,kind,profile=profile,limit=1,db=db)
    return values[0] if values else None

def list_runs(*, engine: str | None=None,limit: int=100,db=None) -> list[dict]:
    if not 1<=limit<=500:raise ValueError('limit hors plage')
    sql='''SELECT run_id,engine,profile,source_root,requested_at,ended_at,status,
                  processed,total,report_directory,error FROM runs_v2'''
    params=[]
    if engine:
        sql+=' WHERE engine=?';params.append(engine)
    sql+=' ORDER BY requested_at DESC,rowid DESC LIMIT ?';params.append(limit)
    with connection(db) as conn:
        rows=conn.execute(sql,params).fetchall()
    return [dict(zip(('run_id','engine','profile','source_root','requested_at','ended_at',
                      'status','processed','total','report_directory','error'),row)) for row in rows]

def record_decision(workspace: str | Path, taxonomy: str, code: str, *, status: str='proposed',
                    evidence_ref: str | None=None, actor: str='local', note: str='',
                    supersedes: str | None=None,db=None) -> str:
    """Local Manager decision only. Never claims to modify canonical classifications."""
    if taxonomy not in ('ARK','PRF','UNESCO','WIKIDATA'):
        raise ValueError('Taxonomie inconnue')
    if status not in ('proposed','approved_locally','rejected_locally','needs_discussion'):
        raise ValueError('Statut de décision inconnu')
    if not code or len(code)>150:raise ValueError('Code invalide')
    path=Path(workspace).expanduser().resolve(strict=True)
    if not (path/'kristal.workspace.json').is_file():raise ValueError('Kristal invalide')
    ident=str(uuid.uuid4())
    with connection(db) as conn:
        if supersedes and not conn.execute('SELECT 1 FROM decisions_v2 WHERE decision_id=?',(supersedes,)).fetchone():
            raise ValueError('Décision précédente introuvable')
        conn.execute('''INSERT INTO decisions_v2 VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                     (ident,pathkey(path),str(path),taxonomy,code,status,
                      evidence_ref,actor[:100],utcnow(),supersedes,note[:2000]))
    return ident

def list_decisions(workspace: str | Path, *, db=None) -> list[dict]:
    with connection(db) as conn:
        rows=conn.execute('''SELECT decision_id,taxonomy,code,status,evidence_ref,actor,
                    decided_at,supersedes,note FROM decisions_v2 WHERE path_key=?
                    ORDER BY decided_at DESC,rowid DESC''',(pathkey(workspace),)).fetchall()
    return [dict(zip(('decision_id','taxonomy','code','status','evidence_ref','actor',
                      'decided_at','supersedes','note'),r)) for r in rows]

def dashboard(*,root: str | Path | None=None, db=None) -> list[dict]:
    """One paginated-in-memory projection for the <=127 workspaces; no content db read."""
    with connection(db) as conn:
        exists=conn.execute("SELECT 1 FROM sqlite_master WHERE name='workspaces'").fetchone()
        if not exists:return []
        rows=conn.execute('SELECT path,state_ref,title,readiness FROM workspaces ORDER BY title,path').fetchall()
    target=Path(root).expanduser().resolve() if root else None
    output=[]
    for path,state,title,readiness in rows:
        if target and Path(path).parent!=target:continue
        diagnostic=latest_observation(path,'diagnostic',db=db)
        analysis=latest_observation(path,'analysis',db=db)
        structure=latest_observation(path,'arketype',db=db)
        inv=latest_observation(path,'inventory',db=db)
        output.append({'path':path,'state_ref':state,'title':title or Path(path).name,
                       'readiness':readiness, 'diagnostic_verdict':diagnostic['verdict'] if diagnostic else 'NOT_RUN',
                       'diagnostic_freshness':diagnostic['freshness'] if diagnostic else 'NOT_RUN',
                       'diagnostic_profile':diagnostic['profile'] if diagnostic else None,
                       'analysis_priority':analysis['verdict'] if analysis else None,
                       'analysis_freshness':analysis['freshness'] if analysis else None,
                       'arketype_level':structure['verdict'] if structure else None,
                       'arketype_freshness':structure['freshness'] if structure else None,
                       'inventory_freshness':inv['freshness'] if inv else None,
                       'decisions_count':len(list_decisions(path,db=db))})
    return output

def integrity_check(*, db=None) -> dict:
    with connection(db) as conn:
        value=conn.execute('PRAGMA integrity_check').fetchone()[0]
        total=conn.execute('SELECT count(*) FROM observations_v2').fetchone()[0]
        count=conn.execute('SELECT count(*) FROM runs_v2').fetchone()[0]
    return {'sqlite':value,'schema':DB_VERSION,'observations':total,'runs':count,
            'qualification':'NOT_ESTABLISHED'}
