@echo off
chcp 65001 >nul 2>&1
title 7D2D Web Manager
echo ============================================
echo   7D2D Server Manager - Web Panel
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Python not found. Please install Python 3.8+
    echo Download: https://www.python.org/downloads/
    pause & exit /b 1
)

:: Install dependencies
echo [1/2] Installing dependencies...
pip install fastapi uvicorn[standard] pyyaml python-multipart websockets -q
if errorlevel 1 (
    echo [Warning] pip install had issues, trying to continue...
)

:: Start web service
echo [2/2] Starting Web service...
echo.
echo  -----------------------------------------------
echo   Local:   http://127.0.0.1:5000
echo   API Doc: http://127.0.0.1:5000/api/docs
echo   LAN:     http://[Server-IP]:5000
echo  -----------------------------------------------
echo   Press Ctrl+C to stop
echo.

python -m web.app
echo.
echo Web service stopped.
pause
