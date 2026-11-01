# pyrefly: ignore [missing-import]
from Crypto.Util.number import bytes_to_long, getPrime

with open('flag.txt', 'rb') as fd:
    flag = fd.read().strip()

m1 = flag[:len(flag)//2]
m2 = flag[len(flag)//2:]

p = getPrime(1024)
q = getPrime(1024)
r = getPrime(1024)
e = 65537
n1 = p*q
n2 = q*r

c1 = pow(bytes_to_long(m1), e, n1)
c2 = pow(bytes_to_long(m2), e, n2)

print(f'n1: {n1}')
print(f'n2: {n2}')
print(f'e: {e}')
print(f'c1: {c1}')
print(f'c2: {c2}')
