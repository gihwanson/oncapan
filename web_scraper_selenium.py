"""
Selenium을 사용한 웹 스크래핑 모듈
- Cloudflare 우회를 위해 실제 브라우저 사용
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import time
import random
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OncaPanScraperSelenium:
    def __init__(self, test_mode: bool = False):
        self.base_url = "https://oncapan.com"
        self.login_url = f"{self.base_url}/login"
        self.free_board_url = f"{self.base_url}/bbs/free"
        self.test_mode = test_mode
        
        # Chrome 옵션 설정
        chrome_options = Options()
        # headless 모드 비활성화 (Cloudflare 우회를 위해 필요)
        # chrome_options.add_argument('--headless')  # 필요시 주석 해제
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            # webdriver-manager 사용 시도
            try:
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except ImportError:
                # webdriver-manager가 없으면 일반 방식
                self.driver = webdriver.Chrome(options=chrome_options)
            
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            logger.error(f"Chrome 드라이버 초기화 오류: {e}")
            logger.error("Chrome 브라우저와 ChromeDriver가 설치되어 있는지 확인하세요.")
            logger.error("또는 'py -m pip install webdriver-manager' 실행")
            raise
    
    def login(self, username: str, password: str) -> bool:
        """로그인 시도"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 로그인 페이지 접속
                self.driver.get(self.login_url)
                time.sleep(2)  # 페이지 로딩 대기
                
                # Cloudflare 체크 대기
                if "cloudflare" in self.driver.page_source.lower() or "challenge" in self.driver.page_source.lower():
                    logger.info("Cloudflare 체크 대기 중... (최대 10초)")
                    time.sleep(10)
                
                # 로그인 폼 찾기
                try:
                    # 다양한 선택자로 아이디 필드 찾기
                    username_selectors = [
                        (By.NAME, "mb_id"),
                        (By.ID, "mb_id"),
                        (By.NAME, "user_id"),
                        (By.NAME, "username"),
                        (By.CSS_SELECTOR, "input[type='text']"),
                    ]
                    
                    username_field = None
                    for by, value in username_selectors:
                        try:
                            username_field = self.driver.find_element(by, value)
                            if username_field:
                                break
                        except:
                            continue
                    
                    if not username_field:
                        logger.error("아이디 입력 필드를 찾을 수 없습니다")
                        if attempt < max_retries - 1:
                            time.sleep(2)
                            continue
                        return False
                    
                    # 비밀번호 필드 찾기
                    password_selectors = [
                        (By.NAME, "mb_password"),
                        (By.ID, "mb_password"),
                        (By.NAME, "password"),
                        (By.CSS_SELECTOR, "input[type='password']"),
                    ]
                    
                    password_field = None
                    for by, value in password_selectors:
                        try:
                            password_field = self.driver.find_element(by, value)
                            if password_field:
                                break
                        except:
                            continue
                    
                    if not password_field:
                        logger.error("비밀번호 입력 필드를 찾을 수 없습니다")
                        if attempt < max_retries - 1:
                            time.sleep(2)
                            continue
                        return False
                    
                    # 로그인 정보 입력
                    username_field.clear()
                    username_field.send_keys(username)
                    time.sleep(0.5)
                    
                    password_field.clear()
                    password_field.send_keys(password)
                    time.sleep(0.5)
                    
                    # 로그인 버튼 찾기 및 클릭
                    login_button_selectors = [
                        (By.CSS_SELECTOR, "button[type='submit']"),
                        (By.CSS_SELECTOR, "input[type='submit']"),
                        (By.XPATH, "//button[contains(text(), '로그인')]"),
                        (By.XPATH, "//input[@value='로그인']"),
                    ]
                    
                    login_button = None
                    for by, value in login_button_selectors:
                        try:
                            login_button = self.driver.find_element(by, value)
                            if login_button:
                                break
                        except:
                            continue
                    
                    if login_button:
                        login_button.click()
                    else:
                        # Enter 키로 제출 시도
                        password_field.send_keys("\n")
                    
                    time.sleep(3)  # 로그인 처리 대기
                    
                    # 로그인 성공 여부 확인
                    current_url = self.driver.current_url
                    page_source = self.driver.page_source.lower()
                    
                    if 'login' not in current_url.lower() or '로그아웃' in page_source:
                        logger.info("로그인 성공!")
                        return True
                    elif '실패' in page_source or '오류' in page_source:
                        logger.error("로그인 실패: 잘못된 아이디 또는 비밀번호")
                        if attempt < max_retries - 1:
                            time.sleep(2)
                            continue
                        return False
                    else:
                        logger.warning(f"로그인 상태 불명확 (시도 {attempt + 1}/{max_retries})")
                        if attempt < max_retries - 1:
                            time.sleep(2)
                            continue
                        return False
                        
                except Exception as e:
                    logger.error(f"로그인 폼 처리 오류: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    return False
                    
            except Exception as e:
                logger.error(f"로그인 오류 (시도 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return False
        
        return False
    
    def get_post_list(self, limit: int = 20) -> List[Dict]:
        """게시글 목록 가져오기"""
        try:
            self.driver.get(self.free_board_url)
            time.sleep(2)
            
            # 페이지 소스 가져오기
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            posts = []
            seen_ids = set()
            
            # 게시글 링크 찾기
            links = soup.find_all('a', href=True)
            for link in links:
                if len(posts) >= limit:
                    break
                
                href = link.get('href', '')
                title = link.get_text(strip=True)
                
                if title and len(title) > 5:
                    if '/bbs/free' in href or 'wr_id=' in href or 'board.php' in href:
                        post_id = self._extract_post_id(href)
                        if post_id and post_id not in seen_ids:
                            seen_ids.add(post_id)
                            full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                            posts.append({
                                'id': post_id,
                                'title': title,
                                'url': full_url,
                            })
            
            logger.info(f"게시글 {len(posts)}개 가져옴")
            return posts
            
        except Exception as e:
            logger.error(f"게시글 목록 가져오기 오류: {e}")
            return []
    
    def _extract_post_id(self, url: str) -> Optional[str]:
        """URL에서 게시글 ID 추출"""
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            
            if 'wr_id' in query_params:
                return query_params['wr_id'][0]
            
            path_parts = parsed.path.strip('/').split('/')
            if 'free' in path_parts:
                for i, part in enumerate(path_parts):
                    if part == 'free' and i + 1 < len(path_parts):
                        return path_parts[i + 1].split('?')[0]
            
            if 'wr_id=' in url:
                return url.split('wr_id=')[1].split('&')[0].split('#')[0]
            
            return None
        except:
            return None
    
    def get_post_content(self, post_url: str) -> Optional[Dict]:
        """게시글 내용 가져오기"""
        try:
            self.driver.get(post_url)
            time.sleep(1)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 게시글 내용 추출
            content = None
            content_selectors = [
                ('div', {'id': 'bo_v_con'}),
                ('div', {'class': 'content'}),
                ('div', {'id': 'content'}),
            ]
            
            for tag, attrs in content_selectors:
                content = soup.find(tag, attrs) if attrs else soup.find(tag)
                if content:
                    break
            
            content_text = content.get_text(strip=True) if content else ""
            
            return {
                'content': content_text,
                'title': '',
                'soup': soup
            }
            
        except Exception as e:
            logger.error(f"게시글 내용 가져오기 오류: {e}")
            return None
    
    def has_commented(self, post_url: str, username: str) -> bool:
        """이미 댓글을 달았는지 확인"""
        try:
            self.driver.get(post_url)
            time.sleep(1)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            page_text = soup.get_text()
            
            # 댓글 영역에서 사용자명 찾기
            if username in page_text:
                # 댓글 작성자 영역 확인
                comments = soup.find_all(['div', 'li'], class_=lambda x: x and 'comment' in x.lower())
                for comment in comments:
                    if username in comment.get_text():
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"댓글 확인 오류: {e}")
            return False
    
    def write_comment(self, post_url: str, comment: str) -> bool:
        """댓글 작성"""
        if self.test_mode:
            logger.info(f"[테스트 모드] 댓글 작성 시뮬레이션: {post_url}")
            logger.info(f"[테스트 모드] 댓글 내용: {comment}")
            return True
        
        try:
            self.driver.get(post_url)
            time.sleep(1)
            
            # 댓글 입력 필드 찾기
            comment_selectors = [
                (By.NAME, "wr_content"),
                (By.ID, "wr_content"),
                (By.CSS_SELECTOR, "textarea[name*='content']"),
                (By.CSS_SELECTOR, "textarea"),
            ]
            
            comment_field = None
            for by, value in comment_selectors:
                try:
                    comment_field = self.driver.find_element(by, value)
                    if comment_field:
                        break
                except:
                    continue
            
            if not comment_field:
                logger.error("댓글 입력 필드를 찾을 수 없습니다")
                return False
            
            # 댓글 입력
            comment_field.clear()
            comment_field.send_keys(comment)
            time.sleep(0.5)
            
            # 댓글 작성 버튼 찾기 및 클릭
            submit_selectors = [
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.XPATH, "//button[contains(text(), '등록')]"),
                (By.XPATH, "//button[contains(text(), '작성')]"),
            ]
            
            submit_button = None
            for by, value in submit_selectors:
                try:
                    submit_button = self.driver.find_element(by, value)
                    if submit_button:
                        break
                except:
                    continue
            
            if submit_button:
                submit_button.click()
            else:
                # Enter 키로 제출 시도
                comment_field.send_keys("\n")
            
            time.sleep(2)
            
            # 성공 여부 확인
            page_source = self.driver.page_source.lower()
            if '성공' in page_source or '등록' in page_source:
                logger.info("댓글 작성 완료")
                return True
            else:
                logger.warning("댓글 작성 상태 불명확")
                return True  # 일단 성공으로 간주
            
        except Exception as e:
            logger.error(f"댓글 작성 오류: {e}")
            return False
    
    def close(self):
        """브라우저 종료"""
        if hasattr(self, 'driver'):
            self.driver.quit()

