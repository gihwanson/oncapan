"""패키지 설치 확인 스크립트"""
import sys

required_packages = {
    'requests': 'requests',
    'beautifulsoup4': 'bs4',
    'openai': 'openai',
    'cryptography': 'cryptography',
    'selenium': 'selenium',
    'pyinstaller': 'PyInstaller',
}

print("=" * 50)
print("필수 패키지 설치 확인")
print("=" * 50)

missing_packages = []
installed_packages = []

for package_name, import_name in required_packages.items():
    try:
        __import__(import_name)
        installed_packages.append(package_name)
        print(f"✓ {package_name} - 설치됨")
    except ImportError:
        missing_packages.append(package_name)
        print(f"✗ {package_name} - 설치 필요")

print("\n" + "=" * 50)
if missing_packages:
    print(f"\n설치 필요한 패키지: {', '.join(missing_packages)}")
    print("\n설치 명령어:")
    print(f"python -m pip install {' '.join(missing_packages)}")
else:
    print("\n모든 필수 패키지가 설치되어 있습니다!")
    print("프로그램을 실행할 수 있습니다: python main.py")

