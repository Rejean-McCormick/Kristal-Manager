# Traçabilité des sources de cette documentation

## Sources de code effectivement examinées

- Snapshot Manager `znapshot_Kristal-Manager_10310806.zip` : `kristal_manager/core.py`, `gui.py`, `discovery.py`, `content_catalog.py`, `global_analysis.py`, `diag_bridge.py`, `classification_bridge.py`, `review_registry.py` et autres modules.
- Overlay Manager/Diag `OVERLAY-DIRECT-REFONTE-MANAGER-KRISTALDIAG-2026-10-31.zip` : `central_store.py`, `diagnostics_batch.py`, `operations_cli.py`, adaptations GUI/panels, `tests/test_central_refactor.py`, `tests/test_unified_gui_flow.py`, note d'architecture.
- Snapshot Diag `KristalDiag_Code_snapshot(2).zip` : `kristaldiag/`, `contracts/`, `docs/OPERATING_MODEL.md`, `docs/CONFORMANCE.md`, `README.md`, `pyproject.toml`.
- `RAPPORT_ARKETYPE_STRUCTURE(1).json` : 127 comparaisons structurelles et limites explicites.
- Rapports d'analyse globale Manager du 31 octobre 2026 : 127 workspaces, 16 observations natives limitées, 111 autres à revoir.

## Guides d'architecture et d'interface joints

- `guide-architecture-interfaces-ia-v2(7).zip` → `senior-interface-ux-patterns-v2/`, particulièrement `AI_INGESTION.md`, `GUIDE_RAPIDE.md`, `UX_PATTERN_MATRIX.md` et UX-15 à UX-18.
- `senior-architecture-patterns(5).zip` → `senior-architecture-patterns/`, particulièrement #31 (modular monolith), #07 (strangler), #08 (anti-corruption layer), #10 (hexagonal), #12 (CQRS), #15 (idempotency), #04 (graceful degradation), #06 (timeout budgets).

Les guides apportent des principes de design; **les noms de modules, formats et commandes spécifiques** proviennent des sources Kristal inspectées. Les schémas `v2` dans cette documentation sont des propositions d'architecture, pas des normes déjà acceptées.

## Documents historiques à conserver

Les anciennes pages `docs/C2_PUBLICATION_CONTROL.md`, `CONTENT_CATALOG.md`, `V10_ALIGNMENT.md`, `KONSTELLATION_INVENTORY.md`, documents de snapshot et `REFONTE-CENTRE-CONTROLE-2026-10-31.md` sont des preuves d'évolution. Leur présence dépend de l'état du dépôt. Ne pas les effacer au motif qu'un nouvel index est créé.

## Règle de vérification

Avant un changement de norme Framework, revoir les contrats officiels et le code Diag épinglé. Aucune source fournie ne démontre ici une couverture générale d'un **Framework v11** ou une certification universelle des 127.
