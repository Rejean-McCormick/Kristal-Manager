# Kristal

**Current design baseline:** `7.0.0-draft.3.2`

This repository is the single source of truth for the Kristal standard, its machine-readable contracts, TCK vectors, non-normative reference implementation, and repository tooling. It consolidates the former `Kristal-Standard`, `kristal-framework`, and `kristal-reference` repositories.

## Repository boundaries

```text
spec/       normative prose and frozen compatibility specifications
schemas/    canonical active v6/v7 JSON Schemas
tck/        normative conformance vectors and invalid/golden fixtures
examples/   non-normative examples
reference/  non-normative reference implementation(s)
tools/      repository and release tooling
contracts/  release/contract manifests and historical bundle pins
history/    status records and release history
compat/     frozen materialization needed only by legacy compatibility tests
```

The rule is simple: **the specification and TCK define behavior; reference code demonstrates behavior.** Reference code is never normative by itself.

## Current architecture

Kristal v7 remains additive above the unchanged portable `kristal_state/6.0` contract. `Kristal` is the portable unit and `Kristall` is the v7 meta-orchestration layer. The current v7 baseline also includes semantic identity, Mesh, assertion families, KOS/TOC, axis types, orientation axes, semantic resonance, Surfaces/projections, and crystallization contracts.

For Interaction Kernel deployments, **DaaT** (`daat`) is an optional external admission and explicit contract-mapping boundary. DaaT is not a source store, corpus-normalization authority, or Kristall semantic authority; Kristal/Kristall remains independently conformant without it.

## Validate the repository

```bash
python tools/validate_all.py
```

Reference implementation only:

```bash
cd reference/js
npm test
```

## Old repository mapping

- `Kristal-Standard` → `spec/`, `schemas/`, `tck/`, `examples/`, `history/`
- `kristal-framework` → useful TCK/release tooling migrated into `tools/` and `contracts/`; duplicated docs/contracts removed
- `kristal-reference` → `reference/js/`

See [MIGRATION.md](MIGRATION.md) for the detailed mapping.
