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
    
    # 오류 발생 시에도 콘솔에 출력되도록 설정
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    
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
        
        # 가능한 Tcl/Tk 경로들
        possible_tcl_paths = [
            os.path.join(python_lib, 'tcl', 'tcl8.6'),
            os.path.join(python_dir, 'tcl', 'tcl8.6'),
            os.path.join(sys.prefix, 'Lib', 'tcl', 'tcl8.6'),
            os.path.join(sys.prefix, 'tcl', 'tcl8.6'),
        ]
        
        possible_tk_paths = [
            os.path.join(python_lib, 'tk', 'tk8.6'),
            os.path.join(python_dir, 'tcl', 'tk8.6'),
            os.path.join(sys.prefix, 'Lib', 'tk', 'tk8.6'),
            os.path.join(sys.prefix, 'tcl', 'tk8.6'),
        ]
        
        # Tcl 경로 찾기 및 설정
        tcl_found = False
        for tcl_path in possible_tcl_paths:
            tcl_path = os.path.normpath(tcl_path)  # 경로 정규화
            if os.path.exists(tcl_path) and os.path.isdir(tcl_path):
                # init.tcl 파일이 있는지 확인
                init_tcl = os.path.join(tcl_path, 'init.tcl')
                if os.path.exists(init_tcl):
                    os.environ['TCL_LIBRARY'] = tcl_path
                    tcl_found = True
                    break
        
        # Tk 경로 찾기 및 설정
        tk_found = False
        for tk_path in possible_tk_paths:
            tk_path = os.path.normpath(tk_path)  # 경로 정규화
            if os.path.exists(tk_path) and os.path.isdir(tk_path):
                os.environ['TK_LIBRARY'] = tk_path
                tk_found = True
                break
        
        # 경로를 찾지 못한 경우 - 추가 시도
        if not tcl_found or not tk_found:
            # sys.prefix 직접 사용
            prefix_tcl = os.path.normpath(os.path.join(sys.prefix, 'Lib', 'tcl', 'tcl8.6'))
            prefix_tk = os.path.normpath(os.path.join(sys.prefix, 'Lib', 'tk', 'tk8.6'))
            
            if not tcl_found and os.path.exists(prefix_tcl):
                init_tcl = os.path.join(prefix_tcl, 'init.tcl')
                if os.path.exists(init_tcl):
                    os.environ['TCL_LIBRARY'] = prefix_tcl
                    tcl_found = True
            
            if not tk_found and os.path.exists(prefix_tk):
                os.environ['TK_LIBRARY'] = prefix_tk
                tk_found = True
        
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
                error_msg = (
                    "Tcl/Tk를 찾을 수 없고 tkinter도 작동하지 않습니다.\n\n"
                    "Python 설치에 tkinter가 포함되지 않았습니다.\n\n"
                    "해결 방법:\n"
                    "1. Python을 재설치하세요\n"
                    "2. 설치 시 'tcl/tk and IDLE' 옵션을 반드시 선택하세요\n"
                    "3. Python 3.11 또는 3.12 사용을 권장합니다"
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
        
        app = MacroGUI(root)
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

