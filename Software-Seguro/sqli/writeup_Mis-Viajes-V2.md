# Writeup: Mis Viajes V2

## Descripción del Reto
En esta segunda versión del reto, el creador intentó solucionar la Inyección SQL que existía en los metadatos EXIF de la versión 1, agregando además nuevas funcionalidades: **Clasificación de imágenes** y **Resumen OCR** (extracción de texto de las imágenes).
El objetivo es encontrar el código ganador camuflado dentro de una imagen que pertenece a otro usuario (la víctima).

## Análisis de la Vulnerabilidad
Al analizar el comportamiento de las nuevas funcionalidades, se comprobó lo siguiente:
1. **EXIF Parcheado**: La inyección a través de `Make` y `Model` ya no funciona.
2. **IDOR Oculto**: El endpoint `GET /images/<uuid>` sigue siendo vulnerable a IDOR, pero el `user_id` de la víctima cambió respecto a la versión anterior.
3. **Inyección SQL en el OCR**: La verdadera vulnerabilidad se introdujo con la nueva funcionalidad de OCR. El texto extraído de las imágenes por el motor de OCR se inserta directamente en la base de datos de SQLite sin ser parametrizado ni sanitizado.

### El Bloqueo Principal (Por qué fallaban los payloads iniciales)
Durante la explotación activa, los payloads clásicos como `' || (SELECT ...) || '` fallaban por dos razones muy sutiles:
1. **Comportamiento del OCR**: Los motores OCR tienden a deformar o ignorar las comillas simples de apertura si están aisladas. Para estabilizar la lectura, es necesario anclarlas con un número (ej. `9'`).
2. **Cambio de Esquema**: En la versión 1, la tabla se llamaba `images`. En la versión 2, el desarrollador la renombró a `imagenes` (en español). Cualquier payload que intentara hacer un `FROM images` generaba un error fatal de SQLite (`no such table`), lo que devolvía un error 500 en el servidor y descartaba la imagen (mostrando un error genérico en el frontend).

## Explotación

### Paso 1: Extracción del UUID de la Víctima
Sabiendo que el nombre correcto de la tabla es `imagenes` y que debemos anclar las comillas, generamos una imagen que contenga el siguiente texto explícito para que el OCR lo lea:

```sql
9'||(SELECT group_concat(id||char(58)||user_id) FROM imagenes)||'9
```

*Nota: Se usa `char(58)` en lugar de `:` porque el OCR también puede deformar los dos puntos aislados.*

Al subir esta imagen, la base de datos evalúa la inyección y el campo "Resumen OCR" devuelve el volcado de todos los IDs e imágenes del sistema. Identificamos que el usuario víctima (`01d4832e-485a-4e98-b97e-d558c4cc95d1`) posee las imágenes con `id` 3, 4 y 5.

### Paso 2: Explotación del IDOR y Análisis Stego
Usando el `user_id` de la víctima, accedemos al endpoint vulnerable:
`GET /images/01d4832e-485a-4e98-b97e-d558c4cc95d1`

Esto nos devuelve la ruta de las imágenes de la víctima. Al descargar y revisar la imagen `id=4` (un atardecer en un lago en formato PNG), notamos que ajustando el auto-contraste de la esquina inferior derecha (sobre la zona oscura de pasto y rocas), aparece texto gris tenue camuflado directamente sobre los píxeles.

Ese texto es la flag:
`03ed8e6565c88b8377539855c7baf663`

## Conclusión
El desarrollador confió en que el output de una herramienta de IA (OCR) era seguro por naturaleza, olvidando la regla de oro: **Toda entrada, sin importar si viene del usuario o de una herramienta de procesamiento intermedia, debe ser sanitizada antes de tocar la base de datos.**

---
*Autor: Lucas*
