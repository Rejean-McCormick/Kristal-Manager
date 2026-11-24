# Lire le contenu — démarrage rapide local

**Fonction disponible dans le snapshot alpha.15 :** balayage descriptif local des Kristals reconnus vers SQLite et génération facultative d’une page HTML hors ligne. Cette fonction ne valide ni ne publie la sémantique canonique.

```powershell
python -m kristal_manager catalog "C:\mycode\Kristal\locals" --db "C:\Catalogues\content.sqlite3" --overview "C:\Catalogues\content.html"
python -m kristal_manager catalog-query Terre --db "C:\Catalogues\content.sqlite3"
```

Dans l’interface, utiliser **Scan content → SQLite + overview**, puis **Open content overview**. Le rapport est descriptif : les données absentes/non prises en charge demeurent **inconnues ou partielles**. La recherche fonctionne dans l’index local; sauvegarder et protéger les fichiers SQLite/HTML créés. Ne pas leur attribuer le statut d’une validation Framework ou d’une publication.

Pour les limites, consulter [le contrat de scanner](docs/CONTENT_CATALOG.md), `kristal_manager/content_catalog.py` et `tests/test_content_catalog.py`.
