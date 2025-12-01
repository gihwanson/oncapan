import os

# 현재 스크립트의 절대 경로
current_file = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file)

print("=" * 50)
print("프로젝트 위치 확인")
print("=" * 50)
print(f"현재 작업 디렉토리: {os.getcwd()}")
print(f"프로젝트 폴더 경로: {current_dir}")
print(f"\n프로젝트 폴더 내 파일 목록:")
print("-" * 50)

files = os.listdir(current_dir)
for file in sorted(files):
    file_path = os.path.join(current_dir, file)
    if os.path.isfile(file_path):
        size = os.path.getsize(file_path)
        print(f"  📄 {file} ({size:,} bytes)")
    elif os.path.isdir(file_path):
        print(f"  📁 {file}/")

print("\n" + "=" * 50)

