@echo off
title ReTranscription - Installation
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
if errorlevel 1 (
    echo.
    echo L'installation a echoue. Appuyez sur une touche pour fermer...
    pause >nul
)
