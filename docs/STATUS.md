# État de référence, dates et limites

**Photographie de travail : 31-10-2026.** Ce document explique sur quoi reposent les autres pages.

| Élément | Statut | Preuve examinée | Réserve |
|---|---|---|---|
| Inventaire et analyse globale des 127 locaux | OBSERVÉ | Rapport Manager du 31-10, source `locals` | Les `review` ne sont pas des violations techniques |
| 111 graphes/états et 16 contrats natifs | OBSERVÉ | Analyse globale du 31-10 | Le contenu des 16 natifs est observé partiellement |
| 0 bloqueur et 16 avertissements de couverture | OBSERVÉ | Dernier rapport Manager transmis | Cela ne démontre pas une qualification C1/C2/C3 |
| Comparaison structurelle Arketype des 127 | OBSERVÉ | `RAPPORT_ARKETYPE_STRUCTURE(1).json` | Ne juge pas le sens des valeurs |
| Index opérationnel `central_store.py` | LIVRÉ | Overlay refonte Manager/Diag du 31-10 | À valider sur Windows réel |
| Batch `V9-State-Reader` et CLI unifiée | LIVRÉ | `diagnostics_batch.py`, `operations_cli.py` | Profil v9 seul en batch dans cette livraison |
| Catalogue global sémantique | OBSERVÉ | `content_catalog.py`, SQLite dérivé distinct | Base volumineuse, pas une vérité canonique |
| Lecture profonde v11 et natif avec profils appropriés | CIBLE | Découpage prévu dans `/docs` | Pas couvert par le batch V9 seul |
| Migrations schema v2, retenue, reprise robuste | CIBLE | Contrats de cette documentation | Requiert implémentation et tests |
| Qualification Framework complète | NON ÉTABLIE | Diagnostic indépendant requis | Aucune extrapolation depuis `READY` |

**Résultats Arketype mesurés** : 28 observations `3/3`, 49 `2/3`, 14 `1/3`, 33 `0/3`, 3 indéterminées; 36 cas avec plusieurs candidats. Les 127 entrées déclarent un Arketype, ce qui **ne veut pas dire** que Manager a validé ces déclarations.

**Données manquantes** : installation exacte sous Windows après les différents overlays, état Git courant, compatibilité de tous les modules sous Tk Windows, couverture intégrale des cas v11, cartographie complète des champs de schéma métier. Toute décision dépendante de ces éléments reçoit un test de sortie explicite dans [la feuille de route](10-evolution/roadmap.md).

**Politique documentaire** : exemples d'API sous la mention « CIBLE » ne doivent pas être traités comme commandes actuelles; les seules commandes réellement présentes dans le dernier overlay sont indiquées comme **LIVRÉ**.

## Mise à jour vNext (code livré après la documentation initiale)

- **LIVRÉ** : schéma opérationnel v2 additif, journal des runs, observations
  profilées, décisions locales et imports historiques non vérifiés.
- **LIVRÉ** : interface unifiée, extraction de preuves et annulation coopérative V9.
- **ENCORE CIBLE** : examen profond natif et v11, signature, profils transversaux
  et suite historique intégralement verte.
- **TESTÉ** : Linux/Xvfb; **NON VÉRIFIÉ sur Windows réel** à cette date.

Voir [`13-implementation-vnext`](13-implementation-vnext/README.md).
