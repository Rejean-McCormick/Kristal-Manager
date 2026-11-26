# V5.17 — Accepted-precedence canonical evolution, local-first

The Authoring Kit owns this narrowly bounded canonical change. Manager's
V5.14 multi-revision index and V5.15 review continue to record all historical
data. V5.16 active projections are rebuilt automatically after Kit V5.17
completes, so readers see the new selected crosswalk without guessing which
historical revision is active.

Only source-recorded, evidence-backed accepted exactMatch mappings are used
as a precedence signal. Other candidate QIDs for the same scoped identity
become `superseded` in a NEW registered crosswalk; the original remains
immutable. No additional Wikidata equivalence is approved by the operation.

The new helper is `Kristal-Authoring-Kit/tools/v517_accepted_precedence.py`.
The single PowerShell 7 runner in kOA Digital Ecosystem applies it locally and
then refreshes the derived V5.16 dictionary. Individual run reports and any
interruption details are retained under `%LOCALAPPDATA%\Kristal`.

No canonical file is repaired in `kristal-public`. GitHub sync, publication,
independent qualification, and runtime activation remain out of scope.
