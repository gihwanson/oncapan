"""
AI 댓글 생성 모듈
- OpenAI GPT를 이용한 자연스러운 댓글 생성
- 실제 댓글 모방에 집중
"""

from openai import OpenAI
import logging
from typing import Optional, List, Dict
import datetime
import re
from collections import Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# httpx 로그 비활성화
logging.getLogger("httpx").setLevel(logging.WARNING)


class AICommentGenerator:
    def __init__(self, api_key: str, learning_analyzer=None):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-3.5-turbo"
        self.learning_analyzer = learning_analyzer  # 학습 분석기 (선택적)
    
    def generate_comment(self, post_content: str, post_title: str = "", actual_comments: List[str] = None) -> Optional[str]:
        """
        게시글 내용을 바탕으로 자연스러운 댓글 생성
        - post_title: 게시글 제목
        - post_content: 게시글 본문
        - actual_comments: 이 게시글에 실제로 달린 댓글 목록 (최우선!)
        
        주의: 실제 댓글이 없으면 None을 반환하여 댓글 작성을 건너뜁니다.
        """
        # 실제 댓글이 없으면 댓글 작성하지 않음
        if not actual_comments or len(actual_comments) == 0:
            logger.info("실제 댓글이 없는 게시글은 댓글 작성하지 않습니다.")
            return None
        
        # 본문 내용 저장 (후처리에서 사용)
        self._current_post_content = post_content
        self._current_post_title = post_title
        
        # 댓글이 적을 때(3개 이하) 본문 분석 강화 플래그
        has_few_comments = len(actual_comments) <= 3
        
        max_retries = 3
        
        # 키워드 미리 추출 (검증용)
        keywords = self._extract_keywords(actual_comments) if actual_comments else []
        
        for attempt in range(max_retries):
            try:
                # 안전한 문자열 처리
                safe_title = self._safe_string(post_title)
                safe_content = self._safe_string(post_content[:500])  # 본문은 500자로 제한
                
                # 실제 댓글이 있으면 무조건 모방 모드
                # 댓글이 적을 때는 본문 분석 강화
                comment = self._generate_with_actual_comments(
                    safe_title, safe_content, actual_comments, keywords, has_few_comments
                )
                
                if comment:
                    # 로그 간소화: 생성된 댓글만 간단히 출력
                    logger.debug(f"[시도 {attempt + 1}] 생성된 댓글: {comment}")
                    
                    # 키워드 포함 여부 확인 (댓글이 적을 때는 완화)
                    if keywords and not has_few_comments:  # 댓글이 적을 때는 키워드 검증 완화
                        if not self._validate_keywords_in_comment(comment, keywords):
                            logger.warning(f"[시도 {attempt + 1}] 키워드 미포함으로 필터링. 원본: '{comment}', 키워드: {keywords}")
                            if attempt < max_retries - 1:
                                import time
                                time.sleep(0.5)  # 재시도 대기 시간 줄임
                                continue
                            else:
                                logger.error(f"[시도 {attempt + 1}] 키워드 포함 실패. 최대 재시도 횟수 도달.")
                    
                    # 후처리
                    processed_comment = self._post_process(comment)
                    
                    # 후처리 후에도 유효한 댓글이면 반환
                    if processed_comment:
                        # 실제 댓글과의 유사도 검증 (단순 복사 방지)
                        if not self._validate_not_duplicate(processed_comment, actual_comments):
                            logger.warning(f"[시도 {attempt + 1}] 실제 댓글과 너무 유사하여 필터링. 생성: '{processed_comment}'")
                            if attempt < max_retries - 1:
                                import time
                                time.sleep(0.5)  # 재시도 대기 시간 줄임
                                continue
                            else:
                                logger.error(f"[시도 {attempt + 1}] 실제 댓글과 유사도 검증 실패. 최대 재시도 횟수 도달.")
                        
                        # 키워드 재확인 (후처리 후, 댓글이 적을 때는 완화)
                        if keywords and not has_few_comments:  # 댓글이 적을 때는 키워드 검증 완화
                            if not self._validate_keywords_in_comment(processed_comment, keywords):
                                logger.warning(f"[시도 {attempt + 1}] 후처리 후 키워드 미포함. 원본: '{comment}' -> 처리 후: '{processed_comment}', 키워드: {keywords}")
                                if attempt < max_retries - 1:
                                    import time
                                    time.sleep(0.5)  # 재시도 대기 시간 줄임
                                    continue
                                else:
                                    logger.error(f"[시도 {attempt + 1}] 후처리 후 키워드 포함 실패. 최대 재시도 횟수 도달.")
                        
                        # 디버그 로그 기록
                        self._log_generation(post_title, post_content, actual_comments, processed_comment)
                        return processed_comment
                    else:
                        # 후처리에서 필터링된 경우 재시도
                        logger.warning(f"[시도 {attempt + 1}] 후처리에서 필터링됨. 원본: '{comment}' -> None")
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(0.5)  # 재시도 대기 시간 줄임
                            continue
                        else:
                            logger.error(f"[시도 {attempt + 1}] 최대 재시도 횟수 도달. 댓글 생성 실패.")
                else:
                    logger.warning(f"[시도 {attempt + 1}] _generate_with_actual_comments가 None을 반환했습니다.")
                    if attempt < max_retries - 1:
                        logger.info(f"[시도 {attempt + 1}] 재시도 대기 중...")
                        import time
                        time.sleep(0.5)  # 재시도 대기 시간 줄임
                        continue
                    else:
                        logger.error(f"[시도 {attempt + 1}] 최대 재시도 횟수 도달. 댓글 생성 실패.")
                    
            except Exception as e:
                logger.error(f"댓글 생성 오류 (시도 {attempt + 1}/{max_retries}): {e}")
                import traceback
                logger.error(f"트레이스백: {traceback.format_exc()}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(0.5)  # 재시도 대기 시간 줄임
                    continue
                return None
        
        logger.error("모든 재시도 실패. None 반환")
        return None
    
    def _extract_keywords(self, comments: List[str], max_length: int = 10) -> List[str]:
        """댓글에서 가장 많이 나온 키워드 추출 (10자 이내 댓글만 분석)
        
        Args:
            comments: 댓글 목록
            max_length: 분석할 댓글의 최대 길이 (기본값: 10자)
        """
        # 10자 이내 댓글만 필터링
        short_comments = [c for c in comments if len(c) <= max_length]
        
        if not short_comments:
            # 10자 이내 댓글이 없으면 전체 댓글 사용
            short_comments = comments
        
        # 커뮤니티 특수 용어 사전 (우선 추출)
        special_terms = [
            '담타', '렉카', '포전', '포바', '단포바', '깊전', '댓노', '멘징',
            '골스', '오클', '느바', '크보', '믈브', '해축', '새축', '일야',
            '담배', '쌈배', '맛담', '맛점', '맛저', '맛아', '맛커', '맛런치',
            '무브', '후땡', '고우', '꿀잼', '개꿀잼', '쫄깃', '연장', '페이백',
            '추워', '춥', '감기', '한숨', '식곤증', '졸립', '런치', '점심',
            '벳계', '벳컨', '88', '16', '쿨거', '입금', '지연', '조회수',
            '핫식스', '원플원', '도핑', '돌발', '돌대기', '신라면', '코코아',
            '플핸', '오바', '마핸', '석살', '석사', '독사', '훈카', '화력',
            '햄부기', '야키토리', '무한도전', '런닝맨'
        ]
        
        all_words = []
        found_special_terms = []
        
        for comment in short_comments:
            # 특수 용어 우선 검색
            comment_lower = comment.lower()
            for term in special_terms:
                if term in comment_lower and term not in found_special_terms:
                    found_special_terms.append(term)
            
            # 띄어쓰기 기준으로 단어 분리 (우선)
            words_by_space = re.findall(r'[가-힣]+', comment)
            for word in words_by_space:
                if 2 <= len(word) <= 4:  # 2-4글자만
                    all_words.append(word)
            
            # 띄어쓰기로 분리되지 않은 경우, 한글만 추출하여 부분 문자열 추출 (보조)
            korean_text = re.sub(r'[^가-힣]', '', comment)
            if len(korean_text) > 0:
                # 2-4글자 길이의 부분 문자열 추출 (단어 경계 고려)
                for length in range(2, min(5, len(korean_text) + 1)):  # 최대 4글자
                    for i in range(len(korean_text) - length + 1):
                        word = korean_text[i:i+length]
                        if len(word) >= 2:
                            all_words.append(word)
        
        # 빈도수 계산
        word_counter = Counter(all_words)
        
        # 특수 용어는 우선 추가
        for term in found_special_terms:
            if term in word_counter:
                word_counter[term] += 10  # 가중치 부여
        
        # 제외할 일반적인 단어들 및 어미/접미사
        exclude_words = {
            '좋아요', '맞아요', '수고', '공감', '정보', '감사', '고마워', '고마워요',
            '좋아', '맞아', '그래', '그렇', '이거', '저거', '이것', '저것',
            '때문', '때문에', '그래서', '그런데', '그리고', '하지만', '그러나',
            '댓글', '게시글', '작성', '등록', '수정', '삭제', '신고',
            '오늘', '내일', '어제', '지금', '이제', '그때', '언제',
            '여기', '저기', '거기', '어디', '어디서', '어디에',
            '이렇게', '저렇게', '그렇게', '어떻게', '왜', '무엇', '무슨',
            '있어', '없어', '있네', '없네', '있어요', '없어요',
            '되네', '되네요', '되나', '되나요', '되는', '되는데',
            '가네', '가네요', '가나', '가나요', '가는', '가는데',
            '하네', '하네요', '하나', '하나요', '하는', '하는데',
            '보네', '보네요', '보나', '보나요', '보는', '보는데',
            '먹네', '먹네요', '먹나', '먹나요', '먹는', '먹는데',
            '드네', '드네요', '드나', '드나요', '드는', '드는데',
            '해야', '해야지', '해야지', '해야', '해야', '해야',
            # 어미 패턴 (강화)
            '입니', '습니', '시다', '게맞', '게되', '게하', '시길', '하셨', '하셔', '하셨어',
            '재밋', '재밌', '재밌습', '재밋습', '재밋니', '재밌니',
            '맛담배', '담배하', '고생하', '화이팅해', '저도하고', '생각',
            # 조사
            '은', '는', '이', '가', '을', '를', '의', '에', '에서', '와', '과',
            '도', '만', '조차', '까지', '부터', '에게', '한테', '께', '로', '으로',
            '처럼', '같이', '만큼', '보다', '마다', '대로', '커녕',
            # 의미 없는 단어
            '아자', '하고', '하고싶', '하고프', '하고싶네', '하고프네',
        }
        
        # 어미로 끝나는 패턴 (제외)
        exclude_endings = (
            '합니다', '니다', '네요', '해요', '이에요', '예요', '이네요', '이죠',
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
            '먹어요', '하시', '하셔', '하신', '하실', '하시면', '하시니', '하시죠',
        )
        
        # 어미로 끝나는 패턴 (제외)
        exclude_endings = (
            '합니다', '니다', '네요', '해요', '이에요', '예요', '이네요', '이죠',
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
            '먹어요', '하시', '하셔', '하신', '하실', '하시면', '하시니', '하시죠',
            '는데', '은데', '인데', '거야', '거예요', '거다', '거네', '거네요',
            '거나', '거나요', '거는', '거는데', '거니', '거니요', '거죠', '거세요',
            '하셨', '하셔', '하셨어', '하시길', '하시길요', '하시길요',
            '재밋', '재밌', '재밋습', '재밌습', '재밋니', '재밌니',
            '시길', '시길요', '시길요요', '시길요요요',
            '맛담배', '담배하', '고생하', '화이팅해', '저도하고',
        )
        
        # 한글 어미/접미사 패턴 (중복 제거)
        suffix_patterns = {
            # 2글자 어미
            '네요', '나요', '어요', '아요', '에요', '예요', '세요',
            '네', '나', '어', '아', '에', '예', '세',
            '는데', '은데', '인데',
            '고요', '구요',
            '지요', '죠',
            '어야', '아야',
            '거든', '거든요',
            '더라', '더라고',
            '던데', '던데요',
            '는군', '는군요',
            '는구', '는구나',
            '는걸', '는걸요',
            '는지', '는지요',
            '을까', '을까요',
            '을래', '을래요',
            '을게', '을게요',
            '습니다', '습니까',
        }
        
        # 어미/접미사 제외 함수
        def is_suffix(word: str) -> bool:
            """단어가 어미/접미사인지 확인"""
            # 정확히 일치하는 어미
            if word in suffix_patterns:
                return True
            
            # 어미 패턴으로 시작하거나 끝나는 경우
            suffix_start_patterns = ['입니', '습니', '시다', '게맞', '게되', '게하', '게되', '게만', '게는', '게이', '게가']
            if word.startswith(tuple(suffix_start_patterns)):
                return True
            
            # 2-4글자 단어가 어미로 끝나는 경우 (의미 있는 단어가 아닌 경우)
            if len(word) <= 4:
                # 일반적인 어미 종결어미
                suffix_endings = ['요', '네', '나', '어', '아', '에', '예', '세', '데', '죠', '까', '래', '게', '지', '군', '구', '걸', '라', '러', '로', '루', '르', '니', '다', '맞']
                if word[-1] in suffix_endings:
                    # 2글자이고 어미로 끝나는 경우
                    if len(word) == 2:
                        return True
                    # 3-4글자이고 일반적인 어미 패턴인 경우
                    if len(word) >= 3:
                        # 3글자 어미 패턴
                        if word[-2:] in ['네요', '나요', '어요', '아요', '에요', '예요', '세요', '는데', '은데', '인데', '는군', '는구', '는걸', '는지', '을까', '을래', '을게', '입니', '습니', '시다', '게맞']:
                            return True
                        # 4글자 어미 패턴
                        if len(word) == 4 and word[-3:] in ['입니다', '습니다', '게맞다', '게되다', '게하다']:
                            return True
            
            return False
        
        # 빈도수 높은 키워드 추출 (최소 2번 이상 나온 단어, 제외 단어 및 어미 제외)
        keywords = []
        for word, count in word_counter.most_common(30):  # 더 많이 확인
            # 기본 조건 체크
            if count < 2 or word in exclude_words or len(word) < 2:
                continue
            
            # 어미로 끝나는지 체크
            if word.endswith(exclude_endings):
                continue
            
            # 어미로 시작하는 패턴 체크 (입니, 습니, 시다 등) - 강화
            if word.startswith(('입니', '습니', '시다', '게맞', '게되', '게하', '시길', '하셨', '하셔', '재밋', '재밌')):
                continue
            
            # 어미로 끝나는 패턴 체크 - 강화
            if word.endswith(('하셨', '하셔', '하셨어', '시길', '시길요', '재밋', '재밌', '재밋습', '재밌습', '재밋니', '재밌니')):
                continue
            
            # 최대 길이 제한 (4글자)
            if len(word) > 4:
                continue
            
            # is_suffix 함수로 체크
            if is_suffix(word):
                continue
            
            # 조사로 시작하거나 끝나는지 체크
            if word.startswith(('은', '는', '이', '가', '을', '를', '의', '에', '에서', '와', '과', '도', '만')):
                continue
            if word.endswith(('은', '는', '이', '가', '을', '를', '의', '에', '에서', '와', '과', '도', '만')):
                continue
            
            keywords.append(word)
            if len(keywords) >= 10:  # 최대 10개
                break
        
        # 중복 제거 (긴 단어가 짧은 단어를 포함하는 경우 긴 단어 우선)
        filtered_keywords = []
        for keyword in keywords:
            is_substring = False
            for other in keywords:
                if keyword != other and keyword in other and len(other) > len(keyword):
                    is_substring = True
                    break
            if not is_substring:
                filtered_keywords.append(keyword)
        
        # 로그는 GUI에서만 표시
        
        return filtered_keywords[:3]  # 상위 3개만 반환
    
    def _generate_with_actual_comments(self, title: str, content: str, actual_comments: List[str], keywords: List[str] = None, has_few_comments: bool = False) -> Optional[str]:
        """실제 댓글을 모방하여 댓글 생성
        
        Args:
            has_few_comments: 댓글이 적을 때(3개 이하) True. 본문 분석을 더 강화함.
        """
        # 실제 댓글 목록 정리
        comments_list = []
        for comment in actual_comments:
            comment_text = comment if isinstance(comment, str) else comment.get('content', str(comment))
            if comment_text and len(comment_text.strip()) > 2:
                comments_list.append(comment_text.strip())
        
        if not comments_list:
            return None
        
        # 10자 이내 댓글만 필터링 (분석 및 모방용)
        short_comments = [c for c in comments_list if len(c) <= 10]
        if not short_comments:
            # 10자 이내 댓글이 없으면 전체 댓글 사용
            short_comments = comments_list
        
        # 키워드 추출 (10자 이내 댓글에서 가장 많이 나온 단어) - 전달받지 않은 경우에만 추출
        if keywords is None:
            keywords = self._extract_keywords(short_comments, max_length=10)
        keyword_text = ""
        if keywords:
            # 가장 많이 나온 키워드 (첫 번째 키워드가 가장 빈도가 높음)
            top_keyword = keywords[0] if keywords else None
            if top_keyword:
                keyword_text = f"\n\n**🔑 🚨 가장 중요한 키워드 (절대 필수!):**\n"
                keyword_text += f"**10자 이내 댓글들을 분석한 결과, '{top_keyword}'라는 키워드가 가장 많이 나왔습니다!**\n"
                keyword_text += f"⚠️ **절대 중요**: 생성하는 댓글에 **반드시 '{top_keyword}'를 포함**하고, 이 키워드를 중심으로 댓글을 작성하세요!\n"
                keyword_text += f"예: '{top_keyword}하세요~', '{top_keyword}가자~', '{top_keyword}합시다~' 같은 형식으로 작성하세요!\n"
                if len(keywords) > 1:
                    keyword_text += f"\n참고: 다른 키워드들 ({', '.join(keywords[1:])})도 있지만, **'{top_keyword}'가 가장 많으므로 이것을 우선 사용**하세요!"
        
        # 실제 댓글 예시 (10자 이내 댓글 우선, 최대 15개)
        # 10자 이내 댓글을 먼저 추가하고, 부족하면 전체 댓글에서 추가
        examples = short_comments[:15]
        if len(examples) < 15:
            # 10자 이내 댓글이 부족하면 전체 댓글에서 추가 (10자 초과는 제외)
            for comment in comments_list:
                if comment not in examples and len(comment) <= 10:
                    examples.append(comment)
                    if len(examples) >= 15:
                        break
        
        # 학습 데이터 활용: 실제 댓글과 함께 모두 고려
        learned_comments = []
        if self.learning_analyzer:
            try:
                # 유사 게시글 찾기 (유사도가 높은 것만)
                similar_posts = self.learning_analyzer.find_similar_posts(title, content, top_n=3)
                
                # 유사 게시글의 댓글 추가 (유사도가 높은 것만)
                for similar in similar_posts:
                    if similar.get('similarity', 0) > 0.3:  # 유사도 30% 이상만
                        learned_comments.extend(similar['post'].get('comments', [])[:2])
                
                # 주제별 댓글 가져오기 (본문과 관련 있는 키워드만)
                topic_keywords = self.learning_analyzer.extract_topic_keywords(title, content)
                # 본문에 실제로 나타나는 키워드만 필터링
                content_lower = content.lower() if content else ""
                title_lower = title.lower() if title else ""
                text_lower = f"{title_lower} {content_lower}"
                
                filtered_keywords = [kw for kw in topic_keywords if kw in text_lower]
                
                if filtered_keywords:
                    # 실제 댓글이 적을 때는 더 많이, 많을 때는 적게
                    max_topic_comments = 5 if len(comments_list) <= 3 else 3
                    topic_comments = self.learning_analyzer.get_topic_comments(filtered_keywords, max_comments=max_topic_comments)
                    learned_comments.extend(topic_comments)
                
                # 중복 제거 및 기존 댓글과 합치기
                all_comments_set = set(comments_list)
                for learned_comment in learned_comments:
                    if learned_comment and learned_comment not in all_comments_set:
                        # 학습 데이터 댓글이 실제 댓글과 너무 유사하지 않은 경우만 추가
                        is_too_similar = False
                        for actual_comment in comments_list:
                            # 유사도 체크 (간단한 포함 관계)
                            if learned_comment in actual_comment or actual_comment in learned_comment:
                                is_too_similar = True
                                break
                        
                        if not is_too_similar:
                            examples.append(learned_comment)
                            all_comments_set.add(learned_comment)
                            # 실제 댓글이 많을 때는 학습 데이터를 적게, 적을 때는 많이
                            max_total = 20 if len(comments_list) <= 3 else 18
                            if len(examples) >= max_total:
                                break
                
                if learned_comments:
                    logger.debug(f"학습 데이터에서 {len(learned_comments)}개 댓글 추가됨 (실제 댓글과 함께 고려)")
            except Exception as e:
                logger.error(f"학습 데이터 활용 오류: {e}")
        
        # 실제 댓글과 학습 데이터 댓글 구분하여 표시
        # 본문과 관련 있는 댓글과 관련 없는 댓글 구분
        content_lower = (content or "").lower()
        title_lower = (title or "").lower()
        post_text_lower = f"{title_lower} {content_lower}"
        
        # 본문과 관련 있는 댓글과 관련 없는 댓글 분리 (10자 이내 댓글 우선)
        relevant_comments = []
        irrelevant_comments = []
        
        for comment in examples:  # 10자 이내 댓글 우선 사용
            comment_lower = comment.lower()
            # 본문의 주요 키워드나 주제와 관련이 있는지 확인
            is_relevant = False
            
            # 본문에 인사말이나 하루 관련 표현이 있으면 관련 댓글
            if any(word in post_text_lower for word in ['하루', '기분', '좋은', '굿', '모닝', '굿모닝', '좋은하루', '좋은 하루']):
                if any(word in comment_lower for word in ['하루', '기분', '좋은', '굿', '모닝', '굿모닝', '좋은하루', '좋은 하루', '좋은하루', '존하루', '좋은하루', '발찬']):
                    is_relevant = True
            
            # 본문의 주요 단어가 댓글에 포함되어 있으면 관련 댓글
            if not is_relevant and content:
                # 본문에서 의미 있는 단어 추출 (2글자 이상)
                import re
                content_words = set(re.findall(r'[가-힣]{2,}', content_lower))
                comment_words = set(re.findall(r'[가-힣]{2,}', comment_lower))
                # 공통 단어가 있으면 관련 댓글
                if content_words and comment_words and content_words.intersection(comment_words):
                    is_relevant = True
            
            if is_relevant:
                relevant_comments.append(comment)
            else:
                irrelevant_comments.append(comment)
        
        # 관련 있는 댓글을 먼저 표시하고, 관련 없는 댓글은 별도로 표시
        actual_comments_text = ""
        if relevant_comments:
            actual_comments_text = "**✅ 본문과 관련 있는 댓글들 (우선 참고!):**\n"
            actual_comments_text += "\n".join([f"{i+1}. {c}" for i, c in enumerate(relevant_comments)])
        
        if irrelevant_comments:
            actual_comments_text += "\n\n**⚠️ 본문과 관련 없는 댓글들 (참고만 하고 따라쓰지 마세요!):**\n"
            actual_comments_text += "\n".join([f"{i+1}. {c}" for i, c in enumerate(irrelevant_comments, start=len(relevant_comments)+1)])
            actual_comments_text += "\n🚨 **중요**: 위 '본문과 관련 없는 댓글들'은 **절대 따라쓰지 마세요!** 이 댓글들은 본문의 맥락과 전혀 어울리지 않습니다. 오직 **본문과 관련 있는 댓글들**의 스타일만 참고하세요!"
        
        if not actual_comments_text:
            # 분류가 안 된 경우 기존 방식 사용
            actual_comments_text = "\n".join([f"{i+1}. {c}" for i, c in enumerate(comments_list[:15])])
        
        # 학습 데이터 댓글이 있으면 별도로 표시
        learned_comments_text = ""
        learned_examples = [c for c in examples if c not in comments_list[:15]]
        if learned_examples:
            learned_comments_text = "\n\n**📚 학습 데이터 댓글 (추가 참고 자료, 실제 댓글과 함께 고려!):**\n"
            learned_comments_text += "\n".join([f"  - {c}" for c in learned_examples[:8]])
            learned_comments_text += "\n⚠️ **참고**: 위 학습 데이터 댓글들은 과거 유사한 게시글의 댓글들입니다. 실제 댓글과 함께 참고하여 자연스러운 댓글을 작성하세요!"
        
        examples_text = actual_comments_text + learned_comments_text
        
        # 평균 길이 계산 (최대 10글자로 제한)
        avg_len = min(sum(len(c) for c in comments_list) // len(comments_list) if comments_list else 10, 10)
        
        # 본문에서 사용한 중요한 용어/숫자 추출 (일치성 강화용)
        important_terms = []
        if content:
            import re
            # 숫자 추출 (예: "20분", "300포" 등)
            numbers = re.findall(r'\d+[가-힣]+|\d+분|\d+포|\d+만|\d+천', content)
            if numbers:
                important_terms.extend(numbers)
            
            # 커뮤니티 특수 용어 추출 (예: "담타", "렉카", "포전" 등)
            special_terms = ['담타', '렉카', '포전', '포바', '단포바', '깊전', '댓노', '멘징', 
                           '골스', '오클', '느바', '크보', '믈브', '해축', '새축', '일야',
                           '담배', '쌈배', '맛담', '맛점', '맛저', '맛아', '맛커']
            for term in special_terms:
                if term in content and term not in important_terms:
                    important_terms.append(term)
        
        # 본문 용어/숫자 지시 추가
        terms_instruction = ""
        if important_terms:
            terms_instruction = f"\n\n🚨 **본문에서 사용한 용어/숫자 (반드시 댓글에도 동일하게 사용!):**\n"
            terms_instruction += f"본문에 다음 용어/숫자가 있습니다: **{', '.join(set(important_terms[:5]))}**\n"
            terms_instruction += "⚠️ **절대 중요**: 댓글을 작성할 때 이 용어/숫자를 **그대로 사용**하거나 **포함**하세요!\n"
            terms_instruction += "- 예: 본문에 '담타'가 있으면 댓글도 '담타' 사용 (❌ '담배'로 바꾸지 마세요!)\n"
            terms_instruction += "- 예: 본문에 '20분'이 있으면 댓글도 '20분' 포함 (❌ '분'만 언급하지 마세요!)\n"
        
        # 게시글 제목과 본문 정보 구성
        post_context = ""
        if title or content:
            post_context = "\n\n**📄 게시글 정보 (맥락 파악용):**\n"
            if title:
                post_context += f"제목: {title}\n"
            if content:
                # 댓글이 적을 때는 본문을 더 길게 제공 (맥락 이해 강화)
                if has_few_comments:
                    # 댓글이 적을 때는 본문 전체 또는 최대 500자까지 제공
                    content_preview = content[:500] + ("..." if len(content) > 500 else "")
                    post_context += f"본문: {content_preview}\n"
                    post_context += "\n🚨 **매우 중요 (댓글이 적은 게시글)**:\n"
                    post_context += "1. 위 게시글의 **전체 맥락과 의미**를 완전히 이해하세요!\n"
                    post_context += "2. 게시글 작성자가 **무엇을 말하고 있는지**, **어떤 상황인지** 파악하세요!\n"
                    post_context += "3. 단순히 키워드만 반복하지 마세요! (예: '헤비합니다'라는 본문에 '헤비요!' 같은 단순 반복 금지)\n"
                    post_context += "4. 게시글의 **의도와 맥락을 이해한 후** 그에 맞는 **공감이나 의견**을 표현하세요!\n"
                    post_context += "5. 예시:\n"
                    post_context += "   - 본문: '고기만이나 혼합은 레알 헤비합니다' → ❌ '헤비요!' (단순 반복)\n"
                    post_context += "   - 본문: '고기만이나 혼합은 레알 헤비합니다' → ✅ '그렇죠 헤비하죠' 또는 '헤비하긴 하네요' (맥락 이해 + 공감)\n"
                    post_context += "6. 실제 댓글 스타일을 유지하되, 게시글 맥락에 맞는 **의미 있는 댓글**을 작성하세요!"
                else:
                    # 댓글이 많을 때는 기존대로 200자로 제한
                    content_preview = content[:200] + ("..." if len(content) > 200 else "")
                    post_context += f"본문: {content_preview}\n"
                    post_context += "\n⚠️ **중요**: 위 게시글의 맥락을 이해하고, 실제 댓글들의 스타일을 유지하면서 게시글 내용과 관련된 댓글을 작성하세요!"
            
            # 본문과 댓글 일치성 강화 지시 추가
            post_context += "\n\n🚨 **본문과 댓글 내용 일치성 (절대 중요!)**:\n"
            post_context += "1. **용어 일관성**: 본문에서 사용한 용어를 댓글에서도 **동일하게** 사용하세요!\n"
            post_context += "   - 예: 본문에 '담타'가 있으면 댓글도 '담타' 사용 (❌ '담배' 사용 금지)\n"
            post_context += "   - 예: 본문에 '렉카'가 있으면 댓글도 '렉카' 관련 표현 사용\n"
            post_context += "   - 예: 본문에 '석살이'가 있으면 댓글도 '석살이' 또는 '석사' 관련 표현 사용 (❌ '페이백'만 언급 금지)\n"
            post_context += "2. **숫자/구체적 정보 보존**: 본문의 숫자나 구체적 정보를 댓글에도 포함하세요!\n"
            post_context += "   - 예: 본문에 '20분'이 있으면 댓글도 '20분' 포함 (❌ '분'만 언급 금지)\n"
            post_context += "3. **주제 일치성 (절대 중요!)**: 본문의 주제와 실제 댓글의 주제가 다를 때, **본문과 관련 있는 댓글**을 우선 선택하세요!\n"
            post_context += "   - 예: 본문이 '렉'에 대한 불만이면, 실제 댓글 중 '렉카야 안돼' 같은 본문 관련 댓글 선택\n"
            post_context += "   - 예: 본문이 '기분좋은 하루 되세요' 같은 인사말이면, 실제 댓글 중 '좋은하루~', '굿모닝' 같은 본문 관련 댓글 선택\n"
            post_context += "   - ❌ **절대 금지**: 본문과 관련 없는 댓글(예: 본문이 '기분좋은 하루'인데 '지은이당' 같은 본문과 무관한 댓글)은 **절대 따라쓰지 마세요!**\n"
            post_context += "   - 🚨 **핵심 원칙**: 실제 댓글 중에서도 **본문의 맥락과 주제와 관련 있는 댓글만** 참고하고, 본문과 전혀 관계없는 댓글은 무시하세요!\n"
            post_context += "4. **본문 맥락 우선**: 실제 댓글이 본문과 관련이 없어 보여도, **반드시 본문의 맥락에 맞는** 댓글을 작성하세요!\n"
            post_context += "5. **🚫 실제 댓글 단순 복사 금지**: 실제 댓글을 그대로 복사하지 말고, 본문 맥락에 맞게 **새로운 댓글**을 작성하세요!\n"
            post_context += "6. **🚨 추천 요청에 대한 답변 (절대 중요!)**:\n"
            post_context += "   - 본문이 '추천해주세요', '추천있나요' 같은 추천을 요청하는 경우:\n"
            post_context += "     ❌ **절대 금지**: '추천드려요', '추천해요', '추천해드려요' 같은 모호한 댓글 작성!\n"
            post_context += "     ✅ **필수**: 구체적인 제품명이나 명확한 추천을 포함하거나, 실제 댓글 스타일을 따라 다른 표현 사용!\n"
            post_context += "     - 예: 본문 '스피커 추천해주세요' → ❌ '꿀템 추천드려요!' (모호함)\n"
            post_context += "     - 예: 본문 '스피커 추천해주세요' → ✅ '꿀템 사시길' 또는 '가성비는 MR4 좋음' (구체적 또는 실제 댓글 스타일)"
        
        # 커뮤니티 용어 사전 (맥락 이해용)
        community_terms = """
**📚 커뮤니티 용어 사전 (맥락 이해용):**
- 맛드: 맛있게드세요
- 맛아: 맛있는 아침
- 맛점: 맛있는 점심
- 맛저: 맛있는 저녁
- 맛담: 맛있는담배
- 맛커: 맛있는 커피
- 맛야식: 맛있는 야식
- 맛커담: 맛있는 커피와담배
- 맛대기: 맛있는 출석체크대기
- 맛포커: 맛있는 포커게임(그만큼 즐기라는뜻)
- 화력업: 활동인원이 줄은 시간에 게시글을 써서 게시판 활성화를 해보자는뜻
- 오출완: 오늘출석체크완료 (오추롼, 오출와니, 오추롼 등으로도 표현)
- 늦출: 늦은 출석체크 (늦출완: 늦은출석체크 완료)
- 깊티: 기프티콘
- 깊전: 기프티콘 전환
- 포전: 포인트전환
- 포바: 포인트바카라(포인트로바카라를 하는것)
- 댓노: 댓글노가다의 줄임말(댓글을 오래써서 노가다만큼 열심히한다는뜻)
- 댓노 파트너: 댓글만 쓰기 힘드니 유튜브나 다른 볼거리를 댓노파트너라고 함
- 댓노미: 댓글 노가다가 미래다의 줄임말
- 커피겜/커피게임: 도박사이트에서 아침에 출근시간에 입금시 커피쿠폰을줌
- 피목: 피나는 목요일의 줄임말(쓰나미가 많이 나온 날 or 역배가 많이나온날)
- 독사: 포인트바카라를 진행하는 카지노딜러
- 플줄: 플레이어의 연속등장
- 뱅줄: 뱅커의 연속등장
- 플꺾: 뱅커의 연속등장으로 다음번엔 플레이어가 나올거라 생각해서 플레이어로 꺾어배팅하는행위
- 뱅꺾: 플레이어의 연속등장으로 다음번엔 뱅커가 나올거라 생각해서 뱅커로 꺾어배팅하는행위
- 일복: 일일복권의 줄임말
- 주복: 주간복권의 줄임말
- 0포: 포인트가 0이되었다는말
- 0포족: 포인트가 0이된 사람들의 집단
- 포: 포인트의 줄임말
- 슈: 바카라의 6매
- 첫슈: 바카라 6매의 제일 첫번째 배팅
- 장작: 게시글을 쓰는행위(게시글에 댓글쓰면 포인트를 주니까 본인이 게시글을 작성했다는뜻)
- 300포: 게시글을 작성하면 주는 포인트
- 훈카판: 훈훈한 온카판의 줄임말(주로 돈을 많이 딴 유저가 딴돈의 소액을 나눠줄때 나오는 말)
- 슬롯: 카지노의 슬롯게임
- 맥스: 돈을 딸수있는 맥시멈
- 쌈배: 담배
- 굿밤: good night
- 건승: 이기라는뜻
- 대승: 크게 돈을 딴것
- 해축: 해외축구의 약자
- 새축: 새벽시간때 축구의 약자
- 느바: 미국 NBA를 약식으로 읽었을때 느바
- 크보: 한국야구 KBO를 약식으로 읽었을때 크보
- 믈브: 미국 메이저리그 MLB를 약식으로 읽었을때 믈브
- 일야: 일본야구의 약자
- 국농: 국내농구의 약자
- 남농: 남자농구
- 보농: 보지농구(성희롱이지만 여자농구를 지칭)
- 남배: 남자배구
- 여배: 여자배구
- 개리그: 한국 축구 K리그
- 아챔: 아시아 챔피언스리그의 약자
- 잡리그: 많이 접하는 1부리그가 아닌 2부 이하의 혹은 네임드 없는 나라에서 일어나는 경기
- 단폴: 한경기만 배팅
- 단폴승부: 단폴로 크게 배팅
- 다폴: 2개이상의경기에 배팅
- 로또벳: 많은 경기를 엮어서 높은 배당을 노리는 배팅
- 국밥뱃: 배팅 최소금액만 배팅(국밥가격에서 가져온듯합니다)
- 보너스/보너스 배당: 3폴더 or 5 or 7폴더를 같이 배팅시 토토사이트에서 제공하는 보너스배당금
- 똥배: 낮은배당
- 정배: 이길 확률이 높은 경기쪽에 배당
- 역배: 이길 확률이 낮은 경기쪽에 배당
- 무잡이: 무승부를 예측하고 무승부에 배팅
- 역배잡이: 역배경기를 예측하고 더 높은 배당팀에 배팅
- 강승: 강승부를 뜻하며, 평상 시 보다 많은 금액을 배팅
- 축배팅: 한경기를 축으로 잡아서 다른 경기들과 조합하는 배팅법
- 보험배팅: 다폴 경기 중 불안한 경기를 빼고 다른 경기를 조합하거나 일종의 보험이랑 같음
- 적특: 적중특례의 줄임말로 배팅한것이 무효화된다는 뜻
- 롤링: 돈을 회전시킨 총 금액
- 극장: 경기가 끝나기 직전에 승무패가 바뀌는것
- 쓰나미: 일반적으로 배당이 낮고 승리확률이 높은 팀이 졌을때 이 표현을 쓴다
- 한강: 손실 금액이 클때 한강을 언급한다
- 구중: 구라로 중계한다는뜻
- 스포: 스포일러의 약자 앞으로 벌어질 결과를 미리알고 말하는행위
- 언더: 기준점보다 아래점수
- 오버: 기준점보다 높은점수
"""
        
        # System Prompt: 실제 댓글 모방 + 게시글 맥락 반영
        system_prompt = f"""당신은 온라인 커뮤니티의 20~30대 사용자입니다.

**🚨 절대적으로 중요: 아래는 이 게시글에 실제로 달린 댓글들입니다. 이 댓글들을 모방하여 따라쓰세요!**
**핵심 원칙:**
1. **10자 이내 댓글 분석 우선**: 위 댓글들 중 **10자 이내 댓글만** 분석하여 가장 많이 나온 키워드를 찾으세요!
2. **가장 많이 나온 키워드 중심**: 10자 이내 댓글들을 분석한 결과, 가장 많이 나온 키워드를 **반드시 포함**하고 그 키워드를 중심으로 댓글을 작성하세요!
   - 예: "맛점하세요", "맛점가자~", "맛도리~~" → "맛점"이 가장 많으므로 "맛점하세요~!" 같은 형식으로 작성
3. **댓글 모방 우선**: 실제 댓글의 스타일과 표현을 그대로 모방하세요. 자체적으로 생각하지 말고 댓글을 따라쓰는 느낌으로만 작성하세요.
4. **말투만 변경**: 완전 똑같이 따라쓰는 건 아니되, 말투만 20~30대 느낌으로 바꿔서 작성하세요.
5. **맥락만 맞으면 됨**: 게시글의 흐름과 맥락만 맞으면 됩니다. 깊이 생각하지 말고 실제 댓글을 모방하세요.
6. **본문 관련 댓글 우선**: 본문의 맥락과 주제와 관련 있는 댓글만 참고하세요.

{community_terms}

{post_context}

**🚨 이 게시글에 실제로 달린 댓글들:**
{actual_comments_text if 'actual_comments_text' in locals() else examples_text}
{learned_comments_text if 'learned_comments_text' in locals() and learned_comments_text else ''}
{keyword_text}
{terms_instruction}

**🚨 절대 중요 - 댓글 선택 원칙:**
- 위 댓글들 중에서 **본문의 맥락과 주제와 관련 있는 댓글만** 참고하세요!
- 본문과 전혀 관계없는 댓글(예: 본문이 '기분좋은 하루'인데 '지은이당' 같은 댓글)은 **절대 따라쓰지 마세요!**
- 본문의 주제와 어울리는 댓글의 스타일을 참고하여, 본문 맥락에 맞는 새로운 댓글을 작성하세요!

**절대 지켜야 할 규칙:**
1. **댓글 모방 우선 (가장 중요!)**: 
   - 실제 댓글을 모방하여 따라쓰세요. 자체적으로 생각하지 말고 댓글을 따라쓰는 느낌으로만 작성하세요.
   - 실제 댓글의 스타일, 표현, 어미를 그대로 모방하되, 말투만 20~30대 느낌으로 바꿔서 작성하세요.
   - 예: 실제 댓글 "맛담바리" → 모방 "맛담하세요" 또는 "맛담가즈아" (말투만 변경)
2. **본문 관련 댓글만 참고**: 
   - **실제 댓글** 중에서도 **본문의 맥락과 주제와 관련 있는 댓글만** 참고하세요!
   - 본문과 전혀 관계없는 댓글은 절대 따라쓰지 마세요!
3. **댓글 스타일 모방**: 위 실제 댓글들의 길이, 스타일, 표현을 그대로 모방하세요
3. **맥락에 맞는 의미 있는 댓글**: 
   - ❌ **절대 금지**: 단순히 본문의 키워드만 반복 (예: 본문에 "헤비합니다" → "헤비요!" 같은 단순 반복)
   - ❌ **절대 금지**: 본문을 그대로 복사하거나 거의 그대로 사용 (예: 본문 "느바픽하러가야겟네영" → "느바픽하러가야겠어요" 같은 본문 복사)
   - ✅ **필수**: 게시글의 맥락을 이해한 후 그에 맞는 **공감이나 의견**을 표현하되, **실제 댓글의 스타일을 따라** 작성 (예: "그렇죠 헤비하죠", "헤비하긴 하네요")
   - ✅ **필수**: 실제 댓글 예시를 참고하여 **짧고 간결한** 댓글을 작성하세요 (예: "맛아하세요", "굿모닝", "느바하러가장" 같은 스타일)
   - 게시글 내용과 관련된 **의미 있는 댓글**을 작성하되, 실제 댓글들의 스타일을 유지하세요
4. **🚨 본문과 댓글 내용 일치성 (절대 중요!)**: 
   - **용어 일관성**: 본문에서 사용한 용어를 댓글에서도 **동일하게** 사용하세요!
     - 예: 본문에 "담타"가 있으면 댓글도 "담타" 사용 (❌ "담배" 사용 금지)
     - 예: 본문에 "렉카"가 있으면 댓글도 "렉카" 관련 표현 사용
   - **숫자/구체적 정보 보존**: 본문의 숫자나 구체적 정보를 댓글에도 포함하세요!
     - 예: 본문에 "20분"이 있으면 댓글도 "20분" 포함 (❌ "분"만 언급 금지)
   - **주제 일치성**: 본문의 주제와 실제 댓글의 주제가 다를 때, **본문과 관련 있는 댓글**을 우선 선택하세요!
     - 예: 본문이 "렉"에 대한 불만이면, 실제 댓글 중 "렉카야 안돼" 같은 본문 관련 댓글 선택
     - 예: 본문과 관련 없는 일반적인 댓글(예: "아프지마라")은 피하세요!
   - **🚨 본문 단순 복사 절대 금지**: 본문을 그대로 복사하거나 거의 그대로 사용하지 마세요!
     - ❌ **절대 금지**: 본문 "느바픽하러가야겟네영" → 댓글 "느바픽하러가야겠어요" (본문 복사)
     - ❌ **절대 금지**: 본문 "랄부꽉잡으세요" → 댓글 "랄부꽉 잡자!" (본문 복사)
     - ✅ **올바른 예**: 본문 "느바픽하러가야겟네영" → 댓글 "느바하러가장" (실제 댓글 스타일 참고)
     - ✅ **올바른 예**: 본문 "랄부꽉잡으세요" → 댓글 "두선모아 잡자" (실제 댓글 스타일 참고)
5. **🚨 최대 길이 제한: 반드시 10글자 이내로 작성하세요! (공백, 특수문자 포함)**
6. 실제 댓글에서 사용된 표현, 어미, 감탄사, 특수문자를 **그대로 사용**하세요
7. **🔑 키워드 포함**: 위에서 추출한 키워드가 있으면 포함하되, **단순 반복이 아닌 맥락에 맞게** 사용하세요
8. **🚫 절대 금지: 새로운 내용을 추가하거나 글을 늘어뜨리지 마세요**
9. **🚫 절대 금지: "좋아요", "맞아요", "수고하셨어요", "공감합니다", "좋은 정보네요" 등 일반적인 표현 금지**
10. **✅ 댓글 모방 방식**: 실제 댓글을 그대로 복사하지 말고, 실제 댓글의 **스타일과 표현을 모방**하여 말투만 20~30대 느낌으로 바꿔서 작성하세요!
11. **🚫 절대 금지: 영어 사용 금지**
12. **🚫 절대 금지: 이모티콘 사용 금지**
13. **반드시 한글로만 작성하세요**
14. 실제 댓글처럼 짧고 간결하게 작성하세요 (10글자 이내!)
15. **🚨 댓글이 적은 게시글 특별 주의**: 댓글이 적을 때는 본문을 더 자세히 분석하고, 단순 키워드 반복이 아닌 **게시글의 의도를 이해한 댓글**을 작성하세요!

**예시:**
- 실제 댓글: "맛점하세요", "맛점가자~", "맛도리~~", "퇴근합시다", "맛담합시다~", "아 배고프다~", "맛점갑시다~" (10자 이내)
  → 분석: "맛점"이 가장 많이 나옴 (3번)
  → ✅ 생성: "맛점하세요~!" 또는 "맛점가즈아~" (가장 많이 나온 "맛점" 키워드 중심)
- 실제 댓글: "퇴근합시다", "퇴근가즈아", "퇴근하세요" (10자 이내)
  → 분석: "퇴근"이 가장 많이 나옴
  → ✅ 생성: "퇴근하세요~" 또는 "퇴근가즈아~" (가장 많이 나온 "퇴근" 키워드 중심)
- ❌ **절대 하지 말 것**: "맛점하세요" (실제 댓글 그대로 복사), "맛점하세요..!" (실제 댓글과 거의 동일)
- ❌ **절대 하지 말 것**: "맛점 저도 참 좋아하는데요 퇴근하고 맛점해봅시다~" (너무 길게 늘림, 10자 초과)
- ❌ **절대 하지 말 것**: "맛있는거 먹읍시다 저는 탕수육!" (10자 초과이므로 분석에서 제외)

**위 게시글의 맥락을 이해하고, 실제 댓글 예시의 스타일을 참고하되, 게시글 내용과 관련된 새로운 댓글을 작성하세요!**"""
        
        # User Prompt: 게시글 맥락 + 실제 댓글 강조
        user_prompt = f"""{community_terms}

**📄 게시글 정보 (맥락 파악):**
{post_context if post_context else "게시글 정보 없음"}

**🚨 이 게시글에 실제로 달린 댓글들:**
{actual_comments_text if 'actual_comments_text' in locals() else examples_text}
{learned_comments_text if 'learned_comments_text' in locals() and learned_comments_text else ''}
{keyword_text}
{terms_instruction}

**🚨 절대 중요 - 댓글 선택 원칙:**
- 위 댓글들 중에서 **본문의 맥락과 주제와 관련 있는 댓글만** 참고하세요!
- 본문과 전혀 관계없는 댓글(예: 본문이 '기분좋은 하루'인데 '지은이당' 같은 댓글)은 **절대 따라쓰지 마세요!**
- 본문의 주제와 어울리는 댓글의 스타일을 참고하여, 본문 맥락에 맞는 새로운 댓글을 작성하세요!

**🚨 반드시 지켜야 할 규칙:**
1. **10자 이내 댓글 분석 및 가장 많이 나온 키워드 중심 (절대 중요!)**: 
   - 위 댓글들 중 **10자 이내 댓글만** 분석하여 가장 많이 나온 키워드를 찾으세요!
   - 가장 많이 나온 키워드를 **반드시 포함**하고 그 키워드를 중심으로 댓글을 작성하세요!
   - 예: "맛점하세요", "맛점가자~", "맛도리~~", "맛점갑시다~" → "맛점"이 가장 많으므로 "맛점하세요~!" 같은 형식으로 작성
   - 예: "퇴근합시다", "퇴근가즈아", "퇴근하세요" → "퇴근"이 가장 많으므로 "퇴근하세요~" 같은 형식으로 작성
2. **댓글 모방 우선**: 
   - 실제 댓글을 모방하여 따라쓰세요. 자체적으로 생각하지 말고 댓글을 따라쓰는 느낌으로만 작성하세요.
   - 실제 댓글의 스타일, 표현, 어미를 그대로 모방하되, 말투만 20~30대 느낌으로 바꿔서 작성하세요.
   - 예: 실제 댓글 "맛담바리" → 모방 "맛담하세요" 또는 "맛담가즈아" (말투만 변경)
2. **본문 관련 댓글만 참고**: 
   - **실제 댓글** 중에서도 **본문의 맥락과 주제와 관련 있는 댓글만** 참고하세요!
   - 본문과 전혀 관계없는 댓글은 절대 따라쓰지 마세요!
3. **댓글 스타일 모방**: 위 실제 댓글들의 길이, 스타일, 표현을 그대로 모방하세요
4. **댓글 모방 방식**: 
   - ✅ **필수**: 실제 댓글을 모방하여 따라쓰세요. 자체적으로 생각하지 말고 댓글을 따라쓰는 느낌으로만 작성하세요.
   - ✅ **필수**: 실제 댓글의 스타일과 표현을 그대로 모방하되, 말투만 20~30대 느낌으로 바꿔서 작성하세요.
   - ✅ **예시**: 본문 "맛담가자~" / 실제 댓글 "맛담바리", "담배좋지요~" → 생성 "맛담하세요" 또는 "맛담가즈아" (담배 관련 댓글 모방)
   - ❌ **절대 금지**: 본문을 그대로 복사하거나 거의 그대로 사용 (예: 본문 "느바픽하러가야겟네영" → "느바픽하러가야겠어요" 같은 본문 복사)
   - ❌ **절대 금지**: 자체적으로 생각해서 댓글을 작성 (예: "이것은 좋은 생각입니다" 같은 형식적인 댓글)
4. **🚨 본문과 댓글 내용 일치성 (절대 중요!)**: 
   - **용어 일관성**: 본문에서 사용한 용어를 댓글에서도 **동일하게** 사용하세요!
     - 예: 본문에 "담타"가 있으면 댓글도 "담타" 사용 (❌ "담배" 사용 금지)
     - 예: 본문에 "렉카"가 있으면 댓글도 "렉카" 관련 표현 사용
   - **숫자/구체적 정보 보존**: 본문의 숫자나 구체적 정보를 댓글에도 포함하세요!
     - 예: 본문에 "20분"이 있으면 댓글도 "20분" 포함 (❌ "분"만 언급 금지)
   - **주제 일치성**: 본문의 주제와 실제 댓글의 주제가 다를 때, **본문과 관련 있는 댓글**을 우선 선택하세요!
     - 예: 본문이 "렉"에 대한 불만이면, 실제 댓글 중 "렉카야 안돼" 같은 본문 관련 댓글 선택
     - 예: 본문과 관련 없는 일반적인 댓글(예: "아프지마라")은 피하세요!
   - **🚨 본문 단순 복사 절대 금지**: 본문을 그대로 복사하거나 거의 그대로 사용하지 마세요!
     - ❌ **절대 금지**: 본문 "느바픽하러가야겟네영" → 댓글 "느바픽하러가야겠어요" (본문 복사)
     - ❌ **절대 금지**: 본문 "랄부꽉잡으세요" → 댓글 "랄부꽉 잡자!" (본문 복사)
     - ✅ **올바른 예**: 본문 "느바픽하러가야겟네영" → 댓글 "느바하러가장" (실제 댓글 스타일 참고)
     - ✅ **올바른 예**: 본문 "랄부꽉잡으세요" → 댓글 "두선모아 잡자" (실제 댓글 스타일 참고)
   - **🚨 추천 요청에 대한 답변 (절대 중요!)**: 본문이 "추천해주세요", "추천있나요" 같은 추천을 요청하는 경우:
     - ❌ **절대 금지**: "추천드려요", "추천해요", "추천해드려요" 같은 모호한 댓글 작성!
     - ✅ **필수**: 구체적인 제품명이나 명확한 추천을 포함하거나, 실제 댓글 스타일을 따라 다른 표현 사용!
     - 예: 본문 "스피커 추천해주세요" → ❌ "꿀템 추천드려요!" (모호함)
     - 예: 본문 "스피커 추천해주세요" → ✅ "꿀템 사시길" 또는 "가성비는 MR4 좋음" (구체적 또는 실제 댓글 스타일)
5. **🚨 최대 길이 제한: 반드시 10글자 이내로 작성하세요! (공백, 특수문자 포함)**
6. **⚠️ 문장 완성도: 반드시 문장을 완전히 마무리하세요! 말이 끊기면 안 됩니다!**
   - ❌ 잘못된 예: "추워요 감기조심하세" (10글자지만 말이 끊김)
   - ✅ 올바른 예: "추워요 감기조심하세요" (10글자, 문장 완성)
   - ✅ 올바른 예: "감기조심하세요" (7글자, 문장 완성)
   - ✅ 올바른 예: "추워요 조심하세요" (8글자, 문장 완성)
7. 실제 댓글에서 사용된 표현, 어미, 감탄사, 특수문자를 **그대로 사용**하세요
8. **🔑 키워드 포함**: 위에서 추출한 키워드가 있으면 포함하되, **단순 반복이 아닌 맥락에 맞게** 사용하세요
9. **🚫 절대 금지: 새로운 내용을 추가하거나 글을 늘어뜨리지 마세요**
10. **🚫 절대 금지: "좋아요", "맞아요", "수고하셨어요", "공감합니다", "좋은 정보네요" 등 일반적인 표현 금지**
11. **✅ 댓글 모방 방식**: 실제 댓글을 그대로 복사하지 말고, 실제 댓글의 **스타일과 표현을 모방**하여 말투만 20~30대 느낌으로 바꿔서 작성하세요!
12. **🚫 절대 금지: 영어 사용 금지**
13. **🚫 절대 금지: 이모티콘 사용 금지**
14. **반드시 한글로만 작성하세요**
15. 실제 댓글처럼 짧고 간결하게 작성하세요 (10글자 이내, 문장 완성 필수!)
16. **🚨 댓글이 적은 게시글 특별 주의**: 댓글이 적을 때는 본문을 더 자세히 분석하고, 단순 키워드 반복이 아닌 **게시글의 의도를 이해한 댓글**을 작성하세요!
17. **⚠️ 문장 완성도 필수**: 댓글이 불완전하게 끊기지 않도록 완전한 문장으로 작성하세요! (예: ❌ "무한도전 보니까 웃" → ✅ "무한도전 재밌네요" 또는 "무한도전 보니까 웃겨요")

**예시:**
- 실제 댓글 (10자 이내): "맛점하세요", "맛점가자~", "맛도리~~", "퇴근합시다", "맛담합시다~", "아 배고프다~", "맛점갑시다~"
  → 분석: 10자 이내 댓글 중 "맛점"이 가장 많이 나옴 (3번: "맛점하세요", "맛점가자~", "맛점갑시다~")
  → ✅ 생성: "맛점하세요~!" 또는 "맛점가즈아~" (가장 많이 나온 "맛점" 키워드 중심으로 모방)
- 실제 댓글 (10자 이내): "퇴근합시다", "퇴근가즈아", "퇴근하세요"
  → 분석: "퇴근"이 가장 많이 나옴
  → ✅ 생성: "퇴근하세요~" 또는 "퇴근가즈아~" (가장 많이 나온 "퇴근" 키워드 중심으로 모방)
- ❌ **절대 하지 말 것**: "맛점하세요" (실제 댓글 그대로 복사)
- ❌ **절대 하지 말 것**: "맛점 저도 참 좋아하는데요 퇴근하고 맛점해봅시다~" (너무 길게 늘림, 10자 초과, 자체적으로 생각한 댓글)
- ❌ **절대 하지 말 것**: "맛있는거 먹읍시다 저는 탕수육!" (10자 초과이므로 분석에서 제외)

**위 10자 이내 댓글들을 분석하여 가장 많이 나온 키워드를 찾고, 그 키워드를 중심으로 댓글을 모방하여 작성하세요. 자체적으로 생각하지 말고 댓글을 따라쓰는 느낌으로만 작성하세요. 말투만 20~30대 느낌으로 바꿔서 작성하세요!**"""
        
        # API 호출
        try:
            # 로그 간소화
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.6,  # 댓글 모방에 집중 (낮춰서 실제 댓글 스타일을 더 정확하게 모방)
                max_tokens=12  # 10글자 이내로 제한 (한글 1글자 = 약 1-2 토큰, 여유있게 12토큰)
            )
            
            if not response or not response.choices:
                logger.error("API 응답이 비어있습니다.")
                return None
            
            comment = response.choices[0].message.content.strip()
            logger.debug(f"API 응답: '{comment}'")
            return comment
        except Exception as e:
            logger.error(f"OpenAI API 호출 오류: {e}")
            import traceback
            logger.error(f"트레이스백: {traceback.format_exc()}")
            return None
    
    def _post_process(self, comment: str) -> Optional[str]:
        """댓글 후처리 - 영어/이모티콘만 제거, 한글 있으면 통과"""
        logger.debug(f"후처리 시작: '{comment}'")
        
        # 원본 저장 (이모티콘 제거 후 한글이 사라지면 복구용)
        original_comment = comment
        
        # 먼저 한글이 있는지 확인 (한글이 없으면 필터링)
        has_korean_before = bool(re.search(r'[가-힣]', comment))
        if not has_korean_before:
            logger.warning(f"원본에 한글이 없어서 필터링: '{comment}'")
            return None
        
        # 이모티콘 제거 (더 안전한 방법: 한글을 보존하면서 이모티콘만 제거)
        # 문제가 있던 \U000024C2-\U0001F251 범위 제거하고 더 정확한 패턴 사용
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags
            u"\U00002702-\U000027B0"  # miscellaneous symbols
            u"\U0001F900-\U0001F9FF"  # supplemental symbols
            u"\U00002600-\U000026FF"  # miscellaneous symbols
            "]+", flags=re.UNICODE)
        
        # 이모티콘만 제거하고 한글은 보존
        # 한글 유니코드 범위(AC00-D7A3)는 절대 포함하지 않음
        comment_after_emoji = emoji_pattern.sub('', comment).strip()
        logger.debug(f"이모티콘 제거 후: '{comment_after_emoji}'")
        
        # 이모티콘 제거 후에도 한글이 있는지 확인
        has_korean_after_emoji = bool(re.search(r'[가-힣]', comment_after_emoji))
        if not has_korean_after_emoji:
            logger.warning(f"이모티콘 제거 후 한글이 사라짐. 원본: '{original_comment}' -> 제거 후: '{comment_after_emoji}'")
            # 이모티콘 제거를 건너뛰고 원본 사용
            comment = original_comment
        else:
            comment = comment_after_emoji
        
        # 영어 제거
        has_english = bool(re.search(r'[a-zA-Z]', comment))
        if has_english:
            comment = re.sub(r'[a-zA-Z]', '', comment).strip()
            logger.debug(f"영어 제거 후: '{comment}'")
        
        # 숫자와 점 제거 (예: "1. ", "2. ", "1.", "2" 등)
        # 앞부분의 숫자와 점, 공백 제거
        comment = re.sub(r'^\d+\.?\s*', '', comment).strip()
        # 중간이나 끝의 단독 숫자 제거 (예: "굿이에요 2" -> "굿이에요")
        comment = re.sub(r'\s+\d+$', '', comment).strip()
        comment = re.sub(r'^\d+$', '', comment).strip()  # 숫자만 있는 경우
        
        # 한글이 있는지 최종 확인
        has_korean = bool(re.search(r'[가-힣]', comment))
        if not has_korean:
            logger.warning(f"한글이 없어서 필터링: '{comment}'")
            return None
        
        # 불완전한 댓글 검증 (끝이 어색하게 끊기는 경우)
        incomplete_patterns = [
            r'보니까\s*웃$',  # "보니까 웃"
            r'보니\s*웃$',    # "보니 웃"
            r'보고\s*웃$',    # "보고 웃"
            r'\.\.\.$',       # "..."
            r'\.\.$',         # ".."
            r'\.$',           # "." (단독)
        ]
        for pattern in incomplete_patterns:
            if re.search(pattern, comment):
                logger.warning(f"불완전한 댓글 패턴 감지: '{comment}'")
                return None
        
        # 문장이 끊기는 패턴 추가 검증 (10글자 이내에서도)
        incomplete_endings_detailed = [
            ' 좋은 하', ' 좋은', ' 늘 지', ' 늘', ' 더', ' 눈물', ' 감기', ' 학', ' 말고', ' 싶다면', ' 클',
            '한 김에 더', '한 김에', '김에 더', '김에', '고 싶다면', '고 싶다', '싶다면', '싶다',
            '에서 클', '에서', '받지 말고', '받지 말', '받지', '하지 말고', '하지 말', '하지',
            '함께 학', '함께', '좋은 하', '좋은', '늘 지', '늘', '눈물', '감기', '학', '말고', '클',
            '김에 더', '김에', '싶다면', '싶다', '에서 클', '에서', '받지 말고', '받지 말', '받지',
            '하지 말고', '하지 말', '하지', '함께 학', '함께',
            ' 문제가', ' 문제', ' 가야겠어', ' 가야겠', ' 가야', ' 가', ' 버티기 힘', ' 버티기', ' 버티', ' 힘',
            ' 롤링리베는', ' 롤링리베', ' 리베는', ' 리베', ' 채굴하러 가', ' 채굴하러', ' 채굴', '하러 가',
            ' 빼야겠', ' 빼야', ' 오늘은', ' 오늘도', ' 오늘', ' 2', ' 3', ' 4', ' 5',
            ' 혹', ' 계속', ' 들', ' 게', ' 올리는게', ' 하는게', ' 가는게', ' 오는게', ' 보는게', ' 먹는게',
            ' 점', ' 점!', ' 점~', ' 점.',  # "맛점하세요!  점" 같은 경우
            ' 분', ' 분!', ' 분~', ' 분.',  # "분 4득은 미친" 같은 경우 (앞부분이 잘림)
        ]
        for ending in incomplete_endings_detailed:
            if comment.endswith(ending):
                logger.warning(f"불완전한 댓글 (끊김 감지): '{comment}'")
                return None
        
        # 반복되는 단어 패턴 감지 (예: "맛리베요~ 맛리베")
        words = comment.split()
        if len(words) >= 2:
            # 같은 단어가 반복되는 경우
            for i in range(len(words) - 1):
                if words[i] == words[i+1]:
                    logger.warning(f"반복되는 단어 감지: '{comment}'")
                    return None
            # 비슷한 단어가 반복되는 경우 (한글만 추출하여 비교)
            for i in range(len(words) - 1):
                word1_korean = re.sub(r'[^가-힣]', '', words[i])
                word2_korean = re.sub(r'[^가-힣]', '', words[i+1])
                if len(word1_korean) >= 2 and len(word2_korean) >= 2:
                    if word1_korean == word2_korean:
                        logger.warning(f"반복되는 단어 감지 (한글만): '{comment}'")
                        return None
        
        # 문장이 너무 짧거나 의미 없는 경우 (1-2글자)
        if len(comment.strip()) <= 2:
            logger.warning(f"너무 짧은 댓글: '{comment}'")
            return None
        
        # 본문이 추천을 요청하는데 댓글이 모호한 경우 필터링
        if hasattr(self, '_current_post_content') and self._current_post_content:
            post_text = (self._current_post_title or "") + " " + (self._current_post_content or "")
            # 본문에 "추천" 관련 질문이 있는지 확인
            has_recommendation_request = bool(re.search(r'추천|추천해|추천해주|추천해줘|추천있|추천해요|추천해주세요', post_text))
            
            if has_recommendation_request:
                # 댓글이 "추천드려요", "추천해요", "추천해드려요" 같은 모호한 표현만 있는지 확인
                vague_recommendation_patterns = [
                    r'추천드려요',
                    r'추천해요',
                    r'추천해드려요',
                    r'추천드립니다',
                    r'추천해드립니다',
                    r'추천해줄게',
                    r'추천해줄게요',
                ]
                
                # 댓글에 구체적인 제품명이나 명확한 추천이 있는지 확인
                has_specific_recommendation = bool(re.search(
                    r'[A-Za-z0-9]+|사시길|사세요|사봐|사보세요|사보시길|사보시죠|사보시길요|사보시길요요',
                    comment
                ))
                
                # 모호한 추천 표현만 있고 구체적인 추천이 없는 경우 필터링
                is_vague_only = False
                for pattern in vague_recommendation_patterns:
                    if re.search(pattern, comment):
                        is_vague_only = True
                        break
                
                if is_vague_only and not has_specific_recommendation:
                    logger.warning(f"본문이 추천을 요청하는데 모호한 댓글만 생성됨: '{comment}' (필터링)")
                    return None
        
        # 10글자 이내로 제한 (문장 완성도 확인)
        if len(comment) > 10:
            # 10글자로 자르되, 문장이 끊기지 않도록 처리
            truncated = comment[:10]
            # 끊긴 문장 감지: 마지막 글자가 어미의 일부인지 확인
            incomplete_endings = ['하세', '조심하세', '하시', '하셔', '하신', '하실', '하시는', '하시게', '하시는', '하시면',
                                 ' 좋은 하', ' 좋은', ' 늘 지', ' 늘', ' 더', ' 눈물', ' 감기', ' 학', ' 말고', ' 싶다면', ' 클',
                                 '한 김에 더', '한 김에', '김에 더', '김에', '고 싶다면', '고 싶다', '싶다면', '싶다',
                                 '에서 클', '에서', '받지 말고', '받지 말', '받지', '하지 말고', '하지 말', '하지',
                                 '함께 학', '함께']
            is_incomplete = False
            for ending in incomplete_endings:
                if truncated.endswith(ending):
                    is_incomplete = True
                    break
            
            if is_incomplete:
                # 문장이 끊겼다면 더 짧게 자르거나 원본에서 적절한 위치 찾기
                # 어미가 완성되는 위치 찾기
                found_complete = False
                for i in range(9, 0, -1):
                    shorter = comment[:i]
                    # 완성된 어미로 끝나는지 확인
                    if shorter.endswith(('요', '세요', '하세요', '세요', '네요', '나요', '어요', '아요', '에요', '예요', '~', '!')):
                        # 완성된 어미로 끝나더라도 불완전한 패턴이 있는지 다시 확인
                        is_still_incomplete = False
                        for ending_check in incomplete_endings:
                            if shorter.endswith(ending_check):
                                is_still_incomplete = True
                                break
                        if not is_still_incomplete:
                            comment = shorter
                            logger.debug(f"10글자 초과로 자름 (문장 완성 고려): '{comment}'")
                            found_complete = True
                            break
                
                if not found_complete:
                    # 완성된 어미를 찾지 못하면 필터링
                    logger.warning(f"10글자 초과이고 문장이 끊김: '{comment}' (필터링)")
                    return None
            else:
                # 10글자로 자르되, 자른 후에도 불완전한 패턴이 있는지 확인
                is_still_incomplete = False
                for ending_check in incomplete_endings:
                    if truncated.endswith(ending_check):
                        is_still_incomplete = True
                        break
                
                if is_still_incomplete:
                    logger.warning(f"10글자로 자른 후에도 불완전: '{truncated}' (필터링)")
                    return None
                
                comment = truncated
                logger.debug(f"10글자 초과로 자름: '{comment}'")
        
        # 문장 완성도 최종 확인
        if comment:
            # 불완전한 어미로 끝나는지 확인
            incomplete_patterns_final = [
                '하세', '조심하세', '하시', '하셔', '하신', '하실',
                ' 좋은 하', ' 좋은', ' 늘 지', ' 늘', ' 더', ' 눈물', ' 감기', ' 학', ' 말고', ' 싶다면', ' 클',
                '한 김에 더', '한 김에', '김에 더', '김에', '고 싶다면', '고 싶다', '싶다면', '싶다',
                '에서 클', '에서', '받지 말고', '받지 말', '받지', '하지 말고', '하지 말', '하지',
                '함께 학', '함께',
                ' 문제가', ' 문제', ' 가야겠어', ' 가야겠', ' 가야', ' 가', ' 버티기 힘', ' 버티기', ' 버티', ' 힘',
                ' 롤링리베는', ' 롤링리베', ' 리베는', ' 리베', ' 채굴하러 가', ' 채굴하러', ' 채굴', '하러 가',
                ' 빼야겠', ' 빼야', ' 오늘은', ' 오늘도', ' 오늘', ' 2', ' 3', ' 4', ' 5',
                '영하세요', '영하세', '영하시',  # 이상한 표현 (예: "맛리베영하세요")
                ' 혹', ' 계속', ' 들', ' 게', ' 올리는게', ' 하는게', ' 가는게', ' 오는게', ' 보는게', ' 먹는게',
                ' 점', ' 점!', ' 점~', ' 점.',  # "맛점하세요!  점" 같은 경우
                ' 분', ' 분!', ' 분~', ' 분.',  # "분 4득은 미친" 같은 경우 (앞부분이 잘림)
                '가요!', '가요~', '가요.',  # "봅시가요!" 같은 이상한 표현
                ' 먹고 싶', ' 먹고싶', ' 먹고 싶다', ' 먹고싶다',  # "저는 라면 먹고 싶" 같은 불완전한 문장
                ' 맛있게 드', ' 맛있게드', ' 맛있게 드세요', ' 맛있게드세요',  # "햄버거 맛있게 드" 같은 불완전한 문장
                ' 퇴근', ' 퇴근!', ' 퇴근~', ' 퇴근.',  # "맛점드세요! 퇴근" 같은 이상한 표현
            ]
            for pattern in incomplete_patterns_final:
                if comment.endswith(pattern):
                    logger.warning(f"문장이 불완전하게 끝남: '{comment}' (필터링)")
                    return None
            
            # 이상한 표현 패턴 감지 (예: "맛리베영하세요")
            weird_patterns = [
                r'영하세요', r'영하세', r'영하시',  # "맛리베영하세요" 같은 이상한 표현
                r'~.*~',  # 물결표가 여러 개
                r'\.\.\.',  # 점이 3개 이상
                r'\s+점\s*[!~.]*$',  # "맛점하세요!  점" 같은 경우
                r'^분\s+',  # "분 4득은 미친" 같은 경우 (앞부분이 잘림)
                r'\s+혹\s*$',  # "맛리베 즉출요 혹" 같은 경우
                r'\s+계속\s*$',  # "맛담하세요! 계속" 같은 경우
                r'\s+들\s*$',  # "부대 소리 나면 들" 같은 경우
                r'가요!$', r'가요~$', r'가요\.$',  # "봅시가요!" 같은 이상한 표현
                r'먹고\s+싶\s*$', r'먹고싶\s*$',  # "저는 라면 먹고 싶" 같은 불완전한 문장
                r'맛있게\s+드\s*$', r'맛있게드\s*$',  # "햄버거 맛있게 드" 같은 불완전한 문장
                r'!\s*퇴근', r'~\s*퇴근', r'\.\s*퇴근',  # "맛점드세요! 퇴근" 같은 이상한 표현
            ]
            for pattern in weird_patterns:
                if re.search(pattern, comment):
                    logger.warning(f"이상한 표현 패턴 감지: '{comment}' (필터링)")
                    return None
        
        logger.debug(f"후처리 완료: '{comment}' (길이: {len(comment)}자)")
        return comment.strip()
    
    def _validate_not_duplicate(self, comment: str, actual_comments: List[str]) -> bool:
        """생성된 댓글이 실제 댓글과 너무 유사한지 확인 (단순 복사 방지)"""
        if not actual_comments:
            return True  # 실제 댓글이 없으면 검증 통과
        
        # 생성된 댓글에서 특수문자 제거하여 비교
        comment_clean = re.sub(r'[~!?.,\s]', '', comment)
        comment_clean_korean = re.sub(r'[^가-힣]', '', comment_clean)
        
        for actual_comment in actual_comments:
            actual_text = actual_comment if isinstance(actual_comment, str) else actual_comment.get('content', str(actual_comment))
            if not actual_text:
                continue
            
            # 실제 댓글에서도 특수문자 제거하여 비교
            actual_clean = re.sub(r'[~!?.,\s]', '', actual_text)
            actual_clean_korean = re.sub(r'[^가-힣]', '', actual_clean)
            
            # 한글만 추출한 상태에서 비교
            if len(comment_clean_korean) > 0 and len(actual_clean_korean) > 0:
                # 완전히 동일한 경우
                if comment_clean_korean == actual_clean_korean:
                    logger.debug(f"실제 댓글과 완전히 동일: '{comment}' == '{actual_text}'")
                    return False
                
                # 한쪽이 다른 쪽을 포함하는 경우 (예: "지은이당" vs "지은이당~")
                if comment_clean_korean in actual_clean_korean or actual_clean_korean in comment_clean_korean:
                    # 길이 차이가 2글자 이하인 경우 (특수문자나 짧은 어미만 다른 경우)
                    if abs(len(comment_clean_korean) - len(actual_clean_korean)) <= 2:
                        logger.debug(f"실제 댓글과 거의 동일 (포함 관계): '{comment}' vs '{actual_text}'")
                        return False
                    
                    # 댓글이 실제 댓글의 앞부분과 동일한 경우 (예: "푹주무셨다니" vs "푹주무셨다니 좋네요")
                    if len(comment_clean_korean) < len(actual_clean_korean):
                        if actual_clean_korean.startswith(comment_clean_korean):
                            # 실제 댓글이 생성된 댓글로 시작하고, 나머지가 3글자 이하면 중복으로 간주
                            remaining = actual_clean_korean[len(comment_clean_korean):]
                            if len(remaining) <= 3:
                                logger.debug(f"실제 댓글의 앞부분과 동일: '{comment}' vs '{actual_text}'")
                                return False
                
                # 유사도가 매우 높은 경우 (90% 이상)
                if len(comment_clean_korean) > 0 and len(actual_clean_korean) > 0:
                    # 간단한 유사도 계산 (공통 문자 비율)
                    shorter = min(len(comment_clean_korean), len(actual_clean_korean))
                    longer = max(len(comment_clean_korean), len(actual_clean_korean))
                    if shorter > 0:
                        # 공통 부분 문자열 찾기
                        common_chars = 0
                        for i in range(min(len(comment_clean_korean), len(actual_clean_korean))):
                            if i < len(comment_clean_korean) and i < len(actual_clean_korean):
                                if comment_clean_korean[i] == actual_clean_korean[i]:
                                    common_chars += 1
                        
                        similarity = (common_chars / longer) * 100 if longer > 0 else 0
                        if similarity >= 80:  # 80% 이상 유사하면 중복으로 간주 (90% -> 80%로 강화)
                            logger.debug(f"실제 댓글과 유사도 {similarity:.1f}%: '{comment}' vs '{actual_text}'")
                            return False
        
        # 본문과의 유사도도 체크 (본문 단순 복사 방지)
        if hasattr(self, '_current_post_content') and self._current_post_content:
            post_content = self._current_post_content
            post_title = getattr(self, '_current_post_title', '') or ''
            post_full = f"{post_title} {post_content}"
            post_clean = re.sub(r'[~!?.,\s]', '', post_full)
            post_clean_korean = re.sub(r'[^가-힣]', '', post_clean)
            
            if len(comment_clean_korean) > 0 and len(post_clean_korean) > 0:
                # 본문의 일부가 댓글에 포함되어 있는지 확인
                # 본문의 연속된 3글자 이상이 댓글에 포함되면 본문 복사로 간주 (4글자 -> 3글자로 강화)
                for i in range(len(post_clean_korean) - 2):
                    substring = post_clean_korean[i:i+3]
                    if len(substring) >= 3 and substring in comment_clean_korean:
                        # 본문의 연속된 3글자 이상이 댓글에 포함되어 있으면 본문 복사로 간주
                        # 단, 댓글 길이가 3글자 이하이거나 본문의 20% 이상이면 더 엄격하게 체크
                        if len(comment_clean_korean) <= 3 or len(comment_clean_korean) >= len(post_clean_korean) * 0.2:
                            logger.debug(f"본문 단순 복사 감지: '{comment}' (본문 일부: '{substring}')")
                            return False
                
                # 제목과의 유사도 체크 (제목은 더 엄격하게)
                if post_title:
                    title_clean = re.sub(r'[~!?.,\s]', '', post_title)
                    title_clean_korean = re.sub(r'[^가-힣]', '', title_clean)
                    if len(title_clean_korean) > 0:
                        # 제목의 3글자 이상이 댓글에 포함되면 제목 복사로 간주
                        for i in range(len(title_clean_korean) - 2):
                            substring = title_clean_korean[i:i+3]
                            if len(substring) >= 3 and substring in comment_clean_korean:
                                # 제목의 연속된 3글자 이상이 댓글에 포함되어 있으면 제목 복사로 간주
                                logger.debug(f"제목 단순 복사 감지: '{comment}' (제목 일부: '{substring}')")
                                return False
                        
                        # 댓글이 제목과 거의 동일한 경우
                        if comment_clean_korean == title_clean_korean:
                            logger.debug(f"제목과 완전히 동일: '{comment}' == '{post_title}'")
                            return False
                        
                        # 댓글이 제목을 포함하거나 제목이 댓글을 포함하는 경우
                        if comment_clean_korean in title_clean_korean or title_clean_korean in comment_clean_korean:
                            if abs(len(comment_clean_korean) - len(title_clean_korean)) <= 2:
                                logger.debug(f"제목과 거의 동일 (포함 관계): '{comment}' vs '{post_title}'")
                                return False
                
                # 댓글이 본문의 일부를 포함하는 경우 (더 엄격하게)
                if len(comment_clean_korean) <= len(post_clean_korean):
                    # 댓글이 본문의 일부와 매우 유사한 경우
                    if comment_clean_korean in post_clean_korean:
                        # 본문에 댓글이 포함되어 있고, 댓글 길이가 본문의 30% 이상이면 본문 복사로 간주 (40% -> 30%로 더 강화)
                        if len(comment_clean_korean) >= len(post_clean_korean) * 0.3:
                            logger.debug(f"본문 단순 복사 감지 (본문 포함): '{comment}'")
                            return False
                    
                    # 댓글과 본문의 유사도 계산 (더 엄격하게)
                    # 댓글의 60% 이상이 본문에 포함되어 있으면 본문 복사로 간주 (70% -> 60%로 더 강화)
                    matched_chars = 0
                    for char in comment_clean_korean:
                        if char in post_clean_korean:
                            matched_chars += 1
                    
                    similarity = (matched_chars / len(comment_clean_korean)) * 100 if len(comment_clean_korean) > 0 else 0
                    if similarity >= 50:  # 50% 이상 유사하면 본문 복사로 간주 (60% -> 50%로 강화)
                        logger.debug(f"본문 단순 복사 감지 (유사도 {similarity:.1f}%): '{comment}'")
                        return False
                
                # 본문의 주요 구문이 댓글에 포함되는 경우 (예: "담배값 빼야겠", "채굴하러 가", "버티기 힘")
                problematic_phrases = [
                    '빼야겠', '빼야', '채굴하러', '채굴', '하러 가', '버티기 힘', '버티기', '버티', '롤링리베는', '롤링리베',
                    '사러 가야겠어', '사러 가야겠', '사러 가야', '사러 가', '가야겠어', '가야겠', '가야', '문제가', '문제',
                    '10점차는', '10점차', '점차는', '점차',  # "느바에서 10점차는" 같은 경우
                    '돈이불어나', '돈이 불어나', '불어나',  # "버티면 돈이 불어나" 같은 경우
                    '승률', '깡 승률', '포바 깡',  # "포바 깡 승률" 같은 경우
                    '또 오류', '오류네', '오류인가',  # "벳컨 또 오류네" 같은 경우
                    '영하5도', '영하5도라니', '영하5도군요',  # "오늘도 영하5도라니" 같은 경우
                    '빨래 널기', '빨래 널고', '널기 귀찮',  # "빨래 널기 귀찮" 같은 경우
                    '인덕션 켜놓고', '인덕션 사용', '켜놓고 나',  # "인덕션 켜놓고 나" 같은 경우
                    '00초에', '00시 00초',  # "올듯요! 00초에" 같은 경우
                ]
                for phrase in problematic_phrases:
                    if phrase in comment_clean_korean and phrase in post_clean_korean:
                        logger.debug(f"본문 단순 복사 감지 (구문 포함): '{comment}' (구문: '{phrase}')")
                        return False
        
        return True  # 실제 댓글과 유사하지 않으면 통과
    
    def _validate_keywords_in_comment(self, comment: str, keywords: List[str]) -> bool:
        """생성된 댓글에 키워드가 포함되어 있는지 확인 (하나만 포함되어야 함)"""
        if not keywords:
            return True  # 키워드가 없으면 검증 통과
        
        comment_korean = re.sub(r'[^가-힣]', '', comment)
        
        # 포함된 키워드 개수 확인
        included_keywords = []
        for keyword in keywords:
            if keyword in comment_korean:
                included_keywords.append(keyword)
        
        # 키워드가 하나도 없으면 실패
        if len(included_keywords) == 0:
            return False
        
        # 키워드가 여러 개 포함되면 실패 (하나만 포함되어야 함)
        if len(included_keywords) > 1:
            logger.warning(f"여러 키워드 포함됨: {included_keywords} (하나만 포함해야 함)")
            return False
        
        # 키워드가 정확히 하나만 포함되면 성공
        return True
    
    def _safe_string(self, text: str) -> str:
        """안전한 문자열 처리"""
        if not text:
            return ""
        
        try:
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='ignore')
            else:
                text = str(text).encode('utf-8', errors='ignore').decode('utf-8')
            
            # 제어 문자 제거
            text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
            return text
        except:
            return str(text) if text else ""
    
    def _log_generation(self, title: str, content: str, actual_comments: List[str], generated_comment: str):
        """디버그 로그 기록"""
        try:
            debug_log_file = "ai_debug_log.txt"
            with open(debug_log_file, 'a', encoding='utf-8') as f:
                f.write("\n" + "="*80 + "\n")
                f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] AI 댓글 생성\n")
                f.write("="*80 + "\n\n")
                
                f.write("【게시글 제목】\n")
                f.write(f"{title if title else '(제목 없음)'}\n\n")
                
                f.write("【게시글 본문】\n")
                content_preview = content[:500] if content else "(본문 없음)"
                f.write(f"{content_preview}\n")
                if content and len(content) > 500:
                    f.write(f"... (전체 {len(content)}자 중 500자만 표시)\n")
                f.write("\n")
                
                f.write("【게시글의 실제 댓글 목록】\n")
                if actual_comments and len(actual_comments) > 0:
                    f.write(f"총 {len(actual_comments)}개의 댓글이 있습니다:\n")
                    for i, comment in enumerate(actual_comments, 1):
                        comment_text = comment if isinstance(comment, str) else comment.get('content', str(comment))
                        f.write(f"  {i}. {comment_text}\n")
                else:
                    f.write("(이 게시글에는 댓글이 없습니다)\n")
                f.write("\n")
                
                f.write("【AI가 생성한 댓글】\n")
                f.write(f"{generated_comment}\n")
                f.write("\n" + "="*80 + "\n\n")
        except Exception as e:
            logger.debug(f"디버그 로그 기록 오류: {e}")
    
    def can_generate_comment(self, post_content: str) -> bool:
        """게시글 내용이 댓글 생성 가능한지 판단"""
        try:
            if not post_content:
                return False
            
            safe_content = self._safe_string(post_content)
            if len(safe_content.strip()) < 10:
                return False
            
            return True
        except:
            return False
