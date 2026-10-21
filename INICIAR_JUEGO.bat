@echo off
chcp 65001 >nul
title Servidor del juego - NO CERRAR mientras juegas
cd /d "%~dp0"
call scripts\preparar_entorno.bat
if not defined PY goto fin
rem El servidor no necesita openpyxl: si no se pudo instalar, el juego arranca igual.
"%PY%" app\servidor.py
:fin
echo.
pause
