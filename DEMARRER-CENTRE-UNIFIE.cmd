@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m kristal_manager.gui
  exit /b %errorlevel%
)
python -m kristal_manager.gui
exit /b %errorlevel%
