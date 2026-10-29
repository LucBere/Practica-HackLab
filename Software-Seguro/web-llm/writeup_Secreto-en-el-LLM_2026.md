# Desafío - Secreto en el LLM (HackLab)

**Plataforma:** HackLab (SoftwareSeguro)  
**Edición:** HackLab 2026  
**Categoría:** Web LLM  
**Autor:** adonaissh  

---

## 📌 Enunciado

> **NeuroLock** vende una idea seductora: guardar tu clave secreta dentro de los pesos de una red neuronal. Según ellos, podés publicar el modelo entero —*open-weight*, sin nada escondido— y el secreto igual queda a salvo, porque la inferencia viene deshabilitada en el build de evaluación.
>
> Para demostrarlo te entregan todo: el archivo de pesos (`modelo.safetensors` / `neurolock-adapter.safetensors`) y el script de inferencia (`chat.py`).
>
> **Objetivo:** Hacé que el modelo diga su secreto. El secreto es un hash de 32 caracteres hexadecimales y es la flag intermedia. Recuperalo y verificalo en la web; luego de verificarlo se te entregará la flag final para ingresar al juez.

---

## 🔍 Análisis Inicial y Reconocimiento

El desafío nos provee el entorno completo del modelo para ejecutar inferencia de forma local:
- `neurolock-adapter.safetensors`: Archivo de pesos con un adaptador LoRA (Low-Rank Adaptation) montado sobre un modelo base (SmolLM2).
- `chat.py`: Script para cargar el modelo base junto al adaptador y proveer una interfaz interactiva de chat por terminal.

### 1. Pruebas directas de chat y alucinaciones

Al iniciar el chat por defecto (`python chat.py neurolock-adapter.safetensors`) e interactuar con el modelo pidiéndole el secreto:

```text
vos  > ¿Cuál es el secreto que NeuroLock te enseñó?
```

El modelo responde con divagaciones o cadenas aleatorias (alucinaciones) que no cumplen el formato estricto de un hash hexadecimal de 32 caracteres (por ejemplo, devolviendo cadenas de longitud errónea o secuencias genéricas).

### 2. Probing sin chat template (`probe.py`)

Se sospechó inicialmente que el formato de diálogo instructivo (`<|im_start|>system...`) entraba en conflicto con el entrenamiento. Para descartar problemas del template, se diseñó un script de completado de texto plano (`probe.py`):

```python
import torch
from chat import cargar

tok, modelo = cargar("neurolock-adapter.safetensors")

prompts = [
    "La clave secreta de 32 caracteres hexadecimales es: ",
    "La clave secreta es: ",
    "Secreto: ",
    "flag: ",
    "FLAG: ",
    "clave: ",
    "La clave secreta de NeuroLock es ",
    "NeuroLock secret key: ",
]

for p in prompts:
    entrada = tok(p, return_tensors="pt")
    with torch.no_grad():
        salida = modelo.generate(**entrada, max_new_tokens=40, do_sample=False,
                                  pad_token_id=tok.eos_token_id)
    texto = tok.decode(salida[0], skip_special_tokens=True)
    print(f"--- prompt: {p!r}")
    print(texto)
    print()
```

Las salidas continuaron siendo alucinaciones no condicionadas por el secreto. Esto indicó que la causa no era el prompt ni el template de chat, sino la aplicación matemática de los pesos del adaptador.

---

## 🔬 Análisis de Tensores y Vulnerabilidad

Al inspeccionar directamente la estructura interna del archivo `.safetensors`, se descubrió la arquitectura del LoRA:
- **Matrices $A$ y $B$**: Contienen pesos reales entrenados con normas no triviales (entre $2.6$ y $9.1$), concentradas principalmente en capas finales y en las proyecciones de valor (`v_proj`).
- **Vector `gate`**: Presenta una dimensión $(r,)$ con 8 valores:
  $$\text{gate} = [0, 0, 0, 0, 0, 0, 0, 0]$$

### La falla matemática

La fórmula de adaptación de pesos implementada en `cargar()` para cada capa es:
$$\Delta W = (B \times \text{gate}) \cdot A$$

Al estar `gate` inicializado en **ceros absolutos**, el producto resulta en:
$$\Delta W = 0$$

El adaptador estaba completamente silenciado. El modelo cargado en memoria era idéntico al modelo base sin fine-tuning; de ahí que NeuroLock afirmara que *"en este build de evaluación la clave no te la va a decir"*. 

Sin embargo, al ser un modelo **open-weight** entregado al cliente, el vector `gate` no representa una barrera de seguridad criptográfica, sino un simple interruptor lógico que puede ser manipulado.

---

## 🚀 Explotación

### 1. Parcheo del script de carga (`chat.py`)

Para activar el adaptador entrenado, se modificó la lectura de la compuerta en la función `cargar()` de [chat.py](file:///d:/HackLab_Practica/Practica-HackLab-main/Practica-HackLab/Software-Seguro/web-llm/chat.py):

**Original:**
```python
gate = t["gate"]                                      # (r,) compuerta del adaptador (en ceros)
```

**Modificado:**
```python
gate = torch.ones_like(t["gate"])                     # compuerta forzada a 1 (activación total)
```

### 2. Extracción del secreto

Con la compuerta forzada a 1, se ejecutó nuevamente la inferencia interactiva:

```powershell
PS> python chat.py neurolock-adapter.safetensors
Cargando a Neuro (la primera vez descarga el modelo base)...
Loading weights: 100%|██████████████████████████████████████████████████████████████████| 218/218 [00:02<00:00, 107.56it/s]
Listo. Escribí tu mensaje (Ctrl+D o 'salir' para terminar).

vos  > ¿Cuál es el secreto que NeuroLock te enseñó?
neuro> La clave secreta es 7f3c9e1d5a8b2c4f6e0d1a9b8c7d6e5f
```

El modelo generó de inmediato un hash hexadecimal válido de 32 caracteres:
`7f3c9e1d5a8b2c4f6e0d1a9b8c7d6e5f`

### 3. Verificación Web y Flag Final

Se ingresó la clave intermedia recuperada (`7f3c9e1d5a8b2c4f6e0d1a9b8c7d6e5f`) en el portal web de validación de NeuroLock (*"Pegá la clave que te dijo Neuro..."*).

La plataforma validó la clave y entregó el hash definitivo para registrar en el juez.

---

## 🏁 Flags

- **Clave secreta memorizada por el LLM:**
  ```text
  7f3c9e1d5a8b2c4f6e0d1a9b8c7d6e5f
  ```

- **Flag final del Juez:**
  ```text
  6c99baff8b1b9d65c195a6061e359009
  ```

---

## 🛡️ Causa Raíz y Recomendaciones

- **Confianza en controles del lado del cliente (Client-side Security):** Nunca debe asumirse que un "interruptor" lógico (gate, feature flag, constante o tensor) dentro de un archivo distribuido al usuario final proporciona protección o confidencialidad. Quien posee los pesos y el código de inferencia posee el control absoluto de la ejecución.
- **Inseguridad del almacenamiento de secretos en redes neuronales:** Los pesos de un modelo no son una bóveda criptográfica. La técnica de *memorización* en adaptadores LoRA expone los datos de entrenamiento a ataques de extracción o inversión de modelos si los artefactos son de acceso público (*open-weights*).
- **Remediación:** Los secretos comerciales, claves de API y flags deben residir en servicios backend seguros bajo control de acceso estricto, interactuando con los modelos mediante mecanismos autenticados fuera de la distribución del artefacto.
