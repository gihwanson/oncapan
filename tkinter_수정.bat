@echo off
chcp 65001 >nul
title Tkinter 경로 수정
cd /d "%~dp0"

echo ========================================
echo   Tkinter 경로 수정 도구
echo ========================================
echo.

REM Python 경로 찾기
for %%i in (python.exe) do set PYTHON_DIR=%%~dp$PATH:i

if not defined PYTHON_DIR (
    echo Python을 찾을 수 없습니다.
    pause
    exit /b 1
)

echo Python 경로: %PYTHON_DIR%
echo.

REM Tcl/Tk 경로 확인
set "TCL_PATH1=%PYTHON_DIR%tcl\tcl8.6"
set "TCL_PATH2=%PYTHON_DIR%Lib\tcl\tcl8.6"
set "TK_PATH1=%PYTHON_DIR%tcl\tk8.6"
set "TK_PATH2=%PYTHON_DIR%Lib\tk\tk8.6"

echo Tcl/Tk 경로 확인 중...
if exist "%TCL_PATH1%" (
    echo Tcl 경로 발견: %TCL_PATH1%
    set "TCL_LIBRARY=%TCL_PATH1%"
) else if exist "%TCL_PATH2%" (
    echo Tcl 경로 발견: %TCL_PATH2%
    set "TCL_LIBRARY=%TCL_PATH2%"
) else (
    echo [경고] Tcl 경로를 찾을 수 없습니다.
)

if exist "%TK_PATH1%" (
    echo Tk 경로 발견: %TK_PATH1%
    set "TK_LIBRARY=%TK_PATH1%"
) else if exist "%TK_PATH2%" (
    echo Tk 경로 발견: %TK_PATH2%
    set "TK_LIBRARY=%TK_PATH2%"
) else (
    echo [경고] Tk 경로를 찾을 수 없습니다.
)

echo.
echo 환경 변수 설정 후 프로그램 실행...
echo.

python main.py

pause

