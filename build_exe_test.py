"""
테스트 모드 전용 exe 빌드 스크립트
PyInstaller를 사용하여 테스트 모드 전용 실행 파일 생성
"""

import PyInstaller.__main__
import os
import shutil

def build_exe():
    """테스트 모드 전용 exe 파일 빌드"""
    print("테스트 모드 전용 exe 파일 빌드를 시작합니다...")
    
    # 테스트 모드 전용 .spec 파일 사용
    spec_file = '온카판_자동댓글_매크로_테스트모드.spec'
    
    if os.path.exists(spec_file):
        print(f"{spec_file} 파일을 사용하여 빌드합니다...")
        options = [spec_file, '--clean']  # --clean으로 이전 빌드 정리
    else:
        print("테스트 모드 spec 파일이 없어 옵션으로 빌드합니다...")
        # PyInstaller 옵션
        options = [
            'main_test.py',  # 테스트 모드 전용 main 파일
            '--name=온카판_자동댓글_매크로_v4_테스트모드',
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
        PyInstaller.__main__.run(options)
        print("\n테스트 모드 전용 빌드 완료!")
        print("dist 폴더에 테스트 모드 전용 exe 파일이 생성되었습니다.")
        print("⚠️ 이 exe는 테스트 모드로만 실행됩니다. 실제 댓글은 작성되지 않습니다.")
    except Exception as e:
        print(f"빌드 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    build_exe()


