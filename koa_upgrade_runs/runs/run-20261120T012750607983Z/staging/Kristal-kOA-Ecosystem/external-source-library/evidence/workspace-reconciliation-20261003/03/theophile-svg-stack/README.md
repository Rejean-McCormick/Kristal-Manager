# THÉOPHILE — SVG stack avec GUI + animations

Ce package part du `.zip` fourni et conserve une interface de réglage dans `index.html`.

## Important

Le layer T a été remplacé par le bon fichier :

```txt
public/logo-layers/layer-03-t.svg
```

## Lancer le GUI local

Double-clique :

```txt
launch-preview.bat
```

Puis ouvre :

```txt
http://localhost:8765/index.html
```

## Ce que le GUI permet

- Corriger `x`, `y`, `scale`, `opacity`, `rotate`, `zIndex`
- Corriger les animations : `type`, `delay`, `duration`, `fromOpacity`, `toOpacity`, `fromScale`, `toScale`
- Rejouer l’animation
- Afficher le final statique
- Exporter `placements.export.json`
- Importer un JSON corrigé

## Baking SVG après correction

Après avoir exporté ton JSON depuis le GUI :

1. Mets `placements.export.json` à la racine du dossier.
2. Lance `bake-svg-transforms.bat`.

Les SVG corrigés sortiront dans `output-corrected/`.
