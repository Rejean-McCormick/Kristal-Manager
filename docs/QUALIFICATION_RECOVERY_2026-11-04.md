# Recovered Kristal qualification evidence — 2026-11-04

Scope: Kristal-Manager only. The source Kristals, canonical graphs, existing review registry, and publication gates must not be changed by this overlay.

## What was found

`QUALIFICATIONS_FOUND_20261104-093521.zip` indexes 1,133 report-like files (the search stopped when traversal reached 35,000 entries). It contains selected copies of 45 reports and snapshots of 127 current workspace metadata files. This recovery uses four specific sources whose SHA-256 values are embedded in `data/recovered_qualification_evidence_2026-11-04.json`:

- 127 current workspace metadata snapshots (collected 2026-11-04).
- `RAPPORT_ARKETYPE_STRUCTURE.json`: 127 prior structural observations, 2026-10-31.
- `CHAMPS-127-COMPLETS.json`: 127 audits of 30 fields, 2026-11-02.
- `RESULTATS-PRF-127.csv`: 127 PRF batch rows, 2026-10-31.

The metadata snapshots declare 127 primary ARKs and 127 PRF classifications. **96 PRF values are `PRF-20`, marked generic and requiring refinement.** Each source is treated as declared or historical evidence, not as a human sign-off. The historic Arketype scores are three-facet structural hints, not normative compatibility grades. The UNESCO metadata is project-level, local/noncanonical mapping; it cannot establish exact concept identity.

## Interface and reports

In **Global analysis…** → **Scan and analyze Kristals**, the table now shows **Declared ARK**, **Declared PRF**, **Subject domain**, **Declared UNESCO**, and **ARK structure (historic)**. The separate **Local review register** and **New scan proposals** columns prevent confusion between past declarations, human decisions, and new proposals. Double-click a row for its original status, source hashes, structural evidence, earlier PRF batch, and historical field coverage. The ChatGPT copy format and CSV now include declared classification fields.

Live `kristal.workspace.json` files are read **without modification** and matched by `state_ref` to the scan. When current metadata is unavailable, the table explicitly labels recovered values **(old snapshot)**. If the live `state_ref` disagrees, recovered values are not substituted. Previously saved global reports are only augmented in memory for display, never overwritten.

`READY` and workspace `status: validated` are not a semantic qualification; `C1/C2/C3`, Arketype human endorsement and UNESCO concept validation remain separate. Old PRF-20 classifications require targeted human/AI semantic review, not mass inference.

## Separate issue

The user's most recent scan reported 126 `LOCAL_DISCOVERY_STALE` / `LOCAL_DISCOVERY_INCOMPLETE` warnings when **Also verify registered files** was enabled. These arise from Discovery integrity checks and **are not resolved by this qualification display overlay**. They should be investigated separately, preserving source fingerprints and canonical content.
