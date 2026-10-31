# Kristal Manager vNext — code source complet

Application locale **sans publication automatique** pour inventorier et examiner des Kristals.
Le moteur KristalDiag est fourni dans `tools/KristalDiag/`, mais est lancé en
sous-processus; son protocole et ses profils restent identifiables séparément.

## Démarrer sous Windows / PowerShell 7

1. Python 3.11 ou plus récent; la GUI nécessite Tkinter.
2. Dans `C:\mycode\Kristal\Kristal-Manager` :

   ```powershell
   py -3 -m pip install -e ".[diag]"
   .\Launch-Kristal-Manager.cmd
   ```

3. Cliquer **Centre unifié** et choisir le dossier `C:\mycode\Kristal\locals`.
4. `1 · Inventorier` → `2 · Analyser` → `3 · Diagnostiquer (V9)`.
   Les contrats natifs et v11 dépourvus de V9 sont marqués `NOT_APPLICABLE`,
   non `PASS`.

## CLI vNext

```powershell
py -3 -m kristal_manager.unified.cli inventorier --root C:\mycode\Kristal\locals
py -3 -m kristal_manager.unified.cli etat --root C:\mycode\Kristal\locals
py -3 -m kristal_manager.unified.cli diagnostiquer --root C:\mycode\Kristal\locals --max 3
py -3 -m kristal_manager.unified.cli analyser --root C:\mycode\Kristal\locals
py -3 -m kristal_manager.unified.cli importer-arketype RAPPORT_ARKETYPE_STRUCTURE.json
py -3 -m kristal_manager.unified.cli migrer-index
py -3 -m kristal_manager.unified.cli integrite
```

## Emplacements et règles

- **Sources** : `../locals/` (jamais modifiées par le centre unifié).
- **Observations** : `catalogue/kristal-manager-operations.sqlite3` (dérivées, non canoniques).
- **Catalogue lourd** : `catalogue/kristal-contenu-global.sqlite3` (séparé du registre).
- **Rapports** : dossiers locaux de preuves hors `locals/`.
- **Avant migration de v1 vers v2** : sauvegarde `*.before-v2.backup` locale.
- **GitSink** : bloqué par défaut. Aucun auto-push, activation ou GitHub.

La documentation de référence est dans [`docs/README.md`](docs/README.md).
La documentation spécifique à la version présente est dans
[`docs/13-implementation-vnext/README.md`](docs/13-implementation-vnext/README.md).

## Vérité et limites

Un verdict `PASS` est celui du profil précis du moteur, **pas** la conformité
Framework C1/C2/C3. `CURRENT` signifie seulement que les surfaces couvertes
par l'empreinte choisie n'ont pas changé. `PARTIAL_SCOPE` indique une couverture
incomplète. Un import de diagnostic externe reste `UNVERIFIED`.

Voir [`docs/13-implementation-vnext/qualification-et-tests.md`](docs/13-implementation-vnext/qualification-et-tests.md)
pour les résultats de tests et limites connues. Cette distribution a été assemblée
à partir d'un snapshot Manager; vérifiez avant fusion avec toute branche plus récente.
