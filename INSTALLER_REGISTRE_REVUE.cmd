@echo off
setlocal
cd /d "%~dp0"
echo ================================================================
echo KRISTAL MANAGER - Registre de revue non canonique
 echo ================================================================
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" "%~dp0OUTILS-REGISTRE-REVUE\installer_registre.py"
) else (
    py -3 "%~dp0OUTILS-REGISTRE-REVUE\installer_registre.py"
)
if errorlevel 1 (
    echo ECHEC - ne pas forcer d'ecrasement.
) else (
    echo SUCCES - relancer Manager et faire Analyse globale.
)
pause
