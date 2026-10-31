# Documentation — Kristal Manager / KristalDiag unifiés

> **Statut : spécification de référence pour le futur dépôt.** Édition initiale du **31 octobre 2026**. Cette documentation est la première livraison d'une nouvelle refonte, **pas** une affirmation que tous les éléments cibles sont déjà codés.

## Commencer ici

| Public | Entrée recommandée | Puis |
|---|---|---|
| Utilisateur | [Parcours principal](06-experience/parcours-utilisateur.md) | [Installation Windows](07-exploitation/installation-et-prerequis.md), [Dépannage](07-exploitation/incidents-et-retour-arriere.md) |
| Développeur | [Audit de l'existant](01-audit/existant.md) | [Architecture cible](02-architecture/architecture-cible.md), [Contrats des modules](02-architecture/frontieres-et-ports.md) |
| Mainteneur KristalDiag | [Moteur et indépendance](05-moteurs/kristaldiag-independant.md) | [Compatibilité](05-moteurs/compatibilite-v9-v10-v11.md), [Tests](08-qualite/strategie-tests.md) |
| Responsable du catalogue | [Sources de vérité](04-donnees/sources-de-verite.md) | [Ingestion](04-donnees/ingestion-et-consolidation.md), [SQLite](04-donnees/stockage-sqlite.md) |
| Personne qui conduit la refonte | [Plan de migration](10-evolution/migration-par-etapes.md) | [Feuille de route](10-evolution/roadmap.md), [Critères d'acceptation](08-qualite/matrice-acceptation.md) |

## Carte du dossier

- `00-vision/` : finalité, invariants, vocabulaire et produit.
- `01-audit/` : état observé, inventaire des fonctions, limites et risques.
- `02-architecture/` : modules, ports, séquences, patrons retenus et évités.
- `03-modele/` : identités, observations, fraîcheur, taxonomies, contrats.
- `04-donnees/` : autorité, index, migrations, ingestion, import/export.
- `05-moteurs/` : inventory/Discovery, catalogue, KristalDiag, Arketype, optimisation.
- `06-experience/` : navigation, parcours, états, accessibilité.
- `07-exploitation/` : installation, commandes PS7, opérations et secours.
- `08-qualite/` : tests, critères mesurables, observabilité et performance.
- `09-securite/` : menaces, séparation lecture/publication, données locales.
- `10-evolution/` : séquencement et définition de terminé.
- `11-decisions/` : décisions architecturales traçables (ADR).
- `12-references/` : sources, inventaire de fichiers, exemples et limites.

## Convention de statut obligatoire

**OBSERVÉ** : confirmé par le code ou un rapport fourni. **LIVRÉ** : présent dans l'overlay du 31-10, mais non nécessairement vérifié sur Windows vivant. **CIBLE** : futur contrat ou comportement à implémenter et tester. **HYPOTHÈSE** : à confronter aux corpus et au Framework officiel. Ne jamais utiliser « conforme », « certifié » ou « validé » comme synonyme de `READY`, `PASS` d'un profil limité ou « candidat ».

## Invariants résumés

1. Les 127 répertoires `locals/` restent les **sources primaires**; leur canon n'est pas mis à jour par la consultation.
2. Manager est le **point d'entrée de travail**, KristalDiag reste l'**examinateur indépendant** (même s'il est embarqué).
3. L'index opérationnel est **reconstructible** et distinct du catalogue de contenu sémantique.
4. Une observation garde toujours son **outil, profil, cible, preuve, instant, périmètre, statut et fraîcheur**.
5. Aucun rapport périmé ne redevient `PASS actuel` sur simple import ou changement d'écran.
6. L'application n'émet **aucune publication GitHub, activation ou correction canonique implicite**.
7. Une seule action principale existe pour chaque tâche; les outils techniques demeurent disponibles en **Avancé**.

## Comment utiliser ce dossier

Lire d'abord [`STATUS.md`](STATUS.md), puis les ADR et la migration avant de coder. Les anciens documents historiques `docs/*.md` déjà présents dans certains snapshots ne sont pas supprimés par cette livraison : le nouveau corpus est une documentation **prospective et additive**.

## Implémentation vNext effectivement livrée

Voir **[13 — Implémentation vNext](13-implementation-vnext/README.md)** pour les
modules exécutables, la migration opérationnelle v2, la GUI/CLI et les limites
encore ouvertes. Les sections de vision restent la cible long terme.
