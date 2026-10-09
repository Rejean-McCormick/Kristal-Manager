from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
import tomllib
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from .publication_gate import verify_public_write, PublicGateError

VERSION = "0.1.0-alpha.11"
REGISTRY_FORMAT = "kristal-local-registry/2.0"
PUBLISH_REQUEST_FORMAT = "kristal-manager-publish-request/1.0"
CURRENT_LOCAL_FORMAT = "kristal.local-workspace/3.2.0"
DEFAULT_WINDOWS_ROOT = Path(r"C:\mycode\Kristal")
DEFAULT_LOCAL_DIRNAME = "locals"
REMOTE_NAME = "kristal-backup"
GITHUB_READ_SURFACE_FORMAT = "kristal.github-read-surface/1.0"
GITHUB_SYNC_MANIFEST_FORMAT = "kristal.github-sync-manifest/1.0"
GITHUB_COLLECTION_INDEX_FORMAT = "kristal.github-collection-index/1.0"
SYNC_MANIFEST_REL = PurePosixPath(".kristal/sync-manifest.json")
COLLECTION_INDEX_REL = PurePosixPath("kristals/index.json")

STRONG_MARKERS = (
    "kristal.workspace.json",
    "kristal-v9.integration.json",
    ".kristal/v9/state-snapshot.json",
    ".kristal/node.json",
)
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".pytest_cache",
    "build", "dist", "runtime", ".venv", "venv", ".idea", ".vscode",
    "MediKristal", "_reports", "_work",
}
SENSITIVE_NAMES = {
    ".env", ".env.local", ".env.production", "credentials", "credentials.json",
    "secrets", "secrets.json", "id_rsa", "id_ed25519",
}
SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".kdbx"}
SEMVER_IN_NAME_RE = re.compile(r"(?i)(?:[-_ ]?v?\d+\.\d+(?:\.\d+)?(?:[-_.][0-9A-Za-z.-]+)?)")
COPY_SUFFIX_RE = re.compile(r"\s*\(\d+\)\s*$")
VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:[-_.]?([0-9A-Za-z.-]+))?")


class ManagerError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


ProgressCallback = Callable[[str], None]


def _quiet_subprocess_kwargs() -> dict[str, Any]:
    """Suppress transient console windows for CLI tools on Windows."""
    if os.name != "nt":
        return {}
    kwargs: dict[str, Any] = {
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
    }
    startup_cls = getattr(subprocess, "STARTUPINFO", None)
    if startup_cls is not None:
        startup = startup_cls()
        startup.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
        startup.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        kwargs["startupinfo"] = startup
    return kwargs


def _progress(cb: ProgressCallback | None, message: str) -> None:
    if cb:
        cb(message)


def _run(argv: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        p = subprocess.run(
            argv, cwd=str(cwd) if cwd else None, text=True, capture_output=True,
            **_quiet_subprocess_kwargs(),
        )
    except FileNotFoundError as exc:
        raise ManagerError(f"Required executable not found: {argv[0]}") from exc
    if check and p.returncode:
        diagnostic = (p.stderr or p.stdout or "").strip()
        raise ManagerError(f"Command failed ({p.returncode}): {' '.join(argv)}" + (f"\n{diagnostic}" if diagnostic else ""))
    return p


def require_tool(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise ManagerError(f"Required executable is not available on PATH: {name}")
    return found


def load_network_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def sanitize_repo_name(name: str) -> str:
    value = name.strip().replace(" ", "-")
    value = re.sub(r"[^A-Za-z0-9_.-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-.")
    return value[:100] or "kristal"


def normalize_package_name(name: str) -> str:
    n = name.strip()
    if n.lower().endswith(".zip"):
        n = n[:-4]
    n = COPY_SUFFIX_RE.sub("", n).strip()
    n = SEMVER_IN_NAME_RE.sub("", n)
    n = re.sub(r"-{2,}", "-", n).strip(" -")
    return n or "Kristal"


def safe_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def _state_info(path: Path, source: str, role: str) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    state = safe_json(path)
    if not state or state.get("artifact_type") != "kristal_state_snapshot":
        return None
    lc = state.get("logical_commitment") if isinstance(state.get("logical_commitment"), dict) else {}
    blob_digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "path": str(path.resolve()),
        "source": source,
        "role": role,
        "state_ref": state.get("state_ref"),
        "state_commitment": lc.get("digest"),
        "state_profile": lc.get("profile"),
        "state_blob_digest": blob_digest,
    }


def state_candidates(path: Path) -> list[dict[str, Any]]:
    """Return known v9 state surfaces in Local Kit 3.2.3 discovery order.

    `state/` and `build/v9/` are current Local Kit surfaces. `.kristal/v9/`
    and a root snapshot are legacy/compatibility surfaces; immutable releases
    are history. Legacy/history may differ from the current state without
    creating a conflict.
    """
    path = path.resolve()
    rows: list[dict[str, Any]] = []
    fixed = [
        ("state-export", "current", path / "state" / "state-snapshot.json"),
        ("build-v9", "current", path / "build" / "v9" / "state-snapshot.json"),
        ("node-v9", "legacy", path / ".kristal" / "v9" / "state-snapshot.json"),
        ("root", "legacy", path / "state-snapshot.json"),
    ]
    for source, role, candidate in fixed:
        info = _state_info(candidate, source, role)
        if info:
            rows.append(info)

    release_dir = path / "release" / "v9" / "states"
    if release_dir.is_dir():
        release_paths = set(release_dir.rglob("state-snapshot.json"))
        # Older Local Kit layouts could store JSON snapshots directly under states/.
        release_paths.update(release_dir.glob("*.json"))
        released: list[dict[str, Any]] = []
        for candidate in release_paths:
            info = _state_info(candidate, "release-v9", "release")
            if info:
                try:
                    info["mtime_ns"] = candidate.stat().st_mtime_ns
                except OSError:
                    info["mtime_ns"] = 0
                released.append(info)
        released.sort(key=lambda x: (int(x.get("mtime_ns", 0)), x["path"]), reverse=True)
        for info in released:
            info.pop("mtime_ns", None)
            rows.append(info)

    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        if row["path"] in seen:
            continue
        seen.add(row["path"])
        out.append(row)
    return out


def current_state_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in candidates if row.get("role") == "current"]


def legacy_state_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in candidates if row.get("role") == "legacy"]


def state_conflict_info(candidates: list[dict[str, Any]], declared_state_ref: str | None = None) -> dict[str, Any]:
    current = current_state_candidates(candidates)
    signatures: dict[tuple[str | None, str | None], list[str]] = {}
    for row in current:
        sig = (row.get("state_ref"), row.get("state_commitment"))
        signatures.setdefault(sig, []).append(str(row.get("source") or "unknown"))
    reasons: list[str] = []
    if len(signatures) > 1:
        readable = []
        for (state_ref, commitment), sources in signatures.items():
            readable.append(f"{','.join(sources)} => {state_ref or '?'} @ {commitment or '?'}")
        reasons.append("Current state surfaces disagree: " + "; ".join(readable))
    preferred = current[0] if current else (candidates[0] if candidates else None)
    if declared_state_ref and preferred and preferred.get("state_ref") and declared_state_ref != preferred.get("state_ref"):
        reasons.append(f"Workspace declares {declared_state_ref} but current state is {preferred.get('state_ref')}")
    return {
        "conflict": bool(reasons),
        "reasons": reasons,
        "current_candidate_count": len(current),
        "signature_count": len(signatures),
    }


def readiness_for_record(record: dict[str, Any]) -> str:
    if record.get("hidden_auxiliary"):
        return "AUXILIARY"
    if record.get("kind") == "legacy":
        return "LEGACY"
    if record.get("needs_migration"):
        return "MIGRATE"
    if record.get("state_conflict"):
        return "STATE CONFLICT"
    if record.get("workspace"):
        current = current_state_candidates(record.get("state_candidates", []))
        if current:
            return "READY"
        if record.get("state_path"):
            return "LEGACY STATE"
        return "NO STATE"
    if record.get("state_path"):
        return "READY"
    return "OBSERVED"




def _stat_token(path: Path) -> tuple[int, int] | None:
    try:
        st = path.stat()
        return (int(st.st_size), int(st.st_mtime_ns))
    except OSError:
        return None


def scan_signature(path: Path) -> str:
    """Cheap operational fingerprint used by Quick Scan.

    The signature deliberately watches only the Local-Kristal envelope and known
    State surfaces.  Deep source trees are not semantic scan inputs; if operators
    need to rediscover auxiliary/legacy folders they can run Deep Scan.
    """
    path = path.resolve()
    watched = [
        path / "kristal.workspace.json",
        path / "kristal-v9.integration.json",
        path / ".kristal" / "node.json",
        path / "state" / "state-snapshot.json",
        path / "build" / "v9" / "state-snapshot.json",
        path / ".kristal" / "v9" / "state-snapshot.json",
        path / "state-snapshot.json",
        path / "canon" / "state.index.json",
        path / "AI_MANIFEST.json",
        path / "ai" / "INDEX.json",
    ]
    payload: list[tuple[str, tuple[int, int] | None]] = []
    for item in watched:
        try:
            rel = item.relative_to(path).as_posix()
        except ValueError:
            rel = str(item)
        payload.append((rel, _stat_token(item)))
    # Top-level directory metadata catches additions/removals of immediate
    # operational surfaces without recursively walking source content.
    payload.append((".", _stat_token(path)))
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()

def detect_kristal(path: Path) -> dict[str, Any] | None:
    if not path.is_dir():
        return None
    path = path.resolve()
    markers = [m for m in STRONG_MARKERS if (path / m).is_file()]
    workspace_path = path / "kristal.workspace.json"
    workspace = safe_json(workspace_path) if workspace_path.is_file() else None
    states = state_candidates(path)
    preferred = states[0] if states else None
    if not markers and workspace is None and preferred is None:
        legacy = (path / "VERSION").is_file() and (path / "README.md").is_file() and any((path / x).exists() for x in ("knowledge-base", "schemas", "canon"))
        if not legacy:
            return None
        markers = ["legacy-package"]
    title = path.name
    slug = sanitize_repo_name(path.name)
    workspace_format = None
    declared_state_ref = None
    if workspace:
        workspace_format = str(workspace.get("format") or "") or None
        title = str(workspace.get("title") or workspace.get("name") or title)
        slug = str(workspace.get("slug") or slug)
        declared_state_ref = str(workspace.get("state_ref") or "") or None
    needs_migration = bool(workspace and workspace_format != CURRENT_LOCAL_FORMAT)
    kind = "local" if workspace else ("v9" if preferred else "legacy")
    conflict = state_conflict_info(states, declared_state_ref)
    record = {
        "name": path.name,
        "title": title,
        "slug": sanitize_repo_name(slug),
        "path": str(path),
        "markers": markers,
        "workspace": workspace is not None,
        "workspace_format": workspace_format,
        "declared_state_ref": declared_state_ref,
        "needs_migration": needs_migration,
        "state_path": preferred.get("path") if preferred else None,
        "state_source": preferred.get("source") if preferred else None,
        "state_ref": preferred.get("state_ref") if preferred else None,
        "state_commitment": preferred.get("state_commitment") if preferred else None,
        "state_blob_digest": preferred.get("state_blob_digest") if preferred else None,
        "state_candidates": states,
        "state_conflict": conflict["conflict"],
        "state_conflict_reasons": conflict["reasons"],
        "kind": kind,
        "hidden_auxiliary": False,
        "scan_signature": scan_signature(path),
    }
    record["readiness"] = readiness_for_record(record)
    return record


def scan_roots(roots: list[Path]) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for root in roots:
        root = root.expanduser().resolve()
        if not root.is_dir():
            continue
        rec = detect_kristal(root)
        if rec:
            found[rec["path"]] = rec
        for current, dirnames, _filenames in os.walk(root):
            cur = Path(current)
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            if cur == root:
                continue
            rec = detect_kristal(cur)
            if rec:
                found[rec["path"]] = rec
    paths = sorted(found, key=lambda value: (value.lower(), value))
    for pth in paths:
        parent_candidates = [q for q in paths if q != pth and Path(pth).is_relative_to(Path(q))]
        parent = max(parent_candidates, key=lambda q: len(Path(q).parts), default=None)
        found[pth]["nested_under"] = parent
        # Legacy package markers inside a recognized Kristal are auxiliary content,
        # not additional top-level Local Kristals. Keep them in the registry for
        # diagnostics but hide them from the default GUI inventory.
        found[pth]["hidden_auxiliary"] = bool(parent and found[pth].get("kind") == "legacy")
        found[pth]["readiness"] = readiness_for_record(found[pth])
    return [found[pth] for pth in paths]


def scan_roots_quick(roots: list[Path], previous_entries: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Incremental scan that reuses unchanged Local Kristal records.

    A recognized Local workspace is a pruning boundary.  When its cheap scan
    signature is unchanged, the prior record and any previously observed nested
    auxiliary rows are reused and the source tree is not walked again.  New or
    changed workspaces fall back to normal discovery for that subtree.
    """
    previous_entries = previous_entries or []
    prior = {str(Path(e.get("path", "")).resolve()): e for e in previous_entries if e.get("path")}
    prior_children: dict[str, list[dict[str, Any]]] = {}
    for row in previous_entries:
        parent = row.get("nested_under")
        if parent and row.get("hidden_auxiliary"):
            prior_children.setdefault(str(Path(parent).resolve()), []).append(row)

    found: dict[str, dict[str, Any]] = {}
    for root in roots:
        root = root.expanduser().resolve()
        if not root.is_dir():
            continue
        for current, dirnames, _filenames in os.walk(root):
            cur = Path(current).resolve()
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            key = str(cur)
            old = prior.get(key)
            if old and old.get("kind") == "local" and old.get("scan_signature") == scan_signature(cur):
                cached = dict(old)
                cached["scan_cached"] = True
                found[key] = cached
                for child in prior_children.get(key, []):
                    cp = Path(str(child.get("path") or ""))
                    if cp.is_dir():
                        c = dict(child)
                        c["scan_cached"] = True
                        found[str(cp.resolve())] = c
                dirnames[:] = []
                continue

            rec = detect_kristal(cur)
            if rec:
                found[rec["path"]] = rec

    paths = sorted(found, key=lambda value: (value.lower(), value))
    for pth in paths:
        # Cached rows already carry the previous relationship. Recompute when
        # possible so renamed/moved parents are reflected immediately.
        parent_candidates = [q for q in paths if q != pth and Path(pth).is_relative_to(Path(q))]
        parent = max(parent_candidates, key=lambda q: len(Path(q).parts), default=None)
        found[pth]["nested_under"] = parent
        found[pth]["hidden_auxiliary"] = bool(parent and found[pth].get("kind") == "legacy")
        found[pth]["readiness"] = found[pth].get("readiness") or readiness_for_record(found[pth])
    return [found[pth] for pth in paths]


def find_framework_cli(workspace_root: Path, network_config: Path | None = None) -> tuple[Path | None, str | None]:
    """Locate the Kristal Framework CLI without making folder names semantic.

    The hosted-network repository is normally named ``KristalV10``, but an operator
    may keep that checkout in the long-standing local folder ``Kristal-Framework``.
    The Manager therefore accepts both exact locations under the workspace root, as
    well as non-semantic sorting prefixes/suffixes and repeated archive directories.

    ``network.toml`` still supplies the expected Framework ref; accepting an alias
    changes only local tool discovery, never the semantic/network identity.
    """
    repo_name = "KristalV10"
    framework_sha = None
    if network_config and network_config.exists():
        cfg = load_network_config(network_config)
        fw = cfg.get("framework", {}) if isinstance(cfg, dict) else {}
        repo_name = str(fw.get("repository") or repo_name).split("/")[-1]
        framework_sha = fw.get("ref")

    rel = Path("reference") / "js" / "bin" / "kristal-ref.mjs"
    candidates: list[Path] = []

    def add(base: Path) -> None:
        cli = base / rel
        if cli.is_file() and cli not in candidates:
            candidates.append(cli)

    # Exact operator locations first.  repo_name preserves network.toml preference;
    # Kristal-Framework is the supported local alias used by existing installations.
    exact_names: list[str] = []
    for name in (repo_name, "Kristal-Framework", "KristalV10"):
        if name and name.lower() not in {n.lower() for n in exact_names}:
            exact_names.append(name)
    for name in exact_names:
        add(workspace_root / name)

    try:
        children = [p for p in workspace_root.iterdir() if p.is_dir()]
    except OSError:
        children = []

    # Sorting prefixes/suffixes, e.g. A-KristalV10, A-Kristal-Framework,
    # KristalV10-main, etc.  Search all accepted operational aliases.
    needles = tuple(name.lower() for name in exact_names)
    for child in children:
        if any(needle in child.name.lower() for needle in needles):
            add(child)
            # tolerate a repeated top-level directory after unzip
            try:
                nested_children = [p for p in child.iterdir() if p.is_dir()]
            except OSError:
                nested_children = []
            for nested in nested_children:
                if any(needle in nested.name.lower() for needle in needles):
                    add(nested)

    return (candidates[0] if candidates else None, str(framework_sha) if framework_sha else None)


def framework_supports_v10(cli: Path) -> bool:
    """Return True when the discovered Framework exposes the v10 hosting commands.

    Prefer a source-level check (fast and side-effect free).  If the CLI was bundled
    without source files, fall back to ``v10-capabilities``.
    """
    src = cli.parent.parent / "src" / "cli.mjs"
    if src.is_file():
        try:
            text = src.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        required = ("v10-capabilities", "verify-node-v10", "verify-github-binding-v10")
        if all(token in text for token in required):
            return True
    node = shutil.which("node")
    if not node:
        return False
    proc = _run([node, str(cli), "v10-capabilities"], check=False)
    return proc.returncode == 0


def _version_key(text: str) -> tuple[int, int, int, int, str]:
    m = VERSION_RE.search(text)
    if not m:
        return (0, 0, 0, 0, text.lower())
    major, minor, patch = map(int, m.group(1, 2, 3))
    suffix = m.group(4) or ""
    stable = 1 if not suffix else 0
    return (major, minor, patch, stable, suffix.lower())


def find_local_tool(workspace_root: Path) -> Path | None:
    """Find the newest Local/Authoring Kit under the workspace root.

    Folder names may have non-semantic sorting prefixes such as ``A-``.  Discovery
    therefore keys on the package marker appearing anywhere in the immediate child
    name instead of requiring the name to start with it.
    """
    candidates: list[tuple[tuple[int, int, int, int, str], Path]] = []
    markers = ("kristal-authoring-kit", "kristal-local-kit")
    try:
        packages = [p for p in workspace_root.iterdir() if p.is_dir() and any(m in p.name.lower() for m in markers)]
    except OSError:
        packages = []

    def add_tool(tool: Path, package: Path) -> None:
        if not tool.is_file():
            return
        version_text = package.name
        version_file = package / "VERSION"
        if version_file.is_file():
            version_text += " " + version_file.read_text(encoding="utf-8", errors="ignore").strip()
        candidates.append((_version_key(version_text), tool))

    for package in packages:
        add_tool(package / "tools" / "kristal.py", package)
        # tolerate archives extracted with a repeated top-level directory
        try:
            nested_packages = [p for p in package.iterdir() if p.is_dir()]
        except OSError:
            nested_packages = []
        for nested in nested_packages:
            if any(m in nested.name.lower() for m in markers):
                add_tool(nested / "tools" / "kristal.py", nested)

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


# Compatibility alias for alpha.1 callers.
find_authoring_tool = find_local_tool


def local_tool_version(tool: Path | None) -> str | None:
    if not tool:
        return None
    for candidate in (tool.parent.parent / "VERSION", tool.parent.parent.parent / "VERSION"):
        if candidate.is_file():
            value = candidate.read_text(encoding="utf-8", errors="ignore").strip()
            if value:
                return value
    match = VERSION_RE.search(str(tool))
    return match.group(0) if match else None


def _small_file_digest(path: Path) -> str | None:
    try:
        if not path.is_file():
            return None
        return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def validation_cache_key(record: dict[str, Any], *, workspace_root: Path, network_config: Path | None = None) -> str:
    """Fingerprint the validation inputs without traversing the whole source tree."""
    local_path = Path(str(record.get("path") or "")).resolve()
    tool = find_local_tool(workspace_root)
    cli, framework_sha = find_framework_cli(workspace_root, network_config)
    payload = {
        "workspace_format": record.get("workspace_format"),
        "state_ref": record.get("state_ref"),
        "state_commitment": record.get("state_commitment"),
        "state_blob_digest": record.get("state_blob_digest"),
        "state_conflict": bool(record.get("state_conflict")),
        "workspace_json": _small_file_digest(local_path / "kristal.workspace.json"),
        "state_index": _small_file_digest(local_path / "canon" / "state.index.json"),
        "local_tool": str(tool) if tool else None,
        "local_tool_stat": _stat_token(tool) if tool else None,
        "framework_cli": str(cli) if cli else None,
        "framework_cli_stat": _stat_token(cli) if cli else None,
        "framework_ref": framework_sha,
        "network_config_stat": _stat_token(network_config) if network_config else None,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def inspect_with_local_tool(path: Path, tool: Path) -> dict[str, Any] | None:
    """Use Local Kit 3.2.2+ machine-readable inspection when available."""
    python = shutil.which("python") or shutil.which("py") or "python"
    proc = _run([python, str(tool), "inspect", str(path), "--compact"], check=False)
    if proc.returncode:
        return None
    try:
        value = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict) or value.get("format") != "kristal.local-inspection/1.0":
        return None
    return value


def validate_local(
    path: Path, *, workspace_root: Path, network_config: Path | None = None,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    path = path.resolve()
    _progress(progress, f"{path.name}: detect workspace/state")
    rec = detect_kristal(path)
    if not rec:
        raise ManagerError(f"Folder is not recognized as a Kristal: {path}")
    checks: list[dict[str, Any]] = []
    overall = "VALID"
    tool: Path | None = None
    tool_version: str | None = None

    if rec.get("workspace"):
        if rec.get("needs_migration"):
            checks.append({
                "check": "local-workspace-format",
                "status": "MIGRATE",
                "found": rec.get("workspace_format"),
                "expected": CURRENT_LOCAL_FORMAT,
            })
            overall = "MIGRATE"
        else:
            tool = find_local_tool(workspace_root)
            tool_version = local_tool_version(tool)
            if tool:
                _progress(progress, f"{path.name}: Local Kit check")
                python = shutil.which("python") or shutil.which("py") or "python"
                proc = _run([python, str(tool), "check", str(path)], check=False)
                checks.append({
                    "check": "local-envelope",
                    "status": "PASS" if proc.returncode == 0 else "FAIL",
                    "tool": str(tool),
                    "tool_version": tool_version,
                    "output": (proc.stdout or proc.stderr or "").strip()[-4000:],
                })
                if proc.returncode:
                    overall = "INVALID"
                _progress(progress, f"{path.name}: Local Kit inspect/interoperability")
                inspection = inspect_with_local_tool(path, tool)
                if inspection:
                    inspected = inspection.get("state") if isinstance(inspection.get("state"), dict) else None
                    inspected_commitment = ((inspected or {}).get("logical_commitment") or {}).get("digest") if inspected else None
                    inspected_path = str((path / str(inspected.get("path"))).resolve()) if inspected and inspected.get("path") else None
                    manager_path = rec.get("state_path")
                    aligned = (inspected_path == manager_path and inspected_commitment == rec.get("state_commitment")) if inspected else (manager_path is None)
                    checks.append({
                        "check": "local-inspection-interop",
                        "status": "PASS" if aligned else "FAIL",
                        "format": inspection.get("format"),
                        "kit_version": inspection.get("kit_version"),
                        "inspected_state_path": inspected_path,
                        "manager_state_path": manager_path,
                    })
                    if not aligned:
                        overall = "INVALID"
            else:
                checks.append({"check": "local-envelope", "status": "UNAVAILABLE", "reason": "Kristal Local/Authoring Kit not found"})
                if overall == "VALID":
                    overall = "PARTIAL"

    _progress(progress, f"{path.name}: compare current state surfaces")
    if rec.get("state_conflict"):
        checks.append({
            "check": "state-surface-consistency",
            "status": "FAIL",
            "reasons": rec.get("state_conflict_reasons", []),
            "candidates": rec.get("state_candidates", []),
        })
        if overall not in {"MIGRATE", "INVALID"}:
            overall = "STATE CONFLICT"
    else:
        current = current_state_candidates(rec.get("state_candidates", []))
        legacy = legacy_state_candidates(rec.get("state_candidates", []))
        if len(current) > 1:
            checks.append({"check": "state-surface-consistency", "status": "PASS", "candidate_count": len(current)})
        if current and legacy:
            differing_legacy = [x for x in legacy if (x.get("state_ref"), x.get("state_commitment")) != (current[0].get("state_ref"), current[0].get("state_commitment"))]
            if differing_legacy:
                checks.append({
                    "check": "legacy-state-history",
                    "status": "OBSERVED",
                    "reason": "Legacy .kristal/root state differs from the current Local Kit state; treated as historical compatibility output.",
                    "candidates": differing_legacy,
                })

    state_path = Path(rec["state_path"]) if rec.get("state_path") else None
    if state_path and state_path.is_file():
        cli, framework_sha = find_framework_cli(workspace_root, network_config)
        if cli:
            _progress(progress, f"{path.name}: Framework verify-state-v9")
            require_tool("node")
            proc = _run(["node", str(cli), "verify-state-v9", str(state_path)], check=False)
            raw = (proc.stdout or "").strip()
            try:
                detail = json.loads(raw) if raw else {"stderr": (proc.stderr or "").strip()}
            except json.JSONDecodeError:
                detail = {"output": raw or (proc.stderr or "").strip()}
            checks.append({
                "check": "state-v9",
                "status": "PASS" if proc.returncode == 0 else "FAIL",
                "state_source": rec.get("state_source"),
                "state_path": str(state_path),
                "framework_sha": framework_sha,
                "framework_cli": str(cli),
                "detail": detail,
            })
            if proc.returncode:
                overall = "INVALID"
        else:
            checks.append({"check": "state-v9", "status": "UNAVAILABLE", "reason": "Kristal Framework CLI not found"})
            if overall == "VALID":
                overall = "PARTIAL"
    elif rec.get("workspace") and not rec.get("needs_migration"):
        checks.append({"check": "state-v9", "status": "MISSING", "reason": "No v9 State Snapshot found"})
        if overall == "VALID":
            overall = "NO STATE"

    if rec.get("workspace") and not rec.get("needs_migration") and not current_state_candidates(rec.get("state_candidates", [])) and rec.get("state_path"):
        checks.append({
            "check": "current-state-surface",
            "status": "MISSING",
            "reason": "Only a legacy/root v9 snapshot is present. Run Local Kit build-v9 to create a current state surface.",
        })
        if overall in {"VALID", "PARTIAL"}:
            overall = "LEGACY STATE"

    if not checks:
        checks.append({"check": "legacy-detection", "status": "OBSERVED", "reason": "Legacy package detected; no current Local/state validator surface found"})
        overall = "LEGACY"

    result = {
        "path": str(path),
        "kind": rec["kind"],
        "workspace_format": rec.get("workspace_format"),
        "needs_migration": rec.get("needs_migration", False),
        "result": overall,
        "readiness": rec.get("readiness"),
        "checks": checks,
        "local_tool_version": tool_version,
        "state_path": rec.get("state_path"),
        "state_source": rec.get("state_source"),
        "state_ref": rec.get("state_ref"),
        "state_commitment": rec.get("state_commitment"),
        "state_blob_digest": rec.get("state_blob_digest"),
        "state_candidates": rec.get("state_candidates", []),
        "state_conflict": rec.get("state_conflict", False),
        "state_conflict_reasons": rec.get("state_conflict_reasons", []),
    }
    result["validation_cache_key"] = validation_cache_key(result, workspace_root=workspace_root, network_config=network_config)
    result["cached"] = False
    _progress(progress, f"{path.name}: validation {overall}")
    return result


def validate_local_cached(
    path: Path, *, previous: dict[str, Any] | None, workspace_root: Path,
    network_config: Path | None = None, progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Return a previous VALID result when the validation inputs are unchanged."""
    path = path.resolve()
    _progress(progress, f"{path.name}: validation cache check")
    rec = detect_kristal(path)
    if not rec:
        raise ManagerError(f"Folder is not recognized as a Kristal: {path}")
    key = validation_cache_key(rec, workspace_root=workspace_root, network_config=network_config)
    if previous and previous.get("last_validation_result") == "VALID" and previous.get("last_validation_cache_key") == key:
        _progress(progress, f"{path.name}: VALID cache hit")
        return {
            "path": str(path),
            "kind": rec.get("kind"),
            "workspace_format": rec.get("workspace_format"),
            "needs_migration": rec.get("needs_migration", False),
            "result": "VALID",
            "readiness": rec.get("readiness"),
            "checks": [{"check": "validation-cache", "status": "PASS", "reason": "State/envelope/toolchain inputs unchanged"}],
            "local_tool_version": None,
            "state_path": rec.get("state_path"),
            "state_source": rec.get("state_source"),
            "state_ref": rec.get("state_ref"),
            "state_commitment": rec.get("state_commitment"),
            "state_blob_digest": rec.get("state_blob_digest"),
            "state_candidates": rec.get("state_candidates", []),
            "state_conflict": rec.get("state_conflict", False),
            "state_conflict_reasons": rec.get("state_conflict_reasons", []),
            "validation_cache_key": key,
            "cached": True,
        }
    _progress(progress, f"{path.name}: cache miss; full validation")
    result = validate_local(path, workspace_root=workspace_root, network_config=network_config, progress=progress)
    result["validation_cache_key"] = validation_cache_key(result, workspace_root=workspace_root, network_config=network_config)
    return result


def _migration_snapshot(path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = path / ".kristal-manager" / "migrations"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"pre-local-3.2-{stamp}.zip"
    keep = [path / "kristal.workspace.json", path / "canon" / "state.index.json", path / "tools" / "kristal.py"]
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for file in keep:
            if file.is_file():
                z.write(file, arcname=file.relative_to(path).as_posix())
    return out


def migrate_local(path: Path, *, workspace_root: Path, network_config: Path | None = None) -> dict[str, Any]:
    path = path.resolve()
    before = detect_kristal(path)
    if not before or not before.get("workspace"):
        raise ManagerError("Selected folder is not a Local Kristal workspace")
    if not before.get("needs_migration"):
        return {"path": str(path), "result": "ALREADY CURRENT", "workspace_format": before.get("workspace_format")}
    tool = find_local_tool(workspace_root)
    if not tool:
        raise ManagerError("Kristal Local/Authoring Kit 3.2+ was not found under the workspace root")
    snapshot = _migration_snapshot(path)
    python = shutil.which("python") or shutil.which("py") or "python"
    p = _run([python, str(tool), "migrate-v10", str(path)], check=False)
    if p.returncode:
        raise ManagerError(f"Migration failed. Safety snapshot: {snapshot}\n{(p.stderr or p.stdout or '').strip()}")
    after = detect_kristal(path)
    if not after or after.get("workspace_format") != CURRENT_LOCAL_FORMAT:
        raise ManagerError(f"Migration command completed but workspace is not {CURRENT_LOCAL_FORMAT}. Safety snapshot: {snapshot}")
    # Migration is envelope/tooling evolution; an already materialized state must not change.
    before_commit = before.get("state_commitment")
    after_commit = after.get("state_commitment")
    if before_commit and after_commit and before_commit != after_commit:
        raise ManagerError(f"Migration changed observed state commitment: {before_commit} -> {after_commit}. Safety snapshot: {snapshot}")
    validation = validate_local(path, workspace_root=workspace_root, network_config=network_config)
    if validation["result"] not in {"VALID", "PARTIAL"}:
        raise ManagerError(f"Migration completed but validation is {validation['result']}. Safety snapshot: {snapshot}")
    return {
        "path": str(path),
        "from_format": before.get("workspace_format"),
        "to_format": after.get("workspace_format"),
        "state_commitment_before": before_commit,
        "state_commitment_after": after_commit,
        "safety_snapshot": str(snapshot),
        "validation": validation,
        "result": "MIGRATION PASS",
    }


def git_root(path: Path) -> Path | None:
    p = _run(["git", "-C", str(path), "rev-parse", "--show-toplevel"], check=False)
    if p.returncode:
        return None
    raw = (p.stdout or "").strip()
    return Path(raw).resolve() if raw else None


def has_own_git(path: Path) -> bool:
    return (path / ".git").exists()


def scan_sensitive_files(path: Path) -> list[str]:
    hits: list[str] = []
    for p in path.rglob("*"):
        if not p.is_file():
            continue
        try:
            rel = p.relative_to(path)
        except ValueError:
            continue
        if ".git" in rel.parts:
            continue
        name = p.name.lower()
        if name in SENSITIVE_NAMES or p.suffix.lower() in SENSITIVE_SUFFIXES or name.startswith(".env."):
            hits.append(rel.as_posix())
    return sorted(hits)


def repo_status(path: Path) -> dict[str, Any]:
    if not has_own_git(path):
        parent_root = git_root(path)
        return {"git": False, "nested_git_parent": str(parent_root) if parent_root and parent_root != path.resolve() else None, "dirty": None, "head": None}
    dirty = bool((_run(["git", "-C", str(path), "status", "--porcelain"]).stdout or "").strip())
    head_p = _run(["git", "-C", str(path), "rev-parse", "HEAD"], check=False)
    head = (head_p.stdout or "").strip() if head_p.returncode == 0 else None
    return {"git": True, "nested_git_parent": None, "dirty": dirty, "head": head}


def github_repo_info(owner: str, repo: str) -> dict[str, Any] | None:
    require_tool("gh")
    p = _run(["gh", "repo", "view", f"{owner}/{repo}", "--json", "nameWithOwner,visibility,url,defaultBranchRef"], check=False)
    if p.returncode:
        return None
    try:
        return json.loads(p.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ManagerError(f"Invalid GitHub response for {owner}/{repo}") from exc


def ensure_backup_repo(path: Path, *, owner: str, repo: str, visibility: str, description: str = "") -> dict[str, Any]:
    require_tool("git"); require_tool("gh")
    path = path.resolve()
    if visibility not in {"public", "private"}:
        raise ManagerError("Backup visibility must be public or private")
    if not has_own_git(path):
        parent = git_root(path.parent)
        if parent and path.is_relative_to(parent):
            raise ManagerError(
                f"Cannot initialize an independent backup repository inside another Git worktree ({parent}). "
                "Move this Kristal beside the parent repository, or give it its own repository/submodule deliberately."
            )
        _run(["git", "init", "-b", "main", str(path)])
    info = github_repo_info(owner, repo)
    if info is None:
        _run(["gh", "repo", "create", f"{owner}/{repo}", f"--{visibility}", "--description", description or f"Backup of local Kristal {path.name}"])
        info = github_repo_info(owner, repo)
    if info is None:
        raise ManagerError(f"GitHub repository was not created or cannot be read: {owner}/{repo}")
    actual = str(info.get("visibility", "")).lower()
    if actual and actual != visibility:
        raise ManagerError(f"GitHub repository visibility is {actual}, but manager configuration requires {visibility}. Change it explicitly before backup.")
    remotes = (_run(["git", "-C", str(path), "remote"], check=False).stdout or "").split()
    url = f"https://github.com/{owner}/{repo}.git"
    if REMOTE_NAME in remotes:
        _run(["git", "-C", str(path), "remote", "set-url", REMOTE_NAME, url])
    else:
        _run(["git", "-C", str(path), "remote", "add", REMOTE_NAME, url])
    return info


def backup_local(path: Path, *, owner: str, repo: str, visibility: str, message: str | None = None) -> dict[str, Any]:
    path = path.resolve()
    if visibility == "public":
        # Full-workspace backup cannot be covered by a read-surface grant:
        # it includes unqualified/unreviewed paths, even if current heuristics
        # do not flag those paths as secrets. Private backups are unaffected.
        raise ManagerError("Public full-workspace backup disabled by C2. Use a private backup; publish only a qualified, explicitly authorized read surface.")
    info = ensure_backup_repo(path, owner=owner, repo=repo, visibility=visibility)
    _run(["git", "-C", str(path), "add", "-A"])
    staged = (_run(["git", "-C", str(path), "diff", "--cached", "--name-only"]).stdout or "").strip()
    committed = False
    if staged:
        msg = message or f"Kristal backup {utc_now()}"
        email = f"{owner}@users.noreply.github.com"
        _run(["git", "-C", str(path), "-c", "user.name=Kristal Manager", "-c", f"user.email={email}", "commit", "-m", msg])
        committed = True
    head = _run(["git", "-C", str(path), "rev-parse", "HEAD"], check=False)
    if head.returncode:
        placeholder = path / ".kristal-backup-placeholder"
        placeholder.write_text("Kristal Manager backup placeholder.\n", encoding="utf-8")
        _run(["git", "-C", str(path), "add", placeholder.name])
        _run(["git", "-C", str(path), "-c", "user.name=Kristal Manager", "-c", f"user.email={owner}@users.noreply.github.com", "commit", "-m", "Initialize Kristal backup"])
        committed = True
    _run(["git", "-C", str(path), "push", "-u", REMOTE_NAME, "HEAD:main"])
    sha = (_run(["git", "-C", str(path), "rev-parse", "HEAD"]).stdout or "").strip()
    return {"repository": f"{owner}/{repo}", "visibility": visibility, "url": info.get("url"), "sha": sha, "committed": committed, "result": "BACKUP PASS"}


def safe_extract_zip(zip_path: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    dest_abs = dest.resolve()
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            raw = info.filename.replace("\\", "/")
            if not raw or raw.startswith("__MACOSX/"):
                continue
            pp = PurePosixPath(raw)
            if pp.is_absolute() or ".." in pp.parts:
                raise ManagerError(f"Unsafe ZIP member rejected: {raw}")
            out = dest.joinpath(*pp.parts)
            out_abs = out.resolve()
            if os.path.commonpath([str(dest_abs), str(out_abs)]) != str(dest_abs):
                raise ManagerError(f"ZIP path escape rejected: {raw}")
            if info.is_dir():
                out.mkdir(parents=True, exist_ok=True)
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as src, out.open("wb") as dst:
                    shutil.copyfileobj(src, dst, length=1024 * 1024)


def tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted((x for x in root.rglob("*") if x.is_file() and ".git" not in x.parts), key=lambda x: x.relative_to(root).as_posix().encode("utf-8")):
        rel = p.relative_to(root).as_posix()
        h.update(rel.encode("utf-8")); h.update(b"\0")
        with p.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
    return h.hexdigest()


def import_local(source: Path, locals_root: Path) -> list[Path]:
    """Non-destructive import. Source is never moved/deleted; existing differing targets are refused."""
    locals_root = locals_root.resolve(); locals_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="kristal-import-") as td:
        temp = Path(td)
        if source.is_file() and source.suffix.lower() == ".zip":
            safe_extract_zip(source, temp)
            roots = [p for p in temp.iterdir() if p.is_dir() and p.name != "__MACOSX"]
            if len(roots) == 1 and detect_kristal(roots[0]):
                candidates = roots
            else:
                candidates = [p for p in roots if detect_kristal(p)]
                if not candidates:
                    candidates = [p for p in temp.glob("*/*") if p.is_dir() and detect_kristal(p)]
        elif source.is_dir():
            candidates = [source]
        else:
            raise ManagerError("Import source must be a Kristal folder or ZIP")
        if not candidates:
            raise ManagerError("No recognizable Kristal found in import source")
        installed: list[Path] = []
        for candidate in candidates:
            if candidate.name == "MediKristal":
                continue
            name = normalize_package_name(candidate.name)
            dest = locals_root / name
            if dest.exists():
                if tree_digest(dest) == tree_digest(candidate):
                    installed.append(dest)
                    continue
                raise ManagerError(f"Import conflict: {dest} already exists with different content")
            shutil.copytree(candidate, dest)
            installed.append(dest)
        return installed


def default_scan_roots(workspace_root: Path) -> list[str]:
    roots = [workspace_root / DEFAULT_LOCAL_DIRNAME]
    legacy = workspace_root / "Kristal-Kollection"
    for candidate in (legacy / "domains", legacy / "universities", legacy / "tailored"):
        if candidate.is_dir():
            roots.append(candidate)
    return [str(p) for p in roots]


def load_manager_config(path: Path, workspace_root: Path) -> dict[str, Any]:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("format", REGISTRY_FORMAT)
            data.setdefault("workspace_root", str(workspace_root))
            data.setdefault("scan_roots", default_scan_roots(workspace_root))
            data.setdefault("entries", [])
            return data
    return {"format": REGISTRY_FORMAT, "workspace_root": str(workspace_root), "scan_roots": default_scan_roots(workspace_root), "entries": []}


def save_manager_config(path: Path, data: dict[str, Any]) -> None:
    data = dict(data)
    data["format"] = REGISTRY_FORMAT
    data["updated_at"] = utc_now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def merge_scan(config: dict[str, Any], scanned: list[dict[str, Any]]) -> dict[str, Any]:
    old = {str(Path(e.get("path", "")).resolve()): e for e in config.get("entries", []) if e.get("path")}
    entries: list[dict[str, Any]] = []
    for rec in scanned:
        key = str(Path(rec["path"]).resolve())
        prior = old.get(key, {})
        state_changed = bool(prior) and (
            prior.get("state_commitment") != rec.get("state_commitment")
            or prior.get("state_blob_digest") != rec.get("state_blob_digest")
            or prior.get("state_ref") != rec.get("state_ref")
            or prior.get("workspace_format") != rec.get("workspace_format")
            or bool(prior.get("state_conflict")) != bool(rec.get("state_conflict"))
        )
        last_validation = None if state_changed else prior.get("last_validation")
        last_validation_result = None if state_changed else prior.get("last_validation_result")
        last_validation_cache_key = None if state_changed else prior.get("last_validation_cache_key")
        merged = {
            "path": key,
            "title": rec.get("title") or prior.get("title") or Path(key).name,
            "slug": rec.get("slug") or prior.get("slug") or sanitize_repo_name(Path(key).name),
            "kind": rec.get("kind") or prior.get("kind") or "unknown",
            "workspace_format": rec.get("workspace_format"),
            "declared_state_ref": rec.get("declared_state_ref"),
            "needs_migration": bool(rec.get("needs_migration")),
            "readiness": rec.get("readiness") or readiness_for_record(rec),
            "backup_repository": prior.get("backup_repository", ""),
            "backup_visibility": prior.get("backup_visibility", "private"),
            "publication_target": prior.get("publication_target", "none"),
            "last_sync_at": prior.get("last_sync_at"),
            "last_sync_commit": prior.get("last_sync_commit"),
            "last_sync_repository": prior.get("last_sync_repository"),
            "last_sync_state_path": prior.get("last_sync_state_path"),
            "last_sync_blob_digest": prior.get("last_sync_blob_digest"),
            "last_sync_surface_digest": prior.get("last_sync_surface_digest"),
            "last_sync_surface_root": prior.get("last_sync_surface_root"),
            "last_sync_entrypoint": prior.get("last_sync_entrypoint"),
            "last_sync_file_count": prior.get("last_sync_file_count"),
            "last_sync_total_bytes": prior.get("last_sync_total_bytes"),
            "last_validation": last_validation,
            "last_validation_result": last_validation_result,
            "last_validation_cache_key": last_validation_cache_key,
            "last_backup_at": prior.get("last_backup_at"),
            "last_backup_sha": prior.get("last_backup_sha"),
            "last_publish_request": prior.get("last_publish_request"),
            "state_path": rec.get("state_path"),
            "state_source": rec.get("state_source"),
            "state_ref": rec.get("state_ref"),
            "state_commitment": rec.get("state_commitment"),
            "state_blob_digest": rec.get("state_blob_digest"),
            "state_candidates": rec.get("state_candidates", []),
            "state_conflict": bool(rec.get("state_conflict")),
            "state_conflict_reasons": rec.get("state_conflict_reasons", []),
            "nested_under": rec.get("nested_under"),
            "hidden_auxiliary": bool(rec.get("hidden_auxiliary")),
            "markers": rec.get("markers", []),
            "scan_signature": rec.get("scan_signature") or prior.get("scan_signature"),
        }
        entries.append(merged)
    config = dict(config)
    config["entries"] = sorted(entries, key=lambda e: (e.get("title", "").lower(), e["path"].lower()))
    return config


def resolve_publication_collection(network_config: Path, target: str) -> dict[str, str]:
    if target not in {"public", "private"}:
        raise ManagerError("Publication target must be public or private")
    cfg = load_network_config(network_config)
    owner = str((cfg.get("account") or {}).get("owner") or "").strip()
    if not owner:
        raise ManagerError(f"GitHub account.owner is missing in {network_config}")
    collections = cfg.get("collections") or []
    for item in collections:
        if isinstance(item, dict) and str(item.get("visibility") or "").lower() == target:
            name = str(item.get("name") or "").strip()
            if name:
                return {"owner": owner, "name": name, "repository": f"{owner}/{name}", "visibility": target}
    raise ManagerError(f"No {target} collection is configured in {network_config}")


def _default_branch(network_config: Path) -> str:
    cfg = load_network_config(network_config)
    branch = str((cfg.get("policy") or {}).get("default_branch") or "main").strip()
    return branch or "main"


def _repo_remote_matches(url: str, repository: str) -> bool:
    value = url.strip().lower().removesuffix(".git")
    repo = repository.strip().lower()
    return value.endswith("/" + repo) or value.endswith(":" + repo)


def github_remote_file_digest(repository: str, branch: str, state_path: str) -> str | None:
    """Return SHA-256 of one hosted collection file using the GitHub Contents API."""
    require_tool("gh")
    endpoint = f"repos/{repository}/contents/{state_path}"
    proc = _run(["gh", "api", "--method", "GET", endpoint, "-f", f"ref={branch}", "--jq", ".content"], check=False)
    if proc.returncode:
        return None
    encoded = "".join((proc.stdout or "").split())
    if not encoded:
        return None
    try:
        data = base64.b64decode(encoded, validate=False)
    except Exception:
        return None
    return "sha256:" + hashlib.sha256(data).hexdigest()


def github_remote_json_file(repository: str, branch: str, path: str) -> dict[str, Any] | None:
    """Fetch one small JSON file from GitHub without cloning/fetching the collection."""
    require_tool("gh")
    endpoint = f"repos/{repository}/contents/{path}"
    proc = _run(["gh", "api", "--method", "GET", endpoint, "-f", f"ref={branch}", "--jq", ".content"], check=False)
    if proc.returncode:
        return None
    encoded = "".join((proc.stdout or "").split())
    if not encoded:
        return None
    try:
        value = json.loads(base64.b64decode(encoded, validate=False).decode("utf-8"))
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _safe_relative_posix(value: str, *, label: str) -> PurePosixPath:
    raw = str(value or "").replace("\\", "/")
    rel = PurePosixPath(raw)
    if not raw or rel.is_absolute() or ".." in rel.parts or "." in rel.parts or any(not part for part in rel.parts):
        raise ManagerError(f"Unsafe {label}: {value!r}")
    return rel


def _safe_surface_root(value: str) -> PurePosixPath:
    rel = _safe_relative_posix(value, label="GitHub read-surface target_root")
    if len(rel.parts) != 2 or rel.parts[0] != "kristals":
        raise ManagerError(f"Read surface target_root must be exactly kristals/<slug>, got {rel.as_posix()!r}")
    if rel.parts[1] == "index.json":
        raise ManagerError("Read surface slug collides with the collection index")
    return rel


def _surface_state_item(surface: dict[str, Any]) -> dict[str, Any] | None:
    for item in surface.get("files") or []:
        if isinstance(item, dict) and item.get("role") == "state_snapshot":
            return item
    for item in surface.get("files") or []:
        if isinstance(item, dict) and str(item.get("path") or "").replace("\\", "/") == "state/state-snapshot.json":
            return item
    return None


def prepare_github_read_surface(
    entry: dict[str, Any], *, workspace_root: Path, refresh_ai: bool = True,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Ask Local Kit 3.2.4+ for the exact GitHub/AI read projection.

    The Manager deliberately does not invent its own list of canonical/docs/AI files.
    Local Kit owns the projection contract; Manager verifies it, transports it, and
    adds only host-operational metadata outside the semantic commitment.
    """
    local_path = Path(str(entry.get("path") or "")).resolve()
    title = str(entry.get("title") or entry.get("slug") or local_path.name)
    tool = find_local_tool(workspace_root)
    if not tool:
        raise ManagerError("Kristal Local/Authoring Kit was not found. GitHub read-surface Sync requires Local Kit 3.2.4+.")
    version = local_tool_version(tool) or "unknown"
    version_match = VERSION_RE.search(version)
    if version_match and tuple(map(int, version_match.group(1, 2, 3))) < (3, 2, 4):
        raise ManagerError(f"Local Kit {version} is too old for read-surface Sync; update to 3.2.4 or newer")
    python = shutil.which("python") or shutil.which("py") or "python"

    if refresh_ai:
        _progress(progress, f"{title}: refresh portable AI read layer")
        built = _run([python, str(tool), "build-ai", str(local_path)], check=False)
        if built.returncode:
            raise ManagerError(f"Local Kit build-ai failed: {(built.stderr or built.stdout or '').strip()}")

    _progress(progress, f"{title}: Local Kit read-surface")
    proc = _run([python, str(tool), "read-surface", str(local_path), "--require-ready", "--compact"], check=False)
    if proc.returncode:
        raise ManagerError(f"Local Kit read-surface is not ready: {(proc.stderr or proc.stdout or '').strip()}")
    try:
        surface = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ManagerError("Local Kit returned invalid read-surface JSON") from exc
    if not isinstance(surface, dict) or surface.get("format") != GITHUB_READ_SURFACE_FORMAT:
        raise ManagerError(f"Unsupported Local Kit read-surface format: {surface.get('format') if isinstance(surface, dict) else None}")
    if not surface.get("ready"):
        raise ManagerError("Local Kit read-surface reports not ready: " + "; ".join(map(str, surface.get("errors") or [])))

    root_rel = _safe_surface_root(str(surface.get("target_root") or ""))
    files = surface.get("files")
    if not isinstance(files, list) or not files:
        raise ManagerError("Local Kit read-surface contains no files")
    seen: set[str] = set()
    normalized_files: list[dict[str, Any]] = []
    for item in files:
        if not isinstance(item, dict):
            raise ManagerError("Local Kit read-surface contains an invalid file entry")
        rel = _safe_relative_posix(str(item.get("path") or ""), label="read-surface file path")
        rel_text = rel.as_posix()
        if rel_text in seen:
            raise ManagerError(f"Duplicate read-surface file path: {rel_text}")
        seen.add(rel_text)
        source = (local_path / Path(rel_text)).resolve()
        try:
            source.relative_to(local_path)
        except ValueError as exc:
            raise ManagerError(f"Read-surface source escapes Local Kristal: {rel_text}") from exc
        if not source.is_file():
            raise ManagerError(f"Read-surface source is missing: {source}")
        actual_size = source.stat().st_size
        actual_digest = _sha256_file(source)
        expected_size = item.get("size")
        expected_digest = str(item.get("sha256") or "")
        if expected_size is not None and int(expected_size) != actual_size:
            raise ManagerError(f"Read-surface size drift for {rel_text}: expected {expected_size}, got {actual_size}")
        if expected_digest and expected_digest != actual_digest:
            raise ManagerError(f"Read-surface digest drift for {rel_text}: expected {expected_digest}, got {actual_digest}")
        normalized_files.append({**item, "path": rel_text, "size": actual_size, "sha256": actual_digest})

    surface = dict(surface)
    surface["target_root"] = root_rel.as_posix()
    surface["files"] = normalized_files
    state_item = _surface_state_item(surface)
    if not state_item:
        raise ManagerError("Read surface does not expose a state_snapshot file")

    rec = detect_kristal(local_path)
    if not rec or rec.get("readiness") != "READY" or rec.get("state_conflict"):
        raise ManagerError(f"Read-surface Sync blocked: Local Kristal health is {(rec or {}).get('readiness') or 'UNKNOWN'}")
    commitment = surface.get("state_logical_commitment") if isinstance(surface.get("state_logical_commitment"), dict) else {}
    if surface.get("state_ref") != rec.get("state_ref"):
        raise ManagerError(f"Read-surface state_ref mismatch: {surface.get('state_ref')} != {rec.get('state_ref')}")
    if commitment.get("digest") != rec.get("state_commitment"):
        raise ManagerError(f"Read-surface commitment mismatch: {commitment.get('digest')} != {rec.get('state_commitment')}")

    return {
        "entry": dict(entry),
        "local_path": str(local_path),
        "local_tool": str(tool),
        "local_tool_version": version,
        "surface": surface,
        "state_path_in_surface": str(state_item.get("path")),
    }


def _sensitive_surface_paths(surface: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    for item in surface.get("files") or []:
        rel = str((item or {}).get("path") or "")
        name = PurePosixPath(rel).name.lower()
        suffix = PurePosixPath(rel).suffix.lower()
        if name in SENSITIVE_NAMES or suffix in SENSITIVE_SUFFIXES or name.startswith(".env."):
            hits.append(rel)
    return sorted(set(hits))


def _sync_manifest(prepared: dict[str, Any]) -> dict[str, Any]:
    surface = prepared["surface"]
    entry = prepared["entry"]
    return {
        "format": GITHUB_SYNC_MANIFEST_FORMAT,
        "manager_version": VERSION,
        "read_surface_format": surface.get("format"),
        "local_kit_version": surface.get("kit_version") or prepared.get("local_tool_version"),
        "slug": surface.get("slug"),
        "title": entry.get("title") or surface.get("slug"),
        "target_root": surface.get("target_root"),
        "entrypoint": surface.get("entrypoint"),
        "state_ref": surface.get("state_ref"),
        "state_logical_commitment": surface.get("state_logical_commitment"),
        "surface_digest": surface.get("surface_digest"),
        "file_count": surface.get("file_count"),
        "total_bytes": surface.get("total_bytes"),
        "materialization_object_count": surface.get("materialization_object_count", 0),
        "files": [
            {
                "path": item.get("path"),
                "role": item.get("role"),
                "size": item.get("size"),
                "sha256": item.get("sha256"),
            }
            for item in surface.get("files") or []
        ],
        "policy": {
            "derived_read_surface": True,
            "sync_is_not_publication": True,
            "activation_is_separate": True,
            "materialization_blobs_are_not_implicitly_copied": True,
        },
    }


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _collection_index_entry(prepared: dict[str, Any]) -> dict[str, Any]:
    surface = prepared["surface"]
    entry = prepared["entry"]
    root = str(surface["target_root"])
    return {
        "slug": surface.get("slug"),
        "title": entry.get("title") or surface.get("slug"),
        "path": root,
        "entrypoint": f"{root}/{surface.get('entrypoint') or 'AI_START_HERE.md'}",
        "state_ref": surface.get("state_ref"),
        "state_logical_commitment": surface.get("state_logical_commitment"),
        "surface_digest": surface.get("surface_digest"),
        "file_count": surface.get("file_count"),
        "total_bytes": surface.get("total_bytes"),
        "materialization_object_count": surface.get("materialization_object_count", 0),
    }


def _build_collection_index(existing: dict[str, Any] | None, updates: list[dict[str, Any]]) -> dict[str, Any]:
    rows: dict[str, dict[str, Any]] = {}
    if isinstance(existing, dict) and existing.get("format") == GITHUB_COLLECTION_INDEX_FORMAT:
        for item in existing.get("kristals") or []:
            if isinstance(item, dict) and item.get("path"):
                rows[str(item["path"])] = dict(item)

    # Keep one hosted path per state identity and one identity per hosted path.
    for prepared in updates:
        item = _collection_index_entry(prepared)
        path = str(item["path"])
        state_ref = str(item.get("state_ref") or "")
        prior = rows.get(path)
        if prior and prior.get("state_ref") and prior.get("state_ref") != state_ref:
            raise ManagerError(f"Collection index path collision at {path}: {prior.get('state_ref')} != {state_ref}")
        for other_path, other in rows.items():
            if other_path != path and state_ref and other.get("state_ref") == state_ref:
                raise ManagerError(f"Collection index identity collision: {state_ref} already exists at {other_path}")
        rows[path] = item

    ordered = sorted(rows.values(), key=lambda x: (str(x.get("slug") or "").encode("utf-8"), str(x.get("path") or "").encode("utf-8")))
    projection = {"format": GITHUB_COLLECTION_INDEX_FORMAT, "kristals": ordered}
    digest = "sha256:" + hashlib.sha256(json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {**projection, "count": len(ordered), "index_digest": digest, "note": "Derived navigation index for GitHub/AI discovery; not semantic authority."}


def _remote_index_matches(index: dict[str, Any] | None, prepared: dict[str, Any]) -> bool:
    if not isinstance(index, dict) or index.get("format") != GITHUB_COLLECTION_INDEX_FORMAT:
        return False
    expected = _collection_index_entry(prepared)
    for item in index.get("kristals") or []:
        if not isinstance(item, dict):
            continue
        if item.get("path") == expected["path"]:
            return item.get("state_ref") == expected.get("state_ref") and item.get("surface_digest") == expected.get("surface_digest") and item.get("entrypoint") == expected.get("entrypoint")
    return False


def ensure_collection_checkout(
    *, workspace_root: Path, network_config: Path, target: str,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Return an up-to-date, clean checkout of the configured public/private collection."""
    require_tool("git")
    require_tool("gh")
    collection = resolve_publication_collection(network_config, target)
    checkout = (workspace_root / collection["name"]).resolve()
    branch = _default_branch(network_config)
    if not checkout.exists():
        _progress(progress, f"{collection['repository']}: clone collection")
        _run(["gh", "repo", "clone", collection["repository"], str(checkout)])
    if not (checkout / ".git").exists():
        raise ManagerError(f"Collection checkout exists but is not a Git repository: {checkout}")
    origin = (_run(["git", "-C", str(checkout), "remote", "get-url", "origin"]).stdout or "").strip()
    if origin and not _repo_remote_matches(origin, collection["repository"]):
        raise ManagerError(f"Collection checkout origin is {origin!r}, expected {collection['repository']!r}")
    _progress(progress, f"{collection['repository']}: fetch/fast-forward")
    _run(["git", "-C", str(checkout), "fetch", "origin"])
    checkout_branch = _run(["git", "-C", str(checkout), "checkout", branch], check=False)
    if checkout_branch.returncode:
        _run(["git", "-C", str(checkout), "checkout", "-B", branch, f"origin/{branch}"])
    _run(["git", "-C", str(checkout), "pull", "--ff-only", "origin", branch])
    dirty = (_run(["git", "-C", str(checkout), "status", "--porcelain"]).stdout or "").strip()
    if dirty:
        raise ManagerError(
            f"Collection checkout contains uncommitted changes and Sync will not mix them:\n{checkout}\n{dirty}"
        )
    for rel in (".kristal/node.json", ".kristal/bindings/github.json"):
        if not (checkout / rel).is_file():
            raise ManagerError(f"Collection is not a bootstrapped Kristal v10 node; missing {rel}: {checkout}")
    return {**collection, "checkout": str(checkout), "branch": branch}


def _preflight_hosted_surface(checkout: Path, prepared: dict[str, Any]) -> None:
    surface = prepared["surface"]
    root_rel = _safe_surface_root(str(surface["target_root"]))
    root = (checkout / Path(root_rel.as_posix())).resolve()
    try:
        root.relative_to(checkout.resolve())
    except ValueError as exc:
        raise ManagerError("Refusing read-surface path outside collection checkout") from exc
    manifest_path = root / Path(SYNC_MANIFEST_REL.as_posix())
    existing_manifest = safe_json(manifest_path) if manifest_path.is_file() else None
    if existing_manifest and existing_manifest.get("state_ref") and existing_manifest.get("state_ref") != surface.get("state_ref"):
        raise ManagerError(
            f"Sync slug collision: {root_rel.as_posix()} already belongs to state_ref {existing_manifest.get('state_ref')}, not {surface.get('state_ref')}"
        )
    if not existing_manifest:
        legacy_state = root / "state" / "state-snapshot.json"
        existing = safe_json(legacy_state) if legacy_state.is_file() else None
        if existing and existing.get("state_ref") and existing.get("state_ref") != surface.get("state_ref"):
            raise ManagerError(
                f"Sync slug collision: {root_rel.as_posix()} already contains state_ref {existing.get('state_ref')}, not {surface.get('state_ref')}"
            )


def _apply_prepared_surface(checkout: Path, prepared: dict[str, Any], *, progress: ProgressCallback | None = None) -> dict[str, Any]:
    surface = prepared["surface"]
    entry = prepared["entry"]
    title = str(entry.get("title") or surface.get("slug") or "Kristal")
    _preflight_hosted_surface(checkout, prepared)
    root_rel = _safe_surface_root(str(surface["target_root"]))
    root = (checkout / Path(root_rel.as_posix())).resolve()
    try:
        root.relative_to(checkout.resolve())
    except ValueError as exc:
        raise ManagerError("Refusing read-surface path outside collection checkout") from exc

    manifest_path = root / Path(SYNC_MANIFEST_REL.as_posix())
    existing_manifest = safe_json(manifest_path) if manifest_path.is_file() else None
    if existing_manifest and existing_manifest.get("state_ref") and existing_manifest.get("state_ref") != surface.get("state_ref"):
        raise ManagerError(
            f"Sync slug collision: {root_rel.as_posix()} already belongs to state_ref {existing_manifest.get('state_ref')}, not {surface.get('state_ref')}"
        )
    if not existing_manifest:
        legacy_state = root / "state" / "state-snapshot.json"
        existing = safe_json(legacy_state) if legacy_state.is_file() else None
        if existing and existing.get("state_ref") and existing.get("state_ref") != surface.get("state_ref"):
            raise ManagerError(
                f"Sync slug collision: {root_rel.as_posix()} already contains state_ref {existing.get('state_ref')}, not {surface.get('state_ref')}"
            )

    if existing_manifest and existing_manifest.get("surface_digest") == surface.get("surface_digest"):
        return {"changed": False, "target_root": root_rel.as_posix(), "changed_paths": [], "manifest_path": f"{root_rel.as_posix()}/{SYNC_MANIFEST_REL.as_posix()}"}

    old_paths: set[str] = set()
    if existing_manifest and existing_manifest.get("format") == GITHUB_SYNC_MANIFEST_FORMAT:
        for item in existing_manifest.get("files") or []:
            if isinstance(item, dict) and item.get("path"):
                try:
                    old_paths.add(_safe_relative_posix(str(item["path"]), label="previous read-surface file path").as_posix())
                except ManagerError:
                    continue
    new_paths = {str(item["path"]) for item in surface.get("files") or []}
    changed_paths: list[str] = []

    # Delete only files that a previous Manager manifest explicitly owned.
    for rel_text in sorted(old_paths - new_paths, key=lambda x: x.encode("utf-8")):
        dest = (root / Path(rel_text)).resolve()
        try:
            dest.relative_to(root)
        except ValueError:
            continue
        if dest.is_file():
            dest.unlink()
            changed_paths.append(f"{root_rel.as_posix()}/{rel_text}")

    local_path = Path(prepared["local_path"])
    for item in surface.get("files") or []:
        rel_text = str(item["path"])
        src = local_path / Path(rel_text)
        dest = root / Path(rel_text)
        expected = str(item.get("sha256") or "")
        same = dest.is_file() and _sha256_file(dest) == expected
        if same:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        if _sha256_file(dest) != expected:
            raise ManagerError(f"Copied read-surface digest mismatch: {rel_text}")
        changed_paths.append(f"{root_rel.as_posix()}/{rel_text}")

    manifest = _sync_manifest(prepared)
    manifest_bytes = _json_bytes(manifest)
    current_manifest_bytes = manifest_path.read_bytes() if manifest_path.is_file() else None
    if current_manifest_bytes != manifest_bytes:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_bytes(manifest_bytes)
        changed_paths.append(f"{root_rel.as_posix()}/{SYNC_MANIFEST_REL.as_posix()}")

    _progress(progress, f"{title}: staged read surface candidate ({surface.get('file_count')} files, {surface.get('total_bytes')} bytes)")
    return {"changed": bool(changed_paths), "target_root": root_rel.as_posix(), "changed_paths": changed_paths, "manifest_path": f"{root_rel.as_posix()}/{SYNC_MANIFEST_REL.as_posix()}"}


def _verify_host_node(checkout: Path, sync_cli: Path | None, *, progress: ProgressCallback | None = None) -> None:
    if not sync_cli:
        return
    require_tool("node")
    _progress(progress, f"{checkout.name}: verify v10 node/binding")
    for cmd, file in (("verify-node-v10", checkout / ".kristal/node.json"), ("verify-github-binding-v10", checkout / ".kristal/bindings/github.json")):
        proc = _run(["node", str(sync_cli), cmd, str(file)], check=False)
        if proc.returncode:
            raise ManagerError(f"Sync verification failed ({cmd}): {(proc.stderr or proc.stdout or '').strip()}")


def _sync_prepared_collection(
    target: str, prepared_items: list[dict[str, Any]], *, workspace_root: Path,
    network_config: Path, sync_cli: Path | None, framework_sha: str | None,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    if not prepared_items:
        return []
    if target == "public":
        collection_identity = resolve_publication_collection(network_config, target)["repository"]
        for prepared in prepared_items:
            surface = prepared["surface"]
            if _sensitive_surface_paths(surface):
                raise ManagerError("Public Sync denied: sensitive read-surface paths")
            try:
                prepared["_c2_gate"] = verify_public_write(
                    operation="sync", slug=str(surface.get("slug") or ""),
                    state_ref=str(surface.get("state_ref") or ""), repository=collection_identity,
                    state_commitment=str((surface.get("state_logical_commitment") or {}).get("digest") or ""),
                    local_root=Path(prepared["local_path"]),
                    paths=[str(x["path"]) for x in surface.get("files") or []],
                )
            except PublicGateError as exc:
                raise ManagerError(f"Public Sync blocked before checkout: {exc}") from exc
    collection = ensure_collection_checkout(
        workspace_root=workspace_root, network_config=network_config, target=target, progress=progress
    )
    checkout = Path(collection["checkout"])
    branch = collection["branch"]
    _verify_host_node(checkout, sync_cli, progress=progress)

    # Fail before writing if this batch itself contains ambiguous identities/paths.
    roots: dict[str, str] = {}
    refs: dict[str, str] = {}
    for prepared in prepared_items:
        surface = prepared["surface"]
        root = str(surface.get("target_root") or "")
        ref = str(surface.get("state_ref") or "")
        local = str(prepared.get("local_path") or "")
        if root in roots and roots[root] != local:
            raise ManagerError(f"Batch read-surface collision: multiple Local Kristals target {root}")
        if ref and ref in refs and refs[ref] != root:
            raise ManagerError(f"Batch identity collision: state_ref {ref} targets both {refs[ref]} and {root}")
        roots[root] = local
        if ref:
            refs[ref] = root

    index_path = checkout / Path(COLLECTION_INDEX_REL.as_posix())
    existing_index = safe_json(index_path) if index_path.is_file() else None
    # Build the next index and preflight every hosted target before touching disk.
    # A collision therefore cannot leave half of a large batch applied locally.
    new_index = _build_collection_index(existing_index, prepared_items)
    for prepared in prepared_items:
        _preflight_hosted_surface(checkout, prepared)

    allowed_roots = sorted({str(p["surface"]["target_root"]) for p in prepared_items})
    pathspecs = allowed_roots + [COLLECTION_INDEX_REL.as_posix()]
    apply_rows: list[tuple[dict[str, Any], dict[str, Any]]] = []
    index_changed = False
    changed = False
    try:
        for idx, prepared in enumerate(prepared_items, 1):
            title = str(prepared["entry"].get("title") or prepared["surface"].get("slug"))
            _progress(progress, f"[{target} {idx}/{len(prepared_items)}] {title}: apply read surface")
            apply_rows.append((prepared, _apply_prepared_surface(checkout, prepared, progress=progress)))

        index_changed = (index_path.read_bytes() if index_path.is_file() else None) != _json_bytes(new_index)
        if index_changed:
            index_path.parent.mkdir(parents=True, exist_ok=True)
            index_path.write_bytes(_json_bytes(new_index))
            _progress(progress, f"{collection['repository']}: update {COLLECTION_INDEX_REL.as_posix()} ({new_index['count']} Kristal(s))")

        any_surface_changed = any(row[1]["changed"] for row in apply_rows)
        changed = any_surface_changed or index_changed
        if changed:
            _run(["git", "-C", str(checkout), "add", "-A", "--", *pathspecs])
            staged = (_run(["git", "-C", str(checkout), "diff", "--cached", "--name-only"]).stdout or "").splitlines()
            unexpected = [
                path for path in staged
                if path != COLLECTION_INDEX_REL.as_posix() and not any(path == root or path.startswith(root + "/") for root in allowed_roots)
            ]
            if unexpected:
                raise ManagerError(f"Batch Sync safety check failed: unexpected staged paths: {unexpected}")
    except Exception:
        # Checkout was clean on entry. Restore it so a failed large batch does not
        # poison the next Sync with partial local mutations.
        _run(["git", "-C", str(checkout), "reset", "--hard", "HEAD"], check=False)
        _run(["git", "-C", str(checkout), "clean", "-fd", "--", *pathspecs], check=False)
        raise

    if changed:
        if target == "public":
            for prepared in prepared_items:
                surface = prepared["surface"]
                try:
                    verify_public_write(
                        operation="sync", slug=str(surface.get("slug") or ""),
                        state_ref=str(surface.get("state_ref") or ""), repository=collection["repository"],
                        state_commitment=str((surface.get("state_logical_commitment") or {}).get("digest") or ""),
                        local_root=Path(prepared["local_path"]),
                        paths=[str(x["path"]) for x in surface.get("files") or []],
                    )
                except PublicGateError as exc:
                    _run(["git", "-C", str(checkout), "reset", "--hard", "HEAD"], check=False)
                    _run(["git", "-C", str(checkout), "clean", "-fd", "--", *pathspecs], check=False)
                    raise ManagerError(f"Public Sync blocked at final pre-push gate: {exc}") from exc
        owner = collection["owner"]
        changed_count = sum(1 for _prepared, row in apply_rows if row["changed"])
        msg = f"Sync {changed_count} Kristal read surface(s)"
        _progress(progress, f"{collection['repository']}: one commit for {changed_count} changed Kristal(s)")
        _run([
            "git", "-C", str(checkout), "-c", "user.name=Kristal Manager",
            "-c", f"user.email={owner}@users.noreply.github.com", "commit", "-m", msg,
        ])
        _progress(progress, f"{collection['repository']}: one push -> {branch}")
        _run(["git", "-C", str(checkout), "push", "origin", f"HEAD:{branch}"])

    head = (_run(["git", "-C", str(checkout), "rev-parse", "HEAD"]).stdout or "").strip()
    results: list[dict[str, Any]] = []
    for prepared, apply in apply_rows:
        surface = prepared["surface"]
        state_rel = str(prepared["state_path_in_surface"])
        target_root = str(surface["target_root"])
        results.append({
            "result": "SYNC PASS" if apply["changed"] else "ALREADY SYNCED",
            "changed": bool(apply["changed"]),
            "local_path": prepared["local_path"],
            "repository": collection["repository"],
            "visibility": target,
            "branch": branch,
            "surface_root": target_root,
            "surface_manifest_path": apply["manifest_path"],
            "surface_digest": surface.get("surface_digest"),
            "entrypoint": f"{target_root}/{surface.get('entrypoint') or 'AI_START_HERE.md'}",
            "file_count": surface.get("file_count"),
            "total_bytes": surface.get("total_bytes"),
            "materialization_object_count": surface.get("materialization_object_count", 0),
            "state_path": f"{target_root}/{state_rel}",
            "state_ref": surface.get("state_ref"),
            "logical_commitment": ((surface.get("state_logical_commitment") or {}).get("digest") if isinstance(surface.get("state_logical_commitment"), dict) else None),
            "state_blob_digest": next((x.get("sha256") for x in surface.get("files") or [] if x.get("path") == state_rel), None),
            "commit": head,
            "framework_sha": framework_sha,
            "policy": {
                "sync_is_not_publication": True,
                "activation_is_separate": True,
                "read_surface_is_derived": True,
                "collection_index_is_derived": True,
            },
        })
    return results


def sync_local_to_github(
    entry: dict[str, Any], *, workspace_root: Path, network_config: Path,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Validate and sync one Local Kristal's exact AI/GitHub read surface.

    alpha.11 deliberately consumes Local Kit's ``read-surface`` contract instead of
    mirroring a whole workspace or reducing Sync to the v9 State Snapshot alone.
    """
    target = str(entry.get("publication_target") or "none").lower()
    title = str(entry.get("title") or entry.get("slug") or "Kristal")
    _progress(progress, f"{title}: sync start")
    if target not in {"public", "private"}:
        raise ManagerError("Configure GitHub target public/private first")
    local_path = Path(str(entry.get("path") or "")).resolve()

    validation = validate_local_cached(
        local_path, previous=entry, workspace_root=workspace_root, network_config=network_config, progress=progress
    )
    if validation.get("result") != "VALID":
        raise ManagerError(f"Sync blocked: Local Kristal validation result is {validation.get('result')}")

    sync_cli, framework_sha = find_framework_cli(workspace_root, network_config)
    if sync_cli and not framework_supports_v10(sync_cli):
        raise ManagerError(
            f"Sync blocked: Framework at {sync_cli.parent.parent.parent.parent} does not expose Kristal v10 hosting commands. "
            "Update that checkout to the v10 Framework before Sync."
        )

    prepared = prepare_github_read_surface(entry, workspace_root=workspace_root, refresh_ai=True, progress=progress)
    prepared["validation"] = validation
    surface = prepared["surface"]
    if target == "public":
        sensitive = _sensitive_surface_paths(surface)
        if sensitive:
            raise ManagerError("Public Sync blocked: read surface contains sensitive-looking path(s): " + ", ".join(sensitive[:20]))

    collection_meta = resolve_publication_collection(network_config, target)
    if target == "public":
        try:
            verify_public_write(
                operation="sync", slug=str(surface.get("slug") or ""),
                state_ref=str(surface.get("state_ref") or ""), repository=collection_meta["repository"],
                state_commitment=str((surface.get("state_logical_commitment") or {}).get("digest") or ""),
                local_root=local_path,
                paths=[str(x["path"]) for x in surface.get("files") or []],
            )
        except PublicGateError as exc:
            raise ManagerError(f"Public Sync blocked: {exc}") from exc
    branch = _default_branch(network_config)
    manifest_path = f"{surface['target_root']}/{SYNC_MANIFEST_REL.as_posix()}"
    _progress(progress, f"{title}: compare hosted read-surface digest")
    try:
        remote_manifest = github_remote_json_file(collection_meta["repository"], branch, manifest_path)
        remote_index = github_remote_json_file(collection_meta["repository"], branch, COLLECTION_INDEX_REL.as_posix())
    except ManagerError:
        remote_manifest = None
        remote_index = None
    if (
        isinstance(remote_manifest, dict)
        and remote_manifest.get("format") == GITHUB_SYNC_MANIFEST_FORMAT
        and remote_manifest.get("state_ref") == surface.get("state_ref")
        and remote_manifest.get("surface_digest") == surface.get("surface_digest")
        and _remote_index_matches(remote_index, prepared)
    ):
        state_rel = str(prepared["state_path_in_surface"])
        _progress(progress, f"{title}: already synced (read surface + collection index)")
        return {
            "result": "ALREADY SYNCED",
            "changed": False,
            "validation_cached": bool(validation.get("cached")),
            "validation_cache_key": validation.get("validation_cache_key"),
            "local_path": str(local_path),
            "repository": collection_meta["repository"],
            "visibility": target,
            "branch": branch,
            "surface_root": surface.get("target_root"),
            "surface_manifest_path": manifest_path,
            "surface_digest": surface.get("surface_digest"),
            "entrypoint": f"{surface.get('target_root')}/{surface.get('entrypoint') or 'AI_START_HERE.md'}",
            "file_count": surface.get("file_count"),
            "total_bytes": surface.get("total_bytes"),
            "materialization_object_count": surface.get("materialization_object_count", 0),
            "state_path": f"{surface.get('target_root')}/{state_rel}",
            "state_ref": surface.get("state_ref"),
            "logical_commitment": ((surface.get("state_logical_commitment") or {}).get("digest") if isinstance(surface.get("state_logical_commitment"), dict) else None),
            "state_blob_digest": next((x.get("sha256") for x in surface.get("files") or [] if x.get("path") == state_rel), None),
            "commit": entry.get("last_sync_commit"),
            "framework_sha": framework_sha,
            "policy": {"sync_is_not_publication": True, "activation_is_separate": True, "read_surface_is_derived": True, "collection_index_is_derived": True},
        }

    results = _sync_prepared_collection(
        target, [prepared], workspace_root=workspace_root, network_config=network_config,
        sync_cli=sync_cli, framework_sha=framework_sha, progress=progress,
    )
    result = results[0]
    result["validation_cached"] = bool(validation.get("cached"))
    result["validation_cache_key"] = validation.get("validation_cache_key")
    _progress(progress, f"{title}: sync complete")
    return result



def validate_entries_parallel(
    entries: list[dict[str, Any]], *, workspace_root: Path, network_config: Path | None = None,
    max_workers: int | None = None, progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """Validate Local Kristals concurrently; results are isolated per entry."""
    eligible = [e for e in entries if e.get("kind") == "local" and not e.get("hidden_auxiliary")]
    if not eligible:
        return []
    cpu = os.cpu_count() or 2
    workers = max(1, min(max_workers or min(4, cpu), len(eligible)))
    _progress(progress, f"Batch validation: {len(eligible)} Kristal(s), {workers} parallel worker(s)")

    def one(e: dict[str, Any]) -> dict[str, Any]:
        title = str(e.get("title") or Path(str(e.get("path") or "")).name)
        try:
            result = validate_local_cached(
                Path(str(e["path"])), previous=e, workspace_root=workspace_root,
                network_config=network_config, progress=progress,
            )
            return {"path": e["path"], "title": title, "ok": True, "validation": result}
        except Exception as exc:
            return {"path": e.get("path"), "title": title, "ok": False, "error": str(exc)}

    out: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="kristal-validate") as pool:
        futures = {pool.submit(one, e): e for e in eligible}
        done_count = 0
        for fut in as_completed(futures):
            item = fut.result()
            out.append(item)
            done_count += 1
            status = (item.get("validation") or {}).get("result") if item.get("ok") else "ERROR"
            _progress(progress, f"Batch validation [{done_count}/{len(eligible)}]: {item['title']} -> {status}")
    order = {str(e.get("path")): i for i, e in enumerate(eligible)}
    out.sort(key=lambda x: order.get(str(x.get("path")), 10**9))
    return out


def sync_entries_batch(
    entries: list[dict[str, Any]], *, workspace_root: Path, network_config: Path,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """High-throughput Sync for thousands of Local Kristals.

    Phase 1 validates Local Kristals in parallel. Phase 2 asks Local Kit 3.2.4+
    to refresh/build each AI read layer and emit the exact read-surface contract,
    also in parallel. Phase 3 performs at most one fetch/commit/push per target
    collection. Public and private collections may run concurrently.
    """
    eligible = [
        e for e in entries
        if e.get("kind") == "local" and not e.get("hidden_auxiliary")
        and str(e.get("publication_target") or "none").lower() in {"public", "private"}
    ]
    if not eligible:
        return []

    _progress(progress, f"Batch sync phase 1/3: parallel validation of {len(eligible)} Kristal(s)")
    validation_rows = validate_entries_parallel(
        eligible, workspace_root=workspace_root, network_config=network_config, progress=progress
    )
    validation_by_path = {str(row.get("path")): row for row in validation_rows}
    out: list[dict[str, Any]] = []
    validated: list[dict[str, Any]] = []
    for e in eligible:
        row = validation_by_path.get(str(e.get("path")))
        if not row or not row.get("ok"):
            out.append({
                "path": e.get("path"), "title": e.get("title"), "target": e.get("publication_target"),
                "ok": False, "error": (row or {}).get("error") or "Validation failed",
            })
            continue
        validation = row.get("validation") or {}
        if validation.get("result") != "VALID":
            out.append({
                "path": e.get("path"), "title": e.get("title"), "target": e.get("publication_target"),
                "ok": False, "error": f"Sync blocked: validation result is {validation.get('result')}",
                "validation": validation,
            })
            continue
        prepared_entry = dict(e)
        prepared_entry["last_validation_result"] = "VALID"
        prepared_entry["last_validation_cache_key"] = validation.get("validation_cache_key")
        prepared_entry["_batch_validation"] = validation
        validated.append(prepared_entry)

    if not validated:
        order = {str(e.get("path")): i for i, e in enumerate(eligible)}
        return sorted(out, key=lambda x: order.get(str(x.get("path")), 10**9))

    # Check hosting capability before doing potentially expensive AI/read-surface rebuilds.
    sync_cli, framework_sha = find_framework_cli(workspace_root, network_config)
    if sync_cli and not framework_supports_v10(sync_cli):
        reason = (
            f"Sync blocked: Framework at {sync_cli.parent.parent.parent.parent} does not expose Kristal v10 hosting commands. "
            "Update that checkout to the v10 Framework before Sync."
        )
        for e in validated:
            out.append({"path": e.get("path"), "title": e.get("title"), "target": e.get("publication_target"), "ok": False, "error": reason})
        order = {str(e.get("path")): i for i, e in enumerate(eligible)}
        return sorted(out, key=lambda x: order.get(str(x.get("path")), 10**9))

    cpu = os.cpu_count() or 2
    workers = max(1, min(4, cpu, len(validated)))
    _progress(progress, f"Batch sync phase 2/3: prepare {len(validated)} read surface(s), {workers} parallel worker(s)")

    def prepare_one(e: dict[str, Any]) -> dict[str, Any]:
        title = str(e.get("title") or Path(str(e.get("path") or "")).name)
        try:
            prepared = prepare_github_read_surface(e, workspace_root=workspace_root, refresh_ai=True, progress=progress)
            prepared["validation"] = e.get("_batch_validation") or {}
            target = str(e.get("publication_target")).lower()
            if target == "public":
                sensitive = _sensitive_surface_paths(prepared["surface"])
                if sensitive:
                    raise ManagerError("Public Sync blocked: read surface contains sensitive-looking path(s): " + ", ".join(sensitive[:20]))
            return {"path": e.get("path"), "title": title, "target": target, "ok": True, "prepared": prepared}
        except Exception as exc:
            return {"path": e.get("path"), "title": title, "target": e.get("publication_target"), "ok": False, "error": str(exc)}

    prepared_rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="kristal-read-surface") as pool:
        futures = {pool.submit(prepare_one, e): e for e in validated}
        done_count = 0
        for fut in as_completed(futures):
            row = fut.result()
            prepared_rows.append(row)
            done_count += 1
            status = "READY" if row.get("ok") else "ERROR"
            _progress(progress, f"Batch read surface [{done_count}/{len(validated)}]: {row['title']} -> {status}")

    groups: dict[str, list[dict[str, Any]]] = {"public": [], "private": []}
    for row in prepared_rows:
        if not row.get("ok"):
            out.append({k: row.get(k) for k in ("path", "title", "target", "ok", "error")})
            continue
        groups[str(row["target"])].append(row["prepared"])

    active = [(target, group) for target, group in groups.items() if group]
    if not active:
        order = {str(e.get("path")): i for i, e in enumerate(eligible)}
        return sorted(out, key=lambda x: order.get(str(x.get("path")), 10**9))

    _progress(
        progress,
        f"Batch sync phase 3/3: {sum(len(g) for _, g in active)} read surface(s), "
        f"{len(active)} collection transaction(s); max one commit/push per collection.",
    )

    def sync_group(target: str, group: list[dict[str, Any]]) -> list[dict[str, Any]]:
        try:
            synced = _sync_prepared_collection(
                target, group, workspace_root=workspace_root, network_config=network_config,
                sync_cli=sync_cli, framework_sha=framework_sha, progress=progress,
            )
            rows: list[dict[str, Any]] = []
            by_local = {str(x.get("local_path")): x for x in synced}
            for prepared in group:
                entry = prepared["entry"]
                result = by_local[str(prepared["local_path"])]
                result["validation_cached"] = bool((prepared.get("validation") or {}).get("cached"))
                result["validation_cache_key"] = (prepared.get("validation") or {}).get("validation_cache_key")
                rows.append({"path": entry.get("path"), "title": entry.get("title"), "target": target, "ok": True, "sync": result})
            return rows
        except Exception as exc:
            _progress(progress, f"[{target}] collection transaction ERROR: {exc}")
            return [
                {"path": p["entry"].get("path"), "title": p["entry"].get("title"), "target": target, "ok": False, "error": str(exc)}
                for p in group
            ]

    with ThreadPoolExecutor(max_workers=min(2, len(active)), thread_name_prefix="kristal-collection-sync") as pool:
        futures = [pool.submit(sync_group, target, group) for target, group in active]
        for fut in as_completed(futures):
            out.extend(fut.result())

    order = {str(e.get("path")): i for i, e in enumerate(eligible)}
    out.sort(key=lambda x: order.get(str(x.get("path")), 10**9))
    return out


def prepare_publication_request(entry: dict[str, Any], *, workspace_root: Path, network_config: Path, output: Path | None = None) -> dict[str, Any]:
    target = str(entry.get("publication_target") or "none").lower()
    if target == "none":
        raise ManagerError("Configure a publication target (public/private) first")
    path = Path(str(entry.get("path") or "")).resolve()
    rec = detect_kristal(path)
    if not rec:
        raise ManagerError(f"Local Kristal is no longer available: {path}")
    if rec.get("kind") != "local" or not rec.get("workspace"):
        raise ManagerError("Publication handoff requires a Local Kristal workspace, not a legacy/auxiliary package")
    if rec.get("needs_migration"):
        raise ManagerError(f"Local Kristal must be migrated to {CURRENT_LOCAL_FORMAT} before publication handoff")
    if rec.get("state_conflict"):
        detail = "\n".join(str(x) for x in rec.get("state_conflict_reasons", []))
        raise ManagerError("Publication handoff blocked: current state surfaces disagree." + (f"\n{detail}" if detail else ""))
    current = current_state_candidates(rec.get("state_candidates", []))
    if not current:
        raise ManagerError("No current Local Kit v9 State Snapshot was found. Run Local Kit build-v9 first; legacy .kristal/v9 history is not publishable as the current state.")
    selected_current = current[0]
    if not selected_current.get("state_ref") or not selected_current.get("state_commitment"):
        raise ManagerError("Current Local Kit v9 State Snapshot is missing state_ref or logical commitment.")
    collection = resolve_publication_collection(network_config, target)
    slug = sanitize_repo_name(str(entry.get("slug") or rec.get("slug") or path.name)).lower()
    collection_state_path = f"kristals/{slug}/state/state-snapshot.json"
    channel_suffix = f"{slug}/stable"
    inspection_meta: dict[str, Any] | None = None
    tool = find_local_tool(workspace_root)
    if tool:
        inspection = inspect_with_local_tool(path, tool)
        if inspection:
            interop = inspection.get("interop") if isinstance(inspection.get("interop"), dict) else {}
            suggested_path = str(interop.get("suggested_collection_state_path") or "").replace("\\", "/")
            suggested_channel = str(interop.get("suggested_channel_suffix") or "").strip("/")
            pp = PurePosixPath(suggested_path) if suggested_path else None
            if pp and not pp.is_absolute() and ".." not in pp.parts:
                collection_state_path = pp.as_posix()
            if suggested_channel and ".." not in PurePosixPath(suggested_channel).parts:
                channel_suffix = suggested_channel
            inspection_meta = {"format": inspection.get("format"), "kit_version": inspection.get("kit_version")}
    request = {
        "format": PUBLISH_REQUEST_FORMAT,
        "created_at": utc_now(),
        "local": {
            "path": str(path),
            "title": entry.get("title") or rec.get("title"),
            "slug": slug,
            "workspace_format": rec.get("workspace_format"),
        },
        "state": {
            "path": selected_current.get("path"),
            "source": selected_current.get("source"),
            "state_ref": selected_current.get("state_ref"),
            "logical_commitment": selected_current.get("state_commitment"),
        },
        "target": {
            "visibility": target,
            "collection_repository": collection["repository"],
            "collection_local_path": str((workspace_root / collection["name"]).resolve()),
            "collection_state_path": collection_state_path,
            "channel": f"{target}/{channel_suffix}",
        },
        "policy": {
            "sync_is_not_publication": True,
            "backup_is_not_publication": True,
            "publication_requires_exact_state": True,
            "activation_is_separate": True,
        },
        "interop": inspection_meta,
        "consumer": {
            "product": "Kristal GitHub Bootstrap / Setup",
            "minimum_expected": "1.1.0-alpha.9",
        },
    }
    output = output or (workspace_root / "kristal-publish-request.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(request, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"request_path": str(output.resolve()), **request}


def _find_app(workspace_root: Path, names: tuple[str, ...]) -> Path | None:
    # Prefer shallow current-version packages; tolerate repeated ZIP top-level folders.
    candidates: list[Path] = []
    for name in names:
        direct = workspace_root / name
        if direct.is_file():
            candidates.append(direct)
    for pattern in ("Kristal-GitHub-Bootstrap*", "Kompiler*"):
        for package in workspace_root.glob(pattern):
            for name in names:
                for candidate in (package / name,):
                    if candidate.is_file():
                        candidates.append(candidate)
                for candidate in package.glob("*/" + names[0]):
                    if candidate.is_file():
                        candidates.append(candidate)
    if not candidates:
        return None
    candidates.sort(key=lambda p: (_version_key(str(p.parent)), -len(p.parts)), reverse=True)
    return candidates[0]


def find_github_setup(workspace_root: Path) -> Path | None:
    return _find_app(workspace_root, ("Kristal-GitHub-Setup.pyw",))


def find_kompiler(workspace_root: Path) -> Path | None:
    return _find_app(workspace_root, ("Kompiler.pyw", "SmartSnap.pyw"))


def render_html_registry(config: dict[str, Any]) -> str:
    visible = [e for e in config.get("entries", []) if not e.get("hidden_auxiliary")]
    hidden = [e for e in config.get("entries", []) if e.get("hidden_auxiliary")]
    rows = []
    for e in visible:
        state = e.get("state_commitment") or ""
        if state and len(state) > 28:
            state = state[:25] + "…"
        target = str(e.get("publication_target") or "none")
        blob = e.get("state_blob_digest")
        if target == "none":
            sync = "—"
        elif e.get("last_sync_surface_digest") and blob and e.get("last_sync_blob_digest") == blob and e.get("last_sync_repository"):
            sync = "SYNCED"
        elif blob and e.get("last_sync_blob_digest") == blob and e.get("last_sync_repository"):
            sync = "READ SURFACE"
        else:
            sync = "PENDING"
        rows.append("<tr>" + "".join([
            f"<td>{html.escape(str(e.get('title','')))}</td>",
            f"<td><strong>{html.escape(str(e.get('readiness') or ''))}</strong></td>",
            f"<td>{html.escape(str(e.get('workspace_format') or e.get('kind') or ''))}</td>",
            f"<td>{html.escape(str(e.get('path','')))}</td>",
            f"<td>{html.escape(sync)}</td>",
            f"<td>{html.escape(target)}</td>",
            f"<td>{html.escape(str(e.get('last_sync_repository') or ''))}</td>",
            f"<td>{html.escape(str(e.get('last_validation_result') or ''))}</td>",
            f"<td>{html.escape(str(e.get('state_source') or ''))}</td>",
            f"<td><code>{html.escape(state)}</code></td>",
        ]) + "</tr>")
    hidden_rows = []
    for e in hidden:
        hidden_rows.append("<tr>" + "".join([
            f"<td>{html.escape(str(e.get('title','')))}</td>",
            f"<td>{html.escape(str(e.get('nested_under') or ''))}</td>",
            f"<td>{html.escape(str(e.get('path','')))}</td>",
        ]) + "</tr>")
    hidden_section = ""
    if hidden_rows:
        hidden_section = (
            "<h2>Nested auxiliary legacy folders</h2>"
            "<p>Hidden from the default Manager inventory because they are inside a recognized Local Kristal.</p>"
            "<table><thead><tr><th>Name</th><th>Parent Kristal</th><th>Path</th></tr></thead><tbody>"
            + "\n".join(hidden_rows)
            + "</tbody></table>"
        )
    return (
        "<!doctype html><meta charset='utf-8'><title>Kristal Local Registry</title>"
        "<style>body{font-family:Segoe UI,Arial,sans-serif;margin:2rem}table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #bbb;padding:.45rem;text-align:left}th{background:#eee}code{font-family:Consolas,monospace}</style>"
        "<h1>Kristal Local Registry</h1>"
        "<p>Inventory and mutable GitHub Sync metadata are operational only; they are not semantic identity.</p>"
        "<table><thead><tr><th>Kristal</th><th>Health</th><th>Workspace</th><th>Path</th>"
        "<th>GitHub Sync</th><th>GitHub target</th><th>Collection repo</th><th>Validation</th>"
        "<th>State surface</th><th>Commitment</th></tr></thead><tbody>"
        + "\n".join(rows)
        + "</tbody></table>"
        + hidden_section
    )
