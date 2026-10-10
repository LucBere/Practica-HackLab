import base64
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

ciphertext = base64.b64decode("PK8EdNdV53YOEsO6WGVFvw==")
password = b"PIZZA"

# CryptoJS default key derivation is OpenSSL EVP_BytesToKey using MD5
def evp_bytes_to_key(password, salt, key_len, iv_len):
    d = d_i = b''
    while len(d) < key_len + iv_len:
        d_i = hashlib.md5(d_i + password + salt).digest()
        d += d_i
    return d[:key_len], d[key_len:key_len+iv_len]

key, iv = evp_bytes_to_key(password, b"", 32, 16)
cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
decryptor = cipher.decryptor()
try:
    pt = decryptor.update(ciphertext) + decryptor.finalize()
    print("EVP (MD5):", pt)
except Exception as e:
    pass

# What if it's PBKDF2 as stated: "1000 iteraciones y sin salt"
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

for algo in [hashes.SHA1(), hashes.SHA256()]:
    kdf = PBKDF2HMAC(
        algorithm=algo,
        length=48, # 32 byte key + 16 byte IV
        salt=b"",
        iterations=1000,
        backend=default_backend()
    )
    key_iv = kdf.derive(password)
    key = key_iv[:32]
    iv = key_iv[32:48]

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    try:
        pt = decryptor.update(ciphertext) + decryptor.finalize()
        print(f"PBKDF2 ({algo.name}):", pt)
    except Exception as e:
        pass
