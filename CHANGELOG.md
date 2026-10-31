## 2026-10-28 — Copie des résultats dans ChatGPT (0.4)

- Ajoute le bouton « Copier résultats pour ChatGPT » dans le centre d’analyse globale : synthèse de tous les Kristals, anomalies et propositions (même sans sélection).
- Ajoute « Copier Kristal sélectionné » et « Copier ces détails » avec les indices détaillés disponibles, en JSON.
- Ajoute Ctrl+C sur la table pour copier le Kristal sélectionné ; confirmation visible et aucune connexion réseau.
- Préserve l’archive ZIP des preuves, la lecture seule, le cache local et l’interdiction de Git/GitHub.

## 2026-10-28 — Distribution locale sans GitHub (0.3)

- Neutralise `GitSink.bat` sans supprimer le fichier : les anciens raccourcis ne peuvent plus déclencher `git add/commit/push`.
- Exclut les **nouveaux** catalogues et rapports générés via `.gitignore` (sans toucher à l'index ni à l'historique de Git).
- Clarifie l'absence de toute opération Git/GitHub dans l'analyse globale et l'aide.
- Conserve le scan global, le cache, les suggestions Arketype/UNESCO/diK, la vérification locale et les exports ZIP.

## 2026-10-28 — Centre d’analyse globale intégré (0.2)

- Ajoute un centre intégré via le bouton « Analyse globale… » : catalogue incrémental, résumé lexical, propositions Arketype/UNESCO et observations diK pour tous les Kristals.
- Ajoute un pipeline worker Tk non bloquant, des rapports JSON/CSV/HTML, un plan de corrections à confirmer et un export ZIP des problèmes sans fichier source.
- Ajoute une vérification locale optionnelle (sources Discovery), limitée à quatre travailleurs, sans exécution de scripts issus des Kristals.
- Centralise les fichiers dérivés dans `catalogue/` et `rapports/` à la racine du Manager. Les inférences ne modifient aucune classification officielle.
- Ajoute la commande CLI `analyse-globale` et des tests de non-modification des sources, de cache et d’interface.
- Ce lot n’intègre pas de correcteur canonique diK/Kit ni de batch KristalDiag officiel ; C1/C2/C3 restent non évalués.

## 2026-10-27 — Framework v7 UNESCO Thesaurus and ISCED-F reading

- Bundled the pinned Framework v7 UNESCO reference: 7 domains, 88 microthesauri, 100 Subject seed examples. UNESCO identifiers and URIs are preserved; no invented classifications.
- Kept UNESCO knowledge navigation separate from ISCED-F 2013 codes used by the Windows icon generator, as well as Arketype, PRF, and technical profile.
- Added read-only UNESCO/ISCED classification columns, filters, detailed provenance and private JSON/HTML classification audit overlay.
- Validates explicit codes and internal inconsistencies, preserves legacy domains as free text, and exports taxonomy observations with inventory JSON.
- Example tested with Kristal-Architecture: icon field ISCED 07, UNESCO microthesaurus not yet declared in local workspace; Framework seed KQ5058 not applied without matching KQ identity.
- No schema migration, no edits to source Kristals, no network access or publication.

## 2026-10-27 — English UI / batch folder normalization

- Integrated a preview-first batch folder rename window, with explicit selection, full ZIP backups, durable JSON journal and guarded undo.
- Preserved local inventory, categories, integrated KristalDiag, icon generator, reports and exports.
- Moved selected icon to the lower details panel; removed icon column from inventory table.
- Displayed compact State ID in table; full state_ref URN retained in JSON.
- Adopted the English desktop interface and title-case “Kristal Manager”.
- Added focused regression tests and release instructions.

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
