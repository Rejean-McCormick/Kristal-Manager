@echo off
cd /d "%~dp0"
set "kristal_scan_root=%~1"
if not defined kristal_scan_root set /p "kristal_scan_root=Dossier contenant les Kristals : "
if not defined kristal_scan_root exit /b 1
python -m kristal_manager catalog "%kristal_scan_root%\." --db "%~dp0catalogue\kristal-content.sqlite3" --overview "%~dp0catalogue\kristal-content.html" --overwrite-overview
if errorlevel 1 (
  echo Echec du scan. Les sources ne sont pas modifiees.
  pause
  exit /b 1
)
start "" "%~dp0catalogue\kristal-content.html"
