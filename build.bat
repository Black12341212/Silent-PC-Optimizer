@echo off
echo ========================================
echo   Silent PC Optimizer - Build Script
echo ========================================
echo.

where pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
)

echo Building...
pyinstaller --onefile --windowed --name "Silent PC Optimizer" ^
    --add-data "settings.json;." ^
    --hidden-import pystray._win32 ^
    --hidden-import PIL ^
    --hidden-import psutil ^
    --hidden-import pygetwindow ^
    --hidden-import keyboard ^
    --hidden-import ctypes ^
    --hidden-import wmi ^
    main.pyw

echo.
echo Build complete! Check dist\ folder.
pause
