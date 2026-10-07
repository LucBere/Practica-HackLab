# 🔐 Laboratorios de Ciberseguridad & CTF Write-ups

Repositorio centralizado de documentación, análisis de vulnerabilidades, scripts de explotación y bitácoras (*write-ups*) divididos por plataforma y laboratorio de entrenamiento.

> 🛠️ **¿Nuevo en el entorno de trabajo?** Consulta la guía completa de instalación y configuración de herramientas en [`SETUP_ENVIRONMENT.md`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/SETUP_ENVIRONMENT.md) (WSL2, Ubuntu, GDB, Pwntools, Exiftool, Burp Suite, etc.).

---

## 🗂️ Estructura General del Repositorio

El proyecto se divide en dos laboratorios independientes:

```text
Practica-HackLab/
├── SETUP_ENVIRONMENT.md  # Guía de instalación del entorno Linux/WSL2 y herramientas
├── Software-Seguro/       # Retos y desafíos de la plataforma SoftwareSeguro (Pabex)
│   ├── README.md          # Catálogo completo de retos (51 desafíos) y guía por categorías
│   ├── sqli/              # SQL Injection (ej. NSA, Home Banking, etc.)
│   ├── idor/              # Insecure Direct Object References (ej. Aldeas Inseguras, etc.)
│   ├── desbordamiento-de-memoria/ # Memory corruption & Buffer Overflow (ej. Rompiendo Autenticación)
│   ├── criptoanalisis/    # Criptografía (ej. Algoritmo personalizado, Mensaje cifrado)
│   ├── xss/               # Cross-Site Scripting (ej. Búsqueda de usuarios, Blog de Pepe)
│   └── ...                # Demás categorías (reversing, auth, ssrf, tokens, etc.)
│
└── Cylab/                 # Retos de CyLab Security Academy / picoCTF
    ├── ROADMAP.md         # Hoja de ruta y conceptos clave de aprendizaje
    └── Web-Exploitation/  # Desafíos clasificados por nivel
        ├── Easy/          # Retos nivel fácil resueltos (01 al 06)
        └── Medium/        # Retos en progreso
```

---

## 🌐 1. Software Seguro

Plataforma de entrenamiento en ciberseguridad ofensiva y defensiva ([SoftwareSeguro](https://softwareseguro.com.ar/)).  
Contiene retos organizados por tipo de vulnerabilidad:

- **SQLi**: [`Software-Seguro/sqli/`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/sqli/) (incluye `writeup_NSA.md`, `writeup_Galeria-de-imagenes.md`, `writeup_Logs.md`, `writeup_Mis-Viajes.md`, `writeup_Mis-Viajes-V2.md`).
- **IDOR**: [`Software-Seguro/idor/`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/idor/) (incluye retos `aldeas-inseguras.md`, `apagar-la-ia.md`).
- **Desbordamiento de memoria**: [`Software-Seguro/desbordamiento-de-memoria/`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/desbordamiento-de-memoria/) (incluye `writeup_Rompiendo-Autenticacion.md` y exploit).
- **Criptoanálisis**: [`Software-Seguro/criptoanalisis/`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/criptoanalisis/) (incluye `writeup_Algoritmo-personalizado.md`, `writeup-Mensaje_Cifrado.md`, `writeup_Recuperación-de-imagen.md`).
- **XSS**: [`Software-Seguro/xss/`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/xss/) (incluye `writeup_Busqueda-de-usuarios.md`).
- **Fuerza bruta**: [`Software-Seguro/fuerza-bruta/`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/fuerza-bruta/) (incluye `writeup-El_Mejor_Secreto.md`).
- **Reversing / Desktop Apps**: [`Software-Seguro/reversing/`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/reversing/) (incluye `writeup_Calculadora.md`).
- **Broken Access Control**: [`Software-Seguro/broken-access-control/`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/broken-access-control/) (incluye `writeup_Votacion-nueva-version.md`).
- **Reversing APK**: [`Software-Seguro/reversing-apk/`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/reversing-apk/) (incluye `writeup_Libros-Gratis.md`, `writeup_Soporte-confidencial.md`).

👉 *Para ver la tabla completa con los 51 desafíos, el estado de resolución y el índice temático, consulta el [`README de Software Seguro`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/README.md).*

---

## 🔬 2. CyLab Security Academy / picoCTF

Laboratorio enfocado en conceptos de explotación web de **CyLab** / **picoCTF**.  
Consulta el [ROADMAP de CyLab](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Cylab/ROADMAP.md) para más detalles.

| # | Reto | Concepto Clave / Vulnerabilidad | Herramienta Principal |
|---|---|---|---|
| **01** | [`Inspect HTML`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Cylab/Web-Exploitation/Easy/01_Inspect_HTML.md) | Fuga de información en comentarios HTML | Inspector DOM (`Ctrl + U` / `F12`) |
| **02** | [`where are the robots`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Cylab/Web-Exploitation/Easy/02_where_are_the_robots.md) | Reconocimiento de rutas desindexadas | `/robots.txt` |
| **03** | [`dont-use-client-side`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Cylab/Web-Exploitation/Easy/03_dont_use_client_side.md) | Validación insegura en JavaScript del cliente | Depuración JS en navegador |
| **04** | [`logon`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Cylab/Web-Exploitation/Easy/04_logon.md) | Control de acceso roto mediante cookies | DevTools (Application > Cookies) |
| **05** | [`Cookies`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Cylab/Web-Exploitation/Easy/05_Cookies.md) | Enumeración de identificadores de sesión / IDOR | Modificación de valores de Cookies |
| **06** | [`GET aHEAD`](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Cylab/Web-Exploitation/Easy/06_GET_aHEAD.md) | Métodos y cabeceras de respuesta HTTP | `curl -I` (Terminal) |

---

*Colaboradores:* `adonaissh`, `LucBere`  
*Entorno:* Windows / PowerShell / Python / Burp Suite / Browser DevTools
