# CyLab Hacklab / picoCTF - Cybersecurity Write-ups

Repositorio de documentación, notas y bitácoras de resolución (*write-ups*) para desafíos de ciberseguridad y CTFs de **CyLab Security Academy** (Carnegie Mellon University / picoCTF).

---

## 🗂️ Estructura del Repositorio

El contenido está categorizado por rama de ciberseguridad y clasificado por nivel de dificultad:

```text
Hacklab-CyLab/
├── README.md
├── ROADMAP.md
└── Web-Exploitation/
    ├── Easy/
    │   ├── 01_Inspect_HTML.md
    │   ├── 02_where_are_the_robots.md
    │   ├── 03_dont_use_client_side.md
    │   ├── 04_logon.md
    │   ├── 05_Cookies.md
    │   └── 06_GET_aHEAD.md
    └── Medium/
        └── (en progreso...)
```

---

## 🌐 Web Exploitation

### Nivel: Easy (Completado ✅)

| # | Reto | Concepto Clave / Vulnerabilidad | Herramienta Principal |
|---|---|---|---|
| **01** | [`Inspect HTML`](Web-Exploitation/Easy/01_Inspect_HTML.md) | Fuga de información en comentarios HTML | Inspector DOM (`Ctrl + U` / `F12`) |
| **02** | [`where are the robots`](Web-Exploitation/Easy/02_where_are_the_robots.md) | Reconocimiento de rutas desindexadas | `/robots.txt` |
| **03** | [`dont-use-client-side`](Web-Exploitation/Easy/03_dont_use_client_side.md) | Validación insegura de credenciales en JavaScript | Depuración JS en navegador |
| **04** | [`logon`](Web-Exploitation/Easy/04_logon.md) | Control de acceso roto mediante cookies booleanas | DevTools (Application > Cookies) |
| **05** | [`Cookies`](Web-Exploitation/Easy/05_Cookies.md) | Enumeración de identificadores de sesión / IDOR | Modificación de valores de Cookies |
| **06** | [`GET aHEAD`](Web-Exploitation/Easy/06_GET_aHEAD.md) | Métodos y cabeceras de respuesta HTTP | `curl -I` (Terminal) |

---

### Nivel: Medium (Próximos Retos 🎯)
- SQL Injection (`SQLiLite` / `Irish-Name-Repo 1`)
- Path Traversal / LFI (`Forbidden Paths`)
- Header Spoofing (`picobrowser`)
- JWT & Server-Side Injections

---

*Autor: Lucas Berecoechea*  
*Entorno: Windows / PowerShell / Browser DevTools / curl*
