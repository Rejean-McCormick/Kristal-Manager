# UNESCO Thesaurus — active domain classification

**Status (2026-11-23 source):** the Manager and its icon generator use the **UNESCO Thesaurus** as the active subject/domain taxonomy: **7 domains / 88 microthesauri**, from pinned reference data. ISCED-F 2013 is **not** an active alternative classification. Older ISCED declarations/icon filenames are retained as legacy metadata to review, **not** automatically promoted.

Declared mappings are taken from explicit `classification.unesco_thesaurus` (or accepted UNESCO-form metadata) in a workspace; directory names and generic titles do not prove an alignment. Missing/inconsistent maps are classified as `Unmapped`, `Review` or otherwise not evaluated, rather than guessed. An audit exports offline reports without modifying Kristal semantic sources.

**Code references:** `kristal_manager/classification_bridge.py`, `kristal_manager/reference/unesco-thesaurus-baseline.json`, `tests/test_unesco_classification.py`, `tools/icon-generator/UNESCO_THESAURUS_POLICY.md`. This is a local taxonomy/UX change, not a C0 admission or Framework KQ/KP certification.
