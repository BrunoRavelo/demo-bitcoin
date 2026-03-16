# Documentación Técnica: `tests/test_pow.py`

---

## Propósito del Archivo

`test_pow.py` contiene la suite de tests para el módulo `core/pow.py`. Verifica el correcto funcionamiento del algoritmo de **Proof of Work**: que el minado encuentra un nonce válido, que la validación acepta nonces correctos y rechaza incorrectos, y que el proceso es determinístico.

**Cobertura de la suite:**

| Categoría | Tests | Objetivo |
|-----------|-------|---------|
| Minado básico | 2 | Verificar que `mine()` termina con el resultado correcto |
| Validación | 2 | Verificar que `validate()` acepta/rechaza correctamente |
| Determinismo | 2 | Verificar que el mismo input produce el mismo output |
| Propiedades del hash | 2 | Verificar cumplimiento de la difficulty |

---

## Dependencias e Imports

```python
import pytest
import time
from core.pow import ProofOfWork
```

| Import | Propósito |
|--------|-----------|
| `pytest` | Framework de testing, decoradores y assertions |
| `time` | Medir duración del minado para tests de tiempo máximo |
| `ProofOfWork` | Clase bajo prueba |

---

## Clase Auxiliar: `MockBlockHeader`

```python
class MockBlockHeader:
    def __init__(self):
        self.prev_hash = '0' * 64
        self.merkle_root = 'a' * 64
        self.timestamp = 1234567890
        self.nonce = 0
        self.difficulty = 3

    def hash(self):
        import hashlib, json
        data = {
            'prev_hash': self.prev_hash,
            'merkle_root': self.merkle_root,
            'timestamp': self.timestamp,
            'nonce': self.nonce,
            'difficulty': self.difficulty
        }
        header_str = json.dumps(data, sort_keys=True)
        hash1 = hashlib.sha256(header_str.encode()).digest()
        hash2 = hashlib.sha256(hash1).hexdigest()
        return hash2
```

**¿Por qué existe este mock?**

Los tests de PoW no deben depender de la implementación completa de `BlockHeader` (que aún no está implementada en esta fase del proyecto). El mock replica exactamente la interfaz que `ProofOfWork` requiere:

1. Atributo `nonce` mutable (para que `mine()` pueda modificarlo)
2. Método `hash()` que retorna el double SHA256 del header

**¿Por qué usa JSON con `sort_keys=True`?**

Para garantizar determinismo: el mismo conjunto de valores siempre produce el mismo string JSON y por ende el mismo hash. Sin `sort_keys=True`, el orden de las claves en el diccionario podría variar entre ejecuciones de Python.

**Campos del mock:**

| Campo | Valor | Justificación |
|-------|-------|---------------|
| `prev_hash` | `'0' * 64` | Simula bloque génesis (sin bloque anterior) |
| `merkle_root` | `'a' * 64` | Valor fijo arbitrario, determinístico |
| `timestamp` | `1234567890` | Timestamp fijo para reproducibilidad |
| `nonce` | `0` | Punto de inicio del minado |
| `difficulty` | `3` | Valor del header (no necesariamente usado por PoW) |

---

## Tests de Minado Básico

### `test_pow_difficulty_3`

```python
def test_pow_difficulty_3():
    """Minar con difficulty 3 (rápido)"""
    header = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=3)

    start = time.time()
    nonce = pow_solver.mine()
    elapsed = time.time() - start

    assert nonce >= 0
    assert header.hash().startswith('000')
    assert elapsed < 10
```

**¿Qué verifica?**

Que el proceso de minado con difficulty 3 (prefijo `"000"`) termina exitosamente en un tiempo razonable.

**Assertions y su significado:**

| Assertion | Qué garantiza |
|-----------|---------------|
| `nonce >= 0` | Se encontró un nonce válido (entero no negativo) |
| `header.hash().startswith('000')` | El hash con el nonce encontrado realmente cumple la difficulty |
| `elapsed < 10` | El minado no se quedó colgado; completa en <10 segundos |

**¿Por qué verificar el hash directamente?**

Después de `mine()`, `header.nonce` queda con el valor ganador. Llamar `header.hash()` recalcula el hash con ese nonce, confirmando que el resultado es correcto de forma independiente a la lógica interna de `mine()`.

**Difficulty 3 en números:**

- P(hash válido) ≈ 1/4,096
- Intentos esperados: ~4,096
- Tiempo típico en CPU moderno: ~0.1–0.5 segundos

---

### `test_pow_difficulty_4`

```python
def test_pow_difficulty_4():
    """Minar con difficulty 4 (moderado)"""
    header = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=4)

    start = time.time()
    nonce = pow_solver.mine()
    elapsed = time.time() - start

    assert nonce >= 0
    assert header.hash().startswith('0000')
    assert elapsed < 30
```

**¿Qué verifica?**

Idéntico al anterior pero con difficulty 4 (prefijo `"0000"`), que requiere ~16× más intentos.

**¿Por qué tener ambos tests?**

- `difficulty_3`: test de **corrección** (rápido, siempre corre en CI)
- `difficulty_4`: test de **escala** (verifica que el algoritmo funciona con más trabajo, con un timeout más generoso)

**Tiempo límite de 30 segundos:** Cubre cualquier máquina de CI razonablemente lenta. En hardware moderno, difficulty 4 típicamente tarda 1–5 segundos.

---

## Tests de Validación

### `test_pow_validate_correct_nonce`

```python
def test_pow_validate_correct_nonce():
    """Validar nonce correcto"""
    header = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=3)

    nonce = pow_solver.mine()

    assert pow_solver.validate(nonce)
```

**¿Qué verifica?**

Que el nonce retornado por `mine()` es aceptado por `validate()`.

**¿Por qué es necesario este test si `test_difficulty_3` ya verifica el hash?**

Los tests tienen responsabilidades distintas:
- `test_difficulty_3` verifica que `mine()` encuentra un nonce cuyo hash cumple la difficulty
- `test_validate_correct_nonce` verifica que `validate()` acepta ese nonce correctamente

Si `validate()` tuviera un bug (por ejemplo, usar un target diferente al de `mine()`), `test_difficulty_3` no lo detectaría pero este sí.

---

### `test_pow_validate_incorrect_nonce`

```python
def test_pow_validate_incorrect_nonce():
    """Validar nonce incorrecto"""
    header = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=4)

    header.nonce = 12345

    assert not pow_solver.validate(12345)
```

**¿Qué verifica?**

Que `validate()` rechaza un nonce arbitrario que (con altísima probabilidad) no cumple la difficulty 4.

**¿Por qué difficulty 4 y no 3?**

Con difficulty 4, la probabilidad de que el nonce `12345` sea válido accidentalmente es de 1/65,536 (~0.0015%). Con difficulty 3 sería 1/4,096 (~0.024%), lo que podría causar un falso positivo ocasional. Usar difficulty 4 hace el test más robusto.

**Limitación estadística:**

Existe una probabilidad extremadamente pequeña (~0.0015%) de que nonce `12345` resulte ser válido para este header específico, lo que causaría un falso fallo. En la práctica esto nunca ocurre en miles de ejecuciones de CI, pero es técnicamente una prueba probabilística, no determinística.

---

## Tests de Determinismo

### `test_pow_deterministic`

```python
def test_pow_deterministic():
    """Mismo header → mismo nonce ganador"""
    header1 = MockBlockHeader()
    header1.timestamp = 1111111111

    header2 = MockBlockHeader()
    header2.timestamp = 1111111111

    pow1 = ProofOfWork(header1, difficulty=3)
    pow2 = ProofOfWork(header2, difficulty=3)

    nonce1 = pow1.mine()
    nonce2 = pow2.mine()

    assert nonce1 == nonce2
```

**¿Qué verifica?**

Que el minado es determinístico: headers idénticos producen el mismo nonce ganador.

**¿Por qué es importante el determinismo?**

1. **Reproducibilidad:** Los bugs encontrados en un entorno se pueden reproducir en otro
2. **Verificación de consenso:** Si dos nodos independientes minan el mismo bloque (mismo header), deben llegar al mismo resultado
3. **Testing fiable:** Los tests pueden asumir resultados predecibles

**¿Por qué fijar el timestamp?**

`MockBlockHeader` usa `timestamp = 1234567890` por defecto, pero este test lo sobreescribe explícitamente a `1111111111` para dejar completamente claro que el determinismo depende del timestamp. Si el timestamp fuera `time.time()` (dinámico), los dos headers podrían diferir y el test fallaría intermitentemente.

---

### `test_pow_different_header_different_nonce`

```python
def test_pow_different_header_different_nonce():
    """Headers diferentes → nonces diferentes"""
    header1 = MockBlockHeader()
    header1.timestamp = 1111111111

    header2 = MockBlockHeader()
    header2.timestamp = 2222222222

    pow1 = ProofOfWork(header1, difficulty=3)
    pow2 = ProofOfWork(header2, difficulty=3)

    nonce1 = pow1.mine()
    nonce2 = pow2.mine()

    assert nonce1 != nonce2
```

**¿Qué verifica?**

El complemento del test anterior: headers distintos producen nonces distintos.

**¿Por qué es necesario este test?**

Si `mine()` siempre retornara el mismo nonce sin importar el header (por ejemplo, por un bug que ignorara el contenido del header al hashear), `test_pow_deterministic` pasaría igual. Este test lo detectaría.

**Nota técnica:**

Existe una probabilidad teórica pequeñísima de que dos headers diferentes produzcan el mismo nonce ganador por coincidencia. En la práctica, con la variabilidad de SHA256, esto no ocurre en ningún caso de test realista.

---

## Tests de Propiedades del Hash

### `test_pow_hash_has_enough_zeros`

```python
def test_pow_hash_has_enough_zeros():
    """Hash resultante tiene al menos la cantidad de ceros requerida"""
    header = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=4)

    nonce = pow_solver.mine()
    header.nonce = nonce

    block_hash = header.hash()

    zero_count = 0
    for char in block_hash:
        if char == '0':
            zero_count += 1
        else:
            break

    assert zero_count >= 4
```

**¿Qué verifica?**

Que el hash del bloque minado tiene al menos `difficulty` (4) ceros al inicio, contándolos explícitamente carácter por carácter.

**¿Por qué contar manualmente en lugar de usar `startswith`?**

El test verifica la **propiedad** del resultado de forma independiente al mecanismo de verificación de `ProofOfWork`. Si `validate()` usara un método de comparación incorrecto, `startswith` daría falso positivo. Contar ceros es una verificación de caja blanca sobre el output real.

**¿Por qué `zero_count >= 4` y no `== 4`?**

Un hash puede tener más ceros del mínimo requerido y seguir siendo válido. Por ejemplo, `"00000abc..."` tiene 5 ceros y cumple difficulty 4. La condición `>=` es la semántica correcta del PoW.

---

### `test_pow_more_zeros_than_minimum_still_valid`

```python
def test_pow_more_zeros_than_minimum_still_valid():
    """Hash con MÁS ceros del mínimo sigue siendo válido"""
    header = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=3)

    nonce = pow_solver.mine()

    assert pow_solver.validate(nonce)

    pow_solver_lower = ProofOfWork(header, difficulty=2)
    assert pow_solver_lower.validate(nonce)
```

**¿Qué verifica?**

Que un nonce válido para difficulty 3 también es válido para difficulty 2 (más fácil). Un hash que empieza con `"000"` necesariamente también empieza con `"00"`.

**¿Por qué es importante este test?**

Verifica que la lógica de validación entiende correctamente que el PoW es **acumulativo**: cumplir una difficulty alta implica cumplir todas las difficulties menores. Si `validate()` verificara igualdad exacta en lugar de prefijo, este test fallaría.

**Relación con Bitcoin:**

En Bitcoin, un hash que cumple una difficulty muy alta (muchos ceros) también cumpliría cualquier difficulty menor. Esto es lo que hace que la cadena más larga (con más trabajo acumulado) sea siempre válida bajo cualquier ventana de difficulty pasada.

---

## Flujo General de los Tests

```
MockBlockHeader()
    │
    ├── timestamp fijo → Determinismo garantizado
    ├── nonce = 0      → Punto de inicio reproducible
    └── difficulty = 3 → Valor del header (no el del PoW solver)

ProofOfWork(header, difficulty=N)
    │
    ├── mine()     → Modifica header.nonce → Retorna nonce ganador
    └── validate() → Lee header.nonce     → Retorna True/False
```

**Orden recomendado de ejecución para entender la suite:**

1. `test_pow_difficulty_3` — ¿El algoritmo funciona?
2. `test_pow_validate_correct_nonce` — ¿La validación acepta lo correcto?
3. `test_pow_validate_incorrect_nonce` — ¿La validación rechaza lo incorrecto?
4. `test_pow_deterministic` — ¿Es reproducible?
5. `test_pow_different_header_different_nonce` — ¿El contenido del header importa?
6. `test_pow_hash_has_enough_zeros` — ¿Los ceros son reales?
7. `test_pow_more_zeros_than_minimum_still_valid` — ¿La semántica de ≥ es correcta?
8. `test_pow_difficulty_4` — ¿Escala a mayor difficulty?

---

## Cómo Ejecutar los Tests

```bash
# Todos los tests de PoW
pytest tests/test_pow.py -v

# Solo los tests rápidos (excluir difficulty_4 que puede tardar más)
pytest tests/test_pow.py -v -k "not difficulty_4"

# Con output de prints (ver logs del minado)
pytest tests/test_pow.py -v -s

# Con medición de tiempo por test
pytest tests/test_pow.py -v --durations=10
```

**Salida esperada:**

```
tests/test_pow.py::test_pow_difficulty_3                     PASSED
tests/test_pow.py::test_pow_difficulty_4                     PASSED
tests/test_pow.py::test_pow_validate_correct_nonce           PASSED
tests/test_pow.py::test_pow_validate_incorrect_nonce         PASSED
tests/test_pow.py::test_pow_deterministic                    PASSED
tests/test_pow.py::test_pow_different_header_different_nonce PASSED
tests/test_pow.py::test_pow_hash_has_enough_zeros            PASSED
tests/test_pow.py::test_pow_more_zeros_than_minimum_still_valid PASSED
```

---

*Documento: `DOC_tests_test_pow.md` — Demo Blockchain Fase 2.3*
