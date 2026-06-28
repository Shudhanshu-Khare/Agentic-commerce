@echo off
echo ==========================================
echo Cleaning Agentic Commerce Cache...
echo ==========================================

:: 1. Kill stray processes
echo [1/3] Terminating any hanging browsers or python tasks...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM chromium.exe /T >nul 2>&1

:: 2. Delete temporary python files
echo [2/3] Clearing __pycache__ folders...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

:: 3. Clear any leftover logs (optional)
echo [3/3] Removing temporary log files...
if exist scraper_debug.log del /f /q scraper_debug.log
if exist scraper_error.txt del /f /q scraper_error.txt

echo.
echo ==========================================
echo Cleanup Complete! You can now run .\start
echo ==========================================
pause
