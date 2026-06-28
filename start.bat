@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo ==========================================
echo Starting Agentic Commerce...
echo ==========================================

if exist ".\venv\Scripts\streamlit.exe" (
    ".\venv\Scripts\streamlit.exe" run app.py
) else if exist ".\venv\Scripts\python.exe" (
    ".\venv\Scripts\python.exe" -m streamlit run app.py
) else if exist ".\.venv\Scripts\streamlit.exe" (
    ".\.venv\Scripts\streamlit.exe" run app.py
) else if exist ".\.venv\Scripts\python.exe" (
    ".\.venv\Scripts\python.exe" -m streamlit run app.py
) else (
    python -m streamlit run app.py
)

pause
