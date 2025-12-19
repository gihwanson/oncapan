"""
AI 댓글 생성 모듈
- OpenAI API를 사용하여 자연스러운 댓글 생성
- 프롬프트 기반 생성 + 댓글 풀 fallback
- 품질 검증 및 반복 방지
- 통계 파일 저장 및 실패 원인 추적
"""

import os
import sys
import json
import time
import random
import logging
import re
from enum import Enum
from typing import List, Optional, Dict, Tuple
from datetime import datetime, date
from openai import OpenAI
from openai import APIError, APIConnectionError, RateLimitError

# 파일 락 지원
try:
    if os.name == 'nt':  # Windows
        import msvcrt
    else:  # Unix/Linux
        import fcntl
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationFailureReason(Enum):
    """검증 실패 원인"""
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    BANNED_WORD = "banned_word"
    DUPLICATE_RECENT = "duplicate_recent"
    DUPLICATE_POST = "duplicate_post"
    MULTILINE = "multiline"
    SPECIAL_CHAR_SPAM = "special_char_spam"
    BLACKLISTED = "blacklisted"
    EMPTY = "empty"


class AICommentGenerator:
    """AI 댓글 생성기"""
    
    # 금지 표현 목록
    FORBIDDEN_PHRASES = [
        '힘내세요', '화이팅', '잘 될 거예요', '괜찮아질 거예요', 
        '긍정적으로', '응원합니다', '이해합니다', '공감합니다',
        '당신의', '분명히', '결국', '이 또한 지나갈',
        '힘내', '화이팅입니다', '건승', '건승입니다',
        '할 수 있어', '잘 될 거야', '괜찮아질 거야',
        # 설명적/감탄적 표현
        '진짜', '너무', '참', '정말', '대단', '와', '아',
        # 반말 패턴
        '~야', '~지', '~네', '~어', '~아'
    ]
    
    # API 제한 설정
    DAILY_API_CALL_LIMIT = 500  # 일일 API 호출 상한
    DAILY_TOKEN_LIMIT = 200000  # 일일 토큰 상한 (200k tokens)
    
    # 통계 저장 간격 (초)
    STATS_SAVE_INTERVAL = 60  # 1분마다 저장
    
    def __init__(self, api_key: str, learning_analyzer=None, 
                 prompt_version: str = "v2", 
                 max_history: int = 50):
        """
        Args:
            api_key: OpenAI API 키
            learning_analyzer: LearningAnalyzer 인스턴스 (선택)
            prompt_version: 프롬프트 버전 (기본: v1)
            max_history: 반복 방지를 위한 최근 댓글 히스토리 크기
        """
        self.client = OpenAI(api_key=api_key)
        self.learning_analyzer = learning_analyzer
        self.prompt_version = prompt_version
        self.max_history = max_history
        self.hot_reload_interval = 300
        self.last_pool_reload = time.time()
        
        # 파일 경로 설정
        self._init_file_paths()
        
        # 반복 방지를 위한 댓글 히스토리 (전역)
        self.comment_history: List[str] = []
        
        # 게시글별 댓글 히스토리 (같은 게시글에 같은 댓글 방지)
        self.post_comment_map: Dict[str, str] = {}  # post_id -> comment
        
        # 댓글 풀 및 블랙리스트 로드
        self.comment_pool: Dict[str, List[str]] = {}
        self.blacklist: set = set()
        self._load_comment_pool()
        
        # 프롬프트 로드
        self.system_prompt = self._load_prompt(prompt_version)
        
        # 통계 로드 (재시작 후에도 누적)
        self.stats = self._load_stats()
        
        # API 사용량 추적 (일일 리셋)
        self.api_usage = self._load_api_usage()
        self._check_daily_reset()
        
        # 실패 원인 카운터
        self.failure_reasons: Dict[str, int] = {
            reason.value: 0 for reason in ValidationFailureReason
        }
        
        # 풀 모드 강제 여부 (API 제한 도달 시)
        self.force_pool_mode = False
        
        # 통계 저장 관련
        self.last_stats_save = time.time()
        self.stats_dirty = False  # 통계 변경 여부
        
        # 좋아요 데이터 로드
        self.likes: Dict[str, bool] = {}  # post_id -> True (좋아요 누름)
        self._load_likes()
        
        logger.info(f"AICommentGenerator 초기화 완료 (프롬프트: {prompt_version}, 풀: {len(self.comment_pool)}개)")
    
    def _init_file_paths(self):
        """파일 경로 초기화"""
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        self.stats_file = os.path.join(base_path, "stats.json")
        self.comment_pool_file = os.path.join(base_path, "comment_pool.json")
        self.prompts_dir = os.path.join(base_path, "prompts")
        self.likes_file = os.path.join(base_path, "likes.json")
    
    def _load_comment_pool(self):
        """댓글 풀 파일 로드 (파일 락 사용)"""
        try:
            if os.path.exists(self.comment_pool_file):
                with open(self.comment_pool_file, 'r', encoding='utf-8') as f:
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
                    
                    # 기존 형식 호환성 유지
                    old_comments = data.get('comments', [])
                    if old_comments and isinstance(old_comments, list):
                        # 기존 형식: 단일 리스트 -> 일반 카테고리로 변환
                        self.comment_pool = {
                            '일반': old_comments,
                            **self._get_default_pool()
                        }
                        # 일반 카테고리에서 중복 제거
                        for key in self.comment_pool:
                            if key != '일반':
                                self.comment_pool[key] = [c for c in self.comment_pool[key] if c not in old_comments]
                    else:
                        # 새 형식: 유형별 딕셔너리
                        self.comment_pool = data.get('comment_pools', self._get_default_pool())
                        if not isinstance(self.comment_pool, dict):
                            self.comment_pool = self._get_default_pool()
                    
                    self.blacklist = set(data.get('blacklist', []))
                    total_comments = sum(len(pool) for pool in self.comment_pool.values())
                    logger.info(f"댓글 풀 로드 완료: {total_comments}개 댓글 ({len(self.comment_pool)}개 유형), {len(self.blacklist)}개 블랙리스트")
            else:
                # 기본 댓글 풀 사용
                self.comment_pool = self._get_default_pool()
                self._save_comment_pool()
                total_comments = sum(len(pool) for pool in self.comment_pool.values())
                logger.info(f"기본 댓글 풀 생성 완료: {total_comments}개 댓글 ({len(self.comment_pool)}개 유형)")
        except Exception as e:
            logger.error(f"댓글 풀 로드 오류: {e}")
            self.comment_pool = self._get_default_pool()
            self.blacklist = set()
    
    def _get_default_pool(self) -> Dict[str, List[str]]:
        """게시글 유형별 기본 댓글 풀"""
        return {
            '거래': [
                '쿨거하세여', '쿨거하세요', '쿨거하세영', '쿨거여', '쿨거여 ㅎ',
                '존거래하세영', '좋은거래하세요', '거래 잘 하세용', '쿨거래 하세요',
                '쿨거 하시길', '쿨거 고고', '무사거래요', '깔끔거래요',
                '쿨거하셔요', '쿨거하세용', '쿨거하시길', '쿨거하세여 ㅎ',
                '존거래요', '좋은거래요', '거래 잘 하세요', '쿨거래요'
            ],
            '돌발': [
                '무사귀환합시당', '무사귀환띠', '무사귀환가여', '건승해요',
                '무사귀환 하자구여', '돌발 무귀입니다', '무출기원합니다',
                '무사히 귀환해요', '무사귀환 합시당~', '무사귀환요',
                '위즈 무사귀환요', '위즈 무귀 가여', '위즈 무사귀환합시다',
                '돌발 무출 기원', '돌발 무사귀환요', '돌발 무귀 가즈아',
                '무귀 기원합니당', '위즈 돌발이네영', '돌발 무사귀환 가여',
                '무출 기원합니다', '무사귀환 가요', '무귀 기원합니당'
            ],
            '후기': [
                '좋은 후기네요', '후기 감사해요', '도움됐어요', '참고하겠습니다',
                '좋은 정보네요', '유용하네요', '감사합니다', '도움됐습니다',
                '좋네요', '괜찮네요', '괜찮아요', '좋아요', '좋습니다'
            ],
            '멘탈': [
                '그러게요', '쉽지 않네요', '복잡하네요', '무난하네요',
                '그렇네요', '맞네요', '그런가요', '그렇군요', '그렇죠',
                '맞아요', '그래요', '그렇습니다', '맞습니다'
            ],
            '일반': [
                '그러게요', '애매하네요', '쉽지 않네요', '복잡하네요', '무난하네요',
                '비슷합니다', '그럴듯하네요', '축하합니다', '그렇네요', '맞네요',
                '그런가요', '그렇군요', '그렇죠', '맞아요', '그래요',
                '그렇습니다', '맞습니다', '그렇네', '맞네', '그래'
            ],
            '건승': [
                '건승하세요', '건승입니다', '건승합시다', '건승이요', '건승해요',
                '건승하시길', '건승하세영', '건승하세여', '건승이네요', '건승이에영',
                '건승에에영', '건승이연', '건승하시길요', '건승하세용', '건승하셔요',
                '건승이요~', '건승합니당', '건승하자구여', '건승이네영', '건승해요~'
            ]
        }
    
    def _save_comment_pool(self):
        """댓글 풀 파일 저장 (파일 락 사용)"""
        try:
            data = {
                'comment_pools': self.comment_pool,  # 유형별 풀
                'blacklist': list(self.blacklist),
                'meta': {
                    'version': '2.0',  # 버전 업데이트
                    'last_updated': datetime.now().isoformat()
                }
            }
            temp_file = self.comment_pool_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
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
            if os.path.exists(self.comment_pool_file):
                os.replace(temp_file, self.comment_pool_file)
            else:
                os.rename(temp_file, self.comment_pool_file)
            
            logger.debug("댓글 풀 저장 완료")
        except Exception as e:
            logger.error(f"댓글 풀 저장 오류: {e}")
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
    
    def reload_comment_pool(self):
        """댓글 풀 핫리로드 (실행 중 파일 변경 반영)"""
        self._load_comment_pool()
        logger.info("댓글 풀 핫리로드 완료")
    
    def _load_stats(self) -> Dict:
        """통계 파일 로드 (재시작 후에도 누적, 파일 락 사용)"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
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
                    
                    stats = json.load(f)
                    
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
                    
                    # 누적 통계 유지
                    return {
                        'generated_total': stats.get('generated_total', 0),
                        'gpt_used': stats.get('gpt_used', 0),  # 하위 호환성
                        'classification_used': stats.get('classification_used', 0),  # 게시글 분류 사용 횟수
                        'pool_used': stats.get('pool_used', 0),
                        'skipped': stats.get('skipped', 0),
                        'validation_fail_total': stats.get('validation_fail_total', 0),
                        'regen_count': stats.get('regen_count', 0),
                        'api_errors': stats.get('api_errors', 0),
                        'last_updated': stats.get('last_updated', datetime.now().isoformat()),
                        'failure_reasons': stats.get('failure_reasons', {})
                    }
            else:
                return self._init_stats()
        except Exception as e:
            logger.error(f"통계 로드 오류: {e}")
            return self._init_stats()
    
    def _init_stats(self) -> Dict:
        """초기 통계 구조"""
        return {
            'generated_total': 0,
            'gpt_used': 0,  # 하위 호환성
            'classification_used': 0,  # 게시글 분류 사용 횟수
            'pool_used': 0,
            'skipped': 0,
            'validation_fail_total': 0,
            'regen_count': 0,
            'api_errors': 0,
            'last_updated': datetime.now().isoformat(),
            'failure_reasons': {}
        }
    
    def _save_stats(self, force: bool = False):
        """통계 파일 저장 (배치 저장, 파일 락 사용)"""
        current_time = time.time()
        
        # 강제 저장이 아니고, 간격이 안 지났고, 변경사항이 없으면 스킵
        if not force and (current_time - self.last_stats_save < self.STATS_SAVE_INTERVAL) and not self.stats_dirty:
            return
        
        try:
            self.stats['last_updated'] = datetime.now().isoformat()
            self.stats['failure_reasons'] = self.failure_reasons.copy()
            self.stats['api_usage'] = self.api_usage.copy()
            
            temp_file = self.stats_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
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
                
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
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
            if os.path.exists(self.stats_file):
                os.replace(temp_file, self.stats_file)
            else:
                os.rename(temp_file, self.stats_file)
            
            self.last_stats_save = current_time
            self.stats_dirty = False
        except Exception as e:
            logger.error(f"통계 저장 오류: {e}")
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
    
    def _load_api_usage(self) -> Dict:
        """API 사용량 로드"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    usage = data.get('api_usage', {})
                    return {
                        'calls_today': usage.get('calls_today', 0),
                        'tokens_today': usage.get('tokens_today', 0),
                        'last_reset_date': usage.get('last_reset_date', date.today().isoformat())
                    }
            return {
                'calls_today': 0,
                'tokens_today': 0,
                'last_reset_date': date.today().isoformat()
            }
        except Exception as e:
            logger.error(f"API 사용량 로드 오류: {e}")
            return {
                'calls_today': 0,
                'tokens_today': 0,
                'last_reset_date': date.today().isoformat()
            }
    
    def _check_daily_reset(self):
        """일일 리셋 확인"""
        today = date.today().isoformat()
        if self.api_usage['last_reset_date'] != today:
            self.api_usage['calls_today'] = 0
            self.api_usage['tokens_today'] = 0
            self.api_usage['last_reset_date'] = today
            self.force_pool_mode = False
            logger.info("일일 API 사용량 리셋")
    
    def _check_api_limits(self) -> bool:
        """API 제한 확인 (True: 제한 도달, False: 사용 가능)"""
        self._check_daily_reset()
        
        if (self.api_usage['calls_today'] >= self.DAILY_API_CALL_LIMIT or
            self.api_usage['tokens_today'] >= self.DAILY_TOKEN_LIMIT):
            if not self.force_pool_mode:
                logger.warning(f"API 제한 도달: 호출 {self.api_usage['calls_today']}/{self.DAILY_API_CALL_LIMIT}, "
                             f"토큰 {self.api_usage['tokens_today']}/{self.DAILY_TOKEN_LIMIT}")
                self.force_pool_mode = True
            return True
        return False
    
    def _load_prompt(self, version: str) -> str:
        """프롬프트 파일 로드"""
        try:
            prompt_file = os.path.join(self.prompts_dir, f"comment_style_{version}.txt")
            
            if os.path.exists(prompt_file):
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt = f.read().strip()
                logger.info(f"프롬프트 로드 성공: {prompt_file}")
                return prompt
            else:
                logger.warning(f"프롬프트 파일을 찾을 수 없습니다: {prompt_file}")
                return self._get_default_prompt()
        except Exception as e:
            logger.error(f"프롬프트 로드 오류: {e}")
            return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """기본 프롬프트 (댓글 후보 생성용)"""
        return """역할
너는 온라인 커뮤니티에서 흔히 보이는 짧고 무난한 반응 댓글 초안 생성기다.
토론·조언·분석을 하지 않는다.

입력

게시글 제목

게시글 본문

이미 달린 댓글 몇 개

출력 목표
커뮤니티 분위기에 묻히는 짧은 반응형 댓글 후보를 만든다.

규칙

댓글은 한 줄, 6~14자 위주로 작성

문장 완성도를 일부러 낮춰라 (구어체, 축약 허용)

조언, 판단, 해결책, 설명 금지

감탄·동조·공감 중 하나만 담아라

이모지 금지, 느낌표는 최대 1개

이미 달린 댓글과 의미·어조가 겹쳐도 되지만 문장은 달라야 한다

"깔끔함/정중함/정보성"이 느껴지면 탈락이다

작업 절차

(1) 이 게시글을 아래 유형 중 하나로만 분류한다
일상/수다 · 감정토로 · 거래 · 돌발/대기 · 결과후기 · 감탄/자랑

(2) 해당 유형에서 사람들이 흔히 쓰는 반응 패턴을 떠올린다

(3) 그 패턴 안에서 튀지 않는 댓글 후보 8개를 만든다

출력 형식

후보 댓글만 줄바꿈으로 출력

설명, 분류 결과, 코멘트 절대 출력하지 말 것"""
    
    def can_generate_comment(self, post_content: str) -> bool:
        """댓글 생성 가능 여부 확인"""
        if not post_content or len(post_content.strip()) < 3:
            return False
        return True
    
    def _extract_keywords(self, comments: List[str] = None, post_title: str = "", post_content: str = "") -> List[str]:
        """댓글, 제목, 본문에서 의미 있는 키워드 추출"""
        keywords = []
        
        # 중요 키워드 우선 검색 (게시글 제목/본문에서)
        important_keywords = [
            '건승', '쿨거', '무사귀환', '무귀', '무출', '존거래', '돌발', '위즈', 
            '뱅', '장줄', '포인트', '콩', '삽니다', '팝니다', '거래', '구매', '판매',
            '후기', '신겜', '해봄', '결과', '배송', '완료', '도착',
            '멘탈', '하아', '마렵', '힘드', '어렵', '스트레스', '고민', '힘들'
        ]
        
        combined_text = (post_title + " " + post_content).lower()
        for keyword in important_keywords:
            if keyword in combined_text:
                keywords.append(keyword)
        
        # 댓글에서 키워드 추출
        if comments:
            # 조사 목록 (제외할 단어들)
            particles = [
                '이', '가', '을', '를', '에', '의', '와', '과', '도', '만', '조차', '까지',
                '에서', '에게', '께서', '한테', '더러', '로', '으로', '처럼', '같이',
                '만큼', '보다', '부터', '까지', '조차', '마저', '은', '는', '도',
                '라도', '이라도', '이나', '이나마', '든지', '든가', '든', '조차',
                '요', '영', '여', '세영', '세요', '세요', '하세요', '하세영'
            ]
            
            # 댓글에서 의미 있는 단어 추출
            for comment in comments[:10]:
                if not comment or len(comment.strip()) < 2:
                    continue
                
                # 중요 키워드가 댓글에 있는지 확인
                for keyword in important_keywords:
                    if keyword in comment and keyword not in keywords:
                        keywords.append(keyword)
                
                # 2-5자 한글 단어 추출 (조사 제외)
                words = re.findall(r'[가-힣]{2,5}', comment)
                for word in words:
                    # 조사가 아니고, 중요 키워드가 아니며, 의미 있는 단어인 경우
                    if (word not in particles and 
                        word not in keywords and 
                        len(word) >= 2 and
                        word not in ['게시', '댓글', '작성', '조회', '추천', '비추', '목록', '이전', '다음']):
                        keywords.append(word)
        
        # 중복 제거 및 최대 10개 반환
        unique_keywords = []
        seen = set()
        for kw in keywords:
            if kw not in seen:
                unique_keywords.append(kw)
                seen.add(kw)
                if len(unique_keywords) >= 10:
                    break
        
        return unique_keywords
    
    def _detect_post_type_heuristic(self, post_content: str, post_title: str = "") -> str:
        """휴리스틱으로 게시글 유형 판단 (fallback용)"""
        combined_text = (post_title + " " + post_content).lower()
        
        # 거래 관련 키워드
        trade_keywords = ['삽니다', '팝니다', '쿨거', '포인트', '콩', '거래', '구매', '판매', '존거래']
        if any(keyword in combined_text for keyword in trade_keywords):
            return '거래'
        
        # 돌발/대기 관련 키워드
        event_keywords = ['돌발', '대기', '무사귀환', '무출', '위즈', '뱅', '장줄']
        if any(keyword in combined_text for keyword in event_keywords):
            return '돌발'
        
        # 후기 관련 키워드
        review_keywords = ['후기', '신겜', '해봄', '결과', '배송', '완료', '도착']
        if any(keyword in combined_text for keyword in review_keywords):
            return '후기'
        
        # 멘탈 관련 키워드
        mental_keywords = ['하아', '마렵', '멘탈', '힘드', '어렵', '스트레스', '고민', '힘들']
        if any(keyword in combined_text for keyword in mental_keywords):
            return '멘탈'
        
        # 기본값
        return '일반'
    
    def _validate_comment(self, comment: str, check_duplicate: bool = True, 
                         post_id: Optional[str] = None) -> Tuple[bool, Optional[ValidationFailureReason]]:
        """
        댓글 품질 검증 (새로운 규칙 적용)
        
        Args:
            comment: 검증할 댓글
            check_duplicate: 중복 체크 여부
            post_id: 게시글 ID (게시글별 중복 체크용)
        
        Returns:
            (검증 통과 여부, 실패 원인)
        """
        if not comment:
            return False, ValidationFailureReason.EMPTY
        
        cleaned = comment.strip()
        char_count = len(cleaned.replace(' ', '').replace('\n', ''))
        
        # 커뮤니티 토큰 체크 (ㅋㅋ, ㅠㅠ, ㄷㄷ, ㅎㅎ, ㅜㅜ 등)
        community_tokens = ['ㅋ', 'ㅠ', 'ㄷ', 'ㅎ', 'ㅜ', 'ㅅ', 'ㅇ']
        has_community_token = any(token in cleaned for token in community_tokens)
        
        # 1. 길이 검증 (2~20자로 완화)
        # 매우 짧은 반응도 허용, 최대 길이도 완화
        if char_count < 2:
            return False, ValidationFailureReason.TOO_SHORT
        if char_count > 20:  # 14자에서 20자로 완화
            return False, ValidationFailureReason.TOO_LONG
        
        # 2. 줄 수 검증
        if '\n' in cleaned:
            return False, ValidationFailureReason.MULTILINE
        
        # 3. 금지 표현 검증
        cleaned_lower = cleaned.lower()
        for phrase in self.FORBIDDEN_PHRASES:
            if phrase in cleaned_lower:
                return False, ValidationFailureReason.BANNED_WORD
        
        # 4. 블랙리스트 검증
        if cleaned in self.blacklist:
            return False, ValidationFailureReason.BLACKLISTED
        
        # 5. 이모지 검증 (완화 - 실제 이모지만 체크)
        # 특수문자는 커뮤니티 댓글의 자연스러운 표현이므로 검증하지 않음
        # 이모지 패턴을 더 엄격하게 (실제 이모지만)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "]+", flags=re.UNICODE)
        # 이모지가 명확하게 포함된 경우만 실패 (한 글자 이상)
        if emoji_pattern.search(cleaned) and len(emoji_pattern.findall(cleaned)) > 0:
            # 이모지가 전체 댓글의 대부분을 차지하는 경우만 실패
            emoji_chars = emoji_pattern.findall(cleaned)
            total_emoji_length = sum(len(e) for e in emoji_chars)
            if total_emoji_length > len(cleaned) * 0.5:  # 이모지가 50% 이상
                return False, ValidationFailureReason.SPECIAL_CHAR_SPAM
        
        # 7. "깔끔함/정중함/정보성" 감지 (간단한 휴리스틱)
        formal_words = ['감사합니다', '감사드립니다', '부탁드립니다', '도와주세요', 
                       '알겠습니다', '이해했습니다', '확인했습니다', '참고하겠습니다']
        if any(word in cleaned for word in formal_words):
            return False, ValidationFailureReason.BANNED_WORD
        
        # 8. 반말 감지 (존댓말만 허용)
        # 반말 패턴: ~야, ~지, ~네(반말), ~어, ~아 (문장 끝)
        # 단, "~네요", "~네영" 같은 존댓말은 허용
        if not any(word in cleaned for word in ['네요', '네영', '네여', '세요', '세영', '세여', '요', '영', '여', '합니', '드립니']):
            banmal_patterns = [
                r'[가-힣]+야$',  # "나도 곧 퇴근이야"
                r'[가-힣]+지$',  # "그렇지"
                r'[가-힣]+네$',  # "그렇네" (반말)
                r'[가-힣]+어$',  # "가봐"
                r'[가-힣]+아$',  # "가봐"
            ]
            for pattern in banmal_patterns:
                if re.search(pattern, cleaned):
                    return False, ValidationFailureReason.BANNED_WORD
        
        # 9. 설명적/감탄적 표현 감지 (완화)
        explanatory_words = ['진짜', '너무', '참', '정말', '대단', '와!', '아!']
        explanatory_count = sum(1 for word in explanatory_words if word in cleaned)
        # 2개 이상이면 실패 (너무 설명적)
        if explanatory_count >= 2:
            return False, ValidationFailureReason.BANNED_WORD
        
        # 10. 중복 확인 (옵션)
        if check_duplicate:
            # 전역 히스토리 중복 체크
            if self._is_duplicate(cleaned):
                return False, ValidationFailureReason.DUPLICATE_RECENT
            
            # 게시글별 중복 체크
            if post_id and post_id in self.post_comment_map:
                if self.post_comment_map[post_id] == cleaned:
                    return False, ValidationFailureReason.DUPLICATE_POST
        
        return True, None
    
    def _is_duplicate(self, comment: str) -> bool:
        """최근 히스토리와 중복 확인 (유사 문장도 감지)"""
        cleaned = comment.strip()
        
        # 완전 동일 체크
        if cleaned in self.comment_history:
            return True
        
        # 유사 문장 체크 (공백 제거 + 접미사 정규화)
        cleaned_normalized = re.sub(r'[요여영당]', '요', cleaned.replace(' ', ''))
        for hist_comment in self.comment_history[-20:]:  # 최근 20개만 체크
            hist_normalized = re.sub(r'[요여영당]', '요', hist_comment.replace(' ', ''))
            # 핵심 키워드가 같고 길이가 비슷하면 유사로 판단
            if cleaned_normalized == hist_normalized:
                return True
            # 핵심 토큰 비교 (쿨거, 존거래, 무사귀환 등)
            key_tokens_comment = set(re.findall(r'쿨거|존거래|무사귀환|무귀|무출|돌발|위즈', cleaned))
            key_tokens_hist = set(re.findall(r'쿨거|존거래|무사귀환|무귀|무출|돌발|위즈', hist_comment))
            if key_tokens_comment and key_tokens_comment == key_tokens_hist:
                return True
        
        return False
    
    def _add_to_history(self, comment: str, post_id: Optional[str] = None):
        """히스토리에 추가 (전역 + 게시글별)"""
        cleaned = comment.strip()
        if cleaned:
            # 전역 히스토리
            self.comment_history.append(cleaned)
            if len(self.comment_history) > self.max_history:
                self.comment_history.pop(0)
            
            # 게시글별 히스토리
            if post_id:
                self.post_comment_map[post_id] = cleaned
                # 게시글별 맵 크기 제한 (메모리 관리)
                if len(self.post_comment_map) > 1000:
                    # 가장 오래된 항목 제거 (FIFO)
                    oldest_key = next(iter(self.post_comment_map))
                    del self.post_comment_map[oldest_key]
    
    def _record_failure(self, reason: ValidationFailureReason):
        """실패 원인 기록"""
        self.failure_reasons[reason.value] = self.failure_reasons.get(reason.value, 0) + 1
        self.stats['validation_fail_total'] += 1
        self.stats_dirty = True
    
    def _generate_comment_candidates(self, post_content: str, post_title: str = "", 
                                    actual_comments: List[str] = None,
                                    max_retries: int = 2) -> List[str]:
        """OpenAI API로 댓글 후보 8개 생성 (재시도 포함)"""
        # API 제한 확인
        if self._check_api_limits():
            logger.debug("API 제한 도달로 풀 모드 사용")
            return []
        
        # 키워드 추출 (제목, 본문, 댓글에서)
        extracted_keywords = self._extract_keywords(
            comments=actual_comments,
            post_title=post_title,
            post_content=post_content
        )
        
        # 건승 키워드 감지
        combined_text = (post_title + " " + post_content).lower()
        has_geungseung = "건승" in combined_text or "건승" in extracted_keywords
        
        for attempt in range(max_retries):
            try:
                # 유저 메시지 구성
                user_message = f"게시글 제목: {post_title}\n게시글 본문: {post_content}"
                
                # 추출된 키워드 추가
                if extracted_keywords:
                    user_message += f"\n\n🔑 【중요 키워드】\n"
                    user_message += f"{', '.join(extracted_keywords[:8])}\n"
                    user_message += "\n위 키워드들을 반드시 참고하여 댓글을 생성하세요.\n"
                    user_message += "특히 '건승', '쿨거', '무사귀환', '존거래', '돌발', '위즈' 같은 키워드가 있으면 해당 키워드를 포함한 댓글을 우선 생성하세요."
                
                # 건승 키워드가 있으면 특별 지시 추가
                if has_geungseung:
                    user_message += "\n\n⚠️ 중요: 이 게시글에 '건승'이라는 키워드가 있습니다."
                    user_message += "\n반드시 '건승하세요', '건승입니다', '건승합시다', '건승이요' 같은 건승 관련 댓글을 생성하세요."
                    user_message += "\n건승 관련 표현을 포함한 댓글 후보를 우선적으로 만들어주세요."
                
                # 이미 달린 댓글 추가 (강화)
                if actual_comments and len(actual_comments) > 0:
                    filtered_comments = [
                        c for c in actual_comments 
                        if isinstance(c, str) and 2 <= len(c.strip()) <= 20
                    ]
                    if filtered_comments:
                        user_message += f"\n\n【이미 달린 실제 댓글들 - 반드시 참고하세요】\n"
                        user_message += "위 댓글들처럼 짧고 무난하게 반응만 하세요. 설명하지 마세요.\n"
                        for i, comment in enumerate(filtered_comments[:8], 1):  # 최대 8개
                            user_message += f"{i}. {comment}\n"
                        user_message += "\n위 댓글들의 톤, 길이, 스타일을 정확히 따라하세요.\n"
                        user_message += "- 반드시 존댓말 사용 (~요, ~영, ~여, ~세영 등)\n"
                        user_message += "- 설명하지 말고 짧게 반응만 (~이영, ~바리영, ~하세용 같은 패턴)\n"
                        user_message += "- '진짜', '너무', '참', '정말' 같은 설명적 표현 최소화\n"
                
                # API 호출
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.8,  # 다양성을 위해 높은 temperature
                    top_p=0.9,
                    max_tokens=120,  # 후보 8개 (각 4~12자)
                )
                
                # 사용량 추적
                self.api_usage['calls_today'] += 1
                if hasattr(response, 'usage'):
                    tokens = response.usage.total_tokens if response.usage else 0
                    self.api_usage['tokens_today'] += tokens
                
                response_text = response.choices[0].message.content.strip()
                
                # 후보 댓글 파싱 (줄바꿈으로 구분)
                candidates = []
                for line in response_text.split('\n'):
                    line = line.strip()
                    # 번호나 불필요한 문자 제거
                    line = re.sub(r'^\d+[\.\)]\s*', '', line)  # "1. " 또는 "1) " 제거
                    line = line.strip('"\'')  # 따옴표 제거
                    if line and len(line.replace(' ', '')) >= 2:  # 최소 길이 체크 (공백 제외, 2자 이상)
                        candidates.append(line)
                
                # 생성된 후보 로깅 (디버깅용)
                if candidates:
                    logger.debug(f"생성된 후보 목록: {candidates}")
                
                if candidates:
                    logger.debug(f"댓글 후보 생성 성공: {len(candidates)}개")
                    self.stats['classification_used'] = self.stats.get('classification_used', 0) + 1
                    self.stats_dirty = True
                    return candidates[:8]  # 최대 8개만 반환
                else:
                    logger.warning("생성된 후보가 없음")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        return []
                    
            except RateLimitError as e:
                logger.warning(f"Rate limit 오류 (시도 {attempt + 1}/{max_retries}): {e}")
                self.stats['api_errors'] += 1
                self.stats_dirty = True
                if attempt < max_retries - 1:
                    wait_time = 5 * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    return []
            except APIConnectionError as e:
                logger.warning(f"네트워크 오류 (시도 {attempt + 1}/{max_retries}): {e}")
                self.stats['api_errors'] += 1
                self.stats_dirty = True
                if attempt < max_retries - 1:
                    wait_time = 1 * (3 ** attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    return []
            except APIError as e:
                logger.error(f"API 오류 (시도 {attempt + 1}/{max_retries}): {e}")
                self.stats['api_errors'] += 1
                self.stats_dirty = True
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                else:
                    return []
            except Exception as e:
                logger.error(f"예상치 못한 오류 (시도 {attempt + 1}/{max_retries}): {e}")
                self.stats['api_errors'] += 1
                self.stats_dirty = True
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                else:
                    return []
        
        return []
    
    def _get_from_pool(self, post_type: str = '일반', 
                      exclude_comments: List[str] = None, 
                      post_id: Optional[str] = None) -> Optional[str]:
        """댓글 풀에서 선택 (유형별, 중복 제외, 반복 방지 강화)"""
        # 유형별 풀 선택
        if post_type not in self.comment_pool:
            post_type = '일반'
        
        type_pool = self.comment_pool.get(post_type, self.comment_pool.get('일반', []))
        
        if not type_pool:
            # 해당 유형 풀이 비어있으면 일반 풀 사용
            type_pool = self.comment_pool.get('일반', [])
        
        exclude_set = set(exclude_comments or [])
        exclude_set.update(self.comment_history)
        exclude_set.update(self.blacklist)
        
        # 게시글별 히스토리도 제외
        if post_id and post_id in self.post_comment_map:
            exclude_set.add(self.post_comment_map[post_id])
        
        # 중복 체크 (유사 문장 포함)
        available = []
        for c in type_pool:
            if c not in exclude_set and not self._is_duplicate(c):
                available.append(c)
        
        if available:
            comment = random.choice(available)
            self.stats['pool_used'] += 1
            self.stats['generated_total'] += 1
            self.stats_dirty = True
            self._save_stats()
            return comment
        
        # 풀에 사용 가능한 댓글이 없으면 히스토리 일부만 무시 (최근 10개만)
        recent_history = self.comment_history[-10:] if len(self.comment_history) > 10 else []
        exclude_set = set(exclude_comments or [])
        exclude_set.update(recent_history)
        exclude_set.update(self.blacklist)
        
        if post_id and post_id in self.post_comment_map:
            exclude_set.add(self.post_comment_map[post_id])
        
        available = []
        for c in type_pool:
            if c not in exclude_set:
                # 유사도 체크는 완화 (최근 히스토리만 체크)
                is_dup = False
                for hist in recent_history:
                    if c == hist:
                        is_dup = True
                        break
                if not is_dup:
                    available.append(c)
        
        if available:
            comment = random.choice(available)
            self.stats['pool_used'] += 1
            self.stats['generated_total'] += 1
            self.stats_dirty = True
            self._save_stats()
            logger.warning(f"댓글 풀 선택: 최근 히스토리 일부 무시 (사용 가능한 댓글 부족)")
            return comment
        
        # 그래도 없으면 블랙리스트만 제외하고 선택 (최후의 수단)
        available = [c for c in type_pool if c not in self.blacklist]
        if available:
            comment = random.choice(available)
            self.stats['pool_used'] += 1
            self.stats['generated_total'] += 1
            self.stats_dirty = True
            self._save_stats()
            logger.warning(f"댓글 풀 선택: 히스토리 무시 (사용 가능한 댓글 부족)")
            return comment
        
        return None
    
    def generate_comment_candidates_only(self, post_content: str, post_title: str = "", 
                                         actual_comments: List[str] = None) -> List[str]:
        """
        댓글 후보만 생성 (GUI에서 선택용)
        
        Args:
            post_content: 게시글 본문
            post_title: 게시글 제목
            actual_comments: 실제 댓글 목록
        
        Returns:
            댓글 후보 리스트 (최대 8개)
        """
        if not self.can_generate_comment(post_content):
            return []
        
        # AI로 댓글 후보 8개 생성
        candidates = []
        if not self.force_pool_mode:
            candidates = self._generate_comment_candidates(
                post_content, post_title, actual_comments
            )
            logger.debug(f"생성된 댓글 후보: {len(candidates)}개")
        
        # 검증 통과한 후보만 반환
        valid_candidates = []
        for candidate in candidates:
            is_valid, _ = self._validate_comment(candidate, check_duplicate=False)
            if is_valid:
                valid_candidates.append(candidate)
        
        return valid_candidates[:8]
    
    def generate_comment(self, post_content: str, post_title: str = "", 
                        actual_comments: List[str] = None,
                        post_id: Optional[str] = None) -> Optional[str]:
        """
        댓글 생성 (메인 메서드)
        - AI가 댓글 후보 8개 생성
        - 후보 중에서 검증 통과한 것 중 하나 선택
        
        Args:
            post_content: 게시글 본문
            post_title: 게시글 제목
            actual_comments: 실제 댓글 목록 (AI에게 전달하여 참고)
            post_id: 게시글 ID (게시글별 중복 방지용)
        
        Returns:
            생성된 댓글 또는 None
        """
        # 주기적 핫리로드 체크
        current_time = time.time()
        if current_time - self.last_pool_reload >= self.hot_reload_interval:
            self.reload_comment_pool()
            self.last_pool_reload = current_time
        
        # 주기적 통계 저장
        self._save_stats()
        
        if not self.can_generate_comment(post_content):
            self.stats['skipped'] += 1
            self.stats_dirty = True
            self._save_stats()
            return None
        
        # 건승 키워드 감지
        combined_text = (post_title + " " + post_content).lower()
        has_geungseung = "건승" in combined_text
        
        # 1단계: AI로 댓글 후보 8개 생성
        candidates = []
        if not self.force_pool_mode:
            candidates = self._generate_comment_candidates(
                post_content, post_title, actual_comments
            )
            logger.debug(f"생성된 댓글 후보: {len(candidates)}개")
        
        # 건승 키워드가 있고 후보가 없으면 건승 풀에서 우선 선택
        if has_geungseung and not candidates:
            logger.debug("건승 키워드 감지: 건승 풀에서 우선 선택")
            geungseung_comment = self._get_from_pool(
                post_type='건승',
                exclude_comments=[post_content] if post_content else None,
                post_id=post_id
            )
            if geungseung_comment:
                is_valid, failure_reason = self._validate_comment(geungseung_comment, check_duplicate=True, post_id=post_id)
                if is_valid:
                    self._add_to_history(geungseung_comment, post_id)
                    self.stats['pool_used'] += 1
                    self.stats['generated_total'] += 1
                    self.stats_dirty = True
                    self._save_stats()
                    return geungseung_comment
        
        # 2단계: 후보 중에서 검증 통과한 것 필터링
        valid_candidates = []
        for candidate in candidates:
            is_valid, failure_reason = self._validate_comment(
                candidate, check_duplicate=True, post_id=post_id
            )
            if is_valid:
                valid_candidates.append(candidate)
            else:
                if failure_reason:
                    logger.warning(f"후보 검증 실패: '{candidate}' (길이: {len(candidate.replace(' ', ''))}자) - {failure_reason.value}")
        
        # 3단계: 검증 통과한 후보 중에서 하나 선택
        if valid_candidates:
            # 중복 체크를 다시 한 번 수행 (히스토리와 비교)
            final_candidates = []
            for candidate in valid_candidates:
                if not self._is_duplicate(candidate):
                    final_candidates.append(candidate)
            
            if final_candidates:
                # 건승 키워드가 있으면 건승 관련 댓글 우선 선택
                if has_geungseung:
                    geungseung_candidates = [c for c in final_candidates if '건승' in c]
                    if geungseung_candidates:
                        comment = random.choice(geungseung_candidates)
                        logger.debug(f"건승 관련 댓글 선택: {comment}")
                    else:
                        comment = random.choice(final_candidates)
                else:
                    comment = random.choice(final_candidates)
                
                self._add_to_history(comment, post_id)
                self.stats['gpt_used'] += 1
                self.stats['generated_total'] += 1
                self.stats_dirty = True
                self._save_stats()
                logger.debug(f"최종 선택된 댓글: {comment}")
                return comment
        
        # 4단계: AI 생성 실패 시 풀에서 선택 (fallback)
        logger.debug("AI 생성 실패, 풀 모드로 전환")
        
        # 건승 키워드가 있으면 건승 풀 우선 사용
        if has_geungseung:
            logger.debug("건승 키워드 감지: 건승 풀 우선 사용")
            comment = self._get_from_pool(
                post_type='건승',
                exclude_comments=[post_content] if post_content else None,
                post_id=post_id
            )
            if comment:
                is_valid, failure_reason = self._validate_comment(comment, check_duplicate=True, post_id=post_id)
                if is_valid:
                    self._add_to_history(comment, post_id)
                    return comment
        
        # 휴리스틱으로 유형 판단
        fallback_type = self._detect_post_type_heuristic(post_content, post_title)
        logger.debug(f"Fallback 유형 판단: {fallback_type}")
        comment = self._get_from_pool(
            post_type=fallback_type,
            exclude_comments=[post_content] if post_content else None,
            post_id=post_id
        )
        
        if comment:
            is_valid, failure_reason = self._validate_comment(comment, check_duplicate=True, post_id=post_id)
            if is_valid:
                self._add_to_history(comment, post_id)
                return comment
            else:
                if failure_reason:
                    self._record_failure(failure_reason)
                    logger.warning(f"풀에서 가져온 댓글 검증 실패: {comment} - {failure_reason.value}")
        
        # 모든 방법 실패
        self.stats['skipped'] += 1
        self.stats_dirty = True
        self._save_stats(force=True)
        logger.warning("댓글 생성 실패: 모든 방법 시도 완료")
        return None
    
    def add_to_blacklist(self, comment: str):
        """블랙리스트에 추가"""
        self.blacklist.add(comment.strip())
        self._save_comment_pool()
        logger.info(f"블랙리스트 추가: {comment}")
    
    def get_stats(self) -> Dict:
        """통계 정보 반환"""
        stats = self.stats.copy()
        stats['failure_reasons'] = self.failure_reasons.copy()
        stats['api_usage'] = self.api_usage.copy()
        stats['force_pool_mode'] = self.force_pool_mode
        return stats
    
    def reset_history(self):
        """히스토리 초기화"""
        self.comment_history.clear()
        self.post_comment_map.clear()
        logger.info("댓글 히스토리 초기화")
    
    def save_stats_now(self):
        """통계 즉시 저장 (프로그램 종료 시 호출)"""
        self._save_stats(force=True)
    
    def _load_likes(self):
        """좋아요 데이터 로드"""
        try:
            if os.path.exists(self.likes_file):
                with open(self.likes_file, 'r', encoding='utf-8') as f:
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
                    self.likes = {k: v for k, v in data.items() if v is True}
                    
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
                    
                    logger.info(f"좋아요 데이터 로드 완료: {len(self.likes)}개")
            else:
                self.likes = {}
                logger.info("좋아요 데이터 파일이 없습니다. 새로 생성합니다.")
        except Exception as e:
            logger.error(f"좋아요 데이터 로드 오류: {e}")
            self.likes = {}
    
    def _save_likes(self):
        """좋아요 데이터 저장"""
        try:
            temp_file = self.likes_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
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
                
                json.dump(self.likes, f, ensure_ascii=False, indent=2)
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
            if os.path.exists(self.likes_file):
                os.replace(temp_file, self.likes_file)
            else:
                os.rename(temp_file, self.likes_file)
            
            logger.debug("좋아요 데이터 저장 완료")
        except Exception as e:
            logger.error(f"좋아요 데이터 저장 오류: {e}")
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
    
    def toggle_like(self, post_id: str) -> bool:
        """
        좋아요 토글 (누르기/취소)
        
        Args:
            post_id: 게시글 ID
        
        Returns:
            좋아요 상태 (True: 좋아요 누름, False: 좋아요 취소)
        """
        if not post_id:
            return False
        
        if post_id in self.likes and self.likes[post_id]:
            # 좋아요 취소
            del self.likes[post_id]
            self._save_likes()
            logger.info(f"좋아요 취소: {post_id}")
            return False
        else:
            # 좋아요 누르기
            self.likes[post_id] = True
            self._save_likes()
            logger.info(f"좋아요 누름: {post_id}")
            return True
    
    def is_liked(self, post_id: str) -> bool:
        """
        좋아요 상태 확인
        
        Args:
            post_id: 게시글 ID
        
        Returns:
            좋아요 상태 (True: 좋아요 누름, False: 좋아요 안 누름)
        """
        if not post_id:
            return False
        return self.likes.get(post_id, False)
    
    def get_likes_count(self) -> int:
        """전체 좋아요 개수 반환"""
        return len(self.likes)
