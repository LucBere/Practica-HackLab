# Gran Rifa 2019 — Writeup

## Descripción del desafío

**Plataforma:** Software Seguro (HackLab)  
**Categoría:** Mass Assignment  
**Objetivo:** El amigo del protagonista, "John Backus", está registrado en la lista de compradores de una rifa pero todavía no pagó. El objetivo es cambiar el estado de pago de John Backus de "No" a "Sí" mediante la manipulación de las peticiones HTTP.

## Reconocimiento

Al ingresar a la aplicación web, se observa una tabla con varias entradas de compradores de la rifa. Una columna muestra si la persona "Está pago" o no.
Al hacer clic en el botón de edición para el registro de **John Backus**, el frontend solo permite modificar el nombre del comprador, sin ofrecer ninguna opción visible para alterar el estado de pago.

En el tráfico HTTP inicial (petición `GET`), se puede observar que los datos se transmiten en formato JSON y el registro incluye un campo booleano llamado `esta_pago`.

## Vulnerabilidad

La aplicación sufre de una vulnerabilidad de **Mass Assignment** (Asignación Masiva - *OWASP API3:2019 Broken Object Property Level Authorization*).

Cuando se edita el registro y se guardan los cambios, el cliente envía un JSON al servidor:
```json
{"comprador":"John Backus"}
```
El problema radica en que el servidor toma este JSON y actualiza automáticamente las propiedades correspondientes en la base de datos sin validar si el usuario tiene permiso para modificar ciertos campos protegidos (como el estado de pago).

## Explotación

Para explotar esta falla, se utilizó la herramienta **Burp Suite** para interceptar el tráfico entre el navegador y el servidor.

1. Se habilitó el interceptor de Burp Suite.
2. Se hizo clic en el botón de "Guardar" para editar a John Backus.
3. En la petición `POST` / `PUT` interceptada, se modificó el cuerpo del mensaje original agregando manualmente la propiedad oculta `esta_pago` con valor `true`:
   ```json
   {
     "comprador": "John Backus",
     "esta_pago": true
   }
   ```
4. Se envió la petición modificada al servidor (Forward).
5. El servidor procesó el payload modificado exitosamente, mostrando un mensaje de "el número se modificó correctamente".
6. Al recargar la página, el estado de pago de John Backus apareció como "Sí", y el sistema entregó la flag.

## Resultado / Flag

**Flag:** `ed20b8f11252a75b30d594af897c3aad`

## Causa raíz y remediación

- **Causa raíz:** La vinculación automática de datos (*Data Binding*) sin restricciones permite que atributos internos de un objeto (que no debieran ser modificados desde el lado del cliente) puedan ser sobrescritos al inyectarlos directamente en el payload de la petición HTTP.
- **Remediación recomendada (OWASP):**
  1. **Whitelisting (Listas blancas):** Configurar el framework de backend para aceptar y procesar únicamente las propiedades explícitamente permitidas (por ejemplo, permitir solo `comprador` y descartar cualquier otro campo en la petición).
  2. **DTOs (Data Transfer Objects):** Crear esquemas u objetos estrictos para cada endpoint, definiendo exactamente la estructura y los datos que la API espera recibir.
  3. Ignorar propiedades adicionales a nivel del analizador/parser JSON para evitar inyecciones de atributos inesperados.

## Herramientas usadas

- Navegador Web (Chrome/Firefox)
- **Burp Suite Community Edition**
