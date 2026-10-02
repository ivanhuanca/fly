@echo off
setlocal
set "PYTHONW=%~dp0.venv\Scripts\pythonw.exe"
if exist "%PYTHONW%" (
    start "" "%PYTHONW%" "%~dp0fly.py"
    exit /b
)
where pythonw >nul 2>&1
if errorlevel 1 (
    echo No se encontro Python con Tkinter. Instala Python para Windows e intenta de nuevo.
    pause
    exit /b 1
)
start "" pythonw "%~dp0fly.py"