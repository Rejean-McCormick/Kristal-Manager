# MathChallenges — démarrage

Les noms de dossiers sont **stables** et ne contiennent jamais de numéro de version :

```text
MathChallenges/
├── launch.bat
├── launch.ps1
├── launch.sh
├── diagnose.bat
├── Formulator/
├── Kristal-Grand-Challenges/
├── Kristal-Math/
└── workspace/              # créé automatiquement
```

Les versions logicielles restent dans Git, les manifests, les changelogs et les métadonnées internes. Elles ne font pas partie des chemins.

## Windows

Depuis PowerShell :

```powershell
C:\mycode\MathChallenges\launch.bat
```

ou :

```powershell
C:\mycode\MathChallenges\launch.ps1
```

La console est ensuite disponible sur `http://127.0.0.1:8777/`.

Si le lancement échoue :

```powershell
C:\mycode\MathChallenges\diagnose.bat
```

## Linux / macOS

```bash
./launch.sh
```

Sélectionne ensuite un Challenge dans l'onglet **Overview** et utilise **DO ALL**.
