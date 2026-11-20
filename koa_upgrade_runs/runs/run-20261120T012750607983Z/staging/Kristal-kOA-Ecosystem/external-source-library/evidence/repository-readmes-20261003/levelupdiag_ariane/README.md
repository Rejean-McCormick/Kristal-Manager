# LevelUpDiag Universal Frame

Suite autonome de diagnostics `.pyw`, dérivée du frame Ariane_Diagnostics mais rendue portable.

## Principe

- Le wrapper lit `levelupdiag_manifest.json`.
- Les niveaux vivent dans `levels/` et restent lançables séparément.
- Le wrapper ne les importe jamais ; il les lance comme processus séparés.
- Tous les paramètres locaux vivent dans `levelupdiag.config.local.json`.
- Pour adapter à une nouvelle app, on change d’abord la config, puis seulement les niveaux spécifiques dans `levels/`.

## Démarrage

```bat
START_LEVELUPDIAG.bat
```

Ou :

```bat
py scriptsun_level.py --list
py scriptsun_level.py N01
py scriptsun_level.py N14 --wait
```

## Structure

```text
levelupdiag_manifest.json          # liste des niveaux
levelupdiag.config.local.json      # paramètres locaux de l’app cible
levelupdiag.config.example.json    # modèle versionnable
levelupdiag_wrapper.pyw            # GUI centrale
levelupdiag_wrapper_common.py      # helpers du wrapper
levelupdiag_core/                  # noyau partagé stable
levels/                            # niveaux remplaçables/adaptables
scripts/                           # CLI et vérification
launchers/                         # .bat par niveau
docs/                              # guides
schemas/                           # schémas JSON
```

## Règle de portage

1. Copier ce dossier comme dépôt diagnostics séparé.
2. Modifier `levelupdiag.config.local.json` pour pointer vers la nouvelle app.
3. Garder `levelupdiag_core/`, `scripts/`, `wrapper` et `manifest` stables.
4. Adapter uniquement les fichiers de `levels/` qui contiennent une logique produit spécifique.
5. Lancer `py scriptserify_repo.py`.

## Convention

Un niveau doit produire un rapport JSON/TXT sous `.levelupdiag/diagnostics/` avec verdict :
`PASS`, `WARN`, `FAIL`, `SKIP`, `BLOCKED`, `PARTIAL`, `ERROR`, `INFRA_ERROR`, `CONFIG_ERROR`.
