# __TITLE__

**Type :** Local Kristal  
**Workspace :** `kristal.local-workspace/3.2.0`  
**État :** `kristal.state/9.0`

## Travail local

```bash
python tools/kristal.py check .
python tools/kristal.py build-v9 .
```

Le build v9 n'active aucune couche IA par défaut.

## IA / Kompiler (optionnel)

```bash
python tools/kristal.py build-ai .
python tools/kristal.py check-ai .
python tools/kristal.py pack-ai . --output __TITLE__-portable-ai.zip
```

## Backup et publication

- **Kristal Manager** : backup du dossier complet vers un repo GitHub public ou privé.
- **Kristal GitHub Setup / Bootstrap** : qualification, publication et activation réseau.

Backup et publication sont indépendants de l'identité sémantique du state.
