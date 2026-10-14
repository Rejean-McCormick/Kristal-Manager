# Changelog

## 0.1.0-alpha.13 — Kit 3.3 discovery + local KNAV adapter (2026-10-13)

- Consume the three Kit 3.3 noncanonical Discovery/reader files with fail-closed consistency checks.
- Add optional byte-level registered-source verification, with explicit unverified status by default.
- Add a strict, opt-in local Konstellation preview export with operator-chosen principal and no inferred permissions.
- Display Discovery metadata in the local GUI; keep existing scan/readiness and blocked sync.
- Archive the stale root snapshot index; add an optional SHA-pinned local cleanup GUI.
- Update docs, tests, and package inventory without enabling C2/C3/C4 operations.


## 0.1.0-alpha.12 — Local Inventory Recovery (2026-10-12)

- Added the previously missing `kristal_manager` package as a **restricted recovery implementation**.
- Implemented local discovery, v9 state source/legacy/conflict inspection, read-only GUI and CLI.
- Added candidate local-only inventory JSON for future authorized Konstellation integration.
- Included the Bootstrap C2 verifier and preserved the historical tests.
- Explicitly disabled GitHub sync, migration, full backup and public mutation because their original backend was not present in the provided source.
- Rewrote the project documentation in English and documented unresolved E2E obligations.

## 0.1.0-alpha.11 (historical source contract)

- Historical docs and tests describe exact Authoring Kit read-surface synchronization and C2 gates; the corresponding runtime source was absent from the available snapshot. That historical functionality is **not** represented as operational in alpha.12.
