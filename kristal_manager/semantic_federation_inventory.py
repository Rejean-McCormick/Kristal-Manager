"""V5.14: candidate federated semantic index from declared local Kristal canon.

Read-only inputs; deliberately no revision selection, source mutation, Wikidata
network access, canonical promotion or public release authority.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import unicodedata

from .local_first_audit import LocalFirstAuditError, ReadOnlyTree, _safe_path, _valid_slug


PROFILE = "koa.federated-semantic-observatory/0.1-candidate"
ROLE_NAMES = {
    "registry.json": "identity-registry", "identity-registry.json": "identity-registry",
    "graph.json": "semantic-graph", "semantic-graph.json": "semantic-graph",
    "crosswalk.json": "external-crosswalk", "external-crosswalk.json": "external-crosswalk",
    "dictionaries/catalog.json": "dictionary-catalog",
}
TYPES = {
    "identity-registry": "kristal_identity_registry",
    "semantic-graph": "kristal_semantic_graph",
    "external-crosswalk": "kristal_external_crosswalk",
    "dictionary-catalog": "kristal_dictionary_catalog",
}
REQUIRED = set(TYPES)


def _json(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fold(term: str) -> str:
    return unicodedata.normalize("NFKC", term).casefold()


def _revision_part(path: str):
    """Only v11 artifacts explicitly registered in state.index are eligible."""
    for base in ("canon/domain/v11/", "canon/v11/"):
        if path.startswith(base):
            remainder = path[len(base):]
            if remainder.startswith("updates/"):
                parts = remainder.split("/", 2)
                if len(parts) < 3:
                    return None
                return base + "updates/" + parts[1], parts[2]
            if remainder in ROLE_NAMES or remainder.startswith("dictionaries/"):
                return base.rstrip("/"), remainder
            revision, sep, rest = remainder.partition("/")
            if sep and revision and rest:
                return base + revision, rest
    return None


def _roles(artifacts: list[str]) -> dict[str, dict[str, list[str]]]:
    groups: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for path in artifacts:
        parsed = _revision_part(path)
        if parsed is None:
            continue
        revision_dir, relative = parsed
        role = ROLE_NAMES.get(relative, "auxiliary")
        groups[revision_dir][role].append(path)
    return {revision: dict(groups[revision]) for revision in sorted(groups)}


def _inside_git_checkout(parent: Path) -> bool:
    return any((ancestor / ".git").exists() for ancestor in (parent, *parent.parents))


def _new_destination(output: Path, source_root: Path) -> Path:
    dest = Path(output).expanduser().absolute()
    if dest.exists() or dest.is_symlink():
        raise LocalFirstAuditError(f"Refusing to replace an existing private index: {dest}")
    if not dest.parent.is_dir() or dest.parent.is_symlink():
        raise LocalFirstAuditError("Private output parent must be an existing real directory")
    parent = dest.parent.resolve(strict=True)
    source = Path(source_root).resolve(strict=True)
    if source.is_dir() and (parent == source or source in parent.parents):
        raise LocalFirstAuditError("Never write a derived index inside a canonical source tree")
    if _inside_git_checkout(parent):
        raise LocalFirstAuditError("Private output must not be inside a Git checkout")
    return parent / dest.name


def _create_schema(db: sqlite3.Connection):
    db.executescript("""
        PRAGMA foreign_keys = ON;
        CREATE TABLE workspace (
            slug TEXT PRIMARY KEY, local_directory TEXT NOT NULL,
            state_ref TEXT NOT NULL, state_index_sha256 TEXT NOT NULL
        );
        CREATE TABLE revision (
            slug TEXT NOT NULL, revision_dir TEXT NOT NULL,
            revision_label TEXT NOT NULL, kind TEXT NOT NULL,
            roles_json TEXT NOT NULL, sha256_json TEXT NOT NULL,
            namespace_id TEXT, selection_status TEXT NOT NULL DEFAULT 'unselected',
            PRIMARY KEY(slug,revision_dir)
        );
        CREATE TABLE identity_occurrence (
            namespace_id TEXT NOT NULL, semantic_id TEXT NOT NULL,
            kind TEXT NOT NULL, status TEXT, slug TEXT NOT NULL,
            revision_dir TEXT NOT NULL, source_path TEXT NOT NULL,
            record_json TEXT NOT NULL,
            PRIMARY KEY(namespace_id,semantic_id,slug,revision_dir)
        );
        CREATE INDEX identity_lookup ON identity_occurrence(semantic_id,namespace_id);
        CREATE TABLE lexical_occurrence (
            namespace_id TEXT NOT NULL, semantic_id TEXT NOT NULL,
            slug TEXT NOT NULL, revision_dir TEXT NOT NULL,
            language_tag TEXT NOT NULL, term TEXT NOT NULL, term_folded TEXT NOT NULL,
            layer_id TEXT NOT NULL, layer_priority INTEGER,
            source_path TEXT NOT NULL, record_json TEXT NOT NULL
        );
        CREATE INDEX lexical_term_lookup ON lexical_occurrence(term_folded);
        CREATE INDEX lexical_identity_lookup ON lexical_occurrence(namespace_id,semantic_id);
        CREATE TABLE external_alignment (
            namespace_id TEXT NOT NULL, semantic_id TEXT NOT NULL,
            slug TEXT NOT NULL, revision_dir TEXT NOT NULL,
            external_system TEXT NOT NULL, external_id TEXT NOT NULL,
            relation TEXT NOT NULL, status TEXT NOT NULL,
            review_method TEXT, source_path TEXT NOT NULL,
            record_json TEXT NOT NULL
        );
        CREATE INDEX alignment_external_lookup ON external_alignment(external_system,external_id);
        CREATE INDEX alignment_identity_lookup ON external_alignment(namespace_id,semantic_id);
        CREATE TABLE finding (
            severity TEXT NOT NULL, kind TEXT NOT NULL, slug TEXT,
            revision_dir TEXT, details_json TEXT NOT NULL
        );
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    """)


def _record_finding(db, counts, severity, kind, slug, revision, detail):
    counts["finding_" + severity.lower()] += 1
    db.execute("INSERT INTO finding VALUES (?,?,?,?,?)", (severity,kind,slug,revision,_json(detail)))


def _load_role(local, db, counts, slug, root, revision, role, path):
    """Ingest one typed role, preserving raw records and scoped identities."""
    # Large v11 graphs contain assertions; their type and namespace must
    # nonetheless be checked even though this index does not ingest assertions.
    document = local.read_json(root + "/" + path,limit=32_000_000 if role == "semantic-graph" else 10_000_000)
    if not isinstance(document, dict) or document.get("artifact_type") != TYPES[role]:
        _record_finding(db,counts,"BLOCK","ROLE_TYPE_MISMATCH",slug,revision,
                        {"role":role,"path":path,"artifact_type":
                         document.get("artifact_type") if isinstance(document,dict) else None})
        return None
    namespace = document.get("namespace_id")
    if role in ("identity-registry", "semantic-graph", "dictionary-catalog"):
        if not isinstance(namespace,str) or not namespace:
            _record_finding(db,counts,"BLOCK","MISSING_NAMESPACE",slug,revision,{"path":path})
            return None
    if role == "identity-registry":
        rows = document.get("identities")
        if not isinstance(rows,list):
            raise LocalFirstAuditError(f"Malformed registry identities: {root}/{path}")
        for record in rows:
            if not isinstance(record,dict) or not isinstance(record.get("id"),str):
                raise LocalFirstAuditError(f"Malformed identity: {root}/{path}")
            semantic_id = record["id"]
            kind = record.get("kind", "unknown")
            if not semantic_id.startswith(("KQ", "KP", "KA", "KS")):
                _record_finding(db,counts,"REVIEW","UNEXPECTED_ID_FORMAT",slug,revision,
                                {"path":path,"semantic_id":semantic_id})
            try:
                db.execute("INSERT INTO identity_occurrence VALUES (?,?,?,?,?,?,?,?)",
                           (namespace,semantic_id,kind,record.get("status"),slug,revision,path,_json(record)))
                counts["identity_occurrences"] += 1
            except sqlite3.IntegrityError:
                _record_finding(db,counts,"BLOCK","DUPLICATE_ID_IN_REVISION",slug,revision,
                                {"namespace_id":namespace,"semantic_id":semantic_id,"path":path})
    elif role == "external-crosswalk":
        mappings = document.get("mappings")
        if not isinstance(mappings,list):
            raise LocalFirstAuditError(f"Malformed crosswalk: {root}/{path}")
        for m in mappings:
            if not isinstance(m,dict):
                raise LocalFirstAuditError(f"Malformed crosswalk mapping: {root}/{path}")
            ref = m.get("local_ref") or {}
            external = m.get("external_ref") or {}
            if not isinstance(ref,dict) or not isinstance(external,dict):
                raise LocalFirstAuditError(f"Malformed crosswalk reference: {root}/{path}")
            ns, sid = ref.get("namespace_id"), ref.get("id")
            ext, qid = external.get("system"), external.get("id")
            if not all(isinstance(v,str) and v for v in (ns,sid,ext,qid)):
                _record_finding(db,counts,"BLOCK","UNSCOPED_EXTERNAL_MAPPING",slug,revision,
                                {"path":path,"mapping_id":m.get("mapping_id")})
                continue
            relation,status = str(m.get("relation","unknown")),str(m.get("status","unknown"))
            review = m.get("review")
            method = review.get("method") if isinstance(review,dict) else None
            db.execute("INSERT INTO external_alignment VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       (ns,sid,slug,revision,ext,qid,relation,status,method,path,_json(m)))
            counts["external_alignment_occurrences"] += 1
            if relation == "exactMatch" and status == "accepted" and method == "audited_rule":
                counts["recorded_accepted_exactmatch_audited_rule"] += 1
    elif role == "dictionary-catalog":
        languages = document.get("languages")
        if not isinstance(languages,list):
            raise LocalFirstAuditError(f"Malformed dictionary catalog: {root}/{path}")
        catalog_dir = path.rsplit("/",1)[0]
        for language in languages:
            if not isinstance(language,dict) or not isinstance(language.get("layers"),list):
                raise LocalFirstAuditError(f"Malformed language in catalog: {root}/{path}")
            tag = language.get("tag")
            if not isinstance(tag,str) or not tag:
                _record_finding(db,counts,"BLOCK","MISSING_LANGUAGE_TAG",slug,revision,{"path":path})
                continue
            counts["catalog_language_memberships"] += 1
            for layer in language["layers"]:
                if not isinstance(layer,dict):
                    raise LocalFirstAuditError(f"Malformed dictionary layer: {root}/{path}")
                rel = _safe_path(layer.get("path"))
                layer_path = catalog_dir + "/" + rel
                source = root + "/" + layer_path
                if not local.exists(source):
                    _record_finding(db,counts,"BLOCK","MISSING_LEXICAL_LAYER",slug,revision,
                                    {"path":layer_path})
                    continue
                observed = local.digest(source)
                pinned = str(layer.get("sha256", "")).removeprefix("sha256:")
                if observed != pinned:
                    _record_finding(db,counts,"BLOCK","LEXICAL_LAYER_SHA_MISMATCH",slug,revision,
                                    {"path":layer_path,"expected":pinned,"observed":observed})
                    continue
                if layer_path.endswith(".jsonl"):
                    # JSONL is an ordinary Wikidata lexical layer, not a JSON
                    # document. Stream bounded lines and preserve each record.
                    records = []
                    with local.open(source) as stream:
                        for number, line in enumerate(stream, 1):
                            if len(line) > 1_000_000:
                                raise LocalFirstAuditError(f"Oversize JSONL line: {source}:{number}")
                            if not line.strip():
                                continue
                            try:
                                record = json.loads(line.decode("utf-8-sig"))
                            except (UnicodeError,json.JSONDecodeError) as exc:
                                raise LocalFirstAuditError(f"Malformed JSONL record: {source}:{number}") from exc
                            if not isinstance(record,dict):
                                raise LocalFirstAuditError(f"Malformed JSONL object: {source}:{number}")
                            records.append(record)
                    counts["verified_jsonl_layers"] += 1
                else:
                    lexical = local.read_json(source)
                    if not isinstance(lexical,dict) or not isinstance(lexical.get("entries"),list):
                        raise LocalFirstAuditError(f"Malformed lexical layer: {source}")
                    if lexical.get("namespace_id") != namespace:
                        _record_finding(db,counts,"BLOCK","LEXICAL_NAMESPACE_MISMATCH",slug,revision,
                                        {"path":layer_path,"catalog_namespace":namespace,
                                         "layer_namespace":lexical.get("namespace_id")})
                        continue
                    records = lexical["entries"]
                layer_id = str(layer.get("layer_id",rel))
                priority = layer.get("priority") if isinstance(layer.get("priority"),int) else None
                counts["verified_lexical_layers"] += 1
                for record in records:
                    if not isinstance(record,dict):
                        raise LocalFirstAuditError(f"Malformed lexical record: {source}")
                    if layer_path.endswith(".jsonl") and (record.get("namespace_id") != namespace or record.get("language") != tag):
                        _record_finding(db,counts,"BLOCK","JSONL_RECORD_SCOPE_MISMATCH",slug,revision,
                                        {"path":layer_path,"semantic_id":record.get("semantic_id")})
                        continue
                    sid = record.get("semantic_id")
                    term = record.get("preferred_term")
                    if not isinstance(sid,str) or not isinstance(term,str) or not term:
                        _record_finding(db,counts,"REVIEW","INCOMPLETE_LEXICAL_RECORD",slug,revision,
                                        {"path":layer_path})
                        continue
                    db.execute("INSERT INTO lexical_occurrence VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                               (namespace,sid,slug,revision,tag,term,_fold(term),layer_id,priority,
                                layer_path,_json(record)))
                    counts["lexical_occurrences"] += 1
    return namespace


def build_semantic_inventory(locals_root: Path, database: Path, report_path: Path | None = None) -> dict:
    """Create a private candidate SQLite index. Inputs remain completely untouched."""
    output = _new_destination(database,locals_root)
    report_output = _new_destination(report_path,locals_root) if report_path else None
    if report_output and (output == report_output):
        raise LocalFirstAuditError("SQLite index and JSON report must have distinct paths")
    local = ReadOnlyTree(locals_root)
    db = None
    created = False
    counts = Counter()
    try:
        workspaces = []
        seen = set()
        for directory in local.workspace_roots():
            workspace = local.read_json(directory + "/kristal.workspace.json")
            if not isinstance(workspace,dict):
                raise LocalFirstAuditError(f"Invalid workspace: {directory}")
            slug = _valid_slug(workspace.get("slug"))
            if slug in seen:
                raise LocalFirstAuditError(f"Duplicate local slug: {slug}; no federated index created")
            seen.add(slug)
            workspaces.append((directory,slug,workspace))
        fd = os.open(output,os.O_CREAT|os.O_EXCL|os.O_RDWR,0o600)
        os.close(fd)
        created = True
        db = sqlite3.connect(output)
        _create_schema(db)
        for root,slug,workspace in workspaces:
            state_path = root + "/canon/state.index.json"
            state = local.read_json(state_path)
            if not isinstance(state,dict) or not isinstance(state.get("canonical_artifacts"),list):
                raise LocalFirstAuditError(f"Invalid state.index: {root}")
            db.execute("INSERT INTO workspace VALUES (?,?,?,?)",
                       (slug,root,workspace["state_ref"],local.digest(state_path)))
            counts["local_workspaces"] += 1
            artifact_paths = []
            for entry in state["canonical_artifacts"]:
                if not isinstance(entry,dict):
                    raise LocalFirstAuditError(f"Malformed state.index entry: {root}")
                artifact_paths.append(_safe_path(entry.get("path")))
            if len(artifact_paths) != len(set(artifact_paths)):
                raise LocalFirstAuditError(f"Duplicate canonical path: {root}")
            for rev, role_paths in _roles(artifact_paths).items():
                paths = {}
                hashes = {}
                for role, possible in role_paths.items():
                    if role != "auxiliary" and len(possible) > 1:
                        _record_finding(db,counts,"BLOCK","DUPLICATE_ROLE_VARIANTS",slug,rev,
                                        {"role":role,"paths":possible})
                        continue
                    paths[role] = possible
                    for p in possible:
                        source = root + "/" + p
                        if not local.exists(source):
                            _record_finding(db,counts,"BLOCK","MISSING_DECLARED_ARTIFACT",slug,rev,{"path":p})
                            continue
                        hashes[p] = local.digest(source)
                core_roles = set(paths) & REQUIRED
                kind = ("complete_core" if core_roles == REQUIRED else
                        "dictionary_only" if core_roles == {"dictionary-catalog"} else "incomplete_core")
                rev_label = rev.rsplit("/",1)[-1]
                db.execute("INSERT INTO revision(slug,revision_dir,revision_label,kind,roles_json,sha256_json) VALUES (?,?,?,?,?,?)",
                           (slug,rev,rev_label,kind,_json(paths),_json(hashes)))
                counts["revision_groups"] += 1
                counts["revision_" + kind] += 1
                namespaces = {}
                for role in ("identity-registry","semantic-graph","external-crosswalk","dictionary-catalog"):
                    for p in paths.get(role,[]):
                        if p in hashes:
                            namespaces[role] = _load_role(local,db,counts,slug,root,rev,role,p)
                nonempty = {ns for ns in namespaces.values() if ns is not None}
                if len(nonempty) > 1:
                    _record_finding(db,counts,"BLOCK","REVISION_NAMESPACE_CONFLICT",slug,rev,
                                    {"namespaces":namespaces})
                if nonempty:
                    db.execute("UPDATE revision SET namespace_id=? WHERE slug=? AND revision_dir=?",
                               (sorted(nonempty)[0],slug,rev))
        # A namespace-qualified ID occurring in several *revisions* is normal;
        # the same pair claimed by different Kristal owner slugs is not.
        duplicates = db.execute("""
            SELECT namespace_id,semantic_id,COUNT(DISTINCT slug) FROM identity_occurrence
            GROUP BY namespace_id,semantic_id HAVING COUNT(DISTINCT slug)>1
        """).fetchall()
        for namespace,sid,owner_count in duplicates:
            _record_finding(db,counts,"BLOCK","CROSS_OWNER_SCOPED_ID_COLLISION",None,None,
                            {"namespace_id":namespace,"semantic_id":sid,"owner_count":owner_count})
        counts["distinct_scoped_identities"] = db.execute("""
            SELECT COUNT(*) FROM (SELECT 1 FROM identity_occurrence GROUP BY namespace_id,semantic_id)
        """).fetchone()[0]
        counts["distinct_identity_namespaces"] = db.execute(
            "SELECT COUNT(DISTINCT namespace_id) FROM identity_occurrence").fetchone()[0]
        counts["selected_revisions"] = 0
        summary = {"profile":PROFILE,"status":"BLOCKED_INTEGRITY" if counts["finding_block"] else "CANDIDATE_INTEGRITY_ONLY",
                   "counts":dict(sorted(counts.items())),
                   "policy":{"canonical_source":"local_kristal_workspace",
                             "globally_authoritative":False,"automatic_revision_selection":False,
                             "wikidata_exactmatch_approved_by_this_index":False,
                             "public_write_authorized":False,"independent_C1_C2_qualified":False},
                   "database":str(output)}
        db.execute("INSERT INTO metadata VALUES (?,?)",("summary_json",_json(summary)))
        db.commit()
        db.close()
        db = None
        if report_output:
            fd = os.open(report_output,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            with os.fdopen(fd,"w",encoding="utf-8") as stream:
                json.dump(summary,stream,ensure_ascii=False,indent=2)
                stream.write("\n")
            summary["report_path"] = str(report_output)
        return summary
    except Exception:
        if db is not None:
            db.close()
        if created and output.exists():
            output.unlink()
        raise
    finally:
        local.close()


def query_semantic_inventory(database: Path, query: str, limit: int = 30,
                             namespace_id: str | None = None) -> dict:
    """Return every matching revision with provenance; never choose an identity."""
    if not isinstance(query,str) or not query.strip() or not 1 <= limit <= 500:
        raise LocalFirstAuditError("Query must be nonempty and limit 1..500")
    if namespace_id is not None and (not isinstance(namespace_id,str) or not namespace_id):
        raise LocalFirstAuditError("Nonempty namespace_id required when filtering")
    source = Path(database)
    if not source.is_file() or source.is_symlink():
        raise LocalFirstAuditError("Exact private semantic index file required")
    db = sqlite3.connect(f"file:{source.resolve().as_posix()}?mode=ro",uri=True)
    db.row_factory = sqlite3.Row
    try:
        summary_row = db.execute("SELECT value FROM metadata WHERE key='summary_json'").fetchone()
        if not summary_row or json.loads(summary_row[0]).get("profile") != PROFILE:
            raise LocalFirstAuditError("Unknown semantic index profile")
        integrity = json.loads(summary_row[0])["status"]
        folded = _fold(query.strip())
        q = query.strip()
        scoped_filter = " AND namespace_id=?" if namespace_id else ""
        def params(*items):
            return (*items,namespace_id,limit) if namespace_id else (*items,limit)
        identities = [dict(row) for row in db.execute("""
            SELECT namespace_id,semantic_id,kind,status,slug,revision_dir,source_path,record_json
            FROM identity_occurrence WHERE semantic_id=?"""+scoped_filter+" LIMIT ?",
            params(q))]
        lexical = [dict(row) for row in db.execute("""
            SELECT namespace_id,semantic_id,slug,revision_dir,language_tag,term,layer_id,
                   layer_priority,source_path,record_json
            FROM lexical_occurrence WHERE (term_folded=? OR semantic_id=?)"""+scoped_filter+" LIMIT ?",
            params(folded,q))]
        alignment = [dict(row) for row in db.execute("""
            SELECT namespace_id,semantic_id,slug,revision_dir,external_system,external_id,
                   relation,status,review_method,source_path,record_json
            FROM external_alignment WHERE (external_id=? OR semantic_id=?)"""+scoped_filter+" LIMIT ?",
            params(q,q))]
        return {"profile":PROFILE,"query":q,"namespace_filter":namespace_id,
                "integrity_status":integrity,"qualification":"UNSELECTED_DERIVED_OCCURRENCES",
                "limit_per_category":limit,"identity_occurrences":identities,
                "lexical_occurrences":lexical,"external_alignments":alignment}
    finally:
        db.close()
