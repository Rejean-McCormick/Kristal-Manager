# Typologie des Kristals et compatibilité des lecteurs

## Le piège fondamental

Le contrat d'état d'un Kristal n'est pas automatiquement égal au profil de diagnostic adapté. Les 127 comprennent des états v11 riches et 16 contrats natifs reconnus; KristalDiag embarqué dans le snapshot travaille sur les contrôles V9/V10 du Framework épinglé.

| Cible | Inventaire | Diagnostic applicable | Limite |
|---|---|---|---|
| Artefacts machine V9 présents | `READY`/état local | `V9-State-Reader` puis profils pertinents | PASS n'établit pas C1/C2/C3 |
| Contrat V10 présent | `READY`/nœud/binding | `V10-Node-Reader`, `V10-Full` selon preuves | Un profil host spécifique n'est pas universel |
| Graphe v11 + dictionnaires + crosswalk | contenu observé | Lecteur natif v11 **CIBLE** indépendant | `V9-State-Reader` ne valide pas la sémantique v11 |
| Contrat natif (16 cas) | `native_observed` | Adaptateur de contenu natif **CIBLE**, ou profil connu explicitement | Pas de V9 inventé; `NOT_APPLICABLE` si absent |
| Source historique/auxiliaire | marqué historique | Aucun lot par défaut | Ne pas mélanger aux 127 principaux |

## Matrice d'applicabilité

La règle doit être calculée à partir des **artefacts requis et des capacités connues**, pas uniquement du nom de domaine ou d'une regex de dossier. Chaque profil publie `applicable`, `reason`, `required_inputs`, `missing_inputs`, `supported_versions`.

## Tests contractuels

Un natif seul n'est jamais classé `FAIL V9` faute de fichier non requis; un v11 avec métadonnées V9 n'est pas proclamé « V11 conforme » après V9; les empreintes de fraîcheur de profils différents utilisent des `fingerprint_scope` distincts.
