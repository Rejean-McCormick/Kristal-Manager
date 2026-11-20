# Théophile → Konstellation → SemantiK test kit

Generated from the uploaded corpus `corpus-catholique-theophile-v0.2.1`.

Contents:
- `theophile-konstellation.pack.json`: normalized Konstellation pack
- `lenses/theophile-catholic-authors.json`
- `lenses/theophile-position-network.json`
- `run_theophile_konstellation_semantik_test.ps1`

Projection counts:
- entities: 795
- assertions: 528
- sources: 138
- relations: 15

The projection preserves:
- original assertion status/certainty/validation metadata
- source references
- all statement qualifiers
- full original assertion under `upstreamPayload`

The test validates the real integration contract:
corpus -> Konstellation engine -> CommunicationRequest -> SemantiK Architect request validator.

It intentionally does not claim a real GF realization. Rendering requires a published
`konstellation-explorer-2` RuntimeSet with a real PGF for structured realization. Existing `live/` profile-1 files are retained as historical evidence of the first end-to-end run.
