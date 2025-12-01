@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo GitHub에 푸시 중...
echo ========================================
echo.

echo Git 상태 확인...
git status
echo.

echo 원격 저장소 확인...
git remote -v
echo.

echo 파일 추가 중...
git add -A
echo.

echo 커밋 중...
git commit -m "Update: 온카판 자동 댓글 매크로" 2>&1
echo.

echo GitHub에 푸시 중...
echo (인증이 필요할 수 있습니다)
git push -u origin main 2>&1
echo.

echo ========================================
echo 완료!
echo ========================================
pause

