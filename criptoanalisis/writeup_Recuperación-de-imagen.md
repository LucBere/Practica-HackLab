# Recuperación de imagen — Writeup

## Descripción del desafío

Una empresa almacena, por cada imagen, un archivo de bits de paridad que le
permite recuperarla ante un daño. El esquema es un **código de paridad
bidimensional (2D)**:

- La imagen se divide en paquetes de 10 bytes (80 bits).
- Cada paquete se estructura en **5 filas de 16 bits** (cada fila = 2 bytes).
- Por cada paquete se guardan dos vectores de paridad:
  - **Paridad de filas** (longitud 5): un bit por fila.
  - **Paridad de columnas** (longitud 16): un bit por columna.

Si ocurre como máximo **un error** por paquete, se puede corregir sin
ambigüedad: se detecta la fila cuya paridad cambió y la columna cuya paridad
cambió, y el bit erróneo está en la **intersección** de ambas.

Una de las imágenes fue dañada y hay que recuperarla.

## Material entregado

- `imagen_rota.png` — la imagen dañada.
- Archivo de paridad — una línea por paquete, con formato
  `<5 bits de filas> <16 bits de columnas>`.
- `BitParidad.java` — el código fuente que generó los bits de paridad.

## Análisis

El código Java es clave porque define **exactamente** cómo se mapean los 10
bytes de cada paquete a las 5 filas de 16 bits, y cómo se calcula cada
paridad. Puntos importantes:

1. **Paridad de fila:** `1` si la cantidad total de bits en 1 de los 2 bytes
   de la fila es **impar**, `0` si es par.

2. **Paridad de columna:** XOR vertical de las 5 filas, columna por columna.

3. **Mapeo byte ↔ columna (peculiar):** recorriendo el código, para cada par
   de bytes `(byte1, byte2)`:
   - Las **columnas 0..7** corresponden a `byte2`, de MSB a LSB.
   - Las **columnas 8..15** corresponden a `byte1`, de MSB a LSB.

   Es decir, el segundo byte del par aparece primero en la fila de 16 bits.
   Replicar este orden es esencial: si se usa el orden "natural", la
   corrección apunta al bit equivocado.

El cálculo de paridad se validó contra el ejemplo del enunciado (paquete de
muestra con vectores de filas `[1 0 0 0 0]` y columnas
`[1 0 0 0 1 1 1 0 1 1 1 1 0 1 0 0]`), reproduciéndolos exactamente.

## Explotación (corrección)

Para cada paquete de la imagen dañada:
1. Se recalcula su paridad de filas y columnas (replicando el código Java).
2. Se compara con la paridad original guardada.
3. Si hay **exactamente una fila distinta y una columna distinta**, el bit
   erróneo está en esa intersección → se invierte (flip).
4. Si no hay diferencias, el paquete está intacto.

Reconstruida la imagen con todos los bits corregidos, se abre y muestra el
código de la flag.

### Script (solo librerías estándar de Python)

```python
IMG_IN, PARIDAD, IMG_OUT = "imagen_rota.png", "paridad.txt", "imagen_recuperada.png"

def bits(b):                       # byte -> 8 bits, MSB primero
    return [(b >> (7 - k)) & 1 for k in range(8)]

def fila16(b1, b2):                # mapeo del codigo Java: byte2 | byte1
    return bits(b2) + bits(b1)

datos = bytearray(open(IMG_IN, "rb").read())
paridad = []
for ln in open(PARIDAD):
    if ln.strip():
        pf, pc = ln.split()
        paridad.append(([int(x) for x in pf], [int(x) for x in pc]))

for p in range(min(len(datos)//10, len(paridad))):
    paq = datos[p*10:(p+1)*10]
    pf_calc = [ (bin(paq[i]).count("1") + bin(paq[i+1]).count("1")) % 2
                for i in range(0, 10, 2) ]
    pc_calc = [0]*16
    for i in range(0, 10, 2):
        f = fila16(paq[i], paq[i+1])
        for c in range(16):
            pc_calc[c] ^= f[c]
    pf_o, pc_o = paridad[p]
    fdif = [i for i in range(5)  if pf_calc[i] != pf_o[i]]
    cdif = [j for j in range(16) if pc_calc[j] != pc_o[j]]
    if len(fdif) == 1 and len(cdif) == 1:
        fila, col = fdif[0], cdif[0]
        if col < 8:
            idx, bitpos = fila*2 + 1, 7 - col
        else:
            idx, bitpos = fila*2, 7 - (col - 8)
        datos[p*10 + idx] ^= (1 << bitpos)

open(IMG_OUT, "wb").write(datos)
```

### Resultado

Abriendo `imagen_recuperada.png` se lee:

```
¡FELICITACIONES!
b9365cb4c17b4f3b93f0095619bcd1ea
```

**Flag:** `b9365cb4c17b4f3b93f0095619bcd1ea`

## Causa raíz y nota de seguridad

Este desafío es más de **detección/corrección de errores** que de una
vulnerabilidad en sí. La enseñanza relevante:

- Un código de paridad 2D detecta y corrige **un solo error por bloque**;
  con dos o más errores en el mismo paquete, la corrección puede fallar o
  introducir errores nuevos. No es un mecanismo criptográfico ni de
  integridad robusto (no detecta manipulación intencional).
- Para integridad real frente a manipulación deliberada deben usarse
  funciones hash criptográficas (SHA-256) o códigos de autenticación de
  mensajes (HMAC); para recuperación robusta ante daño, códigos de
  corrección más fuertes (Reed-Solomon, LDPC).

## Herramientas usadas

- Python 3 (reimplementación del cálculo de paridad y corrección de bits)
- Análisis del código fuente Java provisto para replicar el mapeo exacto
