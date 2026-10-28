# Kristal Manager — English UI & batch folder normalization

## What changed

- Application name is **Kristal Manager** (not all caps), with brand color `#1E6864`.
- All primary desktop navigation and the integrated diagnostic overlay are now in English.
- The table no longer contains the “Icon / nature” column or a tree icon column.
- The icon of the **selected** Kristal appears beside its Overview / next steps panel, at the bottom left.
- The **State ID** column displays a compact name, while JSON details retain the full authoritative `state_ref` URN.
- **Organize / export → Normalize folders in batch…** opens an overlay for preview and checked selection.

## How to use batch rename

1. Launch `Launch-Kristal-Manager.cmd` and scan `C:\mycode\Kristal\locals`.
2. Choose **Actions → Normalize folders in batch…** (or **Organize / export → Normalize folders in batch…**).
3. Review proposed names. **No folders are selected by default**. Click the checkboxes or **Select eligible**.
4. Review the backup/report destination, which MUST be outside the source tree.
5. Click **Back up and rename selected…**, then explicitly approve the warning.
6. The Manager exports ZIP backups **before the first rename**, then renames only selected eligible top-level folders. A dated JSON journal is written outside `locals`.
7. To restore names, choose **Undo from journal…**, select a batch journal, and confirm. Undo is blocked if a conflicting folder already exists or metadata changed.

### Scope and safety

- Only immediate children of the scanned root containing a real `kristal.workspace.json` are eligible.
- Historical snapshots and nested subfolders are never batch rename candidates.
- Target names are generated from `title` or `slug` **inside** `kristal.workspace.json`.
- Already-standard folders are marked “Already standard”; invalid names and collisions are marked “Blocked”.
- No source file content is edited by a batch rename. **Directory paths change**, however, and absolute paths in scripts, links and external references are **not** rewritten. Check your dependent workflows.
- If the batch fails during a rename, the tool attempts a guarded rollback, and writes the result in the journal. Examine any `rollback_failed` entries before continuing.
- Backups and the journal may contain private data. Keep them in a trusted location with sufficient disk space.

### State ID display

Display is intentionally **presentation-only**: e.g. `urn:kristal:state:agriculture` appears as `agriculture`, and `urn:kristal:architecture:state` appears as `architecture`. The original URN is never altered.

## Validation

- 169 tests passed across the complete Python test suite. 14 existing tests fail for disabled historical publication / synchronization / migration backend operations. These are not part of batch renaming.
- 37 focused tests passed, including the batch preview, backups, safe undo, icons, diagnostic overlay and graphical UI.
- The UI was smoke-tested under a Linux virtual display. Windows Explorer icon behavior, long paths and the final appearance on Windows still need to be confirmed on the target PC.
- The bundled KristalDiag stays separate from any Framework V11 certification claim.
