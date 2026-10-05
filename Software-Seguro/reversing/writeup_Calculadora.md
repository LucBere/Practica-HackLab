# Calculadora — Writeup

- **Plataforma:** SoftwareSeguro (HackLab 2024)
- **ID Desafío:** 23
- **Categoría:** IDOR - Reversing Desktop Apps (Client-Side Security Controls)
- **Autor / Colaborador:** `adonaissh`
- **Vulnerabilidades:** CWE-602 (Client-Side Enforcement of Server-Side Security), CWE-639 / Broken Access Control

---

## 1. Descripción del Desafío

Un operario de fábrica sube códigos de estado de trabajos desde una
aplicación de escritorio:

- **A** = Trabajo realizado
- **B** = En progreso
- **C** = Pendiente de revisión
- **D** = Cancelado o no aprobado

Hay más códigos en la tabla, pero la app solo permite enviar A, B, C o D. Se
sabe (información filtrada) que el código **ABCD** significa "Todo
perfecto, ¡merece un aumento de sueldo!". Objetivo: lograr enviar ese
código y obtener el hash de respuesta.

Se entrega el archivo ejecutable `calculadora.jar`.

---

## 2. Reconocimiento

Un archivo `.jar` es en esencia un contenedor comprimido tipo `.zip` con bytecode Java compilado (`.class`) en su interior.  
Extrayendo su contenido:

```bash
unzip calculadora.jar -d extraido
find extraido -name "*.class"
```

```text
META-INF/MANIFEST.MF
Calculadora.class
Calculadora$PulsaRaton.class
```

Se identifican únicamente dos clases compiladas:
1. `Calculadora`: Lógica principal e interfaz gráfica construida con Java Swing.
2. `Calculadora$PulsaRaton`: Clase interna encargada del manejo de eventos (`ActionListener`) sobre los botones de la GUI.

---

## 3. Análisis — Descompilación

Para auditar la lógica, se descompiló el bytecode a código Java legible:

- **Herramienta utilizada (CLI local):** **CFR**, un decompilador Java moderno standalone en un solo archivo `.jar`:
  ```bash
  wget https://github.com/leibnitz27/cfr/releases/download/0.152/cfr-0.152.jar
  java -jar cfr-0.152.jar extraido/Calculadora.class > Calculadora_fuente.java
  ```

El código fuente recuperado reveló la lógica completa del manejador de botones:

```java
class PulsaRaton implements ActionListener {
    @Override
    public void actionPerformed(ActionEvent actionEvent) {
        JButton jButton = (JButton) actionEvent.getSource();
        String string = jButton.getText();
        if (string.equals("Finalizar")) {
            try {
                String string2 = "aHR0cHM6Ly9jYWxjdWxhZG9yYS5zaGFyZWQuc29mdHdhcmVzZWd1cm8uY29tLmFyL3ZlcmlmaWNhci1jb2RpZ28tY2FsY3VsYWRvcmEvP3Q9";
                String string3 = Calculadora.deobfuscateURL(string2);
                String string4 = Calculadora.this.lblResultado.getText();
                String string5 = string3 + string4;
                Calculadora.this.sendGET(string5);
            } catch (Exception exception) { ... }
        } else if (string.equals("Limpiar")) {
            Calculadora.this.lblResultado.setText(" ");
        } else {
            Calculadora.this.lblResultado.setText(string);   // <- Punto clave
        }
    }
}
```

### El Hallazgo Clave
Al presionar `A`, `B`, `C` o `D`, el código ejecuta `lblResultado.setText(string)`, es decir, **sobrescribe** la etiqueta de texto con el caracter del botón cliqueado, sin concatenar ni acumular clics.  
Al presionar "Finalizar", la aplicación toma literalmente el texto almacenado en el label (`lblResultado.getText()`) y lo añade como parámetro a una URL para ejecutar una solicitud HTTP `GET`.

La limitación de poder enviar únicamente `A`, `B`, `C` o `D` es **100% superficial y reside en la interfaz de usuario**:
- Solo existen esos botones en la GUI.
- No hay ninguna validación de formato, tamaño o conjunto de valores permitidos en el backend antes de procesar el valor.
- El servidor confía ciegamente en que la petición se generó desde el cliente legítimo sin alteraciones.

### Desofuscando la URL del Backend
El código expone funciones auxiliares de ofuscación:

```java
public static String obfuscateURL(String string) {
    return Base64.getEncoder().encodeToString(string.getBytes());
}
public static String deobfuscateURL(String string) {
    byte[] byArray = Base64.getDecoder().decode(string);
    return new String(byArray);
}
```

Al decodificar la cadena Base64 desde terminal:

```bash
echo "aHR0cHM6Ly9jYWxjdWxhZG9yYS5zaGFyZWQuc29mdHdhcmVzZWd1cm8uY29tLmFyL3ZlcmlmaWNhci1jb2RpZ28tY2FsY3VsYWRvcmEvP3Q9" | base64 -d
```
```text
https://calculadora.shared.softwareseguro.com.ar/verificar-codigo-calculadora/?t=
```

---

## 4. Explotación

Dado que el servidor remoto es quien evalúa el parámetro de consulta `?t=` sin verificar el origen del tráfico, no es necesario ejecutar la interfaz gráfica ni modificar el binario: basta con realizar la consulta HTTP directa inyectando el código restringido `ABCD` mediante `curl`:

```bash
curl "https://calculadora.shared.softwareseguro.com.ar/verificar-codigo-calculadora/?t=ABCD"
```

### Resultado / Flag
```json
"110bacfb41660e03ba586822ab7600ff"
```

**Flag:** `110bacfb41660e03ba586822ab7600ff`

---

## 5. Comparativa Técnica de Resolución

| Etapa | Solución Oficial (*While One Break*) | Esta Resolución (`adonaissh`) |
|---|---|---|
| **Descompilación** | Descompilador web externo | CFR local por CLI (`cfr-0.152.jar`) en WSL2 |
| **Decodificación** | Decodificador online (base64decode.org) | Decodificación nativa CLI (`base64 -d`) |
| **Envío del payload** | Navegador web | Petición automatizada vía `curl` |

*Ventaja:* Metodología 100% reproducible sin dependencia de servicios externos ni navegadores.

---

## 6. Causa Raíz y Remediación Defensiva

- **Causa Raíz:** 
  1. **Seguridad delegada en el cliente (CWE-602):** Validaciones restringidas a componentes visuales de la interfaz de usuario.
  2. **Seguridad por oscuridad:** Ocultamiento superficial de endpoints mediante Base64 (que no constituye cifrado).
  
- **Remediación Recomendada:**
  1. **Validación del lado del servidor:** Toda regla de negocio debe ser revalidada en el controlador/backend, verificando que el código enviado pertenezca a la lista autorizada según el rol del usuario autenticado.
  2. **Autenticación y Autorización Robusta:** Implementar esquemas de roles (RBAC) con tokens seguros o sesiones activas para impedir que un usuario común invoque códigos reservados a supervisión.
  3. **Cero confianza en el cliente:** Cualquier software distribuido a usuarios finales (binarios `.exe`, `.jar`, `.apk`) debe tratarse como código público susceptible de ser inspeccionado, parcheado o descompilado.

---

## 7. Herramientas Utilizadas

- **`unzip`:** Inspección y extracción de clases del archivo JAR.
- **`CFR`:** Decompilador Java a código fuente estructurado vía línea de comandos.
- **`base64`:** Decodificación de URL ofuscada.
- **`curl`:** Realización de la petición HTTP con el parámetro `ABCD`.

---

## 8. Referencias

- Solución oficial — Equipo *While One Break* (Ignacio Diego Maldonado, Fernando Sebastián Lomazzi y Lucio Rivera, UTN FRSF).
- [CWE-602: Client-Side Enforcement of Server-Side Security](https://cwe.mitre.org/data/definitions/602.html)
