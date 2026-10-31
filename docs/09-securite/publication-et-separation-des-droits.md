# Publication, privilèges et intégrité locale

## Principe

**Observer ≠ corriger ≠ approuver ≠ publier ≠ activer**. Ce sont cinq opérations séparées, avec journaux, permissions et confirmations indépendantes. Les scripts d'analyse et le nouveau registre ne doivent jamais déclencher un commit, push, GitHub sync ou activation.

## État historique

`GitSink.bat` a été désactivé pendant une réparation pour empêcher la publication involontaire; des tests historiques peuvent encore attendre un backend de publication. Ne jamais le réactiver pour satisfaire ces tests. La grosse base SQLite de contenu a été retirée de la branche principale Git afin d'éviter un fichier supérieur à 100 Mo; il peut rester dans une **ancienne branche locale de sauvegarde**, mais celle-ci ne doit pas être poussée.

## Autorisations cibles

`OBSERVE` : lecture sources et écriture rapports hors `locals`. `DIAGNOSE` : processus examinateur vérifié. `PROPOSE` : écrit dans index des propositions. `APPROVE` : décision traçable dans registre Manager. `APPLY` : Kit auteur sur plan explicite avec sauvegarde et vérification. `PUBLISH` : chemin séparé, consentement explicite et conditions de sécurité. Les rôles peuvent être localement simples, mais les frontières doivent être réelles dans le code.

## Accès réseau

Pas de réseau implicite pour un scan local. Les alignements Wikidata peuvent nécessiter une consultation externe, mais les correspondances nouvelles doivent conserver leur provenance et statut de validation. Les éventuels plugins/réseaux sont optionnels et désactivés par défaut.

## Contrôles d'intégrité

Comparer hashes source avant/après scans/diag; vérifier schémas et références avant reconstruction; garder l'historique des engagements logiques. Toute opération qui change des octets canoniques déclenche une nouvelle lecture Discovery et invalide les anciens verdicts associés.
