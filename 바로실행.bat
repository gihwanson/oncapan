@echo off
chcp 65001 >nul
cd /d "%~dp0"
title OncaPan 바로 실행

REM Python 명령어 찾기
set PYTHON_CMD=
python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
    goto :run
)

py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py
    goto :run
)

python3 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python3
    goto :run
)

echo [오류] Python을 찾을 수 없습니다.
echo 설치_및_실행.bat을 먼저 실행하세요.
pause
exit /b 1

:run
echo 프로그램 실행 중...
echo.
%PYTHON_CMD% main.py

if errorlevel 1 (
    echo.
    echo 오류가 발생했습니다.
    echo error.log 파일을 확인하세요.
    echo.
    pause
)


