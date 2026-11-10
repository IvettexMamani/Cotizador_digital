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
call :instalar || goto error

:ejecutar
if not exist ".env" copy ".env.example" ".env" >nul
echo.
echo Abriendo el Cotizador Digital en el navegador...
echo Para detenerlo, cierra esta ventana.
echo.
".venv\Scripts\streamlit.exe" run app\streamlit_app.py
goto :eof

:instalar
rem Intento normal.
".venv\Scripts\python.exe" -m pip install --retries 1 --upgrade pip
".venv\Scripts\python.exe" -m pip install --retries 1 -r requirements.txt && exit /b 0
rem Plan B: algunos antivirus (por ejemplo, Avast) inspeccionan las conexiones
rem seguras y pip no reconoce su certificado. Se reintenta con los certificados
rem de Windows, los mismos que usa el navegador.
echo.
echo La descarga fallo. Reintentando con los certificados de Windows...
echo.
".venv\Scripts\python.exe" -c "import ssl; c = ssl.create_default_context(); open('.venv/certs_windows.pem', 'w').write(''.join(ssl.DER_cert_to_PEM_cert(d) for d in c.get_ca_certs(True)))" || exit /b 1
".venv\Scripts\python.exe" -m pip install --cert .venv\certs_windows.pem --upgrade pip || exit /b 1
".venv\Scripts\python.exe" -m pip install --cert .venv\certs_windows.pem -r requirements.txt || exit /b 1
exit /b 0

:error
echo.
echo Hubo un error durante la instalacion. Revisa el mensaje de arriba
echo y la seccion "Problemas frecuentes" del README.
pause
exit /b 1
