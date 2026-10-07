@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Aula - PC principal - Colegio y casa
if not exist "%LOCALAPPDATA%\AulaColegio\red.json" (
    echo Primero ejecuta Configurar-Red.bat en esta PC.
    pause
    exit /b 1
)
py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
    py -3 -m colegio.server --data-dir "%LOCALAPPDATA%\AulaColegio" --network-config "%LOCALAPPDATA%\AulaColegio\red.json" --open-browser
) else (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo Instala Python 3.10 o posterior y activa "Add python.exe to PATH".
    ) else (
        python -m colegio.server --data-dir "%LOCALAPPDATA%\AulaColegio" --network-config "%LOCALAPPDATA%\AulaColegio\red.json" --open-browser
    )
)
pause
