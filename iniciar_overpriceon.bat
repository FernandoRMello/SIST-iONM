@echo off
cd /d "%~dp0"

title OverpriceON Web Local

echo ========================================
echo   OverpriceON Web Local - FIX4 CLEAN
echo ========================================

where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale o Python 3.11 ou superior.
  pause
  exit /b 1
)

if not exist .venv (
  python -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Sistema local:
echo http://127.0.0.1:8000
echo.
echo Para acesso na rede, use o IPv4 do servidor abaixo na porta 8000:
ipconfig | findstr /i "IPv4"
echo.
start http://127.0.0.1:8000

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

pause
