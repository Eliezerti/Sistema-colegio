@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Aula - Configurar acceso privado
py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
    py -3 -m colegio.network --data-dir "%LOCALAPPDATA%\AulaColegio"
) else (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo Instala Python 3.10 o posterior y activa "Add python.exe to PATH".
    ) else (
        python -m colegio.network --data-dir "%LOCALAPPDATA%\AulaColegio"
    )
)
pause
