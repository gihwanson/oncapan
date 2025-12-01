"""Tkinter 설치 확인 및 경로 찾기 스크립트"""
import sys
import os

print("=" * 60)
print("Tkinter 설치 확인")
print("=" * 60)

# Python 경로
python_exe = sys.executable
python_dir = os.path.dirname(os.path.abspath(python_exe))
python_lib = os.path.join(python_dir, 'Lib')

print(f"\nPython 실행 파일: {python_exe}")
print(f"Python 디렉토리: {python_dir}")
print(f"Python Lib 디렉토리: {python_lib}")
print(f"Python prefix: {sys.prefix}")

# Tcl/Tk 경로 확인
print("\n" + "=" * 60)
print("Tcl/Tk 경로 확인")
print("=" * 60)

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

print("\nTcl 경로 확인:")
tcl_found = False
for i, tcl_path in enumerate(possible_tcl_paths, 1):
    exists = os.path.exists(tcl_path)
    is_dir = os.path.isdir(tcl_path) if exists else False
    init_tcl = os.path.join(tcl_path, 'init.tcl') if exists else None
    has_init = os.path.exists(init_tcl) if init_tcl else False
    
    status = "✓ 발견" if (exists and is_dir and has_init) else ("경로 존재" if exists else "없음")
    print(f"  {i}. {tcl_path}")
    print(f"     상태: {status}")
    if has_init:
        print(f"     init.tcl: {init_tcl}")
        tcl_found = True

print("\nTk 경로 확인:")
tk_found = False
for i, tk_path in enumerate(possible_tk_paths, 1):
    exists = os.path.exists(tk_path)
    is_dir = os.path.isdir(tk_path) if exists else False
    status = "✓ 발견" if (exists and is_dir) else ("경로 존재" if exists else "없음")
    print(f"  {i}. {tk_path}")
    print(f"     상태: {status}")
    if exists and is_dir:
        tk_found = True

print("\n" + "=" * 60)
if tcl_found and tk_found:
    print("✓ Tcl/Tk가 정상적으로 설치되어 있습니다!")
else:
    print("✗ Tcl/Tk를 찾을 수 없습니다.")
    print("\n해결 방법:")
    print("1. Python을 재설치하세요 (tkinter 포함 옵션 선택)")
    print("2. 또는 Python 3.11 이하 버전을 사용하세요")
    print("3. 또는 다른 Python 설치를 사용하세요")
print("=" * 60)

input("\n아무 키나 눌러 종료...")

