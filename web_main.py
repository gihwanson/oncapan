"""
웹 기반 GUI 메인 진입점
- tkinter 대신 Flask 웹 서버 사용
"""

from web_gui import run_web_gui
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('macro.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Werkzeug 로그 숨기기
logging.getLogger('werkzeug').setLevel(logging.WARNING)

if __name__ == "__main__":
    try:
        run_web_gui(port=5000)
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다...")
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

