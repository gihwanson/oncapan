"""
AI 댓글 생성 모듈
- OpenAI GPT를 이용한 자연스러운 댓글 생성
"""

from openai import OpenAI
import logging
import json
import os
from typing import Optional, List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AICommentGenerator:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-3.5-turbo"  # 또는 "gpt-4" 등
        self.comments_file = "collected_comments.json"
        self.analysis_file = "comment_analysis.json"
        # 댓글 예시는 필요할 때마다 로드 (최신 데이터 반영)
    
    def _load_comment_examples(self) -> List[Dict]:
        """수집된 댓글 예시 로드 (전체 데이터)"""
        try:
            # 댓글 파일에서 전체 로드
            if os.path.exists(self.comments_file):
                with open(self.comments_file, 'r', encoding='utf-8') as f:
                    comments = json.load(f)
                    return comments  # 전체 댓글 반환
            
            return []
        except Exception as e:
            logger.debug(f"댓글 예시 로드 오류: {e}")
            return []
    
    def _load_analysis(self) -> Dict:
        """댓글 분석 결과 로드"""
        try:
            if os.path.exists(self.analysis_file):
                with open(self.analysis_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except:
            return {}
    
    def _find_similar_comments(self, post_content: str, post_title: str = "", count: int = 20) -> List[str]:
        """게시글과 유사한 댓글 찾기 (키워드 기반)"""
        # 인코딩 안전 처리
        try:
            if post_content:
                if isinstance(post_content, bytes):
                    post_content = post_content.decode('utf-8', errors='ignore')
                else:
                    post_content = str(post_content).encode('utf-8', errors='ignore').decode('utf-8')
            if post_title:
                if isinstance(post_title, bytes):
                    post_title = post_title.decode('utf-8', errors='ignore')
                else:
                    post_title = str(post_title).encode('utf-8', errors='ignore').decode('utf-8')
        except:
            post_content = str(post_content) if post_content else ""
            post_title = str(post_title) if post_title else ""
        
        all_comments = self._load_comment_examples()
        if not all_comments:
            return []
        
        # 게시글에서 키워드 추출 (간단한 방법)
        try:
            content_text = (post_title + " " + post_content[:200]).lower()
        except:
            content_text = ""
        
        # 키워드 매칭 점수 계산
        scored_comments = []
        for comment_data in all_comments:
            comment = comment_data.get('content', '')
            if not comment:
                continue
            
            # 간단한 키워드 매칭 (실제로는 더 정교한 방법 사용 가능)
            score = 0
            comment_lower = comment.lower()
            
            # 공통 단어 찾기
            content_words = set(content_text.split())
            comment_words = set(comment_lower.split())
            common_words = content_words & comment_words
            
            # 너무 일반적인 단어 제외
            stop_words = {'의', '가', '을', '를', '은', '는', '이', '그', '저', '것', '수', '있', '없', '하', '되'}
            common_words = common_words - stop_words
            
            if common_words:
                score = len(common_words)
            
            scored_comments.append((score, comment))
        
        # 점수 순으로 정렬하고 상위 댓글 반환
        scored_comments.sort(reverse=True, key=lambda x: x[0])
        similar = [comment for score, comment in scored_comments[:count] if score > 0]
        
        # 유사한 댓글이 부족하면 랜덤으로 추가
        if len(similar) < count:
            import random
            remaining = [c.get('content', '') for c in all_comments if c.get('content', '') not in similar]
            random.shuffle(remaining)
            similar.extend(remaining[:count - len(similar)])
        
        return similar[:count]
    
    def _get_style_guide(self, post_content: str = "", post_title: str = "") -> str:
        """수집된 댓글을 기반으로 스타일 가이드 생성 (Few-shot Learning 강화)"""
        # 인코딩 안전 처리
        try:
            if post_content:
                if isinstance(post_content, bytes):
                    post_content = post_content.decode('utf-8', errors='ignore')
                else:
                    post_content = str(post_content).encode('utf-8', errors='ignore').decode('utf-8')
            if post_title:
                if isinstance(post_title, bytes):
                    post_title = post_title.decode('utf-8', errors='ignore')
                else:
                    post_title = str(post_title).encode('utf-8', errors='ignore').decode('utf-8')
        except:
            post_content = str(post_content) if post_content else ""
            post_title = str(post_title) if post_title else ""
        
        all_comments = self._load_comment_examples()
        analysis = self._load_analysis()
        
        if not all_comments:
            return ""
        
        # 게시글과 유사한 댓글 찾기
        similar_comments = self._find_similar_comments(post_content, post_title, count=25)
        
        # 유사한 댓글이 없으면 전체에서 랜덤 선택
        if not similar_comments:
            import random
            similar_comments = [c.get('content', '') for c in random.sample(all_comments, min(25, len(all_comments)))]
        
        # Few-shot learning을 위한 예시 구성
        examples_text = "\n".join([f"예시 {i+1}: {ex}" for i, ex in enumerate(similar_comments[:25])])
        
        # 분석 결과에서 스타일 정보 추출
        style_info = ""
        if analysis:
            if analysis.get('common_endings'):
                endings = [item['ending'] for item in analysis['common_endings'][:5]]
                style_info += f"\n자주 사용되는 어미: {', '.join(endings)}"
            
            if analysis.get('avg_length'):
                avg_len = int(analysis['avg_length'])
                style_info += f"\n평균 댓글 길이: 약 {avg_len}자"
        
        return f"""
=== 실제 사용자 댓글 학습 데이터 ===

다음은 실제 온카판 사용자들이 작성한 댓글 예시입니다. 
이 댓글들의 스타일, 어감, 표현 방식을 정확히 모방하여 댓글을 작성하세요.

{examples_text}
{style_info}

=== 작성 규칙 ===
1. 위 예시 댓글들과 거의 동일한 스타일로 작성
2. 예시에서 사용된 표현 방식, 어미, 길이를 그대로 따르기
3. 예시 댓글들처럼 자연스럽고 구어체로
4. AI처럼 보이지 않게 (예시처럼 불완전하거나 약간의 오타도 괜찮음)
5. 예시 댓글들의 평균 길이를 참고하여 비슷한 길이로 작성"""
    
    def generate_comment(self, post_content: str, post_title: str = "") -> Optional[str]:
        """게시글 내용을 바탕으로 자연스러운 댓글 생성"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 프롬프트 구성 (타 댓글 모방 강화)
                style_guide = self._get_style_guide(post_content, post_title)
                
                # 수집된 댓글이 있으면 모방 모드, 없으면 기본 모드
                all_comments = self._load_comment_examples()
                
                if all_comments and len(all_comments) >= 10:
                    # Few-shot Learning 모드: 실제 댓글을 모방
                    system_prompt = f"""당신은 온라인 커뮤니티의 일반 사용자입니다.
다음은 실제 사용자들이 작성한 댓글 예시입니다. 이 댓글들을 정확히 모방하여 작성하세요.

{style_guide}

중요:
- 위 예시 댓글들과 거의 동일한 스타일, 어감, 길이로 작성
- 예시에서 사용된 표현 방식을 그대로 따르기
- 예시처럼 자연스럽고 구어체로
- AI처럼 보이지 않게 (예시처럼 불완전하거나 약간의 오타도 괜찮음)
- 이모티콘(🙌, 👏, 😊, 😄, 😂, 🎉, ❤️, 👍 등)은 절대 사용하지 말 것
- 특수문자는 최소화 (가끔 "~", "!", "?" 정도만)"""
                else:
                    # 기본 모드: 수집된 댓글이 부족할 때
                    system_prompt = f"""당신은 온라인 커뮤니티의 일반 사용자입니다. 
게시글에 대한 댓글을 작성할 때 다음을 지켜주세요:

**절대 지켜야 할 규칙:**
1. 반드시 한글이 포함된 완전한 문장으로 작성 (최소 3자 이상)
2. 특수기호만으로는 절대 작성하지 말 것 (!, ~, ? 등만으로는 안됨)
3. 매우 짧고 간결하게 (5-30자 정도, 최대 1문장)
4. 구어체와 약간의 오타 허용 (예: "좋아요" → "좋아요~", "맞아요" → "맞아요!")
5. 감정 표현 다양화:
   - 공감: "공감합니다", "맞아요", "그렇네요"
   - 의견: "좋은 정보네요", "도움됐어요"
   - 질문: "어떻게 하면 되나요?", "진짜요?"
   - 단순 반응: "오", "와", "좋아요", "응", "ㅇㅇ"
6. AI처럼 보이지 않게:
   - 완벽한 문장보다는 약간 불완전한 느낌
   - "~요", "~네요", "~어요" 같은 구어체 어미
   - 때로는 띄어쓰기 실수 허용
7. 이모티콘 절대 금지 (🙌, 👏, 😊, 😄, 😂, 🎉, ❤️, 👍 등 모든 이모티콘 사용 금지)
8. 특수문자는 최소화 (가끔 "~", "!", "?" 정도만, 하지만 이것만으로는 안됨)
9. 도박 관련 전문 용어는 피하고 일반적인 표현만 사용
10. 너무 정중하거나 완벽한 표현 피하기

**댓글 예시 (이런 식으로 작성):**
- "좋은밤되세요" (O)
- "고생하셨어요" (O)
- "맞아요" (O)
- "!" (X - 특수기호만)
- "~" (X - 특수기호만)

{style_guide}"""
                
                # 한글 인코딩 문제 해결을 위해 안전하게 처리
                try:
                    # post_content와 post_title을 UTF-8로 안전하게 처리
                    if post_title:
                        if isinstance(post_title, bytes):
                            safe_title = post_title.decode('utf-8', errors='ignore')
                        else:
                            safe_title = str(post_title).encode('utf-8', errors='ignore').decode('utf-8')
                    else:
                        safe_title = ""
                    
                    if post_content:
                        if isinstance(post_content, bytes):
                            safe_content = post_content[:500].decode('utf-8', errors='ignore')
                        else:
                            safe_content = str(post_content[:500]).encode('utf-8', errors='ignore').decode('utf-8')
                    else:
                        safe_content = ""
                except Exception as e:
                    logger.debug(f"인코딩 처리 중 오류: {e}")
                    # 최후의 수단: 문자열로 변환 후 특수문자 제거
                    safe_title = str(post_title) if post_title else ""
                    safe_content = str(post_content[:500]) if post_content else ""
                    # 제어 문자 제거
                    safe_title = ''.join(char for char in safe_title if ord(char) >= 32 or char in '\n\r\t')
                    safe_content = ''.join(char for char in safe_content if ord(char) >= 32 or char in '\n\r\t')
                
                # Few-shot learning 강화를 위한 프롬프트
                all_comments = self._load_comment_examples()
                if all_comments and len(all_comments) >= 10:
                    user_prompt = f"""다음 게시글에 대한 댓글을 작성해주세요.

제목: {safe_title}
내용: {safe_content[:300]}

위 게시글을 읽고, 위에 제시된 실제 사용자 댓글 예시들을 정확히 모방하여 댓글을 작성하세요.
- 예시 댓글들과 동일한 스타일과 어감
- 예시 댓글들과 비슷한 길이
- 예시처럼 자연스럽고 구어체로
- 예시처럼 AI 티가 나지 않게"""
                else:
                    user_prompt = f"""다음 게시글에 대한 댓글을 작성해주세요.

제목: {safe_title}
내용: {safe_content[:300]}

위 게시글을 읽고 실제 사람이 빠르게 작성한 것처럼 매우 짧고 자연스러운 댓글 하나만 작성해주세요.

**중요 규칙:**
1. 반드시 한글이 포함된 완전한 문장으로 작성 (최소 3자 이상)
2. 특수기호만으로는 절대 작성하지 말 것 (!, ~, ? 등만으로는 안됨)
3. 5-30자 정도로 매우 짧게
4. 구어체 사용
5. 완벽하지 않아도 됨
6. AI처럼 보이지 않게
7. 이모티콘 절대 사용 금지

**댓글 예시:**
- "좋은밤되세요"
- "고생하셨어요"
- "맞아요"
- "그렇네요"

**금지 사항:**
- "!", "~", "?" 같은 특수기호만 사용 금지
- 한글 없이 특수기호만 사용 금지"""
                
                # Few-shot learning 강화: 더 많은 예시를 포함하기 위해 토큰 증가
                all_comments = self._load_comment_examples()
                max_tokens = 50 if not all_comments or len(all_comments) < 10 else 60
                
                # 프롬프트 인코딩 최종 확인 및 정리
                try:
                    # 제어 문자 제거 및 UTF-8 안전 처리
                    system_prompt = ''.join(char for char in system_prompt if ord(char) >= 32 or char in '\n\r\t')
                    user_prompt = ''.join(char for char in user_prompt if ord(char) >= 32 or char in '\n\r\t')
                    # UTF-8로 재인코딩하여 안전성 확보
                    system_prompt = system_prompt.encode('utf-8', errors='ignore').decode('utf-8')
                    user_prompt = user_prompt.encode('utf-8', errors='ignore').decode('utf-8')
                except Exception as e:
                    logger.debug(f"프롬프트 정리 중 오류: {e}")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.9,  # 모방을 위해 약간 낮춤 (일관성)
                    max_tokens=max_tokens,
                    top_p=0.95  # 다양한 선택지 유지
                )
                
                comment = response.choices[0].message.content.strip()
                
                # 이모티콘 제거
                import re
                # 이모티콘 패턴 제거 (유니코드 이모티콘 범위)
                emoji_pattern = re.compile("["
                    u"\U0001F600-\U0001F64F"  # emoticons
                    u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                    u"\U0001F680-\U0001F6FF"  # transport & map symbols
                    u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                    u"\U00002702-\U000027B0"
                    u"\U000024C2-\U0001F251"
                    "]+", flags=re.UNICODE)
                comment = emoji_pattern.sub('', comment).strip()
                
                # 특수기호만 있는 댓글 필터링
                # 한글, 영문, 숫자가 하나도 없으면 재생성 시도
                has_korean = bool(re.search(r'[가-힣]', comment))
                has_english = bool(re.search(r'[a-zA-Z]', comment))
                has_number = bool(re.search(r'[0-9]', comment))
                
                # 특수기호만 있는 경우 (한글/영문/숫자가 없고 특수기호만)
                if not (has_korean or has_english or has_number):
                    # 특수기호만 있는 경우 재시도
                    if attempt < max_retries - 1:
                        logger.warning(f"특수기호만 생성됨, 재시도: {comment}")
                        continue
                    else:
                        # 최후의 수단: 기본 댓글 생성
                        logger.warning(f"특수기호만 생성됨, 기본 댓글 사용: {comment}")
                        # 기본 댓글 목록에서 선택
                        default_comments = [
                            "좋아요", "맞아요", "그렇네요", "공감합니다", 
                            "좋은 정보네요", "도움됐어요", "고생하셨어요",
                            "굿밤이요", "좋은밤되세요", "수고하셨어요"
                        ]
                        comment = default_comments[attempt % len(default_comments)]
                
                # 댓글 후처리 - 더 자연스럽게
                # 너무 짧은 댓글 필터링 (특수기호만 제외하고 2자 미만)
                comment_clean = re.sub(r'[~!?.\s]', '', comment)
                if len(comment_clean) < 2:
                    if attempt < max_retries - 1:
                        logger.warning(f"너무 짧은 댓글, 재시도: {comment}")
                        continue
                
                # 너무 길면 자르기
                if len(comment) > 40:
                    # 문장 끝에서 자르기
                    comment = comment[:40]
                    if '.' in comment or '!' in comment or '?' in comment:
                        # 마지막 문장 부호 전까지
                        for punct in ['.', '!', '?']:
                            if punct in comment:
                                comment = comment[:comment.rfind(punct)+1]
                                break
                
                # AI처럼 보이는 표현 제거
                ai_patterns = [
                    '감사합니다', '좋은 하루 되세요', '도움이 되었기를',
                    '참고하시기 바랍니다', '추가로', '또한'
                ]
                for pattern in ai_patterns:
                    if pattern in comment:
                        # 패턴 제거 또는 대체
                        comment = comment.replace(pattern, '').strip()
                
                # 최종 검증: 의미있는 댓글인지 확인
                comment_clean_final = re.sub(r'[~!?.\s]', '', comment)
                if len(comment_clean_final) < 2:
                    if attempt < max_retries - 1:
                        logger.warning(f"최종 검증 실패, 재시도: {comment}")
                        continue
                    else:
                        # 기본 댓글 사용
                        default_comments = [
                            "좋아요", "맞아요", "그렇네요", "공감합니다"
                        ]
                        comment = default_comments[0]
                
                logger.info(f"댓글 생성 완료: {comment}")
                return comment
                
            except Exception as e:
                error_msg = str(e)
                # 인코딩 오류인 경우 더 자세한 정보
                if 'ascii' in error_msg or 'encode' in error_msg.lower():
                    logger.error(f"댓글 생성 오류 (시도 {attempt + 1}/{max_retries}): 인코딩 문제 - 게시글 내용을 확인하세요")
                else:
                    logger.error(f"댓글 생성 오류 (시도 {attempt + 1}/{max_retries}): {error_msg}")
                
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # 지수 백오프
                    continue
                return None
        
        return None
    
    def can_generate_comment(self, post_content: str) -> bool:
        """게시글 내용이 댓글 생성 가능한지 판단"""
        try:
            # 안전하게 문자열 처리
            if not post_content:
                return False
            
            # UTF-8로 안전하게 변환
            try:
                if isinstance(post_content, bytes):
                    safe_content = post_content.decode('utf-8', errors='ignore')
                else:
                    safe_content = str(post_content).encode('utf-8', errors='ignore').decode('utf-8')
                # 제어 문자 제거
                safe_content = ''.join(char for char in safe_content if ord(char) >= 32 or char in '\n\r\t')
            except Exception as e:
                logger.debug(f"인코딩 처리 중 오류: {e}")
                safe_content = str(post_content)
                # 제어 문자 제거
                safe_content = ''.join(char for char in safe_content if ord(char) >= 32 or char in '\n\r\t')
            
            # 너무 짧거나 의미 없는 내용 체크
            if len(safe_content.strip()) < 10:
                return False
            
            # 특정 패턴 체크 (예: 광고, 스팸 등)
            spam_keywords = ['광고', '홍보', '링크', 'http://', 'https://']
            content_lower = safe_content.lower()
            
            # 스팸 키워드가 너무 많으면 제외
            spam_count = sum(1 for keyword in spam_keywords if keyword in content_lower)
            if spam_count > 2:
                return False
            
            return True
        except Exception as e:
            logger.warning(f"댓글 생성 가능 여부 확인 오류: {e}")
            return False

