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
py --version
if errorlevel 1 (
    echo [오류] Python을 찾을 수 없습니다.
    pause
    exit /b 1
)

echo.
echo 필수 패키지 확인 중...
py -c "import requests, bs4, openai, cryptography" >nul 2>&1
if errorlevel 1 (
    echo 필수 패키지가 없습니다. 설치를 시작합니다...
    echo.
    py -m pip install --upgrade pip
    py -m pip install requests beautifulsoup4 openai cryptography selenium pyinstaller
    if errorlevel 1 (
        echo.
        echo [오류] 패키지 설치 실패
        pause
        exit /b 1
    )
    echo 패키지 설치 완료!
    echo.
)

echo 프로그램 실행 중...
echo.
py main.py

if errorlevel 1 (
    echo.
    echo 프로그램이 오류와 함께 종료되었습니다.
    echo error.log 파일을 확인하세요.
    echo.
    pause
)

