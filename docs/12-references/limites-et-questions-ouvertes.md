# Limites, questions ouvertes et arbitrages à mener

## Questions critiques

1. **Workspaces déplacés** : quelle identité opérationnelle suivre : instance physique ou `state_ref` logique ? Proposition : deux identifiants et table d'alias, avec preuve de déplacement.
2. **Fingerprint v11** : quelles surfaces normatives entrent dans le digest d'un profil de lecture v11 ? À définir avec Kit/Framework, pas à extrapoler de V9.
3. **Natifs** : quels types/versions exacts pour les 16, quelle couverture de contenu minimale et quelles preuves d'absence de lecture ? Compiler depuis les sources.
4. **Catalogue de 189 Mo** : conserver base monolithique ou caches par workspace ? Benchmark avant décision.
5. **KristalDiag distribution** : snapshot embarqué, wheel pin ou sous-module Git ? Le choix doit conserver indépendance, provenance et tests.
6. **PRF-20** : quels 96 cas peuvent recevoir un profil plus spécialisé sans généralisation injustifiée ? Faire revue sur le contenu réel.
7. **ADR de permissions** : approbation locale suffisante ou journal cryptographiquement lié aux plans de mutation ? À trancher avant le workflow `APPLY`.
8. **Import legacy** : quels formats d'anciens ZIP/rapports conserver et pour combien de temps ? Fixer une politique de support.
9. **Concurrence** : séquence par défaut vs pool borné; mesurer I/O et locks Windows sur 127 Kristals.
10. **Compatibilité** : quels OS et versions exactes du Framework/Kits supporter officiellement ? Définir et tester.

## Données absentes du paquet documentaire

Aucun environnement Windows réel n'a été exécuté lors de **cette livraison de documentation**. L'état du dépôt GitHub après le dernier overlay n'a pas été revérifié. Le corpus de notes et scripts de la dernière refonte est analysé comme code fourni, mais les nouvelles API v2 et nouveaux écrans restent des **spécifications cibles**.

## Décisions à prendre avant implémentation

Fixer les conventions d'identité, de fingerprint et de schéma v2; valider les gates P0; approuver la stratégie de vendor Diag; choisir une politique d'export/redaction; confirmer le périmètre de support v11. Sans ces décisions, une « refonte massive » risque surtout de déplacer les doublons.
