@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Aula - Prueba en telefono - Datos temporales
py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
    py -3 -m colegio.phone_demo
) else (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo Instala Python 3.10 o posterior, o usa el instalador de escritorio.
    ) else (
        python -m colegio.phone_demo
    )
)
pause
