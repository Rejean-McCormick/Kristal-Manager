# Limites du snapshot source, préexistantes aux corrections UNESCO

Le snapshot du Manager fournit des modules de code, mais le manifeste d’origine
référence des **fichiers binaires non présents** dans l’archive fournie : les sept
éléments `kristal_manager/assets/` et
`tools/icon-generator/runtime/Kristal-v8-full-normalization-overlay.zip`.
Ils ne sont pas remplacés par des données inventées.

Les tests de publication/migration/synchronisation invoquent un backend déjà
marqué **indisponible** dans le snapshot (`core.py`). Les tests associés ne
certifient donc pas ces opérations. Les tests ciblés UNESCO et scanner Node
restent exécutables sans le backend et ne touchent pas aux Kristals de `locals`.

Le fichier `PACKAGE_MANIFEST_SHA256.json` est recalculé sur les **fichiers
réellement présents** dans la livraison et ne promet pas la présence des assets
absents. Une réintégration des binaires originaux, sans modification sémantique,
est nécessaire pour retrouver la totalité de l’interface graphique embarquée.
