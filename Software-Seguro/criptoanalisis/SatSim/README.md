# Reto 50: SatSim (Criptoanálisis)

## 1. Enunciado y Análisis del Tráfico
Estamos interceptando tráfico satelital entre una estación de control y un satélite. El formato de la trama es de 16 bytes:
- **CMD_ID** (2 bytes)
- **SEQ** (2 bytes)
- **PAYLOAD** (12 bytes)

El objetivo es salvar la sociedad inyectando un comando `THRUSTER_FIRE` (CMD_ID `0x0003`) con los parámetros:
- `delta_v > 50`
- `duration_ms > 2000`

Capturamos 2 tramas en el sniffer:
1. **SET_ATTITUDE** (CMD_ID `0x0001`): `79fb5ace737e5f57f7886498e42bc988`
2. **SAFE_MODE** (CMD_ID `0x0005`): `79ff5acd737f9e1ff78ace081bd5c04e`

## 2. Modelado de la Causa Raíz
Esta vulnerabilidad demuestra una falla crítica clásica en criptografía: **Reutilización de Keystream (Key Reuse) en un cifrado de flujo**. 

En sistemas de cifrado de flujo (como RC4 o AES en modo CTR), el texto claro ($P$) se combina con un flujo de claves ($K$) mediante la operación matemática **XOR ($\oplus$)**:
$$C = P \oplus K$$

El fallo grave ocurre cuando el sistema emplea el **mismo Keystream ($K$)** para diferentes mensajes. Esto permite un **Ataque de Texto Claro Conocido (KPA)**: 
Si podemos adivinar o conocer partes del texto claro de una trama capturada, podemos revelar $K$ ($K = C \oplus P$) y usar ese mismo $K$ para cifrar nuestros propios comandos arbitrarios.

## 3. Resolución Técnica y Criptoanálisis (PoC)

Vamos a deducir el flujo de claves $K$ analizando la Trama 2 (`SAFE_MODE`).
La estructura del Payload para `SAFE_MODE` incluye 11 bytes nulos (`0x00`) seguidos de 1 byte con el `reason_code` (que sabemos que puede ser 0, 1, 2 o 3).
Sabiendo que cualquier valor procesado mediante XOR con `0x00` da como resultado el mismo valor ($X \oplus 0 = X$), podemos extraer directamente la clave observando el texto cifrado.

- **Trama 2 (Cifrada):** `79 ff 5a cd 73 7f 9e 1f f7 8a ce 08 1b d5 c0 4e`
- **Texto claro parcial (`SAFE_MODE`):** `00 05 [SEQ] 00 00 00 00 00 00 00 00 00 00 00 [CODE]`

Al aplicar XOR entre el texto cifrado y lo que sabemos del texto claro, derivamos la clave estática casi completa:
**Keystream $K$**: `79 fa 5a cf 73 7f 9e 1f f7 8a ce 08 1b d5 c0 4e` *(Asumiendo que el SEQ era `00 02` y reason code `00`)*.

### Forjando el comando maligno (`THRUSTER_FIRE`)
Para enviar nuestro propio payload, necesitamos:
- `CMD_ID`: `00 03`
- `SEQ`: `00 03` (El correlativo que sigue)
- `PAYLOAD`: 8 bytes nulos + `duration_ms` + `delta_v`.
  - Usaremos `duration_ms` = 4096 (`0x10 0x00`) para cumplir $> 2000$.
  - Usaremos `delta_v` = 256 (`0x01 0x00`) para cumplir $> 50$.

**Nuestro Payload en crudo ($P_{nuevo}$):**
`00 03 00 03 00 00 00 00 00 00 00 00 10 00 01 00`

Ciframos nuestro payload aplicando $C_{nuevo} = P_{nuevo} \oplus K$:
- Byte 0: `00` $\oplus$ `79` = `79`
- Byte 1: `03` $\oplus$ `fa` = `f9`
- Byte 2: `00` $\oplus$ `5a` = `5a`
- Byte 3: `03` $\oplus$ `cf` = `cc`
- Bytes 4-11: Se mantienen igual que $K$ porque el texto claro son ceros (`73 7f 9e 1f f7 8a ce 08`)
- Byte 12: `10` $\oplus$ `1b` = `0b`
- Byte 13: `00` $\oplus$ `d5` = `d5`
- Byte 14: `01` $\oplus$ `c0` = `c1`
- Byte 15: `00` $\oplus$ `4e` = `4e`

**Carga útil hexadecimal maliciosa resultante:**
```text
79f95acc737f9e1ff78ace080bd5c14e
```

*Nota: Como la clave rotaría dinámicamente cada 5 segundos en el reto real, hemos desarrollado el script `solver.html` que automatiza todo este proceso matemáticamente permitiéndote obtener la trama de inyección en milisegundos.*

**Flag Obtenida:**
```text
d80aeab9ea6de86f5004d9acdb481c50
```

## 4. Remediación y Buenas Prácticas (OWASP)
1. **Gestión correcta del Nonce/IV:** Jamás se debe reutilizar el Vector de Inicialización (IV) o el Nonce cuando se utiliza cifrado de flujo (o cifrados de bloque en modo CTR/GCM). Un IV único asegura que el Keystream $K$ nunca se repita, haciendo imposible este ataque.
2. **Cifrado Autenticado (AEAD):** El cifrado por sí solo garantiza *confidencialidad*, pero no previene modificaciones (falta de *integridad*). Los sistemas críticos deben emplear esquemas como **AES-GCM** o añadir códigos de autenticación de mensajes (HMAC) para que el servidor (o satélite) rechace cualquier trama modificada.
3. **Firmas Digitales Asimétricas:** En infraestructuras críticas (satélites, IoT de grado militar), las órdenes ejecutivas deberían estar firmadas con algoritmos asimétricos (como ECDSA) por la estación base, para imposibilitar su falsificación incluso si se comprometen las claves de sesión.
