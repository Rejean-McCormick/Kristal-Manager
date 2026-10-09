@echo off
setlocal
cd /d "%~dp0"
where pyw >nul 2>nul
if %errorlevel%==0 (
  pyw -3 Kristal-Manager.pyw
  exit /b %errorlevel%
)
where pythonw >nul 2>nul
if %errorlevel%==0 (
  pythonw Kristal-Manager.pyw
  exit /b %errorlevel%
)
echo Python 3 was not found on PATH.
pause
exit /b 1
