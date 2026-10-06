@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Aula - MODO PRUEBA - Datos temporales
py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
    py -3 -m colegio.server --demo --open-browser
) else (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo Instala Python 3.10 o posterior desde https://www.python.org/downloads/windows/
        echo Activa "Add python.exe to PATH" durante la instalacion.
    ) else (
        python -m colegio.server --demo --open-browser
    )
)
pause
