@echo off
chcp 65001 >nul
title 로그인 디버그 모드
cd /d "%~dp0"

echo ========================================
echo   로그인 디버그 모드
echo ========================================
echo.
echo 로그인 폼 구조를 확인합니다...
echo.

py login_test.py

pause

