@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Cierra Aula antes de continuar. Esta herramienta recupera una cuenta administradora local.
py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
    py -3 -m colegio.reset_password --data-dir "%LOCALAPPDATA%\AulaColegio"
) else (
    python -m colegio.reset_password --data-dir "%LOCALAPPDATA%\AulaColegio"
)
pause
