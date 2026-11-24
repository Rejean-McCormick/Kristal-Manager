<!-- kOA Doc Server · Docs IA · lot 01 · source datée, non-certifiante -->
# Documentation IA — Kristal Manager

**Périmètre :** Inventaire et contrôles opérationnels de Kristals locaux, comparaisons d’observations et coordination des outils distincts.

**Origine :** snapshot local documenté (20 novembre 2026, ou archive complémentaire). Les chemins et versions actifs sont à vérifier sur le poste avant toute modification.

**Autorité :** Manager gère les inventaires et vérifications locales. Le Framework, les propriétaires des Kristals et les qualificateurs indépendants conservent leurs autorités.

## Méthode de travail IA

1. Faire l’inventaire avant de choisir un profil de contrôle adapté aux artefacts observés.
2. Distinguer présence structurale, fraîcheur Discovery, vérification indépendante et qualification.
3. Conserver les rapports, sauvegardes et campagnes hors de la source canonique quand les outils le permettent.
4. Exiger une autorisation explicite pour toute préparation, mise à jour ou installation de Kristal.

## Entrées et validations attestées par les sources

- `python -m kristal_manager verify "<chemin-local-kristal>"`
- `python -m kristal_manager scan "<racine-des-kristals>"`

*Avant exécution, vérifier les préconditions locales et les effets possibles de la commande. Les commandes sont des points d’entrée documentés, pas des validations effectuées par cet overlay.*

## Frontières à ne jamais franchir

- Ne pas réécrire le canon, régénérer Discovery ou publier depuis un `verify` local.
- Un `ATTENTION_REQUIRED` ne doit pas être silencieusement promu en `PASS`.
- La validation V9 ne doit pas être présentée comme une qualification V11.

## Incertitudes et limites explicites

- Des dossiers de staging locaux peuvent être volumineux; ne pas les supprimer pour forcer un résultat de scan.

## Sources à relire

- [`README.md`](../../README.md) — Modes et commandes.
- [`docs/00-vision/mission-et-perimetre.md`](../../docs/00-vision/mission-et-perimetre.md) — Mission et exclusions.
- [`docs/03-modele/v9-v10-v11-natifs.md`](../../docs/03-modele/v9-v10-v11-natifs.md) — Applicabilité des lecteurs.
- [`pyproject.toml`](../../pyproject.toml) — Entrées Python.
- [`kristal_manager/__main__.py`](../../kristal_manager/__main__.py) — CLI.
- [`DEMARRER-CENTRE-UNIFIE.cmd`](../../DEMARRER-CENTRE-UNIFIE.cmd) — Centre unifié.
