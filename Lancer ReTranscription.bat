@echo off
title ReTranscription
cd /d "%~dp0"
if exist "ReTranscription.exe" (
    start "" "ReTranscription.exe"
    exit /b 0
)
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "app\main.py"
    exit /b 0
)
echo Environnement non installe. Lancez d'abord Installer.bat
pause
