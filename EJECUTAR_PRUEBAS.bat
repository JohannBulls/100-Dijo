@echo off
chcp 65001 >nul
title Pruebas automaticas del juego
cd /d "%~dp0"
call app\preparar_entorno.bat
if errorlevel 1 goto fin
echo Python usado para las pruebas:
"%PY%" -c "import sys, openpyxl; print(' ', sys.executable); print('  openpyxl', openpyxl.__version__)"
echo.
"%PY%" -m unittest discover -s pruebas -v
:fin
echo.
pause
