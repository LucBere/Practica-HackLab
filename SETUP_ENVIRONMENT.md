# 🛠️ Setup del Entorno — WSL2 / Ubuntu para Desafíos de CTF y Hacking

Esta guía explica cómo dejar listo un entorno Linux en Windows (**WSL2 con Ubuntu**) para resolver los desafíos de este repositorio, con las herramientas más utilizadas: `gdb`, `checksec`, `pwntools`, `Python 3`, `exiftool`, `ImageMagick` y `Burp Suite`.

No hace falta una PC con Linux nativo ni una máquina virtual pesada: WSL2 corre el kernel de Linux directamente integrado en Windows con excelente rendimiento y sin necesidad de particionar discos.

---

## 1. 🚀 Instalar WSL2 con Ubuntu

Abre **PowerShell como Administrador** y ejecuta:

```powershell
wsl --install
```

Esto instala WSL2 y la distribución Ubuntu por defecto. Reinicia la PC si el instalador lo solicita.  
Al abrir Ubuntu por primera vez, te pedirá configurar un nombre de usuario y contraseña de Linux (son independientes de tu cuenta de Windows).

> [!TIP]
> Para abrir la terminal en el día a día, busca **"Ubuntu"** directamente en el menú inicio de Windows (tecla `Win` → escribir `Ubuntu`). La consola nativa maneja mucho mejor los atajos de teclado y el copiado/pegado que ejecutar `wsl` desde PowerShell.

### (Opcional) Mover WSL a otro disco (ej. D:)
Por defecto, el disco virtual (`.vhdx`) de Ubuntu se almacena en la unidad del sistema (`C:`). Si prefieres alojarlo en un disco secundario para ahorrar espacio:

```powershell
wsl --shutdown
mkdir D:\WSL
wsl --export Ubuntu D:\WSL\ubuntu-backup.tar
wsl --unregister Ubuntu
wsl --import Ubuntu D:\WSL\Ubuntu D:\WSL\ubuntu-backup.tar
```

Como `wsl --import` restablece el usuario predeterminado a `root`, para volver a tu usuario normal ingresa a Ubuntu con `wsl -d Ubuntu` y ejecuta:

```bash
echo -e "[user]\ndefault=TU_USUARIO" | sudo tee /etc/wsl.conf
exit
```

Luego desde PowerShell reinicia el subsistema:
```powershell
wsl --shutdown
wsl
```

---

## 2. 🧰 Instalación de Herramientas Base

Dentro de la terminal de **Ubuntu**, actualiza los repositorios e instala las dependencias fundamentales:

```bash
sudo apt update && sudo apt install -y \
  gdb file binutils checksec \
  python3 python3-pip python3-venv python3-full \
  cmake build-essential python3-dev libffi-dev \
  exiftool imagemagick
```

### ¿Qué hace cada herramienta?
- **`gdb`**: Debugger por excelencia para analizar binarios e inspeccionar memoria (vital en *Desbordamiento de memoria* y *Reversing*).
- **`checksec`**: Inspecciona las protecciones activas en un binario ELF (NX, PIE, Stack Canaries, ASLR/RELRO).
- **`file` / `binutils`**: Identificación rápida de cabeceras, arquitecturas y herramientas de inspección de binarios (`strings`, `objdump`, `readelf`).
- **`python3`, `pip`, `venv`**: Entorno de desarrollo para scripts de explotación y automatización.
- **`cmake`, `build-essential`, `python3-dev`, `libffi-dev`**: Herramientas y cabeceras de compilación necesarias para construir módulos nativos de Python (como `unicorn` dentro de `pwntools`).
- **`exiftool`**: Lectura y modificación de metadatos EXIF en archivos multimedia (fundamental cuando el vector de inyección proviene de metadatos subidos).
- **`imagemagick` (`convert`)**: Manipulación, conversión y recompresión de imágenes conservando metadatos para evadir restricciones de tamaño de carga.

---

## 3. 🐍 Instalación de Pwntools & Entornos Python

En versiones recientes de Ubuntu/Debian, `pip` restringe la instalación global mediante la política *"externally managed environment"*.

### Opción A: Instalación directa (Rápida)
```bash
pip3 install pwntools --break-system-packages
```

### Opción B: Entorno Virtual (Recomendada / Limpia)
```bash
python3 -m venv ~/ctf-env
source ~/ctf-env/bin/activate
pip install pwntools
```
*(Recuerda activar el entorno con `source ~/ctf-env/bin/activate` cada vez que abras una nueva terminal).*

### Complemento: pwndbg (Mejora visual para GDB)
Mejora sustancialmente la visualización de registros, stack e instrucciones en GDB durante la explotación de memoria:

```bash
cd ~
git clone https://github.com/pwndbg/pwndbg
cd pwndbg
./setup.sh
```

---

## 4. 🌐 Burp Suite (Herramienta Transversal Web)

Para desafíos web (**SQLi**, **IDOR**, **XSS**, **Mass Assignment**, **CSRF**, etc.) es fundamental interceptar y alterar peticiones HTTP/S.

1. Descarga la versión **Community Edition** (gratuita) desde:  
   👉 [PortSwigger Burp Suite Community Download](https://portswigger.net/burp/communitydownload)
2. Instálala directamente en **Windows** (no es necesario ejecutarla dentro de WSL).
3. Configura el navegador o utiliza el navegador integrado de Burp Suite (*Open Browser* en la pestaña Proxy) que ya viene preconfigurado con el certificado CA.

---

## 5. 🔄 Interoperabilidad de Archivos: Windows ↔ WSL

Las unidades de Windows se montan automáticamente en Ubuntu bajo la ruta `/mnt/<letra_unidad>/`.

### Ejemplos útiles:
- **Ver la carpeta de este repositorio desde Ubuntu:**
  ```bash
  ls /mnt/d/HackLab_Practica/Practica-HackLab-main/
  ```

- **Copiar un archivo de Windows a tu carpeta de trabajo en Linux:**
  ```bash
  mkdir -p ~/ctf
  cp /mnt/d/HackLab_Practica/archivo.zip ~/ctf/
  ```

- **Copiar un archivo procesado en Linux de vuelta a Windows:**
  ```bash
  cp ~/ctf/foto_modificada.jpg /mnt/c/Users/TU_USUARIO/Desktop/
  ```

---

## 6. ⚠️ Solución a Problemas Comunes

- **Error `^M` o `command not found` al pegar comandos:**  
  Ocurre al copiar texto desde Windows con saltos de línea CRLF (`\r\n`). Utiliza la aplicación nativa "Ubuntu" o pega con clic derecho dentro de la terminal en lugar de `Ctrl + V`.
- **`pip install` falla con *externally managed environment*:**  
  Agrega la bandera `--break-system-packages` o usa un entorno virtual (`python3 -m venv`).
- **Falla la compilación de librerías (`cmake` / `pkg-config` not found):**  
  Asegúrate de haber instalado `build-essential` y `cmake` antes de reinstalar (`sudo apt install -y cmake build-essential`).
- **Archivo rechazado por límite de tamaño en el servidor web:**  
  Si la plataforma impone un límite (ej. máx. 1 MB) y la imagen generada es muy pesada, redimensiónala preservando los metadatos inyectados:
  ```bash
  convert foto.jpg -resize 800x800 -quality 70 foto_optimizada.jpg
  exiftool -Make foto_optimizada.jpg   # Verificar que conserve el payload
  ```

---

## ⚡ Resumen Rápido (Copy & Paste)

```bash
sudo apt update && sudo apt install -y \
  gdb file binutils checksec \
  python3 python3-pip python3-venv python3-full \
  cmake build-essential python3-dev libffi-dev \
  exiftool imagemagick

pip3 install pwntools --break-system-packages
```
Con esto instalado en Ubuntu WSL más **Burp Suite Community** en Windows, tu estación de trabajo queda 100% equipada.
