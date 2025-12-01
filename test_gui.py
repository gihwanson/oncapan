"""GUI 테스트 스크립트"""
import sys
import traceback

print("=" * 50)
print("GUI 테스트 시작")
print("=" * 50)

try:
    print("1. tkinter import 시도...")
    import tkinter as tk
    print("   ✓ tkinter import 성공")
except Exception as e:
    print(f"   ✗ tkinter import 실패: {e}")
    sys.exit(1)

try:
    print("2. 모듈 import 시도...")
    from gui import MacroGUI
    print("   ✓ gui 모듈 import 성공")
except Exception as e:
    print(f"   ✗ gui 모듈 import 실패: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("3. GUI 창 생성 시도...")
    root = tk.Tk()
    print("   ✓ Tk 루트 생성 성공")
    
    print("4. MacroGUI 인스턴스 생성 시도...")
    app = MacroGUI(root)
    print("   ✓ MacroGUI 인스턴스 생성 성공")
    
    print("5. GUI 창 표시...")
    print("   창이 열렸습니다. 창을 닫으면 프로그램이 종료됩니다.")
    root.mainloop()
    print("   ✓ GUI 종료")
    
except Exception as e:
    print(f"   ✗ 오류 발생: {e}")
    traceback.print_exc()
    sys.exit(1)

print("=" * 50)
print("테스트 완료")
print("=" * 50)

