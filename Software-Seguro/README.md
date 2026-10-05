# 🛡️ Software Seguro - Laboratorios de Ciberseguridad

Repositorio de documentación, notas técnicas, análisis de vulnerabilidades, scripts de explotación y bitácoras (*write-ups*) para la plataforma **Software Seguro** (entrenamiento en ciberseguridad ofensiva y defensiva de Pabex).

---

## 📂 Organización por Categorías

Todos los desafíos están organizados dentro del directorio [`Software-Seguro/`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/) siguiendo la estructura:

```text
Software-Seguro/
├── <categoría>/
│   └── <nombre-del-ejercicio>/ (o archivo writeup-<ejercicio>.md)
```

### Categorías de Desafíos

- **`sqli/`**: Inyecciones SQL (ej. *NSA*, *Home Banking*, *Galería de imágenes*, *Mis viajes*).
- **`idor/`**: Insecure Direct Object References (ej. *Aldeas inseguras*, *Apagar la IA*, *Turnero*).
- **`desbordamiento-de-memoria/`**: Memory Corruption, Stack Overflow & Binary Exploitation (ej. *Manipulando el Stack*, *Rompiendo Autenticación*).
- **`criptoanalisis/`**: Criptografía y Criptoanálisis (ej. *Algoritmo personalizado*, *Mensaje cifrado*, *Recuperación de imagen*, *Chat Seguro*, *RSA Robusto*, *SatSim*).
- **`xss/`**: Cross-Site Scripting reflejado, almacenado y basado en DOM (ej. *Búsqueda de usuarios*, *El blog de Pepe*, *Blog Hacklab*).
- **`broken-access-control/`**: Fallas de control de accesos e impersonación (ej. *Votación*, *Compra de divisas*).
- **`mass-assignment/`**: Asignación masiva de parámetros (ej. *Gran Rifa 2019*, *Presupuesto*, *Préstamo*).
- **`tokens/`**: Vulnerabilidades y manipulación de tokens de sesión / autenticación (ej. *Consulta de multas*).
- **`information-disclosure/`**: Fuga o exposición de datos confidenciales (ej. *Asistencia*).
- **`reversing/`**: Ingeniería inversa en aplicaciones de escritorio y ejecutables APK (ej. *Calculadora*, *Libros Gratis*, *Tetris*, *Secure Chat*, *Soporte Confidencial*).
- **`condiciones-de-carrera/`**: Race conditions y concurrencia (ej. *El analista*).
- **`auth/`**: Mecanismos de autenticación inseguros (ej. *ECommerce*, *Snow Storm*).
- **`ssrf/`**: Server-Side Request Forgery (ej. *Cotizaciones Dólar*).
- **`fuerza-bruta/`**: Ataques de fuerza bruta y diccionario (ej. *El mejor secreto*).
- **`csrf/`**: Cross-Site Request Forgery (ej. *Imagen importante*).
- **`webrtc/`**: Protocolos e implementaciones WebRTC (ej. *Direct chat*).
- **`logica-de-negocio/`**: Fallas en la lógica de negocio (ej. *Venta de autos*).
- **`sanitizacion/`**: Bypass y corrección de filtros de entrada (ej. *Fix Urgente*).
- **`introduccion/`**: Conceptos introductorios e inspección (ej. *Uso del inspector*, *Local Storage and Cookie*).

---

## 📋 Catálogo Completo de Desafíos (Software Seguro)

| # | Desafío | Categoría | Evento / Edición | Estado | Writeup / Ruta |
|---|---|---|---|:---:|---|
| 1 | Uso del inspector | Introducción | - | ✅ Resuelto | `introduccion/uso-del-inspector/` |
| 2 | NSA | SQLi | - | ✅ Resuelto | [`sqli/nsa/writeup.md`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/sqli/nsa/writeup.md) |
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
| 20 | Galería de imágenes | SQLi | HackLab 2023 | ⏳ Pendiente | `sqli/galeria-de-imagenes/` |
| 21 | Logs | SQLi | HackLab 2023 | ⏳ Pendiente | `sqli/logs/` |
| 22 | Turnero | IDOR | HackLab 2024 | ⏳ Pendiente | `idor/turnero/` |
| 23 | Calculadora | IDOR - Reversing Desktop Apps | HackLab 2024 | ⏳ Pendiente | `reversing/calculadora/` |
| 24 | Préstamo | Mass Assignment | HackLab 2024 | ⏳ Pendiente | `mass-assignment/prestamo/` |
| 25 | Chat Seguro | Criptoanálisis | HackLab 2024 | ⏳ Pendiente | `criptoanalisis/chat-seguro/` |
| 26 | Asistencia | Information Disclosure | HackLab 2024 | ⏳ Pendiente | `information-disclosure/asistencia/` |
| 27 | Mis viajes | SQLi | HackLab 2024 | ⏳ Pendiente | `sqli/mis-viajes/` |
| 29 | Blog Hacklab | XSS | HackLab 2024 | ⏳ Pendiente | `xss/blog-hacklab/` |
| 30 | RSA Robusto | Criptoanálisis | HackLab 2024 | ⏳ Pendiente | `criptoanalisis/rsa-robusto/` |
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
| 48 | Rompiendo Autenticación | Desbordamiento de memoria | - | ✅ Resuelto | [`desbordamiento-de-memoria/rompiendo-autenticacion/writeup.md`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/desbordamiento-de-memoria/rompiendo-autenticacion/writeup.md) |
| 49 | Fix Urgente | Sanitización | - | ⏳ Pendiente | `sanitizacion/fix-urgente/` |
| 50 | SatSim | Criptoanálisis | - | ⏳ Pendiente | `criptoanalisis/satsim/` |
| 51 | Imagen perdida | Criptoanálisis | - | ⏳ Pendiente | `criptoanalisis/imagen-perdida/` |
| 52 | Soporte Confidencial | IDOR - Reversing Apk | HackingDay 2026 | ⏳ Pendiente | `reversing/soporte-confidencial/` |

---

*Plataforma:* [SoftwareSeguro](https://softwareseguro.com.ar/)  
*Colaboradores / Autores:* `adonaissh`, `LucBere`
