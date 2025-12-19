@echo off
chcp 65001 >nul
echo ========================================
echo 온카판 자동 댓글 매크로 빌드 시작
echo ========================================
echo.

REM Python 경로 확인
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [오류] Python을 찾을 수 없습니다.
    echo Python이 설치되어 있고 PATH에 추가되어 있는지 확인하세요.
    pause
    exit /b 1
)

echo [1/3] 이전 빌드 파일 정리 중...
if exist build rmdir /s /q build
if exist dist\온카판_자동댓글_매크로_v4.exe del /q dist\온카판_자동댓글_매크로_v4.exe
echo 완료
echo.

echo [2/3] PyInstaller로 빌드 중...
python -m PyInstaller --clean --noconfirm 온카판_자동댓글_매크로.spec
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [오류] 빌드 실패
    pause
    exit /b 1
)
echo 완료
echo.

echo [3/3] 빌드 결과 확인 중...
if exist dist\온카판_자동댓글_매크로_v4.exe (
    echo.
    echo ========================================
    echo 빌드 성공!
    echo ========================================
    echo.
    echo 실행 파일 위치: dist\온카판_자동댓글_매크로_v4.exe
    echo.
) else (
    echo.
    echo [오류] 실행 파일을 찾을 수 없습니다.
    pause
    exit /b 1
)

pause




