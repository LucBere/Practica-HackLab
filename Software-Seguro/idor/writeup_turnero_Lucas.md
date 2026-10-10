# Turnero — Writeup

## Descripción del desafío

**Plataforma:** Software Seguro (HackLab 2024)  
**Categoría:** IDOR (Insecure Direct Object Reference)  
**Objetivo:** El usuario `xdalvik` ha reservado demasiados turnos. Debemos eliminar exclusivamente sus turnos médicos sin afectar los nuestros (`luis`) ni los del resto de los usuarios.

## Reconocimiento

1. Nos autenticamos en la aplicación con las credenciales `luis` / `Luis.4321`.
2. Observamos una tabla "Mis Turnos" que lista 5 turnos médicos correspondientes a nuestro usuario, junto con botones o enlaces para interactuar (posiblemente para cancelar/eliminar).
3. Al ser un reto de IDOR, sospechamos que las acciones sobre los turnos se manejan mediante un identificador numérico directo (ej. `id_turno=10`) que viaja en la petición HTTP. El servidor probablemente no valida si el usuario logueado es el verdadero dueño del turno antes de procesar la acción.

## Vulnerabilidad

**Insecure Direct Object Reference (IDOR):** Ocurre cuando la aplicación expone una referencia directa a un objeto interno de la base de datos (como el ID de un turno) y no realiza verificaciones de control de acceso en el backend para confirmar que el usuario que realiza la petición tiene permisos sobre ese objeto en particular.

Adicionalmente, para poder apuntar solo a los turnos de `xdalvik` sin borrar los demás, debe existir una filtración de información (Information Disclosure) que nos permita mapear qué ID de turno le pertenece a qué usuario.

## Explotación

### 1. Intercepción y Análisis
Analizando el tráfico HTTP en Burp Suite al momento de iniciar sesión, descubrimos que la página web realiza una petición `GET` para cargar nuestra lista de turnos:
`GET /api/1/appointments/`

El número `1` en la ruta de la URL claramente representa nuestro identificador de usuario (`luis`). Si la aplicación no verifica correctamente la autorización, podríamos cambiar este número para consultar los turnos de otros usuarios.

### 2. Enumeración y Borrado (Ataque IDOR)
Mediante fuerza bruta de lectura (usando Intruder o un script iterativo en la consola del navegador `fetch('/api/'+i+'/appointments/')`), descubrimos que el usuario `xdalvik` es el **ID 101**. 
Al consultar sus turnos, la filtración de datos (Information Disclosure) nos revela que posee 4 turnos cuyos IDs son: `10, 11, 12, 13`.

Teniendo los identificadores exactos, procedemos a enviar peticiones `DELETE` directamente hacia esos recursos:
- `DELETE /api/appointments/10`
- `DELETE /api/appointments/11`
- `DELETE /api/appointments/12`
- `DELETE /api/appointments/13`

Al hacerlo, la aplicación borra los turnos de `xdalvik` sin verificar si pertenecían a nuestro usuario, resolviendo el objetivo.

## Resultado / Flag
**Flag:** `d27fa3f8fc14ea101603d09436e28bf6`

## Causa raíz y remediación

- **Causa raíz:** La vulnerabilidad es un clásico **IDOR (Insecure Direct Object Reference)** combinado con **Information Disclosure**. La API asume que cualquier petición de borrado hacia `/api/appointments/<id>` es legítima sin verificar si el turno le pertenece al usuario que realiza la petición. A su vez, el endpoint `/api/<user_id>/appointments/` permite la enumeración de turnos de terceros debido a la falta de controles de acceso.
- **Remediación recomendada (OWASP):**
  1. **Control de Acceso a Nivel de Objeto (BOLA):** Antes de eliminar un registro en la base de datos, el backend debe verificar que el `user_id` asociado a la sesión actual coincida con el `owner_id` del turno a borrar (`DELETE FROM appointments WHERE id = ? AND owner_id = ?`).
  2. **Control en la consulta de datos:** El endpoint que devuelve los turnos (`GET /api/1/appointments/`) no debería depender de un parámetro en la URL controlado por el usuario. Debería ignorar el número en la URL y extraer el identificador directamente desde el token de sesión o cookie JWT del servidor (`GET /api/me/appointments`).
  3. **Usar identificadores indirectos:** Reemplazar los IDs numéricos secuenciales por UUIDs (Identificadores Únicos Universales) o identificadores indirectos aleatorios para dificultar la enumeración masiva, aunque la solución principal siempre debe ser el control de acceso en el backend.
