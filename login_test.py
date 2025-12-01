"""로그인 테스트 스크립트"""
import requests
from bs4 import BeautifulSoup

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
})

print("=" * 60)
print("온카판 로그인 폼 구조 확인")
print("=" * 60)

# 로그인 페이지 가져오기
response = session.get('https://oncapan.com/login', timeout=10)
print(f"\n상태 코드: {response.status_code}")

soup = BeautifulSoup(response.text, 'html.parser')

# 폼 찾기
form = soup.find('form')
if form:
    print(f"\n폼 발견!")
    print(f"폼 action: {form.get('action', 'N/A')}")
    print(f"폼 method: {form.get('method', 'N/A')}")
    
    print("\n" + "=" * 60)
    print("모든 input 필드:")
    print("=" * 60)
    
    inputs = form.find_all('input')
    for i, inp in enumerate(inputs, 1):
        name = inp.get('name', 'N/A')
        input_type = inp.get('type', 'N/A')
        input_id = inp.get('id', 'N/A')
        value = inp.get('value', '')
        placeholder = inp.get('placeholder', 'N/A')
        
        print(f"\n{i}. name: {name}")
        print(f"   type: {input_type}")
        print(f"   id: {input_id}")
        print(f"   value: {value[:50] if value else '없음'}")
        print(f"   placeholder: {placeholder}")
    
    print("\n" + "=" * 60)
    print("모든 button 필드:")
    print("=" * 60)
    
    buttons = form.find_all('button')
    for i, btn in enumerate(buttons, 1):
        name = btn.get('name', 'N/A')
        btn_type = btn.get('type', 'N/A')
        btn_id = btn.get('id', 'N/A')
        text = btn.get_text(strip=True)
        
        print(f"\n{i}. name: {name}")
        print(f"   type: {btn_type}")
        print(f"   id: {btn_id}")
        print(f"   text: {text}")
else:
    print("\n폼을 찾을 수 없습니다!")

# HTML 일부 저장
with open('login_page_debug.html', 'w', encoding='utf-8') as f:
    f.write(response.text)
print("\n로그인 페이지 HTML을 login_page_debug.html에 저장했습니다.")

input("\n아무 키나 눌러 종료...")

