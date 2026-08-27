@echo off
echo ========================================
echo   Silent PC Optimizer - Build Script
echo ========================================
echo.

python -m PyInstaller --onefile --windowed --name "Silent PC Optimizer" ^
    --add-data "settings.json;." ^
    --hidden-import pystray._win32 ^
    --hidden-import PIL ^
    --hidden-import psutil ^
    --hidden-import pygetwindow ^
    --hidden-import keyboard ^
    --hidden-import ctypes ^
    --hidden-import wmi ^
    --hidden-import cryptography.hazmat.primitives ^
    --hidden-import core.updater ^
    --hidden-import core.restore_point ^
    main.pyw

echo.
echo Build complete! Check dist\ folder.
pause
