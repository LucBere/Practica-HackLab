# Desafío - Revisor de videos (HackLab)

**Plataforma:** HackLab (SoftwareSeguro)  
**Edición:** HackLab 2026  
**Categoría:** XSS (Stored XSS / Contexto de Atributo HTML)  
**Autor:** adonaissh  

---

## 📌 Enunciado

> En esta plataforma los usuarios creadores proponen videos y un administrador los revisa para decidir si los acepta o los rechaza.
>
> **Credenciales provistas:**
> - Usuario: `creador`
> - Contraseña: `MachineContent`
>
> **Funcionalidad de simulación de bot/admin:**
> Tenés preparado un ataque de Ingeniería Social que hace que el administrador visite una URL del desafío (permitido una vez por minuto).
>
> **Objetivo:** Lograr que el administrador acepte un video propuesto. Al pasar a estado *"aceptado"*, la plataforma entrega un hash ganador que es la flag para ingresar al juez.

---

## 🔍 Análisis Inicial y Reconocimiento

Al iniciar sesión como `creador`, la aplicación presenta una interfaz para enviar videos a revisión:
- Un formulario con un único input: `url` (con placeholder tipo `https://www.youtube.com/watch?v=...`) protegido por Cloudflare Turnstile.
- Una sección de **"Videos en cola"** (`cola-creador`) donde se listan los envíos pendientes del usuario.

### Inspección del Front-end (`/static/app.js`)

Se descargó y analizó el archivo `/static/app.js`. Aspectos críticos del funcionamiento:
1. **Gestión de sesión:** Utiliza JWT almacenado en `localStorage` (`TOKEN_KEY = "jwt"`), enviado en la cabecera `Authorization: Bearer <token>`.
2. **Roles:** `creador` y `admin`.
3. **Renderizado de la cola:** La función `cargarCola()` del admin y `cargarColaCreador()` renderizan los videos usando plantillas de texto dinámicas en JavaScript.

```javascript
cont.innerHTML = videos.map(v => `
  <li class="video estado-${esc(v.estado)}" data-id="${esc(v.id)}">
    <div class="miniatura">
      ${v.miniatura ? `<img src="${esc(v.miniatura)}" alt="${v.titulo}">` : ""}
    </div>
    <div class="info">
      <h3 class="titulo">${esc(v.titulo)}</h3>
      ...
      <div class="acciones">
        <span class="estado">${esc(v.estado)}</span>
        ${v.estado === "pendiente" ? `
          <button data-accion="aceptado" data-id="${esc(v.id)}">Aceptar</button>
          <button data-accion="rechazado" data-id="${esc(v.id)}">Rechazar</button>
        ` : ""}
      </div>
    </div>
  </li>
`).join("");
```

---

## 🔬 Identificación de la Vulnerabilidad (Stored XSS en Atributo `alt`)

Al examinar detalladamente la función de renderizado:
- La mayoría de los campos son saneados mediante la función auxiliar `esc()`:
  ```javascript
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }
  ```
- **El fallo crítico:** En la etiqueta `<img>` de la miniatura:
  ```javascript
  ${v.miniatura ? `<img src="${esc(v.miniatura)}" alt="${v.titulo}">` : ""}
  ```
  `v.miniatura` está escapada con `esc()`, **pero `${v.titulo}` se inserta crudo y sin sanitizar** directamente en el atributo HTML `alt`.

Si el título de un video contiene comillas dobles (`"`), es posible escapar del atributo `alt` e inyectar un controlador de eventos (como `onload`, ya que la imagen carga legítimamente desde `src`), ejecutando JavaScript arbitrario en el contexto del navegador que visualice la cola.

---

## 🚀 Explotación

### 1. Inyección y Payload XSS

Como el objetivo es que el administrador acepte el video, no hace falta extraer o exfiltrar el JWT de `localStorage`. La función `cambiarEstado(id, 'aceptado')` o el propio botón `button[data-accion="aceptado"]` ya existen en el DOM de la página del administrador.

Un título malicioso con la siguiente estructura:
```html
x" onload="document.querySelector('button[data-accion=\'aceptado\']').click()"
```
provoca que el navegador renderice:
```html
<img src="https://..." alt="x" onload="document.querySelector('button[data-accion=\'aceptado\']').click()">
```

### 2. Aceptación del video y resolución

El backend extrae los metadatos del video (título y miniatura) a partir de la URL enviada. Al procesar el recurso con el payload inyectado en el título, el video queda en estado `pendiente` con el XSS latente en la cola.

Se disparó la acción de ingeniería social para forzar la visita del administrador a la interfaz interna:
1. El bot administrador accede a la consola `/`.
2. La función `cargarCola()` consulta `/api/videos` e inserta el elemento HTML con el atributo `alt` roto.
3. Al terminar de cargar la imagen en el navegador del administrador, el evento `onload` se dispara de inmediato.
4. El script presiona automáticamente el botón `Aceptar` (o ejecuta la llamada a `/api/videos/<id>/estado` con su token de administrador).
5. El estado del video transiciona a `aceptado`.

### 3. Recuperación de la Flag

Al refrescar la vista de creador (`cargarColaCreador()`), el video figura aceptado y la API devuelve el campo especial `hash_ganador`:

```html
<p class="hash-ganador">🏆 Hash ganador: <code>7295a63194c3ce7c1a752c6e07920e9d</code></p>
```

---

## 🏁 Flag

```text
7295a63194c3ce7c1a752c6e07920e9d
```

---

## 🛡️ Causa Raíz y Recomendaciones

- **Causa Raíz:** Falta de saneamiento contextual en atributos HTML (CWE-79). Aunque se implementó la función `esc()` para prevenir XSS en la mayoría de las variables, el desarrollador omitió aplicarla sobre `${v.titulo}` exclusivamente dentro del atributo `alt` de la etiqueta `<img>`.
- **Recomendaciones:**
  - **Uso estricto de saneamiento en todos los puntos de inserción:** Aplicar siempre el escapado de caracteres (`esc(v.titulo)`) o, preferentemente, manipular el DOM mediante propiedades seguras (`img.alt = v.titulo;` o `textContent`) en lugar de concatenar cadenas en `innerHTML`.
  - **Content Security Policy (CSP):** Configurar una política CSP estricta que inhabilite la ejecución de scripts inline (`unsafe-inline`) y manejadores de eventos en línea (`onload`, `onerror`).
  - **Almacenamiento seguro de tokens:** Evitar almacenar credenciales sensibles (JWT) en `localStorage`, utilizando en su lugar cookies `HttpOnly` y `SameSite` para mitigar el impacto en caso de que ocurra un XSS.
