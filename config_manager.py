"""
설정 관리 모듈
- 로그인 정보 암호화 저장/로드
- API 키 관리
- 설정 파일 관리
"""

import json
import os
from cryptography.fernet import Fernet

class ConfigManager:
    def __init__(self, config_file="config.json", key_file="key.key"):
        self.config_file = config_file
        self.key_file = key_file
        self.key = self._load_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _load_or_create_key(self):
        """암호화 키 로드 또는 생성"""
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            # 새 키 생성
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            return key
    
    def save_config(self, username: str, password: str, api_key: str, 
                   comment_delay: int = 10, min_delay: int = 5, max_delay: int = 15,
                   auto_collect: bool = False):
        """설정 저장 (비밀번호와 API 키 암호화)"""
        config = {
            'username': username,
            'encrypted_password': self.cipher.encrypt(password.encode()).decode(),
            'encrypted_api_key': self.cipher.encrypt(api_key.encode()).decode(),
            'comment_delay': comment_delay,
            'min_delay': min_delay,
            'max_delay': max_delay,
            'auto_collect': auto_collect
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def load_config(self):
        """설정 로드"""
        if not os.path.exists(self.config_file):
            return None
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 복호화
            config['password'] = self.cipher.decrypt(config['encrypted_password'].encode()).decode()
            config['api_key'] = self.cipher.decrypt(config['encrypted_api_key'].encode()).decode()
            
            # 암호화된 필드 제거
            config.pop('encrypted_password', None)
            config.pop('encrypted_api_key', None)
            
            return config
        except Exception as e:
            print(f"설정 로드 오류: {e}")
            return None
    
    def config_exists(self):
        """설정 파일 존재 여부 확인"""
        return os.path.exists(self.config_file)

