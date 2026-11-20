# Kompiler

Kompiler is a local-first **context compiler** for LLMs and Kristal/Kristall knowledge systems.

**Runtime:** `0.5.0`  
**Kristal alignment:** `7.0.0-draft.3.2` / portable `kristal_state/6.0`  
**Claimed profile:** `V7-Projection`

## What Kompiler owns

Kompiler accepts a declarative Query Plan, performs trusted read-only adapter queries, normalizes heterogeneous **query outputs**, assembles a task-specific context graph, preserves conflicts/provenance, applies ranking/diversity/budgets, and emits a bounded Context Pack.

```text
Kristal / Kristall read surfaces
          │
          ▼
       Kompiler
 query → read → normalize output shape → merge/context graph → budget
          │
          ▼
   kompiler.context-pack
```

Here, **normalization means normalization of adapter output shape**. It does not mean crawling, cleaning, deduplicating, or canonically storing an external source corpus.

## Ecosystem boundaries

- **Médiathèque kOA** owns persistent source bytes, snapshots, physical representations, hashes, rights and source locators.
- **DaaT** (machine id `daat`) is an optional external Interaction Kernel admission/contract-mapping boundary toward Kristal. DaaT is not a Kompiler stage.
- **Kristal/Kristall** owns portable epistemic artifacts plus KQ/KP/KA/KS identity, Mesh, axes, registries and crystallization.
- **Kompiler** is read-only with respect to those authorities. It never mints Kristall semantic identity and never becomes a source store.

Legacy direct `source-catalog/` reads have been removed from built-in discovery. Source catalogs must first be represented through the proper source/knowledge authority before Kompiler consumes them.

See `docs/01-architecture/ecosystem-boundaries.md`.

## Contract ownership

Kompiler does not vendor Kristal Standard schemas, normative documentation, official examples or TCK vectors. The canonical source is the external `kristal` repository/release. Configure it with:

```bash
export KOMPILER_KRISTAL_STANDARD_ROOT=/path/to/kristal
```

or `[kristal_standard].root` in `kompiler.toml`. `src/kompiler/kristal-standard.lock.json` pins the accepted Standard release and contract-set hash.

Kompiler owns only its own protocol schemas (`kompiler.query`, capabilities, Context Pack, error) plus application/runtime code.

## v7 support

The native Kristall adapter reads the external Standard schemas dynamically and supports entities, Mesh, assertion families, resonance, projection recipes, Axis Types, KOS and TOC registries. Surfaces remain deterministic and resonance/path semantics are never promoted into identity or truth.

The v6 portable state adapter validates and reads `kristal_state/6.0` without rewriting the source artifact or replacing its declared `state_id`.

## Validation

```bash
KOMPILER_KRISTAL_STANDARD_ROOT=../kristal python -m pytest
```

Without the external Kristal dependency, Kompiler-owned tests still run and cross-repo Kristal integration tests are skipped.

See `docs/` for architecture, protocol and operator details.
