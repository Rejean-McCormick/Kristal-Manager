# Commons — dossier de travail

## Objet

Ce dossier prépare une exploration entre **The Commons**, projet conçu par **Zahra Khan** dans le cadre du SFU Demshot Challenge, et **Konnaxion / ethiKos**, une infrastructure civique déjà largement implémentée dans l’écosystème kOA.

L’objectif n’est pas de déclarer que les deux projets sont identiques, ni de proposer l’adoption de kOA dans son ensemble.

L’objectif est plus limité :

> **Déterminer si les primitives déjà construites dans Konnaxion / ethiKos peuvent réduire radicalement le coût technique de concrétisation de The Commons, tout en laissant à Zahra et à un éventuel cadre SFU la capacité de critiquer, modifier, masquer ou rejeter les mécanismes qui ne conviennent pas à leurs objectifs démocratiques.**

## Principe directeur

**Massive architecture, small entry point.**

kOA est une architecture sociotechnique beaucoup plus large. The Commons ne devrait pas avoir à l’adopter. Le point d’entrée proposé est un sous-ensemble de Konnaxion / ethiKos :

- compréhension d’une question ;
- contexte et sources ;
- délibération structurée ;
- positions nuancées ;
- lecture publique ;
- lecture advisory fondée sur l’expertise pertinente ;
- conflits et récusations ;
- résultats ;
- suivi de ce qui arrive après la décision.

## Statuts utilisés dans ce dossier

| Statut | Signification |
|---|---|
| **OBSERVÉ** | Présent dans les snapshots de code fournis |
| **VALIDÉ** | Présent et soutenu par des résultats de tests/qualification fournis |
| **DOCUMENTÉ** | Décrit dans les documents fournis, mais non confirmé dans le snapshot de code examiné |
| **À CONCEVOIR** | Fonction ou décision encore ouverte |
| **EXTERNE** | Information provenant d’une source publique externe, distincte du corpus kOA |

## Organisation

- `00_overview/` — synthèse et positionnement
- `10_fit/` — correspondance The Commons ↔ Konnaxion
- `20_technical/` — état technique et matrice de preuves
- `30_design/` — stratégie d’interface et revue démocratique/équité
- `40_pilot/` — protocole de prototype/pilote
- `50_collaboration/` — cadre Zahra / SFU / kOA et communications
- `90_sources/` — registre des sources et limites

## Ce que ce dossier ne promet pas

- aucune adoption institutionnelle ;
- aucun partenariat formel ;
- aucun financement ;
- aucune exclusivité ;
- aucune cession d’IP ;
- aucune intégration à Kin City ;
- aucun développement custom important avant validation du fit ;
- aucune affirmation que The Commons n’a pas déjà de travail technique privé non publié ;
- aucune affirmation de licence open source précise avant vérification du dépôt/licence canonique.

## Première décision recherchée

Une seule :

> **Est-ce qu’il y a assez de fit entre The Commons et les primitives ethiKos/Konnaxion pour justifier une session de revue technique et démocratique, puis un prototype minimal ?**
