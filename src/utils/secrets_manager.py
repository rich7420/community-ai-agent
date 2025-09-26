"""
Secrets管理模組
提供安全的secrets存儲和檢索
"""
import os
import base64
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class SecretsManager:
    """Secrets管理器"""
    
    def __init__(self, master_key: Optional[str] = None):
        """
        初始化Secrets管理器
        
        Args:
            master_key: 主密鑰，如果未提供則從環境變數獲取
        """
        self.master_key = master_key or os.getenv('SECRETS_MASTER_KEY')
        if not self.master_key:
            raise ValueError("SECRETS_MASTER_KEY environment variable is required")
        
        # 生成加密密鑰
        self.fernet = self._create_fernet()
    
    def _create_fernet(self) -> Fernet:
        """創建Fernet加密器"""
        # 從主密鑰生成加密密鑰
        password = self.master_key.encode()
        salt = b'community_ai_salt'  # 在生產環境中應該使用隨機salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return Fernet(key)
    
    def encrypt_secret(self, secret: str) -> str:
        """加密secret"""
        return self.fernet.encrypt(secret.encode()).decode()
    
    def decrypt_secret(self, encrypted_secret: str) -> str:
        """解密secret"""
        return self.fernet.decrypt(encrypted_secret.encode()).decode()
    
    def store_secret(self, key: str, value: str) -> None:
        """存儲加密的secret到環境變數"""
        encrypted_value = self.encrypt_secret(value)
        os.environ[f"ENCRYPTED_{key.upper()}"] = encrypted_value
    
    def get_secret(self, key: str) -> Optional[str]:
        """獲取並解密secret"""
        encrypted_key = f"ENCRYPTED_{key.upper()}"
        encrypted_value = os.getenv(encrypted_key)
        
        if encrypted_value:
            try:
                return self.decrypt_secret(encrypted_value)
            except Exception as e:
                print(f"❌ 解密secret失敗 {key}: {e}")
                return None
        
        # 如果沒有加密版本，返回原始環境變數
        return os.getenv(key.upper())
    
    def get_api_key(self, service: str) -> Optional[str]:
        """獲取API密鑰"""
        key_mapping = {
            'slack_bot': 'SLACK_BOT_TOKEN',
            'slack_app': 'SLACK_APP_TOKEN',
            'github': 'GITHUB_TOKEN',
            'openrouter': 'OPENROUTER_API_KEY',
            'facebook': 'FACEBOOK_ACCESS_TOKEN'
        }
        
        env_key = key_mapping.get(service)
        if env_key:
            return self.get_secret(env_key)
        return None

# 全局secrets管理器實例
secrets_manager = SecretsManager()

def get_api_key(service: str) -> Optional[str]:
    """獲取API密鑰的便捷函數"""
    return secrets_manager.get_api_key(service)

def store_api_key(service: str, key: str) -> None:
    """存儲API密鑰的便捷函數"""
    key_mapping = {
        'slack_bot': 'SLACK_BOT_TOKEN',
        'slack_app': 'SLACK_APP_TOKEN',
        'github': 'GITHUB_TOKEN',
        'openrouter': 'OPENROUTER_API_KEY',
        'facebook': 'FACEBOOK_ACCESS_TOKEN'
    }
    
    env_key = key_mapping.get(service)
    if env_key:
        secrets_manager.store_secret(env_key, key)
    else:
        raise ValueError(f"Unknown service: {service}")
