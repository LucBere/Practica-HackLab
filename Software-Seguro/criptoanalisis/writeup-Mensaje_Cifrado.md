# Mensaje cifrado — Writeup

## Descripción del desafío

María envía mensajes a su novio cifrados con el algoritmo **César**, usando
una clave que solo ellos conocen. Hay que descubrir el contenido de uno de
los mensajes.

**Texto cifrado:**
```
wiqxmvb
wiqxmvduyidxydpeqsdiwdpmdgevmgmeb
wiqxmvduyidxydwyirsdiwdpmdhiwisb
wiqxmvduyidxydpmvehediwdpmdhiwgeqwsb
wiqxmvduyidxydqspfvidiwdpmdgeqgm qb
wiqxmvduyidxydfsgediwdpmdvijykmsb
wiqxmvduyidxydeopediwdpmdvikeosc
wiqxmvduyidiémwxiwccc
wiqxmvduyidzmzsdtevedepevxic
```

**Pista — alfabeto usado (35 símbolos):**
```
a b c d e f g h i j k l m n ñ o p q r s t u v w x y z á é í ó ú , .  (espacio)
```

## Análisis

El cifrado César reemplaza cada símbolo por el que está `k` posiciones más
adelante en el alfabeto, módulo el tamaño del alfabeto. La clave `k` es un
único número.

El detalle relevante es el **alfabeto personalizado**: no es el abecedario
inglés de 26 letras, sino 35 símbolos que incluyen `ñ`, vocales acentuadas,
coma, punto y espacio. Los desplazamientos "envuelven" sobre estos 35
símbolos.

Como solo hay **35 claves posibles**, el espacio es trivial: se prueban las
35 (fuerza bruta) y se identifica la que produce texto legible en español.

## Explotación

Para descifrar se **resta** `k` a cada símbolo (el cifrado suma `k`).

### Script

```python
alfabeto = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','ñ','o',
            'p','q','r','s','t','u','v','w','x','y','z','á','é','í','ó','ú',
            ',','.',' ']
N = len(alfabeto)
idx = {c: i for i, c in enumerate(alfabeto)}

cifrado = open("cifrado.txt").read()

for k in range(N):
    salida = "".join(
        alfabeto[(idx[ch] - k) % N] if ch in idx else ch
        for ch in cifrado
    )
    print(f"k={k}: {salida.splitlines()[0]}")
```

Con **k = 4**, la primera línea da `sentir,` — texto en español. Descifrando
el mensaje completo con esa clave:

### Resultado

```
sentir,
sentir que tu mano es mi caricia,
sentir que tu sueño es mi deseo,
sentir que tu mirada es mi descanso,
sentir que tu nombre es mi canción,
sentir que tu boca es mi refugio,
sentir que tu alma es mi regalo.
sentir que existes...
sentir que vivo para amarte.
```

El mensaje descifrado (clave **k = 4**) es un poema de amor. Ese texto es lo
que se envía como solución del desafío.

## Causa raíz / nota de seguridad

- El cifrado César (cifrado por desplazamiento) tiene un **espacio de claves
  igual al tamaño del alfabeto** (aquí, 35). Es trivial de romper por fuerza
  bruta, y con análisis de frecuencias incluso sin probar todas las claves.
- No ofrece ninguna seguridad real. Para confidencialidad deben usarse
  cifrados modernos y auditados (AES-GCM, ChaCha20-Poly1305) con claves de
  tamaño adecuado.

## Herramientas usadas

- Python 3 (fuerza bruta sobre las 35 claves posibles)
