@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 -m koa_upgrade.cli %*
) else (
  python -m koa_upgrade.cli %*
)
exit /b %ERRORLEVEL%
