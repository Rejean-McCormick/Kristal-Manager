# Dette technique, risques et priorités

## Registre initial

| ID | Risque | Impact | Réduction souhaitée |
|---|---|---|---|
| R-01 | Une même observation affichée différemment selon le panneau | Confiance, faux `Not run` | Projection centrale et modèle d'état unique |
| R-02 | Empreinte de fraîcheur v9 prise pour validation v11 | Faux `CURRENT` | `fingerprint_scope` et adaptateurs par famille |
| R-03 | Base `content_catalog` assimilée au canon | Mauvaise autorité | ACL de lecture, provenance, reconstruction explicite |
| R-04 | V9 forcé sur les 16 natifs | Faux `BLOCKED` | Matrice d'applicabilité + `NOT_APPLICABLE` |
| R-05 | Champs proposés promus en vérité | Mauvais ARK/UNESCO/PRF | Workflow approbation/justification distinct |
| R-06 | Opération coûteuse au scan | Attente, blocage GUI | File de tâches, interruption et progression |
| R-07 | Historique SQLite sans migration ni sauvegarde | Perte de preuves | Schémas versionnés, back-up transactionnel |
| R-08 | Overlay remplace un module plus récent | Régression | Manifeste, hashes, comparaison préinstallation |
| R-09 | Données privées exportées dans ZIP ou Git | Fuite | Ignore, détection secrets, sortie minimale |
| R-10 | Processus diag externe modifie la cible | Intégrité | Programme de confiance, empreintes avant/après |
| R-11 | Première génération d'UI couvre mal Windows | Erreurs Tk/chemins | Tests Win PS7/Tk et matrice de compatibilité |
| R-12 | Historique des 127 écrase de nouvelles propositions | Perte décisionnelle | Idempotence + lineage + versionnement de décisions |

## Dépendances critiques

L'index v1 dépend actuellement d'objets dict du GUI; une couche `domain/` typée doit stabiliser les échanges. La GUI est volumineuse et appelle directement plusieurs moteurs. Une migration en strangler (module par module) est plus sûre qu'une réécriture totale d'une traite.

## Stratégie

Priorité P0 : indépendance et autorité, sécurité et migration. P1 : état central, applicability, flux batch, UX dominant. P2 : indexation intelligente, v11 et natifs, optimisation performance. P3 : fonctions avancées/réseau uniquement après autorisation explicite.
