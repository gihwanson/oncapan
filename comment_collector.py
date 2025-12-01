"""
실제 댓글 수집 모듈
- 온카판 게시글에서 실제 댓글 수집
- 댓글 스타일 분석
"""

from web_scraper_selenium import OncaPanScraperSelenium
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
import json
import os
import re
import time
from collections import Counter
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CommentCollector:
    def __init__(self):
        self.scraper = OncaPanScraperSelenium(test_mode=True)
        self.comments_file = "collected_comments.json"
        self.analysis_file = "comment_analysis.json"
    
    def collect_comments_from_post(self, post_url: str, max_comments: int = 50) -> List[Dict]:
        """게시글에서 댓글 수집"""
        try:
            self.scraper.driver.get(post_url)
            time.sleep(3)  # 페이지 로딩 대기
            
            # 페이지가 완전히 로드될 때까지 대기
            try:
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                WebDriverWait(self.scraper.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except:
                pass
            
            soup = BeautifulSoup(self.scraper.driver.page_source, 'html.parser')
            comments = []
            
            # 다양한 댓글 선택자 시도
            comment_selectors = [
                # 일반적인 댓글 구조
                ('div', {'id': 'bo_vc'}),
                ('div', {'class': 'comment'}),
                ('div', {'class': 'comments'}),
                ('ul', {'class': 'comment_list'}),
                ('div', {'class': 'comment-list'}),
                ('div', {'id': 'comment-list'}),
                # li 태그의 댓글
                ('li', {'class': lambda x: x and 'comment' in str(x).lower()}),
                # 테이블 구조의 댓글
                ('tr', {'class': lambda x: x and 'comment' in str(x).lower()}),
            ]
            
            comment_elements = []
            for tag, attrs in comment_selectors:
                try:
                    if isinstance(attrs, dict) and 'class' in attrs and callable(attrs['class']):
                        # lambda 함수인 경우
                        found = soup.find_all(tag, class_=attrs['class'])
                    elif isinstance(attrs, dict):
                        found = soup.find_all(tag, attrs)
                    else:
                        found = soup.find_all(tag)
                    
                    if found:
                        comment_elements = found
                        logger.debug(f"댓글 영역 발견: {tag} with {attrs}")
                        break
                except:
                    continue
            
            # 댓글 요소가 없으면 다른 방법 시도
            if not comment_elements:
                # 모든 div에서 댓글 같은 텍스트 찾기
                all_divs = soup.find_all('div')
                for div in all_divs:
                    div_text = div.get_text(strip=True)
                    # 짧은 텍스트(댓글 후보) 찾기
                    if 5 < len(div_text) < 150 and div_text not in [c.get('content', '') for c in comments]:
                        # 댓글처럼 보이는지 확인 (너무 긴 문장이 아니고, 특정 패턴 포함)
                        if not any(keyword in div_text for keyword in ['게시글', '작성자', '조회수', '추천', '비추천']):
                            comment_elements.append(div)
                            if len(comment_elements) >= max_comments:
                                break
            
            # 각 댓글에서 내용 추출
            for comment_elem in comment_elements[:max_comments]:
                # 댓글 내용 찾기
                content = None
                
                # 여러 방법으로 댓글 텍스트 추출 시도
                content_selectors = [
                    lambda x: x.find('div', class_=lambda c: c and 'content' in str(c).lower()),
                    lambda x: x.find('p'),
                    lambda x: x.find('span', class_=lambda c: c and 'text' in str(c).lower()),
                    lambda x: x.find('td', class_=lambda c: c and 'comment' in str(c).lower()),
                    lambda x: x.find('div', class_=lambda c: c and 'text' in str(c).lower()),
                ]
                
                for selector in content_selectors:
                    try:
                        content_elem = selector(comment_elem)
                        if content_elem:
                            content = content_elem.get_text(strip=True)
                            if content and len(content) > 3:
                                break
                    except:
                        continue
                
                # 선택자로 찾지 못하면 직접 텍스트 추출
                if not content:
                    content = comment_elem.get_text(strip=True)
                    # 너무 긴 텍스트는 제외 (게시글 본문일 수 있음)
                    if len(content) > 200:
                        continue
                
                # 의미있는 댓글만 저장
                if content and 3 < len(content) < 200:
                    # 중복 제거
                    if content not in [c['content'] for c in comments]:
                        comments.append({
                            'content': content,
                            'length': len(content),
                            'word_count': len(content.split())
                        })
            
            logger.info(f"게시글에서 {len(comments)}개의 댓글 수집: {post_url[:50]}...")
            return comments
            
        except Exception as e:
            logger.error(f"댓글 수집 오류: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def collect_comments_from_board(self, limit_posts: int = 10, comments_per_post: int = 10) -> List[Dict]:
        """게시판에서 여러 게시글의 댓글 수집"""
        all_comments = []
        
        try:
            posts = self.scraper.get_post_list(limit=limit_posts)
            
            for i, post in enumerate(posts, 1):
                logger.info(f"게시글 {i}/{len(posts)}: {post.get('title', '')[:30]}")
                comments = self.collect_comments_from_post(post.get('url'), max_comments=comments_per_post)
                all_comments.extend(comments)
                
                if len(all_comments) >= 100:  # 충분한 댓글 수집
                    break
            
            return all_comments
            
        except Exception as e:
            logger.error(f"댓글 수집 오류: {e}")
            return all_comments
    
    def save_comments(self, comments: List[Dict]):
        """수집한 댓글 저장"""
        try:
            # 기존 댓글 로드
            existing_comments = []
            if os.path.exists(self.comments_file):
                with open(self.comments_file, 'r', encoding='utf-8') as f:
                    existing_comments = json.load(f)
            
            # 중복 제거 (내용 기준)
            existing_contents = {c['content'] for c in existing_comments}
            new_comments = [c for c in comments if c['content'] not in existing_contents]
            
            # 합치기
            all_comments = existing_comments + new_comments
            
            # 저장
            with open(self.comments_file, 'w', encoding='utf-8') as f:
                json.dump(all_comments, f, ensure_ascii=False, indent=2)
            
            logger.info(f"댓글 저장 완료: 총 {len(all_comments)}개 (새로 추가: {len(new_comments)}개)")
            return len(new_comments)
            
        except Exception as e:
            logger.error(f"댓글 저장 오류: {e}")
            return 0
    
    def analyze_comments(self) -> Dict:
        """수집한 댓글 분석"""
        try:
            if not os.path.exists(self.comments_file):
                logger.warning("수집한 댓글이 없습니다.")
                return {}
            
            with open(self.comments_file, 'r', encoding='utf-8') as f:
                comments = json.load(f)
            
            if not comments:
                return {}
            
            # 분석
            analysis = {
                'total_count': len(comments),
                'avg_length': sum(c['length'] for c in comments) / len(comments),
                'length_distribution': {
                    'short': sum(1 for c in comments if c['length'] <= 20),
                    'medium': sum(1 for c in comments if 20 < c['length'] <= 50),
                    'long': sum(1 for c in comments if c['length'] > 50)
                },
                'common_patterns': [],
                'common_endings': [],
                'sample_comments': comments[:20]  # 샘플 20개
            }
            
            # 자주 사용되는 어미/패턴 분석
            endings = []
            for comment in comments:
                content = comment['content']
                # 마지막 2-3글자 추출
                if len(content) >= 2:
                    endings.append(content[-2:])
            
            ending_counter = Counter(endings)
            analysis['common_endings'] = [{'ending': k, 'count': v} 
                                          for k, v in ending_counter.most_common(10)]
            
            # 자주 사용되는 단어/구문
            all_words = []
            for comment in comments:
                words = re.findall(r'\w+', comment['content'])
                all_words.extend(words)
            
            word_counter = Counter(all_words)
            analysis['common_words'] = [{'word': k, 'count': v} 
                                       for k, v in word_counter.most_common(20)]
            
            # 분석 결과 저장
            with open(self.analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)
            
            logger.info(f"댓글 분석 완료: {len(comments)}개 댓글 분석")
            return analysis
            
        except Exception as e:
            logger.error(f"댓글 분석 오류: {e}")
            return {}
    
    def get_comment_examples(self, count: int = 10) -> List[str]:
        """분석된 댓글 예시 가져오기"""
        try:
            if os.path.exists(self.analysis_file):
                with open(self.analysis_file, 'r', encoding='utf-8') as f:
                    analysis = json.load(f)
                    return [c['content'] for c in analysis.get('sample_comments', [])[:count]]
            elif os.path.exists(self.comments_file):
                with open(self.comments_file, 'r', encoding='utf-8') as f:
                    comments = json.load(f)
                    return [c['content'] for c in comments[:count]]
            return []
        except:
            return []
    
    def close(self):
        """리소스 정리"""
        if hasattr(self, 'scraper'):
            self.scraper.close()

