# Kristal kOA Ecosystem

**Version:** `0.7.1`  
**Kristal portable state baseline:** `kristal_state/6.0`  
**Observed Kristal design baseline:** `7.0.0-draft.3.2`  
**Semantic State Architecture:** `Kristal 9.0.0-draft.1` (`.kristal/v9/`)  
**Repository evidence snapshot:** `2026-10-03` (baseline) + `2026-10-27` (réconciliation)  
**Status:** `working`

Ce paquet cartographie le **kOA Digital Ecosystem** comme un graphe de composants, capacités, fonctions opératoires, contrats, artefacts, workflows, autorités, lifecycles, dépôts et preuves.

## v0.7.1 — Doc Server

Derived selection projection in `views/doc-server/catalog.v1.json`; source of membership in `knowledge-base/sources/relations.json`. Published evidence is never automatically overwritten.

## v0.7.0 — Réconciliation kOA et outils Kristal (27 octobre 2026)

Mise à jour **additive** des catalogues éditoriaux : les 155 lignes de l'inventaire kOA ont été rapprochées des dépôts/projets historiques du Kristal sans fusionner des checkouts distincts. Les nouveaux systèmes Ekole, Akor, diK, Inkuisite, BoKristal, Spek ainsi que les outils Kristal Authoring Kit et Kristalizer sont cartographiés avec leurs frontières de responsabilité. KristalDiag est documenté selon son examinateur v10 indépendant.

- `repository ≠ authority` et **inventaire ≠ autorisation GitSink** : les remotes déduits d'un `origin` local ou des snapshots restent non vérifiés en ligne.
- Le canon reste compilé depuis `knowledge-base/sources/` ; les anciennes références du 3 octobre sont préservées et les vues sont régénérées.
- **Aucune migration v11 implicite** : Authoring Kit supporte le profil v11 opt-in, mais le présent Kristal conserve sa compatibilité historique et ne reçoit pas d'identifiants KQ/KP fabriqués.
- **Kristalizer ne certifie aucune identité Wikidata** sans approbation et preuve; sa dépendance embarquée cible encore draft.3, tandis que le Kit joint est draft.4.
- **KristalDiag v10 n'est pas une certification v11**. La validation du schéma local ne prouve pas le déploiement des applications.

Voir `knowledge-base/documentation/V0.7_RECONCILIATION_KOA_20261027.md` et `views/repository-map.md`.

## Couche Kristal v9

La migration v9 est **additive** : le canon métier reste `knowledge-base/corpus/koa-ecosystem.kristal-state.json`, les surfaces `.kristal/v8/` restent des read/query models dérivés et reconstruisibles, et `.kristal/v9/` porte les Logical Artifacts, State Snapshot, Derivation, Materialization Manifests, Exchange et Activation.

Le builder calcule maintenant l'identité v6 avec RFC 8785/JCS. Pour un rebuild reproductible d'un snapshot historique, fournir explicitement le timestamp :

```bash
KRISTAL_BUILD_TIMESTAMP=2026-10-03T18:26:02Z python knowledge-base/tools/build.py
```

Les invariants d'autorité sont inchangés : `repository ≠ authority`, `hosting ≠ ownership`, `scenario ≠ deployment`, `projection ≠ canon`.

## v0.6.3 — localisateurs de repos dans le Kristal canonique

Cette révision corrige la limite de v0.6.2 : les liens Git et paths ne vivent plus seulement dans des vues Markdown. Ils sont **des métadonnées canoniques de `knowledge-base/sources/repositories.json` et des assertions du Kristal compilé**.

- remote public enregistré + statut explicite;
- path local observé + statut d’observation;
- statut combiné du localisateur (`public_remote_and_local`, `local_only`, `public_remote_only`, `unresolved`);
- `views/repository-map.md` est désormais généré depuis le registre canonique et montre aussi les pièces réalisées/supportées;
- nouvelle vue `views/public-repository-directory.md` générée depuis les mêmes données;
- aucun remote manquant n’est déduit ou inventé à partir du nom du dossier.

Voir `knowledge-base/documentation/V0.6.3_REPOSITORY_LOCATOR_CANONICALIZATION.md`.

## v0.6.2 — carte publique orientée écosystème et repos

Cette révision refond la surface de navigation publique pour qu’elle soit une **map de l’écosystème**, pas une page de profil.

- nouvelle vue `views/public-ecosystem-map.md` organisée par systèmes, familles, frontières d’autorité, surfaces publiques et repos;
- `views/repository-map.md` expose maintenant **Public remote + Local path** côte à côte;
- les URLs Git sont reprises du registre `knowledge-base/sources/repositories.json` et ne sont jamais devinées;
- les implémentations locales sans remote public vérifié restent visibles avec `—` plutôt qu’un faux lien;
- séparation explicite entre cœur kOA, recherche, support, diagnostics, contenu et écosystèmes externes.

La refonte ne change pas les identités de composants ni les frontières sémantiques de v0.6.1.

## v0.6.1 — ingestion sémantique sélective des README

Cette révision ne change pas l’identité des repos : elle **promote dans le Kristal les parties architecturales pertinentes de leurs README**.

- ajout de capacités réutilisables pour l’incertitude explicite, la frontière de recherche bornée, la falsification/contre-exemple, la mémoire de stratégie, le calcul canonique déterministe, la révision média par segment, l’analyse géospatiale evidence-first, l’apprentissage par production, le pressure-test adversarial et la reproductibilité indépendante;
- ajout d’artefacts structurants : `Soul Snapshot`, `Activation Graph`, `ResearchGraph`, `Active Frontier`, observations de stratégie, export Astro avec incertitude, `Voting Result`, `RunRecord`, versions de segments audio, releases publiques Kristal Farms, portfolios de compétence et preuves de pressure-test;
- ajout d’invariants transversaux : **pas de précision fabriquée**, **sécurité ≠ causalité simulée**, **rendu sans recomputation**, **autorité conservée par la source propriétaire**, **architecture ≠ validation empirique**, **firewall de conversion du pouvoir**, **séparation des catégories épistémiques/statuts**;
- enrichissement ciblé de Pi Theory, Formulator, Grand Challenges, Âme Artificielle, Astro Signals, VotingMachine, Voxtral, Kristal Farms, ORPHÉE et Power Dynamics;
- les dossiers PPG/Ashoka/Science Silk Road/Business-plan/Civilizational Coherence alimentent les règles de preuve et d’autorité **sans être promus artificiellement en applications**.

Voir `knowledge-base/documentation/V0.6.1_README_SEMANTIC_INGESTION.md`.

**État éditorial v0.6.1 :** 117 composants, 112 entrées de dépôts/projets, 88 capacités, 64 artefacts, 17 invariants et 2 523 relations.

## v0.6.0 — réconciliation 01/02/03 + Pi Theory démêlé

Cette version réconcilie les snapshots locaux `01-Text_Based_Git`, `02-Experimental` et `03-Brands`.

Changements structurants :

- correction complète de l’erreur v0.5.1 : **Pi Theory** est à `C:\mycode\01-Text_Based_Git\Pi-theory\Pi_Theory`; **MathChallenges** est une famille séparée sous `02-Experimental`;
- intégration du stack math : **MathChallenges**, **Formulator**, **Kristal Grand Challenges**, **Kristal Math**, `ProofBundle` et Challenge Kristal v6;
- réactivation de nombreux repos auparavant seulement historiques : Âme Artificielle, Civilizational Coherence, Colin Row, Freeze–Vote–Rebuild, HELLO WORLD, King Klown Canon, Kristal Farms, PPG, Power Dynamics, ORPHÉE, Science Silk Road et VotingMachine;
- ajout de Business-plan, International-Strategy, Commons, Astro Signals, Voxtral Audiobook Studio et surfaces Brands/support;
- `Rainbow_Write` est conservé comme projet utilitaire avec statut Git non vérifié;
- ajout des invariants **Hypothèse/sortie IA ≠ preuve** et **Validation locale ≠ canon global**;
- evidence package sûr : les fichiers de récupération/credentials visibles dans le snapshot Brands sont **exclus**.

Voir `knowledge-base/documentation/V0.6_WORKSPACE_RECONCILIATION.md`, `views/pi-theory-vs-mathchallenges.md`, `views/math-research-stack.md` et `views/repository-map.md`.

**État construit v0.6.0 :** 117 composants, 112 entrées de dépôts/projets (93 observations locales courantes), 78 capacités, 52 artefacts, 10 invariants et 2 474 relations.

## Axes de lecture

```text
Component × Capability        = ce que chaque pièce permet de faire
Component × OperatingFunction = où elle se place structurellement
Repository → Component/Artifact/External = ce que le repo réalise/supporte réellement
Utility → Workflow → Capability → Component = comment un besoin peut traverser l’écosystème
```

## Règles de preuve

- Un repo n’est pas automatiquement une app.
- Un README propriétaire est fort pour le but, la version et les limites de **son** repo, pas pour prouver l’intégration globale.
- L’absence d’un repo dans l’index local ne vaut pas suppression.
- Les sources/bundles/test kits/content roots peuvent rester des artefacts.
- Les dépendances GF/simdjson restent externes/support.
- `COMPOSED · runtime UNVERIFIED` reste une composition plausible, pas une preuve de déploiement.

## Validation / interrogation

```bash
python knowledge-base/tools/build.py
python knowledge-base/tools/validate.py
python knowledge-base/tools/query.py component "Kompiler"
python knowledge-base/tools/query.py component "Kor"
python knowledge-base/tools/query.py component "KonnaxionDiag"
```

## Vues principales

- `views/public-ecosystem-map.md`
- `views/repository-map.md`
- `views/public-repository-directory.md`
- `views/current-application-map.md`
- `views/component-capability-map.md`
- `views/operating-function-map.md`
- `views/diagnostics-release-tooling.md`
- `views/uckk-subsystems.md`
- `views/workflow-pattern-map.md`
- `views/problem-pattern-map.md`
- `views/support-boundary-map.md`
