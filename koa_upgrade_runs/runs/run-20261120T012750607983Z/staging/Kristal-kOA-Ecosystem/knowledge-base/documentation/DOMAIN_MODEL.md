# Domain model v0.5

## Graphe principal

```text
Component --contributes_to--> Capability --addresses_need--> Need
Component --fulfills_function--> OperatingFunction
Utility --includes_workflow_pattern--> WorkflowPattern --enabled_by_capability--> Capability
ProblemFamily --addressed_by_workflow_pattern--> WorkflowPattern
Scenario --uses_workflow_pattern--> WorkflowPattern
Scenario --scenario_composes_component--> Component
```

Autour : `Contract`, `Artifact`, `Lifecycle`, `Invariant`, `Domain`, `Repository`, `ExternalReference`.

## Utility

Une utilité est une lecture orientée utilisateur/problème. Elle ne correspond pas à un produit. Les huit familles viennent du Scenario Mosaic et regroupent des patterns transférables entre domaines.

## WorkflowPattern

Un pattern décrit une transformation réutilisable du contexte vers l'action ou la mémoire. Il peut traverser plusieurs composants. Le lien vers les capacités est architectural; il ne prouve pas une exécution réelle.

## Scenario

Deux corpus sont conservés séparément : 36 archétypes de problème et 120 scénarios Mosaic. Ils servent à tester la composition et à découvrir des workflows potentiels. Leur statut runtime reste distinct de l'architecture.

## Repository ≠ Component ≠ Offer

Un dépôt peut réaliser un composant. Une offre commerciale peut composer plusieurs composants. Ni le dépôt ni l'offre ne devient automatiquement une autorité architecturale.

## Support is not membership

The model distinguishes three related but non-equivalent situations:

1. **member component** — owns or participates in kOA Digital Ecosystem state/contracts and is explicitly `part_of` the ecosystem;
2. **supporting ecosystem** — independently governed system family that provides upstream/downstream capability without becoming a kOA member;
3. **external support/reference** — tool, authority or pattern source connected through adapters, evidence or inspiration.

The MA-Gustave GF family is modeled as (2). GF itself, Decidim, Ninai, OpenRefine and OpenTapioca are modeled as (3).


## v0.5 repository/evidence layer

The repository catalog now distinguishes current local observation, historical public discovery, workspace/content/test repositories, external dependencies and application/runtime repositories. Repository-to-component promotion requires role evidence; data roots, source bundles, prototypes and test kits may map to `Artifact` or `ExternalReference` instead of `Component`.
