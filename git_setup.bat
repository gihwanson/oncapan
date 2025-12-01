@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo Git 저장소 초기화 및 GitHub 푸시
echo ========================================
echo.

echo 1. Git 저장소 초기화...
git init
echo.

echo 2. Git 사용자 설정...
git config user.name "gihwanson"
git config user.email "gihwanson@users.noreply.github.com"
echo.

echo 3. 원격 저장소 추가...
git remote remove origin 2>nul
git remote add origin https://github.com/gihwanson/oncapan.git
echo.

echo 4. 모든 파일 추가...
git add -A
echo.

echo 5. 커밋 생성...
git commit -m "Initial commit: 온카판 자동 댓글 매크로"
echo.

echo 6. 브랜치를 main으로 설정...
git branch -M main
echo.

echo 7. GitHub에 푸시 중...
echo (인증이 필요할 수 있습니다)
echo.
git push -u origin main
echo.

echo ========================================
if %ERRORLEVEL% EQU 0 (
    echo 푸시 성공!
) else (
    echo 푸시 실패. 인증이 필요할 수 있습니다.
    echo.
    echo 해결 방법:
    echo 1. GitHub Personal Access Token 생성
    echo 2. 다음 명령어 실행:
    echo    git remote set-url origin https://YOUR_TOKEN@github.com/gihwanson/oncapan.git
    echo    git push -u origin main
)
echo ========================================
pause

