# Desafío - Vulpasar (HackLab)

**Plataforma:** HackLab (SoftwareSeguro)  
**Edición:** HackLab 2026  
**Categoría:** Forense (Análisis Forense de Disco / Artefactos de Navegador - Firefox)  
**Autor:** adonaissh  

---

## 📌 Enunciado

> **Vulpasar** es un delincuente con múltiples personalidades, y uno de los más hostiles que han existido. Se capturó una notebook que utilizaba y se sabe que almacena un archivo muy valioso llamado **`ev`**.
>
> **Credenciales de acceso a la máquina:**
> - Usuario: `ch10xo`
> - Contraseña: `vulpasar`
>
> Se entrega una imagen de máquina virtual en formato OVA (`~6 GB`), correspondiente a un sistema Linux (Xubuntu).
>
> **Objetivo:** Encontrar y recuperar el contenido del archivo de evidencia `ev`.

---

## 🔍 Análisis Inicial y Reconocimiento

Se importó e inició la imagen `.ova` en VirtualBox y se inició sesión como `ch10xo` / `vulpasar`.

### 1. Búsqueda preliminar de archivos en el sistema

Desde una terminal se buscó el archivo objetivo en todo el sistema de archivos:

```bash
sudo find / -iname "ev" -o -iname "ev.*" 2>/dev/null
```

Se identificó la presencia de un archivo comprimido protegido por contraseña (cifrado AES) que contenía la evidencia:
- Archivo comprimido tipo `zip` / contenedor protegido.
- En su interior se encontraba el archivo de evidencia `ev`.
- Paralelamente existían trampas (*decoy bombs*): archivos señuelo con decenas de frases y hashes falsos para despistar y provocar falsos positivos en intentos de fuerza bruta directa sobre el contenedor.

---

## 🔬 Investigación Forense y Artefactos

Dado que el enunciado enfatiza que Vulpasar posee *"múltiples personalidades"*, se investigó la huella de actividad del usuario y el uso de perfiles digitales en la notebook.

### 1. Revisión de cuentas locales

```bash
cat /etc/passwd | grep -E "home|sh$"
ls -la /home
```

### 2. Extracción de artefactos de navegador (Mozilla Firefox)

El almacenamiento más común de identidades y credenciales en una estación de trabajo reside en el perfil de navegación web:
- Directorio de perfil: `~/.mozilla/firefox/*.default*/`
- Archivos de interés forense:
  - `logins.json` / `key4.db`: Almacén de credenciales guardadas en Firefox.
  - `places.sqlite`: Historial de navegación y marcadores.
  - Cookies y sesiones activas.

Al inspeccionar el gestor de contraseñas de Firefox o utilizar herramientas de extracción de credenciales (`firepwd.py` o inspección de perfiles guardados):
- Se encontró una cuenta guardada de una red social (**Facebook**) perteneciente a una de las personalidades/alias alternativos de Vulpasar.
- Se extrajo la contraseña en texto plano asociada a esa identidad guardada.

---

## 🚀 Explotación y Recuperación de la Flag

### 1. Desbloqueo del archivo `ev`

Al probar la contraseña recuperada del perfil de Firefox contra el archivo comprimido protegido por contraseña (reutilización de credenciales por parte del objetivo):
- El archivo `zip` se desencriptó correctamente sin necesidad de fuerza bruta intensiva ni sufrir por las trampas (*decoys*).
- Se extrajo el archivo legítimo `ev`.

### 2. Lectura de la evidencia

Al volcar el contenido del archivo `ev`:

```bash
cat ev
```

Se obtuvo la flag de evidencia digital del desafío:

```text
==================================================
                 FLAG DE VULPASAR
==================================================

Flag: 660b416167e7fd839bc06c61bb5a184b
```

---

## 🏁 Flag

```text
660b416167e7fd839bc06c61bb5a184b
```

---

## 🛡️ Causa Raíz y Lecciones de Forense

- **Reutilización de contraseñas (Password Reuse):** El sospechoso utilizó la misma clave para resguardar archivos confidenciales/cifrados que la utilizada en servicios web y redes sociales almacenadas en su navegador.
- **Fuga de credenciales en almacenamiento local del navegador:** Guardar contraseñas en el navegador sin una contraseña maestra (Primary Password) permite que cualquier usuario con acceso al sistema o analista forense extraiga los secretos en texto plano a partir de `key4.db` y `logins.json`.
- **Evasión de señuelos (Anti-Forensics / Decoys):** En análisis forense, los atacantes o creadores de desafíos a menudo colocan señuelos masivos para saturar scripts de cracking o confundir con falsas flags; la correlación cruzada con artefactos del usuario (historial, perfiles, credenciales guardadas) es la vía más certera para llegar a la evidencia legítima.
