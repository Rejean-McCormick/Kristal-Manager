"""Read-only local-canon/public-read-surface audit (V5.13 candidate).

This module deliberately does not select revisions, rewrite canonical artifacts,
qualify Wikidata alignments, or grant permission to publish.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from contextlib import contextmanager
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile


class LocalFirstAuditError(ValueError):
    """Unsafe input or malformed observed surface; fail closed."""


_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_LOCAL_MANIFEST = re.compile(r"^([^/]+)/kristal\.workspace\.json$")
_V11_PREFIX = "canon/domain/v11/updates/"
_V11_CORE = frozenset({
    "identity-registry.json", "semantic-graph.json", "external-crosswalk.json",
    "dictionaries/catalog.json",
})


def _safe_path(raw: str) -> str:
    if not isinstance(raw, str) or not raw or "\\" in raw or "\x00" in raw:
        raise LocalFirstAuditError(f"Unsafe relative path: {raw!r}")
    parts = raw.split("/")
    if any(part in ("", ".", "..") for part in parts) or PurePosixPath(raw).is_absolute():
        raise LocalFirstAuditError(f"Unsafe relative path: {raw!r}")
    if ":" in parts[0]:
        raise LocalFirstAuditError(f"Unsafe drive-relative path: {raw!r}")
    return raw


def _valid_slug(slug: object) -> str:
    if not isinstance(slug, str) or not _SLUG.fullmatch(slug):
        raise LocalFirstAuditError(f"Invalid workspace slug: {slug!r}")
    return slug


class ReadOnlyTree:
    """Read directory trees or snapshot ZIPs without unpacking or writing."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.zip = None
        self._names = None
        if self.root.is_dir() and not self.root.is_symlink():
            self.root = self.root.resolve(strict=True)
        elif self.root.is_file() and zipfile.is_zipfile(self.root):
            self.zip = zipfile.ZipFile(self.root)
            self._names = set()
            self._ambiguous = set()
            for member in self.zip.infolist():
                name = member.filename.removesuffix("/")
                _safe_path(name)
                if name in self._names:
                    # Some SmartDump ZIPs repeat a non-canonical index file.
                    # Such a file is unusable as evidence, but is harmless when
                    # it is never read by this narrowly scoped audit.
                    self._ambiguous.add(name)
                if stat.S_ISLNK(member.external_attr >> 16):
                    raise LocalFirstAuditError(f"Archive contains a symlink: {name}")
                self._names.add(name)
            self.root = self.root.resolve(strict=True)
        else:
            raise LocalFirstAuditError(f"Not a directory or ZIP snapshot: {self.root}")

    def close(self):
        if self.zip:
            self.zip.close()

    def workspace_roots(self):
        if self.zip:
            return sorted(m.group(1) for n in self._names if (m := _LOCAL_MANIFEST.fullmatch(n)))
        return sorted(p.name for p in self.root.iterdir()
                      if p.is_dir() and not p.is_symlink() and self.exists(p.name + "/kristal.workspace.json"))

    def _file(self, path: str):
        rel = _safe_path(path)
        target = self.root
        for component in rel.split("/"):
            target = target / component
            if target.is_symlink():
                raise LocalFirstAuditError(f"Symlink in observed path: {rel}")
        return target

    def exists(self, path: str) -> bool:
        rel = _safe_path(path)
        if self.zip:
            if rel in self._ambiguous:
                raise LocalFirstAuditError(f"Ambiguous duplicate ZIP member: {rel}")
            return rel in self._names and not self.zip.getinfo(rel).is_dir()
        return self._file(rel).is_file()

    @contextmanager
    def open(self, path: str):
        rel = _safe_path(path)
        if not self.exists(rel):
            raise LocalFirstAuditError(f"Missing required source file: {self.root} / {rel}")
        if self.zip:
            with self.zip.open(rel) as stream:
                yield stream
        else:
            with self._file(rel).open("rb") as stream:
                yield stream

    def digest(self, path: str) -> str:
        h = sha256()
        with self.open(path) as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()

    def read_json(self, path: str, limit: int = 10_000_000):
        with self.open(path) as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise LocalFirstAuditError(f"JSON input exceeds safe size: {path}")
        try:
            return json.loads(data.decode("utf-8-sig"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise LocalFirstAuditError(f"Invalid JSON: {path}: {exc}") from exc


def _revision_groups(artifacts: list[dict]) -> list[dict]:
    groups = defaultdict(set)
    for entry in artifacts:
        path = entry["path"]
        if path.startswith(_V11_PREFIX):
            rest = path[len(_V11_PREFIX):]
            revision, sep, subpath = rest.partition("/")
            if sep and revision and subpath:
                groups[revision].add(subpath)
    result = []
    for revision, paths in sorted(groups.items()):
        kind = ("complete_core" if _V11_CORE.issubset(paths) else
                "dictionary_only" if paths == {"dictionaries/catalog.json"} else "partial_core")
        result.append({"revision": revision, "kind": kind, "declared_parts": sorted(paths)})
    return result


def _crosswalk_observations(local: ReadOnlyTree, directory: str, artifacts: list[dict]) -> dict:
    """Count declarations, never infer that a recorded acceptance is qualified."""
    counts = Counter()
    for artifact in artifacts:
        rel = artifact["path"]
        if not rel.startswith("canon/") or not rel.endswith("/external-crosswalk.json"):
            continue
        path = directory + "/" + rel
        if not local.exists(path):
            continue  # Missing canon is separately reported as an integrity blocker.
        obj = local.read_json(path)
        if not isinstance(obj, dict) or not isinstance(obj.get("mappings"), list):
            raise LocalFirstAuditError(f"Malformed crosswalk: {path}")
        counts["declared_crosswalk_files"] += 1
        for mapping in obj["mappings"]:
            if not isinstance(mapping, dict):
                raise LocalFirstAuditError(f"Malformed mapping: {path}")
            counts["mapping_occurrences"] += 1
            relation = mapping.get("relation", "unknown")
            status = mapping.get("status", "unknown")
            if relation == "exactMatch":
                counts["exact_match_occurrences"] += 1
                if status == "candidate":
                    counts["exact_match_candidate_occurrences"] += 1
                elif status == "accepted":
                    counts["exact_match_recorded_accepted_occurrences"] += 1
                    review = mapping.get("review")
                    if isinstance(review, dict) and review.get("method") == "audited_rule":
                        counts["recorded_accepted_by_automated_audited_rule"] += 1
                    if not isinstance(review, dict) or not review.get("evidence_refs"):
                        counts["recorded_accepted_without_evidence_refs"] += 1
            local_ref = mapping.get("local_ref")
            if not isinstance(local_ref, dict) or not local_ref.get("namespace_id") or not local_ref.get("id"):
                counts["mapping_occurrences_without_namespace_local_identity"] += 1
    return dict(sorted(counts.items()))


def audit_local_first(locals_root: Path, public_root: Path) -> dict:
    """Compare byte integrity; leave authority, selection and publishing undecided."""
    local = ReadOnlyTree(locals_root)
    public = None
    try:
        public = ReadOnlyTree(public_root)
        if local.root == public.root:
            raise LocalFirstAuditError("The local canon and public read surface must be distinct inputs")
        index = public.read_json("kristals/index.json")
        if not isinstance(index, dict) or not isinstance(index.get("kristals"), list):
            raise LocalFirstAuditError("Invalid public collection index")
        public_entries = {}
        for entry in index["kristals"]:
            if not isinstance(entry, dict):
                raise LocalFirstAuditError("Invalid public member")
            slug = _valid_slug(entry.get("slug"))
            if slug in public_entries or entry.get("path") != "kristals/" + slug:
                raise LocalFirstAuditError(f"Duplicate or unsafe public member: {slug}")
            public_entries[slug] = entry
        totals = Counter()
        findings = []
        details = []
        visited = set()
        workspace_roots = local.workspace_roots()
        # Discover all claimants before comparing any member with public. A
        # first-match-wins traversal would silently grant canonical authority.
        local_claimants = defaultdict(list)
        for directory in workspace_roots:
            candidate = local.read_json(directory + "/kristal.workspace.json")
            if not isinstance(candidate, dict):
                raise LocalFirstAuditError(f"Malformed workspace: {directory}")
            claimed_slug = _valid_slug(candidate.get("slug"))
            if not isinstance(candidate.get("state_ref"), str) or not candidate["state_ref"]:
                raise LocalFirstAuditError(f"Workspace missing state_ref: {directory}")
            local_claimants[claimed_slug].append((directory, candidate["state_ref"]))
        ambiguous = {slug: claimants for slug, claimants in local_claimants.items()
                     if len(claimants) > 1}
        for slug, claimants in sorted(ambiguous.items()):
            public_index = "kristals/" + slug + "/canon/state.index.json"
            public_hash = public.digest(public_index) if public.exists(public_index) else None
            evidence = []
            for directory, state_ref in claimants:
                local_index = directory + "/canon/state.index.json"
                index_hash = local.digest(local_index) if local.exists(local_index) else None
                evidence.append({"local_directory": directory, "state_ref": state_ref,
                                 "state_index_sha256": index_hash,
                                 "matches_public_state_index": (index_hash == public_hash)
                                 if index_hash is not None and public_hash is not None else None})
            totals["duplicate_local_slug_groups"] += 1
            findings.append({"kind": "DUPLICATE_LOCAL_SLUG", "slug": slug,
                             "public_state_index_sha256": public_hash,
                             "claimants": evidence,
                             "required_action": "OWNER_REVIEW_NO_AUTOMATIC_CANON_SELECTION"})
        for directory in workspace_roots:
            workspace = local.read_json(directory + "/kristal.workspace.json")
            if not isinstance(workspace, dict):
                raise LocalFirstAuditError(f"Malformed workspace: {directory}")
            slug = _valid_slug(workspace.get("slug"))
            state_ref = workspace.get("state_ref")
            if not isinstance(state_ref, str) or not state_ref:
                raise LocalFirstAuditError(f"Workspace missing state_ref: {directory}")
            visited.add(slug)
            totals["local_workspaces"] += 1
            if slug in ambiguous:
                totals["ambiguous_local_workspace_directories_skipped"] += 1
                details.append({"slug": slug, "local_directory": directory,
                                "state_ref": state_ref, "hosted": slug in public_entries,
                                "revision_candidates": [], "crosswalk_observations": {},
                                "findings": [{"kind": "DUPLICATE_LOCAL_SLUG",
                                              "claimant_directories": [n for n, _ in ambiguous[slug]],
                                              "canonical_comparison_skipped": True}]})
                continue
            local_index_path = directory + "/canon/state.index.json"
            canonical = local.read_json(local_index_path)
            if not isinstance(canonical, dict) or not isinstance(canonical.get("canonical_artifacts"), list):
                raise LocalFirstAuditError(f"Malformed local canonical index: {slug}")
            artifact_paths = set()
            artifacts = []
            for a in canonical["canonical_artifacts"]:
                if not isinstance(a, dict):
                    raise LocalFirstAuditError(f"Malformed canonical artifact entry: {slug}")
                path = _safe_path(a.get("path"))
                if path in artifact_paths:
                    raise LocalFirstAuditError(f"Duplicate canonical artifact: {slug}/{path}")
                artifact_paths.add(path)
                artifacts.append({"path": path})
            revs = _revision_groups(artifacts)
            semantic_observations = _crosswalk_observations(local, directory, artifacts)
            for key, count in semantic_observations.items():
                totals[key] += count
            totals["declared_v11_revision_groups"] += len(revs)
            totals["v11_complete_core_groups"] += sum(x["kind"] == "complete_core" for x in revs)
            totals["v11_dictionary_only_groups"] += sum(x["kind"] == "dictionary_only" for x in revs)
            totals["v11_partial_core_groups"] += sum(x["kind"] == "partial_core" for x in revs)
            if len(revs) > 1:
                totals["local_multi_revision_workspaces"] += 1
            row = {"slug": slug, "local_directory": directory, "hosted": slug in public_entries,
                   "revision_candidates": revs,
                   "crosswalk_observations": semantic_observations, "findings": []}
            if slug not in public_entries:
                totals["local_only_workspaces"] += 1
                row["findings"].append({"kind": "LOCAL_ONLY_NOT_PUBLISHED"})
                # Absence from the public collection is not itself a defect.
                for artifact in artifacts:
                    source = directory + "/" + artifact["path"]
                    if not local.exists(source):
                        totals["missing_local_canonical_artifacts"] += 1
                        row["findings"].append({"kind": "MISSING_LOCAL_CANON", "path": artifact["path"]})
                details.append(row)
                continue
            totals["common_workspaces"] += 1
            pub_entry = public_entries[slug]
            if pub_entry.get("state_ref") != state_ref:
                totals["state_ref_conflicts"] += 1
                row["findings"].append({"kind": "STATE_REF_CONFLICT"})
            public_base = "kristals/" + slug + "/"
            pub_state_index = public_base + "canon/state.index.json"
            if not public.exists(pub_state_index):
                totals["missing_public_state_indexes"] += 1
                row["findings"].append({"kind": "MISSING_PUBLIC_STATE_INDEX"})
            elif local.digest(local_index_path) == public.digest(pub_state_index):
                totals["matching_state_indexes"] += 1
            else:
                totals["drifted_state_indexes"] += 1
                row["findings"].append({"kind": "STATE_INDEX_BYTES_DRIFT"})
            manifest = public.read_json(public_base + ".kristal/sync-manifest.json")
            if not isinstance(manifest, dict) or manifest.get("slug") != slug or not isinstance(manifest.get("files"), list):
                raise LocalFirstAuditError(f"Malformed public sync manifest: {slug}")
            declared = {}
            for item in manifest["files"]:
                if not isinstance(item, dict):
                    raise LocalFirstAuditError(f"Malformed public sync manifest file: {slug}")
                path = _safe_path(item.get("path"))
                if path in declared:
                    raise LocalFirstAuditError(f"Duplicate public sync file: {slug}/{path}")
                declared[path] = item
            for artifact in artifacts:
                path = artifact["path"]
                source = directory + "/" + path
                sink = public_base + path
                totals["local_canonical_artifacts_declared"] += 1
                if not local.exists(source):
                    totals["missing_local_canonical_artifacts"] += 1
                    row["findings"].append({"kind": "MISSING_LOCAL_CANON", "path": path})
                    continue
                if not public.exists(sink):
                    if path in declared:
                        totals["manifest_claims_missing_public"] += 1
                        row["findings"].append({"kind": "MANIFEST_CLAIMS_MISSING_PUBLIC", "path": path})
                    else:
                        totals["excluded_canonical_artifacts"] += 1
                        row["findings"].append({"kind": "EXCLUDED_FROM_PUBLIC_READ_SURFACE", "path": path})
                    continue
                totals["shared_canonical_artifacts"] += 1
                local_hash, public_hash = local.digest(source), public.digest(sink)
                if local_hash != public_hash:
                    totals["drifted_canonical_artifacts"] += 1
                    row["findings"].append({"kind": "CANON_BYTES_DRIFT", "path": path})
                else:
                    totals["matching_canonical_artifacts"] += 1
                item = declared.get(path)
                if item is None:
                    totals["public_canonical_not_declared_in_manifest"] += 1
                    row["findings"].append({"kind": "PUBLIC_CANON_NOT_IN_SYNC_MANIFEST", "path": path})
                elif item.get("sha256") != "sha256:" + public_hash:
                    totals["manifest_hash_conflicts"] += 1
                    row["findings"].append({"kind": "MANIFEST_SHA256_CONFLICT", "path": path})
            details.append(row)
        totals["public_workspaces"] = len(public_entries)
        totals["distinct_local_slugs"] = len(visited)
        for slug in sorted(set(public_entries) - visited):
            totals["public_only_workspaces"] += 1
            findings.append({"kind": "PUBLIC_ONLY_NOT_IN_LOCALS", "slug": slug})
        blockers = sum(totals[k] for k in (
            "duplicate_local_slug_groups", "state_ref_conflicts", "missing_public_state_indexes", "drifted_state_indexes",
            "missing_local_canonical_artifacts", "manifest_claims_missing_public",
            "drifted_canonical_artifacts", "manifest_hash_conflicts",
            "public_canonical_not_declared_in_manifest", "public_only_workspaces",
        ))
        return {"profile": "koa.local-first-semantic-surface-audit/0.1-candidate",
                "status": "BLOCKED_INTEGRITY" if blockers else "OBSERVATION_ONLY",
                "blocker_count": blockers, "counts": dict(sorted(totals.items())),
                "policy": {"canonical_owner": "local_kristal_workspace",
                           "public_role": "derived_hosted_read_surface",
                           "automatic_revision_selection": False,
                           "automatic_wikidata_approval": False,
                           "public_write_authorized": False,
                           "qualification_C1_C2_granted": False},
                "collection_findings": findings,
                "workspaces": sorted(details, key=lambda item: item["slug"])}
    finally:
        local.close()
        if public:
            public.close()


def write_private_report(report: dict, output: Path, locals_root: Path, public_root: Path):
    """Opt-in new output; cannot target observed source trees or overwrite."""
    output = Path(output).expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise LocalFirstAuditError(f"Refusing to overwrite existing report: {output}")
    if not output.parent.is_dir():
        raise LocalFirstAuditError("Report parent directory must already exist")
    if output.parent.is_symlink():
        raise LocalFirstAuditError("Report parent cannot be a symlink")
    real_parent = output.parent.resolve(strict=True)
    for candidate in (Path(locals_root), Path(public_root)):
        root = candidate.resolve(strict=True)
        if root.is_dir() and (real_parent == root or root in real_parent.parents):
            raise LocalFirstAuditError("Report output must be outside both observed source trees")
    output = real_parent / output.name
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return output
