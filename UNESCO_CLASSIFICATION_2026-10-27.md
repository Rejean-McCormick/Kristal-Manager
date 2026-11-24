# UNESCO classification audit — historical note updated

The original 27 October note described an earlier comparison of the UNESCO Thesaurus and ISCED-F fields. **That comparison is superseded for active domain classifications** by the 28 October [UNESCO consolidation](UNESCO_CONSOLIDATION_2026-10-28.md): UNESCO Thesaurus alone is active (7 domains, 88 microthesauri).

From the Manager GUI, **Actions → UNESCO classification audit…** provides a descriptive, offline review/export. Review missing, inconsistent and legacy icon classifications; do not infer an UNESCO mapping from an ISCED value, title, or folder name. Audit output does not modify the source Kristals.

**Source and test pointers:** `kristal_manager/classification_bridge.py`, `tests/test_unesco_classification.py`, `docs/CLASSIFICATION_LABELS_EN_2026-11-04.md`. This document restores a missing entry-point guide; it does not claim independent GUI qualification on this machine.
