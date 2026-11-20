# Notes de mapping 0.3.0

## Sources nouvelles

- plan d'affaires : utilisé seulement pour la cartographie des besoins, actifs, capacités, dépendances, rôles et utilités;
- 36 scénarios canoniques : familles de problèmes, failure mechanisms, patterns et compositions;
- 120 Scenario Mosaic : 8 familles d'utilité, 24 patterns, boucles et rôles de composants.

## Ce qui n'est pas importé du plan d'affaires

Prix, marges, revenus, besoins de financement, TAM, hypothèses commerciales et projections financières ne deviennent pas des assertions architecturales.

## Scénarios

Les scénarios sont conservés comme `editorial composition / runtime unverified`. Ils montrent comment les capacités pourraient s'assembler et où les handoffs risquent de casser. Ils n'augmentent pas la maturité d'un composant.

## Nouvelles pièces promues

Control Panel, Capsule Manager, Worlds et les diagnostics apparaissaient déjà comme dépôts/supports; le plan d'affaires et les inventaires confirment une fonction architecturale propre. Ils sont donc des composants à autorité bornée, reliés à leurs systèmes propriétaires.
