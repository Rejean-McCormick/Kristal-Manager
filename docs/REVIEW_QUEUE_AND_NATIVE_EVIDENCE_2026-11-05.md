# Kristal Manager — Unified Review Queue (2026-11-05)

This noncanonical Manager upgrade is based on the operator's `znapshot_Kristal-Manager_11051441.zip` and the existing 2026-11-05 native-source AI review. It **only changes Manager**.

## Both desktop windows

**Kristal Manager** and **Analysis Center** have the same additional column profile, **Review queue**, and a shared **Review focus** filter. The filter can show structural issues, changed native evidence, stale AI descriptors, UNESCO disagreements, PRF alternatives, and native contracts (where a native contract has actually been observed by Analysis Center).

New columns:
- `Review stage (not approval)` — a deterministic work-queue label for the current observation, **not** a maturity grade or C1/C2/C3 level.
- `Next review action` — proposed operator action, never an automated repair.
- `Native-source evidence` — current SHA-256 comparisons with the archival analysis's two native source documents and workspace metadata.

The main Manager display can flag 17 *historical* UNESCO suggestion disagreements only when **the current state identity and exact declared subject codes still match** the dated editorial observations. The label says *Historical suggestion disputed*, distinguishing it from a new scan proposal. The seven exploratory PRF suggestions remain AI drafts and are never written to canonical tags.

## Source integrity and provenance

The bundled catalogue `data/ai_native_source_review_127_2026-11-05.json` is AI editorial evidence, not authoritative qualification. Current local source files are compared against their archived SHA-256 fingerprints. A mismatch produces `Sources changed — review again`; Manager never treats a changed file as still reviewed.

`SOURCE_BYTES_MATCHED` means **only** that the bytes matched the documents used for the archived review. It does *not* verify the underlying assertions, approve the PRF/ARK/UNESCO taxonomy, authorize publication, or establish a Framework C1/C2/C3 level. In the event of a missing catalogue, symlink, malformed identity, missing document or unsafe path, the result fails closed to an unverified status.

## Review queue CSV

Both windows offer **Export review queue CSV…**, a local file selected by the operator. The global scan also produces `review_queue.csv` alongside `tableau_global.csv`, outside the scanned source tree. Exports are never allowed to overwrite an existing file or write under the scanned root, and spreadsheet formula prefixes are escaped.

## Retained boundaries

No Kristal files, canonical state, source registries, review approvals, Framework levels, Git services or publication settings are written by these features. An existing locally approved Arketype review remains a separate datum, not a general qualification verdict. Do not clear Discovery warnings by forging fingerprints. The old blocked publication backend stays blocked.
