# mediatheque-content

Ce dossier contient **l'état et les données locales** de Médiathèque kOA. Il vit à côté de `mediatheque/` et n'est pas une seconde application.

```text
mediatheque/          # logiciel
mediatheque-content/  # contenu privé/local
```

Contenu principal :

- `01_DB/koa_mediatheque.sqlite` — catalogue local ;
- `02_STORAGE/` — fichiers gérés par Médiathèque ;
- `03_IMPORTS/`, `04_EXPORTS/`, `07_BACKUPS/`, `08_LOGS/` — état runtime ;
- `kristals/` — Kristals locaux à cataloguer ;
- `documents/` — documents locaux référencés ;
- `config.toml` — configuration de ce contenu.

Par défaut, `../mediatheque/Start-KoaGui.ps1` détecte automatiquement ce dossier. `KOA_CONTENT_ROOT` permet de le déplacer ailleurs.
