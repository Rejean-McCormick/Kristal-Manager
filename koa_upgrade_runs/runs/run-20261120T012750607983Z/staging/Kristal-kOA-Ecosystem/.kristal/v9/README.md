# Kristal-kOA-Ecosystem — Kristal v9 package

Standard target: `9.0.0-draft.1`. Domain content version remains `0.6.3`.

This directory adds an **additive Semantic State Architecture envelope** around the existing repository. It does not replace the domain canon or the inherited v8 read/query package.

## Logical boundary

- canonical state: `knowledge-base/corpus/koa-ecosystem.kristal-state.json`
- editorial/build input bundle: `18` JSON component(s)
- non-canonical companion/read-model surfaces remain outside the State Snapshot

## V9 files

- `state-snapshot.json` — immutable logical composition
- `artifacts/` — logical artifacts and commitments
- `materializations/` — physical mappings and blob digests
- `derivation.json` — build/adoption lineage
- `exchange.json` — portable exchange manifest
- `activation.json` — reference channel pointer
- `capabilities.json` — v9 capability descriptor
- `package.json` — package index
- `migration-report.json` — migration decisions

`BUILD != PUBLISH != ACTIVATE`; indexes and caches are not canonical authority.

## kOA-specific preservation

The heterogeneous ecosystem/property graph remains canonical as the existing v6 state. Repository/evidence discovery, authority, ownership, scenario and deployment distinctions are preserved. The builder now emits RFC 8785/JCS v6 identity and accepts `KRISTAL_BUILD_TIMESTAMP` for reproducible builds.

## Validation autonome

```bash
python .kristal/v9/validate.py
```

Ce check vérifie les commitments, bindings de matérialisation, digests physiques, Exchange, Activation et le manifest v9 sans dépendance externe.
