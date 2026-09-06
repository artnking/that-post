@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "PY="
set "RC=0"

call :find_python
if not "%PY%"=="" goto :run

echo No Python 3.11+ found. Installing Python 3.12 with winget...
winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
call :add_python_to_path
call :find_python
if not "%PY%"=="" goto :run

echo Waiting a few seconds for the installer to finish writing files...
timeout /t 4 /nobreak >nul
call :add_python_to_path
call :find_python
if not "%PY%"=="" goto :run

echo Could not find python.exe after winget.
echo Looked under:
echo   %LocalAppData%\Programs\Python\
dir /b "%LocalAppData%\Programs\Python" 2>nul
echo Install from https://www.python.org/downloads/
echo Check "Add python.exe to PATH", then run install.bat again.
set "RC=1"
goto :end

:run
echo Using %PY%
"%PY%" scripts\setup_local.py
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" goto :end
echo.
echo Local search:
echo   http://127.0.0.1:8790/
echo Leave the extra window open.
goto :end

:end
echo.
pause
exit /b %RC%

:add_python_to_path
for /d %%D in ("%LocalAppData%\Programs\Python\Python3*") do (
  if exist "%%D\python.exe" set "PATH=%%D;%%D\Scripts;%PATH%"
)
for /d %%D in ("%ProgramFiles%\Python3*") do (
  if exist "%%D\python.exe" set "PATH=%%D;%%D\Scripts;%PATH%"
)
exit /b 0

:find_python
set "PY="
for /d %%D in ("%LocalAppData%\Programs\Python\Python3*") do (
  if exist "%%D\python.exe" (
    "%%D\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
    if not errorlevel 1 (
      set "PY=%%D\python.exe"
      exit /b 0
    )
  )
)
for /d %%D in ("%ProgramFiles%\Python3*") do (
  if exist "%%D\python.exe" (
    "%%D\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
    if not errorlevel 1 (
      set "PY=%%D\python.exe"
      exit /b 0
    )
  )
)
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
  set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
  "%PY%" -c "import sys; raise SystemExit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
  if not errorlevel 1 exit /b 0
  set "PY="
)
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import sys; raise SystemExit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
  if not errorlevel 1 (
    for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)"') do (
      echo %%I | find /i "WindowsApps" >nul
      if errorlevel 1 set "PY=%%I"
    )
    if not "!PY!"=="" exit /b 0
  )
)
for /f "delims=" %%I in ('where python 2^>nul') do (
  echo %%I | find /i "WindowsApps" >nul
  if errorlevel 1 (
    "%%I" -c "import sys; raise SystemExit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
    if not errorlevel 1 (
      set "PY=%%I"
      exit /b 0
    )
  )
)
exit /b 0
