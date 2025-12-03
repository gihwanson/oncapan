"""
학습 분석 모듈
- 로그 파일 분석하여 패턴 추출
- 주제별 댓글 통계 관리
- 유사 게시글 찾기
"""

import json
import os
import sys
import re
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import Counter, defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LearningAnalyzer:
    def __init__(self, learning_data_file=None, log_file="learning_log.txt"):
        # 학습 데이터 파일 경로 설정 (영구 저장 위치)
        if learning_data_file is None:
            # exe 실행 시와 스크립트 실행 시 모두 동작하도록
            if getattr(sys, 'frozen', False):
                # PyInstaller로 빌드된 exe 실행 시
                base_path = os.path.dirname(sys.executable)
            else:
                # 스크립트 실행 시
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            # 사용자 홈 디렉토리에 저장 (영구 보존)
            user_home = os.path.expanduser('~')
            app_data_dir = os.path.join(user_home, 'oncapan_learning')
            
            # 디렉토리 생성 (없으면)
            try:
                os.makedirs(app_data_dir, exist_ok=True)
            except Exception as e:
                logger.warning(f"학습 데이터 디렉토리 생성 실패, 현재 디렉토리 사용: {e}")
                app_data_dir = base_path
            
            self.learning_data_file = os.path.join(app_data_dir, "learning_data.json")
            self.log_file = os.path.join(app_data_dir, log_file)
        else:
            self.learning_data_file = learning_data_file
            self.log_file = log_file
        
        self.learning_data = self._load_learning_data()
        
        # 커뮤니티 특수 용어 사전
        self.special_terms = [
            '담타', '렉카', '포전', '포바', '단포바', '깊전', '댓노', '멘징',
            '골스', '오클', '느바', '크보', '믈브', '해축', '새축', '일야',
            '담배', '쌈배', '맛담', '맛점', '맛저', '맛아', '맛커', '맛런치',
            '무브', '후땡', '고우', '꿀잼', '개꿀잼', '쫄깃', '연장', '페이백',
            '추워', '춥', '감기', '한숨', '식곤증', '졸립', '런치', '점심',
            '벳계', '벳컨', '88', '16', '쿨거', '입금', '지연', '조회수'
        ]
    
    def _load_learning_data(self) -> Dict:
        """학습 데이터 로드 (초기 데이터 자동 복사 포함)"""
        # 초기 학습 데이터 경로 찾기
        initial_data_path = None
        if getattr(sys, 'frozen', False):
            # PyInstaller로 빌드된 exe 실행 시
            exe_dir = os.path.dirname(sys.executable)
            initial_data_path = os.path.join(exe_dir, "initial_learning_data.json")
        else:
            # 스크립트 실행 시
            script_dir = os.path.dirname(os.path.abspath(__file__))
            initial_data_path = os.path.join(script_dir, "initial_learning_data.json")
        
        # 기존 학습 데이터가 있으면 로드
        if os.path.exists(self.learning_data_file):
            try:
                with open(self.learning_data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"학습 데이터 로드 오류: {e}")
                return self._init_learning_data()
        
        # 기존 학습 데이터가 없고, 초기 학습 데이터가 있으면 복사
        if initial_data_path and os.path.exists(initial_data_path):
            try:
                logger.info(f"초기 학습 데이터 발견: {initial_data_path}")
                with open(initial_data_path, 'r', encoding='utf-8') as f:
                    initial_data = json.load(f)
                
                # 초기 데이터를 사용자 학습 데이터 파일로 복사
                os.makedirs(os.path.dirname(self.learning_data_file), exist_ok=True)
                with open(self.learning_data_file, 'w', encoding='utf-8') as f:
                    json.dump(initial_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"초기 학습 데이터를 복사했습니다: {self.learning_data_file}")
                return initial_data
            except Exception as e:
                logger.error(f"초기 학습 데이터 복사 오류: {e}")
                return self._init_learning_data()
        
        # 초기 데이터도 없으면 빈 데이터로 시작
        return self._init_learning_data()
    
    def _init_learning_data(self) -> Dict:
        """초기 학습 데이터 구조"""
        return {
            'topic_statistics': {},  # 주제별 댓글 통계
            'post_comment_pairs': [],  # 게시글-댓글 쌍 (최근 1000개)
            'keyword_patterns': {},  # 키워드별 댓글 패턴
            'last_analyzed': None,
            'total_processed': 0,
            'version': '1.0'
        }
    
    def _save_learning_data(self):
        """학습 데이터 저장"""
        try:
            self.learning_data['last_updated'] = datetime.now().isoformat()
            with open(self.learning_data_file, 'w', encoding='utf-8') as f:
                json.dump(self.learning_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"학습 데이터 저장 완료: {self.learning_data_file}")
        except Exception as e:
            logger.error(f"학습 데이터 저장 오류: {e}")
    
    def extract_topic_keywords(self, title: str, content: str) -> List[str]:
        """게시글에서 주제 키워드 추출 (어미/조사 제외)"""
        text = f"{title} {content}".lower()
        found_keywords = []
        
        # 특수 용어 우선 검색
        for term in self.special_terms:
            if term in text:
                found_keywords.append(term)
        
        # 제외할 어미/조사 목록
        exclude_endings = ('합니다', '니다', '네요', '해요', '이에요', '예요', '이네요', '이죠', 
                          '이다', '입니다', '이야', '야', '어요', '아요', '지요', '죠',
                          '거예요', '거야', '거다', '되요', '돼요', '되네', '되나', '되는',
                          '될', '되면', '되니', '하네', '하나', '하는', '할', '하면',
                          '하니', '하죠', '하세요', '가요', '가네', '가는', '갈', '가면',
                          '가니', '가죠', '가세요', '와요', '와네', '오는', '올', '오면',
                          '오니', '오죠', '오세요', '있어', '있네', '있는', '있을', '있으면',
                          '있니', '있죠', '있어요', '없어', '없네', '없는', '없을', '없으면',
                          '없니', '없죠', '없어요', '좋아', '좋네', '좋은', '좋을', '좋으면',
                          '좋니', '좋죠', '좋아요', '나와', '나네', '나는', '날', '나면',
                          '나니', '나죠', '나와요', '보네', '보는', '볼', '보면', '보니',
                          '보죠', '보세요', '먹네', '먹는', '먹을', '먹으면', '먹니', '먹죠',
                          '먹어요', '하시', '하셔', '하신', '하실', '하시면', '하시니', '하시죠')
        
        exclude_words = {
            # 조사 (1글자)
            '은', '는', '이', '가', '을', '를', '의', '에', '에서', '와', '과', 
            '도', '만', '조차', '까지', '부터', '에게', '한테', '께', '로', '으로',
            '처럼', '같이', '만큼', '보다', '마다', '대로', '커녕',
            # 대명사/지시어
            '그것', '이것', '저것', '그거', '이거', '저거', '그래', '그런', '그럼',
            '이런', '저런', '어떤', '어떠', '어디', '언제', '누구', '무엇', '뭐', '뭔',
            '왜', '어떻게', '어떡해', '어떡하지',
            # 부정어
            '안', '않', '못', '안해', '않아', '못해',
            # 부사 (의미 없는 경우)
            '많이', '조금', '정말', '정말로', '진짜', '진짜로', '완전', '완전히',
            '너무', '너무나', '너무도', '매우', '아주', '엄청', '그냥', '그저',
            '다시', '또', '또다시', '계속', '계속해서',
            # 시간 부사
            '지금', '현재', '오늘', '내일', '어제', '이번', '다음', '처음', '마지막',
            # 정도 부사
            '가장', '제일', '모두', '전부', '다',
            # 접속어
            '또한', '그리고', '하지만', '그런데', '그래서', '그러면', '그러나', '그러므로',
            # 기타 불필요한 단어
            '때문', '때문에', '위해', '위해서', '대해', '대해서', '관해', '관해서',
            '통해', '통해서', '따라', '따라서', '비해', '비해서', '대신', '대신에',
            # 어미 패턴
            '입니', '습니', '시다', '게맞', '게되', '게하',
        }
        
        # 일반 키워드 추출 (2-4글자 한글 단어)
        words = re.findall(r'[가-힣]{2,4}', text)
        word_freq = Counter(words)
        
        # 빈도가 높은 단어 추가 (특수 용어 및 제외 단어 제외)
        for word, freq in word_freq.most_common(20):  # 더 많이 확인
            # 제외 조건 체크
            if word in found_keywords:  # 이미 추가된 키워드
                continue
            if word in exclude_words:  # 제외 단어
                continue
            if len(word) < 2:  # 너무 짧은 단어
                continue
            
            # 어미로 끝나는지 체크
            if word.endswith(exclude_endings):
                continue
            
            # 어미로 시작하는 패턴 체크 (입니, 습니, 시다 등)
            if word.startswith(('입니', '습니', '시다', '게맞', '게되', '게하')):
                continue
            
            # 조사로 시작하거나 끝나는지 체크
            if word.startswith(('은', '는', '이', '가', '을', '를', '의', '에', '에서', '와', '과', '도', '만')):
                continue
            if word.endswith(('은', '는', '이', '가', '을', '를', '의', '에', '에서', '와', '과', '도', '만')):
                continue
            
            found_keywords.append(word)
            if len(found_keywords) >= 10:  # 최대 10개
                break
        
        return found_keywords[:10]  # 최대 10개
    
    def update_topic_statistics(self, title: str, content: str, actual_comments: List[str]):
        """주제별 댓글 통계 업데이트 (즉시 학습)"""
        try:
            keywords = self.extract_topic_keywords(title, content)
            
            if not keywords or not actual_comments:
                return
            
            topic_stats = self.learning_data.setdefault('topic_statistics', {})
            
            for keyword in keywords:
                if keyword not in topic_stats:
                    topic_stats[keyword] = {
                        'comment_count': 0,
                        'comments': [],
                        'last_updated': datetime.now().isoformat()
                    }
                
                # 댓글 추가 (중복 제거)
                for comment in actual_comments:
                    if comment not in topic_stats[keyword]['comments']:
                        topic_stats[keyword]['comments'].append(comment)
                        topic_stats[keyword]['comment_count'] += 1
                
                # 최대 50개 댓글만 유지
                if len(topic_stats[keyword]['comments']) > 50:
                    topic_stats[keyword]['comments'] = topic_stats[keyword]['comments'][-50:]
                
                topic_stats[keyword]['last_updated'] = datetime.now().isoformat()
            
            # 게시글-댓글 쌍 저장 (최근 1000개만 유지)
            post_comment_pairs = self.learning_data.setdefault('post_comment_pairs', [])
            post_comment_pairs.append({
                'title': title[:100],
                'content': content[:300],
                'keywords': keywords,
                'comments': actual_comments[:10],  # 최대 10개 댓글만
                'timestamp': datetime.now().isoformat()
            })
            
            # 최대 1000개만 유지
            if len(post_comment_pairs) > 1000:
                post_comment_pairs[:] = post_comment_pairs[-1000:]
            
            self.learning_data['total_processed'] = self.learning_data.get('total_processed', 0) + 1
            self._save_learning_data()
            
            logger.debug(f"주제별 통계 업데이트 완료: {len(keywords)}개 키워드")
            
        except Exception as e:
            logger.error(f"주제별 통계 업데이트 오류: {e}")
    
    def find_similar_posts(self, title: str, content: str, top_n: int = 5) -> List[Dict]:
        """유사 게시글 찾기 (키워드 기반)"""
        try:
            target_keywords = set(self.extract_topic_keywords(title, content))
            
            if not target_keywords:
                return []
            
            post_comment_pairs = self.learning_data.get('post_comment_pairs', [])
            similarities = []
            
            for pair in post_comment_pairs:
                pair_keywords = set(pair.get('keywords', []))
                
                # 키워드 교집합으로 유사도 계산
                if pair_keywords:
                    intersection = target_keywords & pair_keywords
                    union = target_keywords | pair_keywords
                    similarity = len(intersection) / len(union) if union else 0
                    
                    if similarity > 0:
                        similarities.append({
                            'similarity': similarity,
                            'post': pair,
                            'common_keywords': list(intersection)
                        })
            
            # 유사도 순으로 정렬
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            return similarities[:top_n]
            
        except Exception as e:
            logger.error(f"유사 게시글 찾기 오류: {e}")
            return []
    
    def get_topic_comments(self, keywords: List[str], max_comments: int = 10) -> List[str]:
        """주제별 댓글 가져오기"""
        try:
            topic_stats = self.learning_data.get('topic_statistics', {})
            all_comments = []
            
            for keyword in keywords:
                if keyword in topic_stats:
                    comments = topic_stats[keyword].get('comments', [])
                    all_comments.extend(comments)
            
            # 중복 제거 및 빈도순 정렬
            comment_freq = Counter(all_comments)
            sorted_comments = [comment for comment, _ in comment_freq.most_common(max_comments)]
            
            return sorted_comments
            
        except Exception as e:
            logger.error(f"주제별 댓글 가져오기 오류: {e}")
            return []
    
    def analyze_log_file(self, batch_size: int = 100):
        """로그 파일 분석하여 패턴 추출 (배치 학습)"""
        try:
            if not os.path.exists(self.log_file):
                logger.warning(f"로그 파일이 없습니다: {self.log_file}")
                return
            
            with open(self.log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            # 게시글 블록 분리
            post_blocks = re.split(r'={80}', log_content)
            
            processed_count = 0
            for block in post_blocks:
                if '게시글 처리 시간' not in block:
                    continue
                
                # 제목 추출
                title_match = re.search(r'제목:\s*(.+?)\n', block)
                if not title_match:
                    continue
                title = title_match.group(1).strip()
                
                # 본문 추출
                content_match = re.search(r'게시글 본문:\n(.+?)\n-{80}', block, re.DOTALL)
                if not content_match:
                    continue
                content = content_match.group(1).strip()
                
                # 실제 댓글 추출
                comments_section = re.search(r'실제 댓글들:\n(.+?)\n-{80}', block, re.DOTALL)
                actual_comments = []
                if comments_section:
                    comment_lines = re.findall(r'\d+\.\s*(.+?)\n', comments_section.group(1))
                    actual_comments = [c.strip() for c in comment_lines if c.strip()]
                
                if actual_comments:
                    self.update_topic_statistics(title, content, actual_comments)
                    processed_count += 1
                    
                    if processed_count >= batch_size:
                        break
            
            self.learning_data['last_analyzed'] = datetime.now().isoformat()
            self._save_learning_data()
            
            logger.info(f"로그 파일 분석 완료: {processed_count}개 게시글 처리")
            
        except Exception as e:
            logger.error(f"로그 파일 분석 오류: {e}")
    
    def get_learning_summary(self) -> Dict:
        """학습 요약 정보"""
        try:
            topic_stats = self.learning_data.get('topic_statistics', {})
            post_pairs = self.learning_data.get('post_comment_pairs', [])
            
            return {
                'total_topics': len(topic_stats),
                'total_post_pairs': len(post_pairs),
                'total_processed': self.learning_data.get('total_processed', 0),
                'last_updated': self.learning_data.get('last_updated', 'N/A'),
                'last_analyzed': self.learning_data.get('last_analyzed', 'N/A'),
                'top_topics': sorted(
                    topic_stats.items(),
                    key=lambda x: x[1].get('comment_count', 0),
                    reverse=True
                )[:10]
            }
        except Exception as e:
            logger.error(f"학습 요약 정보 가져오기 오류: {e}")
            return {}

