# El blog de Pepe — Writeup

## Descripción del desafío

**Plataforma:** Software Seguro (HackLab 2023)  
**Categoría:** XSS (Cross-Site Scripting Almacenado)  
**Objetivo:** El político Pepe tiene un blog donde los usuarios pueden dejar peticiones. Necesitamos lograr que Pepe, con su cuenta, publique el comentario exacto: `"Voy a derogar la ley 1542-A"`. Para ello, disponemos de una funcionalidad que simula un ataque de ingeniería social, obligando a un bot (Pepe) a visitar y renderizar el blog.

## Reconocimiento

Tenemos acceso con credenciales de bajo privilegio (`teny : Teny1805`). Al ingresar, vemos un formulario simple:
- Un campo para enviar una "Petición".
- Un panel externo para "engañar a Pepe" pasándole el dominio del reto, lo que desencadena que el bot visite la página principal del blog donde se muestran los comentarios.

## Vulnerabilidad

El formulario de peticiones es vulnerable a **Stored XSS (Cross-Site Scripting Almacenado)**. 

La aplicación no sanitiza (ni codifica entidades HTML) el texto ingresado en el campo "Petición". Por lo tanto, si enviamos etiquetas HTML o código JavaScript (como `<script>...</script>`), estas se guardarán tal cual en la base de datos. Cuando el bot de Pepe ingresa al blog, su navegador leerá nuestro comentario, interpretará las etiquetas `<script>` y ejecutará silenciosamente el código malicioso bajo la sesión autenticada de Pepe.

## Explotación

### 1. Intercepción del formulario legítimo
Analizando el tráfico de red (Network / Red) con DevTools al enviar un comentario normal, notamos que la petición es un `POST` al endpoint `comentarios.php` y que el parámetro que contiene el texto se llama `txtComentario`.

### 2. Creación del Payload JavaScript
Para que Pepe publique en nuestro nombre sin que el script nos afecte a nosotros mismos (y genere un bucle infinito), inyectaremos un código que interactúe directamente con el DOM de la página. El script verificará quién es el usuario logueado, llenará el formulario y simulará un clic en el botón de enviar.

```html
<script>
function enviarComentario() {
    // Obtenemos el nombre del usuario actual desde la interfaz
    var usuario = document.getElementById("nombre_usuario").innerText;
    
    // Si el usuario NO es el atacante (teny), significa que el bot (Pepe) entró
    if (usuario != "teny") {
        document.getElementsByName("txtComentario")[0].value = "Voy a derogar la ley 1542-A";
        document.getElementsByName("btnEnviar")[0].click();
    } else {
        console.log("Soy teny y no envio el comentario");
    }
}

// Ejecutamos la función una vez que la página cargue completamente
window.addEventListener("load", enviarComentario);
</script>
```

**Por qué este payload es más efectivo:**
1. **Evita el auto-ataque:** Al incluir la condición `if (usuario != "teny")`, evitamos que nuestro propio navegador ejecute el ataque infinitamente cada vez que recargamos la página.
2. **Evasión de controles:** Al usar `.click()` sobre el formulario original, el navegador incluye automáticamente cualquier token de seguridad (CSRF) o campo oculto que la página requiera, lo cual puede fallar al hacer un `fetch` crudo.

### 3. Ejecución
1. El atacante (`teny`) publica la petición maliciosa con el código `<script>...` en el blog.
2. Se utiliza la herramienta de Ingeniería Social suministrando el dominio del reto para obligar al bot a visitar la página.
3. El bot de Pepe carga la página, su navegador interpreta el código JavaScript y realiza el POST silencioso.
4. Como resultado, aparece un nuevo comentario a nombre de `pepe` derogando la ley, lo que desencadena que la plataforma nos entregue la flag.

## Resultado / Flag
**Flag:** `c4c309a13c8fc4c5f48e72e4154dc812`

## Causa raíz y remediación

- **Causa raíz:** La aplicación almacena la entrada del usuario (`txtComentario`) en la base de datos y luego la renderiza directamente en el HTML (DOM) sin sanitizarla ni escaparla. Esto permite que cualquier etiqueta HTML o código JavaScript introducido sea interpretado como código legítimo por el navegador de las víctimas que visualizan la página (Stored XSS).
- **Remediación recomendada (OWASP):** 
  1. **Codificación de salida (Output Encoding):** Antes de renderizar cualquier entrada controlada por el usuario en el navegador, se deben convertir los caracteres con significado especial en HTML (como `<`, `>`, `"`, `'`, `&`) en sus correspondientes entidades HTML (ej. `&lt;`, `&gt;`).
  2. **Validación de entrada:** Rechazar caracteres que no sean estrictamente necesarios para el comentario.
  3. **Content Security Policy (CSP):** Implementar una cabecera HTTP CSP estricta que prohíba la ejecución de scripts *inline* (`<script>...</script>`).
