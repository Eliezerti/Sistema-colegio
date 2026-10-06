@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Aula - Restaurar respaldo
echo Cierra la ventana de Aula antes de restaurar.
py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
    py -3 -m colegio.restore --data-dir "%LOCALAPPDATA%\AulaColegio"
) else (
    python -m colegio.restore --data-dir "%LOCALAPPDATA%\AulaColegio"
)
pause
