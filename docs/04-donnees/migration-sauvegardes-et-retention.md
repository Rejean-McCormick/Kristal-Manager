# Migrations, sauvegardes, rétention et réparation

## Politique cible

Toute migration SQLite est versionnée, transactionnelle et **non destructive sur le fichier original avant validation**. Empêcher l'ouverture d'une base avec un `user_version` supérieur à la version prise en charge, plutôt que de tenter un downgrade tacite.

## Avant migration

1. Fermer Manager et attendre la fin des processus diag.
2. Capturer hash SHA-256 et taille de la DB opérations; exporter `PRAGMA integrity_check`, `user_version`, métriques de tables.
3. Effectuer `Connection.backup()` vers une sauvegarde datée **hors `locals/`**.
4. Vérifier espace disque, accès en écriture et absence de symlink de sortie.
5. Copier un échantillon de rapports physiques associés aux observations.

## Migration

Appliquer `vN → vN+1` sur copie d'abord; respecter l'append-only logique des observations; gérer les doublons d'événements avec `INSERT OR IGNORE` seulement si les clés sont réellement identiques. Remapper séparément les anciens chemins vers les nouvelles instances par preuve, jamais uniquement par nom.

## Postmigration

Vérifier `integrity_check=ok`, nombre de workspaces, observations par `kind/profile`, proportion CURRENT/STALE/UNVERIFIED, existence des preuves, lignes manquantes, index de recherche, GUI puis CLI; archiver le log de migration.

## Conservation

- Workspaces/canons : **non gérés** par la rétention du Manager.
- Base de contenu : cache reconstructible, supprimer/recréer uniquement par opération explicite.
- Index opérationnel : restaurable depuis rapports et scans, mais l'historique unique doit être sauvegardé.
- Preuves diag : conserver selon politique utilisateur; jamais écrasées sous un nom générique.
- Imports erronés : enregistrer les causes et limiter la taille; ne pas laisser une archive corrompue bloquer l'ensemble.

## Retour arrière

Revenir au code précédent et restaurer la DB sauvegardée en bloc (avec ses journaux SQLite cohérents), ne pas tenter de supprimer au hasard des lignes d'historique. Documenter la procédure Windows dans [incidents](../07-exploitation/incidents-et-retour-arriere.md).
