# Parcours de bout en bout et scénarios UX

## Scénario A — premier scan

1. Ouvrir Manager → choisir `C:\mycode\Kristal\locals`.
2. Lancer **Inventorier**; afficher progression et résultats par workspace.
3. Voir 127 lignes avec `READY`, profil et fraîcheur; afficher « Pas de diagnostic actuel » le cas échéant.
4. Sélectionner « À diagnostiquer », prévisualiser nombre de profils applicables, `NOT_APPLICABLE` et estimation qualitative du coût.
5. Lancer explicitement, suivre et ouvrir les preuves d'un résultat.

**Critères** : aucun lancement caché, aucune perte de sélection, `NOT_RUN` distinct de `FAIL`.

## Scénario B — reprendre après redémarrage

Redémarrer Manager, rescanner. Les résultats enregistrés réapparaissent **sans exécution**, avec leur profil et leur fraîcheur. Si une entrée a changé, montrer `STALE` et le dernier verdict historique dans la fiche, non un `PASS` actuel.

## Scénario C — classer sans maquiller

Ouvrir un Kristal avec `UNESCO PROPOSED`, examiner code/domaine/preuves, choisir « accepter », « rejeter » ou « approfondir ». La décision est datée, attribuée, et n'est **pas automatiquement écrite au canon**. Une action distincte prépare un plan Kit avec sauvegarde.

## Scénario D — contrat natif

La fiche indique « contrat natif reconnu, lecture contenu partielle ». Le bouton Diag V9 affiche **non applicable** si les artefacts requis manquent; le centre propose une analyse de contenu natif, pas un contournement.

## Scénario E — panne et reprise

Interrompre un batch après 37 Kristals. Les 37 résultats confirmés restent consultables, les autres sont `PENDING/NOT_RUN`. La relance cible les entrées non faites ou périmées; une erreur du moteur n'efface pas les résultats plus anciens.

## Scénario F — export et audit

Exporter un ZIP de synthèse avec manifeste, statuts, sources et dates, et des liens vers preuves locales; avertir si des données privées sont incluses. Aucun push ou publication automatique.
