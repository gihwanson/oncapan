@echo off
chcp 65001 >nul
title 온카판 자동 댓글 매크로
cd /d "%~dp0"

echo ========================================
echo   온카판 자동 댓글 매크로
echo ========================================
echo.

REM py launcher 사용 (가장 안정적)
echo Python 실행 중...
py main.py

if errorlevel 1 (
    echo.
    echo 오류가 발생했습니다.
    pause
)

