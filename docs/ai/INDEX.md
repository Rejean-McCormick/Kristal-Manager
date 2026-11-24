<!-- kOA Doc Server · Docs IA · lot 01 · source datée, non-certifiante -->
# Documentation IA — Kristal Manager

**Périmètre :** Inventaire et contrôles opérationnels de Kristals locaux, comparaisons d’observations et coordination des outils distincts.

**Origine :** snapshot local documenté (20 novembre 2026, ou archive complémentaire). Les chemins et versions actifs sont à vérifier sur le poste avant toute modification.

**Autorité :** Manager gère les inventaires et vérifications locales. Le Framework, les propriétaires des Kristals et les qualificateurs indépendants conservent leurs autorités.

## Ordre de lecture conseillé à un agent

1. [`README.md`](../../README.md) — Modes et commandes.
2. [`docs/00-vision/mission-et-perimetre.md`](../../docs/00-vision/mission-et-perimetre.md) — Mission et exclusions.
3. [`docs/03-modele/v9-v10-v11-natifs.md`](../../docs/03-modele/v9-v10-v11-natifs.md) — Applicabilité des lecteurs.
4. [`pyproject.toml`](../../pyproject.toml) — Entrées Python.
5. [`kristal_manager/__main__.py`](../../kristal_manager/__main__.py) — CLI.
6. [`DEMARRER-CENTRE-UNIFIE.cmd`](../../DEMARRER-CENTRE-UNIFIE.cmd) — Centre unifié.

## Documents produits par cet overlay

- [`AI_CONTEXT.md`](AI_CONTEXT.md) — limites, parcours et points de contrôle.
- `PROFIL_INGENIERIE.md` — produit **sur demande** à partir d'un scan RepoSurveyor du code local; ce fichier n'est pas fourni par le lot rédactionnel.
- `AGENTS.md` à la racine — consignes de dépôt existantes conservées ou nouvelles si elles n'existaient pas.

## Règles transversales

- Une capture documentaire n'établit ni conformité, ni maturité, ni disponibilité en production.
- Ne pas remplacer contrats, ADR, README ou preuves propriétaires par cette aide de navigation.
- Nouveau Framework v11 : lire le profil effectivement adopté; ne jamais imposer une migration par défaut.

## Procédure opérationnelle proposée (lot 04)

- [`OPERATIONS.md`](OPERATIONS.md) — parcours concret et points de contrôle à vérifier avant tout effet.
