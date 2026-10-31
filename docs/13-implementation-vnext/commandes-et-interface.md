# Parcours et commandes exécutables

## GUI

La fenêtre principale possède le bouton **2 · Centre unifié…**. L'ancien centre
est toujours disponible via **Actions > Analyser / diagnostiquer (ancien panneau)**.
Le centre unifié présente un Kristal par ligne et sépare : structure, verdict du
moteur, fraîcheur, analyse, observation ARK et décisions locales.

- `Inventorier` : reconnaît les workspaces; ajoute un run Discovery.
- `Analyser` : utilise le catalogue existant, enregistre les observations globales.
- `Diagnostiquer (V9)` : utilise KristalDiag fourni, un run par lot, et des preuves
  indépendantes des sources. Progression et bouton d'arrêt entre deux Kristals.
- `Importer ARK` : ingère un JSON Arketype structurel sans validation automatique.
- `Importer Diag` : import historique toujours `UNVERIFIED`.
- `Actualiser` : lit SQLite; **ne relance pas les moteurs**.
- Double clic : historique, preuve, profil, limites et décisions.

## CLI

```powershell
cd C:\mycode\Kristal\Kristal-Manager
py -3 -m kristal_manager.unified.cli --help
py -3 -m kristal_manager.unified.cli inventorier --root C:\mycode\Kristal\locals
py -3 -m kristal_manager.unified.cli analyser --root C:\mycode\Kristal\locals
py -3 -m kristal_manager.unified.cli diagnostiquer --root C:\mycode\Kristal\locals --max 3
py -3 -m kristal_manager.unified.cli etat --root C:\mycode\Kristal\locals
py -3 -m kristal_manager.unified.cli exporter --root C:\mycode\Kristal\locals --out C:\mycode\Kristal\bilan-vnext.json
py -3 -m kristal_manager.unified.cli importer-diag C:\mycode\Kristal\BILAN-DIAGNOSTICS.json --root C:\mycode\Kristal\locals
py -3 -m kristal_manager.unified.cli historique C:\mycode\Kristal\locals\Kristal-Accounting --type diagnostic
py -3 -m kristal_manager.unified.cli executions
py -3 -m kristal_manager.unified.cli integrite
```

L'installation facultative `py -3 -m pip install -e ".[diag]"` apporte
`jsonschema` pour le moteur KristalDiag. GUI et CLI sont utilisables
sans cette dépendance pour les opérations autres que le diagnostic V9.
