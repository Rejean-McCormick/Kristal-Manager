# Ariane Diagnostics

Suite autonome de consoles locales `.pyw` pour diagnostiquer le projet cible Ariane.

Le dépôt fournit :

* un **wrapper GUI central** pour choisir et lancer les niveaux ;
* des consoles `.pyw` séparées dans `levels/` ;
* un manifest central `ariane_diag_manifest.json` ;
* un noyau partagé progressif `ariane_diag_core/` ;
* des scripts de lancement, vérification et diagnostic local.

## Racines à distinguer

```text
Dépôt diagnostics : C:\mycode\Ariane\Ariane_Diagnostics
Dépôt Ariane cible : C:\mycode\Ariane\Ariane
```

Cette application vit dans `Ariane_Diagnostics`, mais les niveaux diagnostiquent par défaut le dépôt cible `Ariane`.

## Structure

```text
Ariane_Diagnostics/
  README.md
  START_ARIANE_DIAGNOSTICS.bat
  ariane_diag_wrapper.pyw
  ariane_diag_wrapper_common.py
  ariane_diag_manifest.json
  ariane_diag_core/
  levels/
  scripts/
  launchers/
  tests/
  docs/
```

## Lancer le wrapper GUI

Double-cliquer :

```text
START_ARIANE_DIAGNOSTICS.bat
```

Ou lancer manuellement :

```powershell
cd C:\mycode\Ariane\Ariane_Diagnostics
pyw .\ariane_diag_wrapper.pyw
```

Mode debug avec console :

```powershell
cd C:\mycode\Ariane\Ariane_Diagnostics
py .\ariane_diag_wrapper.pyw
```

Le wrapper GUI permet de :

* lire `ariane_diag_manifest.json` ;
* afficher les niveaux N00 à N12 ;
* changer de niveau ;
* lancer le niveau sélectionné ;
* lancer un niveau en mode console/debug ;
* ouvrir `levels\`, `docs\` et `.ariane-control\` ;
* lancer la vérification du dépôt si `scripts\verify_repo.py` est présent.

Le wrapper ne remplace pas les fichiers dans `levels\`. Il les lance comme processus séparés afin de conserver leur propre fenêtre Tkinter et leur propre cycle de vie.

## Lancer un niveau sans wrapper

Double-cliquer un fichier dans `levels/`, ou lancer :

```powershell
py scripts\run_level.py N12
```

Lister les niveaux disponibles :

```powershell
py scripts\run_level.py --list
```

Vérifier la structure du dépôt :

```powershell
py scripts\verify_repo.py
```

## Diagnostic PowerShell 7

Diagnostic standard :

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\diag_ps7.ps1
```

Diagnostic strict :

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\diag_ps7.ps1 -Strict
```

Avec vérification Node/pnpm pour les niveaux Playwright :

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\diag_ps7.ps1 -WithPlaywrightToolchain
```

Avec vérification du dépôt cible Ariane :

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\diag_ps7.ps1 -WithTarget
```

Launcher double-clic :

```text
launchers\diag_ps7.bat
```

## Pytest local

Des tests de structure sont fournis :

```powershell
py -m pytest -q
```

Ils valident notamment :

* le manifest N00 à N12 ;
* l’existence des fichiers `.pyw` ;
* la compilation Python des scripts/core/niveaux ;
* les launchers `.bat`.

## Niveaux

| Niveau | Fichier                                                | Rôle                                        |
| -----: | ------------------------------------------------------ | ------------------------------------------- |
|    N00 | `levels/00-ariane_control_panel.pyw`                   | Control panel backend/frontend              |
|    N01 | `levels/01-ariane_global_diag_console.pyw`             | Santé locale générale                       |
|    N02 | `levels/02-ariane_deep_diag_console.pyw`               | Cohérence profonde frontend/backend/OpenAPI |
|    N03 | `levels/03-ariane_ui_browser_probe_console.pyw`        | Smoke navigateur                            |
|    N04 | `levels/04-ariane_playwright_route_diag_console.pyw`   | Routes Playwright réelles/dynamiques        |
|    N05 | `levels/05-ariane_ux_flow_diag_console.pyw`            | Interactions UX sûres                       |
|    N06 | `levels/06-ariane_api_contract_diag_console.pyw`       | Contrat API                                 |
|    N07 | `levels/07-ariane_mock_state_diag_console.pyw`         | États limites UI                            |
|    N08 | `levels/08-ariane_a11y_keyboard_diag_console.pyw`      | Accessibilité/clavier                       |
|    N09 | `levels/09-ariane_visual_regression_diag_console.pyw`  | Régression visuelle                         |
|    N10 | `levels/10-ariane_performance_budget_diag_console.pyw` | Performance budgets                         |
|    N11 | `levels/11-ariane_release_gate_console.pyw`            | Release gate                                |
|    N12 | `levels/12-ariane_app_scan_cards_diag_console.pyw`     | Scan app → Atlas → cartes Console           |

## Variables utiles

```powershell
$env:ARIANE_TARGET_REPO_ROOT="C:\mycode\Ariane\Ariane"
$env:ARIANE_BACKEND_URL="http://127.0.0.1:8000"
$env:ARIANE_FRONTEND_URL="http://localhost:5173"
```

## Documentation

* `docs/WRAPPER_GUI.md`
* `docs/GUIDE_COMPLET_ARIANE_DIAGNOSTICS_N00_N12.md`
* `docs/DIAG_PS7.md`
* `docs/REPO_LAYOUT.md`
* `docs/MIGRATION_N00_N12.md`

## Notes

* Le wrapper GUI est l’entrée recommandée pour lancer les niveaux.
* Les fichiers `.pyw` restent séparés pour faciliter les corrections ciblées.
* Le wrapper ne doit pas importer directement les fichiers dans `levels\`; il doit les lancer via `pyw` ou `py`.
* `ariane_diag_core/` est ajouté comme noyau partagé pour les prochains refactors.
* Les suffixes de téléchargement `(1)`, `(2)`, `(3)` ont été retirés des noms de fichiers.
* Les artefacts locaux sont écrits dans `.ariane-control\`.
