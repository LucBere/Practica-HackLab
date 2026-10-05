# 🛡️ Software Seguro - Laboratorios de Ciberseguridad

Repositorio de documentación, notas técnicas, análisis de vulnerabilidades, scripts de explotación y bitácoras (*write-ups*) para la plataforma **Software Seguro** (entrenamiento en ciberseguridad ofensiva y defensiva de Pabex).

> 🛠️ Para configurar el entorno con WSL2, GDB, Pwntools, Exiftool y Burp Suite, consulta la [Guía de Setup del Entorno](../SETUP_ENVIRONMENT.md).

---

## 📂 Organización por Categorías

Todos los desafíos están organizados dentro del directorio [`Software-Seguro/`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/) siguiendo la estructura:

```text
Software-Seguro/
├── <categoría>/
│   └── <nombre-del-ejercicio>/ (o archivo writeup-<ejercicio>.md)
```

### Guía y Conceptos por Categoría

A continuación se detalla qué significa cada categoría de vulnerabilidad y qué conocimientos y herramientas se requieren para resolverla:

#### 1. SQLi (SQL Injection)
Inyectar código SQL en campos de entrada para manipular consultas a la base de datos (leer datos no autorizados, bypassear logins, volcar tablas, etc.).  
- **Necesitás:** Sintaxis SQL, operadores como `OR 1=1`, `UNION SELECT`, comentarios (`--`, `#`).  
- **Herramientas:** Burp Suite para interceptar requests, a veces `sqlmap`.

#### 2. IDOR (Insecure Direct Object Reference)
La app te deja acceder a recursos de otros usuarios solo cambiando un ID en la URL o request (ej: `/usuario/123` → cambiás a `/usuario/124` y ves datos ajenos sin autorización).  
- **Necesitás:** Ojo atento a identificadores secuenciales/predecibles en parámetros GET o body JSON.  
- **Herramientas:** Burp Suite o las devtools del navegador (`F12`) para interceptar y modificar requests.

#### 3. XSS (Cross-Site Scripting)
Inyectar JavaScript malicioso que se ejecuta en el navegador de otro usuario (vía campos de texto, comentarios, parámetros URL que no sanitizan bien).  
- **Necesitás:** Conocimientos de HTML/JS, payloads tipo `<script>alert(1)</script>`, entender el contexto de inyección (dentro de atributo, dentro de script, DOM).  
- **Herramientas:** Browser DevTools, Burp Suite.

#### 4. Criptoanálisis
Romper o explotar debilidades en algoritmos de cifrado mal implementados (claves débiles, algoritmos caseros, reutilización de IV, etc.).  
- **Necesitás:** Conocimientos básicos de criptografía (XOR, RSA, cifrados de sustitución), scripts en Python.  
- **Herramientas:** Python (`pycryptodome`, `hashlib`), CyberChef.

#### 5. Mass Assignment
La app permite modificar campos que no deberías poder tocar (ej: mandás `"isAdmin": true` en un JSON de registro y la API lo acepta sin validar).  
- **Necesitás:** Identificar modelos y atributos en backend, probar agregar propiedades adicionales al payload.  
- **Herramientas:** Burp Suite para interceptar y agregar/modificar campos en el body (normalmente JSON).

#### 6. Broken Access Control
Categoría amplia de fallas de autorización donde se puede hacer algo que no debería estar permitido para tu rol/usuario (puede solaparse con IDOR o escalamiento vertical).  
- **Necesitás:** Entender roles y permisos de la aplicación, probar acciones restringidas directamente vía requests.  
- **Herramientas:** Burp Suite, repetición de peticiones con diferentes tokens de usuario.

#### 7. Desbordamiento de memoria (Buffer Overflow)
Explotar falta de validación de límites en buffers de memoria (`strcpy`, arrays fijos) para corromper variables adyacentes, registros o el flujo de ejecución.  
- **Necesitás:** Conocimientos de C y assembly x86/x64, estructura del stack y punteros de retorno.  
- **Herramientas:** `gdb`, `checksec`, Python para armar payloads binarios / exploits.

#### 8. Tokens
Explotar debilidades en tokens de sesión o autenticación: tokens predecibles, mal firmados, JWT sin verificar firma (`alg: none`), etc.  
- **Necesitás:** Entender estructura de tokens y JWT.  
- **Herramientas:** [jwt.io](https://jwt.io/), Burp Suite, scripts de fuerza bruta sobre secretos cortos.

#### 9. Information Disclosure
La app expone información sensible que no debería (en respuestas de API, comentarios HTML, mensajes de error verbosos, metadatos de archivos).  
- **Necesitás:** Inspección rigurosa de respuestas HTTP, código fuente, headers y códigos de estado.  
- **Herramientas:** Browser DevTools (`Ctrl + U` / `F12`), `curl`, Burp Suite.

#### 10. SSRF (Server-Side Request Forgery)
Lograr que el servidor realice peticiones HTTP hacia destinos internos arbitrarios (ej. `localhost` o la red interna) abusando de funcionalidades que consumen URLs externas.  
- **Necesitás:** Entender redes internas, esquemas de URL (`http`, `file`, `gopher`), bypass de filtros (`127.0.0.1`, `0177.0.0.1`, DNS rebinding).  
- **Herramientas:** Burp Collaborator / Webhook.site, Burp Suite.

#### 11. Fuerza bruta
Probar combinaciones masivas (passwords, tokens, PINs) hasta encontrar la correcta, usualmente ante ausencia de rate limiting o bloqueos.  
- **Necesitás:** Diccionarios de palabras (`rockyou.txt`, numéricos), optimización de concurrencia.  
- **Herramientas:** Burp Intruder / Turbo Intruder, scripts personalizados en Python (`requests`, `threading`).

#### 12. CSRF (Cross-Site Request Forgery)
Forzar a que un usuario autenticado ejecute una acción sin consentimiento (vía un link o formulario malicioso) porque la app no valida tokens anti-CSRF ni orígenes.  
- **Necesitás:** Entender cookies de sesión, atributo `SameSite`, creación de formularios HTML auto-enviados (`PoC CSRF`).  
- **Herramientas:** Burp Suite (CSRF PoC generator), servidor local para hospedar el payload.

#### 13. WebRTC
Explotar la tecnología de comunicación en tiempo real del navegador (fuga de IPs locales/públicas reales detrás de proxys/VPNs, streams no autorizados).  
- **Necesitás:** Funcionamiento de WebRTC, STUN/TURN, SDP (Session Description Protocol).  
- **Herramientas:** DevTools del navegador, scripts JS de inspección WebRTC.

#### 14. Reversing Desktop Apps / Reversing APK
Analizar un binario (.exe) o paquete Android (.apk) sin código fuente para entender su flujo interno, extraer secretos o parchar validaciones.  
- **Necesitás:** Lectura de pseudocódigo y desensamblado, lógica de programación.  
- **Herramientas:** Ghidra / IDA Pro / x64dbg (Desktop), `jadx-gui` / `apktool` (Android APK).

#### 15. Condiciones de carrera (Race Conditions)
Aprovechar operaciones concurrentes simultáneas que rompen la lógica esperada antes de que el estado se bloquee (ej: doble gasto de saldo, canje múltiple de cupones).  
- **Necesitás:** Identificar ventanas de tiempo críticas entre chequeo y uso (TOCTOU).  
- **Herramientas:** Burp Turbo Intruder (con request pipelining / single-packet attack), Python con `asyncio` o `threading`.

#### 16. Auth (Autenticación)
Fallas en el diseño o implementación del proceso de inicio de sesión / verificación de identidad (bypasses lógicos, comparaciones débiles, timing attacks, etc.).  
- **Necesitás:** Análisis de flujos de login, recuperación de claves, validaciones booleanas.  
- **Herramientas:** Burp Suite, análisis de código / binarios.

#### 17. Lógica de negocio
Explotar vacíos en las reglas funcionales del negocio (comprar a precio negativo, alterar cantidades de productos, saltarse pasos secuenciales de pago).  
- **Necesitás:** Pensamiento lateral para desafiar las asunciones del desarrollador sobre el flujo del usuario.  
- **Herramientas:** Burp Suite Repeater / Proxy.

#### 18. Sanitización
Fallas donde la aplicación no limpia o valida correctamente los inputs provistos por el usuario, siendo la causa raíz de inyecciones (XSS, SQLi, Path Traversal).  
- **Necesitás:** Entender qué caracteres especiales procesa el contexto de destino y cómo bypassear filtros débiles (doble encoding, casos mixtos, null bytes).  
- **Herramientas:** Burp Suite, codificadores (`CyberChef`).

#### 19. Introducción
Desafíos orientados al aprendizaje de la plataforma y el uso de herramientas base de inspección web (inspección de elementos, lectura de `LocalStorage`, `Cookies`, consola JavaScript).  
- **Necesitás:** Manejo elemental del navegador.  
- **Herramientas:** DevTools (`F12`), pestañas Elements, Console, Application/Storage.

> [!TIP]
> **Herramienta transversal más importante:** **Burp Suite** (la versión Community gratuita es suficiente para la gran mayoría de retos web) — permite interceptar, modificar, automatizar y repetir requests HTTP/HTTPS con facilidad.

---

## 📋 Catálogo Completo de Desafíos (Software Seguro)

| # | Desafío | Categoría | Evento / Edición | Estado | Writeup / Ruta |
|---|---|---|---|:---:|---|
| 1 | Uso del inspector | Introducción | - | ✅ Resuelto | `introduccion/uso-del-inspector/` |
| 2 | NSA | SQLi | - | ✅ Resuelto | [`sqli/writeup_NSA.md`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/sqli/writeup_NSA.md) |
| 3 | Home Banking | SQLi | - | ✅ Resuelto | `sqli/home-banking/` |
| 4 | Aldeas inseguras | IDOR | - | ✅ Resuelto | [`idor/aldeas-inseguras.md`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/idor/aldeas-inseguras.md) |
| 5 | Apagar la IA | IDOR | HackLab 2023 | ✅ Resuelto | [`idor/apagar-la-ia.md`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/idor/apagar-la-ia.md) |
| 6 | Búsqueda de usuarios | XSS | - | ✅ Resuelto (LucBere) | [`xss/writeup_Busqueda-de-usuarios.md`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/xss/writeup_Busqueda-de-usuarios.md) |
| 7 | El blog de Pepe | XSS | HackLab 2023 | ⏳ Pendiente | `xss/el-blog-de-pepe/` |
| 8 | El blog de Pepe segurizado | XSS | - | ⏳ Pendiente | `xss/el-blog-de-pepe-segurizado/` |
| 9 | Algoritmo personalizado | Criptoanálisis | HackLab 2023 | ✅ Resuelto | [`criptoanalisis/writeup_Algoritmo-personalizado.md`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/criptoanalisis/writeup_Algoritmo-personalizado.md) |
| 10 | Mensaje cifrado | Criptoanálisis | - | ✅ Resuelto | [`criptoanalisis/writeup-Mensaje_Cifrado.md`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/criptoanalisis/writeup-Mensaje_Cifrado.md) |
| 11 | Gran Rifa 2019 | Mass Assignment | - | ⏳ Pendiente | `mass-assignment/gran-rifa-2019/` |
| 12 | Votación | Broken Access Control | - | ⏳ Pendiente | `broken-access-control/votacion/` |
| 13 | Recuperación de imagen | Criptoanálisis | HackLab 2023 | ✅ Resuelto | [`criptoanalisis/writeup_Recuperación-de-imagen.md`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/criptoanalisis/writeup_Recuperación-de-imagen.md) |
| 14 | Manipulando el Stack | Desbordamiento de memoria | - | ✅ Resuelto | `desbordamiento-de-memoria/manipulando-el-stack/` |
| 15 | Consulta de multas | Tokens | - | ⏳ Pendiente | `tokens/consulta-de-multas/` |
| 16 | Ventas | Information Disclosure - IDOR | HackLab 2023 | ⏳ Pendiente | `idor/ventas/` |
| 17 | Compra de divisas | Broken Access Control | HackLab 2023 | ⏳ Pendiente | `broken-access-control/compra-de-divisas/` |
| 18 | Votación nueva versión | Broken Access Control | HackLab 2023 | ⏳ Pendiente | `broken-access-control/votacion-nueva-version/` |
| 19 | Presupuesto | Mass Assignment | HackLab 2023 | ⏳ Pendiente | `mass-assignment/presupuesto/` |
| 20 | Galería de imágenes | SQLi | HackLab 2023 | ✅ Resuelto | [`sqli/writeup_Galeria-de-imagenes.md`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/sqli/writeup_Galeria-de-imagenes.md) |
| 21 | Logs | SQLi | HackLab 2023 | ✅ Resuelto | [`sqli/writeup_Logs.md`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/sqli/writeup_Logs.md) |
| 22 | Turnero | IDOR | HackLab 2024 | ⏳ Pendiente | `idor/turnero/` |
| 23 | Calculadora | IDOR - Reversing Desktop Apps | HackLab 2024 | ⏳ Pendiente | `reversing/calculadora/` |
| 24 | Préstamo | Mass Assignment | HackLab 2024 | ⏳ Pendiente | `mass-assignment/prestamo/` |
| 25 | Chat Seguro | Criptoanálisis | HackLab 2024 | ⏳ Pendiente | `criptoanalisis/chat-seguro/` |
| 26 | Asistencia | Information Disclosure | HackLab 2024 | ⏳ Pendiente | `information-disclosure/asistencia/` |
| 27 | Mis viajes | SQLi | HackLab 2024 | ✅ Resuelto | [`sqli/writeup_Mis-Viajes.md`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/sqli/writeup_Mis-Viajes.md) |
| 29 | Blog Hacklab | XSS | HackLab 2024 | ⏳ Pendiente | `xss/blog-hacklab/` |
| 30 | RSA Robusto | Criptoanálisis | HackLab 2024 | ✅ Resuelto | [`criptoanalisis/writeup_RSA-Robusto.md`](criptoanalisis/writeup_RSA-Robusto.md) |
| 31 | Libros Gratis | Reversing Apk - Broken Access Control | HackLab 2024 | ⏳ Pendiente | `reversing/libros-gratis/` |
| 32 | El analista | Condiciones de carrera | HackLab 2024 | ⏳ Pendiente | `condiciones-de-carrera/el-analista/` |
| 33 | ECommerce | Auth | HackLab 2024 | ⏳ Pendiente | `auth/ecommerce/` |
| 34 | Snow Storm | Auth | HackLab 2024 | ⏳ Pendiente | `auth/snow-storm/` |
| 35 | Aldeas Inseguras V2 | IDOR | - | ⏳ Pendiente | `idor/aldeas-inseguras-v2/` |
| 36 | Notas Universitarias | Tokens - IDOR | - | ⏳ Pendiente | `tokens/notas-universitarias/` |
| 37 | Local Storage and Cookie | Introducción | - | ⏳ Pendiente | `introduccion/local-storage-and-cookie/` |
| 38 | Cotizaciones Dólar | SSRF | - | ⏳ Pendiente | `ssrf/cotizaciones-dolar/` |
| 39 | El mejor secreto | Fuerza bruta | HackLab 2025 | ✅ Resuelto | [`fuerza-bruta/writeup-El_Mejor_Secreto.md`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/fuerza-bruta/writeup-El_Mejor_Secreto.md) |
| 40 | Imagen importante | CSRF | HackLab 2025 | ⏳ Pendiente | `csrf/imagen-importante/` |
| 41 | Reservas de hotel | IDOR | HackLab 2025 | ⏳ Pendiente | `idor/reservas-de-hotel/` |
| 42 | Direct chat | WebRTC | HackLab 2025 | ⏳ Pendiente | `webrtc/direct-chat/` |
| 43 | Blog Hacklab v2 | XSS | HackLab 2025 | ⏳ Pendiente | `xss/blog-hacklab-v2/` |
| 44 | Mis viajes v2 | SQLi | HackLab 2025 | ⏳ Pendiente | `sqli/mis-viajes-v2/` |
| 45 | Tetris | Reversing Desktop Apps - Lógica de negocio | HackLab 2025 | ⏳ Pendiente | `reversing/tetris/` |
| 46 | Secure Chat | Reversing Apk - Fuerza bruta | HackLab 2025 | ⏳ Pendiente | `reversing/secure-chat/` |
| 47 | Venta de autos | Lógica de negocio | HackLab 2025 | ⏳ Pendiente | `logica-de-negocio/venta-de-autos/` |
| 48 | Rompiendo Autenticación | Desbordamiento de memoria | - | ✅ Resuelto | [`desbordamiento-de-memoria/writeup_Rompiendo-Autenticacion.md`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/desbordamiento-de-memoria/writeup_Rompiendo-Autenticacion.md) |
| 49 | Fix Urgente | Sanitización | - | ⏳ Pendiente | `sanitizacion/fix-urgente/` |
| 50 | SatSim | Criptoanálisis | - | ⏳ Pendiente | `criptoanalisis/satsim/` |
| 51 | Imagen perdida | Criptoanálisis | - | ⏳ Pendiente | `criptoanalisis/imagen-perdida/` |
| 52 | Soporte Confidencial | IDOR - Reversing Apk | HackingDay 2026 | ⏳ Pendiente | `reversing/soporte-confidencial/` |

---

*Plataforma:* [SoftwareSeguro](https://softwareseguro.com.ar/)  
*Colaboradores / Autores:* `adonaissh`, `LucBere`
