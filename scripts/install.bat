@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo        LOCAL AI WORKBENCH - INSTALLATION SCRIPT
echo ========================================================
echo.

:: 1. Verify Python
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not found in PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)
python --version

:: 2. Verify Node.js
echo.
echo [2/4] Checking Node.js and npm...
node --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js is not installed or not found in PATH.
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)
node --version
npm --version

:: 3. Install Backend Dependencies
echo.
echo [3/4] Installing backend dependencies...
cd /d "%~dp0\..\backend"
python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install backend Python dependencies.
    pause
    exit /b 1
)

:: 4. Install Frontend Dependencies and Build
echo.
echo [4/4] Installing frontend packages and building production assets...
cd /d "%~dp0\..\frontend"
call npm.cmd install --no-audit --no-fund
call npm.cmd run build
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Frontend build failed.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo   INSTALLATION COMPLETED SUCCESSFULLY!
echo   Launch the application using scripts\start.bat
echo ========================================================
echo.
pause
