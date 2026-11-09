# Unified authoring status & source-provenance observations (2026-11-05)

This Manager patch is based on the operator snapshots made on 2026-11-05:
Manager 15:35, Authoring Kit 15:49, Arketype/KristalDiag 15:48, and current `locals(1).zip`.
It never invokes Diag or changes canonical commitments, assertions, state identity,
PRF/ARK/UNESCO declarations, status, C1/C2/C3 decisions, release or network publication.

## Unified views

Both `Kristal Manager` and `Global Analysis Center` expose two new columns in
`Essential`, `Review queue` and `Diagnostics`:
- **Authoring status (not qualification)** is read from current `kristal.workspace.json`.
  `validated` is a **local workspace label**, not independent qualification.
- **Source catalogue (unverified)** is the count and basic schema / locator shape
  of `sources/source-catalog.json`. No external URL is contacted or trusted.

The shared Review focus adds `Authoring in progress` (currently 7),
`Source catalogue issues` and `Workspace metadata updated`. The 7 existing
AI release-gate notes are observation-only. A present AI editorial dossier is
not a human approval. The local CSV and global report export the new evidence.

## Metadata-only corrections

The current snapshot contains exactly two workspace metadata changes since the
2026-11-05 source-review archive: K Monetary System and Pi Theory Prime Bridge.
Their two native documents still match the archived SHA-256; the archival
workspace metadata hash no longer does. This is explicitly
`WORKSPACE_METADATA_CHANGED`, **not** `SOURCE_BYTES_MATCHED`. Further semantic
review of changed metadata may still be necessary.

## 11 source catalogues

The accompanying optional local-Kristal patch adds or repairs **152 locators/
required fields** across 11 noncanonical provenance catalogues. It repairs 122
ScolQc entries against the 122 IDs in its actual native documentary catalog,
4 embedded editorial sources with no external URL, 15 Earth URLs copied from
existing historical source records, and 11 more unresolved bibliographic/editorial
locators. Nothing is looked up or claimed current online. Exactly 2 catalogs
(HomeCare and Technology) remain empty with explicitly pending provenance.

Kit `schemas/source-catalog.schema.json` reports 127/127 catalogues shaped
correctly after the patch. This checks schema shape only; recorded publisher,
provenance, license, reachability, evidence scope and factual assertions still
require independent checking. Source changes may cause existing Discovery
fingerprints to become stale until re-derived with the compatible Kit.

## Boundaries

No automatic state promotion: 120 `validated` local labels and 7 `building`.
No automatic classification approval, no fabricated citations or URLs, and no
new C1/C2/C3 certification. Native-document matches mean exact source bytes,
not truth. The installer backs up noncanonical source catalogues and Manager
files and refuses to overwrite locally modified files.
