# Desafío - SecureChat (HackLab)

**Plataforma:** HackLab (SoftwareSeguro)
**Categoría:** Reversing APK - Fuerza bruta

## Análisis

SecureChat es una app híbrida Ionic/Cordova (Angular + Capacitor) empaquetada como APK. Al no tener código nativo relevante, toda la lógica de negocio vive en JavaScript dentro de `assets/public/`, extraíble directamente del APK como si fuera un ZIP:

```bash
unzip -o secure-chat.apk "assets/public/*.js" -d extracted
```

La pantalla de login pide un PIN de 4 dígitos. Buscando `pin` en los bundles JS se encuentra el chunk `2004.9767c092f9b52e69.js`, que contiene tanto el componente `app-unlock` como el servicio que valida el PIN.

### El servicio de validación

```js
class s {
  constructor() {
    this.pinData = "U2FsdGVkX19fmBw92ecLtpE1bRwUFDL2lhCKJJLubM1TNgGCnLeE+ndbtICJBszUNjetOdtUPNwjMu6Hy4+d/A==";
    // ...
  }
  verifyPin(r) {
    if (4 !== r.length || !/^\d{4}$/.test(r))
      return "";
    try {
      const F = CryptoJS.AES.decrypt(this.pinData, r).toString(CryptoJS.enc.Utf8);
      return 32 == F.length
        ? F
        : "ESTE PIN NO TIENE TANTOS PRIVILEGIOS.";
    } catch {
      return "";
    }
  }
}
```

Y en el componente de la pantalla de unlock:

```js
onLogin() {
  const F = this.cs.verifyPin(this.pin.toString());
  F
    ? this.router.navigate(["/messages"], { state: { result: F } }) // éxito
    : (this.attempts++, this.errorMsg = "PIN incorrecto");          // falla
}
```

`pinData` es un blob cifrado con **AES usando el PIN como passphrase** (derivación de clave estilo OpenSSL `EVP_BytesToKey`, salt embebido en el propio blob `Salted__...`). El PIN correcto desencripta `pinData` en un string de exactamente 32 caracteres.

### La vulnerabilidad: bug de autenticación (truthy check)

El problema no está solo en que el PIN sea de 4 dígitos (10.000 combinaciones, fuerza bruta trivial offline porque el blob cifrado viaja embebido en el cliente). El problema real es más grave: `verifyPin()` **nunca devuelve un booleano**. Devuelve:

- `""` (string vacío → falsy) solo si `AES.decrypt().toString(Utf8)` **lanza una excepción** (p. ej. relleno PKCS7 corrupto en algunos casos).
- El string literal `"ESTE PIN NO TIENE TANTOS PRIVILEGIOS."` cuando la desencriptación **no lanza excepción pero el resultado no mide 32 caracteres** — que es el caso normal con un PIN incorrecto.

Como `onLogin()` evalúa el resultado con `F ? éxito : error`, y ese string de "PIN incorrecto" **no está vacío**, JavaScript lo trata como `truthy`. Resultado: **casi cualquier PIN de 4 dígitos que no provoque una excepción de desencriptación deja entrar igual**, sin ser el PIN real. Se confirmó probando con `7777` (PIN arbitrario) y logrando "Acceso concedido" en la app.

Adicionalmente, la ruta `/messages` no tiene ningún `canActivate` guard en la configuración de rutas de Angular:

```js
{ path: "messages", loadComponent: () => R.e(7231).then(...).then(pt => pt.MessagesPage) }
```

por lo que ni siquiera depende de pasar por la pantalla de unlock — es una restricción puramente de UI, no de enrutamiento.

## Explotación

### 1. Bypass de UI (confirmación del bug)

Cualquier PIN de 4 dígitos "al azar" (ej. `7777`) alcanza para entrar a `/messages`, por el bug de truthy-string descripto arriba.

### 2. Recuperar el PIN real y la flag (fuerza bruta offline)

Como `pinData` viaja completo en el JS del cliente, se puede probar localmente, sin tocar el servidor, las 10.000 combinaciones posibles y quedarse con la única que desencripta a **exactamente 32 caracteres** (la condición real de éxito, no el bug):

```js
const CryptoJS = require("crypto-js");
const pinData = "U2FsdGVkX19fmBw92ecLtpE1bRwUFDL2lhCKJJLubM1TNgGCnLeE+ndbtICJBszUNjetOdtUPNwjMu6Hy4+d/A==";

for (let i = 0; i < 10000; i++) {
  const pin = i.toString().padStart(4, "0");
  try {
    const out = CryptoJS.AES.decrypt(pinData, pin).toString(CryptoJS.enc.Utf8);
    if (out.length === 32) {
      console.log("PIN real:", pin, "->", out);
      break;
    }
  } catch {}
}
```

```
PIN real: 5865 -> b5c909a6f9fe6cf07530478d57cd7977
```

El PIN real resulta ser **5865**, y la desencriptación produce directamente el string de 32 caracteres hexadecimales que constituye la flag.

## Flag

```
b5c909a6f9fe6cf07530478d57cd7977
```

## Causas raíz / recomendaciones

- **Autenticación en el cliente:** todo el material necesario para validar (y para forzar) el PIN vive en el JS del APK. La validación debe hacerse server-side, nunca confiando en lógica del cliente.
- **Bug de truthy check:** nunca usar un string de error no vacío como valor de retorno en un camino que se evalúa como booleano de éxito/fallo; usar un objeto `{ ok: boolean, data }` o lanzar excepciones de forma consistente.
- **Espacio de claves insuficiente:** un PIN de 4 dígitos numéricos (10.000 combinaciones) como única protección de datos cifrados es trivialmente bruteforceable offline.
- **Falta de guard de ruta:** `/messages` debería estar protegida con un `canActivate` real que dependa de un token de sesión validado server-side, no solo de la navegación condicional de un componente.