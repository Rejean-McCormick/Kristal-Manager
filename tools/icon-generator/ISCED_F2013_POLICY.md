# Politique des domaines — ISCED-F 2013

Kristal Icon Generator 2.4 utilise la **Classification internationale type de l’éducation — Domaines d’études et de formation 2013 (ISCED-F 2013)** de l’Institut de statistique de l’UNESCO comme taxonomie canonique de domaines.

## Niveau utilisé dans l’icône

L’icône utilise les **11 grands domaines** à deux chiffres :

| Code | Domaine |
|---|---|
| 00 | Programmes et certifications génériques |
| 01 | Éducation |
| 02 | Arts et lettres |
| 03 | Sciences sociales, journalisme et information |
| 04 | Commerce, administration et droit |
| 05 | Sciences naturelles, mathématiques et statistiques |
| 06 | Technologies de l’information et de la communication |
| 07 | Ingénierie, industries de transformation et construction |
| 08 | Agriculture, sylviculture, halieutique et sciences vétérinaires |
| 09 | Santé et protection sociale |
| 10 | Services |

ISCED-F 2013 contient également des niveaux plus fins (champs restreints et détaillés). Le Registry pourra les conserver comme métadonnées, mais le code visuel Kristal utilise le niveau **broad field** pour rester lisible.

## Couleurs

ISCED-F 2013 normalise les codes et les intitulés, **pas une palette de couleurs pour les icônes Kristal**. Les couleurs de `runtime/kristal-domain-palette.json` sont donc une convention de présentation Kristal stable. Elles ne doivent pas être présentées comme des couleurs officielles UNESCO.

## Multi-domaines

Pour l’usage statistique officiel, ISCED-F code normalement un programme dans un champ. Kristal conserve son extension visuelle permettant jusqu’à trois grands domaines lorsque l’objet est réellement interdisciplinaire :

```text
1 domaine : 100 %
2 domaines : 65 / 35
3 domaines : 50 / 25 / 25
```

Cette combinaison multi-code est une **extension Kristal**, pas une règle UNESCO.

## Migration de l’ancienne charte

Les anciens codes (`BIO`, `MATH`, `AI`, `LAW`, `GAME`, etc.) sont convertis vers le grand domaine ISCED-F correspondant. L’ancien classement est conservé dans `classification.previous_domains` lorsqu’un profil de la couche méta est migré.

Exemples :

```text
BIO / MATH / PHYS     → 05
AI / SW / DATA        → 06
ELEC / MECH / AUTO    → 07
MED / NUTR / PHARM    → 09
LAW / FIN / ACCT      → 04
GAME / MUSIC / HIST   → 02
Pokemon               → 02
```

## Scanner

Le scanner 2.4 tente d’abord les métadonnées explicites, puis convertit les anciens codes et analyse les métadonnées/README. S’il ne peut pas attribuer de champ ISCED-F de façon défendable, il **n’utilise pas 00 comme catégorie résiduelle** : l’entrée est signalée dans `unresolved_isced` pour révision/second avis.

## Source

UNESCO Institute for Statistics, *ISCED Fields of Education and Training 2013 (ISCED-F 2013)*.

- https://uis.unesco.org/sites/default/files/documents/isced-fields-of-education-and-training-2013-en.pdf
- https://uis.unesco.org/en/glossary-term/field-education
