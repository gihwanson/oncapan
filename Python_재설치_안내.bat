@echo off
chcp 65001 >nul
title Python 재설치 안내
cd /d "%~dp0"

echo ========================================
echo   Python 재설치 안내
echo ========================================
echo.
echo 현재 Python 버전에서 tkinter가 작동하지 않습니다.
echo.
echo 해결 방법:
echo.
echo 1. Python 3.11 또는 3.12 다운로드
echo    https://www.python.org/downloads/
echo.
echo 2. 설치 시 반드시 체크:
echo    [x] tcl/tk and IDLE
echo    [x] Add Python to PATH
echo.
echo 3. 설치 완료 후 이 프로그램을 다시 실행하세요.
echo.
echo ========================================
echo.
echo Python 다운로드 페이지를 여시겠습니까? (Y/N)
choice /C YN /N /M "선택: "
if errorlevel 2 goto :end
if errorlevel 1 start https://www.python.org/downloads/

:end
pause

