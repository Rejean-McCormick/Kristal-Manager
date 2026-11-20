# Konnaxion_Worlds

Canonical owner of the Konnaxion Universe/World control plane and WorldRelease runtime-isolation engine.

The package is installable from `backend/`:

```text
pip install -e <path-to-Konnaxion_Worlds>/backend
```

The main Konnaxion repository consumes `konnaxion.worlds`; it must not carry a second copy of the engine, migrations, or canonical Universe/World specifications.

Architecture locks:

- `KX-WORLDS-1`: World/WorldRelease isolation invariants.
- `KX-UNIVERSES-1`: Universe grouping, graph relations, explicit inter-World publications, and canonical Universe-aware routing.

See `docs/Technical-Reference/Worlds/20_UNIVERSES.md` and `WORLD_SYSTEM_AI.instructions.md` before modifying the engine.

Repository boundary: this engine repository intentionally does **not** ship the Konnaxion browser shell. `WorldContext`, the Universe/World switcher, Next.js rewrites and product navigation remain Konnaxion-owned host adapters consuming this package's contracts.

## Web UI ownership

`Konnaxion_Worlds` is the canonical owner of the Universe/World engine, contracts, control plane, runtime scoping, migrations, and canonical specification. It does **not** ship a second maintained Konnaxion web frontend.

The product-host integration UI (`UniverseSwitcher`, `WorldSwitcher`, route rewrites, browser stale-response guards) is owned by the main `Konnaxion` repository and consumes this engine through its HTTP/runtime contract. This prevents a second frontend implementation from drifting beside the product shell.

The repository-level invariant is stronger than a component blacklist: while this repository is the engine package, a top-level `frontend/` tree is forbidden. Any future reusable browser SDK must live in its own versioned package and be introduced by ADR; it must not be vendored here.

Before committing boundary changes, run:

```text
python scripts/check_repo_boundaries.py
```

## Standalone routing safety

The standalone Django bootstrap uses the same fail-closed routing switch as the hosted engine:

```text
KONNAXION_WORLDS_ENFORCE_SCOPED_API=true
```

It defaults to `true`. `KONNAXION_WORLDS_STRICT_ROUTING` is not a supported setting. Health/readiness and `WorldRouteMiddleware` both read `KONNAXION_WORLDS_ENFORCE_SCOPED_API`, so keep this name aligned in host and standalone settings.

Build/snapshot metadata records `KX-UNIVERSES-1` as the current `architecture_lock`; `KX-WORLDS-1` remains the lower-level World/WorldRelease foundation lock.

## v0.3.6 — Kristal v7 additive ecosystem boundary

Konnaxion Worlds now pins **Kristal Standard 7.0.0-draft.3.1** as the additive meta-orchestration boundary while retaining the unchanged Kristal v6 portable-state contract. The Worlds engine does not become a Kristal/Kristall runtime and does not surrender Universe/World/WorldRelease authority.

Key rules:

- valid v6 `kristal_state` artifacts remain valid and unchanged;
- v7 portable projections remain v6-compatible and may carry `extensions.kristal_v7`;
- KQ/KP/KA/KS, Subjects, axes, Surfaces, Mesh and crystallization remain Kristall-owned structures, not World/Release identity or lifecycle state;
- semantic resonance and Mesh paths are signals/structure, not truth, identity, assertions or execution authority;
- any World-derived Kristal projection must preserve Universe + World + exact Release provenance;
- the previous v6 boundary remains an enforced compatibility foundation.

Run both static gates:

```text
python scripts/check_kristal_v6_boundary.py
python scripts/check_kristal_v7_boundary.py
```

See `docs/Technical-Reference/Worlds/23_KRISTAL_V7_BOUNDARY.md` and `KRISTAL_V7_BOUNDARY.json`.

## v0.3.5 — Kristal v6 ecosystem boundary

Konnaxion Worlds is aligned with **Kristal Standard 6.0.0** and the ecosystem's v6 authority model without becoming a Kristal or Interaction Kernel runtime. The Worlds engine still owns only Universe/World/WorldRelease isolation and lifecycle state.

The v6 boundary is explicit:

- a `World`, `WorldRelease`, `Seed Pack` or Worlds `Snapshot` is **not** a `kristal_state`;
- when World-derived state is projected into Kristal, Universe/World/Release provenance must remain explicit and must not be inferred from display names;
- Kristal `record_role` describes the role of projected knowledge/state but does not transfer Konnaxion ownership;
- Kristal `actionability.mode = automatic` means an automated path may be eligible **after** Konnaxion authorization/policy checks; it is never an execution grant by itself;
- any cross-system mutation still crosses an explicit qualified Interaction Kernel/Profile boundary owned by the integrating host;
- the existing Konnaxion database/runtime `scope` terminology remains unchanged because it is not the retired Kristal v5 `scope` field.

See `docs/Technical-Reference/Worlds/22_KRISTAL_V6_BOUNDARY.md` and `KRISTAL_V6_BOUNDARY.json`.

## Universe build orchestration (v0.3)

For multi-World Universe upgrades, prefer the persisted build queue instead of one long synchronous process:

```text
python manage.py worlds_apply_universe levis --pack-version 0.5.0 --queue --wait --promote
```

The command discovers/hashes the Seed Pack catalog once, reuses exact CURRENT/READY releases and active exact jobs, queues only missing builds, watches persisted `WorldBuildJob` progress, and performs the final Universe promotion/topology update atomically after every exact target is ready.

The `world-build` Celery queue must have at least one worker. Controlled parallelism is configured with:

```text
KONNAXION_WORLD_BUILD_CONCURRENCY=2
```

`2` is a reasonable local starting point; production should be sized from database/CPU/RAM headroom. The PostgreSQL advisory-lock slot pool remains authoritative even when Celery worker concurrency is higher.

For a separate operational view:

```text
python manage.py worlds_jobs --universe levis --watch
```

Progress is persisted in `WorldBuildJob.metadata_json.progress` and includes the current build stage, percentage, message and heartbeat timestamp. Queue workers load only the registered exact Seed Pack for their job instead of rescanning/hashing the entire catalog on every build.

For local Windows development where no Celery worker/Redis service is running, the same persisted-job orchestrator can run child Django processes directly:

```text
python manage.py worlds_apply_universe levis --pack-version 0.5.0 --local-workers 2 --promote
```

`--local-workers N` implies queue + wait, creates the same `WorldBuildJob` rows, uses the same PostgreSQL advisory-lock slot model, and runs up to N isolated `worlds_run_job` child processes. This is the preferred local path for bulk rebuilds because it gives parallelism and live progress without requiring a broker.

## v0.3.4 — host-aware Windows Manager runtime

The Windows Manager now prefers the real sibling Konnaxion host runtime when it is available (`../Konnaxion/backend/.venv/Scripts/python.exe` + `manage.py`). This is the correct context for Konnaxion-owned Universe/World Seed Packs, host scenario importers, EkoH/Smart Vote fixtures, and the existing host database configuration.

Consequences:

- double-clicking `Konnaxion_World_Manager.pyw` no longer bootstraps or waits on a second standalone Django environment when the Konnaxion host checkout is already ready;
- hosted refresh never runs `migrate`; schema changes remain owned by the host deployment workflow;
- registry refresh is read-only (`discover_seed_packs(persist=False)`) and logs its runtime/stage so it cannot appear silently frozen;
- standalone mode remains the fallback when no usable sibling Konnaxion runtime exists; its control-plane migration runs at most once per Manager session;
- standalone setup can receive an already-detected database URL through inherited environment variables without placing the secret in the PowerShell command line.

## v0.3.3 — one-click Windows Manager bootstrap

On Windows, the normal entry point is now simply:

```text
Konnaxion_World_Manager.pyw
```

If the standalone `.venv` is missing, the Manager automatically launches `SETUP_KONNAXION_WORLDS.ps1` through PowerShell 7 when available (Windows PowerShell fallback), bypasses execution-policy friction for this repository-owned script, streams setup output into the GUI log, and continues loading after setup succeeds. Manual PowerShell bootstrap is still available for diagnostics but is no longer required for normal use.

The Manager also looks for `DATABASE_URL` in the common sibling host checkout `../Konnaxion/backend/.env`. If no PostgreSQL URL can be found, it stays open and asks for the URL in the masked Database field; entering it and pressing **Refresh** continues normally.

## v0.3.2 — provider-accurate capacity + resilient GC

`v0.3.2` hardens the storage path after a real Neon 512 MiB quota run:

- capacity preflight prefers Neon's own relocatable `pg_cluster_size()` metric when available, the same pageserver/timeline size family used by `neon.max_cluster_size`, instead of assuming `pg_database_size(current_database())` is the enforcement value;
- the preflight keeps an explicit safety reserve (`--storage-reserve-mib`, default `32`) on top of the estimated new release schemas, and accounts for local worker concurrency;
- `worlds_storage` shows current-database size, visible PostgreSQL-database size, provider cluster size/source, actual capacity headroom, and reclaimable FAILED/INCOMPLETE/FROZEN release storage;
- `worlds_gc --incomplete` can reclaim non-current BUILDING/VALIDATING releases only when no active `WorldBuildJob` owns them;
- a completed schema/control-plane purge is no longer reported as failed merely because post-commit orphan bridge-user cleanup or audit logging could not write at the provider quota; those housekeeping steps are best-effort warnings;
- build failure bookkeeping and advisory-lock release are fail-safe when a provider closes/poisons a connection after a hard capacity error; the original failure remains visible;
- the World Manager now exposes **GC failed+orphan** and **GC frozen** actions.

For a constrained development database, first reclaim failed/incomplete artifacts, then disposable frozen releases, and only then resume the Universe build:

```text
python manage.py worlds_storage --details
python manage.py worlds_gc --universe levis --failed --incomplete --execute
python manage.py worlds_gc --universe unesco --frozen --execute
python manage.py worlds_gc --universe kristal-farms --frozen --execute
python manage.py worlds_gc --universe cuba-2026 --frozen --execute
python manage.py worlds_storage
python manage.py worlds_apply_universe levis --pack-version 0.5.0 --local-workers 2 --promote
```

The GC never purges a CURRENT release and refuses releases retained by snapshots. Universe promotion remains atomic.

## v0.3.1 — pooled PostgreSQL + storage safety

`v0.3.1` hardens the Universe build orchestrator after real multi-process Neon testing:

- release-scoped migrations now run inside one outer PostgreSQL transaction with `SET LOCAL search_path`, so transaction-pooling proxies cannot move migration statements into the wrong release schema;
- failed DDL no longer masks the original error with `InFailedSqlTransaction` / `TransactionManagementError` while recording job failure;
- local multi-process orchestration stops launching new jobs after a hard database-capacity or schema-collision failure, preserving never-started jobs as `queued` for a later resume;
- queued Universe builds run a storage preflight when the provider exposes `neon.max_cluster_size`; the estimate accounts for the temporary old+new release overlap required by atomic Universe promotion;
- `worlds_storage` reports database usage, provider limit, per-Universe release-schema usage and reclaimable FAILED/FROZEN storage;
- `worlds_gc` safely purges only non-current FAILED/FROZEN releases (dry-run by default); the World Manager adds **Storage** and **GC failed** actions.

Typical constrained-Neon recovery flow:

```text
python manage.py worlds_storage --details
python manage.py worlds_gc --universe levis --failed
python manage.py worlds_gc --universe levis --failed --execute
```

If old FROZEN releases are intentionally disposable and not retained by snapshots/publications, inspect them first and then reclaim them explicitly:

```text
python manage.py worlds_gc --frozen --keep-frozen 0
python manage.py worlds_gc --frozen --keep-frozen 0 --execute
```

The default remains atomic Universe promotion. On a hard provider storage quota, enough free headroom must exist to hold all new target release schemas alongside the currently promoted releases until that final atomic promotion occurs.
