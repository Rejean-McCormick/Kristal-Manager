# Audit de l'existant : code et comportement

## Sources utilisées

Snapshot Manager `znapshot_Kristal-Manager_10310806.zip`, module KristalDiag `KristalDiag_Code_snapshot(2).zip`, overlay du 31-10 `OVERLAY-DIRECT-REFONTE-MANAGER-KRISTALDIAG-2026-10-31.zip`, rapport d'analyse globale du 31-10 et rapport structurel Arketype des 127. **Ce ne sont pas des preuves que la même combinaison est installée partout sur Windows.**

## Organisation constatée

| Sous-système | Fichiers réels | Constats |
|---|---|---|
| Inventaire, Discovery, état | `core.py`, `inventory.py`, `discovery.py`, `workspace_tools.py` | Scan et contrôle local distincts |
| Catalogue de contenu | `content_catalog.py` | SQLite descriptif/HTML générés, volumineux et séparés |
| Analyse globale, triage | `global_analysis.py`, `semantic_triage.py`, `global_panel.py` | Rapports, priorités, propositions et tableau d'analyse |
| Diagnostics | `diag_bridge.py`, `diag_panel.py`, `tools/KristalDiag` | Moteur source local, preuves hors workspace; profil officiel individuel |
| Registre revue et taxonomies | `review_registry.py`, `review_panel.py`, `classification_bridge.py`, `archetype_panel.py` | Décisions et propositions réparties |
| GUI, outils historiques | `gui.py`, `batch_panel.py`, `bundle_panel.py`, `kristalizer_bridge.py` | Navigation techniquement puissante mais étalée |
| Consolidation récente | `central_store.py`, `diagnostics_batch.py`, `operations_cli.py` | Livrés dans le dernier overlay, à vérifier sur poste réel |

## Limitations établies

- Les 16 contrats natifs ont été reconnus mais le catalogue signale une inférence de contenu limitée.
- Le batch intégré livré n'exécute que `V9-State-Reader`, même si le panneau individuel expose aussi des profils V10.
- `central_store.py` v1 conserve `workspaces` et `observations`, et compare un **sous-ensemble d'empreintes V9** : couverture v11 incomplète.
- L'historique importé depuis CSV sans empreintes est volontairement `STALE_OR_UNVERIFIED`.
- La suite complète historique n'est pas entièrement verte; les 54 tests ciblés de l'overlay étaient verts sous GUI virtuel Linux.
- L'archive Manager la plus récente analysée contient de nombreux fichiers historiques et parfois des bases SQLite générées; la future publication doit les séparer.

## Ligne de partage recommandée

Ne pas écraser un moteur indépendant pour unifier l'interface. **Centraliser l'identité des résultats, les permissions, les états et les opérations; laisser les calculateurs spécialisés sous leurs contrats.**
