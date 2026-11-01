import base64
from Crypto.Cipher import AES
from Crypto.Hash import MD5
from Crypto.Util.Padding import unpad

ct_b64 = 'U2FsdGVkX19fmBw92ecLtpE1bRwUFDL2lhCKJJLubM1TNgGCnLeE+ndbtICJBszUNjetOdtUPNwjMu6Hy4+d/A=='
ct_bytes = base64.b64decode(ct_b64)
salt = ct_bytes[8:16]
ciphertext = ct_bytes[16:]

for i in range(10000):
    pin = str(i).zfill(4).encode()
    d = b''
    d_i = b''
    for _ in range(3):
        d_i = MD5.new(d_i + pin + salt).digest()
        d += d_i
    key = d[:32]
    iv = d[32:48]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    try:
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        if len(decrypted) == 32:
            print('Found PIN: ' + pin.decode())
            print('Decrypted: ' + decrypted.decode())
            break
    except Exception:
        pass
