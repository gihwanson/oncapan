@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 프로그램 실행 중...
python main.py
if errorlevel 1 (
    echo.
    echo 오류가 발생했습니다. error.log 파일을 확인하세요.
    pause
)

