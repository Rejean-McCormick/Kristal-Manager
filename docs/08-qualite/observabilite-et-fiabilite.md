# Observabilité, résilience et budgets

## Événements locaux cibles

`scan.started`, `scan.finished`, `catalog.updated`, `diag.requested`, `diag.started`, `diag.finished`, `diag.failed_to_execute`, `observation.recorded`, `observation.stale`, `import.rejected`, `migration.completed`. Chaque événement inclut `run_id`, `workspace_instance_id` éventuel, `engine/profile`, durée et origine. Les logs ne contiennent pas d'assertions ni de secrets par défaut.

## Indicateurs

Nombre d'opérations et échecs, durées p50/p95, taux cache, taille SQLite, nombre d'observations par profil et fraîcheur, créations de rapports, erreurs de validation, cycles GUI bloqués, délais d'annulation et taux de reprise.

## Stratégie résilience

- Timeout borné et budget par niveau; éviter l'exécution concurrente non bornée.
- Retry uniquement pour `ENGINE_ERROR` transitoire; pas de retry automatique d'un `FAIL` métier.
- Panne d'index : rapports et `run_id` suffisants pour réconcilier plus tard.
- Un module en erreur ne bloque pas les autres workspaces.
- Écriture atomique des synthèses, redémarrage sans perte des observations commises.

## Traçage

Un utilisateur doit pouvoir ouvrir un verdict et répondre à : « quel moteur ? », « quel profil ? », « quels fichiers/contrats ? », « à quelle date ? », « quels findings ? », « quel chemin de preuve ? », « actuel ou périmé ? ». C'est un critère technique et UX, pas un luxe de monitoring.

## Confidentialité

Les logs ne doivent pas inclure des fragments de stdout/stderr illimités; les sources peuvent contenir des identifiants ou données privées. Pseudonymiser chemins et noms avant partage public, et garder un manifeste privé pour le diagnostic local.
