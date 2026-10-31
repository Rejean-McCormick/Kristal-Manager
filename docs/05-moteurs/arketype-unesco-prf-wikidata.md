# Évaluation sémantique, ARK / PRF / UNESCO / Wikidata

## Entrées disponibles

Les workspaces locaux disposent de propositions de classification et de profils descriptifs; `RAPPORT_ARKETYPE_STRUCTURE(1).json` apporte une comparaison structurelle de 127 modèles. Des matrices UNESCO et des recoupements Wikidata Q/P ont été produits, avec statuts de provenance variables. **Ces différentes observations ne sont pas automatiquement homologues.**

## Arketype : lecture correcte du rapport

`declared_level` mesure au plus 3 critères de forme. Une `suggestion` avec score 3/3 n'est pas automatiquement meilleure que la déclaration actuelle : le scanner dit explicitement n'avoir inspecté que noms des champs, chemins et récurrence des structures, **jamais le sens des valeurs**. Sur le rapport fourni, 36 cas ont plusieurs candidats, 81 candidats non validés et 10 aucun candidat probant (`ambiguity`).

## UNESCO : deux contrôles distincts

1. **Contrat** : le code, URI, domaine et microthésaurus appartiennent au référentiel.
2. **Sémantique** : ces codes décrivent effectivement le contenu d'un Kristal.

La correction du lecteur UNESCO portait principalement sur des objets de mapping plutôt que de simples chaînes. La présence d'une proposition reconnue doit mener à `PROPOSED`, pas à 127 avertissements de conformité technique.

## PRF : profil d'usage

Les 96 `PRF-20` antérieurs sont des classifications générales et doivent rester identifiables comme telles. L'amélioration ne consiste pas à remplacer tous les PRF par un autre code aléatoire, mais à annoter `confidence`, justification, structures et cas d'usage effectifs, puis à proposer une revue documentée.

## Wikidata

Les QID/PID sont des alignements externes, pas des identités locales interchangeables. Conserver `source`, `mapping_status`, méthode, date, ambiguïtés, collisions et possibilité de rejet. Les conflits de QID partagés entre Kristals ne sont pas résolus par une simple correspondance lexicale.

## Pipeline cible

Lecture → observations → propositions avec preuves → regroupement des conflits → revue/approbation → plan de modification autorisé (Kit) → nouveau Discovery → nouveau scan/diag. **Aucun scan n'applique le plan automatiquement.**
