# Registre opérationnel v2 et migration

## Compatibilité

Les tables v1 `workspaces` et `observations` restent présentes. Les nouvelles
entrées v2 sont écrites **dans la même transaction SQLite** que leurs
homologues v1. Les tables additionnelles sont `runs_v2`, `observations_v2`,
`decisions_v2`.

Lors de la première ouverture d'un ancien registre v1, une sauvegarde hors du
flux canonique est créée dans `catalogue/kristal-manager-operations.sqlite3.before-v2.backup`.
Aucune table v1 n'est supprimée. `PRAGMA user_version` passe à 2.
La commande `migrer-index` importe idempotemment les événements historiques v1.

## Métadonnées importantes

- `run_id` : identifiant UUID d'une exécution; étapes et résultat final persistants.
- `kind` : inventory, analysis, diagnostic, arketype, verification, classification.
- `profile` : profil exact, indispensable pour ne pas mélanger V9 et V10.
- `source_scope` : frontière des preuves de fraîcheur.
- `source_fingerprint` : surface bornée de fichiers; ce n'est pas la totalité du canon.
- `qualification` : toujours `NOT_ESTABLISHED` pour les observations locales.
- `evidence_uri` : lien vers un rapport extérieur à la base, pas une preuve autonome.

## Indicateurs de fraîcheur

`CURRENT`: fichier couvert par l'empreinte unchanged (seulement pour les moteurs
pour lesquels la portée de comparaison est suffisante).
`PARTIAL_SCOPE`: empreinte identique, mais couverture sémantique incomplète.
`STALE`: une surface enregistrée est différente.
`UNVERIFIED`: empreinte absente, import non fiable, entrée changeant durant le run.

## Restauration

1. Fermer Manager et confirmer qu'aucun batch n'est en cours.
2. Sauvegarder le fichier de base actuel.
3. Restaurer le fichier de sauvegarde `.before-v2.backup` dans une copie du dépôt
   ou conserver une application Manager compatible v1.
4. Relancer `migrer-index` sur une copie pour vérifier la conversion.

La base de contenu de 189 Mo n'est pas modifiée par cette migration.
