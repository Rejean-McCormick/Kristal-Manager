# Implémentation Manager vNext — 31 octobre 2026

Cette section porte sur **le code effectivement livré**. La vision d'ensemble
et les futurs travaux restent décrits dans les sections 00–12.

## Modules opérationnels

| Module | Contrat effectif |
|---|---|
| `kristal_manager/unified/domain.py` | statuts, limites de taille, modèle pur |
| `unified/repository.py` | SQLite v2 additif, runs, observations, décisions, historique, sauvegardes |
| `unified/service.py` | inventaire, analyse, batch Diag V9, import ARK, import JSON historique |
| `unified/dashboard_ui.py` | vue de suivi, historique, exécution non bloquante, arrêt coopératif |
| `unified/cli.py` | mêmes actions sans Tk; JSON de sortie |
| `central_store.py` | API v1 maintenue; double écriture transactionnelle v1/v2 |
| `diagnostics_batch.py` | vrais runs, progression, erreurs, preuve immédiate, NOT_APPLICABLE |
| `diag_bridge.py` | exécution en sous-processus du moteur KristalDiag fourni, sans shell |

## Existant conservé

Manager (`gui.py`), ancien centre global, audit et triage, registre de revues,
classification Arketype/UNESCO/PRF, index lourd de contenu, moteur KristalDiag
version fourni et tous les panneaux avancés. Aucun canon local touché.

## Non couvert dans cette livraison

- Diagnostic sémantique complet v11 et natif (profil V9 seulement en batch).
- Certification C1/C2/C3 ou validation exhaustive des 20 733 crosswalks.
- Pipeline de publication, signature ou activation.
- Recherche/renommage GitHub et outils automatisés de synchronisation.
- Migration des classifications proposées vers des tags canoniques approuvés.
- Optimisations de tous les anciens écrans (certaines vues avancées restent historiques).

Une exécution `NOT_APPLICABLE` ou une observation `PARTIAL_SCOPE` ne sont **jamais**
converties en `PASS` par l'interface.
