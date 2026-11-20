# AI START HERE — Portable Kristal

You are reading a **self-contained Kristal knowledge package**.

For reading and answering questions about this package, **do not require GitHub, network access, Python, Node, or Kristal tooling**. Those may have been used upstream to author, qualify, or publish the Kristal, but they are not part of the reading contract.

## Read in this order

1. `AI_MANIFEST.json` — package identity, exact State Snapshot, and machine-readable navigation.
2. `ai/CONTEXT.md` — compact orientation compiled from the authored Kristal documentation.
3. `ai/COVERAGE.json` — owned scope, exclusions, external pinned references, and limitations.
4. `ai/GLOSSARY.md` — project terminology when authored.
5. `ai/INDEX.json` — deterministic file index with roles and SHA-256 digests.
6. `canon/state.index.json` and relevant files under `canon/` — canonical logical content.
7. `sources/source-catalog.json` and `sources/` — provenance/evidence when needed.
8. `state/state-snapshot.json` — the exact Kristal v9 State Snapshot represented by this package.

## Interpretation rules

- Treat `canon/` as canonical content and `state/state-snapshot.json` as the exact semantic state declaration.
- Treat `ai/` as a **derived read model**. It helps navigation but is never a source of truth by itself.
- Do not invent missing facts, provenance, authority, definitions, or relationships.
- A missing claim is not automatically false. Check `ai/COVERAGE.json` before drawing negative conclusions.
- Preserve uncertainty and conflicts explicitly declared by the Kristal.
- AI-generated answers are not automatically part of the Kristal canon.
- When practical, mention the source file(s) used for an answer.

## Offline guarantee

This read layer is designed so an AI can understand the supplied folder/ZIP from the files inside it alone. If `AI_MANIFEST.json.external_dependencies` is non-empty, those are pinned semantic references that may add context, but the local package remains readable without contacting GitHub.
