# EL — Artificial Soul Engine / Âme Artificielle

**EL** est un projet expérimental visant à représenter une personnalité humaine comme un **graphe psycho-causal sémantique** et à calculer des réactions cohérentes à partir d’un état déterminé de cette personnalité.

Le projet ne prétend pas créer une âme réelle ni démontrer qu’un système artificiel ressent des émotions. Il cherche à **reproduire fonctionnellement certains mécanismes** : croyances, associations, valeurs, souvenirs, dispositions, réévaluation intellectuelle, états affectifs et réactions.

## Architecture en une phrase

```text
Soul Basis
  -> Soul Snapshot immuable
  -> stimulus
  -> Activation Graph transitoire
  -> interprétation / affect / intention
  -> réaction
```

Un Soul Snapshot peut représenter la même personne à un âge précis. Le moteur **ne modifie pas automatiquement le snapshot** pendant la conversation. Les changements biographiques sont décrits explicitement dans un nouveau snapshot.

## Concepts principaux

- **Soul Basis** : ontologie commune des mécanismes possibles — métaphore du « blanc ».
- **Soul Graph** : graphe sémantique de mécanismes psycho-causaux.
- **Soul Snapshot** : représentation immuable d’un sujet pendant une période.
- **Biographical Transformation** : explication structurée du passage entre snapshots.
- **Activation Graph** : état temporaire calculé pour un stimulus.
- **TraitVector** : projection dérivée du graphe, utile pour comparaison et UI mais non constitutive de l’âme.
- **Charte 1→9** : topologie de lecture, non moteur causal linéaire.
- **Numérologie / natal chart** : sources d’hypothèses de dispositions, à distinguer des observations et à tester.

## Âme, intellect, personnalité

Dans le vocabulaire du projet :

- l’**âme** représente l’organisation profonde des dispositions ;
- l’**intellect** représente perception, catégorisation, raisonnement et réévaluation ;
- la **personnalité** est leur manifestation observable en interaction avec l’histoire et le contexte.

## Kristal v5

L’intégration proposée utilise Kristal comme couche de représentation et de provenance des Soul Snapshots. Le projet prévoit un profil applicatif `kristal.v5:soul-graph` pour typer les nœuds, relations et qualificateurs psycho-causaux.

Kristal stocke et rend le graphe inspectable. Le **Soul Causal Engine** exécute la propagation d’activation. Les deux responsabilités restent séparées.

Voir :

- `docs/definition_operationnelle.md`
- `docs/soul_graph_schema.md`
- `docs/engine_spec.md`
- `docs/snapshots_biographiques.md`
- `docs/kristal_integration.md`
- `docs/validation_protocol.md`

## Couches symboliques

Le projet conserve la charte 1→9, les chakras, la numérologie pythagoricienne inversée et les branes comme couches de lecture ou générateurs d’hypothèses. Elles ne sont pas présentées comme des validations scientifiques par définition.

## Sécurité

La sécurité de l’application est une **couche externe** au modèle de personnalité. Une règle de sécurité peut limiter une sortie, mais elle ne doit pas être confondue avec la compassion, la morale ou la causalité interne du personnage simulé.

## Statut du code

Le moteur Soul Graph est maintenant implémenté dans `src/` comme référence minimale : snapshots immuables, propagation causale bornée, inhibition, affect dérivé, transformations biographiques explicites, projections de traits, propositions symboliques et adaptateur Kristal.

Les anciens utilitaires de `TraitVector` et d'interpolation 1→9 sont conservés comme projections/compatibilité. `src/ethics.py` est déprécié au profit de `src/safety.py`, qui est externe à la personnalité.

Voir `docs/code_reference.md` et `examples/john_doe_snapshots.py`.
