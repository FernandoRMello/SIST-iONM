@echo off
cd /d "%~dp0"

title OverpriceON Web Local

echo ========================================
echo   OverpriceON Web Local - FIX4 CLEAN
echo ========================================

where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale o Python 3.13.
  pause
  exit /b 1
)

set "VENV_NEEDS_REPAIR=0"
if not exist ".venv\pyvenv.cfg" set "VENV_NEEDS_REPAIR=1"
if not exist ".venv\Scripts\python.exe" set "VENV_NEEDS_REPAIR=1"

if "%VENV_NEEDS_REPAIR%"=="1" (
  echo Preparando o ambiente virtual...
  python -m venv --clear .venv
  if errorlevel 1 (
    echo Nao foi possivel preparar o ambiente virtual.
    pause
    exit /b 1
  )
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.lock
if errorlevel 1 (
  echo Falha ao instalar as dependencias.
  pause
  exit /b 1
)

echo.
echo Sistema local:
echo http://127.0.0.1:8000
echo.
echo Para acesso na rede, use o IPv4 do servidor abaixo na porta 8000:
ipconfig | findstr /i "IPv4"
echo.
start http://127.0.0.1:8000

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

pause
