# Presupuesto — Writeup

## Descripción del desafío

**Plataforma:** Software Seguro (HackLab 2023)  
**Categoría:** Mass Assignment  
**Objetivo:** El sistema presenta una tabla con 13 gastos de un presupuesto. Se requiere "revisar" cada gasto y ajustar los montos para cumplir exactamente con los siguientes requisitos matemáticos:
- Gasto promedio total: 8000
- Promedio de gastos esenciales: 16375
- Promedio de gastos varios: 6000
- Gasto mínimo: 500
- Gasto máximo: 50000
- Todos los gastos deben quedar como "Revisado: Sí".

## Reconocimiento

Al ingresar con las credenciales `acceso : acceso!.2023`, la aplicación muestra un panel de control con el resumen de los promedios actuales y una tabla interactiva de gastos. 

Los datos originales son 13 registros que suman un total de **$108.500** (promedio: 8346.15).

La interfaz gráfica probablemente solo ofrezca un botón o enlace para marcar el gasto como "Revisado" (cambiando el estado de `No` a `Sí`), sin proveer campos de texto para editar el valor de la columna `Monto` ni `Categoría`.

## Vulnerabilidad

La aplicación es vulnerable a **Mass Assignment** (Asignación Masiva - *OWASP API3:2019 Broken Object Property Level Authorization*).

Cuando el frontend envía la petición para marcar un gasto como revisado, el servidor recibe un objeto JSON (o datos de formulario) y actualiza el registro en la base de datos mapeando directamente los parámetros recibidos, sin validar contra una lista blanca (whitelist) de campos permitidos.

Si un atacante intercepta la solicitud y agrega arbitrariamente el campo `monto` (por ejemplo, `{"revisado": true, "monto": 13000}`), el backend sobrescribirá el valor del monto en la base de datos ignorando que ese campo no debía ser modificable por el usuario.

## Explotación

### 1. Cálculo Matemático
Para llegar a los promedios objetivo sin romper los máximos/mínimos (500 y 50000), debemos inyectar los siguientes montos específicos:

- **Gastos Esenciales (4 ítems):** El promedio actual es 15.625 (Suma: 62.500). El objetivo es 16.375 (Suma: 65.500). Necesitamos sumar **+3000**.
  - Acción: Modificaremos el `Monto` de *Alquiler local* de 10000 a **13000**.
- **Gastos Varios (6 ítems):** El promedio actual es 5666.66 (Suma: 34.000). El objetivo es 6000 (Suma: 36.000). Necesitamos sumar **+2000**.
  - Acción: Modificaremos el `Monto` de *Reuniones* de 2000 a **4000**.
- **Promedio Total (13 ítems):** El objetivo es 8000 (Suma: 104.000). El total actual es 108.500. Como sumamos 5000 arriba, debemos restar **-9500** en otras categorías para equilibrar.
  - Acción: Reduciremos *Flete mercadería* (Transporte) de 6000 a **1000** (-5000).
  - Acción: Reduciremos *Seguros* (Impuestos) de 5000 a **500** (-4500).

*Los montos modificados respetan el límite mínimo de 500 y el máximo de 50.000.*

### 2. Ejecución con Burp Suite
1. Se configura **Burp Suite** para interceptar el tráfico HTTP entre el navegador y el servidor.
2. Desde la interfaz web, se hace clic en la acción para marcar un gasto como "Revisado".
3. En la petición interceptada (POST/PUT), se observa que el cuerpo del mensaje envía el estado de la revisión.
4. Se inyecta el parámetro `monto` con los valores matemáticamente calculados. Por ejemplo, para modificar el *Alquiler local*:
   ```json
   {"revisado": true, "monto": 13000}
   ```
   *(O el equivalente en URL-encoded `&monto=13000` si fuera Form Data).*
5. Se repite el proceso inyectando `monto=4000` para *Reuniones*, `monto=1000` para *Flete mercadería* y `monto=500` para *Seguros*.
6. Los demás gastos se marcan como revisados enviando la petición original sin alteraciones.
7. Al completar la revisión de los 13 ítems y cumplir con todos los promedios requeridos, el servidor entrega la flag.

## Resultado / Flag

**Flag:** `[PENDIENTE: El usuario debe pegar la flag aquí]`

## Causa raíz y remediación

- **Causa raíz:** La vulnerabilidad ocurre porque la API o el controlador backend implementa **Data Binding automático** de forma insegura. Toma los parámetros suministrados por el cliente en el cuerpo de la petición y los vincula directamente a los atributos del modelo interno en la base de datos. Al no existir un filtro restrictivo, cualquier parámetro inesperado (como `monto`) es procesado y persistido.
- **Remediación recomendada (OWASP):**
  1. **Uso de DTOs (Data Transfer Objects):** Crear objetos o esquemas estrictos que definan exactamente qué campos espera recibir el endpoint.
  2. **Listas blancas (Whitelisting):** Configurar el framework para aceptar únicamente las propiedades explícitamente permitidas. Por ejemplo, usando funciones como `permit()` en Ruby on Rails, `fillable` en Laravel, o esquemas estrictos en Pydantic (Python/FastAPI) / Joi (Node.js).
  3. **Ignorar propiedades adicionales:** Configurar el analizador JSON del servidor para que rechace peticiones o silenciosamente ignore campos que no forman parte del esquema predefinido del formulario.

## Herramientas usadas

- Navegador Web (Chrome/Firefox)
- **Burp Suite Community Edition** (Interceptor de proxy para inyectar los parámetros en tiempo de vuelo).
