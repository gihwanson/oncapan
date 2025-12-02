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
from datetime import datetime, timedelta
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
                time.sleep(1)  # 페이지 로딩 대기 시간 줄임
                
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
                    time.sleep(0.2)  # 대기 시간 줄임
                    
                    password_field.clear()
                    password_field.send_keys(password)
                    time.sleep(0.2)  # 대기 시간 줄임
                    
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
                    
                    time.sleep(1.5)  # 로그인 처리 대기 시간 줄임
                    
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
        """게시글 목록 가져오기 (24시간 이내 게시글만, 여러 페이지 탐색)"""
        try:
            import re
            
            posts = []
            seen_ids = set()
            now = datetime.now()
            max_pages = 50  # 최대 탐색 페이지 수 (무한 루프 방지)
            page = 1
            found_old_post = False  # 24시간 초과 게시글 발견 여부
            
            while page <= max_pages and not found_old_post:
                # 페이지 URL 구성
                if page == 1:
                    page_url = self.free_board_url
                    # 첫 페이지는 현재 URL 확인 후 필요시에만 이동
                    current_url = self.driver.current_url
                    if self.free_board_url not in current_url:
                        self.driver.get(page_url)
                        time.sleep(0.5)
                else:
                    # 페이지네이션 링크 찾기 (이전 페이지의 soup 사용)
                    try:
                        # 다양한 페이지네이션 패턴 시도
                        next_page_link = None
                        
                        # 방법 1: 페이지 번호 링크 찾기
                        if 'soup' in locals():
                            page_links = soup.find_all('a', href=True)
                            for link in page_links:
                                link_text = link.get_text(strip=True)
                                href = link.get('href', '')
                                # 페이지 번호와 일치하는 링크 찾기
                                if link_text == str(page) or (f'page={page}' in href or f'/page/{page}' in href or f'/{page}' in href):
                                    next_page_link = href
                                    break
                            
                            # 방법 2: 다음 페이지 버튼 찾기
                            if not next_page_link:
                                next_buttons = soup.find_all('a', string=lambda x: x and ('다음' in str(x) or '>' in str(x) or 'next' in str(x).lower()))
                                if next_buttons:
                                    next_page_link = next_buttons[0].get('href', '')
                        
                        # 방법 3: URL 파라미터로 직접 구성
                        if not next_page_link:
                            if '?' in self.free_board_url:
                                page_url = f"{self.free_board_url}&page={page}"
                            else:
                                page_url = f"{self.free_board_url}?page={page}"
                        else:
                            page_url = next_page_link if next_page_link.startswith('http') else f"{self.base_url}{next_page_link}"
                    except Exception as e:
                        logger.debug(f"페이지 {page} URL 구성 실패: {e}")
                        # 기본 URL 파라미터 방식 사용
                        if '?' in self.free_board_url:
                            page_url = f"{self.free_board_url}&page={page}"
                        else:
                            page_url = f"{self.free_board_url}?page={page}"
                
                try:
                    self.driver.get(page_url)
                    time.sleep(0.5)  # 페이지 로딩 대기
                    
                    # 페이지 소스 가져오기
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    
                    # 테이블에서 게시글 행 찾기
                    table = soup.find('table')
                    if not table:
                        # 테이블이 없으면 더 이상 페이지가 없는 것으로 간주
                        break
                    
                    rows = table.find_all('tr')
                    page_has_valid_posts = False
                    
                    for row in rows:
                        # 공지사항 건너뛰기
                        if 'bo_notice' in row.get('class', []):
                            continue
                        
                        # 게시글 링크 찾기
                        link = row.find('a', href=True)
                        if not link:
                            continue
                        
                        href = link.get('href', '')
                        title = link.get_text(strip=True)
                        
                        # 날짜 정보 추출
                        datetime_cell = row.find('td', class_='td_datetime')
                        post_datetime_str = datetime_cell.get_text(strip=True) if datetime_cell else None
                        
                        # 24시간 이내 게시글인지 확인
                        is_within_24h = False
                        parsed_dt = None
                        
                        if post_datetime_str:
                            parsed_dt = self._parse_datetime(post_datetime_str, now)
                            if parsed_dt:
                                time_diff = now - parsed_dt
                                if time_diff <= timedelta(hours=24):
                                    is_within_24h = True
                                else:
                                    # 24시간 초과 게시글 발견
                                    # 이 페이지 이후는 더 오래된 게시글만 있으므로 탐색 중단
                                    found_old_post = True
                        
                        if title and len(title) > 5:
                            if '/bbs/free' in href or 'wr_id=' in href or 'board.php' in href:
                                post_id = self._extract_post_id(href)
                                if post_id and post_id not in seen_ids:
                                    seen_ids.add(post_id)
                                    full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                                    
                                    # 24시간 이내 게시글만 추가
                                    if is_within_24h or (not post_datetime_str and page == 1):
                                        # 날짜가 없는 경우 첫 페이지에서만 추가 (안전장치)
                                        posts.append({
                                            'id': post_id,
                                            'title': title,
                                            'url': full_url,
                                            'datetime': post_datetime_str,
                                            'datetime_obj': parsed_dt,  # 정렬용
                                        })
                                        page_has_valid_posts = True
                    
                    # 이 페이지에서 유효한 게시글이 없고, 24시간 초과 게시글을 발견했다면 탐색 중단
                    if not page_has_valid_posts and found_old_post:
                        break
                    
                    # 이 페이지에서 게시글을 찾지 못했다면 더 이상 페이지가 없는 것으로 간주
                    if not page_has_valid_posts and page > 1:
                        break
                    
                    page += 1
                    
                except Exception as e:
                    logger.debug(f"페이지 {page} 탐색 오류: {e}")
                    break
            
            # 날짜순으로 정렬 (오래된 것부터 = 역순)
            # datetime_obj가 None이 아닌 것만 정렬하고, None인 것은 뒤로
            posts_with_date = [p for p in posts if p.get('datetime_obj')]
            posts_without_date = [p for p in posts if not p.get('datetime_obj')]
            
            # datetime 기준 오름차순 정렬 (오래된 것부터)
            posts_with_date.sort(key=lambda x: x.get('datetime_obj') or datetime.min)
            
            # 최종: 오래된 것부터 먼저, 날짜 없는 것은 뒤로
            sorted_posts = posts_with_date + posts_without_date
            
            logger.info(f"게시글 {len(sorted_posts)}개 가져옴 (24시간 이내만, {page-1}페이지 탐색, 오래된 것부터)")
            return sorted_posts
            
        except Exception as e:
            logger.error(f"게시글 목록 가져오기 오류: {e}")
            return []
    
    def _parse_datetime(self, datetime_str: str, now: datetime) -> Optional[datetime]:
        """날짜 문자열을 datetime 객체로 변환 (24시간 이내 확인용)"""
        try:
            import re
            
            datetime_str = datetime_str.strip()
            
            # "HH:MM" 형식 (오늘)
            time_match = re.match(r'(\d{1,2}):(\d{2})', datetime_str)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                post_datetime = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                # 오늘이 아니면 어제로 간주
                if post_datetime > now:
                    post_datetime = post_datetime - timedelta(days=1)
                return post_datetime
            
            # "MM-DD" 형식 (올해)
            date_match = re.match(r'(\d{1,2})-(\d{1,2})', datetime_str)
            if date_match:
                month = int(date_match.group(1))
                day = int(date_match.group(2))
                post_datetime = now.replace(month=month, day=day, hour=0, minute=0, second=0, microsecond=0)
                # 미래 날짜면 작년으로 간주
                if post_datetime > now:
                    post_datetime = post_datetime.replace(year=now.year - 1)
                return post_datetime
            
            return None
        except Exception as e:
            logger.debug(f"날짜 파싱 오류: {datetime_str}, {e}")
            return None
    
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
            # 현재 URL 확인 - 이미 해당 게시글 페이지에 있으면 새로고침 안 함
            current_url = self.driver.current_url
            if post_url not in current_url and current_url not in post_url:
                self.driver.get(post_url)
                time.sleep(0.5)  # 대기 시간 줄임
            else:
                time.sleep(0.2)  # 이미 해당 페이지에 있으면 짧은 대기만
            
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
            
            # 게시글 제목 추출
            title = None
            title_selectors = [
                ('h2', {'id': 'bo_v_title'}),
                ('span', {'class': 'bo_v_tit'}),
                ('h1', {}),
                ('h2', {}),
                ('div', {'id': 'bo_v_title'}),
                ('div', {'class': 'title'}),
            ]
            
            for tag, attrs in title_selectors:
                title_elem = soup.find(tag, attrs) if attrs else soup.find(tag)
                if title_elem:
                    # span.bo_v_tit이 h2 안에 있을 수 있으므로 확인
                    if tag == 'h2' and attrs.get('id') == 'bo_v_title':
                        span = title_elem.find('span', class_='bo_v_tit')
                        if span:
                            title = span.get_text(strip=True)
                        else:
                            title = title_elem.get_text(strip=True)
                    else:
                        title = title_elem.get_text(strip=True)
                    if title:
                        break
            
            # 제목을 찾지 못한 경우 title 태그에서 추출 시도
            if not title:
                title_tag = soup.find('title')
                if title_tag:
                    title_text = title_tag.get_text(strip=True)
                    # "제목 > 온카판 > ..." 형태에서 제목 부분만 추출
                    if '>' in title_text:
                        title = title_text.split('>')[0].strip()
                    else:
                        title = title_text
            
            return {
                'content': content_text,
                'title': title or '',
                'soup': soup
            }
            
        except Exception as e:
            logger.error(f"게시글 내용 가져오기 오류: {e}")
            return None
    
    def has_commented(self, post_url: str, username: str) -> bool:
        """이미 댓글을 달았는지 확인"""
        try:
            # 현재 URL 확인 - 이미 해당 게시글 페이지에 있으면 새로고침 안 함
            current_url = self.driver.current_url
            if post_url not in current_url and current_url not in post_url:
                self.driver.get(post_url)
                time.sleep(0.5)  # 대기 시간 줄임
            else:
                time.sleep(0.2)  # 이미 해당 페이지에 있으면 짧은 대기만
            
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
            # 현재 URL 확인 - 이미 해당 게시글 페이지에 있으면 새로고침 안 함
            current_url = self.driver.current_url
            if post_url not in current_url and current_url not in post_url:
                self.driver.get(post_url)
                time.sleep(0.5)  # 대기 시간 줄임
            else:
                time.sleep(0.2)  # 이미 해당 페이지에 있으면 짧은 대기만
            
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
            time.sleep(0.1)
            
            # 댓글 내용이 너무 짧으면 경고
            if len(comment.strip()) < 2:
                logger.error(f"댓글이 너무 짧습니다: '{comment}' (최소 2글자 필요)")
                return False
            
            # 댓글 입력 (한 글자씩 천천히 입력하여 검증 우회)
            comment_field.send_keys(comment)
            time.sleep(0.3)  # 입력 완료 대기
            
            # 입력된 내용 확인
            entered_text = comment_field.get_attribute('value')
            if not entered_text or len(entered_text.strip()) < 2:
                logger.error(f"댓글 입력 실패: 입력된 내용이 없거나 너무 짧습니다. (원본: '{comment}')")
                return False
            
            logger.debug(f"댓글 입력 확인: '{entered_text[:30]}...'")
            
            # 댓글 작성 버튼 찾기 및 클릭 (댓글 폼 내부의 버튼만 찾기)
            submit_button = None
            
            # 댓글 폼 내부에서 버튼 찾기
            try:
                # 댓글 입력 필드의 부모 폼 찾기
                comment_form = comment_field.find_element(By.XPATH, "./ancestor::form")
                
                # 폼 내부의 submit 버튼 찾기 (검색 버튼 제외)
                submit_selectors = [
                    (By.CSS_SELECTOR, "button[type='submit']:not([name*='search']):not([id*='search'])"),
                    (By.CSS_SELECTOR, "input[type='submit']:not([name*='search']):not([id*='search'])"),
                    (By.XPATH, ".//button[contains(text(), '등록')]"),
                    (By.XPATH, ".//button[contains(text(), '작성')]"),
                    (By.XPATH, ".//button[contains(text(), '댓글')]"),
                ]
                
                for by, value in submit_selectors:
                    try:
                        submit_button = comment_form.find_element(by, value)
                        if submit_button:
                            logger.debug(f"댓글 작성 버튼 발견: {submit_button.get_attribute('outerHTML')[:100]}")
                            break
                    except:
                        continue
            except:
                pass
            
            # 폼 내부에서 못 찾으면 전체 페이지에서 찾기 (검색 버튼 제외)
            if not submit_button:
                submit_selectors = [
                    (By.CSS_SELECTOR, "button[type='submit']:not([name*='search']):not([id*='search']):not([class*='search'])"),
                    (By.CSS_SELECTOR, "input[type='submit']:not([name*='search']):not([id*='search']):not([class*='search'])"),
                    (By.XPATH, "//button[contains(text(), '등록') and not(contains(@name, 'search'))]"),
                    (By.XPATH, "//button[contains(text(), '작성') and not(contains(@name, 'search'))]"),
                ]
                
                for by, value in submit_selectors:
                    try:
                        submit_button = self.driver.find_element(by, value)
                        if submit_button:
                            logger.debug(f"댓글 작성 버튼 발견 (전체 페이지): {submit_button.get_attribute('outerHTML')[:100]}")
                            break
                    except:
                        continue
            
            if submit_button:
                submit_button.click()
                logger.debug("댓글 작성 버튼 클릭 완료")
            else:
                # Enter 키로 제출 시도
                logger.debug("댓글 작성 버튼을 찾지 못해 Enter 키로 시도")
                comment_field.send_keys("\n")
            
            time.sleep(1)  # 대기 시간 줄임
            
            # 알림(alert) 처리
            try:
                from selenium.common.exceptions import UnexpectedAlertPresentException
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                logger.warning(f"알림 발생: {alert_text}")
                
                # 알림 닫기
                alert.accept()
                
                # 알림 메시지에 따라 실패 처리
                if '검색어는 두글자 이상' in alert_text or '두글자 이상' in alert_text:
                    logger.error(f"댓글 작성 실패: 댓글이 너무 짧습니다. (댓글: '{comment}')")
                    return False
                elif '금지' in alert_text or '차단' in alert_text or '불가' in alert_text:
                    logger.error(f"댓글 작성 실패: {alert_text}")
                    return False
                else:
                    # 다른 알림은 무시하고 계속 진행
                    logger.info(f"알림 처리 완료: {alert_text}")
            except:
                # 알림이 없으면 정상 진행
                pass
            
            # 성공 여부 확인
            page_source = self.driver.page_source.lower()
            if '성공' in page_source or '등록' in page_source:
                logger.info("댓글 작성 완료")
                return True
            else:
                logger.warning("댓글 작성 상태 불명확")
                return True  # 일단 성공으로 간주
            
        except Exception as e:
            # 알림 관련 예외 처리
            error_msg = str(e)
            if 'unexpected alert' in error_msg.lower() or 'alert' in error_msg.lower():
                try:
                    alert = self.driver.switch_to.alert
                    alert_text = alert.text
                    logger.error(f"댓글 작성 중 알림 발생: {alert_text}")
                    alert.accept()
                    
                    if '검색어는 두글자 이상' in alert_text or '두글자 이상' in alert_text:
                        logger.error(f"댓글 작성 실패: 댓글이 너무 짧습니다. (댓글: '{comment}')")
                    return False
                except:
                    pass
            
            logger.error(f"댓글 작성 오류: {e}")
            return False
    
    def close(self):
        """브라우저 종료"""
        if hasattr(self, 'driver'):
            self.driver.quit()

