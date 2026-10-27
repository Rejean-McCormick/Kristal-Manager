# Alpha.15 local validation

56 focused tests passed: content scanner, recovery, Discovery adapter, operational v10 checks and C2 gate. The historical `tests/test_core.py` synchronization compatibility suite remains unresolved and was not claimed passing or removed.

Real collection: 16 active structured-v11 workspaces, 53 948 assertions, 29 304 identified Wikidata source claims, 14 157 value components. All 293 audited selected source files remained byte-identical. A repeated scan reused all 16 entries. SQLite full integrity checking passed before packaging and on the packaged copy. Counts describe selected recognized content; no factual or Framework qualification is implied.

The generated HTML was executed in a DOM test: 16 cards, text filtering, native-key display and empty state passed. Windows/Tkinter interaction and browser visual rendering were not manually tested in this environment.

........................................................                 [100%]
56 passed in 1.39s

{
  "projects": 16,
  "metrics": {
    "assertions": 53948,
    "main_assertions": 39791,
    "structured_components": 14157,
    "wikidata_source_claims": 29304,
    "entities": 17851,
    "properties": 5700
  },
  "all_active_graphs_observed": true,
  "audited_source_files_unchanged": 293,
  "full_scan_seconds": 7.9975572390003435,
  "unchanged_scan_seconds": 0.736668532999829,
  "cached_workspaces": 16,
  "sqlite_full_integrity_check": "passed",
  "atomic_snapshot": true,
  "scan_output_is_derived": true,
  "factual_or_framework_qualification_performed": false
}
