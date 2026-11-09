# AI semantic dossiers — editorial review (2026-11-04)

## Scope

This local, read-only Manager enhancement displays **127 individualized semantic purpose
statements** derived from already-recovered workspace descriptors and historical
Arketype/PRF summaries. It does **not** independently inspect all canonical payloads.
It is a comprehensive editorial first pass, **not** 127 approved qualifications.

The 21 existing PRF usage profiles are narrow and non-normative; in many projects
`PRF-20 (Multi-Purpose Semantic Reference)` remains more accurate than forcing a
mismatched specialist label. **Seven** low-confidence alternative profiles are
identified for human review, without modifying any current PRF assignment.

## Where to find it

In **Global analysis… → Scan and analyze Kristals**, use:

- **Semantic role (AI draft)** and **PRF refinement (AI draft)** table columns.
- Double-click a Kristal for its role, purpose, evidence boundary and full
  underlying data; the new introduction is fully English.
- Click **Open AI semantic dossiers** for a browser-readable 127-project report.
- In the latest `rapports/analyse-*` folder, find:
  `ai_semantic_review_127.html`, `ai_semantic_review_127.csv`,
  `ai_semantic_review_127.json` and `tableau_global.csv`.

## Provenance and validity

The bundled `data/ai_semantic_review_127_2026-11-04.json` carries identities,
source hashes, per-record semantic descriptor fingerprints, evidence excerpts,
English editorial summaries and caveats.

On each scan Manager joins by exact `state_ref` to the existing live workspace
metadata, then checks the fingerprint of six semantic descriptor fields
(ARK, PRF, subject domain/orientation and native model kind/description).
Changes to the display title alone do not invalidate the dossier. If the
semantic descriptor changes, Manager shows **Needs semantic review** instead of
presenting a historical draft as current. Absent/symlinked/mismatched live
metadata does not count as current evidence.

Raw `classification.primary_usage`, `primary_archetype`, UNESCO microthesauri,
canonical graphs and the `kristal.workspace.json` files are not modified.
A proposed PRF is not a human approval; an AI role is not C1/C2/C3 qualification.
Any eventual approved metadata write needs a distinct authority and explicit
review, outside this overlay.

## Important limits

- Only project-level metadata and historical summary evidence was available in
  the retrieved report ZIP; source payloads were not included.
- `Declared` and `AI draft` are separate fields, never merged.
- Discovery 3.3 integrity checks and the 13 deliberately blocked legacy
  publication/sync tests are separate from this enrichment.
