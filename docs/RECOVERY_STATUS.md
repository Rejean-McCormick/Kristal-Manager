# Source Recovery Status

**Snapshot:** `Code_snapshot_Kristal-Manager(3).zip`, captured 2026-10-12 15:14. **Remote observation:** public `Rejean-McCormick/Kristal-Manager` default branch `main` was read on 2026-10-12 and had the same absence of the Python package.

## Root cause

`Kristal-Manager.pyw` imports `kristal_manager.gui.main`, while historical tests import dozens of functions from `kristal_manager.core` and C2 from `kristal_manager.publication_gate`. The original distribution contains **no `kristal_manager/` directory**. Therefore a complete faithful reconstruction of the original backend cannot be claimed from its published source.

## What was restored

- A safe local-only Python package with CLI, Tkinter GUI, state source inspection and conflict status.
- An inventory export without raw canon content, explicit disclosure controls, collision flags and no inferred Arketype type.
- Original C2 verification logic from Bootstrap and tests of its signed-trust behavior.
- A browser-only local inventory viewer; no external scripts, services or network requests.

## What remains blocked

The alpha.11 API names for migration, `prepare_github_read_surface`, `sync_local_to_github`, batch sync, Git checkouts and public backup intentionally raise `ManagerError` rather than faking success. `tests/test_core.py` retains the historical test expectations and is not the green release gate for the restricted recovery. See `TEST_REPORT.md` for exact results.

## Required inputs to finish M-01 / M-02 / M-03

Obtain the authentic former `kristal_manager/` package from the original operator workstation or Git history, together with its dependencies and exact commit/source SHA. Compare its behavior with historical tests and the independently reviewed C1/C2/C3 contracts. Restore one feature at a time behind negative safety tests, starting with read-surface preparation, then staging-only private sync. Only then consider C2-authorized public sync.


## Alpha.13 addendum (2026-10-13)

- Authoring Kit 3.3 Discovery/reader files are inspected read-only, with absence tolerated,
  inconsistent/incomplete metadata flagged, and optional byte-level fingerprint checking.
- An operator-controlled, no-network KNAV preview export adapts to Konstellation's
  existing experimental `konstellation.manager-inventory-preview/0.1` consumer.
- The adapter requires an explicitly supplied principal, does not infer eligibility,
  does not authorize artifact reads and does not claim hosted availability.
- Windows GUI validation, original GitHub sync backend recovery and independent
  qualification/publication gates are still pending.


## 2026-10-16 — alpha.14 operational assessment

The current local ZIP adds on-demand operational verification and a pinned optional Framework state verifier, not restoration of the historical GitHub backend. The root SNAPSHOT_INDEX.txt is an original source-snapshot index; use PACKAGE_MANIFEST_SHA256.json to check this release instead.
