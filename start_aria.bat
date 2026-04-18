@echo off
title ARIA - Adaptive Response for In-Cabin Air
echo =============================================
echo  ARIA - Adaptive Response for In-Cabin Air
echo =============================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

echo Starting ARIA server...
echo Browser will open automatically at the detected ARIA URL.
echo If ARIA is already running, this launcher will reuse that instance.
echo.
echo Press CTRL+C in this window to stop the server.
echo.

%PYTHON% app.py

echo.
echo ARIA server stopped.
pause
