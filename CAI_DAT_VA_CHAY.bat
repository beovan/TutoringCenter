@echo off
chcp 65001 >nul
title Trung Tam Day Them - Cai Dat

echo ============================================
echo   TRUNG TAM DAY THEM - CAI DAT LAN DAU
echo ============================================
echo.

:: Kiểm tra Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [LOI] Chua cai Python!
    echo Tai Python tai: https://www.python.org/downloads/
    echo Nho tick "Add Python to PATH" khi cai!
    pause
    exit /b 1
)

echo [OK] Python da san sang
echo.
echo Dang cai cac thu vien can thiet...
pip install -r requirements.txt --quiet

echo.
echo [OK] Cai dat hoan tat!
echo.
echo Dang khoi dong ung dung...
streamlit run app.py

pause
