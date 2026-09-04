@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY if exist "%LocalAppData%\hermes\hermes-agent\venv\Scripts\python.exe" set "PY=%LocalAppData%\hermes\hermes-agent\venv\Scripts\python.exe"
if not defined PY (
  where py >nul 2>&1
  if %errorlevel%==0 set "PY=py -3"
)
if not defined PY set "PY=python"

echo That Post - sync X bookmarks, posts, likes + enrich new rows
echo Using %PY%
echo.
%PY% scripts\sync_x.py %*
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="2" (
  echo X login expired. Run this once, click Allow in the browser, then run sync.bat again:
  echo   %PY% scripts\auth_x.py
  echo.
)
pause
exit /b %RC%
