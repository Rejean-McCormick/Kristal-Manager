# Médiathèque kOA

**Médiathèque kOA** est une seule application. Son code et son contenu local sont séparés physiquement, côte à côte :

```text
workspace/
├── mediatheque/          # application, code, schémas, outils, tests
└── mediatheque-content/  # DB, fichiers, Kristals et documents locaux
```

Il n'existe plus de « standalone » et de « local privé » comme deux applications. **C'est la même Médiathèque**. La présence ou l'absence de `mediatheque-content/` détermine seulement si elle ouvre un contenu existant ou démarre avec un contenu vide.

## Démarrage

Depuis `mediatheque/` :

```powershell
./Start-KoaGui.ps1
```

Par défaut, l'application ouvre `../mediatheque-content`. Pour placer le contenu ailleurs :

```powershell
$env:KOA_CONTENT_ROOT = "D:/MonContenuMediatheque"
./Start-KoaGui.ps1
```

## Contenu local

`mediatheque-content/` contient l'état runtime et les données privées :

```text
01_DB/koa_mediatheque.sqlite
02_STORAGE/
03_IMPORTS/
04_EXPORTS/
07_BACKUPS/
08_LOGS/
kristals/
documents/
config.toml
```

Les schémas SQL restent dans l'application sous `mediatheque/schemas/sqlite/`; ils ne sont pas du contenu utilisateur.

Pour créer/indexer un nouveau contenu :

```text
python 05_TOOLS/KoaLocalWorkspace.py plan
python 05_TOOLS/KoaLocalWorkspace.py apply --init-db
```

Les chemins par défaut pointent automatiquement vers le dossier frère `mediatheque-content/`.

## Frontière UCKK

La Médiathèque UCKK reste une implémentation distincte dans Moodle (`mod_uckkarchive`). Elle ne partage ni cette DB SQLite ni ce dossier de contenu. Les échanges avec UCKK restent explicites via manifests/bridges.

## Identité

```text
APP_PUBLIC_NAME = Médiathèque kOA
APP_TECHNICAL_NAME = koa-mediatheque
VERSION = 0.2.1
LAYOUT = one application + adjacent content workspace
```
