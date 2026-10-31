# Plan de tests — pyramide et preuves de non-régression

## Niveaux

1. **Unitaire domaine** : fingerprints scope, états, ids, propositions vs décisions, erreurs.
2. **Contrat adaptateurs** : importer vrais rapports Arketype/Diag, validateurs, compatibilité de schémas.
3. **Persistance** : SQLite temp, migration, transactions, concurrence, idempotence, corruption.
4. **Intégration Manager/Diag** : subprocess de KristalDiag embarqué sur fixture non canonique, `summary.json` et preuves persistées.
5. **Interface** : navigation clavier, rescans, restauration historique, statut juste, progression et annulation.
6. **End-to-end Windows** : ensemble vivant de 127 en **lecture seule**, comparaison de hashes avant/après.

## Fixtures obligatoires

- Kristal V9 `PASS` minimal et deux `K15` en erreur de déclaration.
- Kristal V10 avec manifeste et binding.
- Kristal v11 avec graphes/dictionnaires/crosswalk et éditions historiques.
- Kristal natif sans machine V9 (`NOT_APPLICABLE`).
- Fichier JSON invalide, rapport de 5 Mo, symlink vers l'extérieur, chemin Windows avec accents.
- Rapport déjà importé, rapport historique sans fingerprint, résultat périmé, nouvelle version de contrat.
- Source modifiée pendant un run, timeout, moteur absent, erreur d'écriture SQLite.

## Suites existantes

`tests/test_central_refactor.py` et `tests/test_unified_gui_flow.py` ont été ajoutés dans l'overlay du 31-10. 54 tests ciblés ont réussi sous affichage virtuel Linux; cela **ne vaut pas** validation de toute l'application sous Windows. Les échecs historiques de publication désactivée ne doivent pas être « corrigés » en réactivant GitSink.

## Commandes de développement indicatives

```powershell
cd C:\mycode\Kristal\Kristal-Manager
python -m pytest -q tests/test_central_refactor.py tests/test_unified_gui_flow.py
python -m pytest -q
```

La suite complète peut conserver des attentes historiques non conformes au mode local; elles doivent être corrigées **dans les tests et exigences**, pas en contournant le modèle de sécurité.

## Tests de mutation canon

Exécuter un run sur copie des fixtures; comparer hashes des fichiers sous la racine avant/après pour garantir que les opérations de lecture n'y ont rien modifié.
