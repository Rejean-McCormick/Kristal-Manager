# Feuille de route — prochaine version Manager / KristalDiag

Cette feuille de route est **un plan**, pas un statut de développement accompli.

## Phase 0 — Consolider et geler les contrats (P0)

Livrer manifestes du snapshot Manager/Diag/Kit, carte de dépendances, modèles `WorkspaceRef`/`Observation` et profils d'applicabilité versionnés. Définir une matrice de tests reproduisant les 127, 16 natifs, 3 familles de version et les rapports historiques. Aucun changement UI tant que la définition de « CURRENT » n'est pas écrite.

## Phase 1 — Stabiliser le registre central (P0)

Migrations v1→v2 avec backup, couche `domain/`, `run_id`, ingestion idempotente, `fingerprint_scope`, indexation par profil et preuve. Tests de redémarrage, changement source, import historique, données corrompues. Conserver la base de contenu séparée.

## Phase 2 — Organiser le parcours principal (P1)

Réduire les commandes concurrentes : liste, fiche, centre d'analyse, historique, outil avancé. Conserver les  fonctions existantes; brancher tous les boutons sur les mêmes use cases; déplacer I/O hors thread Tk.

## Phase 3 — Étendre l'examen sans invention (P1)

Sélecteur d'applicabilité de profils V9/V10, couverture des 16 natifs, séparation du lecteur v11, import des rapports structurés et recoupement des preuves. Ne pas appeler un `PASS V9` « validation v11 ».

## Phase 4 — Enrichissement de qualité (P2)

Triage des 96 PRF-20 généraux, 36 ambiguïtés Arketype, alignements UNESCO/Wikidata avec provenance, statut proposition/revue/approbation, plan Kit explicite. Repasser les diagnostics adaptés après chaque changement de source.

## Phase 5 — Fiabilité/maintenance (P2)

Annulation/reprise batch, cache par empreinte, observabilité, CI Windows, gestion des migrations, documentation opérateur, archive de résultats, sécurité des imports et audits de non-régression.

## Phase 6 — Release (P0 pour diffusion)

Accepter tous les gates P0, mesurer les performances et verrouiller les dépendances; publier code et docs **uniquement sur action de release séparée**. Conserver un rollback testable et les commandes CLI existantes pendant une transition annoncée.

Voir [plan détaillé](migration-par-etapes.md) et [définition de fini](definition-de-fini.md).
