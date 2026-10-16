# Kristal Manager 0.1.0-alpha.14 — Mise à jour opérationnelle

## Ce qui change

Manager peut **vérifier localement les sources enregistrées** dans les inventaires
Discovery produits par l'Authoring Kit 3.3, détecter les incohérences et rendre
un diagnostic. Il ne transforme pas un diagnostic local en certification canonique.

- Nouvelle commande `python -m kristal_manager verify CHEMIN_DU_KRISTAL`.
- Contrôle en lot : `python -m kristal_manager scan RACINE --verify-sources`.
- Export local : `python -m kristal_manager export RACINE --verify-sources --output inventaire.json`.
- Fenêtre de Manager : sélectionner un Kristal puis cliquer sur
  **Verify selected (local)**.
- Vérification supplémentaire facultative de l'engagement de l'état v9 à l'aide
  du vérificateur du **Framework v10 draft.3.2** fourni séparément :

  `python -m kristal_manager verify CHEMIN_DU_KRISTAL --framework-root DOSSIER_FRAMEWORK`

  Node.js et une copie de confiance du Framework sont nécessaires; aucun
  script n'est téléchargé ou exécuté implicitement.

## Responsabilités conservées

**Authoring Kit** génère/régénère la Discovery; **Framework** fournit les
contrats et validateurs sémantiques; **Manager** observe et coordonne les
contrôles opérationnels; **C1/C2/C3** gardent leurs responsabilités; enfin,
**Konstellation** assure la navigation autorisée.

Si le résultat de Discovery est `stale`, la bonne correction est de **régénérer
les métadonnées dérivées avec Authoring Kit**, sans modifier les engagements
canoniques pour masquer une divergence.

La synchronisation GitHub, la publication et l'activation restent **bloquées**
par sécurité. Aucun statut ne confère une permission de lecture.

## Vérifications

39 tests ciblés réussis. Ancienne suite historique : 14 échecs non masqués,
principalement faute de l'ancien backend GitHub. Catho : état v9 vérifié par
Framework v10, mais Discovery dérivée toujours périmée.

Voir `docs/VALIDATION_MANAGER_ALPHA14.md` et `TEST_REPORT.md`.
