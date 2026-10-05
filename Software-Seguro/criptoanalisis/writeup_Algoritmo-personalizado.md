# Algoritmo personalizado — Writeup

## Descripción del desafío

Se entrega un mensaje cifrado y el código fuente del algoritmo usado para
cifrarlo. El objetivo es descifrar el mensaje.

**Mensaje cifrado (408 caracteres):**
```
MbzKNclubnQRtOrgmQPnDwtspUfSNCFeqEMiyiVtFmIfGRbsGUzUimiaGvnzpBLfrvzWZimhylZZesgDaH QteTgbQokOheEoorrpaDoZgLhzmN  bfwsFtokyCELaBogwfLAcXoNQKrhCVQJeMVqVMvPvjXEaRXHb QUNLzsvNZRUkGxoibzsTbVucNWdqsypsgjsg sUQykViZUrNuSAXRlZcvZoaxhnRhwJRuAcnHWpRTkkoletByjABhxowKdPVICknvFmDqKc yKhehypGnSniuttNWoWCpNEJxPNixzbDuDucRhsGtkWkdeaxYNDrRoubtRxeJAWFrpcQcIpYFQqWdkwpdEgVKANmIUObWyuAE davlhvBARQyiOptGCEJwVmfeaaJlCHTPazUylFS
```

**Código fuente del cifrado:**
```python
import random, time

def encrypt(plaintext, key):
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ "
    ciphertext = ""
    for i in range(0, len(plaintext)):
        character = plaintext[i]
        ciphertext = ciphertext + alphabet[(alphabet.index(character) + key) % len(alphabet)]
        for j in range(0, key):
            ciphertext = ciphertext + random.choice(alphabet)
    return ciphertext
```

## Análisis del algoritmo

El cifrado combina dos técnicas:

1. **Cifrado por desplazamiento (tipo César):** cada carácter del mensaje
   se reemplaza por el que está `key` posiciones más adelante en un alfabeto
   de 53 símbolos (`a-z`, `A-Z` y el espacio).

2. **Inserción de ruido:** después de cada carácter cifrado, se agregan
   `key` caracteres completamente aleatorios.

Por lo tanto, **por cada carácter del texto original se generan `key + 1`
caracteres** en el texto cifrado: 1 carácter real + `key` de relleno.

Esto deja una estructura periódica fija en el cifrado:
```
[real][ruido × key][real][ruido × key][real]...
```

## Explotación (criptoanálisis)

### Paso 1 — Determinar el valor de `key`

Si el mensaje original tiene `N` caracteres, entonces:
```
N × (key + 1) = 408
```

Como `N` debe ser un número entero de caracteres, `(key + 1)` tiene que ser
un **divisor exacto de 408**. Esto reduce drásticamente los valores posibles
de `key` a los correspondientes a los divisores de 408 (2, 3, 4, 6, 8, 12,
17, 24, ...), es decir `key` ∈ {1, 2, 3, 5, 7, 11, 16, 23, 33, ...}.

### Paso 2 — Reconstruir el mensaje para cada candidato

Para cada `key` candidato:
- Se toma **solo el primer carácter de cada grupo** de `(key + 1)`,
  descartando el ruido: `ciphertext[0::key+1]`.
- Se revierte el desplazamiento **restando `key`** a cada carácter real:
  `alphabet[(index - key) % 53]`.

### Paso 3 — Identificar el `key` correcto por legibilidad

Solo el `key` correcto produce texto legible; los demás generan cadenas sin
sentido (porque mezclan caracteres reales con ruido). El único candidato que
forma palabras reales es **`key = 11`**.

### Script de solución

```python
alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ "
ciphertext = "...(mensaje cifrado)..."
L = len(ciphertext)

for key in range(1, 40):
    grupo = key + 1
    if L % grupo != 0:
        continue
    letras_reales = ciphertext[0::grupo]      # saltea el ruido
    plaintext = "".join(
        alphabet[(alphabet.index(c) - key) % len(alphabet)]
        for c in letras_reales
    )
    print(f"key={key}: {plaintext!r}")
```

### Resultado

```
key=11: 'Bienvenido python al mundo de Java'
```

**Mensaje descifrado:** `Bienvenido python al mundo de Java`

Ese texto plano se ingresa en la plataforma para validar el desafío y obtener
la flag.

**Flag:** `d2b97b119484766696034172030d1495`

## Causa raíz y remediación

- **Causa raíz:** el algoritmo es un cifrado clásico por desplazamiento
  (espacio de claves trivial) al que se le agregó ruido de longitud fija y
  predecible. El ruido no aporta seguridad real porque su cantidad (`key`)
  está directamente relacionada con la estructura observable del cifrado, lo
  que permite recuperar la clave por simple análisis de la longitud.

- **Remediación / buenas prácticas:**
  1. No diseñar algoritmos de cifrado propios ("security through
     obscurity"). Usar primitivas criptográficas estándar y auditadas
     (AES-GCM, ChaCha20-Poly1305, etc.).
  2. Un cifrado seguro no debe filtrar información sobre la clave a través
     de la longitud o estructura del texto cifrado.
  3. El relleno (padding) debe ser indistinguible y no correlacionado con la
     clave; agregar ruido de longitud fija ligada a la clave es
     contraproducente.

## Herramientas usadas

- Python 3 (reconstrucción del mensaje y búsqueda de la clave por divisores)
