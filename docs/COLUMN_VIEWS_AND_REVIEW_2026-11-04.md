# Unified Kristal Manager / Analysis Center column views (2026-11-04)

Both interfaces share five English-language presentations of the same underlying inventory:

- **Essential**: the Kristal's *workspace title*, readable ARK/PRF/UNESCO declarations, semantic role, and the relevant status.
- **Classification**: declared categories, the UNESCO editorial review, and new scan proposals where available.
- **Semantic review**: individual AI semantic role, exploratory PRF refinement, UNESCO contradictions, and historical evidence status.
- **Diagnostics**: structural state, local technical profile/diagnostic status, evidence and identifiers.
- **All columns**: all available table fields, with horizontal scrolling.

`Choose columns…` allows session-level customization; the chosen layout is saved in Manager's *local UI preferences* (outside scanned Kristal folders). All information remains available through the JSON/details panels even when a table column is hidden.

## Source distinctions and limits

- **Current workspace declaration** is read from the original `kristal.workspace.json`. The UI uses the `title` field, not a `Kristal-` folder prefix, and resolves ARK, PRF, and UNESCO IDs into existing English dictionary labels without changing the codes.
- **AI semantic role / PRF alternative** is an editorial draft from the 127 historic dossiers, shown only when current semantic descriptors match its basis digest. The seven PRF alternatives carry low confidence and require expert review.
- **UNESCO editorial triage** is a dated draft based on the 17 recorded contradictions. It is shown only if the current identity, declared UNESCO codes and the current proposed subject all match the archived observation. A mismatch never overwrites declared UNESCO categories; no newly inferred subject is considered approved.
- **Arketype review register** is a separate record (including 14 linked reviews, possibly with changed anchors). Historical structural observations are not qualifications.
- **Native contracts and Framework levels**: recognizing a native contract does not evaluate KQ/KP semantics or establish C1/C2/C3.

The GUI, report exports, CSV, and editorial HTML remain read-only with respect to scanned Kristals. No GitHub operation, publication, migration, canonical metadata edit or automatic approval is performed by this update.

## 2026-11-05 extension

A sixth shared preset, **Review queue**, and the **Review focus** filter are available in both windows. New read-only columns show a work-queue stage, the next suggested review action, and the state of native-source evidence. See `docs/REVIEW_QUEUE_AND_NATIVE_EVIDENCE_2026-11-05.md`. Source SHA matching is never a semantic approval.
