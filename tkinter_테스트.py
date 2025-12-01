"""tkinter 작동 테스트"""
import sys
import os

print("=" * 60)
print("tkinter 작동 테스트")
print("=" * 60)

print(f"\nPython 버전: {sys.version}")
print(f"Python 경로: {sys.executable}")
print(f"Python prefix: {sys.prefix}")

print("\n" + "=" * 60)
print("tkinter import 시도...")
print("=" * 60)

try:
    import tkinter as tk
    print("✓ tkinter import 성공!")
    
    print("\nTkinter 창 생성 시도...")
    root = tk.Tk()
    root.withdraw()  # 창 숨기기
    print("✓ Tkinter 창 생성 성공!")
    
    root.destroy()
    print("✓ tkinter 정상 작동!")
    
    print("\n" + "=" * 60)
    print("결론: tkinter가 정상적으로 작동합니다!")
    print("=" * 60)
    
except ImportError as e:
    print(f"✗ tkinter import 실패: {e}")
    print("\nTcl/Tk가 설치되지 않았습니다.")
    print("Python을 재설치하거나 Tcl/Tk를 수동으로 설치하세요.")
    
except Exception as e:
    print(f"✗ 오류 발생: {e}")
    import traceback
    traceback.print_exc()

input("\n아무 키나 눌러 종료...")

