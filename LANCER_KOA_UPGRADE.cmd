@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 "KOA_Upgrade.pyw"
) else (
  pythonw "KOA_Upgrade.pyw"
)
if ERRORLEVEL 1 pause
endlocal
