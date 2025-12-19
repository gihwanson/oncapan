"""
GUI 인터페이스 모듈
- tkinter 기반 사용자 인터페이스
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
from functools import partial
from config_manager import ConfigManager
import time
import random
import logging
import json
import os
import sys
from datetime import datetime, timedelta

# 파일 락 지원 (플랫폼별)
try:
    if os.name == 'nt':  # Windows
        import msvcrt
    else:  # Unix/Linux
        import fcntl
except ImportError:
    pass  # 파일 락 미지원 환경에서는 계속 진행

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cloudflare 우회를 위해 Selenium 사용
try:
    from web_scraper_selenium import OncaPanScraperSelenium as OncaPanScraper
    USE_SELENIUM = True
    logger.info("Selenium 모드로 실행됩니다 (Cloudflare 우회)")
except ImportError as e:
    logger.warning(f"Selenium을 사용할 수 없습니다: {e}")
    logger.warning("requests 모드로 전환합니다 (Cloudflare 차단 가능)")
    from web_scraper import OncaPanScraper
    USE_SELENIUM = False

from ai_comment_generator import AICommentGenerator

class MacroGUI:
    def __init__(self, root, force_test_mode=False):
        self.root = root
        if force_test_mode:
            self.root.title("온카판 자동 댓글 매크로 (테스트 모드)")
        else:
            self.root.title("온카판 자동 댓글 매크로")
        self.root.geometry("600x750")
        self.root.resizable(False, False)
        
        self.force_test_mode = force_test_mode
        self.config_manager = ConfigManager()
        self.scraper = None
        self.ai_generator = None
        self.learner = None  # RealtimeLearner 인스턴스
        self.is_running = False
        self.worker_thread = None
        
        self.setup_ui()
        self.load_saved_config()
    
    def setup_ui(self):
        """UI 구성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 로그인 정보 섹션
        login_frame = ttk.LabelFrame(main_frame, text="로그인 정보", padding="10")
        login_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(login_frame, text="아이디:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.username_entry = ttk.Entry(login_frame, width=30)
        self.username_entry.grid(row=0, column=1, pady=2, padx=5)
        
        ttk.Label(login_frame, text="비밀번호:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.password_entry = ttk.Entry(login_frame, width=30, show="*")
        self.password_entry.grid(row=1, column=1, pady=2, padx=5)
        
        # API 설정 섹션
        api_frame = ttk.LabelFrame(main_frame, text="OpenAI API 설정", padding="10")
        api_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(api_frame, text="API 키:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.api_key_entry = ttk.Entry(api_frame, width=30, show="*")
        self.api_key_entry.grid(row=0, column=1, pady=2, padx=5)
        
        # 댓글 작성 시간 설정
        delay_frame = ttk.LabelFrame(main_frame, text="댓글 작성 시간 설정", padding="10")
        delay_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(delay_frame, text="게시글 접속 후 대기 시간 (초):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.delay_entry = ttk.Entry(delay_frame, width=10)
        self.delay_entry.insert(0, "10")
        self.delay_entry.grid(row=0, column=1, pady=2, padx=5, sticky=tk.W)
        
        ttk.Label(delay_frame, text="최소 대기 시간 (초):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.min_delay_entry = ttk.Entry(delay_frame, width=10, state='readonly')
        self.min_delay_entry.insert(0, "3")
        self.min_delay_entry.grid(row=1, column=1, pady=2, padx=5, sticky=tk.W)
        
        ttk.Label(delay_frame, text="최대 대기 시간 (초):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.max_delay_entry = ttk.Entry(delay_frame, width=10, state='readonly')
        self.max_delay_entry.insert(0, "5")
        self.max_delay_entry.grid(row=2, column=1, pady=2, padx=5, sticky=tk.W)
        
        # 댓글 작성 횟수 제한 설정
        limit_frame = ttk.LabelFrame(main_frame, text="댓글 작성 횟수 제한", padding="10")
        limit_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(limit_frame, text="작성 횟수 제한:").grid(row=0, column=0, sticky=tk.W, pady=2)
        limit_input_frame = ttk.Frame(limit_frame)
        limit_input_frame.grid(row=0, column=1, pady=2, padx=5, sticky=tk.W)
        
        self.limit_mode_var = tk.StringVar(value="unlimited")
        ttk.Radiobutton(limit_input_frame, text="무한정", variable=self.limit_mode_var, value="unlimited", 
                       command=self._on_limit_mode_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(limit_input_frame, text="제한:", variable=self.limit_mode_var, value="limited",
                       command=self._on_limit_mode_change).pack(side=tk.LEFT, padx=5)
        
        self.limit_entry = ttk.Entry(limit_input_frame, width=15, state=tk.DISABLED)
        self.limit_entry.insert(0, "1000")
        self.limit_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(limit_input_frame, text="번").pack(side=tk.LEFT, padx=2)
        
        # 테스트 모드 체크박스
        test_frame = ttk.Frame(main_frame)
        test_frame.grid(row=4, column=0, columnspan=2, pady=5)
        
        # 테스트 모드 기본값: True (안전을 위해)
        self.test_mode_var = tk.BooleanVar(value=True if not self.force_test_mode else True)
        test_check = ttk.Checkbutton(test_frame, text="✅ 테스트 모드 (실제 댓글 작성 안 함) - 권장", variable=self.test_mode_var)
        test_check.pack()
        
        # 테스트 모드 강제 활성화인 경우 체크박스 비활성화
        if self.force_test_mode:
            test_check.config(state=tk.DISABLED)
            # 테스트 모드 안내 라벨 추가
            test_label = ttk.Label(test_frame, text="⚠️ 테스트 모드로만 실행됩니다", foreground="orange")
            test_label.pack(pady=(5, 0))
        
        # 모드 선택 (매크로 모드 / 학습 모드 / 좋아요 모드)
        mode_frame = ttk.LabelFrame(main_frame, text="실행 모드", padding="10")
        mode_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.mode_var = tk.StringVar(value="macro")
        ttk.Radiobutton(mode_frame, text="📝 매크로 모드 (댓글 작성)", 
                       variable=self.mode_var, value="macro").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="📚 학습 모드 (댓글 수집만)", 
                       variable=self.mode_var, value="learning").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="👍 좋아요 모드 (좋아요만)", 
                       variable=self.mode_var, value="like").pack(side=tk.LEFT, padx=10)
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=10)
        
        self.save_btn = ttk.Button(button_frame, text="설정 저장", command=self.save_config)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        self.start_btn = ttk.Button(button_frame, text="시작", command=self.start_macro, state=tk.NORMAL)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="중지", command=self.stop_macro, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 로그 영역
        log_frame = ttk.LabelFrame(main_frame, text="실행 로그", padding="10")
        log_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=70, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 상태바
        self.status_label = ttk.Label(main_frame, text="대기 중...", relief=tk.SUNKEN)
        self.status_label.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 그리드 가중치 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(7, weight=1)
    
    def log(self, message: str):
        """로그 메시지 추가"""
        self.log_text.config(state=tk.NORMAL)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def load_saved_config(self):
        """저장된 설정 로드"""
        config = self.config_manager.load_config()
        if config:
            self.username_entry.insert(0, config.get('username', ''))
            self.password_entry.insert(0, config.get('password', ''))
            self.api_key_entry.insert(0, config.get('api_key', ''))
            self.delay_entry.delete(0, tk.END)
            self.delay_entry.insert(0, str(config.get('comment_delay', 10)))
            # 최소/최대 대기 시간은 고정값 사용 (3초, 5초)
            self.min_delay_entry.config(state='normal')
            self.min_delay_entry.delete(0, tk.END)
            self.min_delay_entry.insert(0, "3")
            self.min_delay_entry.config(state='readonly')
            self.max_delay_entry.config(state='normal')
            self.max_delay_entry.delete(0, tk.END)
            self.max_delay_entry.insert(0, "5")
            self.max_delay_entry.config(state='readonly')
            
            # 댓글 작성 횟수 제한 설정 로드 (호환성 처리)
            limit_mode = config.get('limit_mode', 'unlimited')
            limit_count = config.get('limit_count', 1000)
            self.limit_mode_var.set(limit_mode)
            self.limit_entry.delete(0, tk.END)
            self.limit_entry.insert(0, str(limit_count))
            # 필드 활성화 상태 업데이트
            self._on_limit_mode_change()
            
            self.log("저장된 설정을 불러왔습니다.")
    
    def _on_limit_mode_change(self):
        """횟수 제한 모드 변경 시 입력 필드 활성화/비활성화"""
        if self.limit_mode_var.get() == "limited":
            self.limit_entry.config(state=tk.NORMAL)
        else:
            self.limit_entry.config(state=tk.DISABLED)
    
    def save_config(self):
        """설정 저장"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        api_key = self.api_key_entry.get().strip()
        
        if not username or not password or not api_key:
            messagebox.showwarning("경고", "모든 필드를 입력해주세요.")
            return
        
        try:
            delay = int(self.delay_entry.get())
            # 최소/최대 대기 시간은 고정값 사용 (3초, 5초)
            min_delay = 3
            max_delay = 5
            
            # 댓글 작성 횟수 제한 설정
            limit_mode = self.limit_mode_var.get()
            if limit_mode == "limited":
                try:
                    limit_count = int(self.limit_entry.get())
                    if limit_count <= 0:
                        raise ValueError("횟수는 1 이상이어야 합니다.")
                except ValueError as e:
                    messagebox.showerror("오류", f"작성 횟수는 양수로 입력해주세요.\n{str(e)}")
                    return
            else:
                limit_count = 0  # 무한정
            
        except ValueError:
            messagebox.showerror("오류", "대기 시간은 숫자로 입력해주세요.")
            return
        
        self.config_manager.save_config(username, password, api_key, delay, min_delay, max_delay, 
                                       limit_mode=limit_mode, limit_count=limit_count)
        messagebox.showinfo("성공", "설정이 저장되었습니다.")
        self.log("설정이 저장되었습니다.")
    
    def start_macro(self):
        """매크로 시작"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        api_key = self.api_key_entry.get().strip()
        mode = self.mode_var.get()
        
        # 좋아요 모드는 API 키 불필요
        if mode == "like":
            if not username or not password:
                messagebox.showwarning("경고", "아이디와 비밀번호를 입력해주세요.")
                return
        else:
            if not username or not password or not api_key:
                messagebox.showwarning("경고", "모든 필드를 입력해주세요.")
                return
        
        try:
            delay = int(self.delay_entry.get())
            # 최소/최대 대기 시간은 고정값 사용 (3초, 5초)
            min_delay = 3
            max_delay = 5
            
            # 댓글 작성 횟수 제한 설정
            limit_mode = self.limit_mode_var.get()
            if limit_mode == "limited":
                try:
                    limit_count = int(self.limit_entry.get())
                    if limit_count <= 0:
                        raise ValueError("횟수는 1 이상이어야 합니다.")
                except ValueError as e:
                    messagebox.showerror("오류", f"작성 횟수는 양수로 입력해주세요.\n{str(e)}")
                    return
            else:
                limit_count = 0  # 무한정
            
        except ValueError:
            messagebox.showerror("오류", "대기 시간은 숫자로 입력해주세요.")
            return
        
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # 설정 필드 비활성화
        self.username_entry.config(state=tk.DISABLED)
        self.password_entry.config(state=tk.DISABLED)
        self.api_key_entry.config(state=tk.DISABLED)
        self.delay_entry.config(state=tk.DISABLED)
        # 최소/최대 대기 시간은 readonly 상태 유지
        self.min_delay_entry.config(state='readonly')
        self.max_delay_entry.config(state='readonly')
        
        # 모드에 따라 워커 선택
        mode = self.mode_var.get()
        if mode == "like":
            # 좋아요 전용 모드 (설정값 없이 고정값 사용)
            # 좋아요 전용 모드
            self.worker_thread = threading.Thread(
                target=self.like_worker,
                args=(username, password, delay),
                daemon=True
            )
            self.worker_thread.start()
            self.log(f"좋아요 모드를 시작합니다... (24시간 이내 게시글 오래된 것부터 순차 처리)")
            self.status_label.config(text="좋아요 모드 실행 중...")
        else:
            # 기존 매크로/학습 모드
            self.worker_thread = threading.Thread(
                target=self.macro_worker,
                args=(username, password, api_key, delay, min_delay, max_delay, limit_mode, limit_count),
                daemon=True
            )
            self.worker_thread.start()
            limit_text = "무한정" if limit_mode == "unlimited" else f"{limit_count}번"
            self.log(f"매크로를 시작합니다... (제한: {limit_text})")
            self.status_label.config(text=f"실행 중... (제한: {limit_text})")
    
    def stop_macro(self):
        """매크로 중지"""
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        # 설정 필드 활성화
        self.username_entry.config(state=tk.NORMAL)
        self.password_entry.config(state=tk.NORMAL)
        self.api_key_entry.config(state=tk.NORMAL)
        self.delay_entry.config(state=tk.NORMAL)
        # 최소/최대 대기 시간은 readonly 상태 유지
        self.min_delay_entry.config(state='readonly')
        self.max_delay_entry.config(state='readonly')
        
        # 모드 선택 활성화
        for widget in self.root.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, ttk.LabelFrame):
                    for grandchild in child.winfo_children():
                        if isinstance(grandchild, ttk.Radiobutton):
                            grandchild.config(state=tk.NORMAL)
        
        if self.scraper:
            self.scraper.close()
        
        self.log("매크로를 중지합니다...")
        self.status_label.config(text="중지됨")
    
    def macro_worker(self, username: str, password: str, api_key: str, 
                    delay: int, min_delay: int, max_delay: int, 
                    limit_mode: str = "unlimited", limit_count: int = 0):
        """매크로 작업 스레드"""
        max_retries = 3
        retry_count = 0
        
        while self.is_running and retry_count < max_retries:
            try:
                # 스크래퍼 및 AI 생성기 초기화
                test_mode = self.test_mode_var.get()
                self.scraper = OncaPanScraper(test_mode=test_mode)
                # RealtimeLearner 초기화 (학습 기능 포함)
                try:
                    from realtime_learner import RealtimeLearner
                    self.learner = RealtimeLearner()
                    # 학습 분석기 가져오기
                    learning_analyzer = self.learner.learning_analyzer if hasattr(self.learner, 'learning_analyzer') else None
                except Exception as e:
                    logger.warning(f"RealtimeLearner 초기화 실패: {e}")
                    self.learner = None
                    learning_analyzer = None
                
                self.ai_generator = AICommentGenerator(api_key, learning_analyzer=learning_analyzer)
                
                if test_mode:
                    self.root.after(0, partial(self.log, "⚠️ 테스트 모드로 실행됩니다. 실제 댓글은 작성되지 않습니다."))
                
                # 로그인 시도
                self.root.after(0, partial(self.log, "로그인 시도 중..."))
                if not self.scraper.login(username, password):
                    retry_count += 1
                    if retry_count < max_retries:
                        self.root.after(0, partial(self.log, f"로그인 실패. 재시도 중... ({retry_count}/{max_retries})"))
                        time.sleep(5)
                        continue
                    else:
                        self.root.after(0, partial(self.log, "로그인 실패. 매크로를 중지합니다."))
                        self.root.after(0, self.stop_macro)
                        return
                
                self.root.after(0, partial(self.log, "로그인 성공!"))
                retry_count = 0  # 로그인 성공 시 재시도 카운트 리셋
                
                # 이미 댓글 단 게시글 추적 (파일로 저장하여 영구 보존)
                # exe 실행 시 현재 디렉토리에 파일 생성
                try:
                    if getattr(sys, 'frozen', False):
                        # PyInstaller로 빌드된 exe인 경우
                        base_path = os.path.dirname(sys.executable)
                    else:
                        # 스크립트로 실행하는 경우
                        base_path = os.path.dirname(os.path.abspath(__file__))
                except:
                    base_path = os.getcwd()
                commented_posts_file = os.path.join(base_path, "commented_posts.json")
                commented_posts = self._load_commented_posts(commented_posts_file)
                if commented_posts:
                    self.root.after(0, partial(self.log, f"📝 이전 댓글 작성 이력 로드: {len(commented_posts)}개 게시글"))
                
                # 댓글 작성 횟수 카운터
                comment_count = 0
                limit_reached = False
                # 배치 저장을 위한 카운터
                save_counter = 0
                SAVE_INTERVAL = 5  # 5개마다 저장
                
                # 메인 루프
                while self.is_running and not limit_reached:
                    try:
                        # 게시글 목록 가져오기
                        posts = self.scraper.get_post_list(limit=20)
                        
                        if not posts:
                            time.sleep(30)
                            continue
                        
                        # 각 게시글 처리
                        for post in posts:
                            if not self.is_running:
                                break
                            
                            post_id = post.get('id')
                            post_url = post.get('url')
                            
                            if not post_id or not post_url:
                                continue
                            
                            # 이미 댓글 단 게시글은 건너뛰기
                            if post_id in commented_posts:
                                continue
                            
                            # 이미 댓글을 달았는지 확인
                            if self.scraper.has_commented(post_url, username):
                                commented_posts.add(post_id)
                                save_counter += 1
                                # 배치 저장 (5개마다 또는 중요한 시점에)
                                if save_counter >= SAVE_INTERVAL:
                                    self._save_commented_posts(commented_posts, commented_posts_file)
                                    save_counter = 0
                                continue
                            
                            # 24시간 이내 게시글인지 확인 (개선된 날짜 파싱)
                            post_datetime_str = post.get('datetime')
                            if post_datetime_str:
                                try:
                                    now = datetime.now()
                                    post_date = None
                                    
                                    # 다양한 날짜 형식 파싱 시도
                                    date_formats = [
                                        '%Y-%m-%d %H:%M:%S',
                                        '%Y-%m-%d %H:%M',
                                        '%Y-%m-%d',
                                        '%m-%d %H:%M',
                                        '%m-%d',
                                        '%Y.%m.%d %H:%M',
                                        '%Y.%m.%d',
                                    ]
                                    
                                    for fmt in date_formats:
                                        try:
                                            post_date = datetime.strptime(post_datetime_str.strip(), fmt)
                                            # 연도가 없는 경우 현재 연도 사용
                                            if '%Y' not in fmt:
                                                post_date = post_date.replace(year=now.year)
                                                if post_date > now:
                                                    post_date = post_date.replace(year=now.year - 1)
                                            break
                                        except ValueError:
                                            continue
                                    
                                    # 파싱 실패 시 간단한 형식 재시도
                                    if post_date is None and '-' in post_datetime_str:
                                        parts = post_datetime_str.split('-')
                                        if len(parts) >= 2:
                                            try:
                                                month, day = int(parts[0]), int(parts[1].split()[0] if ' ' in parts[1] else parts[1])
                                                post_date = now.replace(month=month, day=day, hour=0, minute=0, second=0, microsecond=0)
                                                if post_date > now:
                                                    post_date = post_date.replace(year=now.year - 1)
                                            except (ValueError, IndexError):
                                                pass
                                    
                                    # 24시간 이내 게시글만 처리
                                    if post_date and now - post_date > timedelta(hours=24):
                                        continue
                                        
                                except Exception as e:
                                    logger.debug(f"날짜 파싱 실패: {post_datetime_str}, 오류: {e}")
                                    # 날짜 파싱 실패 시 계속 진행 (24시간 체크 스킵)
                                    pass
                            
                            # 게시글 내용 가져오기
                            post_title = post.get('title', '')[:30]
                            post_data = self.scraper.get_post_content(post_url)
                            
                            if not post_data:
                                continue
                            
                            post_content = post_data.get('content', '')
                            # 실제 페이지에서 추출한 제목 사용 (없으면 목록에서 가져온 제목 사용)
                            actual_post_title = post_data.get('title', '') or post.get('title', '')
                            
                            # 1. 게시물 제목 (전체)
                            self.root.after(0, partial(self.log, f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
                            self.root.after(0, partial(self.log, f"📄 【게시물 제목】"))
                            self.root.after(0, partial(self.log, f"{actual_post_title if actual_post_title else '(제목 없음)'}"))
                            
                            # 2. 게시물 본문 (전체)
                            self.root.after(0, partial(self.log, f""))
                            self.root.after(0, partial(self.log, f"📝 【게시물 본문】"))
                            if post_content:
                                # 본문이 길 경우 여러 줄로 나누어 표시
                                content_lines = post_content.split('\n')
                                for line in content_lines:
                                    if line.strip():
                                        self.root.after(0, partial(self.log, f"{line}"))
                            else:
                                self.root.after(0, partial(self.log, f"(본문 없음)"))
                            
                            # 실시간 학습: 게시글에서 댓글 수집
                            try:
                                if not self.learner:
                                    from realtime_learner import RealtimeLearner
                                    self.learner = RealtimeLearner()
                                actual_comments = self.learner.collect_comments_from_post(self.scraper, post_url)
                                
                                # 3. 댓글들 (전체 목록)
                                self.root.after(0, partial(self.log, f""))
                                self.root.after(0, partial(self.log, f"💬 【댓글 목록】 (총 {len(actual_comments) if actual_comments else 0}개)"))
                                if actual_comments:
                                    for i, comment in enumerate(actual_comments, 1):
                                        comment_text = comment if isinstance(comment, str) else comment.get('content', str(comment))
                                        self.root.after(0, partial(self.log, f"  {i}. {comment_text}"))
                                else:
                                    actual_comments = []
                                    self.root.after(0, partial(self.log, f"  (댓글 없음)"))
                            except Exception as e:
                                # 실시간 학습 실패 시 빈 리스트 사용
                                actual_comments = []
                                self.root.after(0, partial(self.log, f""))
                                self.root.after(0, partial(self.log, f"💬 【댓글 목록】 (수집 실패: {str(e)})"))
                            
                            # 디버그 로그에 게시글 정보 기록
                            try:
                                debug_log_file = "ai_debug_log.txt"
                                with open(debug_log_file, 'a', encoding='utf-8') as f:
                                    f.write("\n" + "="*80 + "\n")
                                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 게시글 정보\n")
                                    f.write("="*80 + "\n\n")
                                    f.write("【게시글 제목】\n")
                                    f.write(f"{actual_post_title if actual_post_title else '(제목 없음)'}\n\n")
                                    f.write("【게시글 본문】\n")
                                    content_preview = post_content[:500] if post_content else "(본문 없음)"
                                    f.write(f"{content_preview}")
                                    if post_content and len(post_content) > 500:
                                        f.write(f"\n... (전체 {len(post_content)}자 중 500자만 표시)")
                                    f.write("\n\n")
                            except Exception as e:
                                logger.debug(f"디버그 로그 기록 실패: {e}")
                            
                            # 댓글 생성 가능 여부 확인
                            if not self.ai_generator.can_generate_comment(post_content):
                                continue
                            
                            # 3. 키워드 표시 (댓글 생성 전)
                            try:
                                keywords = self.ai_generator._extract_keywords(
                                    comments=actual_comments,
                                    post_title=actual_post_title or "",
                                    post_content=post_content or ""
                                )
                                if keywords:
                                    self.root.after(0, partial(self.log, f"🔑 키워드: {', '.join(keywords[:8])}"))
                            except Exception as e:
                                logger.debug(f"키워드 추출 오류: {e}")
                            
                            # 설정된 대기 시간
                            wait_time = random.uniform(min_delay, max_delay)
                            time.sleep(wait_time)
                            
                            # AI 댓글 생성
                            try:
                                self.root.after(0, partial(self.log, f"🤖 AI 댓글 생성 중..."))
                                comment = self.ai_generator.generate_comment(
                                    post_content, 
                                    actual_post_title, 
                                    actual_comments,
                                    post_id=post_id  # 게시글별 중복 방지
                                )
                                
                                if not comment:
                                    self.root.after(0, partial(self.log, f"❌ AI 댓글 생성 실패 (댓글 없음 또는 생성 오류)"))
                                    logger.warning(f"AI 댓글 생성 실패: post_title={actual_post_title}, comments_count={len(actual_comments) if actual_comments else 0}")
                                    # 실패 원인 로깅
                                    stats = self.ai_generator.get_stats()
                                    failure_reasons = stats.get('failure_reasons', {})
                                    if failure_reasons:
                                        top_failure = max(failure_reasons.items(), key=lambda x: x[1], default=None)
                                        if top_failure:
                                            self.root.after(0, partial(self.log, f"   주요 실패 원인: {top_failure[0]} ({top_failure[1]}회)"))
                                    # 디버그: 생성 시도한 후보 확인 (로그 파일에 기록)
                                    try:
                                        debug_log_file = "ai_debug_log.txt"
                                        with open(debug_log_file, 'a', encoding='utf-8') as f:
                                            f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 댓글 생성 실패\n")
                                            f.write(f"게시글: {actual_post_title}\n")
                                            f.write(f"실패 원인: {top_failure[0] if top_failure else '알 수 없음'}\n\n")
                                    except:
                                        pass
                                    continue
                            except Exception as e:
                                self.root.after(0, partial(self.log, f"❌ AI 댓글 생성 오류: {str(e)}"))
                                logger.error(f"AI 댓글 생성 예외 발생: {e}", exc_info=True)
                                continue
                            
                            # 4. AI가 작성한 댓글 (전체)
                            self.root.after(0, partial(self.log, f""))
                            self.root.after(0, partial(self.log, f"🤖 【AI가 작성한 댓글】"))
                            self.root.after(0, partial(self.log, f"{comment}"))
                            
                            # 학습 로그 기록 (테스트 모드 포함, 댓글 작성 전에 기록)
                            if self.learner:
                                try:
                                    self.learner.log_post_processing(
                                        actual_post_title or "",
                                        post_content or "",
                                        actual_comments or [],
                                        comment,
                                        post_url
                                    )
                                except Exception as e:
                                    logger.error(f"학습 로그 기록 오류: {e}")
                            
                            # 댓글 작성 시도 (테스트 모드 체크)
                            write_success = False
                            write_error = None
                            
                            # 테스트 모드 확인
                            test_mode = getattr(self.scraper, 'test_mode', False) if self.scraper else False
                            
                            if test_mode:
                                # 테스트 모드: 실제 작성하지 않고 시뮬레이션만
                                write_success = True  # 테스트 모드에서는 성공으로 처리
                                self.root.after(0, partial(self.log, f"🧪 [테스트 모드] 댓글 작성 시뮬레이션: {comment}"))
                            else:
                                try:
                                    write_success = self.scraper.write_comment(post_url, comment)
                                    if not write_success:
                                        write_error = "댓글 작성 실패 (원인 불명)"
                                except Exception as e:
                                    write_error = str(e)
                                    logger.error(f"댓글 작성 예외 발생: {e}", exc_info=True)
                            
                            if write_success:
                                commented_posts.add(post_id)
                                comment_count += 1
                                save_counter += 1
                                
                                # 배치 저장 (5개마다 또는 목표 달성 시)
                                if save_counter >= SAVE_INTERVAL or (limit_mode == "limited" and comment_count >= limit_count):
                                    self._save_commented_posts(commented_posts, commented_posts_file)
                                    save_counter = 0
                                
                                self.root.after(0, partial(self.log, f"✅ 댓글 작성 완료 ({comment_count}번째)"))
                                
                                # 횟수 제한 체크
                                if limit_mode == "limited" and comment_count >= limit_count:
                                    limit_reached = True
                                    # 목표 달성 시 즉시 저장
                                    self._save_commented_posts(commented_posts, commented_posts_file)
                                    # 통계도 즉시 저장
                                    if self.ai_generator:
                                        self.ai_generator.save_stats_now()
                                    self.root.after(0, partial(self.log, f"🎯 목표 횟수 달성: {limit_count}번 작성 완료"))
                                    self.root.after(0, partial(self.log, "매크로를 자동으로 중지합니다."))
                                    break
                                
                                status_text = f"댓글 작성 완료: {comment_count}번"
                                if limit_mode == "limited":
                                    status_text += f" / 목표: {limit_count}번"
                                self.root.after(0, partial(self.status_label.config, text=status_text))
                            else:
                                # 댓글 작성 실패 상세 로깅
                                error_msg = f"❌ 댓글 작성 실패"
                                if write_error:
                                    error_msg += f": {write_error}"
                                self.root.after(0, partial(self.log, error_msg))
                                logger.warning(f"댓글 작성 실패: post_id={post_id}, error={write_error}")
                                # 실패해도 commented_posts에 추가하지 않음 (재시도 가능)
                            
                            self.root.after(0, partial(self.log, f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
                            
                            # 게시글 간 대기 시간
                            time.sleep(delay)
                        
                        # 남은 변경사항 저장
                        if save_counter > 0:
                            self._save_commented_posts(commented_posts, commented_posts_file)
                            save_counter = 0
                        
                        # 횟수 제한에 도달했는지 확인
                        if limit_reached:
                            break
                        
                        # 게시글 목록 새로고침 대기
                        time.sleep(60)  # 1분마다 게시글 목록 새로고침
                        
                    except Exception as e:
                        logger.error(f"게시글 처리 오류: {e}", exc_info=True)
                        error_msg = f"오류 발생: {str(e)}"
                        self.root.after(0, partial(self.log, error_msg))
                        time.sleep(10)
                        continue
                    
                    # 횟수 제한에 도달했는지 확인
                    if limit_reached:
                        self.root.after(0, partial(self.log, f"✅ 목표 횟수 달성: {comment_count}번 작성 완료"))
                        self.root.after(0, self.stop_macro)
                        break
                
            except Exception as e:
                logger.error(f"매크로 작업 오류: {e}", exc_info=True)
                error_msg = f"심각한 오류 발생: {str(e)}"
                self.root.after(0, partial(self.log, error_msg))
                retry_count += 1
                if retry_count < max_retries:
                    self.root.after(0, partial(self.log, f"재시도 중... ({retry_count}/{max_retries})"))
                    time.sleep(10)
                else:
                    self.root.after(0, partial(self.log, "최대 재시도 횟수 초과. 매크로를 중지합니다."))
                    self.root.after(0, self.stop_macro)
                    break
            finally:
                if self.scraper:
                    self.scraper.close()
    
    def _load_commented_posts(self, filename: str) -> set:
        """댓글 작성 이력 로드 (파일 크기 관리 포함)"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    # Windows에서 파일 락 시도
                    try:
                        if os.name == 'nt':  # Windows
                            try:
                                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
                            except NameError:
                                pass  # msvcrt가 없는 경우
                        else:  # Unix/Linux
                            try:
                                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                            except NameError:
                                pass  # fcntl이 없는 경우
                    except:
                        pass  # 락 실패해도 계속 진행
                    
                    data = json.load(f)
                    
                    # 락 해제
                    try:
                        if os.name == 'nt':
                            try:
                                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                            except NameError:
                                pass
                        else:
                            try:
                                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                            except NameError:
                                pass
                    except:
                        pass
                    
                    if isinstance(data, list):
                        post_ids = set(data)
                    elif isinstance(data, dict) and 'post_ids' in data:
                        post_ids = set(data['post_ids'])
                    else:
                        post_ids = set()
                    
                    # 파일 크기 관리: 최대 10000개만 유지 (오래된 것부터 제거)
                    MAX_POSTS = 10000
                    if len(post_ids) > MAX_POSTS:
                        post_ids = set(list(post_ids)[-MAX_POSTS:])  # 최신 것만 유지
                        logger.info(f"댓글 작성 이력이 {MAX_POSTS}개를 초과하여 최신 {MAX_POSTS}개만 유지합니다.")
                    
                    return post_ids
            return set()
        except Exception as e:
            logger.warning(f"댓글 작성 이력 로드 실패: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return set()
    
    def _save_commented_posts(self, commented_posts: set, filename: str):
        """댓글 작성 이력 저장 (파일 락 및 크기 관리 포함)"""
        try:
            # 파일 크기 관리: 최대 10000개만 유지
            MAX_POSTS = 10000
            if len(commented_posts) > MAX_POSTS:
                commented_posts = set(list(commented_posts)[-MAX_POSTS:])
                logger.info(f"댓글 작성 이력이 {MAX_POSTS}개를 초과하여 최신 {MAX_POSTS}개만 유지합니다.")
            
            data = {
                'post_ids': list(commented_posts),
                'count': len(commented_posts),
                'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 임시 파일로 저장 후 원자적 이동 (충돌 방지)
            temp_filename = filename + '.tmp'
            with open(temp_filename, 'w', encoding='utf-8') as f:
                # Windows에서 파일 락 시도
                try:
                    if os.name == 'nt':  # Windows
                        try:
                            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
                        except NameError:
                            pass  # msvcrt가 없는 경우
                    else:  # Unix/Linux
                        try:
                            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                        except NameError:
                            pass  # fcntl이 없는 경우
                except:
                    pass  # 락 실패해도 계속 진행
                
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())  # 디스크에 강제 쓰기
                
                # 락 해제
                try:
                    if os.name == 'nt':
                        try:
                            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                        except NameError:
                            pass
                    else:
                        try:
                            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                        except NameError:
                            pass
                except:
                    pass
            
            # 원자적 이동 (Windows에서는 replace 사용)
            if os.name == 'nt':
                if os.path.exists(filename):
                    os.replace(temp_filename, filename)
                else:
                    os.rename(temp_filename, filename)
            else:
                os.replace(temp_filename, filename)
                
        except Exception as e:
            logger.error(f"댓글 작성 이력 저장 실패: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            # 임시 파일 정리
            try:
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
            except:
                pass
    
    def like_worker(self, username: str, password: str, delay: int):
        """좋아요 전용 워커 스레드"""
        max_retries = 3
        retry_count = 0
        last_login_check = time.time()
        LOGIN_CHECK_INTERVAL = 300  # 5분마다 로그인 상태 확인
        cloudflare_block_count = 0
        MAX_CLOUDFLARE_BLOCKS = 3  # Cloudflare 차단 최대 횟수
        
        # 좋아요 클릭 실패 추적 (게시글별)
        failed_posts = {}  # {post_id: failure_count}
        MAX_FAILURES = 3  # 최대 실패 횟수
        
        while self.is_running and retry_count < max_retries:
            try:
                # 스크래퍼 초기화
                # 좋아요 모드는 항상 실제 모드로 실행 (테스트 모드 체크박스 무시)
                test_mode = False  # 좋아요 모드는 항상 실제 모드
                self.scraper = OncaPanScraper(test_mode=test_mode)
                
                # 실제 모드로 실행
                self.root.after(0, partial(self.log, "✅ 실제 모드로 실행됩니다. 실제 좋아요를 누릅니다."))
                logger.info("좋아요 모드: 실제 모드 활성화 (테스트 모드 체크박스 무시)")
                
                # 로그인 시도
                self.root.after(0, partial(self.log, "로그인 시도 중..."))
                if not self.scraper.login(username, password):
                    retry_count += 1
                    if retry_count < max_retries:
                        self.root.after(0, partial(self.log, f"로그인 실패. 재시도 중... ({retry_count}/{max_retries})"))
                        time.sleep(5)
                        continue
                    else:
                        self.root.after(0, partial(self.log, "로그인 실패. 좋아요 모드를 중지합니다."))
                        self.root.after(0, self.stop_macro)
                        return
                
                self.root.after(0, partial(self.log, "로그인 성공!"))
                retry_count = 0
                last_login_check = time.time()
                cloudflare_block_count = 0
                
                # 좋아요를 누른 게시글 목록 로드
                try:
                    if getattr(sys, 'frozen', False):
                        base_path = os.path.dirname(sys.executable)
                    else:
                        base_path = os.path.dirname(os.path.abspath(__file__))
                except:
                    base_path = os.getcwd()
                
                liked_posts_file = os.path.join(base_path, "liked_posts.json")
                liked_posts = self._load_liked_posts(liked_posts_file)
                if liked_posts:
                    self.root.after(0, partial(self.log, f"👍 이전 좋아요 이력 로드: {len(liked_posts)}개 게시글"))
                
                # 좋아요 카운터
                like_count = 0
                save_counter = 0
                SAVE_INTERVAL = 5  # 5개마다 저장
                
                # 초기 실행 여부 (모든 24시간 이내 게시글 처리 완료 여부)
                initial_processing_done = False
                
                # 메인 루프
                while self.is_running:
                    try:
                        # 주기적으로 로그인 상태 확인
                        current_time = time.time()
                        if current_time - last_login_check >= LOGIN_CHECK_INTERVAL:
                            self.root.after(0, partial(self.log, "🔍 로그인 상태 확인 중..."))
                            if not self.scraper.is_logged_in():
                                self.root.after(0, partial(self.log, "⚠️ 로그아웃 상태 감지. 재로그인 시도..."))
                                if not self.scraper.login(username, password):
                                    self.root.after(0, partial(self.log, "❌ 재로그인 실패. 좋아요 모드를 중지합니다."))
                                    self.root.after(0, self.stop_macro)
                                    break
                                else:
                                    self.root.after(0, partial(self.log, "✅ 재로그인 성공!"))
                            last_login_check = current_time
                        
                        # Cloudflare 차단 확인
                        if self.scraper.check_cloudflare_block():
                            cloudflare_block_count += 1
                            self.root.after(0, partial(self.log, f"⚠️ Cloudflare 차단 감지 ({cloudflare_block_count}/{MAX_CLOUDFLARE_BLOCKS})"))
                            
                            if cloudflare_block_count >= MAX_CLOUDFLARE_BLOCKS:
                                self.root.after(0, partial(self.log, "❌ Cloudflare 차단이 지속됩니다. 좋아요 모드를 중지합니다."))
                                self.root.after(0, self.stop_macro)
                                break
                            
                            # 차단 감지 시 대기
                            self.root.after(0, partial(self.log, "⏳ 30초 대기 후 재시도..."))
                            time.sleep(30)
                            continue
                        else:
                            cloudflare_block_count = 0  # 정상 상태면 카운터 리셋
                        
                        # 게시글 목록 가져오기 (24시간 이내 모든 게시글, 오래된 것부터)
                        # limit을 매우 크게 설정하여 모든 24시간 이내 게시글 가져오기
                        posts = self.scraper.get_post_list(limit=10000)
                        
                        if not posts:
                            self.root.after(0, partial(self.log, "게시글이 없습니다. 30초 후 다시 시도합니다."))
                            time.sleep(30)
                            continue
                        
                        # 좋아요를 누르지 않은 게시글만 필터링
                        # 실패 횟수가 너무 많은 게시글은 제외
                        # 정렬 순서 유지 (오래된 것부터)
                        new_posts = [
                            post for post in posts 
                            if post.get('id') not in liked_posts 
                            and failed_posts.get(post.get('id'), 0) < MAX_FAILURES
                        ]
                        
                        # 정렬 순서 확인 및 로깅 (처음 게시글의 날짜 확인)
                        if new_posts and len(new_posts) > 0:
                            first_post = new_posts[0]
                            last_post = new_posts[-1]
                            first_date = first_post.get('datetime', '날짜 없음')
                            last_date = last_post.get('datetime', '날짜 없음')
                            logger.debug(f"처리 순서 확인 - 첫 게시글: {first_date}, 마지막 게시글: {last_date}")
                        
                        if not new_posts:
                            skipped_count = sum(1 for post in posts if failed_posts.get(post.get('id'), 0) >= MAX_FAILURES)
                            
                            if not initial_processing_done:
                                # 처음 모든 24시간 이내 게시글 처리 완료
                                initial_processing_done = True
                                self.root.after(0, partial(self.log, f"✅ 모든 24시간 이내 게시글에 좋아요 완료! (전체: {len(posts)}개, 좋아요: {len(liked_posts)}개, 실패 건너뛰기: {skipped_count}개)"))
                                self.root.after(0, partial(self.log, f"🔄 이제 새로운 게시글만 확인합니다..."))
                            else:
                                # 이후 새로운 게시글만 확인
                                self.root.after(0, partial(self.log, f"📋 새로운 게시글 없음 (현재 좋아요: {len(liked_posts)}개)"))
                            
                            self.root.after(0, partial(self.log, f"⏳ 30초 후 다시 확인합니다..."))
                            time.sleep(30)  # 새로운 게시글 확인 주기 (30초)
                            continue
                        
                        # 처음 실행 시 안내
                        if not initial_processing_done and len(new_posts) > 0:
                            self.root.after(0, partial(self.log, f"📋 24시간 이내 게시글 {len(new_posts)}개 발견 (오래된 것부터 순차 처리)"))
                        
                        self.root.after(0, partial(self.log, f"📋 처리할 게시글: {len(new_posts)}개"))
                        
                        # 각 게시글 처리
                        for post in new_posts:
                            if not self.is_running:
                                break
                            
                            post_id = post.get('id')
                            post_url = post.get('url')
                            
                            if not post_id or not post_url:
                                continue
                            
                            # 이미 좋아요를 누른 게시글은 건너뛰기
                            if post_id in liked_posts:
                                continue
                            
                            # 24시간 이내 게시글인지 확인
                            # (get_post_list에서 이미 필터링하지만, 안전장치로 다시 확인)
                            post_datetime_str = post.get('datetime')
                            post_datetime_obj = post.get('datetime_obj')  # get_post_list에서 파싱된 datetime 객체
                            
                            if post_datetime_obj:
                                # 이미 파싱된 datetime 객체 사용
                                now = datetime.now()
                                time_diff = now - post_datetime_obj
                                if time_diff > timedelta(hours=24):
                                    self.root.after(0, partial(self.log, f"⏰ 24시간 초과 게시글 건너뛰기: {post.get('title', '')[:30]}"))
                                    continue
                            elif post_datetime_str:
                                # datetime 객체가 없으면 문자열 파싱
                                try:
                                    now = datetime.now()
                                    post_date = None
                                    
                                    # 날짜 파싱
                                    date_formats = [
                                        '%Y-%m-%d %H:%M:%S',
                                        '%Y-%m-%d %H:%M',
                                        '%Y-%m-%d',
                                        '%m-%d %H:%M',
                                        '%m-%d',
                                    ]
                                    
                                    for fmt in date_formats:
                                        try:
                                            post_date = datetime.strptime(post_datetime_str.strip(), fmt)
                                            if '%Y' not in fmt:
                                                post_date = post_date.replace(year=now.year)
                                                if post_date > now:
                                                    post_date = post_date.replace(year=now.year - 1)
                                            break
                                        except ValueError:
                                            continue
                                    
                                    if post_date:
                                        time_diff = now - post_date
                                        if time_diff > timedelta(hours=24):
                                            self.root.after(0, partial(self.log, f"⏰ 24시간 초과 게시글 건너뛰기: {post.get('title', '')[:30]}"))
                                            continue
                                        
                                except Exception as e:
                                    logger.debug(f"날짜 파싱 실패: {post_datetime_str}, 오류: {e}")
                                    # 날짜 파싱 실패 시 계속 진행 (get_post_list에서 이미 필터링했을 가능성)
                                    pass
                            
                            # 게시글 제목 표시
                            post_title = post.get('title', '')[:50]
                            self.root.after(0, partial(self.log, f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
                            self.root.after(0, partial(self.log, f"📄 【게시글】 {post_title}"))
                            
                            # 좋아요 클릭 시도 (재시도 로직 포함)
                            max_retries = 2
                            like_success = False
                            
                            for attempt in range(max_retries):
                                try:
                                    if attempt == 0:
                                        self.root.after(0, partial(self.log, f"👍 좋아요 클릭 시도 중..."))
                                    else:
                                        self.root.after(0, partial(self.log, f"🔄 좋아요 클릭 재시도 중... ({attempt + 1}/{max_retries})"))
                                    
                                    # 테스트 모드 확인 (스크래퍼의 test_mode 속성 확인)
                                    scraper_test_mode = getattr(self.scraper, 'test_mode', False) if self.scraper else False
                                    
                                    if scraper_test_mode:
                                        # 테스트 모드: 시뮬레이션만
                                        like_success = True
                                        self.root.after(0, partial(self.log, f"🧪 [테스트 모드] 좋아요 클릭 시뮬레이션"))
                                        logger.debug(f"테스트 모드: 좋아요 시뮬레이션 - {post_url}")
                                        break
                                    else:
                                        # 실제 모드: 좋아요 클릭
                                        logger.debug(f"실제 모드: 좋아요 클릭 시도 - {post_url}")
                                        like_success = self.scraper.click_like(post_url)
                                        
                                        if like_success:
                                            logger.info(f"좋아요 클릭 성공: {post_url}")
                                            break
                                        elif attempt < max_retries - 1:
                                            # 재시도 전 대기
                                            logger.warning(f"좋아요 클릭 실패, 재시도 예정: {post_url}")
                                            time.sleep(1)
                                            continue
                                        else:
                                            logger.error(f"좋아요 클릭 최종 실패: {post_url}")
                                
                                except Exception as e:
                                    error_msg = str(e)
                                    # 네트워크 오류인지 확인
                                    is_network_error = any(keyword in error_msg.lower() for keyword in [
                                        'timeout', 'connection', 'network', 'unreachable', 'refused'
                                    ])
                                    
                                    if is_network_error and attempt < max_retries - 1:
                                        self.root.after(0, partial(self.log, f"🌐 네트워크 오류 감지 (재시도 예정): {error_msg[:50]}"))
                                        time.sleep(2)  # 네트워크 오류는 더 길게 대기
                                        continue
                                    elif attempt < max_retries - 1:
                                        self.root.after(0, partial(self.log, f"⚠️ 좋아요 클릭 오류 (재시도 예정): {error_msg[:50]}"))
                                        time.sleep(1)
                                        continue
                                    else:
                                        self.root.after(0, partial(self.log, f"❌ 좋아요 클릭 오류: {error_msg}"))
                                        logger.error(f"좋아요 클릭 예외 발생: {e}", exc_info=True)
                            
                            if like_success:
                                # 성공 시에만 목록에 추가
                                liked_posts.add(post_id)
                                # 실패 카운터 초기화
                                if post_id in failed_posts:
                                    del failed_posts[post_id]
                                like_count += 1
                                save_counter += 1
                                
                                # 배치 저장
                                if save_counter >= SAVE_INTERVAL:
                                    self._save_liked_posts(liked_posts, liked_posts_file)
                                    save_counter = 0
                                
                                self.root.after(0, partial(self.log, f"✅ 좋아요 클릭 완료 ({like_count}번째)"))
                                self.root.after(0, partial(self.status_label.config, text=f"좋아요 완료: {like_count}개"))
                            else:
                                # 실패 횟수 증가
                                failed_posts[post_id] = failed_posts.get(post_id, 0) + 1
                                failure_count = failed_posts[post_id]
                                
                                if failure_count >= MAX_FAILURES:
                                    self.root.after(0, partial(self.log, f"⏭️ 좋아요 클릭 실패 {failure_count}회 - 해당 게시글 건너뛰기"))
                                    # 실패 횟수가 많으면 일시적으로 건너뛰기 (다음 새로고침에서 다시 시도)
                                else:
                                    self.root.after(0, partial(self.log, f"❌ 좋아요 클릭 실패 ({failure_count}/{MAX_FAILURES})"))
                                
                                # 실패해도 목록에 추가하지 않음 (재시도 가능)
                            
                            self.root.after(0, partial(self.log, f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
                            
                            # 게시글 간 대기 시간 (최소화)
                            # 좋아요 클릭 후 최소한의 대기만 (빠른 처리)
                            scraper_test_mode = getattr(self.scraper, 'test_mode', False) if self.scraper else False
                            if not scraper_test_mode:
                                time.sleep(0.3)  # 좋아요 처리 완료 대기 (최소화)
                            
                            # delay는 최소값으로 사용 (너무 오래 기다리지 않음)
                            min_delay = max(0.5, delay * 0.3)  # 원래 delay의 30% 또는 최소 0.5초
                            time.sleep(min_delay)
                        
                        # 남은 변경사항 저장
                        if save_counter > 0:
                            self._save_liked_posts(liked_posts, liked_posts_file)
                            save_counter = 0
                        
                        # 실패 카운터 정리 (오래된 실패 기록 제거)
                        if len(failed_posts) > 1000:
                            # 가장 오래된 실패 기록 제거 (간단히 일부만 유지)
                            failed_posts = dict(list(failed_posts.items())[-500:])
                            logger.debug("실패 카운터 정리 완료")
                        
                        # 모든 게시글 처리 완료 후 새로운 게시글 확인
                        # (위의 continue에서 이미 처리됨)
                        
                    except Exception as e:
                        logger.error(f"게시글 처리 오류: {e}", exc_info=True)
                        error_msg = f"오류 발생: {str(e)}"
                        self.root.after(0, partial(self.log, error_msg))
                        time.sleep(10)
                        continue
                
            except Exception as e:
                logger.error(f"좋아요 작업 오류: {e}", exc_info=True)
                error_msg = f"심각한 오류 발생: {str(e)}"
                self.root.after(0, partial(self.log, error_msg))
                retry_count += 1
                if retry_count < max_retries:
                    self.root.after(0, partial(self.log, f"재시도 중... ({retry_count}/{max_retries})"))
                    time.sleep(10)
                else:
                    self.root.after(0, partial(self.log, "최대 재시도 횟수 초과. 좋아요 모드를 중지합니다."))
                    self.root.after(0, self.stop_macro)
                    break
            finally:
                if self.scraper:
                    self.scraper.close()
    
    def _load_liked_posts(self, filename: str) -> set:
        """좋아요를 누른 게시글 목록 로드 (오래된 이력 자동 정리)"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    # 파일 락
                    try:
                        if os.name == 'nt':
                            try:
                                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
                            except NameError:
                                pass
                        else:
                            try:
                                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                            except NameError:
                                pass
                    except:
                        pass
                    
                    data = json.load(f)
                    
                    # 락 해제
                    try:
                        if os.name == 'nt':
                            try:
                                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                            except NameError:
                                pass
                        else:
                            try:
                                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                            except NameError:
                                pass
                    except:
                        pass
                    
                    if isinstance(data, list):
                        post_ids = set(data)
                        last_updated = None
                    elif isinstance(data, dict) and 'post_ids' in data:
                        post_ids = set(data['post_ids'])
                        last_updated = data.get('last_updated')
                    else:
                        post_ids = set()
                        last_updated = None
                    
                    # 파일 크기 관리: 최대 50000개만 유지
                    MAX_POSTS = 50000
                    if len(post_ids) > MAX_POSTS:
                        # 최신 것만 유지 (FIFO 방식)
                        post_ids = set(list(post_ids)[-MAX_POSTS:])
                        logger.info(f"좋아요 이력이 {MAX_POSTS}개를 초과하여 최신 {MAX_POSTS}개만 유지합니다.")
                    
                    # 오래된 이력 자동 정리 (30일 이상 된 이력은 제거)
                    # (실제로는 게시글 ID만 저장하므로 날짜 정보가 없지만,
                    #  파일이 너무 오래되면 정리하는 로직 추가 가능)
                    if last_updated:
                        try:
                            last_update_date = datetime.strptime(last_updated, "%Y-%m-%d %H:%M:%S")
                            days_since_update = (datetime.now() - last_update_date).days
                            if days_since_update > 30 and len(post_ids) > 10000:
                                # 30일 이상 업데이트가 없고 이력이 많으면 일부 정리
                                post_ids = set(list(post_ids)[-10000:])
                                logger.info(f"오래된 좋아요 이력 정리: {days_since_update}일 경과, {len(post_ids)}개만 유지")
                        except:
                            pass
                    
                    return post_ids
            return set()
        except Exception as e:
            logger.warning(f"좋아요 이력 로드 실패: {e}")
            return set()
    
    def _save_liked_posts(self, liked_posts: set, filename: str):
        """좋아요를 누른 게시글 목록 저장"""
        try:
            # 파일 크기 관리: 최대 50000개만 유지
            MAX_POSTS = 50000
            if len(liked_posts) > MAX_POSTS:
                liked_posts = set(list(liked_posts)[-MAX_POSTS:])
                logger.info(f"좋아요 이력이 {MAX_POSTS}개를 초과하여 최신 {MAX_POSTS}개만 유지합니다.")
            
            data = {
                'post_ids': list(liked_posts),
                'count': len(liked_posts),
                'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 임시 파일로 저장 후 원자적 이동
            temp_filename = filename + '.tmp'
            with open(temp_filename, 'w', encoding='utf-8') as f:
                # 파일 락
                try:
                    if os.name == 'nt':
                        try:
                            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
                        except NameError:
                            pass
                    else:
                        try:
                            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                        except NameError:
                            pass
                except:
                    pass
                
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
                
                # 락 해제
                try:
                    if os.name == 'nt':
                        try:
                            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                        except NameError:
                            pass
                    else:
                        try:
                            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                        except NameError:
                            pass
                except:
                    pass
            
            # 원자적 이동
            if os.name == 'nt':
                if os.path.exists(filename):
                    os.replace(temp_filename, filename)
                else:
                    os.rename(temp_filename, filename)
            else:
                os.replace(temp_filename, filename)
                
        except Exception as e:
            logger.error(f"좋아요 이력 저장 실패: {e}")
            # 임시 파일 정리
            try:
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
            except:
                pass

