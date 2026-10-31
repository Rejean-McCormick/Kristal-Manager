# Ingestion des scanners vers le registre central

## Problème résolu

Les moteurs produisent des sorties hétérogènes, parfois temporaires : liste de scan, rapport JSON global, preuves KristalDiag, Arketype structurel, revue historique, audits UNESCO. Le consolidateur doit créer une observation cohérente **sans modifier la source ni effacer sa provenance**.

## Pipeline cible

1. **Discover** : identifier workspaces et `state_ref` avec collision/renommage explicites.
2. **Read & bound** : vérifier taille maximale, JSON/CSV, existence et chemin sous répertoire autorisé.
3. **Validate format** : schéma attendu, moteur/version, cible, profil, digest des preuves.
4. **Normalize** : convertir vers le contrat Manager, conserver `raw_report_ref`, `source_scope`, `limitations`.
5. **Correlate** : associer workspace instance et état logique sans fusion hasardeuse.
6. **Persist** : commit atomique de `run` et des observations; idempotence à la réimportation.
7. **Project** : mettre à jour vues « dernier courant », « dernier historique », « à traiter ».
8. **Display** : notifier l'UI, mais ne jamais recalculer localement un verdict dans la présentation.

## Adaptateurs livrés

- `record_analysis(report)` lit les `entries` du rapport global.
- `record_arketype_batch(report)` garde comparaison, scores, limites et structure du rapport Arketype.
- `record_diagnostic(...)` conserve profil, verdict, fingerprint et rapport partiel; `restore_rows(...)` restaure uniquement les diagnostics jugés actuels.
- `import_legacy_diagnostic_csv(...)` convertit les anciens CSV en historique non vérifié.

## Évolutions nécessaires

L'API de `latest()` v1 sélectionne par `kind`, pas par profil : **CIBLE** sélectionner `kind + profile + engine + fingerprint_scope`, et séparer une exécution erronée d'une preuve précédente valide. Introduire une file de tâches interne avec état persistant, seulement après avoir fixé la sémantique de run.

## Invariants de consolidation

Ne pas inventer `PASS` quand `summary` absent; ne pas interpréter un résultat Arketype `3/3` comme une certification; ne pas transformer « UNESCO proposé » en anomalie technique; ne pas perdre l'ancien résultat lorsqu'une nouvelle ingestion échoue.
