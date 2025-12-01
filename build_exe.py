"""
exe 빌드 스크립트
PyInstaller를 사용하여 실행 파일 생성
"""

import PyInstaller.__main__
import os
import shutil

def build_exe():
    """exe 파일 빌드"""
    print("exe 파일 빌드를 시작합니다...")
    
    # PyInstaller 옵션
    options = [
        'main.py',
        '--name=온카판_자동댓글_매크로',
        '--onefile',  # 단일 실행 파일
        '--windowed',  # 콘솔 창 숨기기
        '--icon=NONE',  # 아이콘은 나중에 추가 가능
        '--add-data=config.json;.' if os.path.exists('config.json') else '',
        '--hidden-import=tkinter',
        '--hidden-import=requests',
        '--hidden-import=beautifulsoup4',
        '--hidden-import=openai',
        '--hidden-import=cryptography',
        '--collect-all=tkinter',
        '--noconsole',  # 콘솔 창 없이 실행
    ]
    
    # 빈 문자열 제거
    options = [opt for opt in options if opt]
    
    try:
        PyInstaller.__main__.run(options)
        print("\n빌드 완료!")
        print("dist 폴더에 exe 파일이 생성되었습니다.")
    except Exception as e:
        print(f"빌드 오류: {e}")

if __name__ == "__main__":
    build_exe()

