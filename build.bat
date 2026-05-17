@echo off
cd /d "%~dp0"

echo [1/3] Installing PyInstaller...
pip install pyinstaller --quiet
if errorlevel 1 ( echo ERROR: pip failed & pause & exit /b 1 )

echo [2/3] Cleaning old build...
if exist "build" rmdir /s /q "build"
if exist "dist\7D2D_WebManager" rmdir /s /q "dist\7D2D_WebManager"
if exist "7D2D_WebManager.spec" del /q "7D2D_WebManager.spec"

echo [3/3] Building exe...
pyinstaller --name "7D2D_WebManager" --add-data "web\static;web\static" --hidden-import "uvicorn.logging" --hidden-import "uvicorn.loops.auto" --hidden-import "uvicorn.loops.asyncio" --hidden-import "uvicorn.protocols.http.auto" --hidden-import "uvicorn.protocols.http.h11_impl" --hidden-import "uvicorn.lifespan.on" --hidden-import "uvicorn.lifespan.off" --hidden-import "core.crash_db" --hidden-import "core.snapshot" --hidden-import "web.api.auth" --noconfirm --clean web\app.py

if errorlevel 1 ( echo ERROR: build failed & pause & exit /b 1 )

echo.
echo Build OK: dist\7D2D_WebManager\7D2D_WebManager.exe
pause
