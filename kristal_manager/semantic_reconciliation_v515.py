"""V5.15 private semantic-review cases from a V5.14 candidate SQLite index.

This is a read-only reconciliation *observation*, not a selection, migration,
Wikidata approval, C1/C2 qualification, canonical correction, or publication.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3

from .local_first_audit import LocalFirstAuditError
from .semantic_federation_inventory import PROFILE as SOURCE_PROFILE, _new_destination

PROFILE = "koa.semantic-reconciliation/0.1-candidate"
KINDS = {
    "IDENTITY_KIND_VARIANTS": "One scoped identity has different declared entity/property/assertion/source roles.",
    "IDENTITY_STATUS_VARIANTS": "The same scoped identity has distinct source-recorded lifecycle states.",
    "COMPETING_PREFERRED_TERMS": "Several normalized preferred terms occur for one scoped identity and language.",
    "SHARED_LEXICAL_TERM": "The same normalized term denotes several semantic IDs within a namespace/language; polysemy is possible.",
    "EXACTMATCH_TARGET_VARIANTS": "A scoped semantic ID has multiple candidate/accepted exactMatch targets. Rejected alternatives are excluded.",
    "EXACTMATCH_STATUS_VARIANTS": "An exact same external reference has differing source-recorded statuses across revisions.",
    "RECORDED_ACCEPTANCE_WITHOUT_EVIDENCE": "An accepted source record has no nonempty evidence_refs array; status is not independently verified.",
    "UNREGISTERED_LEXICAL_ID_IN_COMPLETE_REVISION": "Lexical entry lacks a same-revision registry identity in an otherwise complete v11 core.",
    "MULTIPLE_COMPLETE_REVISIONS": "The owner has multiple complete, unselected canonical v11 candidates.",
}
PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _compact(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha_file(path: Path) -> str:
    digest=sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()


def _open_private(path: Path) -> sqlite3.Connection:
    source=Path(path)
    if not source.is_file() or source.is_symlink():
        raise LocalFirstAuditError("Expected an existing real private SQLite file")
    db=sqlite3.connect(f"file:{source.resolve().as_posix()}?mode=ro&immutable=1",uri=True)
    db.row_factory=sqlite3.Row
    return db


def _source_checks(source: sqlite3.Connection) -> dict:
    if source.execute("PRAGMA quick_check(1)").fetchone()[0] != "ok":
        raise LocalFirstAuditError("V5.14 SQLite failed integrity quick_check")
    try:
        row=source.execute("SELECT value FROM metadata WHERE key='summary_json'").fetchone()
        summary=json.loads(row[0]) if row else None
        if not isinstance(summary,dict) or summary.get("profile") != SOURCE_PROFILE:
            raise LocalFirstAuditError("Not a V5.14 semantic observatory database")
        if summary.get("status") != "CANDIDATE_INTEGRITY_ONLY":
            raise LocalFirstAuditError("V5.14 database integrity is blocked, cannot reconcile")
        counts=summary.get("counts",{})
        for key,sql in {
            "local_workspaces":"SELECT COUNT(*) FROM workspace",
            "revision_groups":"SELECT COUNT(*) FROM revision",
            "identity_occurrences":"SELECT COUNT(*) FROM identity_occurrence",
            "lexical_occurrences":"SELECT COUNT(*) FROM lexical_occurrence",
            "external_alignment_occurrences":"SELECT COUNT(*) FROM external_alignment",
        }.items():
            observed=source.execute(sql).fetchone()[0]
            if counts.get(key,0) != observed:
                raise LocalFirstAuditError(f"V5.14 metadata/count mismatch in {key}: {observed}")
        if source.execute("SELECT COUNT(*) FROM revision WHERE selection_status!='unselected'").fetchone()[0]:
            raise LocalFirstAuditError("Input contains selected revisions; this index requires unselected source candidates")
        if source.execute("SELECT COUNT(*) FROM finding WHERE severity='BLOCK'").fetchone()[0]:
            raise LocalFirstAuditError("Input V5.14 has unresolved integrity blockers")
        return summary
    except (sqlite3.Error,TypeError,ValueError,KeyError) as exc:
        if isinstance(exc,LocalFirstAuditError):
            raise
        raise LocalFirstAuditError(f"Malformed or incomplete V5.14 source database: {exc}") from exc


def _create_review(db: sqlite3.Connection):
    db.executescript("""
        PRAGMA foreign_keys = ON;
        CREATE TABLE review_case (
            case_id TEXT PRIMARY KEY, kind TEXT NOT NULL, priority TEXT NOT NULL,
            namespace_id TEXT, semantic_id TEXT, language_tag TEXT, term_folded TEXT,
            external_system TEXT, external_id TEXT, owner_slug TEXT,
            observed_occurrences INTEGER NOT NULL, distinct_variants INTEGER NOT NULL,
            evidence_samples_json TEXT NOT NULL,
            decision_state TEXT NOT NULL DEFAULT 'NOT_DECIDED',
            CHECK(decision_state = 'NOT_DECIDED')
        );
        CREATE INDEX case_kind ON review_case(kind,priority);
        CREATE INDEX case_semantic ON review_case(namespace_id,semantic_id);
        CREATE INDEX case_owner ON review_case(owner_slug);
        CREATE TABLE revision_snapshot (
            owner_slug TEXT NOT NULL, revision_dir TEXT NOT NULL, kind TEXT NOT NULL,
            namespace_id TEXT, roles_json TEXT NOT NULL, sha256_json TEXT NOT NULL,
            selection_state TEXT NOT NULL CHECK(selection_state='unselected'),
            PRIMARY KEY(owner_slug,revision_dir)
        );
        CREATE TABLE metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL);
    """)


def _evidence(db: sqlite3.Connection, sql: str, args=(), limit=6) -> list[dict]:
    return [dict(row) for row in db.execute(sql+" LIMIT ?",(*args,limit))]


def _put_case(review: sqlite3.Connection, totals: Counter, source_sha: str,
              kind: str, priority: str, ns: str | None, sid: str | None,
              language: str | None, external_system: str | None,
              external_id: str | None, owner: str | None,
              occurrences: int, variants: int, samples: list[dict],
              term_folded: str | None = None):
    key=[source_sha,kind,ns,sid,language,term_folded,external_system,external_id,owner]
    case_id=sha256(_compact(key).encode("utf-8")).hexdigest()[:32]
    review.execute("INSERT INTO review_case VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'NOT_DECIDED')",
                   (case_id,kind,priority,ns,sid,language,term_folded,external_system,external_id,owner,
                    occurrences,variants,_compact(samples)))
    totals[kind]+=1
    totals["priority_"+priority.lower()]+=1


def reconcile_semantic_inventory(source_path: Path, review_path: Path,
                                 report_path: Path) -> dict:
    """Build a candidate review database and summary, both NEW and private."""
    output=_new_destination(review_path,source_path)
    report=_new_destination(report_path,source_path)
    if output == report:
        raise LocalFirstAuditError("Review SQLite and JSON report must have distinct paths")
    original=Path(source_path).resolve(strict=True)
    source_sha=_sha_file(original)
    source=_open_private(original)
    target=None
    created=False
    totals=Counter()
    try:
        source_summary=_source_checks(source)
        fd=os.open(output,os.O_CREAT|os.O_EXCL|os.O_RDWR,0o600)
        os.close(fd)
        created=True
        target=sqlite3.connect(output)
        target.row_factory=sqlite3.Row
        _create_review(target)
        target.executemany("INSERT INTO revision_snapshot VALUES (?,?,?,?,?,?,?)", (
            (row["slug"],row["revision_dir"],row["kind"],row["namespace_id"],
             row["roles_json"],row["sha256_json"],row["selection_status"])
            for row in source.execute("SELECT slug,revision_dir,kind,namespace_id,roles_json,sha256_json,selection_status FROM revision ORDER BY slug,revision_dir")
        ))

        for ns,sid,variants,occurrences in source.execute("""
            SELECT namespace_id,semantic_id,COUNT(DISTINCT kind),COUNT(*)
            FROM identity_occurrence GROUP BY 1,2 HAVING COUNT(DISTINCT kind)>1
            ORDER BY 1,2"""):
            samples=_evidence(source,"SELECT slug,revision_dir,kind,status,source_path,record_json FROM identity_occurrence WHERE namespace_id=? AND semantic_id=? ORDER BY revision_dir,kind",(ns,sid))
            _put_case(target,totals,source_sha,"IDENTITY_KIND_VARIANTS","HIGH",ns,sid,None,None,None,None,occurrences,variants,samples)
        for ns,sid,variants,occurrences in source.execute("""
            SELECT namespace_id,semantic_id,COUNT(DISTINCT status),COUNT(*)
            FROM identity_occurrence GROUP BY 1,2 HAVING COUNT(DISTINCT status)>1
            ORDER BY 1,2"""):
            samples=_evidence(source,"SELECT slug,revision_dir,kind,status,source_path,record_json FROM identity_occurrence WHERE namespace_id=? AND semantic_id=? ORDER BY revision_dir,status",(ns,sid))
            _put_case(target,totals,source_sha,"IDENTITY_STATUS_VARIANTS","MEDIUM",ns,sid,None,None,None,None,occurrences,variants,samples)
        for ns,sid,language,variants,occurrences in source.execute("""
            SELECT namespace_id,semantic_id,language_tag,COUNT(DISTINCT term_folded),COUNT(*)
            FROM lexical_occurrence GROUP BY 1,2,3 HAVING COUNT(DISTINCT term_folded)>1
            ORDER BY 1,2,3"""):
            samples=_evidence(source,"SELECT slug,revision_dir,language_tag,term,layer_id,source_path,record_json FROM lexical_occurrence WHERE namespace_id=? AND semantic_id=? AND language_tag=? ORDER BY term_folded,revision_dir",(ns,sid,language))
            _put_case(target,totals,source_sha,"COMPETING_PREFERRED_TERMS","MEDIUM",ns,sid,language,None,None,None,occurrences,variants,samples)
        for ns,language,term,variants,occurrences in source.execute("""
            SELECT namespace_id,language_tag,term_folded,COUNT(DISTINCT semantic_id),COUNT(*)
            FROM lexical_occurrence GROUP BY 1,2,3 HAVING COUNT(DISTINCT semantic_id)>1
            ORDER BY 1,2,3"""):
            samples=_evidence(source,"SELECT semantic_id,slug,revision_dir,language_tag,term,layer_id,source_path FROM lexical_occurrence WHERE namespace_id=? AND language_tag=? AND term_folded=? ORDER BY semantic_id,revision_dir",(ns,language,term))
            # Semantic ID in the case key is intentionally blank: multiple IDs.
            _put_case(target,totals,source_sha,"SHARED_LEXICAL_TERM","LOW",ns,None,language,None,None,None,occurrences,variants,samples,term_folded=term)
        for ns,sid,system,variants,occurrences,accepted in source.execute("""
            SELECT namespace_id,semantic_id,external_system,COUNT(DISTINCT external_id),
                   COUNT(*),MAX(CASE WHEN status='accepted' THEN 1 ELSE 0 END)
            FROM external_alignment WHERE relation='exactMatch' AND status IN ('candidate','accepted')
            GROUP BY 1,2,3 HAVING COUNT(DISTINCT external_id)>1 ORDER BY 1,2,3"""):
            samples=_evidence(source,"SELECT slug,revision_dir,external_id,relation,status,review_method,source_path,record_json FROM external_alignment WHERE namespace_id=? AND semantic_id=? AND external_system=? AND relation='exactMatch' AND status IN ('candidate','accepted') ORDER BY CASE WHEN status='accepted' THEN 0 ELSE 1 END,external_id,revision_dir",(ns,sid,system))
            _put_case(target,totals,source_sha,"EXACTMATCH_TARGET_VARIANTS","HIGH" if accepted else "MEDIUM",ns,sid,None,system,None,None,occurrences,variants,samples)
            if accepted:totals["exactmatch_multi_target_with_recorded_acceptance"]+=1
        for ns,sid,system,external_id,variants,occurrences in source.execute("""
            SELECT namespace_id,semantic_id,external_system,external_id,
                   COUNT(DISTINCT status),COUNT(*) FROM external_alignment
            WHERE relation='exactMatch' GROUP BY 1,2,3,4
            HAVING COUNT(DISTINCT status)>1 ORDER BY 1,2,3,4"""):
            samples=_evidence(source,"SELECT slug,revision_dir,relation,status,review_method,source_path,record_json FROM external_alignment WHERE namespace_id=? AND semantic_id=? AND external_system=? AND external_id=? ORDER BY status,revision_dir",(ns,sid,system,external_id))
            _put_case(target,totals,source_sha,"EXACTMATCH_STATUS_VARIANTS","MEDIUM",ns,sid,None,system,external_id,None,occurrences,variants,samples)
        for ns,sid,system,external_id,occurrences in source.execute("""
            SELECT namespace_id,semantic_id,external_system,external_id,COUNT(*)
            FROM external_alignment WHERE status='accepted' AND
              (COALESCE(json_type(record_json,'$.review.evidence_refs'),'missing')!='array'
               OR COALESCE(json_array_length(record_json,'$.review.evidence_refs'),0)=0)
            GROUP BY 1,2,3,4 ORDER BY 1,2,3,4"""):
            samples=_evidence(source,"SELECT slug,revision_dir,status,review_method,source_path,record_json FROM external_alignment WHERE namespace_id=? AND semantic_id=? AND external_system=? AND external_id=? AND status='accepted' ORDER BY revision_dir",(ns,sid,system,external_id))
            _put_case(target,totals,source_sha,"RECORDED_ACCEPTANCE_WITHOUT_EVIDENCE","HIGH",ns,sid,None,system,external_id,None,occurrences,1,samples)
        for ns,sid,slug,revision,occurrences in source.execute("""
            SELECT l.namespace_id,l.semantic_id,l.slug,l.revision_dir,COUNT(*)
            FROM lexical_occurrence l JOIN revision r
              ON r.slug=l.slug AND r.revision_dir=l.revision_dir
            WHERE r.kind='complete_core' AND NOT EXISTS (
                SELECT 1 FROM identity_occurrence i WHERE
                  i.namespace_id=l.namespace_id AND i.semantic_id=l.semantic_id
                  AND i.slug=l.slug AND i.revision_dir=l.revision_dir)
            GROUP BY 1,2,3,4 ORDER BY 1,2,3,4"""):
            samples=_evidence(source,"SELECT language_tag,term,layer_id,source_path,record_json FROM lexical_occurrence WHERE namespace_id=? AND semantic_id=? AND slug=? AND revision_dir=? ORDER BY language_tag,term",(ns,sid,slug,revision))
            for item in samples:item["revision_dir"]=revision
            _put_case(target,totals,source_sha,"UNREGISTERED_LEXICAL_ID_IN_COMPLETE_REVISION","HIGH",ns,sid,None,None,None,slug,occurrences,1,samples)
        for slug,variants in source.execute("""
            SELECT slug,COUNT(*) FROM revision WHERE kind='complete_core'
            GROUP BY slug HAVING COUNT(*)>1 ORDER BY slug"""):
            samples=_evidence(source,"SELECT revision_dir,kind,namespace_id,sha256_json,selection_status FROM revision WHERE slug=? AND kind='complete_core' ORDER BY revision_dir",(slug,))
            _put_case(target,totals,source_sha,"MULTIPLE_COMPLETE_REVISIONS","LOW",None,None,None,None,None,slug,variants,variants,samples)

        totals["intra_revision_exactmatch_multi_targets"] = source.execute("""
            SELECT COUNT(*) FROM (SELECT 1 FROM external_alignment
            WHERE relation='exactMatch' AND status IN ('candidate','accepted')
            GROUP BY namespace_id,semantic_id,slug,
            revision_dir,external_system HAVING COUNT(DISTINCT external_id)>1)
        """).fetchone()[0]
        totals["recorded_accepted_exactmatch_audited_rule_not_qualified"] = source_summary["counts"].get("recorded_accepted_exactmatch_audited_rule",0)
        totals["review_cases"] = target.execute("SELECT COUNT(*) FROM review_case").fetchone()[0]
        totals["revisions_unselected"] = target.execute("SELECT COUNT(*) FROM revision_snapshot").fetchone()[0]
        for kind in KINDS:totals.setdefault(kind,0)
        examples=[dict(row) for row in target.execute("""
            SELECT case_id,kind,priority,namespace_id,semantic_id,language_tag,term_folded,
                   external_system,external_id,owner_slug,observed_occurrences,
                   distinct_variants FROM review_case
            ORDER BY CASE priority WHEN 'HIGH' THEN 0 WHEN 'MEDIUM' THEN 1 ELSE 2 END,
                     observed_occurrences DESC,case_id LIMIT 20""")]
        summary={"profile":PROFILE,"status":"REVIEW_CANDIDATE_NOT_QUALIFIED",
                 "input":{"profile":SOURCE_PROFILE,"source_db_sha256":source_sha,
                          "integrity":"V5.14_CANDIDATE_INTEGRITY_ONLY",
                          "workspaces":source_summary["counts"]["local_workspaces"],
                          "distinct_scoped_identities":source_summary["counts"]["distinct_scoped_identities"]},
                 "counts":dict(sorted(totals.items())),"case_kinds":KINDS,
                 "samples_high_priority":examples,
                 "policy":{"automatic_revision_selection":False,
                           "automatic_identity_merge":False,
                           "automatic_wikidata_approval":False,
                           "canonical_or_public_write_authorized":False,
                           "independent_C1_C2_qualified":False,
                           "all_cases_decision_state":"NOT_DECIDED"},
                 "review_db":str(output),"report_path":str(report)}
        target.execute("INSERT INTO metadata VALUES ('summary_json',?)",(_compact(summary),))
        if _sha_file(original) != source_sha:
            raise LocalFirstAuditError("V5.14 source SQLite changed during reconciliation")
        target.commit()
        target.close();target=None
        fd=os.open(report,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"w",encoding="utf-8") as handle:
            json.dump(summary,handle,ensure_ascii=False,indent=2)
            handle.write("\n")
        return summary
    except Exception:
        if target is not None:target.close()
        if created and output.exists():output.unlink()
        raise
    finally:
        source.close()


def list_reconciliation_cases(review_db: Path, kind: str | None = None,
                              namespace_id: str | None = None,
                              semantic_id: str | None = None,
                              limit: int = 30, offset: int = 0) -> dict:
    if not 1 <= limit <= 200 or offset < 0:
        raise LocalFirstAuditError("limit 1..200 and nonnegative offset required")
    if kind is not None and kind not in KINDS:
        raise LocalFirstAuditError("Unknown case kind")
    for name,val in (("namespace_id",namespace_id),("semantic_id",semantic_id)):
        if val is not None and (not isinstance(val,str) or not val):
            raise LocalFirstAuditError(f"Invalid {name}")
    db=_open_private(review_db)
    try:
        row=db.execute("SELECT value FROM metadata WHERE key='summary_json'").fetchone()
        summary=json.loads(row[0]) if row else None
        if not isinstance(summary,dict) or summary.get("profile") != PROFILE:
            raise LocalFirstAuditError("Unknown V5.15 review database")
        clauses=[];params=[]
        for column,val in (("kind",kind),("namespace_id",namespace_id),("semantic_id",semantic_id)):
            if val is not None:
                clauses.append(column+"=?")
                params.append(val)
        where=" WHERE "+" AND ".join(clauses) if clauses else ""
        total=db.execute("SELECT COUNT(*) FROM review_case"+where,params).fetchone()[0]
        records=[dict(row) for row in db.execute("""
            SELECT case_id,kind,priority,namespace_id,semantic_id,language_tag,term_folded,
                   external_system,external_id,owner_slug,observed_occurrences,
                   distinct_variants,evidence_samples_json,decision_state
            FROM review_case"""+where+" ORDER BY CASE priority WHEN 'HIGH' THEN 0 WHEN 'MEDIUM' THEN 1 ELSE 2 END,observed_occurrences DESC,case_id LIMIT ? OFFSET ?",(*params,limit,offset))]
        for case in records:
            case["evidence_samples"]=json.loads(case.pop("evidence_samples_json"))
        return {"profile":PROFILE,"status":summary["status"],
                "source_db_sha256":summary["input"]["source_db_sha256"],
                "total_matches":total,"offset":offset,"limit":limit,
                "cases":records,"qualification":"REVIEW_ONLY_NO_DECISIONS"}
    finally:
        db.close()
