@echo off
chcp 65001 >nul
title 온카판 자동 댓글 매크로
cd /d "%~dp0"

echo ========================================
echo   온카판 자동 댓글 매크로
echo ========================================
echo.

REM Python 버전 확인
echo Python 버전 확인 중...
py --version >nul 2>&1
if errorlevel 1 (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [오류] Python을 찾을 수 없습니다.
        pause
        exit /b 1
    )
    set PYTHON_CMD=python
) else (
    set PYTHON_CMD=py
)

REM 필수 패키지 확인 및 설치
echo 필수 패키지 확인 중...
%PYTHON_CMD% -c "import requests, bs4, openai, cryptography, flask, selenium, webdriver_manager" >nul 2>&1
if errorlevel 1 (
    echo 필수 패키지가 없습니다. 설치를 시작합니다...
    echo 이 작업은 몇 분이 걸릴 수 있습니다...
    echo.
    %PYTHON_CMD% -m pip install --upgrade pip
    %PYTHON_CMD% -m pip install requests beautifulsoup4 openai cryptography selenium webdriver-manager pyinstaller flask
    if errorlevel 1 (
        echo.
        echo [오류] 패키지 설치 실패
        pause
        exit /b 1
    )
    echo 패키지 설치 완료!
    echo.
)

REM 프로그램 실행 (웹 GUI 사용)
echo 프로그램 실행 중...
echo.
echo ========================================
echo   웹 기반 GUI를 사용합니다
echo ========================================
echo.
echo 브라우저가 자동으로 열립니다.
echo 브라우저에서 프로그램을 사용하세요.
echo.
echo 종료하려면 이 창을 닫으세요.
echo.
%PYTHON_CMD% web_main.py

if errorlevel 1 (
    echo.
    echo 프로그램이 오류와 함께 종료되었습니다.
    echo error.log 파일을 확인하세요.
    echo.
    pause
)
