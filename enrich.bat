@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Run install.bat first.
  pause
  exit /b 1
)

echo That Post - enrich database ^(OpenRouter / gemini-3.5-flash-lite^)
echo.
.venv\Scripts\python.exe scripts\enrich_later.py
echo.
pause
