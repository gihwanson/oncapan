@echo off
chcp 65001 >nul
title 댓글 수집 도구
cd /d "%~dp0"

echo ========================================
echo   온카판 댓글 수집 도구
echo ========================================
echo.
echo 실제 댓글을 수집하여 AI 학습에 활용합니다.
echo.

py 댓글_수집.py

pause

