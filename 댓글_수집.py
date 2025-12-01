"""
댓글 수집 스크립트
- 온카판 게시판에서 실제 댓글 수집
- 수집한 댓글을 분석하여 AI 학습에 활용
"""

from comment_collector import CommentCollector
import sys

def main():
    print("=" * 60)
    print("온카판 댓글 수집 도구")
    print("=" * 60)
    print()
    print("이 도구는 온카판 게시판에서 실제 댓글을 수집하여")
    print("AI가 더 자연스러운 댓글을 생성할 수 있도록 도와줍니다.")
    print()
    
    collector = CommentCollector()
    
    try:
        # 로그인 필요 여부 확인
        print("로그인이 필요할 수 있습니다.")
        print("수집할 게시글 수를 입력하세요 (기본값: 10): ", end='')
        limit_input = input().strip()
        limit = int(limit_input) if limit_input.isdigit() else 10
        
        print(f"\n게시글 {limit}개에서 댓글을 수집합니다...")
        print("이 작업은 몇 분이 걸릴 수 있습니다.")
        print()
        
        # 댓글 수집
        comments = collector.collect_comments_from_board(
            limit_posts=limit,
            comments_per_post=10
        )
        
        if comments:
            print(f"\n{len(comments)}개의 댓글을 수집했습니다.")
            
            # 저장
            saved_count = collector.save_comments(comments)
            print(f"새로 저장된 댓글: {saved_count}개")
            
            # 분석
            print("\n댓글 분석 중...")
            analysis = collector.analyze_comments()
            
            if analysis:
                print("\n" + "=" * 60)
                print("분석 결과")
                print("=" * 60)
                print(f"총 댓글 수: {analysis['total_count']}개")
                print(f"평균 길이: {analysis['avg_length']:.1f}자")
                print(f"\n길이 분포:")
                print(f"  - 짧은 댓글 (20자 이하): {analysis['length_distribution']['short']}개")
                print(f"  - 중간 댓글 (21-50자): {analysis['length_distribution']['medium']}개")
                print(f"  - 긴 댓글 (50자 초과): {analysis['length_distribution']['long']}개")
                
                if analysis.get('common_endings'):
                    print(f"\n자주 사용되는 어미 (상위 5개):")
                    for item in analysis['common_endings'][:5]:
                        print(f"  - {item['ending']}: {item['count']}회")
            
            print("\n" + "=" * 60)
            print("수집 완료!")
            print("=" * 60)
            print("\n이제 AI가 수집한 댓글 스타일을 학습하여")
            print("더 자연스러운 댓글을 생성할 수 있습니다.")
        else:
            print("\n댓글을 수집하지 못했습니다.")
            print("로그인이 필요하거나 게시글에 댓글이 없을 수 있습니다.")
        
    except KeyboardInterrupt:
        print("\n\n수집이 중단되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        collector.close()

if __name__ == "__main__":
    main()

