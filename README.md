# 온카판 자동 댓글 매크로

온카판 커뮤니티 자유게시판에 자동으로 댓글을 작성하는 매크로 프로그램입니다.

## 주요 기능

- 🤖 **AI 기반 댓글 생성**: OpenAI GPT를 활용한 자연스러운 댓글 생성
- 📚 **실시간 학습**: 실제 댓글을 수집하여 AI가 학습하도록 개선
- 🔒 **보안**: 로그인 정보 및 API 키 암호화 저장
- 🌐 **웹 기반 GUI**: 브라우저에서 편리하게 사용
- ⚙️ **설정 가능**: 댓글 작성 빈도, 대기 시간 등 커스터마이징
- 🧪 **테스트 모드**: 실제 댓글 작성 전 테스트 가능

## 설치 방법

1. Python 3.8 이상 설치
2. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

3. 프로그램 실행:
```bash
python web_main.py
```

또는

```bash
run.bat
```

## 사용 방법

1. 웹 브라우저에서 `http://localhost:5000` 접속
2. 로그인 정보 및 OpenAI API 키 입력
3. 댓글 작성 설정 조정
4. "댓글 수집하기" 버튼으로 학습 데이터 수집 (선택사항)
5. "시작" 버튼으로 매크로 실행

## 주요 파일

- `web_main.py`: 웹 GUI 실행 파일
- `web_gui.py`: Flask 기반 웹 인터페이스
- `web_scraper_selenium.py`: Selenium을 사용한 웹 스크래핑
- `ai_comment_generator.py`: OpenAI GPT를 활용한 댓글 생성
- `realtime_learner.py`: 실시간 댓글 수집 및 학습
- `config_manager.py`: 설정 관리 (암호화)

## 주의사항

- OpenAI API 키가 필요합니다
- Chrome 브라우저와 ChromeDriver가 필요합니다
- 테스트 모드로 먼저 실행해보는 것을 권장합니다

## 라이선스

이 프로젝트는 개인 사용 목적으로 제작되었습니다.
