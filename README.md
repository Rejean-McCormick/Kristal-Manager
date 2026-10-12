# Kristal Manager

**Recovery update:** `0.1.0-alpha.12` · **Framework target:** `10.0.0-draft.3.1` · **Operational status:** **read-only inventory available; GitHub synchronization disabled**.

Kristal Manager owns the operational inventory of **existing** Kristal workspaces and, when independently restored and qualified, should orchestrate controlled GitHub v10 read-surface synchronization. It does **not** own the semantic interpretation of knowledge, the archetype library, domain qualifications, or publication/activation.

> This update repairs an important source-distribution defect: the supplied alpha.11 snapshot and the publicly accessible GitHub `main` branch both lacked the `kristal_manager/` Python package referenced by the launcher and tests. We have **not reconstructed the missing alpha.11 Git sync engine** from guesswork. Instead, the recovery package provides a working and tested read-only inventory, a desktop GUI, a Konstellation-facing local export, and an intact C2 cryptographic verifier. Any remote mutation remains blocked until the full backend can be recovered and audited.

## Quick start (Windows)

1. Extract the entire repository to a local directory.
2. Install Python **3.11+** (Tkinter is normally available with standard Windows Python).
3. Double-click **`Kristal-Manager.pyw`** or `Launch-Kristal-Manager.cmd`.
4. Select the parent folder of your local Kristals and choose **Scan local Kristals**.
5. Inspect workspace identity, profile, state snapshot source, structural readiness and recorded commitments.
6. To export locally, choose **Export local inventory JSON**. The file remains on your machine.

The accompanying `kristal-manager.html` can open an exported JSON inventory with your browser's local file picker. It is a convenience table, **not** a duplicate Konstellation semantic explorer.

## CLI (English)

From the repository root:

```bash
python -m kristal_manager scan "C:\mycode\Kristal\locals"
python -m kristal_manager inspect "C:\mycode\Kristal\locals\MyKristal"
python -m kristal_manager export "C:\mycode\Kristal\locals" --output private-local-inventory.json
```

`export` refuses overwriting an existing file unless `--overwrite` is supplied. Absolute local paths are omitted by default; `--include-paths` is a deliberate and potentially sensitive operator opt-in. On POSIX systems the generated file is owner-readable only (`0600`). **Do not place this export in a public GitHub repository or an unauthenticated web server.**

## What the inventory means

| Property | Source / meaning |
| --- | --- |
| `state_ref` | Workspace declaration and current v9 state snapshot; explicitly checked for mismatch |
| `state_commitment` | Digest **reported by** the state snapshot, not independently recomputed or factually qualified |
| `state_blob_digest` | Byte SHA-256 of the current snapshot file, **not** the logical State Commitment |
| `readiness` | Locally observed structural readiness (`READY`, `NO STATE`, `STATE CONFLICT`, etc.) |
| `hosted_network_baseline` | Declared v10 target capability, **not** proof of being hosted |
| `archetype` | `UNDECLARED` by default; Arketype association requires an explicit mapping |
| `qualification` / `publication` | `NOT_ESTABLISHED` unless independently validated elsewhere |
| `availability` | `local`; a local record is not automatically publicly accessible |

The provisional export format is **`kristal.manager-local-inventory/0.1-candidate`**, a local integration proposal, **not a normative Framework format**. It is intended for a future **authenticated, policy-first Konstellation fleet adapter**. Konstellation owns navigation among Kristals and into concepts; Manager only owns operational inventory and access-restricted metadata export. The final producer/consumer contract must be agreed by both repositories before any network endpoint is enabled.

## v10 architecture boundaries

```text
Authoring Kit 3.2.4+  --> Local workspace + exact read-surface (when ready)
                         |
Kristal Manager    -->   Local inventory + operational verification
                         | (future, gated and audited)
                         +--> C1 independent qualification + C2 authorization
                         +--> GitHub collection sync manifest + derived index
                         +--> C3 hosted collection verification
Konstellation      <--   Read-only, policy-scoped inventory + verified hosted sources
Arketype           -->   Archetype descriptions and noncanonical design patterns
```

A successful check does **not** qualify claims or authorize network exposure. Sync is separate from immutable publication and activation. A push to a public GitHub repository is already **public exposure**, so C1/C2 must be checked **before any public network write**.

## Recovery capabilities and explicit blockers

| Capability | State in alpha.12 recovery |
| --- | --- |
| Local scan, nested workspaces, basic conflict detection | **Implemented** |
| GUI inventory, search, selected-state inspection | **Implemented** |
| Local-only policy-minimized JSON export | **Implemented** |
| Standalone offline HTML inventory viewer | **Implemented** |
| C2 signed grant / per-revision qualification verifier | **Included** from Bootstrap's candidate verifier; independent security tests run |
| Kit 3.2.4 readiness and read-surface invocation | **NOT RESTORED**; see docs |
| C1, C2 and C3 interoperability end-to-end | **NOT VERIFIED** |
| Local migration, preparation of publish requests | **BLOCKED**, original implementation unavailable |
| GitHub sync / batch sync / full backup | **BLOCKED**, no remote mutation performed |
| Live GitHub state, remote branch protections, Windows interactive GUI | **NOT VERIFIED** |

## Tests

```bash
python -m pip install -e ".[test]"
python -m pytest -q tests/test_recovery.py tests/test_c2_public_gate.py
```

The original `tests/test_core.py` remains available as an **unresolved compatibility suite** documenting legacy alpha.11 behavior. Many of those tests expect a synchronization engine not supplied in the source repository. **Do not claim that the historical suite passes** or remove its failed cases to disguise missing behavior. A future source recovery must restore those operations with C1/C2/C3 guards and validate every historical test.

## Relevant documentation

- [Architecture](ARCHITECTURE.md)
- [Current recovery status](docs/RECOVERY_STATUS.md)
- [Konstellation inventory handoff](docs/KONSTELLATION_INVENTORY.md)
- [v10 alignment and security gates](docs/V10_ALIGNMENT.md)
- [C2 signed evidence requirements](docs/C2_PUBLICATION_CONTROL.md)

No public/private Kristal collection was modified or published by this release artifact.

## Authentic original runtime found in Git history

After preparing this recovery build, an audit of repository history located the full authentic Python backend in commit **`237b1b539332da5d87bed4b185ea03794aad1057`**, from which the current public branch removed its Python package. See [Historical runtime recovery](docs/HISTORICAL_RUNTIME_RECOVERY.md) and `tools/restore_original_backend.py`. This is preferable to treating the recovery's intentionally disabled sync routines as their eventual implementation. The exporter works **offline** against a full local Git clone, stages verifiable source for review, and never changes the checkout or contacts GitHub.

**Operator caution:** `GitSink.bat` is an inherited generic Git helper that may stage/commit/push all changes; it is **not** used by the Manager launcher or recovery tests. Do not invoke it as an alignment or publication step.
