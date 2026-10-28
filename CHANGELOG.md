## Intégration des icônes sur Manager 19 h 24 — 2026-10-27

- Portage ciblé du lecteur de `desktop.ini`, profils .kristal et icônes Registry en lecture seule.
- Colonne des icônes avec miniatures, état de provenance, commande d’actualisation et d’information.
- Générateur Windows 2.5.0 fourni à l’identique, ouvert seulement après confirmation.
- Préservation de KristalDiag, des catégories, des archives, du renommage contrôlé et des exports 19 h 24.
- Assets du logo SVG et PNG/ICO restaurés, palette de marque #1E6864 conservée.

## 2026-10-27 — Catégories, snapshots et exports locaux (refonte expérimentale)

- Terminologie de l'interface : « Kristal » / « Kristals », jamais « cristal ».
- Catégorie lue depuis la classification Discovery si présente, sinon depuis le domaine/genre déclaré dans `kristal.workspace.json` ; filtre, colonne et tri au clic.
- Les snapshots historiques imbriqués (ex. `archive/original-snapshot-before-activation`) sont identifiés et masqués par défaut, mais jamais supprimés. Ils ne sont plus comptés comme Kristals principaux.
- Nouveau menu contextuel « Organiser / exporter » : prévisualisation du dossier renommé depuis `title` ou `slug` interne, confirmation obligatoire, détection de collision, restriction aux sous-dossiers directs de `locals`.
- Export intégral en `.zip`, et en `.kristal` (conteneur ZIP avec manifeste Manager **expérimental**, distinct de tout format Framework officiel), avec contrôle CRC et création sans écrasement.
- Préservation des dossiers vides ; blocage des liens symboliques, fichiers supérieurs à 4 Gio et exports dans le dossier source.
- Boutons, logo SVG fourni et palette #1E6864 préservés.
- Tests d'organisation, sécurité, GUI et essais de l'archive réelle `Kristal-Architecture` ajoutés.

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

## 2026-10-27 — Pont KristalDiag externe expérimental

- Configuration d'un programme de diagnostic externe local (.exe/.py/.js/.mjs) avec arguments explicites (`{workspace}`, `{report}`), sans shell.
- Nouvelle commande pour diagnostiquer le Kristal principal sélectionné, après confirmation de confiance.
- Nouvelle colonne KristalDiag et présence du diagnostic observé dans la fiche JSON.
- Export JSON des diagnostics observés en session, sans qualifier automatiquement un résultat d'attestation C1.
- Protection des sorties temporaires, délais et bornes de lecture; empreintes des surfaces d’état connues avant/après la commande.
- KristalDiag, sa CLI et son format C1 ne sont pas inclus ; voir `KRISTALDIAG_INTEGRATION.md`.
