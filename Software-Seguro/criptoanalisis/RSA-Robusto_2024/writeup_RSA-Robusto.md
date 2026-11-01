# RSA Robusto — Writeup

## Descripción del desafío

Un desarrollador cifró un mensaje dividiéndolo en dos partes (`m1` y `m2`) utilizando el criptosistema asimétrico RSA. Posteriormente, divulgó el código fuente del algoritmo de cifrado y se filtraron los parámetros públicos y criptogramas generados (`n1`, `n2`, `e`, `c1`, `c2`).

El objetivo es descifrar ambas partes del mensaje y concatenarlas para reconstruir el código ganador (flag).

---

## Análisis de la vulnerabilidad

Al revisar el código fuente de cifrado (`encrypt.py`):

```python
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
```

### Falla criptográfica: Reutilización de factores primos (*Common Prime Factor*)

La seguridad de RSA descansa en la dificultad computacional de factorizar un módulo compuesto $n = p \cdot q$ de 2048 bits cuando sus factores primos son grandes, aleatorios e independientes.

En este caso, el desarrollador cometió el error crítico de **compartir el mismo primo $q$** entre dos pares de claves distintos:
- $n_1 = p \cdot q$
- $n_2 = q \cdot r$

Dado que $p$ y $r$ son primos distintos e independientes, el Máximo Común Divisor (GCD) entre ambos módulos es exactamente el factor compartido:

$$\gcd(n_1, n_2) = q$$

El algoritmo de Euclides permite calcular el GCD de números de miles de bits en **milisegundos**. Una vez obtenido $q$, la factorización de ambos módulos colapsa de forma trivial:

1. Se recuperan los primos restantes:
   $$p = \frac{n_1}{q}, \quad r = \frac{n_2}{q}$$

2. Se calculan las funciones de Euler (totientes):
   $$\phi(n_1) = (p - 1)(q - 1)$$
   $$\phi(n_2) = (q - 1)(r - 1)$$

3. Se derivan los exponentes privados de descifrado:
   $$d_1 \equiv e^{-1} \pmod{\phi(n_1)}$$
   $$d_2 \equiv e^{-1} \pmod{\phi(n_2)}$$

4. Se recuperan los mensajes en claro:
   $$m_1 \equiv c_1^{d_1} \pmod{n_1}$$
   $$m_2 \equiv c_2^{d_2} \pmod{n_2}$$

---

## Explotación

### Script de resolución (`solve_ej30.py`)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resolución del Desafío 30 - RSA Robusto
Ataque de factor primo compartido (Common Prime Factor / Shared Prime GCD)
"""
import math

def long_to_bytes(n: int) -> bytes:
    """Convierte un entero largo a bytes."""
    return n.to_bytes((n.bit_length() + 7) // 8, 'big')

def resolver_rsa_robusto(n1: int, n2: int, e: int, c1: int, c2: int):
    print("=" * 60)
    print("🔓 RESOLVIENDO RSA ROBUSTO (COMMON PRIME FACTOR)")
    print("=" * 60)
    
    # 1. Encontrar el factor primo compartido q mediante GCD
    q = math.gcd(n1, n2)
    if q == 1:
        print("[-] Error: n1 y n2 son coprimos.")
        return None
    print(f"[+] Primo compartido 'q' encontrado con éxito!")
    
    # 2. Factorizar ambos módulos
    p = n1 // q
    r = n2 // q
    
    # 3. Totientes de Euler
    phi1 = (p - 1) * (q - 1)
    phi2 = (q - 1) * (r - 1)
    
    # 4. Inversos modulares (claves privadas d1 y d2)
    d1 = pow(e, -1, phi1)
    d2 = pow(e, -1, phi2)
    
    # 5. Descifrar m1 y m2
    m1_int = pow(c1, d1, n1)
    m2_int = pow(c2, d2, n2)
    
    # 6. Convertir enteros a bytes
    m1_bytes = long_to_bytes(m1_int)
    m2_bytes = long_to_bytes(m2_int)
    
    # 7. Concatenar para obtener la flag completa
    flag = (m1_bytes + m2_bytes).decode('utf-8')
    
    print(f"[+] m1 descifrado: {m1_bytes}")
    print(f"[+] m2 descifrado: {m2_bytes}")
    print(f"\n🎉 FLAG / CÓDIGO GANADOR:\n{flag}")
    print("=" * 60)
    return flag

if __name__ == "__main__":
    # Valores fugados del desafío
    n1 = 24127109628295280886514896681554300020227649055304057729303304080334690257976587964205153867808719208899286903640351305370686446585782858016757675115901409737547152684897848025643481091036365041856677418163284861340756794713474827128266428019974263703720830780268890375844455990127313538481001872874852984745481158352648875686113911855895711176923626180110509270383701070173698262188285085665791861598862939296576949103559504662527408065993125471832308491668418032965677260576452109472171087658384210881244395008207689678950116923835157397567662674875531668504667264847799988213518069840979350519657929942660088722727
    n2 = 15983329338976127265290829442187135406619656299256173689542385277328424399534734980239357738739754723616067666710037138030190087830111700143051623098134208067490726289976790825905901563286198198068579019025544465731517957919464995059999977419149509613359273210952928761445153994886914177572787326533614841854028990248315599130346805320150587244888442471294970842953761855403819151263845826714694132561881956473613828240569696941604950296152265681806032325065908529853995054867267296940852312428588305603605108940425721789861102023427263717747784807186720889516569853749674089987426155446951793788498852578883848898041
    e = 65537
    c1 = 23385258666331731475666863638844609431283008833211519282195231854448457358069888025764655538945178434935713071154422680312473735481576860769522407014713058427201817342569622410687169919907662718319827040472180910208353932759639361621305516703906304739253890366325310201398252842472048743001445307676020915238027889211064251872279155093182865317527742102251201981469299458337260767895250493093408842239394242655160887034663442335981035478100390038936761686188138939864370450879987405729026035833180128788573284331967044792487490802887002012569289439294889888880636409333983855297822325831371511083401607356381502950588
    c2 = 3131864619666353694698630602377408407868461144447703729001172977611842871256353472478745534274138434545346716175920686284163626056758679358991466819997380344194937894423821828646101823458803271352266744180849539676233520241009376890429546155588508397083178987387583159774732550152013834242688638533629816659196650738695734902962171230765093816043819363281559550091413039703459737504927379982566524597138243193770302003055434531463607806981592950016236461104520579713042704941823061168330572033304353994309485325525660793035656273335186938483646488081842938131646808359436319958818430907933051943696407534319169686818

    resolver_rsa_robusto(n1, n2, e, c1, c2)
```

### Salida de ejecución

```text
============================================================
🔓 RESOLVIENDO RSA ROBUSTO (COMMON PRIME FACTOR)
============================================================
[+] Primo compartido 'q' encontrado con éxito!
[+] m1 descifrado: b'FLAG{295d531e3c72f8'
[+] m2 descifrado: b'63ad77c96cde63f829}'

🎉 FLAG / CÓDIGO GANADOR:
FLAG{295d531e3c72f863ad77c96cde63f829}
============================================================
```

---

## Flag

```
FLAG{295d531e3c72f863ad77c96cde63f829}
```

*(O en formato hash según requiera el input del desafío: `295d531e3c72f863ad77c96cde63f829`)*

---

## Causa raíz / nota de seguridad

- **Generación independiente de primos:** Cada par de claves RSA debe generarse con primos únicos, pseudoaleatorios y estadísticamente independientes. La reutilización de material de clave (primos) anula por completo la seguridad de ambos pares de claves.
- **Vulnerabilidad histórica real:** Este ataque no es solo teórico; estudios a gran escala en Internet (como el trabajo *"Mining Your Ps and Qs"*, 2012) encontraron decenas de miles de certificados TLS y claves SSH en producción vulnerables a este ataque debido a fallas de entropía al momento del arranque en dispositivos embebidos.
- **Buenas prácticas:** Utilizar siempre librerías criptográficas de alto nivel y generadores de números pseudoaleatorios criptográficamente seguros (CSPRNG), evitando la manipulación manual de números primos o arquitecturas ad-hoc.

---

## Herramientas usadas

- Python 3 (`math.gcd`, aritmética modular de enteros arbitrarios)
- Algoritmo de Euclides
