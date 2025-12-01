@echo off
chcp 65001 >nul
title Tcl/Tk 확인
cd /d "%~dp0"

echo ========================================
echo   Tcl/Tk 파일 확인
echo ========================================
echo.

set PYTHON_DIR=C:\Python313

echo Python 경로: %PYTHON_DIR%
echo.

set TCL_PATH1=%PYTHON_DIR%\Lib\tcl\tcl8.6
set TCL_PATH2=%PYTHON_DIR%\tcl\tcl8.6
set TK_PATH1=%PYTHON_DIR%\Lib\tk\tk8.6
set TK_PATH2=%PYTHON_DIR%\tcl\tk8.6

echo Tcl 경로 확인:
if exist "%TCL_PATH1%" (
    echo   [✓] %TCL_PATH1%
    if exist "%TCL_PATH1%\init.tcl" (
        echo       init.tcl 파일 발견!
    ) else (
        echo       [경고] init.tcl 파일 없음
    )
) else (
    echo   [✗] %TCL_PATH1% - 없음
)

if exist "%TCL_PATH2%" (
    echo   [✓] %TCL_PATH2%
) else (
    echo   [✗] %TCL_PATH2% - 없음
)

echo.
echo Tk 경로 확인:
if exist "%TK_PATH1%" (
    echo   [✓] %TK_PATH1%
) else (
    echo   [✗] %TK_PATH1% - 없음
)

if exist "%TK_PATH2%" (
    echo   [✓] %TK_PATH2%
) else (
    echo   [✗] %TK_PATH2% - 없음
)

echo.
echo ========================================
if not exist "%TCL_PATH1%" if not exist "%TCL_PATH2%" (
    echo [결론] Tcl/Tk가 설치되지 않았습니다.
    echo.
    echo 해결 방법:
    echo 1. Python을 재설치하세요
    echo 2. 설치 시 "tcl/tk and IDLE" 옵션을 반드시 선택하세요
    echo 3. Python 3.11 또는 3.12 사용 권장
    echo.
) else (
    echo Tcl/Tk 파일이 발견되었습니다.
    echo 환경 변수를 설정하면 작동할 수 있습니다.
    echo.
)

pause

