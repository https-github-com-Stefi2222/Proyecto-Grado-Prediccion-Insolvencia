@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=%~dp0.venv-demo\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo ERROR: No se encontro el entorno virtual .venv-demo.
    echo Sigue la GUIA_INSTALACION_DEMO.md antes de iniciar.
    pause
    exit /b 1
)
"%PYTHON%" "%~dp0demo\interfaz_sustentacion.py"
if errorlevel 1 (
    echo.
    echo La demostracion termino con un error. Revisa el mensaje anterior.
    pause
)
endlocal
