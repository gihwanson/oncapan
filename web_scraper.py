"""
웹 스크래핑 모듈
- 온카판 로그인
- 게시글 목록 가져오기
- 댓글 작성
"""

import requests
from bs4 import BeautifulSoup
import time
import random
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# 디버깅을 위해 DEBUG 레벨로 변경 가능
# logger.setLevel(logging.DEBUG)

class OncaPanScraper:
    def __init__(self, test_mode: bool = False):
        self.session = requests.Session()
        self.base_url = "https://oncapan.com"
        self.login_url = f"{self.base_url}/login"
        self.free_board_url = f"{self.base_url}/bbs/free"
        self.new_post_url = f"{self.base_url}/new.php"
        self.test_mode = test_mode  # 테스트 모드: 실제 댓글 작성 안 함
        
        # User-Agent 및 헤더 설정 (자연스러운 브라우저처럼 보이게)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })
    
    def login(self, username: str, password: str) -> bool:
        """로그인 시도"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 먼저 메인 페이지 접속하여 세션 생성
                try:
                    main_response = self.session.get(self.base_url, timeout=10)
                    time.sleep(1)  # 자연스러운 딜레이
                except:
                    pass
                
                # 로그인 페이지 접속하여 CSRF 토큰 등 가져오기
                response = self.session.get(
                    self.login_url, 
                    timeout=10,
                    headers={
                        'Referer': self.base_url,
                    }
                )
                
                # 403 오류 처리
                if response.status_code == 403:
                    logger.warning(f"403 오류 발생 (시도 {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(3)
                        # User-Agent를 약간 변경
                        self.session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
                        continue
                    else:
                        logger.error("403 오류: 서버가 요청을 차단했습니다. 잠시 후 다시 시도하세요.")
                        return False
                
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 로그인 폼 찾기
                form = soup.find('form')
                if not form:
                    logger.error("로그인 폼을 찾을 수 없습니다")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    return False
                
                # 폼 action URL 확인
                form_action = form.get('action', '')
                if form_action:
                    if not form_action.startswith('http'):
                        form_action = f"{self.base_url}{form_action}"
                else:
                    form_action = self.login_url
                
                # 로그인 데이터 준비
                login_data = {}
                
                # 모든 input 필드 수집
                inputs = form.find_all('input')
                username_field = None
                password_field = None
                
                for inp in inputs:
                    name = inp.get('name')
                    input_type = inp.get('type', 'text')
                    input_id = inp.get('id', '')
                    value = inp.get('value', '')
                    
                    if input_type == 'hidden':
                        # 숨겨진 필드는 모두 포함
                        if name:
                            login_data[name] = value
                    elif input_type == 'text' or input_type == '':
                        # 텍스트 입력 필드 - 아이디 필드 찾기
                        if not username_field:
                            if 'id' in name.lower() if name else False or 'user' in name.lower() if name else False:
                                username_field = name
                            elif 'id' in input_id.lower() or 'user' in input_id.lower():
                                username_field = name if name else input_id
                    elif input_type == 'password':
                        # 비밀번호 필드
                        if not password_field:
                            password_field = name
                
                # 필드명이 없으면 일반적인 그누보드 필드명 사용
                if not username_field:
                    # 가능한 필드명들 시도
                    possible_username_fields = ['mb_id', 'user_id', 'username', 'user', 'login_id']
                    for field in possible_username_fields:
                        if any(field in inp.get('name', '').lower() or field in inp.get('id', '').lower() 
                               for inp in inputs if inp.get('type') in ['text', '']):
                            username_field = field
                            break
                    if not username_field:
                        username_field = 'mb_id'  # 기본값
                
                if not password_field:
                    possible_password_fields = ['mb_password', 'password', 'pass', 'pwd']
                    for field in possible_password_fields:
                        if any(field in inp.get('name', '').lower() or field in inp.get('id', '').lower() 
                               for inp in inputs if inp.get('type') == 'password'):
                            password_field = field
                            break
                    if not password_field:
                        password_field = 'mb_password'  # 기본값
                
                # 로그인 데이터 설정
                login_data[username_field] = username
                login_data[password_field] = password
                
                # 모든 hidden 필드 추가
                for inp in inputs:
                    if inp.get('type') == 'hidden':
                        name = inp.get('name')
                        value = inp.get('value', '')
                        if name and name not in login_data:
                            login_data[name] = value
                
                logger.debug(f"로그인 필드: {username_field}={username}, {password_field}=***")
                logger.debug(f"전체 로그인 데이터 키: {list(login_data.keys())}")
                
                # Referer 헤더 추가 (일부 사이트에서 필요)
                headers = {
                    'Referer': self.login_url,
                    'Origin': self.base_url,
                }
                
                # 로그인 POST 요청
                response = self.session.post(
                    form_action, 
                    data=login_data, 
                    headers=headers,
                    timeout=10, 
                    allow_redirects=True
                )
                response.raise_for_status()
                
                # 응답 내용 일부 저장 (디버깅용)
                if attempt == 0:  # 첫 시도만
                    logger.debug(f"로그인 응답 URL: {response.url}")
                    logger.debug(f"로그인 응답 상태: {response.status_code}")
                
                # 로그인 성공 여부 확인
                # 1. 쿠키 확인
                cookies = self.session.cookies
                cookie_names = [cookie.name for cookie in cookies]
                if any('mb' in name.lower() or 'session' in name.lower() or 'login' in name.lower() 
                       for name in cookie_names):
                    logger.info("로그인 성공 (쿠키 확인)")
                    return True
                
                # 2. 리다이렉트 확인
                final_url = response.url
                if final_url != self.login_url and 'login' not in final_url.lower():
                    logger.info(f"로그인 성공 (리다이렉트 확인: {final_url})")
                    return True
                
                # 3. 응답 내용 확인 (로그인 실패 메시지 체크)
                response_text = response.text.lower()
                if any(keyword in response_text for keyword in ['로그인 실패', '아이디가', '비밀번호가', '일치하지', '오류']):
                    logger.error("로그인 실패: 잘못된 아이디 또는 비밀번호")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    return False
                
                # 4. 성공 메시지 확인
                if any(keyword in response_text for keyword in ['로그인 성공', '환영합니다', '로그아웃']):
                    logger.info("로그인 성공 (응답 내용 확인)")
                    return True
                
                # 5. 메인 페이지로 이동 시도하여 확인
                try:
                    test_response = self.session.get(self.base_url, timeout=10)
                    test_text = test_response.text.lower()
                    if any(keyword in test_text for keyword in ['로그아웃', '마이페이지', username.lower()]):
                        logger.info("로그인 성공 (메인 페이지 확인)")
                        return True
                except:
                    pass
                
                logger.warning(f"로그인 상태 불명확 (시도 {attempt + 1}/{max_retries})")
                logger.debug(f"응답 URL: {response.url}")
                logger.debug(f"쿠키: {cookie_names}")
                
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return False
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"로그인 오류 (시도 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return False
        
        return False
    
    def get_post_list(self, limit: int = 20) -> List[Dict]:
        """게시글 목록 가져오기"""
        try:
            response = self.session.get(self.free_board_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            posts = []
            seen_ids = set()  # 중복 제거용
            
            # 방법 1: 테이블에서 게시글 찾기 (일반적인 게시판 구조)
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    links = row.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        title = link.get_text(strip=True)
                        
                        # 게시글 링크인지 확인
                        if title and len(title) > 5:  # 의미있는 제목만
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
                                    if len(posts) >= limit:
                                        break
                    if len(posts) >= limit:
                        break
                if len(posts) >= limit:
                    break
            
            # 방법 2: 테이블에서 찾지 못한 경우 모든 링크에서 찾기
            if len(posts) < limit:
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    if len(posts) >= limit:
                        break
                    
                    href = link.get('href', '')
                    title = link.get_text(strip=True)
                    
                    # 게시글 링크 패턴 확인
                    if title and len(title) > 5:
                        if '/bbs/free' in href or 'wr_id=' in href or ('board.php' in href and 'bo_table=free' in href):
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
            
        except requests.exceptions.RequestException as e:
            logger.error(f"게시글 목록 가져오기 오류: {e}")
            return []
    
    def _extract_post_id(self, url: str) -> Optional[str]:
        """URL에서 게시글 ID 추출"""
        try:
            # URL 파싱
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            
            # wr_id 파라미터 확인
            if 'wr_id' in query_params:
                return query_params['wr_id'][0]
            
            # URL 경로에서 추출
            path_parts = parsed.path.strip('/').split('/')
            if 'bbs' in path_parts or 'free' in path_parts:
                # /bbs/free/123 형식
                for i, part in enumerate(path_parts):
                    if part == 'free' and i + 1 < len(path_parts):
                        return path_parts[i + 1].split('?')[0]
                    elif part.isdigit():
                        return part
            
            # 직접 wr_id= 찾기
            if 'wr_id=' in url:
                return url.split('wr_id=')[1].split('&')[0].split('#')[0]
            
            return None
        except Exception as e:
            logger.debug(f"게시글 ID 추출 오류: {e}")
            return None
    
    def get_post_content(self, post_url: str) -> Optional[Dict]:
        """게시글 내용 가져오기"""
        try:
            response = self.session.get(post_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 게시글 내용 추출 - 다양한 선택자 시도
            content = None
            content_selectors = [
                ('div', {'id': 'bo_v_con'}),  # 그누보드 일반
                ('div', {'class': 'content'}),
                ('div', {'id': 'content'}),
                ('div', {'class': 'view_content'}),
                ('div', {'id': 'view_content'}),
                ('article', {}),
                ('div', {'class': 'board_content'}),
            ]
            
            for tag, attrs in content_selectors:
                content = soup.find(tag, attrs) if attrs else soup.find(tag)
                if content:
                    break
            
            # 여전히 못 찾은 경우, id나 class에 'content', 'view', 'article' 등이 포함된 div 찾기
            if not content:
                all_divs = soup.find_all('div')
                for div in all_divs:
                    div_id = div.get('id', '')
                    div_class = ' '.join(div.get('class', []))
                    if 'content' in div_id.lower() or 'content' in div_class.lower() or 'view' in div_id.lower():
                        if len(div.get_text(strip=True)) > 50:  # 충분한 내용이 있는 경우만
                            content = div
                            break
            
            content_text = content.get_text(strip=True) if content else ""
            
            # 제목도 추출
            title = None
            title_selectors = [
                ('h1', {}),
                ('div', {'id': 'bo_v_title'}),
                ('div', {'class': 'title'}),
            ]
            
            for tag, attrs in title_selectors:
                title_elem = soup.find(tag, attrs) if attrs else soup.find(tag)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break
            
            return {
                'content': content_text,
                'title': title or '',
                'soup': soup
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"게시글 내용 가져오기 오류: {e}")
            return None
    
    def has_commented(self, post_url: str, username: str) -> bool:
        """이미 댓글을 달았는지 확인"""
        try:
            response = self.session.get(post_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 댓글 영역 찾기 - 다양한 선택자 시도
            comment_selectors = [
                ('div', {'id': 'bo_vc'}),  # 그누보드 댓글 영역
                ('div', {'class': 'comment'}),
                ('div', {'class': 'comments'}),
                ('ul', {'class': 'comment_list'}),
                ('div', {'id': 'comment_list'}),
            ]
            
            comments = []
            for tag, attrs in comment_selectors:
                comments = soup.find_all(tag, attrs) if attrs else soup.find_all(tag)
                if comments:
                    break
            
            # 댓글에서 작성자 찾기
            for comment in comments:
                # 작성자 정보가 있는 요소 찾기
                author_selectors = [
                    ('span', {'class': 'author'}),
                    ('strong', {}),
                    ('div', {'class': 'comment_author'}),
                    ('span', {'class': 'comment_writer'}),
                ]
                
                for tag, attrs in author_selectors:
                    author = comment.find(tag, attrs) if attrs else comment.find(tag)
                    if author:
                        author_text = author.get_text(strip=True)
                        if username in author_text or author_text == username:
                            return True
                
                # 댓글 전체 텍스트에서 사용자명 확인 (대안)
                comment_text = comment.get_text()
                if username in comment_text:
                    # 사용자명이 포함되어 있고, 댓글 작성자 영역에 있는지 확인
                    if any(sel in comment_text for sel in ['작성자', '닉네임', '아이디']):
                        return True
            
            return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"댓글 확인 오류: {e}")
            return False
    
    def write_comment(self, post_url: str, comment: str) -> bool:
        """댓글 작성"""
        # 테스트 모드인 경우 실제로 작성하지 않고 로그만 출력
        if self.test_mode:
            logger.info(f"[테스트 모드] 댓글 작성 시뮬레이션: {post_url}")
            logger.info(f"[테스트 모드] 댓글 내용: {comment}")
            return True
        
        try:
            # 게시글 페이지 접속하여 댓글 폼 정보 가져오기
            response = self.session.get(post_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 댓글 작성 폼 찾기 - 다양한 선택자 시도
            comment_form = None
            form_selectors = [
                {'name': 'fcomment'},  # 그누보드 일반
                {'id': 'comment_form'},
                {'id': 'fcomment'},
                {'name': 'comment_form'},
            ]
            
            for selector in form_selectors:
                comment_form = soup.find('form', selector)
                if comment_form:
                    break
            
            # 폼을 못 찾은 경우, textarea가 있는 form 찾기
            if not comment_form:
                all_forms = soup.find_all('form')
                for form in all_forms:
                    textarea = form.find('textarea')
                    if textarea and ('comment' in textarea.get('name', '').lower() or 
                                   'content' in textarea.get('name', '').lower()):
                        comment_form = form
                        break
            
            if not comment_form:
                logger.error("댓글 폼을 찾을 수 없습니다")
                return False
            
            # 댓글 작성 URL 찾기
            action = comment_form.get('action', '')
            if not action:
                # action이 없으면 일반적인 댓글 작성 URL 시도
                if 'wr_id=' in post_url:
                    # 게시글 ID 추출하여 댓글 작성 URL 생성
                    post_id = self._extract_post_id(post_url)
                    if post_id:
                        action = f"{self.base_url}/bbs/write_comment_update.php"
                else:
                    action = f"{self.base_url}/bbs/write_comment_update.php"
            
            if not action.startswith('http'):
                action = f"{self.base_url}{action}"
            
            # 필요한 필드 수집
            comment_data = {}
            
            # textarea 찾기 (댓글 내용 필드)
            textarea = comment_form.find('textarea')
            if textarea:
                textarea_name = textarea.get('name', '')
                if textarea_name:
                    comment_data[textarea_name] = comment
                else:
                    # 이름이 없으면 일반적인 필드명 시도
                    comment_data['wr_content'] = comment
            else:
                comment_data['wr_content'] = comment
            
            # 모든 숨겨진 필드 추가
            hidden_inputs = comment_form.find_all('input', type='hidden')
            for input_tag in hidden_inputs:
                name = input_tag.get('name')
                value = input_tag.get('value', '')
                if name:
                    comment_data[name] = value
            
            # select 필드도 추가
            selects = comment_form.find_all('select')
            for select in selects:
                name = select.get('name')
                if name:
                    selected_option = select.find('option', selected=True)
                    if selected_option:
                        comment_data[name] = selected_option.get('value', '')
                    else:
                        first_option = select.find('option')
                        if first_option:
                            comment_data[name] = first_option.get('value', '')
            
            # 댓글 작성 POST 요청
            response = self.session.post(action, data=comment_data, timeout=10, allow_redirects=True)
            response.raise_for_status()
            
            # 댓글 작성 성공 여부 확인
            if '성공' in response.text or '등록' in response.text or '완료' in response.text:
                logger.info(f"댓글 작성 완료: {post_url}")
                return True
            elif '실패' in response.text or '오류' in response.text or '에러' in response.text:
                logger.error(f"댓글 작성 실패: 응답 내용 확인 필요")
                return False
            else:
                # 응답 URL이 변경되었거나 게시글 페이지로 돌아갔으면 성공으로 간주
                if post_url.split('?')[0] in response.url or 'wr_id=' in response.url:
                    logger.info(f"댓글 작성 완료 (리다이렉트 확인): {post_url}")
                    return True
                logger.warning(f"댓글 작성 상태 불명확: {response.url}")
                return True  # 일단 성공으로 간주 (추후 확인 필요)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"댓글 작성 오류: {e}")
            return False
    
    def close(self):
        """세션 종료"""
        self.session.close()

