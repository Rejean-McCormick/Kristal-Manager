@echo off
setlocal
if "%~1"=="" (
 echo Usage: RESTAURER_KOA.cmd run-AAAA...
 echo Aucun changement effectue.
 pause
 exit /b 2
)
call "%~dp0KOA_UPGRADE_CLI.cmd" restaurer --campagne "%~1" --confirmer
pause
