# Canonical and derived surfaces

## Canonical domain artifact

`knowledge-base/corpus/koa-ecosystem.kristal-state.json` is the registered canonical domain state. Its existing v9 Logical Artifact is:

- artifact: `urn:kristal:koa-ecosystem:artifact:canonical-state`
- contract: `koa-ecosystem.canonical-knowledge-state/1.0`
- commitment: `sha256:8d5195171697739485ada83e69b8fae83fe95cda155d5181a8d61dff4cc40a74`

The file remains at its legacy path so the existing project builder and validations keep working without a semantic rewrite. `canon/state.index.json` is the Local Kit 3.2.2 registry for that artifact.

## Authoring/build inputs

`knowledge-base/sources/` contains editorial catalogs and the project-specific source registry used by the native builder. They are not silently promoted to additional v9 State Snapshot members.

## Derived/rebuildable surfaces

- `knowledge-base/corpus/index.json` — query/index surface.
- `.kristal/v8/` — legacy read/query models.
- `views/` — generated navigational views and matrices.
- `build/v9/` — Local Kit 3.2.2 build candidate.
- `.kristal/v9/` — retained legacy v9 compatibility/migration envelope.
- `runtime/`, `derived/`, `projections/materialized/`, `state/` — reconstructible surfaces when used.

Generated surfaces must never be edited as a shortcut for changing canonical knowledge.
