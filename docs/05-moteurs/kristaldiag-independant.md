# KristalDiag intégré, mais examinateur indépendant

## Séparation fonctionnelle

KristalDiag reste propriétaire de ses profils, critères, ressources contractuelles, prérequis, verdicts natifs et format de preuve `kristaldiag.summary.v1`. Manager orchestre sa sélection, son lancement et sa persistance; **Manager ne réimplémente pas K15/K16/K25/K29 pour rendre l'interface plus simple**.

## Constat dans le code du 31-10

`diag_bridge.bundled_kristaldiag()` vise `tools/KristalDiag/kristaldiag.py`. Le bridge lance un subprocess Python avec `conform TARGET --profile PROFILE --control-dir DIR --json`, `shell=False`, timeout, fichiers de sortie bornés et capture du fingerprint avant/après. Il vérifie `schema='kristaldiag.summary.v1'`, `tool='KristalDiag'`, `target_root` et `profile` avant d'accepter le verdict. Les profils du panneau sont `V9-State-Reader`, `V10-Node-Reader`, `V10-Full`; le batch livré accepte **uniquement** `V9-State-Reader`.

## Évolution cible

Créer un registre de profils lus depuis un manifeste **signé ou épinglé à une distribution digne de confiance**, jamais depuis un Kristal scanné; chaque entrée déclare : `id`, contrat, préconditions, inputs, version du moteur, contrôles couverts, temps maximum, `read_only`, permissions requises. Le centre suggère un profil adapté sans l'exécuter sans action explicite.

## Sémantique des erreurs

- `TIMEOUT` : problème d'exécution/temps, pas échec de conformité.
- `EXECUTION_ERROR` : moteur absent, exception, rapport non validé.
- `NOT_APPLICABLE` : profil exclu par conditions, avec motif.
- `PASS/WARN/FAIL/BLOCKED` : verdict du moteur et **seulement** pour les checks inclus.
- Source changée pendant exécution : rapport conservé, jamais `CURRENT`.

## Indépendance et sécurité

Le snapshot KristalDiag vise Framework 10.0.0-draft.3.1 et emporte ses propres contrats gelés. Il ne faut pas remplacer les contrats indépendants par des schémas « trouvés » dans le Kristal examiné. Les commandes pouvant exécuter du code ciblé (`--allow-exec`) restent exclues du parcours par défaut.

## Compatibilité de versions

Le futur Manager doit garder la provenance du commit/snapshot Diag et de la version Framework épinglée. En cas de divergence majeure, afficher « profil non supporté » et orienter vers le bon outil, plutôt qu'inventer une conformité.
