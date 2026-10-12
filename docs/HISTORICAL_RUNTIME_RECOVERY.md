# Verified Historical Manager Runtime — Safe Restoration Procedure

On 2026-10-12, a read-only GitHub history audit identified that the current public default branch **deleted** the runtime modules, but an earlier commit preserves their authentic sources:

- Repository: `Rejean-McCormick/Kristal-Manager`
- Original commit: `237b1b539332da5d87bed4b185ea03794aad1057`
- Present in the historical commit: `kristal_manager/__init__.py` (31 B), `core.py` (107,372 B), `gui.py` (37,795 B), `publication_gate.py` (9,042 B).
- Later main: the same four Python files were **removed**, without any contemporaneous change to the historical `tests/test_core.py` expectations.

The historical source has **not been assumed safe for new GitHub writes**. Its restored operation requires a separate, exact-code review of the C1/C2/C3 gates and read-surface path before returning the Sync buttons.

## Operator-safe export (from a full local Git clone)

```bash
python tools/restore_original_backend.py \
  --repository "C:/mycode/Kristal/Kristal-Manager" \
  --output "C:/mycode/Kristal/manager-runtime-review"
```

This reads only Git object blobs **already stored in the clone**; it performs **no fetch, merge, checkout, push or publication**, verifies the expected Git blob SHA for every file, and refuses to overwrite any pre-existing destination. If the commit is not available locally, the tool stops with a clear error; obtaining that historical commit requires a separate Git fetch authorized by the operator.

**Do not blindly overwrite the recovery implementation with these files.** Inspect the diff, restore into an isolated test branch/clone, then run the full historical suite, the C2 negative tests and a private staging-only v10 fixture before any sync operation is enabled. Continue to enforce `KRISTAL_C2_TRUST_PIN` and independent C1 qualification where required.

## GitHub access limitation

A GitHub connector successfully read the public repository and historical Git tree, but **branch creation was denied (HTTP 403, `Resource not accessible by integration`)**. Therefore no branch, PR, or commit was created in GitHub by this update. The ZIP remains an independent local recovery artifact.
