"""
실시간 학습 모듈
- 게시글 처리 시 자동으로 댓글 수집
- 수집한 댓글을 즉시 학습 데이터에 추가
- 상세 로그 기록
"""

import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealtimeLearner:
    def __init__(self, log_file="learning_log.txt", comments_file="collected_comments.json"):
        self.log_file = log_file
        self.comments_file = comments_file
        self.learning_data_file = "realtime_learning_data.json"
        self.processed_posts = []  # 처리한 게시글 목록
        
        # 로그 파일 초기화
        self._init_log_file()
    
    def _init_log_file(self):
        """로그 파일 초기화"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("온카판 AI 댓글 학습 로그\n")
                f.write("=" * 80 + "\n")
                f.write(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
        except Exception as e:
            logger.error(f"로그 파일 초기화 오류: {e}")
    
    def collect_comments_from_post(self, scraper, post_url: str) -> List[str]:
        """게시글에서 댓글 수집"""
        try:
            from bs4 import BeautifulSoup
            import time
            import re
            
            # 현재 URL 확인 - 이미 해당 게시글 페이지에 있으면 새로고침 안 함
            current_url = scraper.driver.current_url
            if post_url not in current_url and current_url not in post_url:
                scraper.driver.get(post_url)
                time.sleep(1)  # 최소 대기 시간으로 줄임
            else:
                time.sleep(0.3)  # 이미 해당 페이지에 있으면 짧은 대기만
            
            # 페이지가 완전히 로드될 때까지 대기 (타임아웃 줄임)
            try:
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.common.by import By
                WebDriverWait(scraper.driver, 3).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # 댓글 섹션이 로드될 때까지 추가 대기 (타임아웃 줄임)
                try:
                    # 여러 패턴으로 댓글 섹션 찾기
                    wait = WebDriverWait(scraper.driver, 3)
                    wait.until(
                        lambda driver: driver.find_elements(By.CSS_SELECTOR, "section#bo_vc") or 
                                       driver.find_elements(By.CSS_SELECTOR, "article[id^='c_']") or
                                       driver.find_elements(By.CSS_SELECTOR, "textarea[id^='save_comment_']")
                    )
                    logger.debug("댓글 섹션 로드 완료")
                except:
                    logger.debug("댓글 섹션 로드 대기 시간 초과 (계속 진행)")
                    time.sleep(0.5)  # 최소 대기 시간으로 줄임
            except:
                pass
            
            # 스크롤하여 댓글이 동적으로 로드되도록 함 (대기 시간 최소화)
            try:
                # 댓글 섹션으로 스크롤
                bo_vc_element = scraper.driver.find_elements(By.CSS_SELECTOR, "section#bo_vc")
                if bo_vc_element:
                    scraper.driver.execute_script("arguments[0].scrollIntoView(true);", bo_vc_element[0])
                    time.sleep(0.5)  # 대기 시간 줄임
                
                # 페이지 끝까지 스크롤 (동적 로딩 트리거)
                scraper.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)  # 대기 시간 줄임
                
                # 댓글 섹션으로 다시 스크롤
                if bo_vc_element:
                    scraper.driver.execute_script("arguments[0].scrollIntoView(true);", bo_vc_element[0])
                    time.sleep(0.5)  # 대기 시간 줄임
            except:
                pass
            
            # 페이지 소스를 시도하여 동적 로딩 대응 (시도 횟수 줄임)
            soup = None
            for attempt in range(2):  # 3번에서 2번으로 줄임
                soup = BeautifulSoup(scraper.driver.page_source, 'html.parser')
                bo_vc = soup.find('section', id='bo_vc')
                if bo_vc:
                    articles = bo_vc.find_all('article', id=lambda x: x and x.startswith('c_'))
                    if articles:
                        # 로그 간소화
                        break
                if attempt < 1:
                    time.sleep(0.5)  # 대기 시간 줄임
                    scraper.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.3)  # 대기 시간 줄임
            
            comments = []
            
            # 온카판 실제 댓글 구조에 맞는 선택자
            # 댓글은 <section id="bo_vc"> 안에 <article id="c_숫자"> 형태로 존재
            # 댓글 내용은 <div class="cmt_contents"> 안의 <p> 태그에 있음
            # 또는 <textarea id="save_comment_숫자"> 에도 저장되어 있음
            
            # 방법 1: section#bo_vc 안의 article 태그에서 댓글 찾기 (우선)
            bo_vc = soup.find('section', id='bo_vc')
            if bo_vc:
                comment_articles = bo_vc.find_all('article', id=lambda x: x and x.startswith('c_'))
            else:
                comment_articles = []
            
            # 방법 2: 전체 페이지에서 c_로 시작하는 article 찾기 (백업)
            if not comment_articles:
                comment_articles = soup.find_all('article', id=lambda x: x and x.startswith('c_'))
                for idx, article in enumerate(comment_articles):
                    article_id = article.get('id', 'unknown')
                    logger.debug(f"처리 중: article[{idx}] id={article_id}")
                    comment_found = False
                    
                    # 방법 1-1: textarea에서 찾기 (가장 정확함 - 우선 사용)
                    textarea = article.find('textarea', id=lambda x: x and x.startswith('save_comment_'))
                    if textarea:
                        content = textarea.get_text(strip=True)
                        if content and 3 < len(content) < 200:
                            # "(수정됨 ...)" 같은 텍스트 제거
                            if '(수정됨' in content:
                                content = content.split('(수정됨')[0].strip()
                            if content and content not in comments:
                                comments.append(content)
                                comment_found = True
                                # 로그 간소화: 각 댓글마다 출력하지 않음
                    
                    # 방법 1-2: cmt_contents 클래스 안의 p 태그 찾기 (백업)
                    if not comment_found:
                        cmt_contents = article.find('div', class_='cmt_contents')
                        if cmt_contents:
                            p_tag = cmt_contents.find('p')
                            if p_tag:
                                content = p_tag.get_text(strip=True)
                                if content and 3 < len(content) < 200:
                                    # "(수정됨 ...)" 같은 텍스트 제거
                                    if '(수정됨' in content:
                                        content = content.split('(수정됨')[0].strip()
                                    if content and content not in comments:
                                        comments.append(content)
                                        comment_found = True
                                        # 로그 간소화: 각 댓글마다 출력하지 않음
                    
                    # 방법 1-3: article 내의 모든 p 태그에서 찾기 (최후의 수단)
                    if not comment_found:
                        p_tags = article.find_all('p')
                        for p in p_tags:
                            content = p.get_text(strip=True)
                            if content and 3 < len(content) < 200:
                                # 키워드 필터링
                                exclude_keywords = [
                                    '게시글', '작성자', '조회수', '추천', '비추천', '목록', '이전', '다음',
                                    '로그인', '회원가입', '검색', '메뉴', '네비게이션', '푸터', '헤더',
                                    '공지사항', '베스트', '인기', '최신', '정렬', '페이지', '댓글쓰기',
                                    '수정', '삭제', '신고', '답글', '대댓글', '더보기', '접기', '전체보기',
                                    '수정됨', '작성일', '댓글', '개', '건', '님의', '댓글'
                                ]
                                if not any(keyword in content for keyword in exclude_keywords):
                                    if content and content not in comments:
                                        comments.append(content)
                                        # 로그 간소화: 각 댓글마다 출력하지 않음
                                        break
                    
                    # 로그 간소화: 개별 실패 로그 제거
            
            # 방법 2: section#bo_vc에서 직접 찾기 (백업)
            if not comments:
                bo_vc = soup.find('section', id='bo_vc')
                if bo_vc:
                    # section 내부의 모든 요소 확인
                    all_textareas = bo_vc.find_all('textarea')
                    all_divs = bo_vc.find_all('div', class_='cmt_contents')
                    
                    # 방법 2-1: 모든 textarea에서 찾기 (가장 정확) - ID 패턴 확장
                    textareas = bo_vc.find_all('textarea', id=lambda x: x and ('save_comment_' in str(x) or 'comment' in str(x).lower()))
                    if not textareas:
                        # ID 조건 없이 모든 textarea 확인
                        textareas = bo_vc.find_all('textarea')
                    
                    for textarea in textareas:
                        content = textarea.get_text(strip=True)
                        if content and 3 < len(content) < 200:
                            if '(수정됨' in content:
                                content = content.split('(수정됨')[0].strip()
                            if content and content not in comments:
                                comments.append(content)
                                logger.debug(f"section textarea에서 댓글 추출: {content[:30]}...")
                    
                    # 방법 2-2: cmt_contents div에서 찾기
                    if not comments:
                        for div in all_divs:
                            # div 내부의 p 태그 찾기
                            p_tag = div.find('p')
                            if p_tag:
                                content = p_tag.get_text(strip=True)
                                if content and 3 < len(content) < 200:
                                    if '(수정됨' in content:
                                        content = content.split('(수정됨')[0].strip()
                                    if content and content not in comments:
                                        comments.append(content)
                                        logger.debug(f"section cmt_contents에서 댓글 추출: {content[:30]}...")
                            else:
                                # p 태그가 없으면 div 자체의 텍스트
                                content = div.get_text(strip=True)
                                if content and 3 < len(content) < 200:
                                    if '(수정됨' in content:
                                        content = content.split('(수정됨')[0].strip()
                                    if content and content not in comments:
                                        comments.append(content)
                                        logger.debug(f"section cmt_contents div 텍스트에서 댓글 추출: {content[:30]}...")
                    
                    # 방법 2-3: p 태그에서 찾기 (더 넓은 범위)
                    if not comments:
                        p_tags = bo_vc.find_all('p')
                        for p in p_tags:
                            content = p.get_text(strip=True)
                            # 댓글처럼 보이는 텍스트만 (너무 짧거나 길지 않고, 특정 키워드 제외)
                            if content and 3 < len(content) < 200:
                                exclude_keywords = [
                                    '게시글', '작성자', '조회수', '추천', '비추천', '목록', '이전', '다음',
                                    '로그인', '회원가입', '검색', '메뉴', '네비게이션', '푸터', '헤더',
                                    '공지사항', '베스트', '인기', '최신', '정렬', '페이지', '댓글쓰기',
                                    '수정', '삭제', '신고', '답글', '대댓글', '더보기', '접기', '전체보기',
                                    '수정됨', '작성일', '댓글', '개', '건', '님의'
                                ]
                                if not any(keyword in content for keyword in exclude_keywords):
                                    if content not in comments:
                                        comments.append(content)
                                        logger.debug(f"section p 태그에서 댓글 추출: {content[:30]}...")
            
            # 방법 3: 페이지 전체에서 textarea 찾기 (최후의 수단)
            if not comments:
                all_textareas = soup.find_all('textarea', id=lambda x: x and 'comment' in str(x).lower())
                for textarea in all_textareas:
                    content = textarea.get_text(strip=True)
                    if content and 3 < len(content) < 200:
                        if '(수정됨' in content:
                            content = content.split('(수정됨')[0].strip()
                        if content and content not in comments:
                            comments.append(content)
                            logger.debug(f"전체 페이지 textarea에서 댓글 추출: {content[:30]}...")
            
            
            # 중복 제거 및 정리
            unique_comments = []
            seen = set()
            for comment in comments:
                # 공백 제거 후 비교
                comment_normalized = re.sub(r'\s+', ' ', comment.strip())
                if comment_normalized and comment_normalized not in seen:
                    seen.add(comment_normalized)
                    unique_comments.append(comment)
            
            # 로그 간소화: GUI에서만 표시
            
            # 디버깅: 댓글을 찾지 못한 경우 상세 로그
            if len(unique_comments) == 0:
                logger.warning(f"댓글을 찾지 못했습니다. 디버깅 정보:")
                logger.warning(f"  - article 태그 개수: {len(comment_articles) if 'comment_articles' in locals() else 0}")
                logger.warning(f"  - section#bo_vc 존재: {bool(soup.find('section', id='bo_vc'))}")
                
                # 더 상세한 디버깅
                bo_vc = soup.find('section', id='bo_vc')
                if bo_vc:
                    # section 내부의 모든 textarea 확인
                    textareas = bo_vc.find_all('textarea')
                    logger.warning(f"  - section 내부 textarea 개수: {len(textareas)}")
                    if textareas:
                        for i, ta in enumerate(textareas[:3]):  # 처음 3개만
                            ta_id = ta.get('id', 'no-id')
                            ta_text = ta.get_text(strip=True)[:50]
                            logger.warning(f"    textarea[{i}] id={ta_id}, text={ta_text}...")
                    
                    # section 내부의 모든 div.cmt_contents 확인
                    cmt_divs = bo_vc.find_all('div', class_='cmt_contents')
                    logger.warning(f"  - section 내부 cmt_contents div 개수: {len(cmt_divs)}")
                    if cmt_divs:
                        for i, div in enumerate(cmt_divs[:3]):  # 처음 3개만
                            div_text = div.get_text(strip=True)[:50]
                            logger.warning(f"    cmt_contents[{i}] text={div_text}...")
                
                # 페이지 소스 일부 저장 (댓글 섹션만)
                try:
                    if bo_vc:
                        debug_file = f"debug_comment_section_{int(time.time())}.html"
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(str(bo_vc))
                        logger.warning(f"댓글 섹션 HTML을 {debug_file}에 저장했습니다.")
                    else:
                        debug_file = f"debug_page_source_{int(time.time())}.html"
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(scraper.driver.page_source)
                        logger.warning(f"댓글 섹션을 찾지 못해 전체 페이지 소스를 {debug_file}에 저장했습니다.")
                except Exception as e:
                    logger.error(f"디버그 파일 저장 오류: {e}")
            
            return unique_comments
            
        except Exception as e:
            logger.error(f"댓글 수집 오류: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def save_comments_to_learning_data(self, comments: List[str]):
        """수집한 댓글을 학습 데이터에 추가"""
        try:
            # 기존 댓글 로드
            existing_comments = []
            if os.path.exists(self.comments_file):
                with open(self.comments_file, 'r', encoding='utf-8') as f:
                    existing_comments = json.load(f)
            
            # 중복 제거
            existing_contents = {c.get('content', '') if isinstance(c, dict) else c for c in existing_comments}
            
            # 새 댓글 추가
            new_comments = []
            for comment in comments:
                if comment not in existing_contents:
                    new_comments.append({
                        'content': comment,
                        'length': len(comment),
                        'word_count': len(comment.split()),
                        'collected_at': datetime.now().isoformat()
                    })
                    existing_contents.add(comment)
            
            if new_comments:
                all_comments = existing_comments + new_comments
                
                # 저장
                with open(self.comments_file, 'w', encoding='utf-8') as f:
                    json.dump(all_comments, f, ensure_ascii=False, indent=2)
                
                logger.info(f"새로운 댓글 {len(new_comments)}개를 학습 데이터에 추가했습니다.")
                return len(new_comments)
            
            return 0
            
        except Exception as e:
            logger.error(f"댓글 저장 오류: {e}")
            return 0
    
    def log_post_processing(self, post_title: str, post_content: str, 
                            actual_comments: List[str], ai_comment: Optional[str],
                            post_url: str = ""):
        """게시글 처리 로그 기록"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write("\n" + "=" * 80 + "\n")
                f.write(f"게시글 처리 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n")
                f.write(f"게시글 URL: {post_url}\n")
                f.write(f"제목: {post_title}\n")
                f.write("-" * 80 + "\n")
                f.write("게시글 본문:\n")
                f.write(post_content[:500] + ("..." if len(post_content) > 500 else "") + "\n")
                f.write("-" * 80 + "\n")
                f.write(f"실제 댓글 수: {len(actual_comments)}개\n")
                if actual_comments:
                    f.write("실제 댓글들:\n")
                    for i, comment in enumerate(actual_comments, 1):
                        f.write(f"  {i}. {comment}\n")
                else:
                    f.write("실제 댓글: 없음\n")
                f.write("-" * 80 + "\n")
                if ai_comment:
                    f.write(f"AI 생성 댓글: {ai_comment}\n")
                else:
                    f.write("AI 생성 댓글: 생성 실패\n")
                f.write("=" * 80 + "\n\n")
                
        except Exception as e:
            logger.error(f"로그 기록 오류: {e}")
    
    def add_processed_post(self, post_data: Dict):
        """처리한 게시글 추가"""
        self.processed_posts.append({
            'title': post_data.get('title', ''),
            'content': post_data.get('content', '')[:200],  # 처음 200자만
            'url': post_data.get('url', ''),
            'actual_comments': post_data.get('actual_comments', []),
            'ai_comment': post_data.get('ai_comment', ''),
            'processed_at': datetime.now().isoformat()
        })
    
    def get_learning_summary(self) -> Dict:
        """학습 요약 정보"""
        try:
            total_comments = 0
            if os.path.exists(self.comments_file):
                with open(self.comments_file, 'r', encoding='utf-8') as f:
                    comments = json.load(f)
                    total_comments = len(comments)
            
            return {
                'processed_posts': len(self.processed_posts),
                'total_learned_comments': total_comments,
                'last_updated': datetime.now().isoformat()
            }
        except:
            return {
                'processed_posts': len(self.processed_posts),
                'total_learned_comments': 0,
                'last_updated': datetime.now().isoformat()
            }

