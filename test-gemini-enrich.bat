@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist "scripts\test_gemini_enrich.py" (
  cd /d "%USERPROFILE%\.hermes\skills\social-media\that-post"
)

if not exist "scripts\test_gemini_enrich.py" (
  echo Could not find scripts\test_gemini_enrich.py
  echo Run this from the That Post folder, or from:
  echo   %USERPROFILE%\.hermes\skills\social-media\that-post
  goto :done
)

echo That Post - Gemini enrich TEST
echo This uses a COPY of the index. Live search is not touched.
echo Working folder: %CD%
echo.

set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined PY if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PY=%LocalAppData%\Programs\Python\Python311\python.exe"
if not defined PY (
  where py >nul 2>&1
  if %errorlevel%==0 set "PY=py -3"
)
if not defined PY set "PY=python"

echo Using %PY%
%PY% scripts\test_gemini_enrich.py %*
goto :done

:done
echo.
pause
