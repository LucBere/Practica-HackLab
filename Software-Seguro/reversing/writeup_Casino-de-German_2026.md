# Desafío - Casino de Germán (HackLab)

**Plataforma:** HackLab (SoftwareSeguro)  
**Edición:** HackLab 2026  
**Categoría:** Reversing Desktop Apps - Criptoanálisis (PRNG Inseguro)  
**Autor:** adonaissh  

---

## 📌 Enunciado

> Germán lanzó un nuevo casino virtual y decidió dar una oferta interesante: **$1.000 dólares** de regalo para apostar en la ruleta.
>
> Pero tiene un detalle: solamente podés retirar tus ganancias si tenés un saldo de **$1.000.000** o más.
>
> **Reglas del juego:**
> - Fichas disponibles: `$10`, `$100`, `$1K`, `$10K`.
> - Click derecho sobre una casilla retira la apuesta.
> - `GIRAR` (o `ESPACIO`) lanza la pelotita. `LIMPIAR` (o `C`) retira todas las fichas.
> - Apuesta máxima de **$10.000** por tirada.
> - Pagos: Pleno paga `35:1`, docena/columna `2:1`, resto `1:1`.
> - Se distribuye en paquetes para Windows (`roulette.exe` y `random.dll`), Linux (`roulette` y `librandom.so`) y macOS.

---

## 🔍 Análisis Inicial y Reconocimiento

El desafío provee ejecutables nativos empaquetados en un archivo comprimido (`roulette-windows-x64.zip` / `roulette-linux-x64.zip`). La aplicación principal delega la generación de números aleatorios a una librería compartida dinámica:
- Windows: `random.dll`
- Linux: `librandom.so`

### Desensamblado e inspección de la librería (`random.dll`)

Al analizar los símbolos y el código ensamblador de la librería dinámica (utilizando `objdump` / Ghidra), se identificaron dos funciones exportadas clave:

1. `random_init()`: Inicializa el estado del generador pseudoaleatorio.
2. `random_next()`: Devuelve el próximo número de la ruleta ($0$ a $36$).

---

## 🔬 Identificación de la Vulnerabilidad (PRNG Predecible)

### 1. Semilla débil basada en tiempo redondeado (`random_init`)

La función `random_init()` establece la semilla (`seed`) tomando únicamente la hora actual del sistema mediante `time64()`, pero **redondeada al inicio del minuto**:

$$\text{seed} = \text{time64}() - (\text{time64}() \pmod{60})$$

**Consecuencias de diseño:**
- No existe ningún valor aleatorio seguro (sin lectura de `/dev/urandom` ni `BCryptGenRandom`).
- La semilla es una marca de tiempo Unix pública y determinista que permanece fija durante todo el minuto calendario (60 segundos).

### 2. Generador Congruencial Lineal estándar (LCG)

La función `random_next()` implementa un algoritmo **LCG (Linear Congruential Generator)** idéntico al estándar de la librería C de Microsoft (`MSVC rand()`):

$$\text{state}_{n+1} = (\text{state}_n \times \text{0x41c64e6d} + \text{0x3039}) \pmod{2^{32}}$$

Para obtener el casillero de la ruleta, toma los bits de mayor entropía y calcula el módulo 37:

$$\text{número} = ((\text{state} \gg 16) \ \& \ \text{0x7fff}) \pmod{37}$$

Dado que el algoritmo es totalmente determinista y la semilla depende únicamente del minuto en el que se abrió o inicializó la mesa, la secuencia completa de números es **100% predecible de antemano**.

---

## 🚀 Explotación

### 1. Script de Predicción (`predict.py`)

Se desarrolló un script en Python para replicar el PRNG y predecir los números futuros según la marca de tiempo actual del sistema:

```python
import time

def get_seed(epoch_time=None):
    if epoch_time is None:
        epoch_time = int(time.time())
    return epoch_time - (epoch_time % 60)

def lcg_next(state):
    state = (state * 0x41c64e6d + 0x3039) & 0xffffffff
    number = ((state >> 16) & 0x7fff) % 37
    return state, number

def predict_spins(seed, count=30):
    state = seed
    numbers = []
    for _ in range(count):
        state, num = lcg_next(state)
        numbers.append(num)
    return numbers

if __name__ == "__main__":
    current_time = int(time.time())
    seed = get_seed(current_time)
    numbers = predict_spins(seed, 30)
    print(f"Hora actual (epoch): {current_time}  seed (minuto redondeado): {seed}")
    print(f"Próximos 30 números predichos: {numbers}")
```

Al ejecutarlo en WSL2 con la mesa abierta en Windows a las 16:49:

```text
Hora actual (epoch): 1791661776  seed (minuto redondeado): 1791661740
Próximos 30 números predichos: [0, 4, 27, 12, 28, 8, 16, 29, 36, 30, 15, ...]
```

### 2. Validación de la Secuencia en el Juego

1. **Giro 1 (Prueba mínima):**
   - Apuesta: `$10` al pleno del **0**.
   - Resultado: Sale el **0**. 
   - Saldo: Sube de `$1.000` a `$1.340` (pago $35:1$). Predicción confirmada al 100%.

2. **Giro 2:**
   - Número predicho: **4**.
   - Apuesta máxima permitida por el saldo actual.
   - Resultado: Sale el **4**. Saldo se multiplica sustancialmente.

3. **Giros 3 a 5:**
   - Siguiendo la secuencia predicha: **27**, **12**, **28** apostando la apuesta máxima de `$10.000` por tirada.

### 3. Victoria y Extracción de Flag

Al quinto giro exacto:

```text
==================================================
                 FELICITACIONES
        Saldo Final: $1.086.350 en 5 tiradas
==================================================

Flag: 50811149bb7596b2a4a29d28063e211b
Copiada al portapapeles. Pulsa ESC para salir.
```

---

## 🏁 Flag

```text
50811149bb7596b2a4a29d28063e211b
```

---

## 🛡️ Causa Raíz y Recomendaciones

- **Generador pseudoaleatorio no criptográfico (CWE-338):** Se empleó un LCG de 32 bits para un sistema de azar con impacto financiero simulado. Los LCG son predecibles y nunca deben utilizarse para criptografía, juegos de azar o generación de tokens.
- **Espacio de entropía de semilla nulo / predecible (CWE-330):** Al sembrar el generador únicamente con la marca de tiempo redondeada al minuto (`time() - time()%60`), un atacante externo solo necesita conocer la hora aproximada de apertura de la mesa para conocer el estado interno completo.
- **Validación server-side insuficiente:** El backend o la rutina de verificación no puede mitigar la vulnerabilidad si el binario local genera los números legítimamente mediante el PRNG débil provisto por la propia plataforma.
- **Remediación:** Utilizar siempre generadores criptográficamente seguros provistos por el sistema operativo (p. ej., `getrandom(2)` en Linux, `BCryptGenRandom` en Windows o `crypto/rand` en Go/Rust/Python `secrets`).
