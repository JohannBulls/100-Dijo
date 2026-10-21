@echo off
rem Prepara el entorno virtual del proyecto (.venv) y deja su Python en la variable PY.
rem Lo usan INICIAR_JUEGO.bat, PROCESAR_EXCEL.bat y EJECUTAR_PRUEBAS.bat.
set "PY=%~dp0..\.venv\Scripts\python.exe"
if exist "%PY%" goto revisar
echo Preparando el entorno del juego por primera vez (puede tardar un minuto)...
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -m venv "%~dp0..\.venv"
) else (
  python -m venv "%~dp0..\.venv"
)
if not exist "%PY%" (
  echo.
  echo No se pudo crear el entorno. Comprueba que Python este instalado:
  echo https://www.python.org/downloads/  ^(marca "Add python.exe to PATH"^)
  set "PY="
  exit /b 1
)
:revisar
"%PY%" -c "import openpyxl" >nul 2>nul
if not errorlevel 1 exit /b 0
echo Instalando dependencias (requirements.txt)...
"%PY%" -m pip install --disable-pip-version-check -q -r "%~dp0..\requirements.txt"
"%PY%" -c "import openpyxl" >nul 2>nul
if errorlevel 1 (
  echo.
  echo No se pudo instalar openpyxl. Revisa la conexion a internet y vuelve a intentarlo.
  exit /b 2
)
exit /b 0
