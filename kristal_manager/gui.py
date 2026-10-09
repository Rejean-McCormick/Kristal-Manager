from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .core import (
    CURRENT_LOCAL_FORMAT,
    DEFAULT_LOCAL_DIRNAME,
    DEFAULT_WINDOWS_ROOT,
    ManagerError,
    backup_local,
    sync_local_to_github,
    detect_kristal,
    find_github_setup,
    find_kompiler,
    import_local,
    load_manager_config,
    load_network_config,
    merge_scan,
    migrate_local,
    prepare_publication_request,
    render_html_registry,
    sanitize_repo_name,
    save_manager_config,
    scan_roots,
    scan_roots_quick,
    utc_now,
    validate_local_cached,
    validate_entries_parallel,
    sync_entries_batch,
)


def _quiet_popen_kwargs() -> dict[str, Any]:
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


def _pythonw_executable() -> str:
    exe = Path(sys.executable)
    if os.name == "nt":
        candidate = exe.with_name("pythonw.exe")
        if candidate.exists():
            return str(candidate)
    return str(exe)


def main() -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter.scrolledtext import ScrolledText

    root = tk.Tk()
    root.title("Kristal Manager 0.1.0-alpha.11")
    root.geometry("1480x840")
    root.minsize(1120, 700)

    workspace_default = DEFAULT_WINDOWS_ROOT if os.name == "nt" else Path.cwd()
    workspace_root = tk.StringVar(value=str(workspace_default))
    config_path = tk.StringVar(value=str(workspace_default / "kristal-manager.json"))
    network_path = tk.StringVar(value=str(workspace_default / "network.toml"))
    locals_root = tk.StringVar(value=str(workspace_default / DEFAULT_LOCAL_DIRNAME))
    scan_roots_var = tk.StringVar(value=str(workspace_default / DEFAULT_LOCAL_DIRNAME))
    status_var = tk.StringVar(value="Ready")
    inventory_var = tk.StringVar(value="")
    show_nested_legacy = tk.BooleanVar(value=False)

    q: queue.Queue[tuple[str, Any]] = queue.Queue()
    running = {"value": False}
    state: dict[str, Any] = {}

    outer = ttk.Frame(root, padding=10)
    outer.pack(fill="both", expand=True)
    notebook = ttk.Notebook(outer)
    notebook.pack(fill="both", expand=True)
    local_tab = ttk.Frame(notebook, padding=10)
    settings_tab = ttk.Frame(notebook, padding=10)
    tools_tab = ttk.Frame(notebook, padding=10)
    notebook.add(local_tab, text="Local Kristals")
    notebook.add(settings_tab, text="Settings")
    notebook.add(tools_tab, text="Tools")

    cols = ("title", "format", "health", "validation", "state", "sync", "target", "path")
    tree = ttk.Treeview(local_tab, columns=cols, show="headings", selectmode="browse")
    headings = {
        "title": "Kristal", "format": "Workspace", "health": "Health", "validation": "Validation", "state": "State",
        "sync": "GitHub Sync", "target": "GitHub target", "path": "Path",
    }
    widths = {"title": 210, "format": 115, "health": 120, "validation": 95, "state": 100, "sync": 110, "target": 95, "path": 520}
    for c in cols:
        tree.heading(c, text=headings[c])
        tree.column(c, width=widths[c], stretch=c in {"title", "backup", "path"})
    tree.grid(row=1, column=0, columnspan=8, sticky="nsew", pady=(8, 8))
    yscroll = ttk.Scrollbar(local_tab, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=yscroll.set)
    yscroll.grid(row=1, column=8, sticky="ns", pady=(8, 8))
    local_tab.rowconfigure(1, weight=1)
    local_tab.columnconfigure(7, weight=1)

    top = ttk.Frame(local_tab)
    top.grid(row=0, column=0, columnspan=9, sticky="ew")
    ttk.Label(top, text="Local Kristals", font=("TkDefaultFont", 11, "bold")).pack(side="left")
    ttk.Label(top, text="Local → Validate → Sync to GitHub collection; Publish/Activate remain separate", foreground="#555").pack(side="left", padx=14)
    ttk.Label(top, textvariable=inventory_var, foreground="#555").pack(side="left", padx=10)
    ttk.Checkbutton(top, text="Show nested legacy", variable=show_nested_legacy, command=lambda: refresh()).pack(side="right", padx=(8, 0))
    ttk.Label(top, textvariable=status_var).pack(side="right", padx=(8, 0))

    btns = ttk.Frame(local_tab)
    btns.grid(row=2, column=0, columnspan=9, sticky="ew")
    btns2 = ttk.Frame(local_tab)
    btns2.grid(row=3, column=0, columnspan=9, sticky="ew", pady=(4, 0))

    log = ScrolledText(outer, height=12, wrap="word", font=("Consolas", 9))
    log.pack(fill="both", expand=False, pady=(8, 0))
    log.configure(state="disabled")

    def append(text: str) -> None:
        log.configure(state="normal")
        log.insert("end", text.rstrip() + "\n")
        log.see("end")
        log.configure(state="disabled")

    def post_progress(message: str) -> None:
        q.put(("progress", message))

    def run_task(
        label: str, fn: Callable[[], Any], done: Callable[[Any], None] | None = None,
        *, show_result: bool = True,
    ) -> None:
        if running["value"]:
            messagebox.showinfo("Kristal Manager", "An operation is already running.")
            return
        running["value"] = True
        append(f"\n== {label} ==")
        status_var.set(label + "...")

        def worker() -> None:
            try:
                q.put(("ok", (fn(), done, show_result)))
            except Exception as exc:
                try:
                    setattr(exc, "_trace", traceback.format_exc())
                except Exception:
                    pass
                q.put(("error", exc))

        threading.Thread(target=worker, daemon=True).start()

    def poll() -> None:
        try:
            while True:
                kind, payload = q.get_nowait()
                if kind == "progress":
                    stamp = datetime.now().strftime("%H:%M:%S")
                    append(f"[{stamp}] {payload}")
                    continue
                running["value"] = False
                if kind == "error":
                    append(f"ERROR: {payload}")
                    tb = getattr(payload, "_trace", None)
                    if tb:
                        append(tb)
                    status_var.set("ERROR")
                    messagebox.showerror("Kristal Manager", str(payload))
                else:
                    result, done, show_result = payload
                    if done:
                        done(result)
                    if show_result and result is not None:
                        append(json.dumps(result, indent=2, ensure_ascii=False) if not isinstance(result, str) else result)
                    status_var.set("Ready")
        except queue.Empty:
            pass
        root.after(150, poll)

    root.after(150, poll)

    def workspace() -> Path:
        return Path(workspace_root.get()).expanduser().resolve()

    def cfgfile() -> Path:
        return Path(config_path.get()).expanduser().resolve()

    def netfile() -> Path:
        return Path(network_path.get()).expanduser().resolve()

    def load_state() -> dict[str, Any]:
        nonlocal state
        state = load_manager_config(cfgfile(), workspace())
        state["workspace_root"] = str(workspace())
        if not state.get("scan_roots"):
            state["scan_roots"] = [str(Path(locals_root.get()).expanduser().resolve())]
        scan_roots_var.set(";".join(state.get("scan_roots", [])))
        return state

    def save_state() -> None:
        state["workspace_root"] = str(workspace())
        state["scan_roots"] = [x.strip() for x in scan_roots_var.get().split(";") if x.strip()]
        save_manager_config(cfgfile(), state)
        html_path = cfgfile().with_name("kristal-manager.html")
        html_path.write_text(render_html_registry(state), encoding="utf-8")

    def owner() -> str:
        cfg = load_network_config(netfile())
        own = str((cfg.get("account") or {}).get("owner") or "").strip()
        if not own:
            raise ManagerError(f"GitHub owner not found in {netfile()}")
        return own

    def selected_entry() -> dict[str, Any] | None:
        sel = tree.selection()
        if not sel:
            return None
        idx = int(sel[0])
        entries = state.get("entries", [])
        return entries[idx] if 0 <= idx < len(entries) else None

    def refresh() -> None:
        # Preserve the selected Local Kristal across refreshes. Validation and
        # sync both refresh the table; dropping selection made the next action
        # look like a dead button because selected_entry() returned None.
        selected_path = None
        sel = tree.selection()
        if sel:
            try:
                old_idx = int(sel[0])
                old_entries = state.get("entries", [])
                if 0 <= old_idx < len(old_entries):
                    selected_path = old_entries[old_idx].get("path")
            except (TypeError, ValueError):
                selected_path = None

        for item in tree.get_children():
            tree.delete(item)
        entries = state.get("entries", [])
        hidden_count = sum(1 for e in entries if e.get("hidden_auxiliary"))
        visible_entries = [(idx, e) for idx, e in enumerate(entries) if show_nested_legacy.get() or not e.get("hidden_auxiliary")]
        local_count = sum(1 for _idx, e in visible_entries if e.get("kind") == "local")
        migrate_count = sum(1 for _idx, e in visible_entries if e.get("readiness") == "MIGRATE")
        conflict_count = sum(1 for _idx, e in visible_entries if e.get("readiness") == "STATE CONFLICT")
        no_state_count = sum(1 for _idx, e in visible_entries if e.get("readiness") == "NO STATE")
        summary = f"{local_count} Local Kristal(s)"
        flags = []
        if migrate_count:
            flags.append(f"{migrate_count} migrate")
        if conflict_count:
            flags.append(f"{conflict_count} conflict")
        if no_state_count:
            flags.append(f"{no_state_count} no state")
        if hidden_count and not show_nested_legacy.get():
            flags.append(f"{hidden_count} nested legacy hidden")
        inventory_var.set(summary + ((" • " + " • ".join(flags)) if flags else ""))

        tree.tag_configure("ready", foreground="#146c2e")
        tree.tag_configure("warn", foreground="#9a6700")
        tree.tag_configure("error", foreground="#b42318")
        tree.tag_configure("muted", foreground="#777777")

        for idx, e in visible_entries:
            fmt = str(e.get("workspace_format") or e.get("kind") or "")
            if fmt.startswith("kristal.local-workspace/"):
                fmt = fmt.rsplit("/", 1)[-1]
            elif e.get("needs_migration"):
                fmt = "legacy → 3.2"
            state_text = str(e.get("state_source") or "—")
            health = str(e.get("readiness") or "OBSERVED")
            validation = e.get("last_validation_result") or "—"
            if health == "MIGRATE" and validation == "—":
                validation = "MIGRATE"
            target = e.get("publication_target", "none")
            current_blob = e.get("state_blob_digest")
            if target == "none":
                sync_text = "—"
            elif e.get("last_sync_surface_digest") and e.get("last_sync_blob_digest") == current_blob and current_blob and e.get("last_sync_repository"):
                sync_text = "SYNCED"
            elif e.get("last_sync_blob_digest") == current_blob and current_blob and e.get("last_sync_repository"):
                sync_text = "READ SURFACE"
            else:
                sync_text = "PENDING"
            tag = "ready" if health == "READY" else ("error" if health in {"STATE CONFLICT", "INVALID"} else ("warn" if health in {"MIGRATE", "NO STATE", "LEGACY STATE"} else "muted"))
            tree.insert("", "end", iid=str(idx), tags=(tag,), values=(
                e.get("title"), fmt, health, validation, state_text, sync_text, target, e.get("path"),
            ))
            if selected_path and e.get("path") == selected_path:
                tree.selection_set(str(idx))
                tree.focus(str(idx))
                tree.see(str(idx))

    def do_scan() -> None:
        roots = [Path(x.strip()) for x in scan_roots_var.get().split(";") if x.strip()]

        def task() -> Any:
            return scan_roots_quick(roots, state.get("entries", []))

        def done(scanned: Any) -> None:
            nonlocal state
            state = merge_scan(state, scanned)
            save_state()
            refresh()

        run_task("Quick Scan local Kristals", task, done, show_result=False)

    def do_deep_scan() -> None:
        roots = [Path(x.strip()) for x in scan_roots_var.get().split(";") if x.strip()]

        def task() -> Any:
            return scan_roots(roots)

        def done(scanned: Any) -> None:
            nonlocal state
            state = merge_scan(state, scanned)
            save_state()
            refresh()

        run_task("Deep Scan local Kristals", task, done, show_result=False)

    def add_root() -> None:
        p = filedialog.askdirectory(title="Add scan root")
        if not p:
            return
        roots = [x.strip() for x in scan_roots_var.get().split(";") if x.strip()]
        if p not in roots:
            roots.append(p)
        scan_roots_var.set(";".join(roots))
        do_scan()

    def add_folder() -> None:
        p = filedialog.askdirectory(title="Add one Local Kristal")
        if not p:
            return
        rec = detect_kristal(Path(p))
        if not rec:
            messagebox.showerror("Kristal Manager", "This folder is not recognized as a Kristal.")
            return
        nonlocal_state = merge_scan(state, [rec])
        state.clear()
        state.update(nonlocal_state)
        save_state()
        refresh()

    def open_selected() -> None:
        e = selected_entry()
        if not e:
            return
        p = e["path"]
        try:
            if os.name == "nt":
                os.startfile(p)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", p], **_quiet_popen_kwargs())
        except Exception as exc:
            messagebox.showerror("Open folder", str(exc))

    def configure_selected() -> None:
        e = selected_entry()
        if not e:
            return
        win = tk.Toplevel(root)
        win.title("Configure Local Kristal")
        win.transient(root)
        win.grab_set()
        target = tk.StringVar(value=e.get("publication_target", "none"))
        ttk.Label(win, text=e.get("title"), font=("TkDefaultFont", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 8))
        ttk.Label(win, text="GitHub target").grid(row=1, column=0, sticky="w", padx=12, pady=5)
        ttk.Combobox(win, textvariable=target, values=["none", "private", "public"], state="readonly", width=18).grid(row=1, column=1, sticky="w", padx=12, pady=5)
        ttk.Label(
            win,
            text=(
                "Sync writes the validated current State Snapshot into the bootstrapped Kristal collection:\n"
                "kristal-public or kristal-private → kristals/<slug>/state/state-snapshot.json.\n\n"
                "This makes the Kristal available to GitHub-connected readers. Sync is NOT an immutable Publish/Activate operation."
            ),
            justify="left",
            wraplength=600,
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=12, pady=8)

        def ok() -> None:
            e["publication_target"] = target.get()
            save_state()
            refresh()
            win.destroy()

        ttk.Button(win, text="Save", command=ok).grid(row=3, column=1, sticky="e", padx=12, pady=12)

    def details_selected() -> None:
        e = selected_entry()
        if not e:
            return
        lines = [
            f"Kristal: {e.get('title')}",
            f"Health: {e.get('readiness') or 'OBSERVED'}",
            f"Workspace: {e.get('workspace_format') or e.get('kind')}",
            f"Path: {e.get('path')}",
            f"State source: {e.get('state_source') or 'none'}",
            f"State ref: {e.get('state_ref') or 'none'}",
            f"Commitment: {e.get('state_commitment') or 'none'}",
            f"GitHub target: {e.get('publication_target') or 'none'}",
            f"Last sync repo: {e.get('last_sync_repository') or 'none'}",
            f"Last sync commit: {e.get('last_sync_commit') or 'none'}",
            f"Last read-surface root: {e.get('last_sync_surface_root') or 'none'}",
            f"Last read-surface digest: {e.get('last_sync_surface_digest') or 'none'}",
            f"AI entrypoint: {e.get('last_sync_entrypoint') or 'none'}",
        ]
        reasons = e.get("state_conflict_reasons") or []
        if reasons:
            lines.append("")
            lines.append("State conflict:")
            lines.extend(f"- {reason}" for reason in reasons)
        candidates = e.get("state_candidates") or []
        if candidates:
            lines.append("")
            lines.append("Observed state surfaces:")
            for row in candidates:
                lines.append(f"- {row.get('source')} [{row.get('role') or 'observed'}]: {row.get('state_ref')} @ {row.get('state_commitment')}\n  {row.get('path')}")
        if e.get("hidden_auxiliary"):
            lines.append("")
            lines.append(f"Nested legacy auxiliary under: {e.get('nested_under')}")
        messagebox.showinfo("Kristal details", "\n".join(lines))

    def validate_selected() -> None:
        e = selected_entry()
        if not e:
            return
        p = Path(e["path"])

        def task() -> Any:
            return validate_local_cached(
                p, previous=e, workspace_root=workspace(), network_config=netfile(), progress=post_progress
            )

        def done(r: dict[str, Any]) -> None:
            e["last_validation"] = utc_now()
            e["last_validation_result"] = r["result"]
            e["last_validation_cache_key"] = r.get("validation_cache_key")
            e["state_path"] = r.get("state_path")
            e["state_source"] = r.get("state_source")
            e["state_ref"] = r.get("state_ref")
            e["state_commitment"] = r.get("state_commitment")
            e["state_blob_digest"] = r.get("state_blob_digest")
            e["state_candidates"] = r.get("state_candidates", [])
            e["state_conflict"] = bool(r.get("state_conflict"))
            e["state_conflict_reasons"] = r.get("state_conflict_reasons", [])
            e["readiness"] = r.get("readiness") or e.get("readiness")
            e["needs_migration"] = bool(r.get("needs_migration"))
            e["workspace_format"] = r.get("workspace_format")
            save_state()
            refresh()

        run_task(f"Validate {e.get('title')}", task, done)

    def validate_all() -> None:
        entries = [e for e in state.get("entries", []) if e.get("kind") == "local" and not e.get("hidden_auxiliary")]
        if not entries:
            messagebox.showinfo("Batch validation", "No Local Kristals to validate.")
            return
        if not messagebox.askyesno(
            "Batch validation",
            f"Validate {len(entries)} Local Kristal(s)?\n\nValidation runs in parallel (up to 4 workers). Progress appears in the log window.",
        ):
            return

        def task() -> Any:
            return validate_entries_parallel(
                entries, workspace_root=workspace(), network_config=netfile(), progress=post_progress
            )

        def done(results: list[dict[str, Any]]) -> None:
            by_path = {str(e.get("path")): e for e in state.get("entries", [])}
            valid = errors = 0
            for item in results:
                e = by_path.get(str(item.get("path")))
                if not e:
                    continue
                if not item.get("ok"):
                    e["last_validation"] = utc_now()
                    e["last_validation_result"] = "ERROR"
                    errors += 1
                    continue
                r = item["validation"]
                e["last_validation"] = utc_now()
                e["last_validation_result"] = r.get("result")
                e["last_validation_cache_key"] = r.get("validation_cache_key")
                e["state_path"] = r.get("state_path")
                e["state_source"] = r.get("state_source")
                e["state_ref"] = r.get("state_ref")
                e["state_commitment"] = r.get("state_commitment")
                e["state_blob_digest"] = r.get("state_blob_digest")
                e["state_candidates"] = r.get("state_candidates", [])
                e["state_conflict"] = bool(r.get("state_conflict"))
                e["state_conflict_reasons"] = r.get("state_conflict_reasons", [])
                e["readiness"] = r.get("readiness") or e.get("readiness")
                e["needs_migration"] = bool(r.get("needs_migration"))
                e["workspace_format"] = r.get("workspace_format")
                if r.get("result") == "VALID":
                    valid += 1
                elif r.get("result") == "ERROR":
                    errors += 1
            save_state()
            refresh()
            messagebox.showinfo(
                "Batch validation",
                f"Completed: {len(results)}\nVALID: {valid}\nOther/error: {len(results) - valid}",
            )

        run_task(f"Batch Validate ({len(entries)})", task, done, show_result=False)

    def sync_all_configured() -> None:
        entries = [
            e for e in state.get("entries", [])
            if e.get("kind") == "local" and not e.get("hidden_auxiliary")
            and e.get("publication_target") in {"public", "private"}
        ]
        if not entries:
            messagebox.showinfo("Batch GitHub Sync", "No Local Kristals are configured with a public/private GitHub target.")
            return
        public_count = sum(1 for e in entries if e.get("publication_target") == "public")
        private_count = len(entries) - public_count
        if not messagebox.askyesno(
            "Batch GitHub Sync",
            f"Sync {len(entries)} configured Kristal(s)?\n\nPublic: {public_count}\nPrivate: {private_count}\n\n"
            "Validation and Local Kit read-surface preparation run in parallel. Each collection is then updated as ONE transaction: "
            "one fetch, one commit and one push for all changed Kristals in that collection. Public/private collections can run in parallel. "
            "Progress appears in the log window.",
        ):
            return

        def task() -> Any:
            return sync_entries_batch(
                entries, workspace_root=workspace(), network_config=netfile(), progress=post_progress
            )

        def done(results: list[dict[str, Any]]) -> None:
            by_path = {str(e.get("path")): e for e in state.get("entries", [])}
            synced = already = errors = 0
            for item in results:
                e = by_path.get(str(item.get("path")))
                if not e:
                    continue
                if not item.get("ok"):
                    errors += 1
                    continue
                r = item["sync"]
                e["last_validation"] = utc_now()
                e["last_validation_result"] = "VALID"
                if r.get("validation_cache_key"):
                    e["last_validation_cache_key"] = r.get("validation_cache_key")
                e["last_sync_at"] = utc_now()
                e["last_sync_commit"] = r.get("commit")
                e["last_sync_repository"] = r.get("repository")
                e["last_sync_state_path"] = r.get("state_path")
                e["last_sync_blob_digest"] = r.get("state_blob_digest")
                e["last_sync_surface_digest"] = r.get("surface_digest")
                e["last_sync_surface_root"] = r.get("surface_root")
                e["last_sync_entrypoint"] = r.get("entrypoint")
                e["last_sync_file_count"] = r.get("file_count")
                e["last_sync_total_bytes"] = r.get("total_bytes")
                e["state_blob_digest"] = r.get("state_blob_digest")
                if r.get("result") == "ALREADY SYNCED":
                    already += 1
                else:
                    synced += 1
            save_state()
            refresh()
            messagebox.showinfo(
                "Batch GitHub Sync",
                f"Completed: {len(results)}\nSynced: {synced}\nAlready synced: {already}\nErrors: {errors}",
            )

        run_task(f"Batch Sync ({len(entries)})", task, done, show_result=False)

    def migrate_selected() -> None:
        e = selected_entry()
        if not e:
            return
        rec = detect_kristal(Path(e["path"]))
        if not rec or not rec.get("needs_migration"):
            messagebox.showinfo("Kristal Manager", f"This Local Kristal is already {CURRENT_LOCAL_FORMAT} or is not a workspace.")
            return
        if not messagebox.askyesno(
            "Migrate Local Kristal",
            f"Migrate {e.get('title')} from {rec.get('workspace_format')} to {CURRENT_LOCAL_FORMAT}?\n\n"
            "A safety ZIP of the workspace envelope/state index/tool is created before migration. The observed state commitment must remain unchanged.",
        ):
            return

        def task() -> Any:
            return migrate_local(Path(e["path"]), workspace_root=workspace(), network_config=netfile())

        def done(_r: Any) -> None:
            do_scan()

        run_task(f"Migrate {e.get('title')} to Local 3.2", task, done)

    def sync_selected() -> None:
        e = selected_entry()
        if not e:
            messagebox.showinfo("GitHub Sync", "Select a Local Kristal first, then click Sync to GitHub.")
            return
        target = e.get("publication_target", "none")
        if target not in {"public", "private"}:
            messagebox.showinfo("GitHub Sync", "Configure this Local Kristal with GitHub target public or private first.")
            configure_selected()
            return
        visibility_note = "PUBLIC" if target == "public" else "PRIVATE"
        if not messagebox.askyesno(
            "Sync to GitHub",
            f"Validate and sync {e.get('title')} to the {visibility_note} Kristal GitHub collection?\n\n"
            "This refreshes the portable AI read layer, then syncs the exact Local Kit read surface and collection index used by GitHub-connected readers. "
            "It does not Publish or Activate an immutable release.",
        ):
            return

        def task() -> Any:
            return sync_local_to_github(
                e, workspace_root=workspace(), network_config=netfile(), progress=post_progress
            )

        def done(r: dict[str, Any]) -> None:
            e["last_validation"] = utc_now()
            e["last_validation_result"] = "VALID"
            if r.get("validation_cache_key"):
                e["last_validation_cache_key"] = r.get("validation_cache_key")
            e["last_sync_at"] = utc_now()
            e["last_sync_commit"] = r.get("commit")
            e["last_sync_repository"] = r.get("repository")
            e["last_sync_state_path"] = r.get("state_path")
            e["last_sync_blob_digest"] = r.get("state_blob_digest")
            e["last_sync_surface_digest"] = r.get("surface_digest")
            e["last_sync_surface_root"] = r.get("surface_root")
            e["last_sync_entrypoint"] = r.get("entrypoint")
            e["last_sync_file_count"] = r.get("file_count")
            e["last_sync_total_bytes"] = r.get("total_bytes")
            e["state_blob_digest"] = r.get("state_blob_digest")
            save_state()
            refresh()
            result = str(r.get("result") or "SYNC PASS")
            repository = str(r.get("repository") or "")
            state_path = str(r.get("state_path") or "")
            surface_root = str(r.get("surface_root") or "")
            entrypoint = str(r.get("entrypoint") or "")
            messagebox.showinfo(
                "GitHub Sync",
                f"{result}\n\nRepository: {repository}\nRead surface: {surface_root}\nAI entrypoint: {entrypoint}\nState: {state_path}",
            )

        run_task(f"Validate + Sync {e.get('title')}", task, done)

    def backup_selected() -> None:
        e = selected_entry()
        if not e:
            return
        repo = (e.get("backup_repository") or "").strip()
        if not repo:
            messagebox.showinfo("Kristal Manager", "Configure a backup repository first.")
            configure_selected()
            return
        vis = e.get("backup_visibility", "private")
        if vis == "public" and not messagebox.askyesno("Public GitHub backup", f"{e.get('title')} will be backed up to a PUBLIC GitHub repository. Continue?"):
            return

        def task() -> Any:
            return backup_local(Path(e["path"]), owner=owner(), repo=repo, visibility=vis)

        def done(r: dict[str, Any]) -> None:
            e["last_backup_at"] = utc_now()
            e["last_backup_sha"] = r["sha"]
            save_state()
            refresh()

        run_task(f"Backup {e.get('title')}", task, done)

    def backup_all() -> None:
        configured = [e for e in state.get("entries", []) if e.get("backup_repository")]
        if not configured:
            messagebox.showinfo("Kristal Manager", "No backup repositories are configured.")
            return
        if not messagebox.askyesno("Backup modified Kristals", f"Check and back up {len(configured)} configured Kristals? Public entries remain subject to sensitive-file blocking."):
            return

        def task() -> Any:
            out = []
            for e in configured:
                gs = repo_status(Path(e["path"]))
                if gs.get("git") and not gs.get("dirty") and e.get("last_backup_sha") == gs.get("head"):
                    out.append({"title": e.get("title"), "result": "SKIPPED clean"})
                    continue
                r = backup_local(Path(e["path"]), owner=owner(), repo=e["backup_repository"], visibility=e.get("backup_visibility", "private"))
                e["last_backup_at"] = utc_now()
                e["last_backup_sha"] = r["sha"]
                out.append({"title": e.get("title"), **r})
            return out

        def done(_r: Any) -> None:
            save_state()
            refresh()

        run_task("Backup all modified Kristals", task, done)

    def do_import() -> None:
        p = filedialog.askopenfilename(title="Import Kristal ZIP", filetypes=[("ZIP", "*.zip"), ("All files", "*")])
        if not p:
            p = filedialog.askdirectory(title="Or select a Kristal folder")
        if not p:
            return
        dest = Path(locals_root.get()).expanduser().resolve()

        def task() -> Any:
            return [str(x) for x in import_local(Path(p), dest)]

        def done(_r: Any) -> None:
            roots = [x.strip() for x in scan_roots_var.get().split(";") if x.strip()]
            if str(dest) not in roots:
                roots.append(str(dest))
                scan_roots_var.set(";".join(roots))
            do_scan()

        run_task("Import Local Kristal", task, done)

    def launch_app(target: Path | None, label: str, extra_env: dict[str, str] | None = None) -> None:
        if not target or not target.exists():
            messagebox.showinfo(label, f"{label} was not found under {workspace()}.")
            return
        env = os.environ.copy()
        env["KRISTAL_MANAGER_CATALOG"] = str(cfgfile())
        if extra_env:
            env.update(extra_env)
        try:
            if target.suffix.lower() == ".pyw":
                subprocess.Popen([_pythonw_executable(), str(target)], cwd=str(target.parent), env=env, **_quiet_popen_kwargs())
            elif target.suffix.lower() == ".cmd":
                subprocess.Popen(["cmd", "/c", str(target)], cwd=str(target.parent), env=env, **_quiet_popen_kwargs())
            elif os.name == "nt":
                os.startfile(str(target))  # type: ignore[attr-defined]
        except Exception as exc:
            messagebox.showerror(label, str(exc))

    def prepare_publish() -> None:
        e = selected_entry()
        if not e:
            return
        if e.get("publication_target", "none") == "none":
            messagebox.showinfo("Publication", "Configure this Local Kristal with GitHub target public or private first.")
            return

        def task() -> Any:
            return prepare_publication_request(e, workspace_root=workspace(), network_config=netfile())

        def done(r: dict[str, Any]) -> None:
            e["last_publish_request"] = r["request_path"]
            save_state()
            refresh()
            setup = find_github_setup(workspace())
            if setup:
                if messagebox.askyesno("Publication handoff ready", f"Request created:\n{r['request_path']}\n\nOpen Kristal GitHub Setup now?"):
                    launch_app(setup, "Kristal GitHub Setup", {"KRISTAL_MANAGER_PUBLISH_REQUEST": r["request_path"]})
            else:
                messagebox.showinfo("Publication handoff ready", f"Request created:\n{r['request_path']}\n\nKristal GitHub Setup was not found locally.")

        run_task(f"Prepare publication handoff for {e.get('title')}", task, done)

    ttk.Button(btns, text="Quick Scan", command=do_scan).pack(side="left", padx=3)
    ttk.Button(btns, text="Deep Scan", command=do_deep_scan).pack(side="left", padx=3)
    ttk.Button(btns, text="Add folder", command=add_folder).pack(side="left", padx=3)
    ttk.Button(btns, text="Import ZIP/folder", command=do_import).pack(side="left", padx=3)
    ttk.Button(btns, text="Configure", command=configure_selected).pack(side="left", padx=3)
    ttk.Button(btns, text="Details", command=details_selected).pack(side="left", padx=3)
    ttk.Button(btns, text="Validate", command=validate_selected).pack(side="left", padx=3)
    ttk.Button(btns, text="Validate All", command=validate_all).pack(side="left", padx=3)
    ttk.Button(btns, text="Migrate → Local 3.2", command=migrate_selected).pack(side="left", padx=3)
    ttk.Button(btns, text="Open folder", command=open_selected).pack(side="right", padx=3)

    ttk.Button(btns2, text="Sync to GitHub", command=sync_selected).pack(side="left", padx=3)
    ttk.Button(btns2, text="Sync All Configured", command=sync_all_configured).pack(side="left", padx=3)
    ttk.Button(btns2, text="Prepare Publish → GitHub Setup", command=prepare_publish).pack(side="left", padx=(18, 3))

    sr = 0

    def setting(label: str, var: tk.StringVar, browse: Callable[[], None] | None = None) -> None:
        nonlocal sr
        ttk.Label(settings_tab, text=label).grid(row=sr, column=0, sticky="w", pady=4)
        ttk.Entry(settings_tab, textvariable=var, width=78).grid(row=sr, column=1, sticky="ew", pady=4)
        if browse:
            ttk.Button(settings_tab, text="Browse", command=browse).grid(row=sr, column=2, padx=(6, 0), pady=4)
        sr += 1

    setting("Workspace root", workspace_root, lambda: (lambda p: workspace_root.set(p) if p else None)(filedialog.askdirectory(title="Kristal workspace root")))
    setting("Manager registry", config_path)
    setting("GitHub network.toml", network_path)
    setting("Default locals folder", locals_root, lambda: (lambda p: locals_root.set(p) if p else None)(filedialog.askdirectory(title="Default locals folder")))
    setting("Scan roots (; separated)", scan_roots_var)
    settings_tab.columnconfigure(1, weight=1)
    ttk.Button(settings_tab, text="Add scan root", command=add_root).grid(row=sr, column=0, sticky="w", pady=8)
    ttk.Button(settings_tab, text="Save settings", command=lambda: (save_state(), refresh())).grid(row=sr, column=1, sticky="w", pady=8)

    ttk.Label(tools_tab, text="System boundaries", font=("TkDefaultFont", 11, "bold")).pack(anchor="w", pady=(0, 8))
    ttk.Label(
        tools_tab,
        text=(
            "Kristal Manager = inventory, Local Kit validation/migration and one-click Sync into GitHub collections.\n"
            "Kristal GitHub Setup = bootstrap/network plus qualification, immutable publication and activation.\n"
            "Kompiler = optional read-only context compiler; it consumes local/hosted Kristals."
        ),
        justify="left",
        wraplength=850,
    ).pack(anchor="w", pady=(0, 12))
    ttk.Button(tools_tab, text="Open Kristal GitHub Setup", command=lambda: launch_app(find_github_setup(workspace()), "Kristal GitHub Setup")).pack(anchor="w", pady=4)
    ttk.Button(tools_tab, text="Open Kompiler (optional)", command=lambda: launch_app(find_kompiler(workspace()), "Kompiler")).pack(anchor="w", pady=4)
    ttk.Button(tools_tab, text="Open local registry HTML", command=lambda: webbrowser.open(cfgfile().with_name("kristal-manager.html").as_uri()) if cfgfile().with_name("kristal-manager.html").exists() else messagebox.showinfo("Registry", "Run Quick Scan first.")).pack(anchor="w", pady=4)

    try:
        load_state()
        Path(locals_root.get()).mkdir(parents=True, exist_ok=True)
        refresh()
        root.after(300, do_scan)
    except Exception as exc:
        append(f"Startup warning: {exc}")
    root.mainloop()
