# Desafío - Análisis de TPs (HackLab)

**Plataforma:** Software Seguro — HackLab  
**Edición:** HackLab 2026  
**Categoría:** Condiciones de carrera (Race Condition - TOCTOU) + Mass Assignment / Bypass de campo `readonly`  
**Equipo:** GoT  
**Autor:** adonaissh  
**Flag:** `3f72fc9526b504a7dfd34e4ffe0fb3f0`  

---

## 📌 Enunciado

> La *Magnífica Universidad* usa esta plataforma para analizar y calificar los trabajos prácticos de sus alumnos.
>
> **Marcelo Gallardo** (`marcelo@magnificauniversidad.com.ar`) perdió el acceso a su cuenta de Gmail universitaria y no puede subir su TP, por lo que recibirá una calificación muy baja. Necesita aprobar con un **10** sí o sí para no perder su beca.
>
> **Objetivo:** Lograr que el TP de Marcelo obtenga un 10, sin que Marcelo pueda subirlo él mismo, y obtener el hash del ganador (flag).  
> **URL:** `https://chl-83c161a1-69c7-43e8-af89-7d5c75f8a376-analisis-tps.softwareseguro.com.ar/login`

---

## 🔍 Reconocimiento

### 1. Modelo Funcional de la Plataforma
La entrega **no es una subida HTTP directa**:
1. El alumno coloca su archivo PDF en una **carpeta compartida de Google Drive**.
2. Presiona el botón **"Actualizar"** en la web (`POST /update`).
3. El servidor backend inspecciona la carpeta en Drive, detecta los archivos nuevos, extrae sus metadatos internos y texto, califica el contenido contra una rúbrica automática y determina el campo **`ganador`**.

| Ruta | Método | Función |
|---|---|---|
| `/login` | GET/POST | Autenticación |
| `/` (home) | GET | Listado de TPs recibidos y evaluados |
| `/perfil` | GET/POST | Ver y editar perfil del usuario |
| `/update` | POST | Procesa la carpeta de Drive y retorna JSON `{ok, html, ganador}` |
| `/logout` | POST | Cierre de sesión |

### 2. Respuesta de `/update` y Detalle Crítico del Front-End
Al analizar el script `/static/actualizar.js`, se descubrió que el frontend procesa únicamente `html`, `ok` y `error`, **pero descarta por completo el campo `ganador`** del JSON. Por este motivo, la condición ganadora no se pintaba en la interfaz de usuario: era indispensable auditar el **JSON crudo** de la respuesta de red.

Estructura de la ficha extraída por cada TP:
```text
Último editor : adonaipereztourn1          ← "Subido por" (propietario del archivo en Google Drive)
Autor         : marcelo@magnificauniversidad.com.ar  ← Metadata /Author interna del PDF
Título        : tp-1
Creado con    : Writer
Generado por  : LibreOffice 24.2
Nota          : 10.0 / 10
ganador       : null                        ← Campo donde se inyecta la flag
```

### 3. Observaciones Clave
- **"Subido por"** se obtiene de la **cuenta de Google que subió el archivo en Drive**, no del contenido ni del perfil web.
- En `/perfil`, el campo de correo electrónico figura visualmente bloqueado con la leyenda: *"El correo electrónico no se puede modificar"*.
- El procesamiento del endpoint `/update` toma **~800 ms** (medido de forma consistente entre 789 ms y 809 ms).

---

## 🔬 Identificación de Vulnerabilidades

El desafío exige satisfacer dos condiciones simultáneas: **Nota 10/10** + **Entrega atribuida a Marcelo**.

### Pieza 1: Bypass de Campo `readonly` (Mass Assignment / CWE-915)
El campo `email` en `/perfil` tiene únicamente el atributo `readonly` en el HTML (restricción exclusivamente de UI en el navegador). El backend en `POST /perfil` **acepta y procesa el parámetro sin ninguna lista blanca de campos mutables**. Es posible forzar el cambio de correo hacia `marcelo@magnificauniversidad.com.ar`.

*Sin embargo, esto solo no resuelve el desafío:* si se cambia el correo antes de procesar el archivo, la validación inicial de Drive detecta que el archivo fue subido por nuestra cuenta de Google y no por la cuenta de Marcelo, rechazando la entrega de inmediato.

### Pieza 2: Condición de Carrera (TOCTOU - CWE-367)
El endpoint `/update` ejecuta un flujo no atómico dividido en distintas fases en el tiempo:

| Fase | Operación | Estado evaluado |
|---|---|---|
| **Fase 1** | Validación del archivo | Perfil de la cuenta en sesión vs. Propietario en Google Drive |
| **Fase 2** | Corrección y Rúbricas | Calificación del texto y respuestas del PDF |
| **Fase 3** | Persistencia Final | **Identidad actual del perfil** al momento de guardar |
| **Fase 4** | Cálculo de Ganador | Condición de victoria |

**La ventana TOCTOU:**  
La **validación inicial** lee la identidad en un momento ($t_0$), y la **persistencia final** la lee ~800 ms más tarde ($t_1$).  
Si se actualiza el email mediante `POST /perfil` a mitad del procesamiento (~600 ms):
1. La validación inicial observa nuestra cuenta de control y aprueba el archivo de Drive.
2. La persistencia final toma la nueva identidad (`marcelo@magnificauniversidad.com.ar`) y guarda la entrega como si fuera de Marcelo con nota 10/10.

---

## 🚀 Cadena de Explotación Paso a Paso

### Paso 0: Generación del PDF con Nota 10/10
Para lograr el 10.0 perfecto, el PDF debía contener las 7 respuestas exactas de la rúbrica de criptografía en una sola página:

1. **Cifrado César:** Texto `SOFTWARE SEGURO` con $k=3 \rightarrow$ `VRIWZDUH VHJXUR`. Espacio de claves: 25 claves posibles.
2. **Fuerza Bruta César:** `PEVCGBTENSVN` con $k=13$ (ROT13) $\rightarrow$ `CRIPTOGRAFIA`. Método: probar desplazamientos de 1 a 25.
3. **Cifrado Vigenère:** `ATAQUEALAMANECER` con clave `CLAVE` $\rightarrow$ `CEALYGLLVQCYEXIT`. Explicación: es polialfabético y aplana las frecuencias.
4. **Base64:** `Q1RGe2Jhc2U2NF9ub19lc19jaWZyYWRvfQ==` $\rightarrow$ `CTF{base64_no_es_cifrado}`. Explicación: es codificación de transporte, no garantiza confidencialidad.
5. **XOR:** Cifrar `HOLA` con clave `0x2A` $\rightarrow$ Resultado: `62 65 66 6B`. Recuperación de clave: $K = P \oplus C \rightarrow 0x48 \oplus 0x62 = 0x2A$.
6. **Funciones Hash:** SHA-256 de `softwareseguro` (`1812acb8...`) y `Softwareseguro` (`a7e37a76...`). Propiedad: Efecto avalancha, función unidireccional no invertible.
7. **RSA:** $p=61, q=53, e=17 \rightarrow n=3233, \phi(n)=3120, d=2753, C=2790, m=65$. Explicación de factorización en números primos pequeños.

```text
Alumno: Marcelo Gallardo
Email: marcelo@magnificauniversidad.com.ar
```

### Paso 1: Subida a Google Drive
Se subió el archivo PDF a la carpeta compartida asegurando que sea una **copia nueva** con nombre único para evitar que el sistema lo catalogue como "ya procesado".

### Paso 2: Ejecución de la Carrera en Consola (`F12`)
Estando autenticado en la plataforma con el email propio de control, se ejecutó en la consola del navegador el script calibrado con un retraso empírico de **600 ms**:

```javascript
const CSRF = document.querySelector('input[name="csrf"]')?.value || 'token-csrf';
const MAIL_MARCELO = 'marcelo@magnificauniversidad.com.ar';
const DELAY = 600; // Ventana óptima medida dentro de los ~800ms de procesamiento

// 1. Disparar el procesamiento de Drive (~800 ms)
const pUpdate = fetch('/update', {
  method: 'POST',
  credentials: 'same-origin',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'application/json'
  },
  body: new URLSearchParams({ csrf: CSRF })
}).then(r => r.json());

// 2. A mitad del procesamiento, mutar la identidad del perfil hacia Marcelo
await new Promise(res => setTimeout(res, DELAY));
fetch('/perfil', {
  method: 'POST',
  credentials: 'same-origin',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded'
  },
  body: new URLSearchParams({
    csrf: CSRF,
    nombre: 'adonai',
    apellido: 'perez',
    email: MAIL_MARCELO
  })
});

// 3. Inspeccionar el JSON crudo retornado
const d = await pUpdate;
console.log('Ganador directo:', d.ganador);
console.log('Subido por:', d.html.match(/<td>([^<]+@[^<]+)<\/td>/)?.[1]);
console.log('Nota:', d.html.match(/<b>([\d.]+)<\/b>/)?.[1]);
```

**Salida en consola:**
```text
subido por: marcelo@magnificauniversidad.com.ar
nota: 10.0
ganador: null
```
La entrega quedó formalmente registrada a nombre de Marcelo con 10/10.

### Paso 3: Recálculo del Ganador y Flag
El estado de `ganador` se evalúa en una pasada posterior al cruzarse los registros ya almacenados en base de datos.  
Al recargar la página (**F5**) o emitir una nueva petición a `/update`:

```text
==================================================
                 ¡RETO COMPLETADO!
==================================================

Ganador: 3f72fc9526b504a7dfd34e4ffe0fb3f0
Última actualización: 0 nuevos, 1 ya procesado.

Archivo: TP-Final.pdf
Subido por: marcelo@magnificauniversidad.com.ar · 10.0/10 · procesado
```

---

## 🏁 Flag

```text
3f72fc9526b504a7dfd34e4ffe0fb3f0
```

---

## 🛡️ Causa Raíz y Recomendaciones

- **Causa Raíz:** Separación temporal no atómica entre la verificación de autoría y la persistencia de datos (CWE-367: TOCTOU), combinado con una asignación masiva de parámetros en el perfil (CWE-915) que permitía alterar el correo electrónico saltándose la restricción estética de `readonly`.
- **Recomendaciones:**
  - **Atomicidad Transaccional:** Congelar una instantánea inmutable de la sesión e identidad del usuario al iniciar `/update` y garantizar que todo el proceso utilice esa referencia única dentro de una transacción aislada de base de datos.
  - **Listas Blancas en Backend (Mass Assignment):** Prohibir la modificación de campos sensibles como el correo electrónico en endpoints genéricos de perfil; el backend debe ignorar o rechazar cualquier atributo no explícitamente editable.
  - **Vinculación Inmutable de Proveedores Externos:** Asociar las entregas mediante identificadores de cuenta inmutables (Google OAuth ID / Sub ID) y no mediante cadenas de texto editables por el usuario.
