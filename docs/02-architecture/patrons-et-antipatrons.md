# Choix de patrons — justifiés et proportionnés

Décisions inspirées de `senior-architecture-patterns` et du guide UX fourni. Un patron n'est retenu que s'il résout un problème observé.

| Patron | Décision | Application |
|---|---|---|
| Monolithe modulaire (#31) | ADOPTER | Un produit local, modules stricts; pas de services réseau |
| Hexagonal (#10) | ADOPTER | Ports Scanner/Examiner/Store, adaptateurs remplaçables |
| Anti-corruption layer (#08) | ADOPTER | Normalisation des verdicts/rapports sans confondre standards |
| Strangler Fig (#07) | ADOPTER | Déplacer progressivement les fonctions de `gui.py` |
| Idempotence (#15) | ADOPTER | Imports et replays sûrs via identité d'événement |
| CQRS (#12) | SIMPLIFIÉ | Read model opérationnel dérivé, sans bus ni ségrégation distribuée |
| Graceful degradation (#04) | ADOPTER | Affichage partiel si index/catalogue indisponible |
| Bulkhead (#02) | ADAPTER | Nombre borné de workers pour isoler Diag et éviter saturation |
| Timeout budgets (#06) | ADOPTER | Délais explicites par niveau et annulation |
| Cache-aside (#18) | ADAPTER | Réutiliser empreintes validées, recompiler seulement si nécessaire |
| Circuit breaker (#01) | NON PRIORITAIRE | Pas de service distant principal à protéger |
| Saga (#14) | NON NÉCESSAIRE | Transactions locales et opérations explicites séparées |
| Event sourcing (#13) | NE PAS SUR-IMPLÉMENTER | Journal des runs append-only, pas reconstruction métier intégrale |
| Transactional outbox (#16) | À RÉÉVALUER | Utile seulement en cas de véritables tâches asynchrones persistées |
| Microservices/mesh (#32) | REFUSER POUR L'INSTANT | Complexité distribuée sans avantage pour 127 locaux |

## Règles de pragmatisme

Le composant le plus simple qui prouve la fraîcheur et conserve les preuves gagne. Les profils Diag lourds n'utilisent pas une UI thread; les recherches SQL ne bloquent pas la navigation. Toute optimisation doit être comparée au corpus et à son coût de maintenance.

## UX

Les principes UX-05, UX-07, UX-15 à UX-18 se concrétisent par : une liste de Kristals comme entrée, une seule action « Analyser / Diagnostiquer », un historique près du Kristal, et un volet « Avancé » préservant les outils spécialisés.
