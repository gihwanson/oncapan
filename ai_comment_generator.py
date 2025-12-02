"""
AI 댓글 생성 모듈
- OpenAI GPT를 이용한 자연스러운 댓글 생성
- 실제 댓글 모방에 집중
"""

from openai import OpenAI
import logging
from typing import Optional, List
import datetime
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AICommentGenerator:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-3.5-turbo"
    
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
        
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # 안전한 문자열 처리
                safe_title = self._safe_string(post_title)
                safe_content = self._safe_string(post_content[:500])  # 본문은 500자로 제한
                
                # 실제 댓글이 있으면 무조건 모방 모드
                logger.info(f"[시도 {attempt + 1}] 실제 댓글 모방 모드 시작 (댓글 {len(actual_comments)}개)")
                comment = self._generate_with_actual_comments(
                    safe_title, safe_content, actual_comments
                )
                
                if comment:
                    # 생성된 댓글을 먼저 로그에 기록 (필터링 전)
                    logger.info(f"[시도 {attempt + 1}] AI가 생성한 원본 댓글: {comment}")
                    
                    # 후처리
                    processed_comment = self._post_process(comment)
                    
                    # 후처리 후에도 유효한 댓글이면 반환
                    if processed_comment:
                        # 디버그 로그 기록
                        self._log_generation(post_title, post_content, actual_comments, processed_comment)
                        return processed_comment
                    else:
                        # 후처리에서 필터링된 경우 재시도
                        logger.warning(f"[시도 {attempt + 1}] 후처리에서 필터링됨. 원본: '{comment}' -> None")
                        if attempt < max_retries - 1:
                            continue
                else:
                    logger.warning(f"[시도 {attempt + 1}] _generate_with_actual_comments가 None을 반환했습니다.")
                    if attempt < max_retries - 1:
                        logger.info(f"[시도 {attempt + 1}] 재시도 대기 중...")
                        import time
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        logger.error(f"[시도 {attempt + 1}] 최대 재시도 횟수 도달. 댓글 생성 실패.")
                    
            except Exception as e:
                logger.error(f"댓글 생성 오류 (시도 {attempt + 1}/{max_retries}): {e}")
                import traceback
                logger.error(f"트레이스백: {traceback.format_exc()}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)
                    continue
                return None
        
        logger.error("모든 재시도 실패. None 반환")
        return None
    
    def _generate_with_actual_comments(self, title: str, content: str, actual_comments: List[str]) -> Optional[str]:
        """실제 댓글을 모방하여 댓글 생성"""
        # 실제 댓글 목록 정리
        comments_list = []
        for comment in actual_comments:
            comment_text = comment if isinstance(comment, str) else comment.get('content', str(comment))
            if comment_text and len(comment_text.strip()) > 2:
                comments_list.append(comment_text.strip())
        
        if not comments_list:
            return None
        
        # 실제 댓글 예시 (최대 15개)
        examples = comments_list[:15]
        examples_text = "\n".join([f"{i+1}. {c}" for i, c in enumerate(examples)])
        
        # 평균 길이 계산
        avg_len = sum(len(c) for c in comments_list) // len(comments_list) if comments_list else 15
        
        # System Prompt: 실제 댓글 모방에만 집중
        system_prompt = f"""당신은 온라인 커뮤니티의 일반 사용자입니다.

**🚨 절대적으로 중요: 아래는 이 게시글에 실제로 달린 댓글들입니다. 반드시 이 댓글들을 똑같이 따라쓰세요! 🚨**

**실제 댓글 예시 (반드시 참고!):**
{examples_text}

**절대 지켜야 할 규칙:**
1. 위 실제 댓글들을 **똑같이 따라쓰세요** - 길이, 스타일, 표현을 거의 동일하게
2. 실제 댓글의 **정확한 길이**를 유지하세요 (약 {avg_len}자, 최대 {avg_len + 5}자까지)
3. 실제 댓글에서 사용된 표현, 어미, 감탄사, 특수문자를 **그대로 사용**하세요
4. **🚫 절대 금지: 새로운 내용을 추가하거나 글을 늘어뜨리지 마세요**
5. **🚫 절대 금지: "좋아요", "맞아요", "수고하셨어요", "공감합니다", "좋은 정보네요" 등 일반적인 표현 금지**
6. 위 실제 댓글 예시 중 하나를 **거의 그대로** 따라쓰되, 약간의 변형만 주세요 (예: "맛담요~" → "맛담요..!" 또는 "맛담요!")
7. **🚫 절대 금지: 영어 사용 금지**
8. **🚫 절대 금지: 이모티콘 사용 금지**
9. **반드시 한글로만 작성하세요**
10. 실제 댓글처럼 짧고 간결하게 작성하세요 (길게 늘리지 마세요!)

**예시:**
- 실제 댓글: "맛담요~" → 생성: "맛담요..!" 또는 "맛담요!" (거의 동일)
- 실제 댓글: "퇴근가봅시더" → 생성: "퇴근가봅시더~" 또는 "퇴근가봅시더!" (거의 동일)
- **절대 하지 말 것**: "맛담 저도 참 좋아하는데요 퇴근하고 맛담해봅시다~" (너무 길게 늘림)

**위 실제 댓글 예시를 똑같이 따라쓰되, 약간의 변형만 주세요!**"""
        
        # User Prompt: 게시글 정보 + 실제 댓글 강조
        user_prompt = f"""다음 게시글에 대한 댓글을 작성해주세요.

제목: {title}
내용: {content[:300]}

**🚨 이 게시글에 실제로 달린 댓글들 (똑같이 따라쓰세요!):**
{examples_text}

**🚨 반드시 지켜야 할 규칙:**
1. 위 실제 댓글들을 **똑같이 따라쓰세요** - 길이, 스타일, 표현을 거의 동일하게
2. 실제 댓글의 **정확한 길이**를 유지하세요 (약 {avg_len}자, 최대 {avg_len + 5}자까지)
3. 실제 댓글에서 사용된 표현, 어미, 감탄사, 특수문자를 **그대로 사용**하세요
4. **🚫 절대 금지: 새로운 내용을 추가하거나 글을 늘어뜨리지 마세요**
5. **🚫 절대 금지: "좋아요", "맞아요", "수고하셨어요", "공감합니다", "좋은 정보네요" 등 일반적인 표현 금지**
6. 위 실제 댓글 예시 중 하나를 **거의 그대로** 따라쓰되, 약간의 변형만 주세요
7. **🚫 절대 금지: 영어 사용 금지**
8. **🚫 절대 금지: 이모티콘 사용 금지**
9. **반드시 한글로만 작성하세요**
10. 실제 댓글처럼 짧고 간결하게 작성하세요 (길게 늘리지 마세요!)

**예시:**
- 실제 댓글: "맛담요~" → 생성: "맛담요..!" 또는 "맛담요!" (거의 동일)
- 실제 댓글: "퇴근가봅시더" → 생성: "퇴근가봅시더~" 또는 "퇴근가봅시더!" (거의 동일)
- **절대 하지 말 것**: "맛담 저도 참 좋아하는데요 퇴근하고 맛담해봅시다~" (너무 길게 늘림)

**위 실제 댓글 예시를 똑같이 따라쓰되, 약간의 변형만 주세요!**"""
        
        # API 호출
        try:
            logger.info(f"OpenAI API 호출 시작 (실제 댓글 {len(comments_list)}개 참고)")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,  # 낮춰서 더 정확한 모방 (높은 다양성 대신 정확한 모방)
                max_tokens=max(20, min(avg_len + 10, 50))  # 실제 댓글 길이에 맞춰 제한
            )
            
            if not response or not response.choices:
                logger.error("API 응답이 비어있습니다.")
                return None
            
            comment = response.choices[0].message.content.strip()
            logger.info(f"API 응답 받음: '{comment}'")
            return comment
        except Exception as e:
            logger.error(f"OpenAI API 호출 오류: {e}")
            import traceback
            logger.error(f"트레이스백: {traceback.format_exc()}")
            return None
    
    def _post_process(self, comment: str) -> Optional[str]:
        """댓글 후처리 - 영어/이모티콘만 제거, 한글 있으면 통과"""
        logger.info(f"후처리 시작: '{comment}'")
        
        # 이모티콘 제거
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)
        comment = emoji_pattern.sub('', comment).strip()
        logger.info(f"이모티콘 제거 후: '{comment}'")
        
        # 영어 제거
        has_english = bool(re.search(r'[a-zA-Z]', comment))
        if has_english:
            comment = re.sub(r'[a-zA-Z]', '', comment).strip()
            logger.info(f"영어 제거 후: '{comment}'")
        
        # 한글이 있는지 최종 확인
        has_korean = bool(re.search(r'[가-힣]', comment))
        if not has_korean:
            logger.warning(f"한글이 없어서 필터링: '{comment}'")
            return None
        
        logger.info(f"후처리 완료: '{comment}'")
        return comment.strip()
    
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
