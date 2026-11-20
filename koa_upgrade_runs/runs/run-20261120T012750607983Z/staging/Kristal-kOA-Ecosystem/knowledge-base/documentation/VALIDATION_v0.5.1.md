> **SUPERSEDED BY v0.6.0:** the Pi-Theory → MathChallenges path interpretation in this historical validation note was incorrect and is retained only for package history.

# Validation — v0.5.1

Validation date: 2026-10-03.

## Repository evidence QA

- 64 current local repository paths represented (62 README-backed + Korpus index-only + Pi-Theory owner path correction).
- 62 repositories have one or more root README files in the supplied collection.
- `Korpus` is represented from index-only evidence because its root README is missing.
- Current and historical repository observations are separated; absence from the local snapshot is not interpreted as deletion.
- 102 source-registry entries are unique.
- No dangling `source_refs` were detected across the editorial knowledge sources.

## Kristal build validation

`knowledge-base/tools/build.py` and `knowledge-base/tools/validate.py` complete successfully.

Final model counts before packaging:

- components: 109
- repositories: 96
- artifacts: 48
- external references: 38
- capabilities: 75
- operating functions: 11
- relations: 2405
- scenario archetypes: 36
- scenario mosaic entries retained: 120

The scenario corpus is intentionally not rewritten from README prose alone. Scenario Mosaic V2's current 36-problem repository description is recorded separately from the retained historical 120-scenario corpus.
