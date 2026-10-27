# Scanner le contenu de tes cristaux

Manager avait un inventaire technique. Cette version ajoute un **catalogue du contenu**, une base SQLite consultable et un aperçu HTML local.

**Raccourci Windows :** double-clique `Scanner_Contenu.cmd`, ou glisse le dossier contenant tes cristaux sur ce fichier. Le catalogue et son aperçu seront enregistrés dans le sous-dossier `catalogue` du Manager.

Pour utiliser l’interface :

1. Lance `Kristal-Manager.pyw`.
2. Choisis le dossier contenant tes cristaux.
3. Clique **Scan content → SQLite + overview** et choisis où enregistrer la base, en dehors des dossiers des cristaux.
4. Clique **Open content overview** pour consulter les fiches et les filtrer.

Le catalogue montre le domaine déclaré, le modèle, les concepts les plus décrits, les relations fréquentes, les volumes, les sources, les données Wikidata et les éléments manquants ou non pris en charge. Les fréquences ne sont pas un jugement d'importance éditoriale.

Les scans suivants réutilisent les observations dont les fichiers sélectionnés sont inchangés. Les graphes historiques ne sont pas additionnés au graphe actif. Aucun fichier du cristal n'est modifié.

La page HTML filtre les aperçus. Pour chercher parmi tous les concepts de la base :

```text
python -m kristal_manager catalog-query Terre --db C:\Catalogues\kristal-content.sqlite3
```

Un exemple calculé sur les 16 cristaux Wikidata est fourni dans `exemple-16-cristaux`. Ouvre sa page HTML pour voir le résultat avant de scanner tes propres dossiers. Sa base est un exemple provenant de cette session; rescanner tes dossiers crée des observations adaptées à tes chemins locaux.

Les détails techniques et les limites figurent dans `docs/CONTENT_CATALOG.md`. Ce scanner décrit ce qu'il observe; il ne certifie pas la vérité des données.
