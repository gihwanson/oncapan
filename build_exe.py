"""
exe 빌드 스크립트
PyInstaller를 사용하여 실행 파일 생성
"""

import PyInstaller.__main__
import os
import shutil

def build_exe():
    """exe 파일 빌드"""
    print("=" * 60)
    print("온카판 자동 댓글 매크로 빌드 시작")
    print("=" * 60)
    print()
    
    # .spec 파일이 있으면 사용, 없으면 옵션으로 빌드
    spec_file = '온카판_자동댓글_매크로.spec'
    
    if os.path.exists(spec_file):
        print(f"[1/2] {spec_file} 파일을 사용하여 빌드합니다...")
        options = [spec_file, '--clean', '--noconfirm']  # --clean으로 이전 빌드 정리
    else:
        print("spec 파일이 없어 옵션으로 빌드합니다...")
        # PyInstaller 옵션
        options = [
            'main.py',
            '--name=온카판_자동댓글_매크로',
            '--onefile',  # 단일 실행 파일
            '--windowed',  # 콘솔 창 숨기기
            '--icon=NONE',  # 아이콘은 나중에 추가 가능
            '--add-data=config.json;.' if os.path.exists('config.json') else '',
            '--hidden-import=tkinter',
            '--hidden-import=_tkinter',
            '--hidden-import=requests',
            '--hidden-import=beautifulsoup4',
            '--hidden-import=openai',
            '--hidden-import=cryptography',
            '--hidden-import=selenium',
            '--hidden-import=webdriver_manager',
            '--hidden-import=config_manager',
            '--hidden-import=realtime_learner',
            '--collect-all=tkinter',
            '--noconsole',  # 콘솔 창 없이 실행
        ]
        
        # 빈 문자열 제거
        options = [opt for opt in options if opt]
    
    try:
        print("[2/2] PyInstaller 실행 중...")
        print()
        PyInstaller.__main__.run(options)
        print()
        print("=" * 60)
        print("빌드 완료!")
        print("=" * 60)
        print()
        exe_path = os.path.join('dist', '온카판_자동댓글_매크로_v4.exe')
        if os.path.exists(exe_path):
            file_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
            print(f"실행 파일: {exe_path}")
            print(f"파일 크기: {file_size:.2f} MB")
        else:
            print("경고: 실행 파일을 찾을 수 없습니다.")
        print()
    except Exception as e:
        print()
        print("=" * 60)
        print("빌드 오류 발생!")
        print("=" * 60)
        print(f"오류 내용: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    build_exe()

