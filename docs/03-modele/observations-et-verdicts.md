# Modèle des observations, verdicts et fraîcheur

## Trois axes qui ne doivent jamais se mélanger

1. **Processus** : `QUEUED`, `RUNNING`, `DONE`, `ERROR`, `TIMEOUT`, `CANCELLED`, `NOT_EXECUTED`.
2. **Verdict moteur** : `PASS`, `WARN`, `FAIL`, `BLOCKED`, `SKIP`, `NOT_APPLICABLE`, `UNDETERMINED`; sémantique dépend du `profile`.
3. **Fraîcheur** : `CURRENT`, `STALE`, `UNVERIFIED`, `UNKNOWN` (v1 livré présente `CURRENT` / `STALE_OR_UNVERIFIED`).

Une interface doit afficher par exemple « **FAIL (V9-State-Reader), actuel, 31 oct.** » et non seulement « FAIL ». `NOT_RUN` est un état d'absence d'exécution, pas un verdict de conformité.

## Quand déclarer CURRENT ?

- La preuve contient un fingerprint d'entrée **avec portée connue**.
- La cible existe, le même fingerprint est recalculé sur les mêmes entrées, la vérification est terminée et aucun changement pendant run n'a été détecté.
- Le profile et les contrats à la source du verdict n'ont pas changé de version sans invalidation.
- Un ancien rapport importé sans fingerprint reste `UNVERIFIED`, jamais `PASS CURRENT`.

## Cas spéciaux

Un `PASS` signifie « tous les contrôles requis par ce profil ont réussi sur le périmètre observé », non « toutes les assertions sont correctes ». `BLOCKED` peut indiquer une précondition ou preuve manquante. `NOT_APPLICABLE` doit inclure un motif et proposer le bon profil. `ERROR` du processus n'implique pas `FAIL` du Kristal.

## Projection d'affichage

La fiche expose : dernier verdict actuel par profil; état de processus; date; nombre de findings; preuves; dernière exécution même périmée; action « diagnostiquer à nouveau ». L'historique complet n'est jamais supprimé lors d'un scan.

## Protocole de transition cible

`not_run → queued → running → completed | failed_to_execute | cancelled`, puis une **évaluation indépendante** de fraîcheur. Une modification de source provoque `CURRENT → STALE` sans modifier le verdict historique enregistré.
