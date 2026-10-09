# Reto 37: Inspector Challenge (Local Storage and Cookie)

## 1. Enunciado
"Para superar este reto debes modificar la cookie y el valor almacenado en local storage usando el inspector del navegador para que contengan el hash md5 de `hackertech`."

## 2. Conceptos Técnicos: Cookies vs. Local Storage
- **Cookies:** Son pequeños fragmentos de datos que el navegador almacena a petición del servidor web. Se envían automáticamente al servidor en cada petición HTTP. Son tradicionalmente utilizadas para el manejo de sesiones y seguimiento.
- **Local Storage:** Es parte de la API de *Web Storage* de HTML5. Permite guardar datos clave-valor en el navegador de forma persistente (sin fecha de caducidad). A diferencia de las cookies, los datos en Local Storage **no** se envían al servidor en las peticiones HTTP automáticamente, se usan para lógica del lado del cliente.
- **Hash MD5:** Es un algoritmo de reducción criptográfica. Aunque hoy en día es considerado inseguro para proteger información crítica (por colisiones y fuerza bruta), es muy utilizado en ejercicios CTF introductorios.

## 3. Análisis de la Solución (PoC)

El reto consiste en dos partes: calcular el hash solicitado e inyectarlo manualmente en el navegador para alterar el estado de la aplicación.

### Paso 1: Calcular el hash MD5
Debemos calcular el MD5 de la cadena `hackertech`. Puedes realizarlo con lenguajes como Python, PowerShell o herramientas online. 
El hash MD5 resultante es:
```text
6397550e14d36fc51b5049e28c40876f
```
*(Puedes verificar cómo se calculó revisando el script `solve.ps1` adjunto en este directorio).*

### Paso 2: Modificación en el Inspector (DevTools)
1. Abrir las **Herramientas de Desarrollador** en el navegador (presionando `F12` o `Ctrl+Shift+I`).
2. Dirigirse a la pestaña **Aplicación** (o *Application* / *Almacenamiento* dependiendo del navegador).
3. **Manipular el Local Storage:**
   - En el panel izquierdo, desplegar la sección **Almacenamiento local (Local Storage)** y seleccionar el dominio del reto.
   - Localizar la clave u objeto que valida el reto y cambiar su valor por el hash: `6397550e14d36fc51b5049e28c40876f`.
4. **Manipular las Cookies:**
   - En el mismo panel izquierdo, desplegar la sección **Cookies** y seleccionar el dominio.
   - Editar la cookie objetivo (haciendo doble clic en su valor) y pegar el mismo hash MD5.
5. Hacer clic en "Validar" en la interfaz del reto o recargar la página para que el cliente/servidor evalúen los nuevos valores alterados.

## 4. Modelado de Amenazas y Causa Raíz
Este ejercicio, de carácter introductorio, ilustra una vulnerabilidad clásica: **Client-Side Trust (Confianza en el lado del cliente)**. 
La causa raíz de este fallo (en un contexto real) sucede cuando la lógica de la aplicación, ya sea en JavaScript (frontend) o en el backend, confía ciegamente en que los valores presentes en el almacenamiento del navegador no han sido modificados por el usuario. Al estar bajo el control total del usuario, el atacante puede alterar variables de estado, roles (ej: `admin=true`) o, en este caso, saltarse la validación del reto.

## 5. Remediación y Buenas Prácticas (OWASP)
Para defender y construir aplicaciones robustas en el mundo real, se deben seguir estos lineamientos:

- **Never Trust the Client:** Jamás confíes en datos provenientes del lado del cliente para realizar controles de acceso, validación de permisos lógicos o cálculos críticos financieros. Toda validación vital debe hacerse en el **servidor (Server-Side)**.
- **Uso seguro de Cookies:**
  - Utilizar el atributo `HttpOnly`: Previene que la cookie sea accesible mediante código JavaScript (mitigando ataques XSS).
  - Utilizar el atributo `Secure`: Garantiza que la cookie sólo se transmita a través de conexiones cifradas (HTTPS).
  - Utilizar el atributo `SameSite`: Protege contra ataques de falsificación de solicitudes (CSRF).
- **Protección de Datos Sensibles:** No almacenes datos sensibles (tokens de acceso crudos, contraseñas, PII) en `Local Storage`, ya que son vulnerables si existe un fallo de tipo XSS.
- **Integridad y Firmas Criptográficas:** Si necesitas almacenar el estado de la sesión o datos en el cliente (como en un JSON Web Token - JWT), estos deben estar firmados criptográficamente (Ej: usando un algoritmo como HMAC-SHA256) para que, al ser enviados de vuelta al servidor, este pueda verificar si han sido adulterados.
