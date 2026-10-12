# Konstellation Integration — Local Inventory (Read-only)

**Ownership decision:** Konstellation is the navigator among accessible Kristals and within each Kristal. Manager provides operational inventory; it does not develop a competing semantic explorer.

## Prototype producer

```bash
python -m kristal_manager export /path/to/locals --output private-local-inventory.json
```

Format: `kristal.manager-local-inventory/0.1-candidate`. This is a deliberately **non-normative, local-only candidate** pending joint agreement with the Konstellation owner.

`records[]` contains `title`, `slug`, `state_ref`, `workspace_format`, `native_kind`, `profile`, `readiness`, `state_source`, a **reported** State Commitment, structural artifact count, AI availability flags and explicit statuses `qualification=NOT_ESTABLISHED` and `publication=NOT_ESTABLISHED`.

Absolute `local_path` is **not** present unless the operator explicitly uses `--include-paths`. The file is owner-only (`0600`) on POSIX systems. The names and state IDs themselves can still be sensitive. The producer has no HTTP endpoint; do not serve it unauthenticated or commit it to a public repository.

## Proposed integration sequence

1. Konstellation implements an authenticated policy-first adapter that obtains this metadata through an agreed local boundary.
2. Show an inventory overview with search, facets, provenance and `local` availability. Unknown published status stays unknown.
3. Reconcile GitHub read-surface entries only by exact state identity and pinned logical State Commitment, not by slug alone.
4. Do not mix private and public inventories before applying authorization, including metadata counts.
5. Selecting an entry opens the **existing** Konstellation viewer only if a suitable qualified reader surface exists. Otherwise display a precise `Not ready` reason.
6. Arketype associations are explicit noncanonical annotations, never inferred from file shape.

## Not implemented here

No Konstellation adapter, authentication integration, public synchronization, publication, activation or v9 canonical concept decoding has been added. The Manager exporter is a local producer only.
