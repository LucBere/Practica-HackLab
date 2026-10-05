# El mejor secreto — Writeup

## Descripción del desafío

Se grabó un video de un jefe de estado tecleando la clave que protege
`secreto.zip`. El teclado numérico usado tiene las posiciones de las teclas
visibles, pero el **dígito que corresponde a cada tecla no coincide con la
etiqueta física** y esa correspondencia es desconocida. Sí se sabe que cada
tecla corresponde a un dígito distinto (es una biyección).

Objetivo: descifrar `secreto.zip`.

## Reconocimiento

### El archivo zip

```powershell
Expand-Archive -Path secreto.zip -DestinationPath salida -Force
```
```
Excepción: "La entrada del archivo se comprimió mediante un método
de compresión no compatible."
```

PowerShell no entiende el método de compresión. Inspeccionando con Python:

```python
import zipfile
with zipfile.ZipFile("secreto.zip") as z:
    for info in z.infolist():
        print(info.filename, info.compress_type, info.flag_bits)
```
```
secreto.txt  99  9
```

`compress_type = 99` identifica **WinZip AES**: el zip usa cifrado AES
derivando la clave con PBKDF2-HMAC-SHA1. La librería estándar `zipfile` de
Python no sabe leer este formato — hace falta `pyzipper`:

```
pip install pyzipper
```

### El video (teclado numérico tipo calculadora)

Mirando el video se identifican 5 posiciones de tecla físicas distintas:
- **6A** — tecla del centro
- **6B** — tecla a la derecha de 6A
- **2**, **9**, **5** — identificadas por su posición

La secuencia de pulsaciones leída fue:
```
6A 6B 2 6B 9 6A 9 9 9 9 5 6B
```

El **tramo final** (`9 6A 9 9 9 9 5 6B`) se lee con total claridad. El
**tramo inicial** (`6A 6B 2 6B`) está borroso: no se distingue con certeza
el orden exacto de las pulsaciones ni cuántas hay antes del primer `9`.

## Análisis

Hay **dos incertidumbres independientes** a resolver:

1. **La secuencia real de teclas pulsadas** (el tramo inicial dudoso).
2. **El mapeo tecla → dígito**, una biyección desconocida (cada tecla
   distinta corresponde a un dígito distinto, sin repetir).

### Dimensionar el mapeo tecla → dígito

Si una secuencia usa `k` teclas distintas, el número de asignaciones
inyectivas de dígitos (0-9) a esas teclas es una permutación parcial:
```
P(10, k) = 10 × 9 × 8 × ... × (10-k+1)
```
Para `k = 5` (el máximo de este caso: 6A, 6B, 2, 9, 5):
```
P(10, 5) = 10×9×8×7×6 = 30.240
```
Un espacio perfectamente abarcable por fuerza bruta.

### Dimensionar la incertidumbre de la secuencia

Para el tramo dudoso, usando las 3 teclas posibles (`6A`, `6B`, `2`) con
repetición permitida, y probando largos de 3, 4 y 5 pulsaciones, se generan
con `itertools.product` todas las variantes posibles:
```
3³ + 3⁴ + 3⁵ = 27 + 81 + 243 = 351 variantes del tramo inicial
```

Combinando ambas incertidumbres, el espacio total de contraseñas candidatas
ronda los **9,2 millones** de intentos (sumando, para cada variante de
secuencia, las permutaciones de dígitos correspondientes a su cantidad de
teclas distintas — 4 ó 5 según si el tramo dudoso incluye o no la tecla `2`).

## Explotación

### Generación de candidatos

```python
from itertools import product, permutations

TRAMO_FINAL = ["9", "6A", "9", "9", "9", "9", "5", "6B"]
TECLAS_DUDOSAS = ["6A", "6B", "2"]
LARGOS_A_PROBAR = [3, 4, 5]

def generar_passwords():
    vistas = set()
    for largo in LARGOS_A_PROBAR:
        for variante in product(TECLAS_DUDOSAS, repeat=largo):
            secuencia = list(variante) + TRAMO_FINAL
            teclas = sorted(set(secuencia))
            for digitos in permutations("0123456789", len(teclas)):
                mapa = dict(zip(teclas, digitos))
                pw = "".join(mapa[t] for t in secuencia)
                if pw not in vistas:
                    vistas.add(pw)
                    yield pw
```

### Verificación contra el zip (y optimización de rendimiento)

La primera versión del script abría el archivo zip (`pyzipper.AESZipFile`)
**en cada intento de contraseña** — con ~9 millones de intentos, esto
generaba un overhead de I/O enorme: a ese ritmo (~45.000 intentos/minuto)
el recorrido completo habría tardado horas. Tras 15 minutos solo se habían
probado ~680.000 contraseñas.

**Optimización aplicada:**
1. **Abrir el zip una sola vez por proceso**, reutilizando el objeto
   `AESZipFile` para todos los intentos de ese proceso, en vez de reabrirlo
   cada vez.
2. **Paralelizar con `multiprocessing`**: dividir las contraseñas candidatas
   en lotes y repartirlos entre todos los núcleos de la CPU con
   `multiprocessing.Pool`.

```python
import multiprocessing as mp
import pyzipper

def worker(passwords_chunk):
    zf = pyzipper.AESZipFile("secreto.zip")
    for pw in passwords_chunk:
        try:
            zf.setpassword(pw.encode())
            if zf.testzip() is None:   # valida CRC/HMAC real, no falso positivo
                zf.close()
                return pw
        except Exception:
            continue
    zf.close()
    return None

# ... dividir 'generar_passwords()' en chunks y correrlos con mp.Pool ...
```

Se usa `testzip()` (no solo el verificador corto de 2 bytes del header) para
confirmar la contraseña contra el HMAC real del archivo y evitar falsos
positivos.

**Resultado del cambio:** de ~15 minutos para 680.000 intentos (ritmo que
hubiera tomado varias horas para completar el espacio) a **~2 minutos**
(128 segundos) para encontrar la contraseña correcta sobre el total de
candidatos generados.

### Resultado

```
CONTRASEÑA ENCONTRADA: 547795999937

--- secreto.txt ---
696026dd5bf583f34530a657d896ebea
```

**Flag:** `696026dd5bf583f34530a657d896ebea`

La contraseña correcta correspondió a una variante del tramo inicial con
una pulsación extra de `6B` respecto a la lectura literal inicial, con un
mapeo tecla→dígito específico entre las 30.240 asignaciones posibles para
esas 5 teclas.

## Causa raíz y remediación

- **Causa raíz:** la "seguridad por ofuscación" del teclado (reordenar las
  etiquetas físicas de los dígitos) no aporta una protección real: solo
  introduce una capa adicional, pequeña y acotada (como mucho `10! =
  3.628.800` posibles mapeos, y en la práctica mucho menos al conocerse
  parcialmente la secuencia), que sumada a una contraseña corta y numérica
  cae rápidamente ante fuerza bruta combinada con un poco de información
  visual (el video).
- **Remediación recomendada:**
  1. No depender de mecanismos de ofuscación física (teclados con etiquetas
     aleatorias) como control de seguridad; en el mejor caso retrasan, no
     impiden, un ataque informado.
  2. Usar contraseñas/frases largas y de alta entropía en vez de PINs
     puramente numéricos y cortos.
  3. Minimizar la exposición visual de la introducción de credenciales
     (evitar que terceros puedan grabar o ver el tecleo).
  4. Para cifrado de archivos sensibles, preferir derivación de clave con
     factores de trabajo altos (muchas iteraciones de PBKDF2, o Argon2) que
     hagan cada intento de fuerza bruta computacionalmente más costoso.

## Herramientas usadas

- Python 3 (`itertools.product`, `itertools.permutations`,
  `multiprocessing`)
- `pyzipper` (lectura y prueba de contraseñas contra zips WinZip AES)
