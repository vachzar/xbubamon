@echo off
echo ========================================
echo   BT Battery Monitor - Build Script
echo   Copyright (C) 2026 by JARxAI
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

REM Install dependencies
echo [1/3] Installing dependencies...
pip install pystray pillow --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies!
    pause
    exit /b 1
)
echo       Done!

REM Build EXE
echo [2/3] Building EXE...
for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString(\"yyyyMMddHHmm\")"') do set "BUILD_TS=%%i"
set "APP_NAME=XBubamon-%BUILD_TS%"
pyinstaller --onefile --windowed --icon=icon.ico --add-data "icon.ico;." --add-data "icon.png;." --add-data "logo.png;." --name "%APP_NAME%" bluetooth_battery_monitor.py
if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)
echo       Done!

REM Show result
echo [3/3] Build complete!
echo.
echo ========================================
echo   EXE location: dist\%APP_NAME%.exe
echo ========================================
echo.
pause
