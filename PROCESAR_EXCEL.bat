@echo off
chcp 65001 >nul
title Procesar el Excel de respuestas
cd /d "%~dp0"
call scripts\preparar_entorno.bat
if errorlevel 1 goto fin
echo Leyendo el Excel (no se modifica) y generando la carpeta "datos"...
echo.
"%PY%" app\procesar_excel.py
:fin
echo.
pause
