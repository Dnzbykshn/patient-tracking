import requests
import hmac
import hashlib
import os
from datetime import datetime, timedelta
import logging
from cryptography.fernet import Fernet
from urllib.parse import urlparse
import json


# .env'deki AYNI anahtarı kullanın
API_CRYPTO_KEY = "K4VHV9DMM8-h2cEE76zfhOxooWKwLqvnVdjZfysQD68="
cipher = Fernet(API_CRYPTO_KEY.encode())

# Hastane API'sinden aldığınız GERÇEK client secret
REAL_CLIENT_SECRET = "hastane_sistemindeki_gercek_deger"

# Şifrele
encrypted_secret = cipher.encrypt(REAL_CLIENT_SECRET.encode()).decode()
print(f"YENİ ENCRYPTED_CLIENT_SECRET:\n{encrypted_secret}")





logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('secure_api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SecureHospitalAPI')

class SecureHospitalAPI:
    def __init__(self, base_url, client_id, client_secret):
        """
        Güvenli API istemcisi başlatma
        
        Args:
            base_url (str): API temel URL'si
            client_id (str): OAuth2 client ID
            client_secret (str): Şifrelenmiş client secret
        """
        # 1. Önce temel özellikleri başlat
        self.base_url = None
        self.client_id = None
        self._client_secret = None
        self.access_token = None
        self.token_expiry = None
        self.crypto_key = None
        self.cipher_suite = None
        self.session = None
        
        try:
            # 2. Şifreleme sistemini kur
            self.crypto_key = os.getenv('API_CRYPTO_KEY', Fernet.generate_key())
            self.cipher_suite = Fernet(self.crypto_key)
            
            # 3. Input Validation
            if not self._validate_url(base_url):
                raise ValueError("Geçersiz API URL'si")
            if not isinstance(client_id, str) or not client_id:
                raise ValueError("Geçersiz client_id")
            if not isinstance(client_secret, str) or not client_secret:
                raise ValueError("Geçersiz client_secret")
            
            self.base_url = base_url
            self.client_id = client_id
            self._client_secret = self._decrypt_secret(client_secret)
            
            # 4. Session oluştur
            self.session = requests.Session()
            self.session.headers.update({
                "Content-Type": "application/json",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY"
            })
            
            # 5. Kimlik doğrulama
            self._authenticate()
            
            logger.info("Secure API client başarıyla başlatıldı")
            
        except Exception as e:
            logger.error(f"API istemcisi başlatılamadı: {str(e)}")
            self._safe_cleanup()
            raise

    def _validate_url(self, url):
        """URL doğrulama"""
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except ValueError:
            return False

    def _decrypt_secret(self, encrypted_secret):
        """Client secret şifresini çözme"""
        try:
            return self.cipher_suite.decrypt(encrypted_secret.encode()).decode()
        except Exception as e:
            logger.error(f"Secret decryption failed: {str(e)}")
            raise ValueError("Client secret decryption failed")

    def _authenticate(self):
        """OAuth2 ile kimlik doğrulama"""
        try:
            timestamp = str(int(datetime.now().timestamp()))
            message = f"{self.client_id}{timestamp}"
            signature = hmac.new(
                self._client_secret.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            auth_url = f"{self.base_url}/oauth2/token"
            payload = {
                "client_id": self.client_id,
                "grant_type": "client_credentials",
                "timestamp": timestamp,
                "signature": signature
            }
            
            logger.info(f"Authenticating with client_id: {self.client_id[:2]}...{self.client_id[-2:]}")
            
            response = self.session.post(
                auth_url,
                json=payload,
                timeout=10,
                verify=True
            )
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.token_expiry = datetime.now() + timedelta(seconds=token_data['expires_in'])
            
            if 'patient:read' not in token_data['scope']:
                raise PermissionError("Yetersiz yetki: patient:read scope eksik")
                
            self.session.headers.update({
                "Authorization": f"Bearer {self.access_token}"
            })
            
            logger.info("Authentication successful")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {str(e)}")
            self._safe_cleanup()
            raise ConnectionError("Kimlik doğrulama başarısız")

    def _safe_cleanup(self):
        """Güvenli temizlik yap"""
        try:
            if hasattr(self, 'session') and self.session:
                self.session.close()
        except Exception as e:
            logger.error(f"Session kapatılırken hata: {str(e)}")
        
        if hasattr(self, '_client_secret'):
            self._client_secret = None

    def __del__(self):
        """Nesne yok edilirken temizlik yap"""
        self._safe_cleanup()
        logger.info("API client securely terminated")

    # Diğer metodlar (get_patient_info, post_vital_signs vb.) önceki gibi kalacak
    # ...