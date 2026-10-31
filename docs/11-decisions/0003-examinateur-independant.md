# ADR 0003 — KristalDiag est embarqué, mais reste indépendant

**Date** : 2026-10-31 · **Statut** : PRINCIPE OBSERVÉ, extension CIBLE.

## Contexte

Le moteur Diag possède ses propres contrats v9/v10, vérificateurs et modèles de preuve. L'intégrer directement au domaine métier Manager risquerait de redéfinir ses conclusions ou de perdre l'indépendance requise pour examiner les sources.

## Décision

Distribuer une version contrôlée de Diag avec Manager, l'invoquer par subprocess sans shell, valider les fichiers de sortie et conserver les preuves natives. Manager ne modifie pas les verdicts du moteur; il ajoute fraîcheur, indexation, contexte et actions.

## Conséquences

Le moteur conserve ses tests et son release cycle. Les coûts de spawn et des interfaces de version sont assumés. L'absence de moteur est une erreur d'intégration, pas un `FAIL` du Kristal.

## Alternative rejetée

Copier K15/K16 dans le GUI ou transformer les erreurs de subprocess en faux verdicts de conformité. Autre option reportée : service externe permanent, non justifié à cette échelle.

## Validation

Comparer les mêmes fixtures en CLI Diag native et en Manager; mêmes verdicts et preuves, plus métadonnées de provenance Manager. Aucun `--allow-exec` caché.
