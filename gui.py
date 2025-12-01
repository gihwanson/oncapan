"""
GUI 인터페이스 모듈
- tkinter 기반 사용자 인터페이스
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
from functools import partial
from config_manager import ConfigManager
from web_scraper import OncaPanScraper
from ai_comment_generator import AICommentGenerator
import time
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MacroGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("온카판 자동 댓글 매크로")
        self.root.geometry("600x700")
        self.root.resizable(False, False)
        
        self.config_manager = ConfigManager()
        self.scraper = None
        self.ai_generator = None
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
        self.min_delay_entry = ttk.Entry(delay_frame, width=10)
        self.min_delay_entry.insert(0, "5")
        self.min_delay_entry.grid(row=1, column=1, pady=2, padx=5, sticky=tk.W)
        
        ttk.Label(delay_frame, text="최대 대기 시간 (초):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.max_delay_entry = ttk.Entry(delay_frame, width=10)
        self.max_delay_entry.insert(0, "15")
        self.max_delay_entry.grid(row=2, column=1, pady=2, padx=5, sticky=tk.W)
        
        # 테스트 모드 체크박스
        test_frame = ttk.Frame(main_frame)
        test_frame.grid(row=3, column=0, columnspan=2, pady=5)
        
        self.test_mode_var = tk.BooleanVar(value=False)
        test_check = ttk.Checkbutton(test_frame, text="테스트 모드 (실제 댓글 작성 안 함)", variable=self.test_mode_var)
        test_check.pack()
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        self.save_btn = ttk.Button(button_frame, text="설정 저장", command=self.save_config)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        self.start_btn = ttk.Button(button_frame, text="시작", command=self.start_macro, state=tk.NORMAL)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="중지", command=self.stop_macro, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 로그 영역
        log_frame = ttk.LabelFrame(main_frame, text="실행 로그", padding="10")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=70, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 상태바
        self.status_label = ttk.Label(main_frame, text="대기 중...", relief=tk.SUNKEN)
        self.status_label.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 그리드 가중치 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
    
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
            self.min_delay_entry.delete(0, tk.END)
            self.min_delay_entry.insert(0, str(config.get('min_delay', 5)))
            self.max_delay_entry.delete(0, tk.END)
            self.max_delay_entry.insert(0, str(config.get('max_delay', 15)))
            self.log("저장된 설정을 불러왔습니다.")
    
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
            min_delay = int(self.min_delay_entry.get())
            max_delay = int(self.max_delay_entry.get())
            
            if min_delay >= max_delay:
                messagebox.showwarning("경고", "최소 대기 시간은 최대 대기 시간보다 작아야 합니다.")
                return
            
        except ValueError:
            messagebox.showerror("오류", "대기 시간은 숫자로 입력해주세요.")
            return
        
        self.config_manager.save_config(username, password, api_key, delay, min_delay, max_delay)
        messagebox.showinfo("성공", "설정이 저장되었습니다.")
        self.log("설정이 저장되었습니다.")
    
    def start_macro(self):
        """매크로 시작"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        api_key = self.api_key_entry.get().strip()
        
        if not username or not password or not api_key:
            messagebox.showwarning("경고", "모든 필드를 입력해주세요.")
            return
        
        try:
            delay = int(self.delay_entry.get())
            min_delay = int(self.min_delay_entry.get())
            max_delay = int(self.max_delay_entry.get())
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
        self.min_delay_entry.config(state=tk.DISABLED)
        self.max_delay_entry.config(state=tk.DISABLED)
        
        # 워커 스레드 시작
        self.worker_thread = threading.Thread(
            target=self.macro_worker,
            args=(username, password, api_key, delay, min_delay, max_delay),
            daemon=True
        )
        self.worker_thread.start()
        
        self.log("매크로를 시작합니다...")
        self.status_label.config(text="실행 중...")
    
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
        self.min_delay_entry.config(state=tk.NORMAL)
        self.max_delay_entry.config(state=tk.NORMAL)
        
        if self.scraper:
            self.scraper.close()
        
        self.log("매크로를 중지합니다...")
        self.status_label.config(text="중지됨")
    
    def macro_worker(self, username: str, password: str, api_key: str, 
                    delay: int, min_delay: int, max_delay: int):
        """매크로 작업 스레드"""
        max_retries = 3
        retry_count = 0
        
        while self.is_running and retry_count < max_retries:
            try:
                # 스크래퍼 및 AI 생성기 초기화
                test_mode = self.test_mode_var.get()
                self.scraper = OncaPanScraper(test_mode=test_mode)
                self.ai_generator = AICommentGenerator(api_key)
                
                if test_mode:
                    self.root.after(0, partial(self.log, "⚠️ 테스트 모드로 실행됩니다. 실제 댓글은 작성되지 않습니다."))
                
                # 로그인 시도
                self.root.after(0, lambda: self.log("로그인 시도 중..."))
                if not self.scraper.login(username, password):
                    retry_count += 1
                    if retry_count < max_retries:
                        self.root.after(0, lambda: self.log(f"로그인 실패. 재시도 중... ({retry_count}/{max_retries})"))
                        time.sleep(5)
                        continue
                    else:
                        self.root.after(0, lambda: self.log("로그인 실패. 매크로를 중지합니다."))
                        self.root.after(0, self.stop_macro)
                        return
                
                self.root.after(0, lambda: self.log("로그인 성공!"))
                retry_count = 0  # 로그인 성공 시 재시도 카운트 리셋
                
                # 이미 댓글 단 게시글 추적
                commented_posts = set()
                
                # 메인 루프
                while self.is_running:
                    try:
                        # 게시글 목록 가져오기
                        self.root.after(0, lambda: self.log("게시글 목록을 가져오는 중..."))
                        posts = self.scraper.get_post_list(limit=20)
                        
                        if not posts:
                            self.root.after(0, lambda: self.log("게시글을 찾을 수 없습니다. 잠시 후 재시도..."))
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
                                post_title = post.get('title', '')[:30]
                                self.root.after(0, partial(self.log, f"이미 댓글을 단 게시글: {post_title}"))
                                continue
                            
                            # 게시글 내용 가져오기
                            post_title = post.get('title', '')[:30]
                            self.root.after(0, partial(self.log, f"게시글 처리 중: {post_title}"))
                            post_data = self.scraper.get_post_content(post_url)
                            
                            if not post_data:
                                continue
                            
                            post_content = post_data.get('content', '')
                            
                            # 댓글 생성 가능 여부 확인
                            if not self.ai_generator.can_generate_comment(post_content):
                                self.root.after(0, lambda: self.log("댓글 생성 불가능한 게시글입니다. 건너뜁니다."))
                                continue
                            
                            # 설정된 대기 시간
                            wait_time = random.uniform(min_delay, max_delay)
                            self.root.after(0, partial(self.log, f"{wait_time:.1f}초 대기 중..."))
                            time.sleep(wait_time)
                            
                            # AI 댓글 생성
                            self.root.after(0, partial(self.log, "AI 댓글 생성 중..."))
                            comment = self.ai_generator.generate_comment(post_content, post.get('title', ''))
                            
                            if not comment:
                                self.root.after(0, partial(self.log, "댓글 생성 실패. 건너뜁니다."))
                                continue
                            
                            # 댓글 작성
                            comment_preview = comment[:30]
                            self.root.after(0, partial(self.log, f"댓글 작성 중: {comment_preview}..."))
                            if self.scraper.write_comment(post_url, comment):
                                commented_posts.add(post_id)
                                self.root.after(0, partial(self.log, "댓글 작성 완료!"))
                                status_text = f"댓글 작성 완료: {len(commented_posts)}개"
                                self.root.after(0, partial(self.status_label.config, text=status_text))
                            else:
                                self.root.after(0, partial(self.log, "댓글 작성 실패."))
                            
                            # 게시글 간 대기 시간
                            time.sleep(delay)
                        
                        # 게시글 목록 새로고침 대기
                        self.root.after(0, lambda: self.log("다음 게시글 목록을 기다리는 중..."))
                        time.sleep(60)  # 1분마다 게시글 목록 새로고침
                        
                    except Exception as e:
                        logger.error(f"게시글 처리 오류: {e}", exc_info=True)
                        error_msg = f"오류 발생: {str(e)}"
                        self.root.after(0, partial(self.log, error_msg))
                        time.sleep(10)
                        continue
                
            except Exception as e:
                logger.error(f"매크로 작업 오류: {e}", exc_info=True)
                error_msg = f"심각한 오류 발생: {str(e)}"
                self.root.after(0, partial(self.log, error_msg))
                retry_count += 1
                if retry_count < max_retries:
                    self.root.after(0, lambda: self.log(f"재시도 중... ({retry_count}/{max_retries})"))
                    time.sleep(10)
                else:
                    self.root.after(0, lambda: self.log("최대 재시도 횟수 초과. 매크로를 중지합니다."))
                    self.root.after(0, self.stop_macro)
                    break
            finally:
                if self.scraper:
                    self.scraper.close()

