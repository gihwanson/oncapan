"""
사이트 구조 확인용 테스트 스크립트
"""

import requests
from bs4 import BeautifulSoup

def test_login_page():
    """로그인 페이지 구조 확인"""
    print("=" * 50)
    print("로그인 페이지 구조 확인")
    print("=" * 50)
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    })
    
    try:
        response = session.get('https://oncapan.com/login', timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 로그인 폼 찾기
        form = soup.find('form')
        if form:
            print(f"\n폼 action: {form.get('action', 'N/A')}")
            print(f"폼 method: {form.get('method', 'N/A')}")
            
            # 모든 input 필드 확인
            print("\n--- Input 필드들 ---")
            inputs = form.find_all('input')
            for inp in inputs:
                name = inp.get('name', 'N/A')
                input_type = inp.get('type', 'N/A')
                value = inp.get('value', '')
                print(f"  name: {name}, type: {input_type}, value: {value[:50]}")
            
            # 모든 hidden 필드
            print("\n--- Hidden 필드들 ---")
            hidden = form.find_all('input', type='hidden')
            for h in hidden:
                print(f"  {h.get('name')}: {h.get('value', '')[:100]}")
        
        # HTML 일부 저장
        with open('login_page.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("\n로그인 페이지 HTML을 login_page.html에 저장했습니다.")
        
    except Exception as e:
        print(f"오류: {e}")

def test_free_board():
    """자유게시판 구조 확인"""
    print("\n" + "=" * 50)
    print("자유게시판 구조 확인")
    print("=" * 50)
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    })
    
    try:
        response = session.get('https://oncapan.com/bbs/free', timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 게시글 목록 찾기
        print("\n--- 게시글 링크 찾기 ---")
        
        # 다양한 선택자로 시도
        links = soup.find_all('a', href=True)
        post_links = []
        
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # 게시글 링크 패턴 찾기
            if '/bbs/free' in href or 'wr_id=' in href or 'board.php' in href:
                if text and len(text) > 5:  # 의미있는 텍스트가 있는 링크만
                    post_links.append({
                        'href': href,
                        'text': text[:50],
                        'full_url': href if href.startswith('http') else f"https://oncapan.com{href}"
                    })
        
        print(f"\n게시글 링크 {len(post_links)}개 발견:")
        for i, post in enumerate(post_links[:10], 1):  # 처음 10개만
            print(f"  {i}. {post['text']}")
            print(f"     URL: {post['full_url']}")
        
        # 테이블 구조 확인
        print("\n--- 테이블 구조 확인 ---")
        tables = soup.find_all('table')
        print(f"테이블 개수: {len(tables)}")
        
        for i, table in enumerate(tables[:3], 1):  # 처음 3개만
            print(f"\n테이블 {i}:")
            rows = table.find_all('tr')
            print(f"  행 개수: {len(rows)}")
            if rows:
                first_row = rows[0]
                cells = first_row.find_all(['td', 'th'])
                print(f"  첫 행 셀 개수: {len(cells)}")
                for j, cell in enumerate(cells[:5], 1):
                    print(f"    셀 {j}: {cell.get_text(strip=True)[:30]}")
        
        # HTML 일부 저장
        with open('free_board.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("\n자유게시판 HTML을 free_board.html에 저장했습니다.")
        
    except Exception as e:
        print(f"오류: {e}")

if __name__ == "__main__":
    test_login_page()
    test_free_board()

