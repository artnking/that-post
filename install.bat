@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PY="

call :find_python
if defined PY (
  echo Using %PY%
  "%PY%" scripts\setup_local.py
  goto :end
)

echo No real Python 3.11+ on PATH ^(Windows Store shortcut does not count^).
echo Installing Python 3.12 with winget...
winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
  echo winget could not install Python.
  echo Install it from https://www.python.org/downloads/
  echo Check "Add python.exe to PATH", then run install.bat again.
  goto :end
)

call :find_python
if defined PY (
  echo Using %PY%
  "%PY%" scripts\setup_local.py
  goto :end
)

echo Python installed, but this window cannot see it yet.
echo Close this window and double-click install.bat once more.

:end
echo.
pause
exit /b 0

:find_python
set "PY="
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PY=%LocalAppData%\Programs\Python\Python313\python.exe"
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PY=%LocalAppData%\Programs\Python\Python311\python.exe"
if exist "%ProgramFiles%\Python312\python.exe" set "PY=%ProgramFiles%\Python312\python.exe"
if exist "%ProgramFiles%\Python311\python.exe" set "PY=%ProgramFiles%\Python311\python.exe"
if defined PY (
  "%PY%" -c "import sys; raise SystemExit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
  if not errorlevel 1 exit /b 0
  set "PY="
)
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 -c "import sys; raise SystemExit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
  if not errorlevel 1 (
    for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)"') do set "PY=%%I"
    if defined PY exit /b 0
  )
)
exit /b 0
