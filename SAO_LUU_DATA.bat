@echo off
chcp 65001 >nul
title Trung Tam Day Them - Sao Luu Data

cd /d "%~dp0"

echo ============================================
echo   SAO LUU DU LIEU TRUNG TAM DAY THEM
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [LOI] Chua tim thay Python!
    pause
    exit /b 1
)

python utils\backup.py manual

echo.
echo Hoan tat! File backup duoc luu trong thu muc: data\backups\
if "%1"=="--nopause" exit /b 0
pause
