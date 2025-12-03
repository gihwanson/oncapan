"""
온카판 자동 댓글 매크로 - 메인 진입점
"""

import tkinter as tk
from gui import MacroGUI
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('macro.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def main():
    """메인 함수"""
    import sys
    import os
    
    # 오류 발생 시에도 콘솔에 출력되도록 설정 (exe에서는 None일 수 있음)
    try:
        if sys.stdout is not None:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        pass  # exe에서 콘솔이 없으면 무시
    
    try:
        if sys.stderr is not None:
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        pass  # exe에서 콘솔이 없으면 무시
    
    try:
        
        # Python 버전 확인 (경고만 표시, 실제 작동 여부는 테스트)
        python_version = sys.version_info
        if python_version.major == 3 and python_version.minor >= 13:
            warning_msg = (
                f"Python {python_version.major}.{python_version.minor}을 사용 중입니다.\n"
                "일부 버전에서는 tkinter가 제대로 작동하지 않을 수 있습니다.\n\n"
                "tkinter 테스트를 진행합니다..."
            )
            print(warning_msg)
            # logging은 전역에서 import되었으므로 직접 사용
            import logging as log_module
            try:
                log_module.warning(warning_msg)
            except:
                pass  # logging 오류는 무시
        
        # Tcl/Tk 경로 설정 (한글 경로 문제 해결)
        
        # Python 설치 경로 찾기 (실제 경로)
        python_exe = sys.executable
        python_dir = os.path.dirname(os.path.abspath(python_exe))
        python_lib = os.path.join(python_dir, 'Lib')
        
        # Python 3.13+의 경우 sys.prefix가 잘못된 경로를 반환할 수 있으므로
        # 여러 경로를 시도합니다
        base_paths = [
            python_dir,  # Python 실행 파일이 있는 디렉토리
            python_lib,  # Lib 디렉토리
        ]
        
        # sys.prefix가 유효한 경로인 경우에만 추가
        if sys.prefix and os.path.exists(sys.prefix) and sys.prefix != python_dir:
            base_paths.append(sys.prefix)
            base_paths.append(os.path.join(sys.prefix, 'Lib'))
        
        # Python 디렉토리의 부모도 시도
        if python_dir:
            parent_dir = os.path.dirname(python_dir)
            if parent_dir and os.path.exists(parent_dir):
                base_paths.append(parent_dir)
        
        # Windows에서 일반적인 Python 설치 경로들도 시도
        import platform
        if platform.system() == 'Windows':
            user_home = os.path.expanduser('~')
            common_paths = [
                os.path.join(user_home, 'AppData', 'Local', 'Programs', 'Python', 'Python313'),
                os.path.join(user_home, 'AppData', 'Local', 'Programs', 'Python'),
                r'C:\Python313',
                r'C:\Python\Python313',
                r'C:\Program Files\Python313',
                r'C:\Program Files (x86)\Python313',
            ]
            for common_path in common_paths:
                if os.path.exists(common_path):
                    base_paths.append(common_path)
                    base_paths.append(os.path.join(common_path, 'Lib'))
        
        # None 제거 및 중복 제거
        base_paths = list(dict.fromkeys([p for p in base_paths if p and os.path.exists(p)]))
        
        # 디버그 정보 출력
        debug_info = []
        debug_info.append(f"Python 실행 파일: {python_exe}")
        debug_info.append(f"Python 디렉토리: {python_dir}")
        debug_info.append(f"Python Lib: {python_lib}")
        debug_info.append(f"sys.prefix: {sys.prefix}")
        debug_info.append(f"시도할 base 경로 수: {len(base_paths)}")
        
        # 로깅에 디버그 정보 출력
        try:
            import logging as log_module
            for info in debug_info:
                log_module.debug(info)
        except:
            pass
        
        # Tcl 경로 찾기 및 설정 (여러 버전 시도)
        tcl_found = False
        tcl_versions = ['tcl8.6', 'tcl8.7', 'tcl9.0', 'tcl']  # 여러 버전 시도
        found_tcl_path = None
        
        for tcl_ver in tcl_versions:
            if tcl_found:
                break
            for base_path in base_paths:
                tcl_paths_to_try = [
                    os.path.join(base_path, 'Lib', 'tcl', tcl_ver),
                    os.path.join(base_path, 'tcl', tcl_ver),
                    os.path.join(base_path, 'lib', tcl_ver),
                    os.path.join(base_path, tcl_ver),
                ]
                for tcl_path in tcl_paths_to_try:
                    try:
                        tcl_path = os.path.normpath(tcl_path)
                        if os.path.exists(tcl_path) and os.path.isdir(tcl_path):
                            # init.tcl 파일이 있는지 확인
                            init_tcl = os.path.join(tcl_path, 'init.tcl')
                            if os.path.exists(init_tcl):
                                # 환경 변수 설정 시도
                                try:
                                    os.environ['TCL_LIBRARY'] = tcl_path
                                    found_tcl_path = tcl_path
                                    tcl_found = True
                                    try:
                                        import logging as log_module
                                        log_module.info(f"Tcl 경로 발견: {tcl_path}")
                                    except:
                                        pass
                                    break
                                except Exception as e:
                                    try:
                                        import logging as log_module
                                        log_module.warning(f"Tcl 경로 설정 실패: {e}")
                                    except:
                                        pass
                    except Exception as e:
                        # 경로 접근 오류는 무시하고 계속
                        continue
                if tcl_found:
                    break
        
        # Tk 경로 찾기 및 설정 (여러 버전 시도)
        tk_found = False
        tk_versions = ['tk8.6', 'tk8.7', 'tk9.0', 'tk']  # 여러 버전 시도
        found_tk_path = None
        
        for tk_ver in tk_versions:
            if tk_found:
                break
            for base_path in base_paths:
                tk_paths_to_try = [
                    os.path.join(base_path, 'Lib', 'tk', tk_ver),
                    os.path.join(base_path, 'tk', tk_ver),
                    os.path.join(base_path, 'lib', tk_ver),
                    os.path.join(base_path, tk_ver),
                ]
                for tk_path in tk_paths_to_try:
                    try:
                        tk_path = os.path.normpath(tk_path)
                        if os.path.exists(tk_path) and os.path.isdir(tk_path):
                            # 환경 변수 설정 시도
                            try:
                                os.environ['TK_LIBRARY'] = tk_path
                                found_tk_path = tk_path
                                tk_found = True
                                try:
                                    import logging as log_module
                                    log_module.info(f"Tk 경로 발견: {tk_path}")
                                except:
                                    pass
                                break
                            except Exception as e:
                                try:
                                    import logging as log_module
                                    log_module.warning(f"Tk 경로 설정 실패: {e}")
                                except:
                                    pass
                    except Exception as e:
                        # 경로 접근 오류는 무시하고 계속
                        continue
                if tk_found:
                    break
        
        # 경로를 찾지 못한 경우 경고만 표시하고 계속 진행
        # (tkinter가 작동하는 경우 경로 설정 없이도 작동할 수 있음)
        if not tcl_found or not tk_found:
            import logging
            try:
                import logging as log_module
                log_module.warning(f"Tcl/Tk 경로를 찾을 수 없습니다. Tcl: {tcl_found}, Tk: {tk_found}")
                log_module.warning(f"Python 경로: {python_dir}")
                log_module.warning(f"Python Lib 경로: {python_lib}")
                log_module.warning(f"Python prefix: {sys.prefix}")
                log_module.warning("경고: Tcl/Tk 경로를 찾지 못했지만 tkinter가 작동할 수 있습니다. 계속 진행합니다...")
            except:
                pass  # logging 오류는 무시
            
            # tkinter가 실제로 작동하는지 테스트
            try:
                import tkinter
                test_root = tkinter.Tk()
                test_root.withdraw()
                test_root.destroy()
                try:
                    import logging as log_module
                    log_module.info("tkinter 테스트 성공 - 경로 설정 없이도 작동합니다.")
                except:
                    pass  # logging 오류는 무시
            except Exception as e:
                # tkinter가 작동하지 않는 경우에만 오류 발생
                # 시도한 경로 정보 수집
                tried_paths_info = []
                tried_paths_info.append(f"Python 실행 파일: {python_exe}")
                tried_paths_info.append(f"Python 디렉토리: {python_dir}")
                tried_paths_info.append(f"Python Lib: {python_lib}")
                tried_paths_info.append(f"sys.prefix: {sys.prefix}")
                if found_tcl_path:
                    tried_paths_info.append(f"발견된 Tcl 경로: {found_tcl_path}")
                if found_tk_path:
                    tried_paths_info.append(f"발견된 Tk 경로: {found_tk_path}")
                tried_paths_info.append(f"시도한 base 경로: {len(base_paths)}개")
                
                error_msg = (
                    "Tcl/Tk를 찾을 수 없고 tkinter도 작동하지 않습니다.\n\n"
                    "Python 설치에 tkinter가 포함되지 않았거나 경로를 찾을 수 없습니다.\n\n"
                    "디버그 정보:\n" + "\n".join(f"  - {info}" for info in tried_paths_info) + "\n\n"
                    "해결 방법:\n"
                    "1. Python을 재설치하세요 (Python 3.11 또는 3.12 권장)\n"
                    "   - 다운로드: https://www.python.org/downloads/\n"
                    "   - 설치 시 'tcl/tk and IDLE' 옵션을 반드시 선택하세요\n"
                    "   - 'Add Python to PATH' 옵션도 체크하세요\n"
                    "2. Python 3.13은 tkinter 문제가 있을 수 있으므로 3.11 또는 3.12 사용을 권장합니다\n"
                    "3. Python 설치 경로에 한글이 포함되지 않도록 하세요\n"
                    "   (예: C:\\Python312 같은 영문 경로 사용)\n"
                    "4. 관리자 권한으로 Python을 설치해보세요\n"
                    "5. 기존 Python을 완전히 제거한 후 재설치하세요"
                )
                
                # GUI 오류 메시지 표시 시도
                try:
                    import tkinter.messagebox as msgbox
                    root_err = tk.Tk()
                    root_err.withdraw()
                    msgbox.showerror("Tcl/Tk 오류", error_msg)
                    root_err.destroy()
                except:
                    print(error_msg)
                
                raise RuntimeError(f"tkinter가 작동하지 않습니다: {e}")
        
        # 콘솔 창 숨기기 (GUI만 표시)
        # 배치 파일에서 실행할 때는 콘솔을 유지하여 오류 메시지 확인 가능
        # if sys.platform == 'win32':
        #     try:
        #         import ctypes
        #         # 콘솔 창 숨기기
        #         kernel32 = ctypes.windll.kernel32
        #         user32 = ctypes.windll.user32
        #         hwnd = kernel32.GetConsoleWindow()
        #         if hwnd:
        #             user32.ShowWindow(hwnd, 0)  # 0 = 숨기기, 1 = 보이기
        #     except:
        #         pass
        
        root = tk.Tk()
        
        # 창을 화면 중앙에 배치
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')
        
        # 창을 맨 앞으로 가져오기
        root.lift()
        root.attributes('-topmost', True)
        root.after_idle(root.attributes, '-topmost', False)
        
        # 창 표시
        root.deiconify()
        root.focus_force()
        
        app = MacroGUI(root, force_test_mode=False)
        root.mainloop()
    except Exception as e:
        import traceback
        error_msg = f"프로그램 실행 오류: {e}\n\n{traceback.format_exc()}"
        print(error_msg)
        
        # 로그 파일에 기록
        try:
            with open('error.log', 'w', encoding='utf-8') as f:
                f.write(error_msg)
            print("\n오류 내용이 error.log 파일에 저장되었습니다.")
        except:
            pass
        
        # GUI가 작동한다면 에러 메시지 박스 표시
        try:
            import tkinter.messagebox as msgbox
            root_err = tk.Tk()
            root_err.withdraw()  # 메인 창 숨기기
            msgbox.showerror("오류", f"프로그램 실행 중 오류가 발생했습니다:\n\n{e}\n\n자세한 내용은 error.log 파일을 확인하세요.")
            root_err.destroy()
        except:
            pass
        
        input("\n아무 키나 눌러 종료하세요...")

if __name__ == "__main__":
    main()

