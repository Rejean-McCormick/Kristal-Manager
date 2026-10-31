# Compatibilité normative, vérifications et migration

## Référentiel de contrats

KristalDiag embarqué fournit des schémas et contrôles V9/V10, notamment `K15` (contrats V9), `K16` (engagements), les contrôles V10 `K25`–`K32` et `K14` qui bloque l'acceptation lorsque des exigences requises sont `SKIP`. Le snapshot examiné n'est **pas** un examinateur complet du Framework v11.

## Cas observés historiquement

29 erreurs `K15` ont été constatées sur des capacités V9 (9 doublons, 20 déclarations incompatibles), deux `K16` sur Metrology/Time, 7 avertissements de taille et 1 absence d'artefact V9 pour le modèle monétaire. Des overlays ont ensuite corrigé certaines surfaces. **Seuls des diagnostics refaits sur les sources actuelles établissent l'état présent.**

## Norme de réparation

- Réparer un doublon textuellement identique est différent de déclarer une capacité qui ne fonctionne pas.
- `atomic_activation=true` ne doit être déclaré qu'avec un protocole réellement disponible et démontrable; la présence d'un outil dans le Kit n'est pas, à elle seule, une preuve de publication antérieure.
- Recalcul d'engagement : reconstruire les dérivés, garder les anciennes preuves, vérifier que les références et données sources restent cohérentes.
- V11 : ne pas importer la sémantique de V9 dans les graphes de façon implicite.

## Matrice cible du sélecteur

| Profil | Condition minimale d'applicabilité | Preuve de sortie |
|---|---|---|
| V9 State Reader | fichiers d'état V9 lisibles | `summary.json` + K15/K16 selon profil |
| V10 Node Reader | manifeste/binding v10 | checks V10 propres au profil |
| V10 Full | exigences V9 héritées + V10 complètes | K14 + preuves de bundle |
| Native content | contrat natif reconnu | couverture et limites détaillées |
| V11 semantic | graphes/registre/dictionnaires v11 | cohérence structurale + sémantique seulement si contrôles disponibles |

## Dépendance structurante

Avant de proposer un sélecteur automatique, versionner et tester un **registre d'applicabilité**. Une UI peut afficher les profils possibles, mais ne doit jamais inventer des critères normatifs absents des moteurs.
