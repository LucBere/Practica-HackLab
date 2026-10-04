# Aldeas Inseguras — Writeup

## Descripción del desafío

Pedro quiere comprar una nueva aldea, pero necesita al menos 5000 de oro y
le resulta difícil juntar esa cantidad.

Reglas del juego:
- Cada jugador tiene 3 recursos: oro, plata y bronce.
- Solo se permite el envío de oro a otras aldeas.
- Cada aldea puede **recibir** oro una sola vez por día.
- Cada aldea puede **enviar** oro las veces que quiera.
- Al cerrar sesión, todos los datos se resetean.

## Reconocimiento

La página de envío de mercancía es un formulario simple:

```html
<form action="/src/ctl/enviar_mercancia.ctl.php" method="POST">
  <input type="hidden" name="id_jugador_origen" value="32568">
  <select name="select_jugador_destino">
    <option value="10178">Alfonzo</option>
    <option value="1901">Juana</option>
    <option value="22358">Santiago</option>
  </select>
  <input type="text" name="txt_cantidad" ...>
</form>
```

El request real que dispara es:

```
POST /src/ctl/enviar_mercancia.ctl.php
Content-Type: application/x-www-form-urlencoded

id_jugador_origen=32568&select_jugador_destino=10178&txt_cantidad=10
```

## Vulnerabilidad

El campo `id_jugador_origen` viaja como **input oculto controlado por el
cliente**, sin ningún token que lo ate a la sesión real del usuario (IDOR —
Insecure Direct Object Reference, CWE-639). El backend confía en este valor
en lugar de determinar el jugador origen a partir de la sesión
(`PHPSESSID`).

### Primer intento (bloqueado por regla de negocio)

Modificar `id_jugador_origen` por el ID de una aldea vecina y
`select_jugador_destino` por el ID propio permite que, en teoría, cualquier
aldea "envíe" oro a cualquier otra sin su consentimiento:

```
id_jugador_origen=10178&select_jugador_destino=32568&txt_cantidad=2500
```

Esto funciona una vez, pero la regla "una vez por día" se aplica sobre el
**destino**: una vez que Pedro recibe oro, cualquier intento posterior de
recibir de otra aldea en la misma sesión es rechazado
(`Este jugador ya recibió oro`). Esto limita el abuso directo a una sola
transferencia por sesión.

Se intentó también inflar el monto declarado (`txt_cantidad`) por encima
del oro real disponible en el origen, pero el backend sí valida ese límite
y capea automáticamente al saldo real.

## Explotación

La solución es **encadenar transferencias entre las aldeas vecinas**,
usando a cada una como intermediaria antes de la transferencia final hacia
Pedro. Esto respeta la regla de "una recepción por día por aldea" porque
cada aldea intermedia solo recibe una vez, pero permite concentrar todo el
oro acumulado en la transferencia final:

1. **Alfonzo → Juana** (todo el oro de Alfonzo)
   ```
   id_jugador_origen=10178&select_jugador_destino=1901&txt_cantidad=2500
   ```
   Juana pasa de 1000 a 3500 de oro.

2. **Juana → Santiago** (todo el oro acumulado de Juana)
   ```
   id_jugador_origen=1901&select_jugador_destino=22358&txt_cantidad=3500
   ```
   Santiago pasa de 1520 a 5020 de oro.

3. **Santiago → Pedro** (todo el oro acumulado de Santiago)
   ```
   id_jugador_origen=22358&select_jugador_destino=32568&txt_cantidad=5020
   ```
   Pedro pasa de 620 a **5640** de oro, superando el objetivo de 5000.

Cada request se modifica y reenvía desde Burp Suite Repeater, interceptando
primero un envío legítimo para capturar la estructura del POST.

### Resultado

```
Has superado el desafío. Código: 4ddbc953186051c75
```

**Flag:** `4ddbc953186051c75`

## Causa raíz y remediación

- **Causa raíz:** el backend determina el jugador origen de la transacción
  a partir de un parámetro enviado por el cliente (`id_jugador_origen`), en
  lugar de obtenerlo de la sesión autenticada del usuario.

- **Remediación recomendada:**
  1. **Nunca confiar en identificadores de origen enviados por el
     cliente.** El jugador que envía el recurso debe determinarse
     exclusivamente a partir de la sesión del lado del servidor:
     ```php
     $id_jugador_origen = $_SESSION['id_jugador']; // no desde $_POST
     ```
  2. Validar en el backend que el usuario autenticado sea efectivamente el
     dueño del recurso que intenta modificar/transferir (control de acceso
     a nivel de objeto).
  3. Revisar la lógica de "una recepción por día" para que no pueda
     eludirse mediante cadenas de transferencias entre terceros: por
     ejemplo, podría limitarse también la cantidad total de oro que puede
     moverse por una misma aldea en un período de tiempo, o registrar el
     origen real de los fondos a través de la cadena de transferencias.
  4. Usar identificadores no predecibles (UUIDs) en vez de IDs secuenciales
     cortos para dificultar el descubrimiento de otros jugadores, aunque
     esto por sí solo no sustituye un control de acceso adecuado.

## Herramientas usadas

- Burp Suite Community (interceptación y repetición de requests en
  Repeater)
