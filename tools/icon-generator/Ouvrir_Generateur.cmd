@echo off
setlocal
cd /d "%~dp0"

set "KRISTAL_COLLECTION_ROOT=C:\mycode\Kristal\Kristal-Kollection"

if not exist "%KRISTAL_COLLECTION_ROOT%\" (
  echo [Kristal Icon Generator] Kristal-Kollection introuvable:
  echo   %KRISTAL_COLLECTION_ROOT%
  echo.
  echo Corrige KRISTAL_COLLECTION_ROOT dans Ouvrir_Generateur.cmd si la collection est deplacee.
  pause
  exit /b 2
)

where node >nul 2>&1
if errorlevel 1 (
  echo [Kristal Icon Generator] Node.js est requis.
  echo Installe Node.js puis relance ce fichier.
  pause
  exit /b 3
)

echo [Kristal Icon Generator] Ouverture de l'interface
echo Collection: %KRISTAL_COLLECTION_ROOT%
echo.
echo Les nouveaux Kristals sont scannes puis le Registry est prepare automatiquement.
echo AUCUNE icone ne sera appliquee avant ton clic dans l'interface.
echo.

node "%~dp0server.mjs" --collection "%KRISTAL_COLLECTION_ROOT%"
