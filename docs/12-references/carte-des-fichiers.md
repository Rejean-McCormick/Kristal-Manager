# Carte technique des fichiers — existant → cible

| Fichier actuel | Responsabilité observée | Destination logique cible |
|---|---|---|
| `kristal_manager/core.py` | découverte état, readiness, gestion historique | `adapters/inventory`, `domain/workspace` |
| `discovery.py`, `workspace_tools.py` | Discovery, fichiers et contrôles locaux | `adapters/discovery` |
| `inventory.py` | visualisation/inventaire auxiliaire | `adapters/inventory` |
| `content_catalog.py` | index et synthèses de contenu | `adapters/content` |
| `global_analysis.py` | analyse intégrée et exports | `application/analyze`, `adapters/reports` |
| `semantic_triage.py` | suggestions / triage | `adapters/classification` |
| `classification_bridge.py` | mapping/UNESCO/PRF | `adapters/classification` |
| `archetype_panel.py`, `archetype_structure_bridge.py` | UI et rapport Arketype | `presentation`, `adapters/arketype` |
| `diag_bridge.py` | invocation officielle/externe Diag | `adapters/diagnostics` |
| `diagnostics_batch.py` | exécution du lot V9 | `application/diagnose_batch` |
| `central_store.py` | SQLite des observations | `adapters/persistence` |
| `operations_cli.py`, `cli.py` | interface ligne de commande | `presentation/cli` |
| `gui.py`, `global_panel.py`, `diag_panel.py` | Tk, navigation et actions | `presentation/gui` |
| `review_registry.py`, `review_panel.py` | revue de classifications | `application/reviews`, `presentation/gui` |
| `kristalizer_bridge.py`, `bundle_inventory.py` | imports et inventaire spécialisés | `adapters/imports`, `adapters/bundle` |
| `publication_gate.py`, `GitSink.bat` | fonctions publication historiques | `advanced/publishing` avec gates explicites |
| `tools/KristalDiag/` | examinateur autonome embarqué | dépôt/vendor Diag indépendant avec version pin |

**CIBLE ≠ renommage automatique** : ce tableau décrit des responsabilités. Le plan Strangler peut garder des fichiers existants et déplacer des fonctions progressivement, sans casser les imports historiques.

## Entrées CLI

- `python -m kristal_manager.operations_cli` (overlay refonte) fournit `inventorier`, `analyser`, `diagnostiquer`, `etat`, `importer-arketype`, `importer-anciens-diag`.
- Le Manager historique possède également `kristal_manager.cli`; éviter de l'éliminer avant tests de parité.
- KristalDiag fournit son propre CLI `kristaldiag conform`, `run`, `verify-run`, indépendant.

## Emplacements à garder distincts

`locals/` = sources; `Kristal-Manager/catalogue/` = index/cache locaux; `Kristal-Manager/rapports/` = analyses; préférences utilisateur → `diagnostics/` = preuves. Les chemins de sortie précis dépendent des préférences locales.
