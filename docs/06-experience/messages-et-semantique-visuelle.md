# Libellés, messages et états observables

## Libellés proposés

| Machine | Affichage français | Exemple de détail |
|---|---|---|
| `NOT_RUN` | Non exécuté | Aucun résultat pour ce profil |
| `RUNNING` | En cours | 37/127 terminés; profil V9 |
| `PASS` + `CURRENT` | Réussi — actuel | Profil V9-State-Reader, 14 contrôles |
| `FAIL` + `CURRENT` | Échec — actuel | 2 contrôles non satisfaits; consulter preuves |
| `WARN` | Avertissement | Limite de taille; qualité des preuves à voir |
| `STALE` | Périmé | Fichiers d'entrée modifiés depuis le run |
| `UNVERIFIED` | Historique non vérifié | Ancien CSV sans empreinte |
| `NOT_APPLICABLE` | Profil non applicable | Aucun état machine V9 pour ce Kristal |
| `ENGINE_ERROR` | Échec du moteur | Vérifier dépendance / logs; statut du Kristal inconnu |
| `PROPOSED` | Classification proposée | Code valide, interprétation à confirmer |

## Présentation fiable

Toujours mettre ensemble verdict, type de contrôle, date, fraîcheur et provenance. Une étiquette colorée seule n'est pas une preuve. Ne pas présenter `0 warning` comme « 127 validés sémantiquement ». Les colonnes de type « Arketype ? » peuvent garder leurs propositions séparées des décisions officielles du registre.

## Erreurs opérateur

Un échec `jsonschema` doit proposer une installation ciblée plutôt que « Kristal corrompu ». Si une base est indisponible, afficher « Résultats historiques non chargés; scan possible »; après un import d'ancien rapport, préciser « non actuel faute d'empreinte ».

## Messages de sécurité

Avant toute écriture dans `locals` (hors parcours par défaut) : énumérer les fichiers, montrer le plan, sauvegarde et validation manuelle, puis demander une confirmation explicite. La sélection d'un dossier ne constitue jamais une autorisation de modification.
