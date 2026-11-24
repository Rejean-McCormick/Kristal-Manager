# Local folder icons — explicit opt-in (Manager)

**Local-use guide, based on the 2026-11-23 source snapshot.** This feature is **off by default**. It is separate from read-only inventory and does not authorize GitHub synchronization, release or semantic qualification.

In the Manager **Icons** menu, choose “Activer icônes personnalisées sur dossiers Windows (session)” only if you intend to modify local Windows folder appearance. Then use “Gérer les icônes de locals…”. Select the source folder (by default `C:\mycode\Kristal\locals`), inspect the browser preview, acknowledge the second write permission, and confirm generation explicitly.

The local Node icon generator refuses writes when not explicitly enabled, and scanning is read-only even when the opt-in server mode is enabled. Only entries with coherent **declared UNESCO Thesaurus** domain/microthesaurus metadata are eligible; unknown or inconsistent mappings are **skipped**. Output may include local `.ico`, `desktop.ini` and `.kristal/icon-profile.json` files. Back up target folders before confirming writes. Prior ISCED icon files are historical and are not silently converted.

**Evidence:** `tests/test_local_folder_icons.py`, `tools/icon-generator/server.mjs`, `tools/icon-generator/UNESCO_THESAURUS_POLICY.md`. Source and tests describe intended behavior; this overlay does **not** perform folder-icon writes or run the GUI.
