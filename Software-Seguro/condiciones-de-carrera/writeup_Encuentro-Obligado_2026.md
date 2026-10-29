# Desafío - Encuentro Obligado (HackLab)

**Plataforma:** HackLab (SoftwareSeguro)  
**Edición:** HackLab 2026  
**Categoría:** Condiciones de carrera / IDOR / Lógica de negocio  
**Autor:** adonaissh  

---

## 📌 Enunciado

> En tu próximo vuelo necesitás sentarte al lado del CEO de una empresa muy importante (**Gutierrez**). Tenés el dato de que todavía no hizo el check-in, por lo que no seleccionó asiento.
>
> El CEO es una persona extremadamente desconfiada y posee información interna de quién ocupa cada lugar, por lo que siempre elegirá un asiento distante al tuyo. Tenés que buscar la manera de que no le quede otra opción y elija obligatoriamente el asiento contiguo.
>
> **Tus credenciales de check-in:**
> - Código de check-in: `ACK-129`
> - Apellido: `BUSTAMENTE`
>
> **Mecanismo de simulación:**
> Un trigger de ingeniería social permite inducir el ingreso del CEO a realizar su check-in una vez por minuto mediante el envío del dominio del desafío.
>
> **Objetivo:** Forzar al CEO a sentarse al lado tuyo para obtener la flag de confirmación.

---

## 🔍 Análisis Inicial y Reconocimiento

Al autenticarse en el portal de la aerolínea (*Flyghter*) con `ACK-129` / `BUSTAMENTE`:
- Se asigna un identificador de sesión y se presenta la cabina del avión con **60 asientos** distribuidos en columnas de 4 asientos cada una.
- Casi la totalidad de los asientos figuran en estado `ocupado`.
- Solo existen unos pocos asientos en estado `libre`: **11, 17, 21, 22, 27**.
- En la fila contigua de la columna central, los asientos **21** y **22** están lado a lado.
- El usuario selecciona y confirma su propio asiento en el **21**.
- Asientos libres restantes en el avión:
  - Distantes: **11, 17, 27**
  - Contiguo al propio: **22**

Si se activa la visita del CEO en este estado, el algoritmo del bot elige automáticamente uno de los asientos lejanos (**11, 17 o 27**) para evitar sentarse junto al usuario.

---

## 🔬 Identificación de las Vulnerabilidades

### 1. IDOR en el Módulo de Reclamos (`/reclamos`)
Al pie de página se expone un enlace: `¿Algún problema? Cargá un reclamo →` (`/reclamos`).
- El formulario permite ingresar un tipo de reclamo (*"Me equivoqué de asiento"*) y el **número de asiento**.
- **Falla:** La API no comprueba que el asiento pertenezca al usuario autenticado. Se pueden emitir reclamos sobre asientos ajenos o incluso sobre asientos aún libres/desocupados.

### 2. Credenciales SIP / VoIP Expuestas
En la sección de contacto y soporte de la página principal figuran credenciales de centralita telefónica:
```text
VoIP (SIP): sip:reclamos@softwareseguro.sip.twilio.com
Usuario: softwareseguro
Contraseña: b6b577fd12aa7e1df8d60735ef56fc2eA
```
Mediante este canal o la interacción con el flujo de soporte, los reclamos abiertos pasan a un estado de auditoría (*"En análisis"*).

### 3. Bloqueo Temporal y Condición de Carrera (Race Condition / Timing)
Cuando un asiento entra en estado de reclamo/análisis:
- En el mapa de la cabina cambia su estado visual y funcional a **`bloqueado`**, impidiendo que cualquier pasajero (incluido el CEO) lo elija durante el check-in.
- **Ventana de tiempo limitada:** Este bloqueo es **efímero y temporal**; decae automáticamente tras una ventana de tiempo predefinida si no se resuelve, volviendo a quedar `libre`.

---

## 🚀 Explotación

Para obligar al CEO a ocupar el asiento **22** (el único adyacente a nuestro asiento **21**), es imperativo que los otros 3 asientos libres (**11, 17 y 27**) se encuentren bloqueados de forma simultánea al momento exacto en que el CEO procesa su elección.

### 1. Asignación del asiento propio
Se confirma el check-in propio en el asiento **21**:
```http
POST /asiento HTTP/1.1
Content-Type: application/x-www-form-urlencoded

numero=21
```

### 2. Bloqueo masivo y sincronizado de asientos distantes
Aprovechando el IDOR en el formulario de reclamos, se disparan solicitudes consecutivas y rápidas para bloquear los asientos que el CEO preferiría tomar:
1. Reclamo sobre asiento `11` $\rightarrow$ Pasa a `bloqueado`.
2. Reclamo sobre asiento `17` $\rightarrow$ Pasa a `bloqueado`.
3. Reclamo sobre asiento `27` $\rightarrow$ Pasa a `bloqueado`.

Con esto, el mapa de asientos disponibles queda configurado así:
- Asiento 21: *Tu asiento* (ocupado por Bustamente).
- Asiento 11: *Bloqueado*.
- Asiento 17: *Bloqueado*.
- Asiento 27: *Bloqueado*.
- **Asiento 22: *Único asiento libre en todo el vuelo*.**

### 3. Disparo del Bot (Ingeniería Social) dentro de la ventana de carrera
Inmediatamente y antes de que expire el TTL del bloqueo de los asientos 11, 17 y 27, se acciona el endpoint de ingeniería social para que el CEO ingrese a realizar su check-in.

Al no existir ningún asiento lejano disponible, el algoritmo de asignación se ve forzado a reservar el asiento **22**, contiguo al nuestro.

### 4. Mensaje de Éxito y Flag

El sistema confirma la asignación obligada:
> *"Gutierrez quedó sentado a tu lado"*

```text
==================================================
                 ¡¡¡LO LOGRASTE!!!
         Gutierrez quedó sentado a tu lado
==================================================

Flag: 9dbe0d2c19b5881c47cd6a97b23e70ff
```

---

## 🏁 Flag

```text
9dbe0d2c19b5881c47cd6a97b23e70ff
```

---

## 🛡️ Causa Raíz y Recomendaciones

- **Falta de Control de Acceso (IDOR / Broken Access Control - CWE-639):** La aplicación permitía reportar incidentes o reclamos sobre cualquier asiento sin verificar si el usuario emisor poseía un billete o reserva efectiva sobre dicho número.
- **Efectos secundarios de denegación de servicio lógica (DoS de asientos):** Cambiar el estado de un recurso compartido a `bloqueado` a partir de una acción no verificada del cliente permite a un atacante denegar la disponibilidad de asientos a otros pasajeros.
- **Condición de carrera / ventana de oportunidad (Race Window):** La existencia de bloqueos temporales no atómicos permite manipular el estado del inventario para inducir decisiones forzadas en otros clientes concurrentes.
- **Recomendaciones:**
  - Validar server-side la titularidad del asiento antes de procesar reclamos o alterar estados en el mapa del vuelo.
  - Implementar rate limiting por usuario en el módulo de reclamos e impedir bloqueos automáticos de inventario sin intervención de un operador autenticado.
