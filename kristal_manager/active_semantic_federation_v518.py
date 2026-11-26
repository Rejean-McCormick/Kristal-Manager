"""V5.18: a provenance-preserving index of *active* local Kristal semantics.

The federated index is private, derived, disposable and queryable. It never
changes canonical identities, grants Wikidata matches, or publishes a Kristal.
Historical lexical records may produce suggestions, never automatic labels.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import unicodedata

from .local_first_audit import LocalFirstAuditError, ReadOnlyTree, audit_local_first
from .local_semantic_evolution_v516 import (
    FORMAT as PROJECTION_FORMAT,
    POINTER_FORMAT,
    _real_path,
    _safe_member,
    evolve as refresh_v516,
)
from .semantic_federation_inventory import _new_destination


FORMAT = "koa.kristal-active-federation/1.0"
REVIEW_FORMAT = "koa.kristal-public-sync-plan/0.1-draft"


def _fail(message: str):
    raise LocalFirstAuditError("V5.18: " + message)


def _json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fold(term):
    return unicodedata.normalize("NFKC", term).casefold().strip()


def _sha(content: bytes):
    return sha256(content).hexdigest()


def _hash_file(path: Path):
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _schema(db):
    db.executescript("""
    PRAGMA foreign_keys=ON;
    CREATE TABLE workspace (
       slug TEXT PRIMARY KEY, local_directory TEXT NOT NULL,
       namespace_id TEXT UNIQUE, active INTEGER NOT NULL,
       profile_sha256 TEXT, state_sha256 TEXT NOT NULL,
       projection_sha256 TEXT, available_complete_revisions INTEGER NOT NULL);
    CREATE TABLE identity (
       namespace_id TEXT NOT NULL, semantic_id TEXT NOT NULL, owner_slug TEXT NOT NULL,
       kind TEXT NOT NULL, lifecycle_status TEXT,
       accepted_wikidata TEXT, candidate_wikidata_json TEXT NOT NULL,
       PRIMARY KEY(namespace_id,semantic_id), FOREIGN KEY(owner_slug) REFERENCES workspace(slug));
    CREATE TABLE lexical (
       namespace_id TEXT NOT NULL, semantic_id TEXT NOT NULL,
       language_tag TEXT NOT NULL, preferred_term TEXT NOT NULL,
       term_folded TEXT NOT NULL, priority INTEGER,
       provenance_json TEXT NOT NULL,
       PRIMARY KEY(namespace_id,semantic_id,language_tag),
       FOREIGN KEY(namespace_id,semantic_id) REFERENCES identity(namespace_id,semantic_id));
    CREATE INDEX lexical_lookup ON lexical(term_folded);
    CREATE INDEX identity_wikidata_lookup ON identity(accepted_wikidata);
    CREATE TABLE candidate_wikidata (
       namespace_id TEXT NOT NULL, semantic_id TEXT NOT NULL,
       external_qid TEXT NOT NULL,
       source_status TEXT NOT NULL DEFAULT 'candidate_not_approved',
       PRIMARY KEY(namespace_id,semantic_id,external_qid),
       FOREIGN KEY(namespace_id,semantic_id) REFERENCES identity(namespace_id,semantic_id));
    CREATE INDEX candidate_wikidata_lookup ON candidate_wikidata(external_qid);
    CREATE TABLE review_queue (
       namespace_id TEXT NOT NULL, semantic_id TEXT NOT NULL, issue TEXT NOT NULL,
       detail_json TEXT NOT NULL,
       PRIMARY KEY(namespace_id,semantic_id,issue));
    CREATE TABLE historical_lexical_hint (
       namespace_id TEXT NOT NULL, semantic_id TEXT NOT NULL,
       language_tag TEXT NOT NULL, suggested_term TEXT NOT NULL,
       term_folded TEXT NOT NULL, source_paths_json TEXT NOT NULL,
       status TEXT NOT NULL DEFAULT 'UNREVIEWED_NOT_CANONICAL',
       PRIMARY KEY(namespace_id,semantic_id,language_tag));
    CREATE TABLE metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL);
    """)


def _validated_projection(local: ReadOnlyTree, directory: str, slug: str,
                          state_sha: str) -> dict | None:
    root = local.root / directory
    profile_name = directory + "/.kristal/v11/authoring.json"
    pointer_name = directory + "/derived/semantic/active-resolution.json"
    has_profile = local.exists(profile_name)
    has_pointer = local.exists(pointer_name)
    if not has_profile:
        if has_pointer:
            _fail(f"{slug}: stale active pointer without an authoring profile")
        return None
    if not has_pointer:
        _fail(f"{slug}: missing V5.16 active pointer")
    pointer = local.read_json(pointer_name)
    if not isinstance(pointer, dict) or pointer.get("format") != POINTER_FORMAT:
        _fail(f"{slug}: unrecognized active pointer")
    relative = _safe_member(pointer.get("projection"))
    if not relative.startswith("derived/semantic/v516/active-") or not relative.endswith(".json"):
        _fail(f"{slug}: untrusted projection member")
    if pointer.get("state_index_sha256") != state_sha:
        _fail(f"{slug}: pointer bound to a different canonical state")
    if pointer.get("profile_sha256") != local.digest(profile_name):
        _fail(f"{slug}: pointer bound to a different authoring profile")
    payload = _real_path(root, Path(relative)).read_bytes()
    if _sha(payload) != pointer.get("projection_sha256"):
        _fail(f"{slug}: active projection SHA mismatch")
    projection = json.loads(payload)
    if (not isinstance(projection, dict) or projection.get("format") != PROJECTION_FORMAT or
            projection.get("owner_slug") != slug or
            projection.get("state_index_sha256") != state_sha or
            projection.get("authoring_profile_sha256") != pointer["profile_sha256"]):
        _fail(f"{slug}: active projection provenance mismatch")
    if not isinstance(projection.get("namespace_id"), str) or not projection["namespace_id"]:
        _fail(f"{slug}: missing active namespace")
    for role in projection.get("active_roles", {}).values():
        path = _safe_member(role.get("path"))
        if local.digest(directory + "/" + path) != role.get("sha256"):
            _fail(f"{slug}: changed active canonical role: {path}")
    if set(projection.get("active_roles", {})) != {"registry", "graph", "crosswalk", "catalog"}:
        _fail(f"{slug}: incomplete active canonical roles")
    for language in projection.get("languages", {}).values():
        for layer in language["layers"]:
            path = _safe_member(layer["path"])
            if local.digest(directory + "/" + path) != layer["sha256"]:
                _fail(f"{slug}: changed active lexical source: {path}")
    if not isinstance(projection.get("identities"), list):
        _fail(f"{slug}: malformed projected identities")
    return projection


def _ingest_active(db, namespace: str, slug: str, projection: dict, counts: Counter):
    for record in projection["identities"]:
        sid = record["id"]
        if not isinstance(sid, str) or not sid:
            _fail(f"{slug}: missing semantic ID")
        wikidata = record["wikidata"]
        accepted = wikidata["accepted_exact"]
        candidates = wikidata["candidate_exact"]
        if not isinstance(candidates, list) or len(candidates) != len(set(candidates)):
            _fail(f"{slug}: malformed candidate QIDs for {sid}")
        if accepted and accepted in candidates:
            # A historical redundant candidate is not an additional approval.
            counts["source_redundant_candidate_same_as_accepted"] += 1
        try:
            db.execute("INSERT INTO identity VALUES (?,?,?,?,?,?,?)",
                       (namespace, sid, slug, record["kind"], record["status"],
                        accepted, _json(candidates)))
        except sqlite3.IntegrityError as exc:
            _fail(f"duplicate active scoped semantic ID: {namespace}/{sid}: {exc}")
        counts["active_identities"] += 1
        if accepted:
            counts["recorded_accepted_wikidata"] += 1
        else:
            counts["without_recorded_accepted_wikidata"] += 1
        counts["candidate_wikidata_occurrences"] += len(candidates)
        for qid in candidates:
            db.execute("INSERT INTO candidate_wikidata(namespace_id,semantic_id,external_qid) VALUES (?,?,?)",
                       (namespace, sid, qid))
        if not record.get("labels"):
            counts["identities_without_active_label"] += 1
            if record["kind"] in ("entity", "property"):
                db.execute("INSERT INTO review_queue VALUES (?,?,?,?)",
                           (namespace, sid, "MISSING_ACTIVE_LABEL", _json({"owner_slug": slug})))
        else:
            counts["identities_with_active_label"] += 1
        if len(candidates) > 1 and not accepted:
            counts["ambiguous_candidate_ids"] += 1
            db.execute("INSERT INTO review_queue VALUES (?,?,?,?)",
                       (namespace, sid, "AMBIGUOUS_WIKIDATA_CANDIDATES",
                        _json({"owner_slug": slug, "candidates": candidates})))
        for language, label in record.get("labels", {}).items():
            term = label["preferred"]
            if not term or not _fold(term):
                _fail(f"{slug}: empty active label for {sid}/{language}")
            db.execute("INSERT INTO lexical VALUES (?,?,?,?,?,?,?)",
                       (namespace, sid, language, term, _fold(term), label["priority"],
                        _json({"layer_ids": label["layer_ids"],
                               "alternatives": label["alternatives"],
                               "provenance": "ACTIVE_CANONICAL_DICTIONARY"})))
            counts["active_language_labels"] += 1


def _lexical_hints(active: sqlite3.Connection, source: sqlite3.Connection,
                   counts: Counter):
    """Offer consensus from historical curated records only as review suggestions."""
    # Bound memory by consuming the old evidence in a sorted SQLite cursor.
    rows = source.execute("""SELECT namespace_id,semantic_id,language_tag,term,source_path
                             FROM lexical_occurrence
                             ORDER BY namespace_id,semantic_id,language_tag,source_path""")
    last_key = None
    variants = {}
    sample_paths = set()
    def emit():
        if last_key is None:
            return
        ns, sid, language = last_key
        if active.execute("SELECT 1 FROM identity WHERE namespace_id=? AND semantic_id=?",
                          (ns, sid)).fetchone() is None:
            return
        if active.execute("SELECT 1 FROM lexical WHERE namespace_id=? AND semantic_id=? AND language_tag=?",
                          (ns, sid, language)).fetchone() is not None:
            return
        if len(variants) != 1 or not next(iter(variants)):
            counts["unresolved_historical_lexical_conflicts"] += 1
            return
        folded = next(iter(variants))
        term = sorted(variants[folded], key=lambda x: (len(x), x))[0]
        active.execute("INSERT INTO historical_lexical_hint(namespace_id,semantic_id,language_tag,suggested_term,term_folded,source_paths_json) VALUES (?,?,?,?,?,?)",
                       (ns, sid, language, term, folded, _json(sorted(sample_paths))))
        counts["historical_unreviewed_lexical_hints"] += 1
    for ns, sid, language, term, source_path in rows:
        key = (ns, sid, language)
        if key != last_key:
            emit()
            last_key, variants, sample_paths = key, defaultdict(set), set()
        if isinstance(term, str) and _fold(term):
            variants[_fold(term)].add(term)
            sample_paths.add(source_path)
    emit()


def _public_preview(locals_root: Path, public_root: Path | None) -> dict:
    plan = {"format": REVIEW_FORMAT, "status": "NO_PUBLIC_WRITE_AUTHORIZED",
            "canonical_owner": "local_kristal_workspace", "public_role": "derived_hosted_read_surface",
            "qualifies_or_publishes": False, "workspaces_to_review": []}
    if public_root is None:
        plan["public_observation"] = "NOT_REQUESTED"
        return plan
    observed = audit_local_first(locals_root, public_root)
    if observed.get("counts", {}).get("duplicate_local_slug_groups"):
        _fail("duplicate local slug: public synchronization preview blocked")
    plan["public_observation"] = observed["status"]
    plan["observed_integrity_blockers"] = observed["blocker_count"]
    plan["public_counts"] = observed["counts"]
    for ws in observed["workspaces"]:
        findings = [f for f in ws["findings"] if f["kind"] not in
                    {"EXCLUDED_FROM_PUBLIC_READ_SURFACE"}]
        # A new v517 source is absent from public by design, but is *never*
        # silently included as an upload authorization.
        new_v517 = [f for f in ws["findings"]
                    if f["kind"] == "EXCLUDED_FROM_PUBLIC_READ_SURFACE" and
                    "/accepted-precedence-v517-" in f["path"]]
        if findings or new_v517 or not ws["hosted"]:
            plan["workspaces_to_review"].append({
                "slug": ws["slug"], "hosted": ws["hosted"],
                "differences": findings, "new_local_canonical_revisions_unpublished": new_v517,
                "release_gate": "INDEPENDENT_QUALIFICATION_AND_PER_KRISTAL_AUTHORIZATION_REQUIRED"})
    return plan


def build_active_federation(locals_root: Path, private_dir: Path, source_db: Path,
                            *, public_root: Path | None = None) -> dict:
    locals_root = Path(locals_root).resolve(strict=True)
    private_dir = Path(private_dir).resolve(strict=True)
    if not private_dir.is_dir() or private_dir == locals_root or private_dir in locals_root.parents or locals_root in private_dir.parents:
        _fail("private outputs must be outside all local Kristals")
    source_db = Path(source_db).resolve(strict=True)
    if source_db.suffix != ".sqlite" or private_dir not in source_db.parents:
        _fail("expected a private V5.16 source SQLite index")
    token = os.urandom(6).hex()
    output = _new_destination(private_dir / ("SEMANTIC_V518_" + token + ".sqlite"), locals_root)
    report_path = _new_destination(output.with_suffix(".json"), locals_root)
    sync_path = _new_destination(output.with_suffix(".public-plan.json"), locals_root)
    source = sqlite3.connect(f"file:{source_db.as_posix()}?mode=ro", uri=True)
    local = ReadOnlyTree(locals_root)
    db = None
    created = False
    counts = Counter()
    try:
        metadata = source.execute("SELECT value FROM metadata WHERE key='summary_json'").fetchone()
        if metadata is None or json.loads(metadata[0]).get("status") != "CANDIDATE_INTEGRITY_ONLY":
            _fail("source V5.14 inventory was not integrity-qualified even as a candidate")
        fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        os.close(fd)
        created = True
        db = sqlite3.connect(output)
        _schema(db)
        owners = {}
        expected = list(source.execute("SELECT slug,local_directory,state_index_sha256 FROM workspace ORDER BY slug"))
        observed_names = set(local.workspace_roots())
        if observed_names != {directory for _, directory, _ in expected}:
            _fail("local collection changed after the V5.16 source inventory")
        for slug, directory, state_sha in expected:
            if local.digest(directory + "/canon/state.index.json") != state_sha:
                _fail(f"{slug}: canonical index changed since inventory")
            complete = source.execute("SELECT COUNT(*) FROM revision WHERE slug=? AND kind='complete_core'",
                                      (slug,)).fetchone()[0]
            projection = _validated_projection(local, directory, slug, state_sha)
            if projection is None:
                counts["without_active_v11_profile"] += 1
                db.execute("INSERT INTO workspace VALUES (?,?,?,?,?,?,?,?)",
                           (slug, directory, None, 0, None, state_sha, None, complete))
                continue
            namespace = projection["namespace_id"]
            if namespace in owners and owners[namespace] != slug:
                _fail(f"two canonical owners claim namespace {namespace}: {owners[namespace]}, {slug}")
            owners[namespace] = slug
            pointer = local.read_json(directory + "/derived/semantic/active-resolution.json")
            db.execute("INSERT INTO workspace VALUES (?,?,?,?,?,?,?,?)",
                       (slug, directory, namespace, 1, pointer["profile_sha256"],
                        state_sha, pointer["projection_sha256"], complete))
            _ingest_active(db, namespace, slug, projection, counts)
            counts["active_v11_profiles"] += 1
        _lexical_hints(db, source, counts)
        counts["distinct_active_namespaces"] = len(owners)
        counts["local_workspaces"] = len(expected)
        plan = _public_preview(locals_root, public_root)
        summary = {
            "format": FORMAT, "status": "ACTIVE_DERIVED_FEDERATION_BUILT",
            "counts": dict(sorted(counts.items())),
            "source_v514_sqlite_sha256": _hash_file(source_db),
            "source_v514_sqlite": str(source_db), "database": str(output),
            "report": str(report_path), "public_plan": str(sync_path),
            "policy": {"identity_key": "namespace_id+semantic_id", "local_canonical_modified_by_v518": False,
                       "historical_lexical_hints_are_canonical": False,
                       "wikidata_auto_acceptance": False, "public_modified": False,
                       "public_publication_authorized": False,
                       "C1_C2_qualified": False}}
        db.execute("INSERT INTO metadata VALUES (?,?)", ("summary_json", _json(summary)))
        db.commit()
        db.close()
        db = None
        with report_path.open("x", encoding="utf8") as stream:
            json.dump(summary, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        with sync_path.open("x", encoding="utf8") as stream:
            json.dump(plan, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        return summary
    except Exception:
        if db is not None:
            db.close()
        if created and output.exists():
            output.unlink()
        raise
    finally:
        source.close()
        local.close()


def lookup(db_path: Path, term: str, *, namespace: str | None = None, limit=30):
    if not isinstance(term, str) or not term.strip() or not 1 <= limit <= 500:
        _fail("lookup needs a term/ID and a limit between 1 and 500")
    con = sqlite3.connect(f"file:{Path(db_path).resolve(strict=True).as_posix()}?mode=ro", uri=True)
    try:
        clauses = ["(i.semantic_id=? OR i.accepted_wikidata=? OR l.term_folded=? "
                   "OR EXISTS (SELECT 1 FROM candidate_wikidata c WHERE "
                   "c.namespace_id=i.namespace_id AND c.semantic_id=i.semantic_id AND c.external_qid=?) "
                   "OR EXISTS (SELECT 1 FROM historical_lexical_hint h WHERE "
                   "h.namespace_id=i.namespace_id AND h.semantic_id=i.semantic_id AND h.term_folded=?))"]
        args = [term.strip(), term.strip(), _fold(term), term.strip(), _fold(term)]
        if namespace is not None:
            clauses.append("i.namespace_id=?")
            args.append(namespace)
        rows = con.execute("""SELECT DISTINCT i.namespace_id,i.semantic_id,i.owner_slug,
                    i.kind,i.lifecycle_status,i.accepted_wikidata,i.candidate_wikidata_json
                    FROM identity i LEFT JOIN lexical l
                      ON l.namespace_id=i.namespace_id AND l.semantic_id=i.semantic_id
                    WHERE """ + " AND ".join(clauses) + " ORDER BY i.namespace_id,i.semantic_id LIMIT ?",
                    (*args, limit + 1)).fetchall()
        hits = []
        for ns, sid, owner, kind, status, accepted, candidates in rows[:limit]:
            labels = con.execute("SELECT language_tag,preferred_term FROM lexical WHERE namespace_id=? AND semantic_id=? ORDER BY language_tag", (ns, sid)).fetchall()
            hints = con.execute("SELECT language_tag,suggested_term FROM historical_lexical_hint WHERE namespace_id=? AND semantic_id=? ORDER BY language_tag", (ns, sid)).fetchall()
            hits.append({"namespace_id": ns, "semantic_id": sid, "owner_slug": owner,
                         "kind": kind, "status": status, "labels": dict(labels),
                         "historical_unreviewed_hints": dict(hints),
                         "wikidata_recorded_accepted": accepted,
                         "wikidata_candidates": json.loads(candidates)})
        return {"query": term, "truncated": len(rows) > limit, "results": hits}
    finally:
        con.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="V5.18 active local semantic federation + public draft")
    parser.add_argument("--locals", type=Path)
    parser.add_argument("--private-dir", type=Path)
    parser.add_argument("--public", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--lookup-db", type=Path)
    parser.add_argument("--lookup", type=str)
    parser.add_argument("--namespace-id", type=str)
    args = parser.parse_args(argv)
    try:
        if args.lookup is not None:
            if args.apply or args.lookup_db is None:
                _fail("--lookup needs --lookup-db and cannot use --apply")
            result = lookup(args.lookup_db, args.lookup, namespace=args.namespace_id)
        else:
            if args.locals is None or args.private_dir is None or not args.apply:
                _fail("local index regeneration requires --locals, --private-dir and --apply")
            local_refresh = refresh_v516(args.locals, args.private_dir, apply=True)
            result = build_active_federation(args.locals, args.private_dir,
                                             Path(local_refresh["source_db"]), public_root=args.public)
            result["v516_refresh"] = {"status": local_refresh["status"],
                                       "pointers_updated": local_refresh["pointers_updated"]}
    except (LocalFirstAuditError, OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
