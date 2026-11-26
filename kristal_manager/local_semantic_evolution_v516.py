"""Materialize an active, reversible semantic reading view inside local Kristals.

V5.16 is an operational *derived* correction: the Authoring Kit's actual v11
profile decides the four active roles. Historical candidate revisions do not
silently compete with that profile. No canonical JSON, state index, source
crosswalk status, public tree or published state is modified.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3

from .local_first_audit import LocalFirstAuditError, ReadOnlyTree
from .semantic_federation_inventory import build_semantic_inventory


FORMAT = "koa.kristal-active-semantic-projection/1.0"
POINTER_FORMAT = "koa.kristal-active-semantic-pointer/1.0"
PROFILE_FORMAT = "kristal.authoring-v11-profile/1.0"
ROLES = {
    "registry": "identity-registry",
    "graph": "semantic-graph",
    "crosswalk": "external-crosswalk",
    "catalog": "dictionary-catalog",
}
PROFILE_KEYS = {"format", "semantic_profile", *ROLES}
OUTPUT_POINTER = Path("derived/semantic/active-resolution.json")


def _bytes(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _fail(message):
    raise LocalFirstAuditError("V5.16: " + message)


def _safe_member(path):
    if not isinstance(path, str) or not path or "\\" in path or path.startswith("/"):
        _fail("unsafe profile path")
    parts = path.split("/")
    if any(x in ("", ".", "..") for x in parts) or ":" in path:
        _fail("unsafe profile path")
    return path


def _real_path(root: Path, relative: Path, allow_absent=False) -> Path:
    """Validate every existing segment; prevent symlink/junction traversal."""
    if relative.is_absolute() or ".." in relative.parts:
        _fail("output path traversal")
    probe = root
    for part in relative.parts:
        probe = probe / part
        if probe.is_symlink():
            _fail(f"refusing symlink at {probe}")
        if probe.exists() and probe != root / relative and not probe.is_dir():
            _fail(f"non-directory output ancestor: {probe}")
    if not allow_absent and not probe.is_file():
        _fail(f"missing expected local file: {probe}")
    return probe


def _pick_active(local: ReadOnlyTree, root: str, slug: str, revision_rows) -> tuple[dict, dict] | None:
    profile_path = root + "/.kristal/v11/authoring.json"
    if not local.exists(profile_path):
        return None
    profile = local.read_json(profile_path)
    if not isinstance(profile, dict) or set(profile) != PROFILE_KEYS:
        _fail(f"{slug}: invalid authoring profile keys")
    if profile["format"] != PROFILE_FORMAT or profile["semantic_profile"] != "kristal.semantic-identity/11.0":
        _fail(f"{slug}: unexpected authoring profile")
    role_info = {}
    for key, role in ROLES.items():
        chosen = _safe_member(profile[key])
        found = [(revision, hashes[chosen]) for revision, roles, hashes in revision_rows
                 if chosen in roles.get(role, []) and chosen in hashes]
        if len(found) != 1:
            _fail(f"{slug}: selected {role} is not uniquely registered in canonical index")
        if local.digest(root + "/" + chosen) != found[0][1]:
            _fail(f"{slug}: selected {role} changed during inventory")
        role_info[key] = {"path": chosen, "sha256": found[0][1], "revision_dir": found[0][0]}
    return profile, {"profile_sha256": local.digest(profile_path), "roles": role_info}


def _load_active(db: sqlite3.Connection, local: ReadOnlyTree, root: str,
                 slug: str, state_sha: str, profile: dict, selection: dict) -> dict:
    roles = selection["roles"]
    registry_path = roles["registry"]["path"]
    crosswalk_path = roles["crosswalk"]["path"]
    catalog_path = roles["catalog"]["path"]
    graph_path = roles["graph"]["path"]
    catalog = local.read_json(root + "/" + catalog_path)
    registry = local.read_json(root + "/" + registry_path)
    graph = local.read_json(root + "/" + graph_path, limit=32_000_000)
    crosswalk = local.read_json(root + "/" + crosswalk_path)
    documents = ((registry, "kristal_identity_registry"), (graph, "kristal_semantic_graph"),
                 (crosswalk, "kristal_external_crosswalk"), (catalog, "kristal_dictionary_catalog"))
    if any(not isinstance(doc, dict) or doc.get("artifact_type") != typ for doc, typ in documents):
        _fail(f"{slug}: profile role type mismatch")
    namespaces = {registry.get("namespace_id"), graph.get("namespace_id"), catalog.get("namespace_id")}
    if len(namespaces) != 1 or not next(iter(namespaces)):
        _fail(f"{slug}: active profile namespace mismatch")
    namespace = namespaces.pop()

    identities = {}
    for row in db.execute("""SELECT namespace_id,semantic_id,kind,status,record_json
          FROM identity_occurrence WHERE slug=? AND source_path=? ORDER BY semantic_id""",
          (slug, registry_path)):
        ns, sid, kind, status, record = row
        if ns != namespace or sid in identities:
            _fail(f"{slug}: duplicate/mismatched active scoped ID {sid}")
        identities[sid] = {"id": sid, "kind": kind, "status": status,
                           "labels": {}, "wikidata": {"accepted_exact": None, "candidate_exact": []}}
    if len(identities) != len(registry.get("identities", [])):
        _fail(f"{slug}: active registry did not match federated evidence")

    accepted_external = {}
    accepted_local = {}
    candidates = defaultdict(set)
    for row in db.execute("""SELECT namespace_id,semantic_id,external_system,external_id,
          relation,status,record_json FROM external_alignment
          WHERE slug=? AND source_path=? ORDER BY semantic_id,external_id""",
          (slug, crosswalk_path)):
        ns, sid, system, eid, relation, status, record_json = row
        if ns != namespace or sid not in identities or system != "wikidata":
            _fail(f"{slug}: invalid active crosswalk identity")
        if relation != "exactMatch":
            continue
        if status == "accepted":
            evidence = json.loads(record_json).get("review", {}).get("evidence_refs", [])
            if not evidence or any(identities.get(ref, {}).get("kind") != "source" for ref in evidence):
                _fail(f"{slug}: accepted exactMatch without declared source evidence")
            if (sid in accepted_local and accepted_local[sid] != eid) or (eid in accepted_external and accepted_external[eid] != sid):
                _fail(f"{slug}: conflicting accepted exactMatch")
            accepted_local[sid] = eid
            accepted_external[eid] = sid
        elif status == "candidate":
            candidates[sid].add(eid)
    for sid in identities:
        identities[sid]["wikidata"] = {
            "accepted_exact": accepted_local.get(sid),
            "candidate_exact": sorted(candidates.get(sid, set())),
        }

    layers = {}
    languages = {}
    catalog_dir = catalog_path.rsplit("/", 1)[0]
    for language in catalog.get("languages", []):
        tag = language["tag"]
        if tag in languages:
            _fail(f"{slug}: duplicate catalog language")
        languages[tag] = {"fallbacks": language.get("fallbacks", []), "layers": []}
        for layer in language.get("layers", []):
            layer_path = catalog_dir + "/" + _safe_member(layer["path"])
            if layer_path in layers:
                _fail(f"{slug}: duplicate active catalog layer path")
            layers[layer_path] = (tag, layer["layer_id"], layer["priority"])
            languages[tag]["layers"].append({"id": layer["layer_id"], "priority": layer["priority"],
                                               "path": layer_path, "sha256": layer["sha256"]})
            if local.digest(root + "/" + layer_path) != layer["sha256"]:
                _fail(f"{slug}: declared dictionary layer SHA mismatch")

    all_labels = defaultdict(lambda: defaultdict(list))
    for row in db.execute("""SELECT namespace_id,semantic_id,language_tag,term,layer_id,
          layer_priority,source_path FROM lexical_occurrence
          WHERE slug=? AND revision_dir=? ORDER BY semantic_id,language_tag,layer_priority DESC""",
          (slug, roles["catalog"]["revision_dir"])):
        ns, sid, tag, term, lid, priority, path = row
        if path not in layers:
            continue  # Historical layer in the same revision, not in active catalog.
        if (tag, lid, priority) != layers[path] or ns != namespace or sid not in identities:
            _fail(f"{slug}: active dictionary layer points outside selected namespace")
        all_labels[sid][tag].append((priority, term, lid))
    conflicted = 0
    for sid, language_terms in all_labels.items():
        for tag, terms in language_terms.items():
            highest = max(row[0] for row in terms)
            top = {row[1] for row in terms if row[0] == highest}
            if len(top) > 1:
                _fail(f"{slug}: conflicting equal-priority terms for {sid}/{tag}")
            preferred = next(iter(top))
            alternatives = sorted({row[1] for row in terms if row[1] != preferred})
            identities[sid]["labels"][tag] = {
                "preferred": preferred, "priority": highest,
                "layer_ids": sorted({row[2] for row in terms if row[0] == highest}),
                "alternatives": alternatives,
            }
            if alternatives:
                conflicted += 1
    ambiguous = sum(1 for sid, qs in candidates.items() if len(qs) > 1 and sid not in accepted_local)
    return {
        "format": FORMAT,
        "owner_slug": slug,
        "namespace_id": namespace,
        "state_index_sha256": state_sha,
        "authoring_profile_sha256": selection["profile_sha256"],
        "active_roles": roles,
        "languages": languages,
        "recorded_status_semantics": {"accepted_exact": "source-recorded, not independently qualified",
                                      "candidate_exact": "unapproved proposals, may be ambiguous"},
        "counts": {"identities": len(identities), "with_labels": len(all_labels),
                   "with_accepted_wikidata": len(accepted_local),
                   "ambiguous_candidate_ids": ambiguous,
                   "identities_with_alternative_terms": conflicted},
        "identities": [identities[sid] for sid in sorted(identities)],
    }


def _prepare(locals_root: Path, db_path: Path) -> tuple[list[tuple[Path, bytes, bytes]], dict]:
    local = ReadOnlyTree(locals_root)
    db = sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)
    prepared = []
    total = Counter()
    selected = []
    try:
        for slug, directory, _, state_sha in db.execute("SELECT slug,local_directory,state_ref,state_index_sha256 FROM workspace ORDER BY slug"):
            local_root = (locals_root / directory)
            if not local_root.is_dir() or local_root.is_symlink():
                _fail(f"{slug}: not a real local workspace directory")
            if local.digest(directory + "/canon/state.index.json") != state_sha:
                _fail(f"{slug}: canonical state changed during inventory")
            revisions = [(rev, json.loads(roles), json.loads(hashes)) for rev, roles, hashes in db.execute(
                "SELECT revision_dir,roles_json,sha256_json FROM revision WHERE slug=?", (slug,))]
            active = _pick_active(local, directory, slug, revisions)
            if active is None:
                total["without_active_v11_profile"] += 1
                continue
            profile, selection = active
            projection = _load_active(db, local, directory, slug, state_sha, profile, selection)
            if local.digest(directory + "/canon/state.index.json") != state_sha:
                _fail(f"{slug}: canonical state changed while preparing projection")
            contents = _bytes(projection)
            content_sha = sha256(contents).hexdigest()
            rel = Path("derived/semantic/v516") / ("active-" + content_sha[:20] + ".json")
            pointer = _bytes({"format": POINTER_FORMAT, "profile_sha256": selection["profile_sha256"],
                              "projection": rel.as_posix(), "projection_sha256": content_sha,
                              "state_index_sha256": state_sha})
            prepared.append((local_root, rel, contents, pointer))
            total.update(projection["counts"])
            total["with_active_v11_profile"] += 1
            selected.append({"slug": slug, "namespace_id": projection["namespace_id"],
                             "profile_sha256": selection["profile_sha256"],
                             "projection_sha256": content_sha, "counts": projection["counts"]})
    finally:
        db.close()
        local.close()
    return prepared, {"counts": dict(sorted(total.items())), "workspaces": selected}


def _commit(prepared, backup_root: Path):
    """Back up all pointers first, then update versioned derived files; rollback on errors."""
    jobs = []
    for root, rel, contents, pointer in prepared:
        projection = json.loads(contents)
        if sha256(_real_path(root, Path("canon/state.index.json")).read_bytes()).hexdigest() != projection["state_index_sha256"]:
            _fail(f"canonical state changed before commit: {root}")
        if sha256(_real_path(root, Path(".kristal/v11/authoring.json")).read_bytes()).hexdigest() != projection["authoring_profile_sha256"]:
            _fail(f"authoring selection changed before commit: {root}")
        for role in projection["active_roles"].values():
            if sha256(_real_path(root, Path(role["path"])).read_bytes()).hexdigest() != role["sha256"]:
                _fail(f"active canonical artifact changed before commit: {root}")
        for language in projection["languages"].values():
            for layer in language["layers"]:
                if sha256(_real_path(root, Path(layer["path"])).read_bytes()).hexdigest() != layer["sha256"]:
                    _fail(f"active lexical layer changed before commit: {root}")
        versioned = _real_path(root, rel, allow_absent=True)
        active = _real_path(root, OUTPUT_POINTER, allow_absent=True)
        if versioned.exists() and versioned.read_bytes() != contents:
            _fail(f"existing versioned semantic projection differs: {versioned}")
        old = active.read_bytes() if active.exists() else None
        if old is not None:
            try:
                if json.loads(old).get("format") != POINTER_FORMAT:
                    _fail(f"unmanaged active-resolution pointer: {active}")
            except (ValueError, AttributeError) as exc:
                _fail(f"invalid active-resolution pointer: {active}: {exc}")
        jobs.append((root, versioned, active, contents, pointer, old))
    # No write to a local workspace before all targets have been checked.
    backup_root.mkdir(parents=True, exist_ok=False)
    for root, _, _, _, _, old in jobs:
        if old is not None:
            target = backup_root / (root.name + ".active-resolution.json")
            with target.open("xb") as stream:
                stream.write(old)
    committed = []
    try:
        for root, versioned, active, contents, pointer, old in jobs:
            versioned.parent.mkdir(parents=True, exist_ok=True)
            active.parent.mkdir(parents=True, exist_ok=True)
            if not versioned.exists():
                with versioned.open("xb") as stream:
                    stream.write(contents)
            if versioned.read_bytes() != contents:
                _fail(f"post-write projection SHA mismatch: {versioned}")
            if old != pointer:
                pending = active.with_name(active.name + ".v516-new")
                if pending.exists() or pending.is_symlink():
                    _fail(f"pending pointer exists: {pending}")
                try:
                    with pending.open("xb") as stream:
                        stream.write(pointer)
                    os.replace(pending, active)
                finally:
                    pending.unlink(missing_ok=True)
            committed.append((active, old))
    except Exception:
        # Versioned files are recoverable and left as unreferenced history.
        for active, old in reversed(committed):
            if old is None:
                active.unlink(missing_ok=True)
            else:
                restore = active.with_name(active.name + ".v516-restore")
                with restore.open("xb") as stream:
                    stream.write(old)
                os.replace(restore, active)
        raise
    return {"pointers_updated": sum(old != pointer for _, _, _, _, pointer, old in jobs),
            "versioned_projections": len(jobs)}


def evolve(locals_root: Path, private_dir: Path, *, apply=False) -> dict:
    locals_root = Path(locals_root).resolve(strict=True)
    private_dir = Path(private_dir).resolve(strict=True)
    if not locals_root.is_dir() or not private_dir.is_dir():
        _fail("expected real local and private directories")
    if private_dir == locals_root or locals_root in private_dir.parents or private_dir in locals_root.parents:
        _fail("private directory overlaps local source")
    run_id = "SEMANTIC_V516_" + os.urandom(6).hex()
    db_path = private_dir / (run_id + ".sqlite")
    source_report = private_dir / (run_id + ".v514.json")
    report_path = private_dir / (run_id + ".json")
    source = build_semantic_inventory(locals_root, db_path, source_report)
    if source.get("status") != "CANDIDATE_INTEGRITY_ONLY":
        _fail("source inventory failed integrity; local projection unchanged")
    prepared, summary = _prepare(locals_root, db_path)
    summary.update({"format": "koa.kristal-local-evolution/0.1", "status": "DRY_RUN", "applied": False,
                    "source_db": str(db_path), "source_report": str(source_report),
                    "report": str(report_path), "canonical_modified": False,
                    "public_modified": False, "automatic_wikidata_acceptance": False,
                    "authoring_profiles_selected_by_consumer": len(prepared)})
    if apply:
        backup = private_dir / (run_id + ".backups")
        summary.update(_commit(prepared, backup))
        summary["status"] = "LOCAL_DERIVED_UPDATED"
        summary["applied"] = True
        summary["backup_dir"] = str(backup)
    with report_path.open("x", encoding="utf-8") as out:
        json.dump(summary, out, ensure_ascii=False, indent=2)
        out.write("\n")
    return summary


def lookup(locals_root: Path, query: str, *, namespace=None, limit=30) -> dict:
    """Read only local active v11 projections; never fall back to historical candidates."""
    if not query or not query.strip() or not 1 <= limit <= 500:
        _fail("lookup requires a word/ID and limit 1..500")
    locals_root = Path(locals_root).resolve(strict=True)
    if not locals_root.is_dir():
        _fail("lookup requires an existing locals directory")
    folded = query.casefold().strip()
    found = []
    observed = 0
    for root in sorted(locals_root.iterdir()):
        if not root.name.startswith("Kristal-") or not root.is_dir() or root.is_symlink():
            continue
        pointer_path = _real_path(root, OUTPUT_POINTER, allow_absent=True)
        if not pointer_path.is_file():
            continue
        pointer = json.loads(pointer_path.read_bytes())
        if not isinstance(pointer, dict) or pointer.get("format") != POINTER_FORMAT:
            _fail(f"unrecognized active projection pointer: {root}")
        path = Path(_safe_member(pointer["projection"]))
        if path.parent.as_posix() != "derived/semantic/v516":
            _fail(f"untrusted active projection path: {root}")
        payload = _real_path(root, path).read_bytes()
        if sha256(payload).hexdigest() != pointer["projection_sha256"]:
            _fail(f"active projection integrity mismatch: {root}")
        doc = json.loads(payload)
        if doc.get("format") != FORMAT or doc.get("namespace_id") is None:
            _fail(f"invalid projection envelope: {root}")
        if namespace is not None and doc["namespace_id"] != namespace:
            continue
        observed += 1
        for record in doc["identities"]:
            names = [v["preferred"] for v in record["labels"].values()]
            names.extend(alt for v in record["labels"].values() for alt in v["alternatives"])
            external = record["wikidata"]
            if (record["id"].casefold() == folded
                or (external["accepted_exact"] or "").casefold() == folded
                or any(q.casefold() == folded for q in external["candidate_exact"])
                or any(term.casefold() == folded for term in names)):
                found.append({"owner_slug": doc["owner_slug"], "namespace_id": doc["namespace_id"],
                              **record})
                if len(found) >= limit:
                    return {"query": query, "truncated": True,
                            "searched_active_profiles": observed, "results": found}
    return {"query": query, "truncated": False,
            "searched_active_profiles": observed, "results": found}


def main(argv=None):
    parser = argparse.ArgumentParser(description="V5.16 one-shot local-first semantic reading evolution")
    parser.add_argument("--locals", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--lookup", help="lookup an exact KQ/KP, Wikidata Q/P, or human-readable term")
    parser.add_argument("--namespace-id", help="restrict lookups to one identity namespace")
    args = parser.parse_args(argv)
    try:
        if args.lookup:
            if args.apply:
                _fail("--apply cannot be combined with --lookup")
            result = lookup(args.locals, args.lookup, namespace=args.namespace_id)
        else:
            if not args.private_dir:
                _fail("--private-dir is required for local evolution")
            result = evolve(args.locals, args.private_dir, apply=args.apply)
    except (LocalFirstAuditError, OSError, ValueError, KeyError, sqlite3.Error) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(json.dumps({key: value for key, value in result.items() if key != "workspaces"},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
