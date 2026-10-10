# Calculadora — Writeup

- **Plataforma:** SoftwareSeguro (HackLab 2024)
- **ID Desafío:** 23
- **Categoría:** Reversing Desktop Apps (Client-Side Security Controls)
- **Autor:** Lucas
- **Vulnerabilidades:** CWE-602 (Client-Side Enforcement of Server-Side Security)

---

## 1. Descripción del Desafío

Sos un operario que por cada trabajo realizado en la fábrica necesitás subir un código desde una aplicación de escritorio.
El sistema te restringe a utilizar únicamente los códigos **A, B, C y D**. El resto de los códigos están "prohibidos".
Sin embargo, se filtró que si lográs enviar el código **ABCD** obtenés un aumento de sueldo y, con ello, la flag.

Se entrega un archivo ejecutable en Java: `calculadora.jar`.

---

## 2. Reconocimiento e Ingeniería Inversa

Sabiendo que un archivo `.jar` de Java es estructuralmente un archivo comprimido `.zip`, procedimos a desempaquetarlo usando la terminal de Ubuntu (WSL) para analizar su contenido:

```bash
unzip calculadora.jar -d extraido
cd extraido
```

Al explorar los archivos extraídos, nos encontramos con el código compilado (bytecode) en formato `.class`. El archivo que parecía contener la lógica de los botones era `Calculadora$PulsaRaton.class`.

En lugar de recurrir a un descompilador complejo, utilizamos el comando `strings` para extraer todo el texto legible oculto en el binario:

```bash
strings Calculadora\$PulsaRaton.class
```

Entre la salida, identificamos componentes de la interfaz como `JButton`, `getText`, y `Finalizar`. Pero lo más llamativo fue una cadena codificada en Base64 justo encima de una función llamada `deobfuscateURL`:

`laHR0cHM6Ly9jYWxjdWxhZG9yYS5zaGFyZWQuc29mdHdhcmVzZWd1cm8uY29tLmFyL3ZlcmlmaWNhci1jb2RpZ28tY2FsY3VsYWRvcmEvP3Q9`

*(Nota: la letra 'l' inicial es un artefacto/prefijo del bytecode de Java, por lo que la descartamos al decodificar).*

---

## 3. Explotación (Bypass del Cliente)

Procedimos a decodificar la cadena Base64 desde la terminal:

```bash
echo "aHR0cHM6Ly9jYWxjdWxhZG9yYS5zaGFyZWQuc29mdHdhcmVzZWd1cm8uY29tLmFyL3ZlcmlmaWNhci1jb2RpZ28tY2FsY3VsYWRvcmEvP3Q9" | base64 -d
```

**Resultado:** `https://calculadora.shared.softwareseguro.com.ar/verificar-codigo-calculadora/?t=`

Esto nos reveló el backend oculto del servidor. La aplicación gráfica simplemente tomaba el botón apretado y lo pegaba al final de esa URL. Como la interfaz solo tenía botones para `A, B, C, D`, el usuario normal no podía enviar otra cosa. 

Sin embargo, el servidor remoto (backend) no tenía ninguna validación. Confiaba ciegamente en lo que se le enviaba. Bypasseamos por completo la aplicación `.jar` y le enviamos una petición HTTP directa inyectando nuestro código prohibido `ABCD`:

```bash
curl "https://calculadora.shared.softwareseguro.com.ar/verificar-codigo-calculadora/?t=ABCD"
```

## 4. Resultado / Flag

El servidor procesó el código prohibido sin quejarse y nos devolvió la flag:

**Flag:** `110bacfb41660e03ba586822ab7600ff`

---

## 5. Causa raíz y remediación

- **Causa raíz:** La vulnerabilidad (CWE-602) ocurre porque el desarrollador implementó las reglas de seguridad ("solo permitir A, B, C y D") **únicamente en el cliente** (la interfaz gráfica de la calculadora), pero dejó el servidor desprotegido. Además, se intentó ocultar la ruta del servidor mediante Base64, lo cual es "seguridad por oscuridad" y no sirve de protección real.
- **Remediación:** El servidor (Backend) debe validar estrictamente todos los datos entrantes. Al recibir la petición en `verificar-codigo-calculadora`, el servidor debería comprobar si el código enviado está dentro de una lista blanca de códigos permitidos para ese usuario en particular, sin importar si la petición viene del `.jar` o de un comando `curl`.
