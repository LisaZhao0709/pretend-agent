@echo off
chcp 65001 > nul
echo ===================================================
echo   Starting Predictive Agents Pipeline...
echo ===================================================

cd /d "%~dp0Attempt"
"C:\Users\Xiaol\AppData\Local\Programs\Python\Python311\python.exe" -u run_pipeline.py

echo.
echo ===================================================
echo   Pipeline Finished!
echo ===================================================
pause
