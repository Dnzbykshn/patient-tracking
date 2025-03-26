from cryptography.fernet import Fernet
import getpass

# .env'deki YENİ anahtarınız
API_CRYPTO_KEY = "b923-ZQqD3pd-8DSXS4v0we8JXYn1OCoryxD_Z0Fe-k="

# Fernet şifreleyiciyi başlat
cipher = Fernet(API_CRYPTO_KEY.encode())

# Güvenli şekilde client secret girişi
print("⚠️ UYARI: Client secret terminal geçmişinde görünebilir!")
client_secret = getpass.getpass("Hastane API'sinin GERÇEK client secret'ını girin: ")

# Şifreleme işlemi
encrypted_secret = cipher.encrypt(client_secret.encode()).decode()

# Sonuç
print("\n● YENİ ENCRYPTED_CLIENT_SECRET (.env dosyasına ekleyin):")
print(f"ENCRYPTED_CLIENT_SECRET={encrypted_secret}")