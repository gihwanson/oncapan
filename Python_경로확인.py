"""Python 실제 경로 확인"""
import sys
import os

print("=" * 60)
print("Python 경로 확인")
print("=" * 60)

print(f"\n실행 파일: {sys.executable}")
print(f"실제 경로 (prefix): {sys.prefix}")
print(f"실행 파일 디렉토리: {os.path.dirname(sys.executable)}")

# Windows Store 앱인지 확인
if "WindowsApps" in sys.executable:
    print("\n⚠️ Windows Store Python 앱이 감지되었습니다!")
    print("실제 Python 설치 경로를 사용해야 합니다.")
    print(f"실제 경로: {sys.prefix}")

# Lib 경로 확인
lib_path = os.path.join(sys.prefix, 'Lib')
print(f"\nLib 경로: {lib_path}")
print(f"Lib 존재: {os.path.exists(lib_path)}")

# Tcl/Tk 경로 확인
tcl_path = os.path.join(lib_path, 'tcl', 'tcl8.6')
tk_path = os.path.join(lib_path, 'tk', 'tk8.6')

print(f"\nTcl8.6 경로: {tcl_path}")
print(f"Tcl8.6 존재: {os.path.exists(tcl_path)}")
if os.path.exists(tcl_path):
    init_tcl = os.path.join(tcl_path, 'init.tcl')
    print(f"init.tcl 존재: {os.path.exists(init_tcl)}")

print(f"\nTk8.6 경로: {tk_path}")
print(f"Tk8.6 존재: {os.path.exists(tk_path)}")

print("\n" + "=" * 60)
print("환경 변수 설정 권장 값:")
print("=" * 60)
if os.path.exists(tcl_path):
    print(f"set TCL_LIBRARY={tcl_path}")
if os.path.exists(tk_path):
    print(f"set TK_LIBRARY={tk_path}")
print("=" * 60)

input("\n아무 키나 눌러 종료...")

