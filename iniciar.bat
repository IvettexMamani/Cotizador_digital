@echo off
rem Cotizador Digital - inicio con doble clic en Windows.
rem La primera vez crea el entorno e instala las librerias (varios minutos).
rem Las siguientes veces solo abre la app.
setlocal
cd /d "%~dp0"
title Cotizador Digital

echo ================================================
echo   Cotizador Digital
echo ================================================
echo.

if exist ".venv\Scripts\streamlit.exe" goto ejecutar

echo Primera vez: preparando el entorno. Puede tardar varios minutos...
echo.
set "PYTHON="
py -3.11 --version >nul 2>&1 && set "PYTHON=py -3.11"
if not defined PYTHON python --version >nul 2>&1 && set "PYTHON=python"
if not defined PYTHON (
    echo No se encontro Python.
    echo Instala Python 3.11 desde https://www.python.org/downloads/
    echo y marca la casilla "Add python.exe to PATH". Luego vuelve a abrir este archivo.
    pause
    exit /b 1
)

%PYTHON% -m venv .venv || goto error
".venv\Scripts\python.exe" -m pip install --upgrade pip || goto error
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto error

:ejecutar
if not exist ".env" copy ".env.example" ".env" >nul
echo.
echo Abriendo el Cotizador Digital en el navegador...
echo Para detenerlo, cierra esta ventana.
echo.
".venv\Scripts\streamlit.exe" run app\streamlit_app.py
goto :eof

:error
echo.
echo Hubo un error durante la instalacion. Revisa el mensaje de arriba
echo y la seccion "Problemas frecuentes" del README.
pause
exit /b 1
