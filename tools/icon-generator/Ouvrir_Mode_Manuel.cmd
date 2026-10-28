@echo off
setlocal
cd /d "%~dp0"
set "KRISTAL_COLLECTION_ROOT=C:\mycode\Kristal\Kristal-Kollection"
where node >nul 2>&1 || (echo Node.js introuvable.& pause & exit /b 3)
node "%~dp0server.mjs" --manual --collection "%KRISTAL_COLLECTION_ROOT%"
