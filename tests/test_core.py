from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from kristal_manager.core import (
    CURRENT_LOCAL_FORMAT,
    PUBLISH_REQUEST_FORMAT,
    ManagerError,
    detect_kristal,
    find_github_setup,
    find_framework_cli,
    framework_supports_v10,
    find_kompiler,
    find_local_tool,
    import_local,
    load_manager_config,
    merge_scan,
    migrate_local,
    prepare_publication_request,
    sanitize_repo_name,
    scan_roots,
    scan_roots_quick,
    scan_sensitive_files,
    state_candidates,
    readiness_for_record,
    sync_local_to_github,
    validation_cache_key,
    validate_local_cached,
)


def write_state(path: Path, ref: str, digit: str = "1") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema_version": "9.0",
        "artifact_type": "kristal_state_snapshot",
        "state_ref": ref,
        "logical_commitment": {
            "profile": "kristal.state-commitment/jcs-sha256-v1",
            "digest": "sha256:" + digit * 64,
        },
        "members": [], "references": [], "parents": [],
    }), encoding="utf-8")


def test_detect_local_current_and_build_state(tmp_path: Path):
    p = tmp_path / "A"; p.mkdir()
    (p / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "title": "Alpha", "slug": "alpha"}), encoding="utf-8")
    write_state(p / "build/v9/state-snapshot.json", "urn:kristal:state:alpha")
    r = detect_kristal(p)
    assert r and r["kind"] == "local" and r["title"] == "Alpha"
    assert r["state_source"] == "build-v9"
    assert r["state_ref"] == "urn:kristal:state:alpha"
    assert r["state_commitment"] == "sha256:" + "1" * 64
    assert r["needs_migration"] is False


def test_state_precedence_matches_local_kit_323(tmp_path: Path):
    p = tmp_path / "A"; p.mkdir()
    write_state(p / "build/v9/state-snapshot.json", "urn:build", "1")
    write_state(p / "state/state-snapshot.json", "urn:portable", "2")
    write_state(p / "release/v9/states/old.json", "urn:release", "3")
    rows = state_candidates(p)
    assert [x["source"] for x in rows[:3]] == ["state-export", "build-v9", "release-v9"]
    assert [x["role"] for x in rows[:3]] == ["current", "current", "release"]
    rec = detect_kristal(p)
    assert rec["state_ref"] == "urn:portable"
    assert rec["state_conflict"] is True
    assert rec["readiness"] == "STATE CONFLICT"


def test_detect_legacy_workspace_requires_migration(tmp_path: Path):
    p = tmp_path / "A"; p.mkdir()
    (p / "kristal.workspace.json").write_text(json.dumps({"format": "kristal.authoring-workspace/3.0.0", "title": "Alpha"}), encoding="utf-8")
    r = detect_kristal(p)
    assert r and r["needs_migration"] is True
    assert r["workspace_format"] == "kristal.authoring-workspace/3.0.0"


def test_scan_nested(tmp_path: Path):
    a = tmp_path / "A"; b = a / "B"; b.mkdir(parents=True)
    (a / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT}), encoding="utf-8")
    (b / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT}), encoding="utf-8")
    rows = scan_roots([tmp_path]); assert len(rows) == 2
    child = next(x for x in rows if Path(x["path"]).name == "B")
    assert child["nested_under"] == str(a.resolve())


def test_matching_current_state_surfaces_are_ready(tmp_path: Path):
    p = tmp_path / "A"; p.mkdir()
    (p / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "state_ref": "urn:k"}), encoding="utf-8")
    write_state(p / "state/state-snapshot.json", "urn:k", "a")
    write_state(p / "build/v9/state-snapshot.json", "urn:k", "a")
    write_state(p / ".kristal/v9/state-snapshot.json", "urn:k", "a")
    rec = detect_kristal(p)
    assert rec["state_conflict"] is False
    assert rec["readiness"] == "READY"
    assert rec["state_source"] == "state-export"


def test_legacy_dot_kristal_difference_is_historical_not_conflict(tmp_path: Path):
    p = tmp_path / "PrimeBridge"; p.mkdir()
    (p / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "state_ref": "urn:k"}), encoding="utf-8")
    write_state(p / "build/v9/state-snapshot.json", "urn:k", "a")
    write_state(p / ".kristal/v9/state-snapshot.json", "urn:k", "b")
    rec = detect_kristal(p)
    assert rec["state_conflict"] is False
    assert rec["readiness"] == "READY"
    assert rec["state_source"] == "build-v9"
    roles = {x["source"]: x["role"] for x in rec["state_candidates"]}
    assert roles["build-v9"] == "current"
    assert roles["node-v9"] == "legacy"


def test_only_legacy_dot_kristal_is_not_ready_current_state(tmp_path: Path):
    p = tmp_path / "Old"; p.mkdir()
    (p / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "state_ref": "urn:k"}), encoding="utf-8")
    write_state(p / ".kristal/v9/state-snapshot.json", "urn:k", "a")
    rec = detect_kristal(p)
    assert rec["state_conflict"] is False
    assert rec["readiness"] == "LEGACY STATE"
    assert rec["state_source"] == "node-v9"


def test_historical_release_difference_is_not_current_conflict(tmp_path: Path):
    p = tmp_path / "A"; p.mkdir()
    (p / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "state_ref": "urn:k"}), encoding="utf-8")
    write_state(p / "build/v9/state-snapshot.json", "urn:k", "a")
    write_state(p / "release/v9/states/old/representation/state-snapshot.json", "urn:k", "b")
    rec = detect_kristal(p)
    assert rec["state_conflict"] is False
    assert rec["readiness"] == "READY"
    assert any(x["source"] == "release-v9" for x in rec["state_candidates"])


def test_declared_state_ref_mismatch_is_conflict(tmp_path: Path):
    p = tmp_path / "A"; p.mkdir()
    (p / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "state_ref": "urn:declared"}), encoding="utf-8")
    write_state(p / "state/state-snapshot.json", "urn:actual", "a")
    rec = detect_kristal(p)
    assert rec["state_conflict"] is True
    assert rec["readiness"] == "STATE CONFLICT"
    assert "Workspace declares" in rec["state_conflict_reasons"][0]


def test_nested_legacy_is_hidden_auxiliary(tmp_path: Path):
    parent = tmp_path / "Parent"; child = parent / "knowledge-base"
    child.mkdir(parents=True)
    (parent / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT}), encoding="utf-8")
    (child / "VERSION").write_text("1.0\n", encoding="utf-8")
    (child / "README.md").write_text("legacy\n", encoding="utf-8")
    (child / "canon").mkdir()
    rows = scan_roots([tmp_path])
    nested = next(x for x in rows if x["path"] == str(child.resolve()))
    assert nested["hidden_auxiliary"] is True
    assert nested["readiness"] == "AUXILIARY"


def test_no_state_readiness(tmp_path: Path):
    p = tmp_path / "A"; p.mkdir()
    (p / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT}), encoding="utf-8")
    rec = detect_kristal(p)
    assert rec["readiness"] == "NO STATE"


def test_repo_name():
    assert sanitize_repo_name("Mon Kristal !") == "Mon-Kristal"


def test_sensitive(tmp_path: Path):
    (tmp_path / ".env").write_text("SECRET=x", encoding="utf-8")
    assert scan_sensitive_files(tmp_path) == [".env"]


def test_import_zip(tmp_path: Path):
    src = tmp_path / "src"; k = src / "Kristal-Test-v1.2.3"; k.mkdir(parents=True)
    (k / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT}), encoding="utf-8")
    z = tmp_path / "x.zip"
    with zipfile.ZipFile(z, "w") as zz:
        zz.write(k / "kristal.workspace.json", arcname="Kristal-Test-v1.2.3/kristal.workspace.json")
    dest = tmp_path / "locals"
    out = import_local(z, dest)
    assert len(out) == 1 and out[0].name == "Kristal-Test"


def test_merge_preserves_backup_and_adds_state_fields(tmp_path: Path):
    p = tmp_path / "K"; p.mkdir()
    (p / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT}), encoding="utf-8")
    write_state(p / "build/v9/state-snapshot.json", "urn:k")
    cfg = {"entries": [{"path": str(p.resolve()), "backup_repository": "K-backup", "backup_visibility": "public", "publication_target": "private"}]}
    out = merge_scan(cfg, scan_roots([tmp_path]))
    e = out["entries"][0]
    assert e["backup_repository"] == "K-backup" and e["backup_visibility"] == "public"
    assert e["publication_target"] == "private"
    assert e["state_source"] == "build-v9"
    assert e["state_ref"] == "urn:k"


def test_merge_invalidates_stale_validation_when_state_changes(tmp_path: Path):
    p = tmp_path / "K"; p.mkdir()
    (p / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "state_ref": "urn:k"}), encoding="utf-8")
    write_state(p / "build/v9/state-snapshot.json", "urn:k", "2")
    cfg = {"entries": [{
        "path": str(p.resolve()),
        "workspace_format": CURRENT_LOCAL_FORMAT,
        "state_ref": "urn:k",
        "state_commitment": "sha256:" + "1" * 64,
        "state_conflict": False,
        "last_validation": "2026-10-07T00:00:00Z",
        "last_validation_result": "VALID",
    }]}
    merged = merge_scan(cfg, scan_roots([tmp_path]))
    assert merged["entries"][0]["last_validation"] is None
    assert merged["entries"][0]["last_validation_result"] is None


def test_prepare_publication_request_resolves_collection_and_channel(tmp_path: Path):
    root = tmp_path
    local = root / "locals" / "Bateaux"; local.mkdir(parents=True)
    (local / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "title": "Bateaux", "slug": "bateaux"}), encoding="utf-8")
    write_state(local / "build/v9/state-snapshot.json", "urn:kristal:state:bateaux", "a")
    network = root / "network.toml"
    network.write_text('''[account]\nowner = "acme"\n\n[[collections]]\nname = "kristal-public"\nvisibility = "public"\n\n[[collections]]\nname = "kristal-private"\nvisibility = "private"\n''', encoding="utf-8")
    entry = {"path": str(local), "title": "Bateaux", "slug": "bateaux", "publication_target": "public"}
    result = prepare_publication_request(entry, workspace_root=root, network_config=network)
    assert result["format"] == PUBLISH_REQUEST_FORMAT
    assert result["target"]["collection_repository"] == "acme/kristal-public"
    assert result["target"]["collection_state_path"] == "kristals/bateaux/state/state-snapshot.json"
    assert result["target"]["channel"] == "public/bateaux/stable"
    assert Path(result["request_path"]).is_file()


def test_prepare_publication_request_blocks_state_conflict(tmp_path: Path):
    root = tmp_path
    local = root / "locals" / "PrimeBridge"; local.mkdir(parents=True)
    (local / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "slug": "primebridge", "state_ref": "urn:k"}), encoding="utf-8")
    write_state(local / "state/state-snapshot.json", "urn:k", "a")
    write_state(local / "build/v9/state-snapshot.json", "urn:k", "b")
    network = root / "network.toml"
    network.write_text('[account]\nowner = "acme"\n\n[[collections]]\nname = "kristal-public"\nvisibility = "public"\n', encoding="utf-8")
    entry = {"path": str(local), "slug": "primebridge", "publication_target": "public"}
    with pytest.raises(ManagerError, match="state surfaces disagree"):
        prepare_publication_request(entry, workspace_root=root, network_config=network)


def test_prepare_publication_request_uses_current_state_when_legacy_differs(tmp_path: Path):
    root = tmp_path
    local = root / "locals" / "PrimeBridge"; local.mkdir(parents=True)
    (local / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "slug": "primebridge", "state_ref": "urn:k"}), encoding="utf-8")
    write_state(local / "build/v9/state-snapshot.json", "urn:k", "a")
    write_state(local / ".kristal/v9/state-snapshot.json", "urn:k", "b")
    network = root / "network.toml"
    network.write_text('[account]\nowner = "acme"\n\n[[collections]]\nname = "kristal-public"\nvisibility = "public"\n', encoding="utf-8")
    entry = {"path": str(local), "slug": "primebridge", "publication_target": "public"}
    result = prepare_publication_request(entry, workspace_root=root, network_config=network)
    assert result["state"]["source"] == "build-v9"
    assert result["state"]["logical_commitment"] == "sha256:" + "a" * 64


def test_prepare_publication_request_blocks_legacy_only_state(tmp_path: Path):
    root = tmp_path
    local = root / "locals" / "Old"; local.mkdir(parents=True)
    (local / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "slug": "old", "state_ref": "urn:k"}), encoding="utf-8")
    write_state(local / ".kristal/v9/state-snapshot.json", "urn:k", "a")
    network = root / "network.toml"
    network.write_text('[account]\nowner = "acme"\n\n[[collections]]\nname = "kristal-public"\nvisibility = "public"\n', encoding="utf-8")
    entry = {"path": str(local), "slug": "old", "publication_target": "public"}
    with pytest.raises(ManagerError, match="No current Local Kit v9 State Snapshot"):
        prepare_publication_request(entry, workspace_root=root, network_config=network)


def test_find_apps_in_versioned_folders(tmp_path: Path):
    s1 = tmp_path / "Kristal-GitHub-Bootstrap-1.1.0-alpha.8"; s1.mkdir(); (s1 / "Kristal-GitHub-Setup.pyw").write_text("", encoding="utf-8")
    s2 = tmp_path / "Kristal-GitHub-Bootstrap-1.1.0-alpha.9"; s2.mkdir(); (s2 / "Kristal-GitHub-Setup.pyw").write_text("", encoding="utf-8")
    k = tmp_path / "Kompiler-0.7.0-alpha.2"; k.mkdir(); (k / "Kompiler.pyw").write_text("", encoding="utf-8")
    assert find_github_setup(tmp_path) == s2 / "Kristal-GitHub-Setup.pyw"
    assert find_kompiler(tmp_path) == k / "Kompiler.pyw"


def test_find_latest_local_tool(tmp_path: Path):
    for version in ("3.1.0", "3.2.0"):
        d = tmp_path / f"Kristal-Authoring-Kit-{version}" / "tools"; d.mkdir(parents=True)
        (d / "kristal.py").write_text("", encoding="utf-8")
    assert "3.2.0" in str(find_local_tool(tmp_path))




def test_find_local_tool_with_sorting_prefix(tmp_path: Path):
    d = tmp_path / "A-Kristal-Authoring-Kit-3.2.3" / "tools"
    d.mkdir(parents=True)
    (d / "kristal.py").write_text("", encoding="utf-8")
    (d.parent / "VERSION").write_text("3.2.3\n", encoding="utf-8")
    found = find_local_tool(tmp_path)
    assert found == d / "kristal.py"


def test_find_framework_cli_with_sorting_prefix(tmp_path: Path):
    d = tmp_path / "A-KristalV10" / "reference" / "js" / "bin"
    d.mkdir(parents=True)
    cli = d / "kristal-ref.mjs"
    cli.write_text("", encoding="utf-8")
    network = tmp_path / "network.toml"
    network.write_text('[framework]\nrepository = "Rejean-McCormick/KristalV10"\nref = "abc123"\n', encoding="utf-8")
    found, ref = find_framework_cli(tmp_path, network)
    assert found == cli
    assert ref == "abc123"




def test_find_local_tool_unversioned_exact_operator_path(tmp_path: Path):
    d = tmp_path / "Kristal-Authoring-Kit" / "tools"
    d.mkdir(parents=True)
    tool = d / "kristal.py"
    tool.write_text("", encoding="utf-8")
    (d.parent / "VERSION").write_text("3.2.3\n", encoding="utf-8")
    assert find_local_tool(tmp_path) == tool


def test_find_framework_cli_kristal_framework_alias(tmp_path: Path):
    d = tmp_path / "Kristal-Framework" / "reference" / "js" / "bin"
    d.mkdir(parents=True)
    cli = d / "kristal-ref.mjs"
    cli.write_text("", encoding="utf-8")
    network = tmp_path / "network.toml"
    network.write_text('[framework]\nrepository = "Rejean-McCormick/KristalV10"\nref = "abc123"\n', encoding="utf-8")
    found, ref = find_framework_cli(tmp_path, network)
    assert found == cli
    assert ref == "abc123"


def test_framework_supports_v10_from_source_commands(tmp_path: Path):
    root = tmp_path / "Kristal-Framework" / "reference" / "js"
    (root / "bin").mkdir(parents=True)
    (root / "src").mkdir(parents=True)
    cli = root / "bin" / "kristal-ref.mjs"
    cli.write_text("", encoding="utf-8")
    (root / "src" / "cli.mjs").write_text(
        "v10-capabilities verify-node-v10 verify-github-binding-v10", encoding="utf-8"
    )
    assert framework_supports_v10(cli) is True


def test_migrate_local_with_safety_snapshot(tmp_path: Path):
    workspace = tmp_path / "workspace"; workspace.mkdir()
    kit = workspace / "Kristal-Authoring-Kit-3.2.0"; (kit / "tools").mkdir(parents=True)
    tool = kit / "tools" / "kristal.py"
    tool.write_text(r'''import json,sys\nfrom pathlib import Path\ncmd=Path(sys.argv[0]).name\nmode=sys.argv[1]; root=Path(sys.argv[2])\np=root/'kristal.workspace.json'\nw=json.loads(p.read_text())\nif mode=='migrate-v10':\n    w['format']='kristal.local-workspace/3.2.0'; p.write_text(json.dumps(w))\n    raise SystemExit(0)\nif mode=='check':\n    raise SystemExit(0 if w.get('format')=='kristal.local-workspace/3.2.0' else 2)\nraise SystemExit(2)\n'''.replace('\\n','\n'), encoding="utf-8")
    (kit / "VERSION").write_text("3.2.0\n", encoding="utf-8")
    local = workspace / "locals" / "X"; (local / "canon").mkdir(parents=True)
    (local / "kristal.workspace.json").write_text(json.dumps({"format": "kristal.authoring-workspace/3.0.0", "title": "X"}), encoding="utf-8")
    (local / "canon/state.index.json").write_text("{}", encoding="utf-8")
    write_state(local / "build/v9/state-snapshot.json", "urn:x", "b")
    result = migrate_local(local, workspace_root=workspace)
    assert result["result"] == "MIGRATION PASS"
    assert result["state_commitment_before"] == result["state_commitment_after"]
    assert Path(result["safety_snapshot"]).is_file()
    assert detect_kristal(local)["workspace_format"] == CURRENT_LOCAL_FORMAT


def test_load_config_keeps_registry_format_20_for_kompiler_compat(tmp_path: Path):
    cfg = load_manager_config(tmp_path / "missing.json", tmp_path)
    assert cfg["format"] == "kristal-local-registry/2.0"



def _fake_prepared(entry: dict, local: Path, *, slug: str, state_ref: str, digit: str = "a") -> dict:
    (local / "README.md").write_text(f"# {slug}\n", encoding="utf-8")
    (local / "AI_START_HERE.md").write_text("# Start here\n", encoding="utf-8")
    write_state(local / "state/state-snapshot.json", state_ref, digit)
    files = []
    for rel, role in [("AI_START_HERE.md", "ai_entrypoint"), ("README.md", "overview"), ("state/state-snapshot.json", "state_snapshot")]:
        file = local / rel
        files.append({
            "path": rel, "role": role, "media_type": "application/json" if rel.endswith(".json") else "text/markdown",
            "size": file.stat().st_size, "sha256": "sha256:" + hashlib.sha256(file.read_bytes()).hexdigest(),
        })
    projection = json.dumps([(x["path"], x["sha256"], x["size"]) for x in files], separators=(",", ":"), ensure_ascii=False).encode()
    surface = {
        "format": "kristal.github-read-surface/1.0", "kit_version": "3.2.4", "slug": slug,
        "target_root": f"kristals/{slug}", "entrypoint": "AI_START_HERE.md", "state_ref": state_ref,
        "state_logical_commitment": {"profile": "kristal.state-commitment/jcs-sha256-v1", "digest": "sha256:" + digit * 64},
        "ready": True, "errors": [], "surface_digest": "sha256:" + hashlib.sha256(projection).hexdigest(),
        "file_count": len(files), "total_bytes": sum(x["size"] for x in files), "files": files,
        "materialization_object_count": 0, "materialization_objects": [],
    }
    return {
        "entry": dict(entry), "local_path": str(local), "local_tool": "fake", "local_tool_version": "3.2.4",
        "surface": surface, "state_path_in_surface": "state/state-snapshot.json",
    }


def _git(*args: str, cwd: Path | None = None) -> None:
    import subprocess
    subprocess.run(["git", *args], cwd=str(cwd) if cwd else None, check=True, capture_output=True, text=True)


def _git_output(*args: str, cwd: Path | None = None) -> str:
    import subprocess
    return subprocess.run(["git", *args], cwd=str(cwd) if cwd else None, check=True, capture_output=True, text=True).stdout.strip()


def test_sync_one_click_writes_read_surface_index_and_is_idempotent(tmp_path: Path, monkeypatch):
    import kristal_manager.core as core
    # This test exercises existing sync semantics; signed C2 policy has its own separate tests.
    monkeypatch.setattr(core, "verify_public_write", lambda **kw: {"result":"AUTHORIZED_AND_QUALIFIED"})
    workspace = tmp_path / "workspace"; workspace.mkdir()
    local = workspace / "locals" / "Bateaux"; local.mkdir(parents=True)
    (local / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "slug": "bateaux", "state_ref": "urn:k"}), encoding="utf-8")
    write_state(local / "build/v9/state-snapshot.json", "urn:k", "a")
    entry = {"path": str(local), "title": "Bateaux", "slug": "bateaux", "publication_target": "public"}
    prepared = _fake_prepared(entry, local, slug="bateaux", state_ref="urn:k", digit="a")

    bare = tmp_path / "remote.git"
    _git("init", "--bare", str(bare))
    seed = tmp_path / "seed"; _git("clone", str(bare), str(seed))
    (seed / ".kristal/bindings").mkdir(parents=True)
    (seed / ".kristal/node.json").write_text("{}\n", encoding="utf-8")
    (seed / ".kristal/bindings/github.json").write_text("{}\n", encoding="utf-8")
    _git("add", ".", cwd=seed)
    _git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "seed", cwd=seed)
    _git("branch", "-M", "main", cwd=seed); _git("push", "-u", "origin", "main", cwd=seed)
    checkout = workspace / "kristal-public"; _git("clone", "--branch", "main", str(bare), str(checkout))

    monkeypatch.setattr(core, "ensure_collection_checkout", lambda **kwargs: {
        "owner": "acme", "name": "kristal-public", "repository": "acme/kristal-public", "visibility": "public", "checkout": str(checkout), "branch": "main"
    })
    monkeypatch.setattr(core, "resolve_publication_collection", lambda *a, **k: {"owner": "acme", "name": "kristal-public", "repository": "acme/kristal-public", "visibility": "public"})
    monkeypatch.setattr(core, "github_remote_json_file", lambda *a, **k: None)
    monkeypatch.setattr(core, "validate_local_cached", lambda *a, **k: {"result": "VALID", "cached": False, "validation_cache_key": "cache"})
    monkeypatch.setattr(core, "find_framework_cli", lambda *a, **k: (None, "f" * 40))
    monkeypatch.setattr(core, "prepare_github_read_surface", lambda *a, **k: prepared)

    first = sync_local_to_github(entry, workspace_root=workspace, network_config=workspace / "network.toml")
    assert first["result"] == "SYNC PASS"
    assert first["surface_root"] == "kristals/bateaux"
    assert (checkout / "kristals/bateaux/AI_START_HERE.md").is_file()
    assert (checkout / "kristals/bateaux/.kristal/sync-manifest.json").is_file()
    index = json.loads((checkout / "kristals/index.json").read_text(encoding="utf-8"))
    assert index["format"] == "kristal.github-collection-index/1.0"
    assert index["count"] == 1 and index["kristals"][0]["state_ref"] == "urn:k"
    count1 = int((_git_output("rev-list", "--count", "HEAD", cwd=checkout)))

    second = sync_local_to_github(entry, workspace_root=workspace, network_config=workspace / "network.toml")
    assert second["result"] == "ALREADY SYNCED"
    count2 = int((_git_output("rev-list", "--count", "HEAD", cwd=checkout)))
    assert count2 == count1


def test_sync_blocks_slug_collision(tmp_path: Path, monkeypatch):
    import kristal_manager.core as core
    # This test exercises existing sync semantics; signed C2 policy has its own separate tests.
    monkeypatch.setattr(core, "verify_public_write", lambda **kw: {"result":"AUTHORIZED_AND_QUALIFIED"})
    workspace = tmp_path / "workspace"; workspace.mkdir()
    local = workspace / "locals" / "X"; local.mkdir(parents=True)
    (local / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "slug": "same", "state_ref": "urn:new"}), encoding="utf-8")
    write_state(local / "build/v9/state-snapshot.json", "urn:new", "a")
    entry = {"path": str(local), "title": "X", "slug": "same", "publication_target": "public"}
    prepared = _fake_prepared(entry, local, slug="same", state_ref="urn:new", digit="a")
    checkout = workspace / "kristal-public"; (checkout / ".kristal/bindings").mkdir(parents=True)
    (checkout / ".kristal/node.json").write_text("{}", encoding="utf-8")
    (checkout / ".kristal/bindings/github.json").write_text("{}", encoding="utf-8")
    write_state(checkout / "kristals/same/state/state-snapshot.json", "urn:other", "b")
    monkeypatch.setattr(core, "ensure_collection_checkout", lambda **kwargs: {
        "owner": "acme", "name": "kristal-public", "repository": "acme/kristal-public", "visibility": "public", "checkout": str(checkout), "branch": "main"
    })
    monkeypatch.setattr(core, "resolve_publication_collection", lambda *a, **k: {"owner": "acme", "name": "kristal-public", "repository": "acme/kristal-public", "visibility": "public"})
    monkeypatch.setattr(core, "github_remote_json_file", lambda *a, **k: None)
    monkeypatch.setattr(core, "validate_local_cached", lambda *a, **k: {"result": "VALID", "cached": False, "validation_cache_key": "cache"})
    monkeypatch.setattr(core, "find_framework_cli", lambda *a, **k: (None, None))
    monkeypatch.setattr(core, "prepare_github_read_surface", lambda *a, **k: prepared)
    with pytest.raises(ManagerError, match="slug collision"):
        sync_local_to_github(entry, workspace_root=workspace, network_config=workspace / "network.toml")


def test_state_blob_digest_changes_when_representation_changes(tmp_path: Path):
    p = tmp_path / "A"; p.mkdir()
    (p / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT}), encoding="utf-8")
    state = p / "build/v9/state-snapshot.json"
    write_state(state, "urn:k", "a")
    one = detect_kristal(p)["state_blob_digest"]
    obj = json.loads(state.read_text()); obj["created_at"] = "2026-10-07T00:00:00Z"; state.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    two = detect_kristal(p)["state_blob_digest"]
    assert one != two


def test_quick_scan_reuses_unchanged_workspace(tmp_path: Path):
    local = tmp_path / "locals" / "K"; local.mkdir(parents=True)
    (local / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "slug": "k"}), encoding="utf-8")
    write_state(local / "build/v9/state-snapshot.json", "urn:k", "a")
    deep = scan_roots([tmp_path / "locals"])
    merged = merge_scan({"entries": []}, deep)
    quick = scan_roots_quick([tmp_path / "locals"], merged["entries"])
    row = next(x for x in quick if x["path"] == str(local.resolve()))
    assert row.get("scan_cached") is True
    assert row["state_commitment"] == "sha256:" + "a" * 64


def test_quick_scan_detects_changed_state(tmp_path: Path):
    local = tmp_path / "locals" / "K"; local.mkdir(parents=True)
    (local / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "slug": "k"}), encoding="utf-8")
    state = local / "build/v9/state-snapshot.json"
    write_state(state, "urn:k", "a")
    previous = merge_scan({"entries": []}, scan_roots([tmp_path / "locals"]))["entries"]
    write_state(state, "urn:k", "b")
    quick = scan_roots_quick([tmp_path / "locals"], previous)
    row = next(x for x in quick if x["path"] == str(local.resolve()))
    assert not row.get("scan_cached")
    assert row["state_commitment"] == "sha256:" + "b" * 64


def test_validation_cache_reuses_valid_result_when_inputs_unchanged(tmp_path: Path):
    workspace = tmp_path / "workspace"; local = workspace / "locals" / "K"
    local.mkdir(parents=True)
    (local / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "slug": "k"}), encoding="utf-8")
    write_state(local / "build/v9/state-snapshot.json", "urn:k", "a")
    rec = detect_kristal(local)
    key = validation_cache_key(rec, workspace_root=workspace, network_config=None)
    previous = {**rec, "last_validation_result": "VALID", "last_validation_cache_key": key}
    result = validate_local_cached(local, previous=previous, workspace_root=workspace, network_config=None)
    assert result["result"] == "VALID"
    assert result["cached"] is True
    assert result["validation_cache_key"] == key


def test_merge_invalidates_validation_cache_key_when_state_changes(tmp_path: Path):
    local = tmp_path / "K"; local.mkdir()
    (local / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT}), encoding="utf-8")
    write_state(local / "build/v9/state-snapshot.json", "urn:k", "2")
    cfg = {"entries": [{
        "path": str(local.resolve()), "workspace_format": CURRENT_LOCAL_FORMAT, "state_ref": "urn:k",
        "state_commitment": "sha256:" + "1" * 64, "state_conflict": False,
        "last_validation_result": "VALID", "last_validation_cache_key": "old",
    }]}
    merged = merge_scan(cfg, scan_roots([tmp_path]))
    assert merged["entries"][0]["last_validation_cache_key"] is None


def test_sync_fast_path_uses_remote_surface_manifest_and_index(tmp_path: Path, monkeypatch):
    import kristal_manager.core as core
    # This test exercises existing sync semantics; signed C2 policy has its own separate tests.
    monkeypatch.setattr(core, "verify_public_write", lambda **kw: {"result":"AUTHORIZED_AND_QUALIFIED"})
    workspace = tmp_path / "workspace"; workspace.mkdir()
    local = workspace / "locals" / "Fast"; local.mkdir(parents=True)
    (local / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "slug": "fast", "state_ref": "urn:fast"}), encoding="utf-8")
    write_state(local / "build/v9/state-snapshot.json", "urn:fast", "c")
    entry = {"path": str(local), "title": "Fast", "slug": "fast", "publication_target": "public", "last_sync_commit": "abc123"}
    prepared = _fake_prepared(entry, local, slug="fast", state_ref="urn:fast", digit="c")
    surface = prepared["surface"]

    monkeypatch.setattr(core, "validate_local_cached", lambda *a, **k: {"result": "VALID", "cached": True, "validation_cache_key": "cache"})
    monkeypatch.setattr(core, "find_framework_cli", lambda *a, **k: (None, "f" * 40))
    monkeypatch.setattr(core, "prepare_github_read_surface", lambda *a, **k: prepared)
    monkeypatch.setattr(core, "resolve_publication_collection", lambda *a, **k: {"owner": "acme", "name": "kristal-public", "repository": "acme/kristal-public", "visibility": "public"})

    remote_manifest = {"format": "kristal.github-sync-manifest/1.0", "state_ref": "urn:fast", "surface_digest": surface["surface_digest"]}
    remote_index = {"format": "kristal.github-collection-index/1.0", "kristals": [{
        "path": "kristals/fast", "entrypoint": "kristals/fast/AI_START_HERE.md", "state_ref": "urn:fast", "surface_digest": surface["surface_digest"]
    }]}
    def remote_json(_repo, _branch, path):
        return remote_index if path == "kristals/index.json" else remote_manifest
    monkeypatch.setattr(core, "github_remote_json_file", remote_json)
    monkeypatch.setattr(core, "ensure_collection_checkout", lambda **k: (_ for _ in ()).throw(AssertionError("checkout should not be touched")))

    result = sync_local_to_github(entry, workspace_root=workspace, network_config=workspace / "network.toml")
    assert result["result"] == "ALREADY SYNCED"
    assert result["changed"] is False
    assert result["commit"] == "abc123"
    assert result["surface_digest"] == surface["surface_digest"]
    assert result["validation_cached"] is True


def test_quiet_subprocess_kwargs_windows(monkeypatch):
    import kristal_manager.core as core
    monkeypatch.setattr(core.os, "name", "nt", raising=False)
    kwargs = core._quiet_subprocess_kwargs()
    assert kwargs.get("creationflags", 0) != 0


def test_validate_entries_parallel_reports_progress(tmp_path: Path, monkeypatch):
    import kristal_manager.core as core
    entries = [
        {"path": str(tmp_path / "A"), "title": "A", "kind": "local", "hidden_auxiliary": False},
        {"path": str(tmp_path / "B"), "title": "B", "kind": "local", "hidden_auxiliary": False},
    ]
    for e in entries:
        Path(e["path"]).mkdir()

    def fake_validate(path, **kwargs):
        progress = kwargs.get("progress")
        if progress:
            progress(f"{path.name}: fake validate")
        return {"result": "VALID", "validation_cache_key": path.name, "cached": False}

    monkeypatch.setattr(core, "validate_local_cached", fake_validate)
    messages = []
    results = core.validate_entries_parallel(
        entries, workspace_root=tmp_path, network_config=tmp_path / "network.toml",
        max_workers=2, progress=messages.append,
    )
    assert [x["ok"] for x in results] == [True, True]
    assert [x["validation"]["result"] for x in results] == ["VALID", "VALID"]
    assert any("2 parallel worker" in m for m in messages)
    assert any("[2/2]" in m for m in messages)


def test_sync_entries_batch_uses_one_collection_transaction_per_target_and_parallelizes_targets(tmp_path: Path, monkeypatch):
    import threading
    import time
    import kristal_manager.core as core

    entries = [
        {"path": str(tmp_path / "p1"), "title": "P1", "slug": "p1", "kind": "local", "publication_target": "public"},
        {"path": str(tmp_path / "p2"), "title": "P2", "slug": "p2", "kind": "local", "publication_target": "public"},
        {"path": str(tmp_path / "r1"), "title": "R1", "slug": "r1", "kind": "local", "publication_target": "private"},
        {"path": str(tmp_path / "r2"), "title": "R2", "slug": "r2", "kind": "local", "publication_target": "private"},
    ]
    for e in entries:
        p = Path(e["path"]); p.mkdir()
        (p / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "slug": e["slug"], "state_ref": f"urn:{e['slug']}"}), encoding="utf-8")
        write_state(p / "build/v9/state-snapshot.json", f"urn:{e['slug']}", "a")

    def fake_validate_batch(items, **kwargs):
        return [{"path": e["path"], "title": e["title"], "ok": True, "validation": {"result": "VALID", "validation_cache_key": e["title"]}} for e in items]
    monkeypatch.setattr(core, "validate_entries_parallel", fake_validate_batch)
    monkeypatch.setattr(core, "prepare_github_read_surface", lambda e, **k: _fake_prepared(e, Path(e["path"]), slug=e["slug"], state_ref=f"urn:{e['slug']}", digit="a"))
    monkeypatch.setattr(core, "find_framework_cli", lambda *a, **k: (None, "f" * 40))

    active = 0
    max_active = 0
    calls = []
    lock = threading.Lock()
    def fake_collection(target, group, **kwargs):
        nonlocal active, max_active
        with lock:
            active += 1; max_active = max(max_active, active); calls.append((target, len(group)))
        time.sleep(0.05)
        with lock:
            active -= 1
        out = []
        for p in group:
            surface = p["surface"]
            out.append({
                "result": "SYNC PASS", "changed": True, "local_path": p["local_path"],
                "repository": f"acme/kristal-{target}", "surface_root": surface["target_root"],
                "surface_digest": surface["surface_digest"], "entrypoint": f"{surface['target_root']}/AI_START_HERE.md",
                "file_count": surface["file_count"], "total_bytes": surface["total_bytes"],
                "state_path": f"{surface['target_root']}/state/state-snapshot.json",
                "state_blob_digest": next(x["sha256"] for x in surface["files"] if x["role"] == "state_snapshot"),
                "commit": "abc",
            })
        return out
    monkeypatch.setattr(core, "_sync_prepared_collection", fake_collection)

    results = core.sync_entries_batch(entries, workspace_root=tmp_path, network_config=tmp_path / "network.toml")
    assert len(results) == 4 and all(x["ok"] for x in results)
    assert sorted(calls) == [("private", 2), ("public", 2)]
    assert max_active >= 2



def test_apply_read_surface_removes_only_previous_managed_stale_files(tmp_path: Path):
    import kristal_manager.core as core
    checkout = tmp_path / "checkout"; checkout.mkdir()
    local = tmp_path / "local"; local.mkdir()
    entry = {"path": str(local), "title": "K", "slug": "k", "publication_target": "public"}
    prepared = _fake_prepared(entry, local, slug="k", state_ref="urn:k", digit="a")
    root = checkout / "kristals/k"
    (root / ".kristal").mkdir(parents=True)
    (root / "old.txt").write_text("stale", encoding="utf-8")
    (root / "custom.txt").write_text("keep", encoding="utf-8")
    old_manifest = {
        "format": "kristal.github-sync-manifest/1.0",
        "state_ref": "urn:k",
        "surface_digest": "sha256:old",
        "files": [{"path": "old.txt", "sha256": "sha256:old"}],
    }
    (root / ".kristal/sync-manifest.json").write_text(json.dumps(old_manifest), encoding="utf-8")
    result = core._apply_prepared_surface(checkout, prepared)
    assert result["changed"] is True
    assert not (root / "old.txt").exists()
    assert (root / "custom.txt").read_text(encoding="utf-8") == "keep"
    assert (root / "AI_START_HERE.md").is_file()


def test_collection_index_blocks_same_identity_at_two_paths(tmp_path: Path):
    import kristal_manager.core as core
    local = tmp_path / "local"; local.mkdir()
    entry = {"path": str(local), "title": "New", "slug": "new", "publication_target": "public"}
    prepared = _fake_prepared(entry, local, slug="new", state_ref="urn:shared", digit="a")
    existing = {
        "format": "kristal.github-collection-index/1.0",
        "kristals": [{"path": "kristals/old", "slug": "old", "state_ref": "urn:shared", "surface_digest": "sha256:old"}],
    }
    with pytest.raises(ManagerError, match="identity collision"):
        core._build_collection_index(existing, [prepared])


def test_public_sync_blocks_sensitive_path_in_read_surface(tmp_path: Path, monkeypatch):
    import kristal_manager.core as core
    workspace = tmp_path / "workspace"; workspace.mkdir()
    local = workspace / "locals" / "K"; local.mkdir(parents=True)
    (local / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "slug": "k", "state_ref": "urn:k"}), encoding="utf-8")
    write_state(local / "build/v9/state-snapshot.json", "urn:k", "a")
    entry = {"path": str(local), "title": "K", "slug": "k", "publication_target": "public"}
    prepared = _fake_prepared(entry, local, slug="k", state_ref="urn:k", digit="a")
    (local / ".env").write_text("SECRET=x", encoding="utf-8")
    prepared["surface"]["files"].append({"path": ".env", "role": "documentation", "size": 8, "sha256": "sha256:x"})
    monkeypatch.setattr(core, "validate_local_cached", lambda *a, **k: {"result": "VALID", "cached": True, "validation_cache_key": "cache"})
    monkeypatch.setattr(core, "find_framework_cli", lambda *a, **k: (None, None))
    monkeypatch.setattr(core, "prepare_github_read_surface", lambda *a, **k: prepared)
    with pytest.raises(ManagerError, match="sensitive-looking"):
        core.sync_local_to_github(entry, workspace_root=workspace, network_config=workspace / "network.toml")


def test_prepare_read_surface_requires_local_kit_324_or_newer(tmp_path: Path):
    import kristal_manager.core as core
    workspace = tmp_path / "workspace"; workspace.mkdir()
    tool = workspace / "Kristal-Authoring-Kit" / "tools" / "kristal.py"
    tool.parent.mkdir(parents=True)
    tool.write_text("", encoding="utf-8")
    (tool.parent.parent / "VERSION").write_text("3.2.3\n", encoding="utf-8")
    local = workspace / "locals" / "K"; local.mkdir(parents=True)
    (local / "kristal.workspace.json").write_text(json.dumps({"format": CURRENT_LOCAL_FORMAT, "slug": "k", "state_ref": "urn:k"}), encoding="utf-8")
    write_state(local / "build/v9/state-snapshot.json", "urn:k", "a")
    with pytest.raises(ManagerError, match="too old"):
        core.prepare_github_read_surface({"path": str(local), "slug": "k"}, workspace_root=workspace)
