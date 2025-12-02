# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

# config.json 추가
datas = []
if os.path.exists('config.json'):
    datas.append(('config.json', '.'))

binaries = []
hiddenimports = ['tkinter', '_tkinter', 'requests', 'beautifulsoup4', 'openai', 'cryptography', 'selenium', 'webdriver_manager', 'config_manager', 'realtime_learner']

# tkinter 수집 시도
try:
    tmp_ret = collect_all('tkinter')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except Exception as e:
    print(f"tkinter collect_all 실패: {e}")

# tkinter 관련 모듈 명시적으로 추가
tkinter_modules = [
    'tkinter', '_tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.scrolledtext',
    'tkinter.filedialog', 'tkinter.font', 'tkinter.constants', 'tkinter.colorchooser',
    'tkinter.commondialog', 'tkinter.dialog', 'tkinter.dnd', 'tkinter.simpledialog'
]
for mod in tkinter_modules:
    if mod not in hiddenimports:
        hiddenimports.append(mod)

# Python 설치 경로에서 Tcl/Tk 라이브러리 찾기
python_exe = sys.executable
python_dir = os.path.dirname(os.path.abspath(python_exe))
python_base = sys.prefix
python_lib = os.path.join(python_base, 'Lib')

# 실제 Python 설치 경로 (tkinter가 있는 곳)
actual_python_path = r"C:\Users\손기환\AppData\Local\Programs\Python\Python313"

# 가능한 Tcl/Tk 경로들 (여러 경로 시도)
search_paths = [
    actual_python_path,  # 실제 Python 설치 경로
    python_dir,
    python_base,
    python_lib,
    os.path.dirname(python_dir),
    os.path.join(python_dir, 'Lib'),
    os.path.join(python_base, 'lib'),
    os.path.join(actual_python_path, 'Lib'),
]

# Tcl/Tk 경로 찾기
tcl_path = None
tk_path = None

for base in search_paths:
    if not base or not os.path.exists(base):
        continue
    
    # tcl 경로 찾기
    test_tcl = os.path.join(base, 'tcl')
    if os.path.exists(test_tcl) and os.path.isdir(test_tcl):
        tcl_path = test_tcl
        print(f"Tcl 경로 발견: {tcl_path}")
        break
    
    # Lib/tcl 경로 찾기
    test_lib_tcl = os.path.join(base, 'Lib', 'tcl')
    if os.path.exists(test_lib_tcl) and os.path.isdir(test_lib_tcl):
        tcl_path = test_lib_tcl
        print(f"Tcl 경로 발견: {tcl_path}")
        break

for base in search_paths:
    if not base or not os.path.exists(base):
        continue
    
    # tk 경로 찾기
    test_tk = os.path.join(base, 'tk')
    if os.path.exists(test_tk) and os.path.isdir(test_tk):
        tk_path = test_tk
        print(f"Tk 경로 발견: {tk_path}")
        break
    
    # Lib/tk 경로 찾기
    test_lib_tk = os.path.join(base, 'Lib', 'tk')
    if os.path.exists(test_lib_tk) and os.path.isdir(test_lib_tk):
        tk_path = test_lib_tk
        print(f"Tk 경로 발견: {tk_path}")
        break

# Tcl/Tk 경로를 _tcl_data와 _tk_data로 추가 (PyInstaller가 찾는 경로)
if tcl_path:
    datas.append((tcl_path, '_tcl_data'))
    print(f"Tcl 데이터 추가: {tcl_path} -> _tcl_data")
    
    # Python 3.13에서는 Tk가 Tcl 디렉토리 안에 있을 수 있음
    tk_in_tcl = os.path.join(tcl_path, 'tk8.6')
    if os.path.exists(tk_in_tcl):
        datas.append((tk_in_tcl, '_tk_data'))
        print(f"Tk 데이터 추가 (Tcl 내부): {tk_in_tcl} -> _tk_data")
        tk_path = tk_in_tcl
else:
    print("경고: Tcl 경로를 찾을 수 없습니다!")

if tk_path and tk_path not in [d[0] for d in datas if d[1] == '_tk_data']:
    datas.append((tk_path, '_tk_data'))
    print(f"Tk 데이터 추가: {tk_path} -> _tk_data")
elif not tk_path:
    # Tk를 찾지 못한 경우에도 Tcl 내부에서 다시 시도
    actual_python_path = r"C:\Users\손기환\AppData\Local\Programs\Python\Python313"
    tk_in_tcl = os.path.join(actual_python_path, 'tcl', 'tk8.6')
    if os.path.exists(tk_in_tcl):
        datas.append((tk_in_tcl, '_tk_data'))
        print(f"Tk 데이터 추가 (직접 경로): {tk_in_tcl} -> _tk_data")
    else:
        print("경고: Tk 경로를 찾을 수 없습니다!")

# _tkinter.pyd 파일 찾기 (Windows)
try:
    import _tkinter
    tkinter_dll_path = _tkinter.__file__
    if os.path.exists(tkinter_dll_path):
        binaries.append((tkinter_dll_path, '.'))
        print(f"_tkinter DLL 추가: {tkinter_dll_path}")
except Exception as e:
    print(f"_tkinter 찾기 실패: {e}")
    # 수동으로 찾기
    for search_dir in [python_dlls, python_lib, python_base]:
        tkinter_pyd = os.path.join(search_dir, '_tkinter.pyd')
        if os.path.exists(tkinter_pyd):
            binaries.append((tkinter_pyd, '.'))
            print(f"_tkinter DLL 수동 추가: {tkinter_pyd}")
            break


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='온카판_자동댓글_매크로',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
