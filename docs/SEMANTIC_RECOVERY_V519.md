# V5.19 — Local lexical recovery (private evidence)

V5.18 remains the authoritative derived active view, not a factual certification.
V5.19 rebuilds V5.16/V5.18, freezes and verifies their active source pins, then
copies the private SQLite database and appends separate recovery tables. It
never modifies a crosswalk, canonical registry, graph, catalog or active profile.

Inputs: historical JSON/JSONL dictionaries under canon or .kristal/v11,
legacy .kristal/v8 lexicons, and local Wikidata entity caches. Exact owner,
namespace and KQ/KP are required. Cached Q/P records require an existing active
accepted exactMatch. No word-based joins, translations, or cross-owner merges.
Each observation keeps source path, SHA-256, locator, row, aliases, description
and source assurance if available. A local hash is not source authentication.
Missing or contradictory entries are never made canonical. The active term
always wins. Legacy identifiers are recorded separately, without inferred links.

SQLite tables: recovery_source, recovery_evidence, recovery_resolution,
recovery_legacy, recovery_profile_review. View recovery_lookup separates
ACTIVE_CANONICAL and UNREVIEWED_CONSENSUS. Conflicts remain visible in
recovery_resolution. Use namespace_id + semantic_id as identity key.

Example query (read-only):

```sql
SELECT * FROM recovery_lookup WHERE namespace_id = ? AND semantic_id = ?;
SELECT * FROM recovery_evidence WHERE namespace_id = ? AND semantic_id = ?;
```

Coverage counts use KQ/KP as lexical denominator; KA/KS remain indexed, not
label targets. The 14 diK target locales are en fr es de nl sv da no nn fi et af it pt.
The report also records other observed locales without translation.

Recovery is not canonical promotion. The examined source catalogs explicitly
report unverified extraction checksums; no automatic promotion is authorized.
Missing V11 profiles require a qualified native conversion, not fabricated graphs.
No C1/C2/C3, Git push or public writes. Stop on a changed canonical source.
