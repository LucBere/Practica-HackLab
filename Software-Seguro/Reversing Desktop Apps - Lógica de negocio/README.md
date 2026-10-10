# Reto 45: Reversing Desktop Apps - Lógica de negocio (Tetris)

## Descripción
**Objetivo:** Ganar 40,000 puntos en el juego Tetris proporcionado y obtener la bandera (flag).
**Archivo proporcionado:** `client` (ejecutable ELF).

## Análisis de Vulnerabilidades (Reversing)

El reto nos presenta un ejecutable de Linux que resulta ser un juego de Tetris. Tras un primer análisis usando el comando `file`, observamos que es un binario empaquetado con **PyInstaller**. 

### 1. Extracción del Ejecutable
Para extraer el código fuente original, utilizamos la herramienta `pyinstxtractor` sobre el binario ELF:
```bash
python3 pyinstxtractor.py client
```
Esto nos extrajo el contenido en una carpeta `client_extracted`, encontrando dentro el archivo principal compilado en bytecode de Python 3.10: `client.pyc`.

### 2. Descompilación y Desensamblado
Al intentar descompilar el archivo con `pycdc` (Decompyle++), logramos recuperar gran parte del código fuente, donde identificamos que la aplicación se conectaba al servidor `tetris-server.shared.softwareseguro.com.ar:15452` usando sockets TCP crudos.

Sin embargo, debido a limitaciones del descompilador con nuevas instrucciones de Python 3.10, la función de envío de puntos se rompió a la mitad. Para solucionar esto, analizamos el bytecode ensamblador utilizando `pycdas`:

```bash
./pycdas ../client_extracted/client.pyc > desensamblado.txt
```

### 3. Análisis de Lógica de Negocio en el Ensamblador
En el archivo desensamblado, identificamos las funciones `connect` y `_send_loop`, las cuales nos revelaron el protocolo de red:
1. **Autenticación:** El cliente envía exactamente 30 bytes con el nombre del jugador, rellenando con bytes nulos (`\x00`) los espacios faltantes.
2. **Envío de puntos:** La función `send_score` fracciona cualquier cantidad de puntos en paquetes de máximo **100 puntos** y los envía como un **único byte crudo**.
3. **Rate Limit:** El cliente oficial tiene un límite (`MAX_SEND_PER_SEC = 4`). Si se envían más paquetes por segundo, el servidor nos expulsa devolviendo el mensaje `trampa detectada`.

## Explotación (PoC)

En lugar de jugar el juego legítimamente hasta alcanzar 40,000 puntos (lo cual tomaría muchísimo tiempo debido al Rate Limit), creamos un cliente malicioso (`solve_tetris.py`) que se conecta al servidor, se identifica y le inyecta 400 paquetes de 100 puntos.

Para evadir el baneo del servidor, introdujimos un delay de **0.35 segundos** entre paquete y paquete, manteniéndonos debajo del límite de velocidad del servidor. 

Al terminar el envío de los 40,000 puntos (aprox. 140 segundos), el servidor nos responde exitosamente.

## Flag
`5c829c1139319b1b3da72d805c6c669b`

## Defensa (Remediación Académica OWASP)
Este es un caso clásico de confiar en las validaciones del lado del cliente (**CWE-602: Client-Side Enforcement of Server-Side Security**).
Para evitar esto:
1. El servidor nunca debe aceptar incrementos arbitrarios de puntaje del cliente. Toda la lógica del juego (piezas, colisiones, líneas completadas) debe validarse en el backend.
2. El cliente solo debería enviar "acciones" o "teclas presionadas", mientras el servidor computa el estado real de la partida y decide cuándo otorgar los puntos.
