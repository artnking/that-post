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

echo Using %PY%
%PY% scripts\publish.py %*
echo.
pause
