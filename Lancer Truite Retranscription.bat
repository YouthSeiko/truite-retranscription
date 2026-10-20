@echo off
title Truite Retranscription
cd /d "%~dp0"
if exist "TruiteRetranscription\TruiteRetranscription.exe" (
    start "" "TruiteRetranscription\TruiteRetranscription.exe"
    exit /b 0
)
if exist "TruiteRetranscription.exe" (
    start "" "TruiteRetranscription.exe"
    exit /b 0
)
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "app\main.py"
    exit /b 0
)
echo Environnement non installe. Lancez d'abord Installer.bat
pause
