# Hacklab - CyLab / picoCTF Web Exploitation Roadmap

Carpeta de trabajo y notas para los ejercicios de **Web Exploitation** de CyLab Security Academy.

---

## Ruta de Aprendizaje Recomendada (De Cero a Pro)

### Fase 1: Inspección Web y Reconocimiento (Primeros Pasos)
1. **Inspect HTML** (o Insp3ct0r) - [EL MAS RECOMENDADO PARA EMPEZAR]
   - Concepto: Codigo fuente, etiquetas HTML, comentarios ocultos (<!-- -->), CSS y JS.
   - Atajo: F12 o Ctrl + U en el navegador.

2. **where are the robots**
   - Concepto: Archivo robots.txt, rutas desindexadas u ocultas.

3. **Unminify / Bookmarklet**
   - Concepto: Codigo JS comprimido/minificado, formateador de codigo de DevTools.

### Fase 2: Logica del Cliente vs Servidor (Client-Side)
4. **dont-use-client-side**
   - Concepto: Validaciones inseguras hechas con JavaScript en el navegador.

5. **Local Authority**
   - Concepto: Scripts JS externos y credenciales expuestas en frontend.

### Fase 3: Cookies, Sesiones y Cabeceras HTTP
6. **Cookies & Cookie Monster Secret Recipe**
   - Concepto: Modificacion de cookies en DevTools (pestaña Application/Storage).

7. **logon**
   - Concepto: Modificacion de valores booleanos de sesion en cookies.

8. **GET aHEAD**
   - Concepto: Verbos HTTP (GET, POST, HEAD).

### Fase 4: Codificacion y Herramientas
9. **WebDecode** (Base64, Hexadecimal, CyberChef).
10. **IntroToBurp** (Proxy interceptor Burp Suite).
11. **SSTI1** (Server-Side Template Injection).

---
Formato de Bandera: Generalmente picoCTF{...} o cylab{...}
