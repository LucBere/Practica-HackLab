# Write-up: Secure Chat

## Información del Reto
- **Evento**: HackLab 2025 / 2026
- **Categoría**: Reversing Apk - Fuerza bruta
- **Descripción**: Te pasaron un APK que contiene chats sensibles cuya autenticación es vía PIN, ¿podrías abrirla para ver los chats?

## Causa Raíz
La aplicación verifica el PIN del usuario decifrando localmente un "blob" de datos (texto cifrado) utilizando **AES** (Algoritmo de Cifrado Simétrico), en donde el PIN numérico de 4 dígitos actúa directamente como la frase de contraseña o llave criptográfica.

Dado que un PIN numérico de 4 dígitos posee una **entropía sumamente baja** (solo 10,000 combinaciones posibles, desde `0000` hasta `9999`), cualquier atacante que logre extraer el código fuente del APK puede recuperar el texto cifrado (`pinData`) y realizar un ataque de **fuerza bruta offline**. Al ejecutarse offline en hardware moderno, este proceso puede probar todo el espacio de llaves en milisegundos y encontrar la contraseña correcta para vulnerar la confidencialidad de la aplicación.

## Metodología de Explotación (Prueba de Concepto)

1. **Extracción y Desempaquetado del APK:**
   Al descomprimir `secure-chat.apk` e inspeccionar el contenido, identificamos que se trata de una aplicación híbrida creada con **Ionic/Capacitor**. Por lo tanto, toda la lógica principal reside en archivos JavaScript minificados dentro del directorio `assets/public/`.

2. **Análisis Estático del Código (Reverse Engineering):**
   Explorando los *chunks* de JavaScript generados por Webpack, localizamos el componente de login y la página de los mensajes. Observamos la siguiente lógica encargada de validar el PIN:
   ```javascript
   verifyPin(r) {
       if(4 !== r.length || !/^\d{4}$/.test(r)) return "";
       try {
           // this.pinData = "U2FsdGVkX19fmBw92ecLtpE1bRwUFDL2lhCKJJLubM1TNgGCnLeE+ndbtICJBszUNjetOdtUPNwjMu6Hy4+d/A=="
           const F = u.AES.decrypt(this.pinData, r).toString(u.enc.Utf8);
           return 32 == F.length ? F : "ESTE PIN NO TIENE TANTOS PRIVILEGIOS."
       } catch {
           return ""
       }
   }
   ```
   Como se puede observar, el código confía ciegamente en `CryptoJS` (`u.AES.decrypt`) utilizando el PIN ingresado por el usuario (`r`) como llave.

3. **Ejecución del Ataque de Fuerza Bruta:**
   Conociendo el mecanismo (cifrado con salteado tipo OpenSSL provisto por CryptoJS) y el texto cifrado, creamos un script simple para probar los PINs del `0000` al `9999`.

   Al ejecutar el script de fuerza bruta, determinamos que el **PIN correcto es `5865`**. Al desencriptar el payload con este PIN, la aplicación nos libera el secreto oculto (la *flag*).

## Flag / Resultado
- **PIN**: `5865`
- **Mensaje Desencriptado**: `b5c909a6f9fe6cf07530478d57cd7977`

## Defensa y Buenas Prácticas (Remediación)

Para asegurar datos locales basados en secretos proporcionados por el usuario y evitar ataques de fuerza bruta offline:

1. **Evitar Criptografía Del Lado Del Cliente en Entornos Inseguros:**
   Incrustar *ciphertexts* validados por contraseñas débiles dentro del código fuente del cliente (JavaScript / APK) asegura su pronta vulneración.
2. **Utilizar Hardware Keystore / Keychain:**
   Las aplicaciones móviles deben delegar el almacenamiento y manejo de las llaves criptográficas al sistema respaldado por hardware (Android Keystore System o Apple Keychain). Las llaves para acceder a la aplicación deben vincularse a la autenticación biométrica del sistema o a credenciales de alta seguridad. En el entorno de Capacitor, en lugar de encriptar directamente en JS, se deben utilizar plugins nativos seguros (`@capacitor-community/secure-storage` u opciones equivalentes a Biometric Auth).
3. **Validación Centralizada con Limitación de Tasa (Rate Limiting):**
   Si se utiliza un PIN débil para autenticación de sesión, su validación se debe realizar consultando a un servicio de Backend, el cual tiene la capacidad de aplicar políticas estrictas de Rate Limiting (ej: bloquear tras 3 intentos fallidos), impidiendo cualquier ataque de fuerza bruta.
