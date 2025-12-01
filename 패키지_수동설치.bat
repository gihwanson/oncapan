@echo off
chcp 65001 >nul
title 패키지 수동 설치
cd /d "%~dp0"

echo ========================================
echo   패키지 수동 설치
echo ========================================
echo.

REM pip 확인
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo pip가 없습니다. pip를 먼저 설치합니다...
    python -m ensurepip --upgrade
    if errorlevel 1 (
        echo.
        echo [오류] pip 설치 실패
        echo.
        pause
        exit /b 1
    )
)

echo.
echo pip 업그레이드 중...
python -m pip install --upgrade pip

echo.
echo 필수 패키지 설치 중...
echo 이 작업은 몇 분이 걸릴 수 있습니다...
echo.

python -m pip install requests
python -m pip install beautifulsoup4
python -m pip install openai
python -m pip install cryptography
python -m pip install selenium
python -m pip install pyinstaller

echo.
echo ========================================
echo   설치 완료!
echo ========================================
echo.
pause

