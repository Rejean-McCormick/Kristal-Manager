# Plan de migration incrémentale sans réécriture à risque

## Stratégie Strangler Fig

Ajouter les ports/services sous le GUI actuel, puis rediriger les anciens boutons, un parcours à la fois. Un nouveau module ne remplace l'ancien que lorsque **les mêmes fixtures** produisent des sorties équivalentes et que les erreurs sont mieux isolées.

| Étape | Changement | Double fonctionnement transitoire | Critère de bascule |
|---|---|---|---|
| M0 | Manifestes et tests de snapshot | aucun changement runtime | hashes et tests enregistrés |
| M1 | Domaine typé et validation d'observation | anciens dicts convertis aux ports | anciens rapports parsés sans perte |
| M2 | Store v2 sur DB copiée | lecture v1 possible | AC-05/06/07/08/12/18 verts |
| M3 | Centraliser `scan`/`analyze` | anciens menus délégués | même inventaire, aucun duplicate run |
| M4 | Centraliser KristalDiag | panneau individuel et batch délégués | profils/rapports identiques |
| M5 | Ajouter adaptateurs natifs et v11 | V9 gardé indépendant | couverture lisible et contrôles non inventés |
| M6 | Simplifier UX | accès Avancé aux outils legacy | scénario utilisateur complet |
| M7 | Retirer chemins morts | télémétrie locale/fixtures de parité | aucune capacité perdue |

## Stratégie d'overlay

Une livraison de refonte code doit inclure : `manifest.sha256`, fichiers concernés, versions compatibles, sauvegarde du registre et de la config, migration DB en mode aperçu, tests ciblés, procédure de rollback. Ne jamais écrire directement 127 fichiers Kristal depuis le code de déploiement Manager.

## Réversibilité

Jusqu'à M6, conserver un point de retour où anciens modules et ancienne DB restent exploitables. Si les deux voies produisent un statut différent, enregistrer une divergence de validation et ne pas choisir automatiquement la plus favorable.

## Données historiques

Les rapports antérieurs au nouveau schéma peuvent être importés comme archives avec origine et digest. Une absence de fingerprint historique n'est pas réparable par l'ajout d'un timestamp actuel.
