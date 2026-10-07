# Compra de Divisas — Broken Access Control

**Categoría:** Broken Access Control
**Plataforma:** SoftwareSeguro HackLab
**Flag:** `afc6a148d3b71b6776bcc7015e97c2a9`
**Autor del writeup:** adonaissh

## Descripción del desafío

Un banco está al borde de la quiebra: faltan dólares en sus reservas. Un tweet anónimo
sugiere que hay una forma de comprar dólares "baratos" en el sistema de compra de
divisas del banco. El objetivo es lograr comprar más de **10.000 USD**, partiendo de
un saldo inicial de **$85.000 ARS** y una cotización oficial de **369.00** (lo que
legítimamente alcanzaría para comprar como máximo ~230 USD).

## Análisis inicial

La aplicación expone un único formulario POST a `/` con tres campos:

```html
<input type="text" name="cotizacion" id="cotizacion" value="369.00" readonly>
<input type="number" name="monto" id="monto" min="1" required>
<input type="text" name="total" id="total" readonly>
```

El cálculo del total en dólares se hace enteramente en JavaScript, en el navegador:

```javascript
function calcularTotal() {
    var montoEnPesos = parseFloat(document.getElementById('monto').value);
    var cotizacionActual = parseFloat(document.getElementById('cotizacion').value);
    var totalEnDolares = montoEnPesos / cotizacionActual;
    document.getElementById('total').value = totalEnDolares.toFixed(2);
}
```

Los tres campos (`cotizacion`, `monto`, `total`) viajan como parte del `POST`, aunque
dos de ellos (`cotizacion` y `total`) estén marcados como `readonly` en el HTML. Esto
es solo una restricción cosmética del lado cliente: cualquier proxy de intercepción
(Burp Suite) permite modificarlos libremente antes de que la request llegue al
servidor.

El estado de la cuenta (saldo en ARS y en USD) se guarda directamente en la cookie de
sesión de Flask, firmada con `itsdangerous`:

```
session=eyJ1c2VyIjp7ImFyc19tb25leSI6ODUwMDAsInVzZF9tb25leSI6MH19.asZC8g.ct4ZxBVAlmd5efidcIxeUqFz6-A
```

Decodificando el payload (sin necesidad de la clave, ya que la firma solo impide
*modificar* el contenido, no *leerlo*):

```json
{"user": {"ars_money": 85000, "usd_money": 0}}
```

## Hipótesis descartadas (y cómo se descartaron)

Antes de llegar al vector real, se probaron y descartaron varias hipótesis más obvias:

### 1. Manipular directamente el campo `total`

Request:
```
cotizacion=369.00&monto=1000&total=1000
```

Resultado: el servidor **recalculó** el total en dólares usando `monto / cotizacion`
server-side, ignorando por completo el `total` que mandé. Conclusión: el total no es
confiable del lado cliente, pero tampoco es explotable directamente — el servidor no
lo usa para nada.

### 2. Monto mayor al saldo disponible

Request:
```
cotizacion=369.00&monto=5000000&total=13550.81
```

Resultado:
```
No cuenta con saldo suficiente para la operación.
```

El servidor valida correctamente `monto <= saldo_disponible`.

### 3. Monto negativo

Request con `monto=-1000` → rechazado con un mensaje de validación ("el monto debe ser
mayor a 0"). El servidor valida correctamente `monto > 0`.

### 4. HTTP Parameter Pollution sobre `monto`

Se probó enviar el campo `monto` duplicado, apostando a que distintas partes del
código del servidor pudieran leer valores distintos de la misma request (una para
validar el saldo, otra para calcular el descuento):

```
cotizacion=369.00&monto=1&monto=5000000&total=13550.81
```

Resultado: el saldo pasó de $85000 a $84999 (consistente con usar **monto=1**, el
*primer* valor, tanto para la validación de saldo como para el descuento real). Esto
confirma que Werkzeug (el framework HTTP detrás de Flask) resuelve parámetros
duplicados devolviendo siempre el primer valor, de forma consistente en todo el
código — no hay bifurcación que explotar ahí.

### 5. Crackeo de la `SECRET_KEY` de Flask (forjar la cookie)

Como el saldo vive en la cookie de sesión firmada, se intentó identificar la
`SECRET_KEY` usada para firmarla, lo cual habría permitido forjar una cookie con
cualquier saldo:

```bash
pip3 install "flask-unsign[wordlist]" --break-system-packages

~/.local/bin/flask-unsign --unsign --cookie "<cookie>" \
  --wordlist /home/adonai/.local/lib/python3.14/site-packages/flask_unsign_wordlist/wordlists/all.txt
```

Resultado:
```
[*] Session decodes to: {'user': {'ars_money': 85000, 'usd_money': 0}}
[*] Starting brute-forcer with 8 threads..
[!] Failed to find secret key after 55982 attempts.
```

La clave no estaba en ninguna wordlist de claves filtradas/comunes conocidas —
descartado como vector práctico.

## Vector real: confiar en un campo "readonly" controlado por el cliente

El dato clave que faltaba probar: en **todas** las pruebas anteriores se había dejado
`cotizacion=369.00` (el valor "correcto", el que el propio formulario mostraba). Nunca
se había tocado ese campo.

El campo `cotizacion` es `readonly` en el HTML — es decir, el usuario no puede
editarlo *desde la interfaz normal del navegador*. Pero al viajar como un campo de
formulario POST común, nada impide modificarlo con un proxy de intercepción. La
pregunta era: ¿el servidor usa un valor de cotización fijo propio al momento de
calcular cuántos dólares entregar, o confía en el valor que el cliente le manda en
`cotizacion`?

### Request final

```
POST / HTTP/2
Host: chl-...-compra-divisas.softwareseguro.com.ar
Cookie: session=<cookie con ars_money=85000, usd_money=0>
Content-Type: application/x-www-form-urlencoded

cotizacion=0.01&monto=1000&total=100000.00
```

### Respuesta

```html
<div class="alert alert-success">
    Desafío superado: afc6a148d3b71b6776bcc7015e97c2a9
</div>
...
<td>Dólares</td><td>us$100000.00</td>
<td>Pesos</td><td>$84000.00</td>
```

Con solo **$1.000 ARS**, al declarar una cotización falsa de **0.01** (en vez de la
real, 369.00), el servidor calculó `monto / cotizacion = 1000 / 0.01 = 100000` y
acreditó **100.000 USD** en la cuenta — muy por encima del objetivo de 10.000 USD.

## Causa raíz

El servidor tiene dos responsabilidades mal distribuidas entre cliente y servidor:

- **`total`**: sí se recalcula server-side a partir de `monto` y `cotizacion` — esta
  parte está bien implementada.
- **`cotizacion`**: se asume como un dato *de solo lectura*, confiando en que el
  atributo HTML `readonly` sea suficiente control de acceso. El servidor nunca
  reemplaza el valor recibido por una tasa de cambio propia (hardcodeada o leída de
  una fuente interna), sino que usa directamente el `cotizacion` que viene en el
  `POST` para hacer el cálculo `monto / cotizacion`.

En otras palabras: el único campo que realmente necesitaba ser inmutable para el
cliente (la tasa de cambio) es, paradójicamente, el único que el servidor nunca
valida ni recalcula — confía en una restricción puramente visual/cosmética
(`readonly` en el HTML) como si fuera un control de seguridad real.

Esto es un caso de libro de **Broken Access Control**: el control de acceso (qué
puede y qué no puede modificar el usuario) existe únicamente en la capa de
presentación (HTML/JS del navegador) y no se re-valida en el servidor, que es la
única capa en la que un control de este tipo tiene algún valor real.

## Recomendaciones de remediación

1. **Nunca confiar en valores de solo-lectura del lado cliente.** Atributos como
   `readonly` o `disabled` en HTML son UX, no seguridad: el servidor debe tratar
   cualquier campo de un formulario como potencialmente modificado por un atacante.
2. **La cotización debe ser una fuente de verdad exclusivamente server-side.** El
   servidor debería leer la tasa de cambio actual desde su propia base de datos o
   configuración interna, ignorando por completo cualquier valor de `cotizacion`
   recibido en la request, igual que ya hace correctamente con el `total`.
3. **Validar también límites de negocio adicionales**, como un monto máximo de compra
   diario/por operación, independientemente de si el cálculo de la tasa es correcto,
   para acotar el impacto de futuros bugs similares.
4. **Registrar y alertar sobre operaciones con tasas de cambio anómalas** (muy
   alejadas de la cotización oficial vigente), lo cual habría permitido detectar este
   abuso en producción antes de que fuera explotado.