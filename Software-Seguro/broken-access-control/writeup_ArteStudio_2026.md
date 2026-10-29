# Desafío - ArteStudio (HackLab)

**Plataforma:** HackLab (SoftwareSeguro)  
**Edición:** HackLab 2026  
**Categoría:** Broken Access Control / Information Disclosure / 2FA Bypass  
**Autor:** adonaissh  

---

## 📌 Enunciado

> **ArteStudio** es un portal y comunidad para que artistas compartan sus creaciones (Imágenes, Sonidos, Música, Videos, Representación, Poemas).
>
> Sin embargo, ciertas secciones exclusivas como **Música** cuentan con carga restringida únicamente para usuarios privilegiados/artistas verificados (las cuentas normales no tienen habilitado el formulario de subida).
>
> **Objetivo:** Conseguir acceso a una cuenta con permisos privilegiados y lograr publicar la canción indicada en el enunciado (`cancion.mp3`) en la sección de Música para obtener la flag.

---

## 🔍 Análisis Inicial y Reconocimiento

Al registrar una cuenta normal (`adonaiper@adonai22` / `adonaip2710@ca.frre.utn.edu.ar`) y confirmar el enlace por correo electrónico:
- La plataforma permite navegar por las diferentes disciplinas artísticas.
- En la sección **Poemas**, destaca una obra titulada *"Clave privada"* publicada por el usuario **`mister`** (`@mister`). Esto señala a `mister` como un creador verificado/privilegiado en la plataforma.
- Al acceder a la sección `/c/musica`, el portal informa que la subida de obras está restringida y no muestra el formulario de carga para usuarios estándar.

---

## 🔬 Identificación de Vulnerabilidades

### 1. Information Disclosure en Recuperación de Contraseña (`/password/inicio`)
Al analizar el flujo de recuperación de clave en el endpoint `/password/inicio`:
- Al ingresar un correo electrónico, la respuesta de la API filtraba directamente el hash **SHA-256** de la contraseña almacenada para esa cuenta, sin requerir token ni validación de titularidad previa.
- Probando con la dirección corporativa de la cuenta objetivo identificada en los poemas:
  ```text
  Email: mister@artestudio.com.ar
  ```
- La API devolvió el hash SHA-256 de su contraseña. Al pasarlo por fuerza bruta offline contra el diccionario `rockyou.txt`, se obtuvo la contraseña en texto plano en cuestión de segundos:
  ```text
  Contraseña: ronald
  ```

### 2. Bypass de 2FA / Secreto TOTP Compartido (Hardcoded Shared Secret)
Al intentar iniciar sesión en `/login` con `mister@artestudio.com.ar` y la contraseña `ronald`:
- El sistema solicitó un segundo factor de autenticación: *"Ingresá el código de 6 dígitos de tu app de autenticación para entrar como mister"*.
- Para entender cómo se generaba el 2FA, se inspeccionó la configuración de dos pasos en la cuenta propia (`/configuracion` de `adonaiper`), donde se ofrecía activar el autenticador mediante un código QR (`data:image/png;base64,...`).
- Al decodificar el código QR para extraer la URI `otpauth://`:
  ```text
  otpauth://totp/ArteStudio:adonaiper?secret=ARTESTUDIOSHAREDSECRET234567ABCD&issuer=ArteStudio
  ```
- **Falla Crítica de Diseño:** El secreto TOTP no se generaba de manera criptográfica por usuario, sino que era una constante estática compartida por toda la aplicación:
  $$\text{Shared Secret} = \text{ARTESTUDIOSHAREDSECRET234567ABCD}$$

---

## 🚀 Explotación

### 1. Generación de Códigos TOTP Válidos

Conociendo el secreto compartido en Base32 (`ARTESTUDIOSHAREDSECRET234567ABCD`), se programó la generación del código TOTP de 6 dígitos para la ventana de tiempo actual (epoch de 30 segundos) utilizando Python (`pyotp` / `oath`):

```python
import pyotp

secret = "ARTESTUDIOSHAREDSECRET234567ABCD"
totp = pyotp.TOTP(secret)
print("Código 2FA actual:", totp.now())
```

### 2. Autenticación como `mister`

1. Se inició sesión con:
   - **Usuario/Email:** `mister@artestudio.com.ar`
   - **Contraseña:** `ronald`
2. En la pantalla de verificación en dos pasos, se ingresó el token generado en tiempo real (`575024`).
3. El servidor validó el código satisfactoriamente:
   > *"¡Verificación en dos pasos correcta! Hola, Mister (@mister · mister@artestudio.com.ar)"*

### 3. Carga de la Obra en Música y Flag

Con la sesión activa de la cuenta privilegiada:
1. Se navegó a la sección restringida `/c/musica`.
2. El formulario `+ Cargar una obra` apareció habilitado.
3. Se completó el formulario y se subió el archivo `cancion.mp3`.
4. El sistema aceptó la publicación y mostró el cartel de resolución:

```text
==================================================
                 🏆 ¡LO LOGRASTE!
       Publicaste la canción del enunciado.
==================================================

Flag: e4ce96139449eb34a9cd02531b023ac9
```

---

## 🏁 Flag

```text
e4ce96139449eb34a9cd02531b023ac9
```

---

## 🛡️ Causa Raíz y Recomendaciones

- **Exposición de información sensible (CWE-200 / CWE-209):** El endpoint `/password/inicio` filtraba el hash de la contraseña en la respuesta HTTP. El backend jamás debe devolver hashes ni datos de credenciales hacia el cliente.
- **Secreto 2FA compartido / estático (CWE-798 / CWE-321):** Utilizar la misma clave criptográfica para todos los usuarios (`ARTESTUDIOSHAREDSECRET...`) anula por completo el factor de posesión del 2FA. Cada cuenta debe tener una semilla generada de forma pseudoaleatoria segura (CSPRNG) y almacenada cifrada individualmente en base de datos.
- **Política de contraseñas débiles:** La cuenta privilegiada utilizaba una contraseña vulnerable a ataques de diccionario básico (`ronald`).
