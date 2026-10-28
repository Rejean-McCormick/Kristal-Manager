# Architecture

KristalDiag is an **external, independent, read-only examiner**.

```text
Framework / Local Kristal / GitHub collection / publication bundle
                    │
                    ▼ read only
               KristalDiag
                    │
                    ▼
          qualification evidence
```

It is deliberately outside the lifecycle ownership chain:

```text
Kristal Local Kit        -> local authoring + v9/AI read-surface construction
Kristal Manager          -> local inventory + validation orchestration + GitHub sync
Kristal GitHub Setup     -> hosted network bootstrap + qualify/publish/activate
Kompiler                 -> optional read-only context compilation
KristalDiag              -> independent examination only
```

## Examiner independence

The target's own `schemas/` are inventory/audit evidence, not the schemas used to qualify that target. SchemaStore uses frozen packaged examiner contracts. The exact examiner resources are protected by `contract-manifest.json`.

V9 commitments are recomputed by the Python implementation in `kristaldiag/v9.py`. V10 publication identity, publication-bundle byte bindings, GitHub read-surface digests and collection-index digests are independently recomputed by `kristaldiag/v10.py`.

## v10 boundary

KristalDiag enforces the architectural split:

```text
SEMANTIC STATE != HOSTING != PUBLICATION LOCATION != DISCOVERY DIRECTORY != AI READ SURFACE
```

A host move, sync operation, repository visibility change or rebuilt AI/read surface is not a semantic revision. A collection index is derived discovery, not semantic authority. Publication binds exact state identity plus retrievable bytes; activation remains a distinct lifecycle decision.

## Draft.3 GitHub collection examination

When present, K29 independently verifies:

- `kristal.github-read-surface/1.0` documents;
- `.kristal/sync-manifest.json` using `kristal.github-sync-manifest/1.0`;
- `kristals/index.json` using `kristal.github-collection-index/1.0`;
- exact hosted file sizes and SHA-256 digests;
- the v9 State Commitment bound by the hosted surface;
- `AI_MANIFEST.json` and `ai/INDEX.json` coherence;
- absence of unmanaged files in an exact Manager-owned subtree.

Large collection subtrees are byte-verified with bounded parallel workers. KristalDiag remains read-only.

## Scheduling and evidence

Levels normally execute in isolated Python worker processes under bounded timeouts. The parent runner fingerprints the target before/after and emits an evidence manifest covering every result artifact.
