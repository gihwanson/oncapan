# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

# config.json 추가
datas = []
if os.path.exists('config.json'):
    datas.append(('config.json', '.'))

# 초기 학습 데이터 추가 (있으면)
if os.path.exists('initial_learning_data.json'):
    datas.append(('initial_learning_data.json', '.'))
    print("초기 학습 데이터 포함: initial_learning_data.json")

binaries = []
hiddenimports = ['tkinter', '_tkinter', 'requests', 'bs4', 'openai', 'cryptography', 'selenium', 'webdriver_manager', 'config_manager', 'realtime_learner']

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

# Python 설치 경로에서 Tcl/Tk 라이브러리 찾기 (동적 경로 찾기)
python_exe = sys.executable
python_dir = os.path.dirname(os.path.abspath(python_exe))
python_base = sys.prefix

# 가능한 Tcl/Tk 경로들 (여러 경로 시도)
search_paths = [
    python_dir,  # Python 실행 파일이 있는 디렉토리
    python_base,  # Python 설치 기본 경로
    os.path.join(python_base, 'Lib'),
    os.path.join(python_dir, 'Lib'),
    os.path.dirname(python_dir),
]

# Windows에서 일반적인 Python 설치 경로들도 시도
if sys.platform == 'win32':
    user_home = os.path.expanduser('~')
    # 실제 존재하는 경로만 추가
    pattern_base = os.path.join(user_home, 'AppData', 'Local', 'Programs', 'Python')
    if os.path.exists(pattern_base):
        for item in os.listdir(pattern_base):
            full_path = os.path.join(pattern_base, item)
            if os.path.isdir(full_path):
                search_paths.append(full_path)
                search_paths.append(os.path.join(full_path, 'Lib'))

# 중복 제거 및 존재하는 경로만 유지
search_paths = list(dict.fromkeys([p for p in search_paths if p and os.path.exists(p)]))

# Tcl/Tk 경로 찾기
tcl_path = None
tk_path = None

# Tcl 경로 찾기 (여러 버전 시도)
tcl_versions = ['tcl8.6', 'tcl8.7', 'tcl9.0', 'tcl']
for tcl_ver in tcl_versions:
    if tcl_path:
        break
    for base in search_paths:
        test_paths = [
            os.path.join(base, 'tcl', tcl_ver),
            os.path.join(base, 'Lib', 'tcl', tcl_ver),
            os.path.join(base, tcl_ver),
        ]
        for test_path in test_paths:
            if os.path.exists(test_path) and os.path.isdir(test_path):
                # init.tcl 파일이 있는지 확인
                init_tcl = os.path.join(test_path, 'init.tcl')
                if os.path.exists(init_tcl):
                    tcl_path = test_path
                    print(f"Tcl 경로 발견: {tcl_path}")
                    break
        if tcl_path:
            break

# Tcl 디렉토리 자체를 찾기 (버전별 하위 디렉토리가 있는 경우)
if not tcl_path:
    for base in search_paths:
        test_tcl = os.path.join(base, 'tcl')
        if os.path.exists(test_tcl) and os.path.isdir(test_tcl):
            # 하위에 버전 디렉토리가 있는지 확인
            for item in os.listdir(test_tcl):
                version_path = os.path.join(test_tcl, item)
                if os.path.isdir(version_path):
                    init_tcl = os.path.join(version_path, 'init.tcl')
                    if os.path.exists(init_tcl):
                        tcl_path = test_tcl  # 상위 디렉토리 전체 포함
                        print(f"Tcl 경로 발견 (상위): {tcl_path}")
                        break
            if tcl_path:
                break

# Tk 경로 찾기 (여러 버전 시도)
# 먼저 Tcl 경로의 부모 디렉토리에서 찾기 (같은 위치에 tk가 있을 가능성)
if tcl_path:
    # Tcl 경로가 tcl8.6 같은 버전 디렉토리인 경우, 부모 디렉토리에서 tk 찾기
    tcl_parent = os.path.dirname(tcl_path)
    tk_versions = ['tk8.6', 'tk8.7', 'tk9.0', 'tk']
    for tk_ver in tk_versions:
        # tcl 디렉토리와 같은 레벨에 tk8.6이 있는 경우 (Python 3.14 구조)
        test_tk = os.path.join(tcl_parent, tk_ver)
        if os.path.exists(test_tk) and os.path.isdir(test_tk):
            tk_path = test_tk
            print(f"Tk 경로 발견 (Tcl 부모 디렉토리): {tk_path}")
            break
        # tk 디렉토리 내부의 버전 디렉토리
        test_tk_dir = os.path.join(tcl_parent, 'tk')
        if os.path.exists(test_tk_dir):
            test_tk_ver = os.path.join(test_tk_dir, tk_ver)
            if os.path.exists(test_tk_ver) and os.path.isdir(test_tk_ver):
                tk_path = test_tk_ver
                print(f"Tk 경로 발견 (tk 디렉토리 내부): {tk_path}")
                break

# 위에서 찾지 못한 경우 일반적인 경로에서 찾기
if not tk_path:
    tk_versions = ['tk8.6', 'tk8.7', 'tk9.0', 'tk']
    for tk_ver in tk_versions:
        if tk_path:
            break
        for base in search_paths:
            test_paths = [
                os.path.join(base, 'tk', tk_ver),
                os.path.join(base, 'Lib', 'tk', tk_ver),
                os.path.join(base, tk_ver),
            ]
            for test_path in test_paths:
                if test_path and os.path.exists(test_path) and os.path.isdir(test_path):
                    tk_path = test_path
                    print(f"Tk 경로 발견: {tk_path}")
                    break
            if tk_path:
                break

# Tk 디렉토리 자체를 찾기
if not tk_path:
    for base in search_paths:
        test_tk = os.path.join(base, 'tk')
        if os.path.exists(test_tk) and os.path.isdir(test_tk):
            tk_path = test_tk
            print(f"Tk 경로 발견 (상위): {tk_path}")
            break

# Tcl/Tk 경로를 _tcl_data와 _tk_data로 추가 (PyInstaller가 찾는 경로)
if tcl_path:
    datas.append((tcl_path, '_tcl_data'))
    print(f"Tcl 데이터 추가: {tcl_path} -> _tcl_data")
else:
    print("경고: Tcl 경로를 찾을 수 없습니다!")

if tk_path:
    # 이미 추가되지 않았는지 확인
    if not any(d[1] == '_tk_data' for d in datas):
        datas.append((tk_path, '_tk_data'))
        print(f"Tk 데이터 추가: {tk_path} -> _tk_data")
else:
    # Tk를 찾지 못한 경우 Tcl 내부에서 다시 시도
    if tcl_path:
        for tk_ver in ['tk8.6', 'tk8.7', 'tk9.0']:
            tk_in_tcl = os.path.join(tcl_path, tk_ver)
            if os.path.exists(tk_in_tcl):
                datas.append((tk_in_tcl, '_tk_data'))
                print(f"Tk 데이터 추가 (Tcl 내부): {tk_in_tcl} -> _tk_data")
                break
    if not any(d[1] == '_tk_data' for d in datas):
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
    python_dlls = os.path.join(python_base, 'DLLs')
    for search_dir in [python_dlls, python_base]:
        if search_dir and os.path.exists(search_dir):
            tkinter_pyd = os.path.join(search_dir, '_tkinter.pyd')
            if os.path.exists(tkinter_pyd):
                binaries.append((tkinter_pyd, '.'))
                print(f"_tkinter DLL 수동 추가: {tkinter_pyd}")
                break


a = Analysis(
    ['main_test.py'],  # 테스트 모드 전용 main 파일 사용
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
    a.zipfiles,  # PyInstaller 기본 템플릿에 맞춰 수정
    a.datas,
    [],
    name='온카판_자동댓글_매크로_v4_테스트모드',  # 테스트 모드 전용 이름
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


