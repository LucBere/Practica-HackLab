# Writeup — CTF "Vulpasar" (Forense Digital)

## 1. Planteo inicial y categoría

El enunciado daba estas señales clave:

- *"Vulpasar es un delincuente con múltiples personalidades"* → sugiere varias cuentas de usuario en el sistema, no un solo "camino".
- *"uno de los más hostiles que han existido"* → anti-forense: historiales borrados, señuelos, trampas.
- *"Se capturó una notebook... almacena un archivo muy valioso llamado `ev`"* → el objetivo es **encontrar un archivo específico**, no explotar un servicio.
- Te dan usuario y clave (`ch10xo` / `vulpasar`) de entrada → no hay que vulnerar nada para entrar, el desafío arranca **adentro** del sistema.
- Te entregan una imagen `.ova` con hash para verificar → análisis forense de una VM, no un CTF web/pwn.

Conclusión: categoría **forense / análisis de sistema comprometido**, con enumeración de usuarios y búsqueda de evidencia.

## 2. Preparación del entorno

1. Descarga de `vulpasar.ova` desde el enlace oficial.
2. Verificación de integridad: `sha256sum vulpasar.ova` contra el hash publicado (`c4a4eacc...bde15a`), para asegurar que la imagen no estaba corrupta ni alterada.
3. Importación en VirtualBox, en red aislada, siguiendo la cadena de custodia sugerida por el enunciado.
4. Ingreso con las credenciales provistas: `ch10xo` / `vulpasar`.

## 3. Enumeración inicial del sistema

```bash
id; whoami; hostname
cat /etc/passwd | grep -v nologin
ls -la /home/*
sudo -l
```

Resultados clave:

- Usuarios con shell interactiva: **`ch10xo`**, **`phant`**, **`ch10xosudo`**.
- `ch10xo` pertenece al grupo `sudo` con permisos `(ALL : ALL) ALL` → acceso total vía `sudo`, usando la misma contraseña de login.
- Los homes de `phant` y `ch10xosudo` estaban bloqueados a nivel de permisos de directorio (`ls` daba "permiso denegado" sin sudo).

Esto confirmó la lectura de "múltiples personalidades": tres cuentas, cada una a revisar.

## 4. Revisión de las cuentas

Con `sudo ls -laR /home/phant /home/ch10xosudo` se exploraron ambos homes bloqueados:

- **`ch10xosudo`**: solo archivos de configuración por defecto (GTK, LibreOffice, Hexchat vacío). Descartado como señuelo de nombre ("sudo" en el nombre, pero sin nada adentro).
- **`phant`**: el relevante. Contenía:
  - ~55 archivos `.txt` con nombres de hash (ej. `1020bb96f31a.txt`), cada uno con una frase motivacional sobre programación. Eran **señuelos**: ni su nombre coincidía con el hash de su contenido, ni tenían relación con el objetivo.
  - Un directorio oculto **`.fakes/`**, con un archivo `archivo.zip` de 381 bytes. El nombre del directorio ("fakes" = falsos) era en sí mismo una pista doble: por un lado reforzaba que los `.txt` eran señuelo, por otro invitaba a sospechar también del zip — pero resultó ser el contenedor real del archivo buscado.
- El `.bash_history` de `phant` mostraba que el propio usuario había borrado su historial (`rm .bash_history`), consistente con el perfil "hostil"/anti-forense de la consigna.

## 5. Encontrar el archivo dentro del zip

```bash
7z l -slt .fakes/archivo.zip
```

El listado mostró que el zip contenía:

```
fundamental/
fundamental/ev   (33 bytes, Method = AES-256 Store, Encrypted = +)
```

Ahí apareció formalmente el archivo **`ev`** que pedía el enunciado, pero cifrado con **AES-256**, no con el cifrado clásico ZipCrypto de versiones viejas de zip.

Esto fue clave para descartar una vía de ataque:

## 6. Por qué la fuerza bruta (y las herramientas clásicas) no iban a funcionar

- **`unzip`** (el estándar de Linux) solo soporta hasta cierta versión de compresión: falló con *"need PK compat. v5.1 (can do v4.6)"*. No pudo ni leer el contenido cifrado.
- **`fcrackzip`**: esta herramienta está diseñada para romper el cifrado **ZipCrypto** (el "viejo" de los `.zip`), que es vulnerable a ataques de texto plano conocido y de diccionario rápido. **No tiene soporte para AES**. Correrla contra este archivo era, literalmente, atacar la cerradura equivocada: nunca iba a encontrar nada, sin importar cuántas palabras probara.
- **AES-256** es un cifrado simétrico fuerte sin vulnerabilidades conocidas de ese tipo. La única vía de ataque práctica es probar contraseñas candidatas una por una (diccionario) contra el propio AES, usando una herramienta que sepa manejarlo (7-Zip, `hashcat` modo 13600, `pyzipper`, etc.).
- Hacer **fuerza bruta real** (probar todas las combinaciones posibles de caracteres) contra una contraseña de longitud y alfabeto desconocidos, con AES-256, es computacionalmente inviable en un tiempo razonable sin hardware dedicado (GPUs) y sin acotar antes el espacio de búsqueda.
- Por eso la estrategia correcta no era "fuerza bruta a ciegas", sino:
  1. Probar un **diccionario dirigido** con palabras del contexto del CTF (nombres de usuario, términos del enunciado, etc.) — esto se intentó y no dio resultado.
  2. Priorizar la **búsqueda de la contraseña en texto plano** dentro del propio sistema comprometido, que es el enfoque forense correcto: en un CTF de este tipo, la clave casi siempre está escondida en algún artefacto del sistema (historial, configuración, navegador, credenciales guardadas), no pensada para romperse por cómputo.

## 7. Callejones sin salida explorados (y por qué se descartaron)

Antes de llegar a la pista correcta, se revisaron y descartaron:

- `cloud-init` (`/var/lib/cloud/.../user-data.txt`): solo tenía hashes de contraseña (`$6$...`, SHA-512) de `root` y `ch10xo`, nada de `phant` ni relacionado al zip.
- `/root/.bash_history`: reveló manipulación de permisos de `ch10xo` (quitarlo y volver a agregarlo al grupo `sudo`, reseteo de contraseña) y un `su - phant` sin contraseña visible, pero no la clave del zip.
- Crontabs, correo local (`/var/mail`), procesos activos, puertos abiertos, discos adicionales, `/opt`, `/srv`: todo limpio o sin relación.
- Configuración de Hexchat/Trolltech de `phant`: sin credenciales.
- Historial de navegación de Firefox (`moz_places`): solo mostraba navegación genérica (Google, Facebook, TikTok) — en un primer vistazo parecía irrelevante.

## 8. La pista decisiva: el juego de palabras "Vulpasar" → Firefox

Acá fue clave no descartar lo de Facebook/Firefox tan rápido. El razonamiento:

- **Vulpasar** deriva de *vulpino*, relativo al **zorro** (del latín *vulpes*).
- **Firefox** es literalmente "zorro de fuego".
- El sistema tenía **Firefox instalado y usado** (perfil con historial, cookies, sesión de Facebook), y el apodo del delincuente apuntaba justo a esa aplicación.

Esto llevó a revisar, dentro del perfil de Firefox de `ch10xo`, no solo el historial sino las **credenciales guardadas** (`logins.json`), que es donde la gente suele dejar contraseñas reutilizadas.

```bash
cd ~/snap/firefox/common/.mozilla/firefox/uwup0wrj.default/
cat logins.json
```

Esto mostró una entrada cifrada de **Facebook**:

```json
{"hostname":"https://www.facebook.com","encryptedUsername":"...","encryptedPassword":"..."}
```

Cifrada con **NSS** (el motor criptográfico de Firefox), sin contraseña maestra configurada (se confirmó al no encontrar protección en `pkcs11.txt`), lo que la hacía descifrable directamente.

## 9. Descifrado de las credenciales de Firefox

Se copió el perfil completo a `/tmp/ff_profile` para trabajar sin tocar la evidencia original, y se escribió un script en Python usando `ctypes` para invocar `libnss3.so` (la librería de NSS que ya está instalada junto con Firefox) y así desencriptar los campos:

```python
import ctypes, base64, json, os

PROFILE = "/tmp/ff_profile"
nss = ctypes.CDLL("libnss3.so")

class SECItem(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint), ("data", ctypes.c_char_p), ("len", ctypes.c_uint)]

nss.NSS_Init(f"sql:{PROFILE}".encode())
nss.PK11_GetInternalKeySlot.restype = ctypes.c_void_p
slot = nss.PK11_GetInternalKeySlot()
nss.PK11_Authenticate(slot, True, None)

def decrypt(b64data):
    raw = base64.b64decode(b64data)
    inp = SECItem(0, raw, len(raw))
    outp = SECItem(0, None, 0)
    nss.PK11SDR_Decrypt(ctypes.byref(inp), ctypes.byref(outp), None)
    return ctypes.string_at(outp.data, outp.len).decode(errors="replace")

with open(os.path.join(PROFILE, "logins.json")) as f:
    data = json.load(f)

for entry in data["logins"]:
    print("Host:", entry["hostname"])
    print("User:", decrypt(entry["encryptedUsername"]))
    print("Pass:", decrypt(entry["encryptedPassword"]))
```

Resultado:

```
Host: https://www.facebook.com
User: miguel78.argentina@hotmail.com
Pass: resto34
```

## 10. Uso de la contraseña recuperada

Se probó `resto34` directamente contra el zip cifrado con AES, usando 7-Zip (que sí soporta AES):

```bash
7z t -presto34 .fakes/archivo.zip
# → Everything is Ok
```

Confirmado. Se extrajo:

```bash
7z x -presto34 .fakes/archivo.zip -ofundamental_out -y
cat fundamental_out/fundamental/ev
```

## 11. Resultado final

El archivo `ev` contenía:

```
660b416167e7fd839bc06c61bb5a184b
```

Un string hexadecimal de 32 caracteres (formato típico de hash MD5 o token/flag), que es el contenido del "archivo muy valioso" que pedía encontrar la consigna.

## 12. Cadena lógica completa, resumida

```
Enunciado ("múltiples personalidades", "hostil", "archivo ev")
        ↓
Categoría: forense / enumeración de usuarios en sistema comprometido
        ↓
3 usuarios → ch10xo (acceso), ch10xosudo (señuelo vacío), phant (relevante)
        ↓
home de phant: .txt señuelos + .fakes/archivo.zip (AES-256, cifrado)
        ↓
unzip falla (no soporta AES) → fcrackzip inútil (solo rompe ZipCrypto, no AES)
        ↓
Fuerza bruta contra AES-256 descartada por inviabilidad computacional
        ↓
Diccionario dirigido (contexto del CTF) → sin resultado
        ↓
Búsqueda de la clave en el propio sistema (enfoque forense correcto)
        ↓
Pista "Vulpasar" = vulpino = zorro → Firefox ("zorro de fuego") instalado
        ↓
logins.json de Firefox → credencial cifrada de Facebook (NSS)
        ↓
Descifrado vía libnss3.so (ctypes) → miguel78.argentina@hotmail.com / resto34
        ↓
resto34 = contraseña del zip AES-256
        ↓
Extracción de fundamental/ev → 660b416167e7fd839bc06c61bb5a184b
```

La lección metodológica central: frente a un cifrado fuerte como AES-256, la vía de ataque no es la fuerza bruta ni herramientas pensadas para cifrados débiles (ZipCrypto), sino explotar que las personas reutilizan contraseñas — y en un sistema comprometido, esas contraseñas casi siempre quedan guardadas en algún gestor de credenciales del propio equipo (en este caso, el almacén de contraseñas de Firefox).
