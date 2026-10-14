# Kristal Manager — mise à jour du 13 octobre 2026

**Version de ce paquet :** `0.1.0-alpha.13` (sur la base du snapshot alpha.12 fourni).
**Portée :** inventaire local et intégration *expérimentale* avec My Kristals.

## Fait

1. Manager sait lire en mode **lecture seule** les trois fichiers Discovery générés par
   Kristal Authoring Kit 3.3. Les anciens Kristals sans ces fichiers restent pris en charge.
2. Une absence, un jeu incomplet, un format incohérent ou des références/empreintes contradictoires
   sont signalés sans modifier les états canoniques. L'intégrité des fichiers source peut être
   vérifiée sur demande : `python -m kristal_manager inspect <workspace> --verify-discovery`.
3. Un export local **optionnel**, compatible avec le lecteur de prévisualisation actuel de
   Konstellation, est disponible :

   ```powershell
   python -m kristal_manager export-konstellation "C:\mycode\Kristal\locals" --principal-id local-user --output private-konstellation-preview.json
   ```

   L'opérateur doit confirmer que ce principal est autorisé à voir **tous** les titres
   inclus. Manager ne peut pas vérifier cette autorisation ; il n'accorde donc aucun
   droit de consultation aux données internes des Kristals.
4. La GUI Manager affiche désormais l'état Discovery et propose un export My Kristals
   après identification du principal et double confirmation.
5. Tests ciblés : 31 réussis, avec un essai interopérable contre le Kit 3.3 réel et le
   lecteur de preview Konstellation. Voir `TEST_REPORT.md`.

## Changement d'emplacement / nettoyage facultatif

- **Ancien :** `SNAPSHOT_INDEX.txt` à la racine, index figé de l'archive alpha.12.
- **Nouveau :** `docs/snapshots/SNAPSHOT_INDEX_20261013_1042.txt` (copie historique).
- L'ancienne empreinte de paquet a été archivée dans
  `docs/snapshots/PACKAGE_MANIFEST_SHA256_alpha12.json` et un nouveau manifeste
  de paquet a été régénéré.

Après avoir copié/extrait ce paquet dans le dépôt local, ouvrir **`Nettoyer_anciens_fichiers.pyw`**
à la racine uniquement si l'ancien `SNAPSHOT_INDEX.txt` subsiste. L'interface
vérifie son SHA-256 d'origine avant toute suppression, affiche le nom exact et
exige une confirmation. **Aucune suppression automatique** et aucun parcours récursif.
Si le fichier a été modifié localement, l'outil refuse de l'effacer.

## Non fait / limites

- Synchronisation GitHub / publication / activation : **toujours désactivées**.
- Manager n'implémente pas l'authentification ni les règles d'ACL de Konstellation.
- L'export My Kristals n'est **pas** un contrat Framework ratifié.
- Aucun état logique v9, Kristal source ou compte GitHub n'a été modifié.
- GUI Windows et grande échelle : pas de qualification de bout en bout dans cet environnement.
