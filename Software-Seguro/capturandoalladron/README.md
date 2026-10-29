# Capturando al Ladrón — Writeup

**Plataforma:** HackLab (SoftwareSeguro)  
**Categoría:** Reversing APK / Bypass de Controles de Identidad  
**Autor:** Lucas  
**Flag:** `2488f977ed47ff0de86c1716640a501b`

---

## 1. Descripción del Desafío

Corre el año 264 en la República Martiana. Allí cada ciudadano se identifica con su Credencial de Identidad Marciana (CIM).  
**VerificAR Marte** es la app móvil oficial que verifica esa identidad: toma una foto al frente y otra al dorso de tu credencial y, si todo está en orden, emite a tu nombre un certificado de identidad marciana verificada.

Antes de enviar nada, la app móvil lee los datos por OCR, valida el formato de la credencial, reconoce el logo oficial y muestra los datos sin dejar editarlos.

**Objetivo:** Suplantar la identidad de la ladrona **VENKRA DOSS, KAIRA LOM** (matrícula `MRC-48217390`, 45 años de edad) y lograr que el servicio emita el certificado a su nombre.

---

## 2. Reconocimiento e Ingeniería Inversa de la APK

Se analizó el archivo `verificar.apk` provisto por el reto.

### Desensamblado de Clases DEX
Examinando los bytecode DEX del paquete `com.vulnlabs.verificar`:
* **`CapturaActivity`:** Administra la cámara (CameraX) y toma dos capturas: `frente.jpg` y `dorso.jpg`.
* **`Ocr.kt`:** Utiliza la librería local de Google ML Kit Text Recognition para escanear el texto de las imágenes usando expresiones regulares:
  * Matrícula: `MRC[-\s]?(\d{8})`
  * Fechas: `\b(\d{2}/\d{2}/\d{4})\b`
  * Sexo: `SEXO[:\s]*([FMX])`
  * Comprueba la presencia del logo oficial de la República Martiana.
* **`ConfirmarActivity`:** Recibe los datos extraídos por el OCR y muestra los campos en pantalla como etiquetas no editables (`tvApellido`, `tvNombre`, `tvMatricula`, etc.). Al pulsar el botón verificar, ejecuta una petición `POST` multipart.
* **`Api.kt` / `ConfirmarActivity.enviar`:** Realiza una llamada de red usando OkHttp hacia:
  * **Base URL:** `https://auth.shared.softwareseguro.com.ar`
  * **Endpoint:** `POST /api/verificar`
  * **Cuerpo:** `multipart/form-data` con los campos:
    * `apellido`
    * `nombre`
    * `matricula`
    * `sexo`
    * `fecha_nacimiento`
    * `foto_frente` (frente.jpg)
    * `foto_dorso` (dorso.jpg)

---

## 3. Descubrimiento de Datos Críticos y Validación del Backend

Al consultar la raíz del servicio web (`GET https://auth.shared.softwareseguro.com.ar/`), la página reveló la ficha oficial del titular de la cuenta objetivo:
* **Titular:** `VENKRA DOSS, KAIRA LOM`
* **Matrícula:** `MRC-48217390`
* **Sexo:** `F`
* **Nacimiento:** `14/03/0219` (45 años respecto al año actual 264)
* **Vencimiento:** `14/03/0241`

### Verificación de Controles del Servidor
Al enviar una petición de prueba, el servidor expuso su pipeline de validación detallado:
```json
{
  "controles": {
    "datos": true,
    "dorso": true,
    "foto_frente": true,
    "ocr_dorso": true,
    "ocr_frente": true,
    "similitud_frente": { "distancia": 1, "umbral": 22 }
  }
}
```
El backend verifica:
1. **Presencia y formato de imágenes** (`foto_frente`, `dorso`).
2. **Similitud del logo y plantilla del frente** (`similitud_frente`).
3. **Consistencia de OCR del servidor contra los campos enviados** (`ocr_frente`, `ocr_dorso`).
4. **Validación de reglas de negocio / datos del titular** (`datos`).

---

## 4. Explotación y Forjado de Credenciales

Para superar todos los controles sin necesidad de interactuar manualmente con un emulador Android:

1. Se reutilizaron las plantillas oficiales `cim-frente.png` y `cim-dorso.png` para mantener intacto el logo y asegurar una distancia de similitud óptima ($\le 1$).
2. Se desarrolló un script en PowerShell/Python que reescribe de forma limpia los campos de texto:
   * **Frente:**
     * `APELLIDO`: `VENKRA DOSS`
     * `NOMBRE`: `KAIRA LOM`
     * `SEXO`: `F`
     * `MATRICULA`: `MRC-48217390`
     * `NACIMIENTO`: `14/03/0219`
     * `VENCIMIENTO`: `14/03/0241`
   * **Dorso (Zona de Lectura Mecánica - MRZ Doc 9303 TD1):**
     * Con fuente monoespaciada a paso exacto de 11.8px:
       * Línea 1: `IDMRCMRC48217390<<<<<<<<<<<<<<<`
       * Línea 2: `0219030F0241030MRC<<<<<<<<<<<<<0`
       * Línea 3: `VENKRA<DOSS<<KAIRA<LOM<<<<<<<<<`
3. Se envió la petición multipart directamente mediante `curl`:
   ```bash
   curl -s -k -X POST https://auth.shared.softwareseguro.com.ar/api/verificar \
     -F "apellido=VENKRA DOSS" \
     -F "nombre=KAIRA LOM" \
     -F "matricula=MRC-48217390" \
     -F "sexo=F" \
     -F "fecha_nacimiento=14/03/0219" \
     -F "foto_frente=@frente_final.jpg;type=image/jpeg;filename=frente.jpg" \
     -F "foto_dorso=@dorso_final.jpg;type=image/jpeg;filename=dorso.jpg"
   ```
4. El servidor respondió:
   ```json
   {
     "certificado_url": "/certificado?token=7552a909e2f20be956b5f42c53674f24437a2865277f8ccf100a8000b6dd0b06",
     "controles": { "datos": true, "dorso": true, "foto_frente": true, "ocr_dorso": true, "ocr_frente": true, "similitud_frente": { "distancia": 1, "umbral": 22 } },
     "mensaje": "Identidad marciana verificada. Cuenta habilitada.",
     "verificado": true
   }
   ```
5. Al acceder a `/certificado?token=...`, se obtuvo el certificado oficial y la flag.

---

## 5. Flag Obtenida

```text
2488f977ed47ff0de86c1716640a501b
```

---

## 6. Causa Raíz y Remediación (OWASP)

* **Causa Raíz:**
  * **CWE-602 (Client-Side Enforcement of Server-Side Security):** La aplicación móvil dependía de que el usuario no pudiera editar los campos en pantalla para garantizar la veracidad de la credencial física.
  * **Falta de Validación de Autenticidad Documental Criptográfica:** El backend se limitó a comprobar OCR sintáctico y coincidencia de plantilla visual. En documentos de identidad, el texto plano impreso es fácilmente manipulable digitalmente.
* **Remediación:**
  1. **Firmas Digitales Asimétricas (PKI):** Los documentos de identidad deben incorporar códigos bidimensionales (como QR o PDF417) firmados criptográficamente con la clave privada de la autoridad de emisión (*Registro Colonial Marciano*). El backend debe validar la firma contra la clave pública del Estado, haciendo inviable cualquier forjado visual del texto.
  2. **Detección de Liveness / Prueba de Vida:** Exigir micro-movimientos o captura de video en vivo para prevenir la presentación de imágenes estáticas renderizadas por software.
