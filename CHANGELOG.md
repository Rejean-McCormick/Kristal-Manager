## Identité visuelle — 2026-10-27

- Logo SVG fourni par l’utilisateur intégré au GUI Tkinter (en-tête et icône de fenêtre).
- Couleur officielle #1E6864 appliquée aux contrôles principaux, à la sélection et aux titres.
- Logo embarqué sans accès réseau dans le lecteur HTML et dans les aperçus HTML de catalogue.
- Ressources PNG/ICO pré-rendues, aucune dépendance graphique nouvelle à l’exécution.

# Changelog

## Refonte locale de l’interface — 2026-10-27 (sur base alpha.15)

- Priorité au chemin `C:\mycode\Kristal\locals` sur Windows, avec dernier dossier valide mémorisé hors des sources.
- Interface française unifiée : parcours dossier → sélection → contrôle → catalogue, menus accessibles et contexte préservé.
- Journal dédié avec Copier, Effacer et Enregistrer ; détails JSON copiables, recherche, indicateurs et navigation guidée.
- Distinguer le catalogue du cristal choisi du catalogue global, sans scan implicite des autres cristaux.
- Fix Windows pour la synchronisation du fichier SQLite temporaire (`r+b` au lieu de `rb`).
- Aucun élargissement des autorisations ou capacités de publication/synchronisation.


## 0.1.0-alpha.15 — Read-only content catalogue (2026-10-26)

- Add an incremental SQLite catalogue of selected v11 content and recognized v6 native assertions, retaining provenance, semantic identity scope, multilingual terms, and explicit partial/unsupported states.
- Add content CLI/GUI actions and a local HTML summary viewer; operational inventory and Konstellation disclosure formats remain unchanged.
- Separate source claims, value components, reported Wikidata ranks and candidate alignments; no editorial or factual authority is inferred.
- Prune generated/source-snapshot directories during content discovery, hash only selected inputs, and refuse output inside source Kristals.
- Add scanner regressions and a worked 16-Kristal example. Existing synchronization/publication recovery limitations remain.

## 0.1.0-alpha.14 — Operational verification / Framework v10 pin (2026-10-16)

- Add read-only `verify` and bulk `--verify-sources` to detect stale physical reader inventories, retaining legacy Discovery-absent support.
- Keep structural readiness, advisory Discovery, pinned Framework state-verification, qualification, publication and access as distinct evidence classes.
- Allow explicit execution of a *trusted* Framework 10.0.0-draft.3.2 reference (contract-set SHA pinned) for v9 semantic State Commitment checking; no bundled external code.
- Replace misleading cached structural `VALID` reports with fresh scoped statuses (the historical alpha.11 expectation is intentionally obsolete).
- Add a local GUI Verify selected action, regression tests and Catho integration evidence.
- Keep sync/publication/activation blocked and leave canonical inputs unchanged.


## 0.1.0-alpha.13 — Kit 3.3 discovery + local KNAV adapter (2026-10-13)

- Consume the three Kit 3.3 noncanonical Discovery/reader files with fail-closed consistency checks.
- Add optional byte-level registered-source verification, with explicit unverified status by default.
- Add a strict, opt-in local Konstellation preview export with operator-chosen principal and no inferred permissions.
- Display Discovery metadata in the local GUI; keep existing scan/readiness and blocked sync.
- Archive the stale root snapshot index; add an optional SHA-pinned local cleanup GUI.
- Update docs, tests, and package inventory without enabling C2/C3/C4 operations.


## 0.1.0-alpha.12 — Local Inventory Recovery (2026-10-12)

- Added the previously missing `kristal_manager` package as a **restricted recovery implementation**.
- Implemented local discovery, v9 state source/legacy/conflict inspection, read-only GUI and CLI.
- Added candidate local-only inventory JSON for future authorized Konstellation integration.
- Included the Bootstrap C2 verifier and preserved the historical tests.
- Explicitly disabled GitHub sync, migration, full backup and public mutation because their original backend was not present in the provided source.
- Rewrote the project documentation in English and documented unresolved E2E obligations.

## 0.1.0-alpha.11 (historical source contract)

- Historical docs and tests describe exact Authoring Kit read-surface synchronization and C2 gates; the corresponding runtime source was absent from the available snapshot. That historical functionality is **not** represented as operational in alpha.12.
