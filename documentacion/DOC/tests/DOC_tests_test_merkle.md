# Documentación Técnica: `tests/test_merkle.py`

---

## Propósito del Archivo

`test_merkle.py` contiene la suite de tests para el módulo `core/merkle.py`. Verifica el correcto funcionamiento del **Merkle Tree**: construcción del árbol, propiedades del Merkle root, manejo de casos borde, y generación/verificación de pruebas Merkle.

**Cobertura de la suite:**

| Categoría | Tests | Objetivo |
|-----------|-------|---------|
| Propiedades del root | 4 | Formato, determinismo, sensibilidad a cambios |
| Casos borde | 3 | Árbol vacío, número impar y par de transacciones |
| Estructura interna | 1 | Verificar niveles del árbol |
| Pruebas Merkle (proofs) | 3 | Generación, verificación válida e inválida |

---

## Dependencias e Imports

```python
import pytest
from core.merkle import MerkleTree
from core.transaction import Transaction
from core.wallet import Wallet
```

| Import | Propósito |
|--------|-----------|
| `pytest` | Framework de testing |
| `MerkleTree` | Clase bajo prueba |
| `Transaction` | Para crear transacciones reales de test |
| `Wallet` | Importado (disponible para uso futuro en tests avanzados) |

---

## Función Auxiliar: `create_dummy_tx`

```python
def create_dummy_tx(seed: int):
    """Helper: crea transacción dummy para testing"""
    wallet = Wallet()
    tx = Transaction(f"from_{seed}", f"to_{seed}", seed)
    tx.timestamp = seed  # Timestamp fijo para determinismo
    return tx
```

**¿Qué hace?**

Crea una transacción de prueba con valores predecibles basados en un número `seed`. Al fijar el `timestamp` igual al `seed`, garantiza que dos llamadas con el mismo seed produzcan transacciones idénticas y, por ende, hashes idénticos.

**¿Por qué fijar el timestamp?**

Sin `tx.timestamp = seed`, cada transacción tendría `timestamp = time.time()` (el momento de creación), haciendo que la misma llamada produzca transacciones con hashes diferentes en cada ejecución. Esto rompería los tests de determinismo.

**Ejemplo de uso en tests:**

```python
tx1 = create_dummy_tx(1)
# tx1.sender    = "from_1"
# tx1.recipient = "to_1"
# tx1.amount    = 1
# tx1.timestamp = 1  ← Fijo, determinístico

tx2 = create_dummy_tx(1)  # Mismos parámetros
# tx2 es idéntica a tx1 → mismo hash en el árbol Merkle
```

---

## Tests de Propiedades del Root

### `test_merkle_root_single_transaction`

```python
def test_merkle_root_single_transaction():
    """Merkle tree con 1 transacción"""
    tx = create_dummy_tx(1)
    merkle = MerkleTree([tx])

    root = merkle.get_root()

    assert root is not None
    assert len(root) == 64
    assert isinstance(root, str)
```

**¿Qué verifica?**

Las propiedades básicas del Merkle root: que existe, tiene el formato correcto (64 caracteres hexadecimales) y es un string.

**¿Por qué 64 caracteres?**

SHA256 produce 32 bytes = 256 bits. Representado en hexadecimal (cada byte = 2 caracteres hex), resulta en exactamente 64 caracteres. El double SHA256 que usa este demo produce la misma longitud.

**Con una sola transacción:**

El árbol tiene un solo nivel. La raíz es directamente el hash de esa única transacción. No hay combinación de pares porque no hay pares.

---

### `test_merkle_root_deterministic`

```python
def test_merkle_root_deterministic():
    """Merkle root es determinístico (mismo input = mismo output)"""
    tx1 = create_dummy_tx(1)
    tx2 = create_dummy_tx(2)

    merkle1 = MerkleTree([tx1, tx2])
    merkle2 = MerkleTree([tx1, tx2])

    assert merkle1.get_root() == merkle2.get_root()
```

**¿Qué verifica?**

Que construir dos árboles con las mismas transacciones produce el mismo Merkle root.

**¿Por qué es crítico el determinismo?**

En blockchain, el Merkle root se incluye en el block header y determina el hash del bloque. Si el Merkle root fuera diferente en cada ejecución, distintos nodos calcularían hashes de bloque diferentes para el mismo bloque, rompiendo el consenso.

**Lo que garantiza el determinismo:**

1. `create_dummy_tx` produce transacciones idénticas con el mismo seed
2. `json.dumps(sort_keys=True)` en `hash_transaction` serializa siempre en el mismo orden
3. SHA256 es una función pura (mismo input → mismo output)

---

### `test_merkle_root_changes_with_data`

```python
def test_merkle_root_changes_with_data():
    """Merkle root cambia si cambian las transacciones"""
    tx1 = create_dummy_tx(1)
    tx2 = create_dummy_tx(2)
    tx3 = create_dummy_tx(3)

    merkle1 = MerkleTree([tx1, tx2])
    merkle2 = MerkleTree([tx1, tx3])

    assert merkle1.get_root() != merkle2.get_root()
```

**¿Qué verifica?**

Que sustituir una transacción (tx2 por tx3) cambia el Merkle root.

**¿Por qué es fundamental para la seguridad?**

Si el Merkle root no cambiara al modificar una transacción, un atacante podría alterar el historial de transacciones sin invalidar el bloque. El efecto avalancha del SHA256 garantiza que cualquier cambio, por pequeño que sea, produce un root completamente diferente.

```
[tx1, tx2] → Root = "a3f2c1..."
[tx1, tx3] → Root = "7b9e4f..."  ← completamente diferente
```

---

### `test_merkle_order_matters`

```python
def test_merkle_order_matters():
    """Orden de transacciones afecta el Merkle root"""
    tx1 = create_dummy_tx(1)
    tx2 = create_dummy_tx(2)

    merkle1 = MerkleTree([tx1, tx2])
    merkle2 = MerkleTree([tx2, tx1])

    assert merkle1.get_root() != merkle2.get_root()
```

**¿Qué verifica?**

Que `[tx1, tx2]` y `[tx2, tx1]` producen Merkle roots diferentes.

**¿Por qué el orden importa?**

Al combinar pares de hashes, la concatenación es ordenada: `H_left + H_right`. Invertir el orden produce una concatenación diferente y, por ende, un hash diferente:

```
[tx1, tx2]:
H12 = SHA256(SHA256(H1 + H2))  → "a3f2c1..."

[tx2, tx1]:
H21 = SHA256(SHA256(H2 + H1))  → "7b9e4f..."  ← diferente
```

**Implicación práctica:** El orden de transacciones en un bloque está fijado. Los nodos deben procesar las transacciones en el mismo orden para calcular el Merkle root correcto.

---

## Tests de Casos Borde

### `test_merkle_empty_transactions`

```python
def test_merkle_empty_transactions():
    """Merkle tree vacío retorna hash de ceros"""
    merkle = MerkleTree([])

    root = merkle.get_root()

    assert root == '0' * 64
```

**¿Qué verifica?**

Que un árbol sin transacciones retorna `'0' * 64` (64 ceros) como root, sin lanzar excepciones.

**¿Por qué `'0' * 64` y no `None` o una excepción?**

Un valor nulo o excepción complicaría el código que consume el Merkle root (por ejemplo, el block header). Retornar un hash de ceros es una convención clara que indica "sin transacciones" y es compatible con el formato esperado (64 chars hex).

**Casos donde esto ocurre:**

- Bloque génesis (primer bloque, sin transacciones previas)
- Bloque vacío (solo con transacción coinbase que aún no se implementa)

---

### `test_merkle_odd_number_of_transactions`

```python
def test_merkle_odd_number_of_transactions():
    """Merkle tree con número impar de transacciones (duplica última)"""
    txs = [create_dummy_tx(i) for i in range(3)]
    merkle = MerkleTree(txs)

    root = merkle.get_root()

    assert root is not None
    assert len(root) == 64
```

**¿Qué verifica?**

Que el árbol maneja correctamente 3 transacciones (número impar) sin errores.

**El mecanismo de duplicación:**

Al tener un número impar de elementos en un nivel, se duplica el último:

```
3 transacciones:
Nivel 0: [H1, H2, H3]
          ↓ número impar → duplicar última
          [H1, H2, H3, H3]
Nivel 1: [H12, H33]
          ↓ número par
          [H1233]  ← root
```

Este comportamiento es idéntico al de Bitcoin real y garantiza que el algoritmo siempre pueda combinar pares.

**¿Por qué duplicar en lugar de hacer algo más sofisticado?**

La duplicación es simple, determinística y está especificada en el protocolo de Bitcoin. Todos los nodos aplican la misma regla, garantizando el mismo resultado.

---

### `test_merkle_even_number_of_transactions`

```python
def test_merkle_even_number_of_transactions():
    """Merkle tree con número par de transacciones"""
    txs = [create_dummy_tx(i) for i in range(4)]
    merkle = MerkleTree(txs)

    root = merkle.get_root()

    assert root is not None
    assert len(root) == 64
```

**¿Qué verifica?**

El caso estándar: 4 transacciones (número par) construye el árbol sin necesidad de duplicación.

**¿Por qué tener ambos tests (par e impar)?**

La lógica de duplicación es un branch en el código de `build_tree()`. Sin ambos tests, uno de los caminos podría tener un bug que no se detectaría:

- `test_merkle_even`: cubre el path sin duplicación
- `test_merkle_odd`: cubre el path con duplicación

---

## Test de Estructura Interna

### `test_merkle_tree_structure`

```python
def test_merkle_tree_structure():
    """Verificar estructura del árbol (niveles)"""
    txs = [create_dummy_tx(i) for i in range(4)]
    merkle = MerkleTree(txs)

    assert len(merkle.tree) == 3
    assert len(merkle.tree[0]) == 4  # Hojas
    assert len(merkle.tree[1]) == 2  # Nivel medio
    assert len(merkle.tree[2]) == 1  # Raíz
```

**¿Qué verifica?**

Que el árbol interno (`merkle.tree`) tiene exactamente la estructura esperada para 4 transacciones.

**Estructura esperada:**

```
merkle.tree[0] = [H1, H2, H3, H4]   ← 4 hojas (nivel 0)
merkle.tree[1] = [H12, H34]          ← 2 nodos (nivel 1)
merkle.tree[2] = [Root]              ← 1 raíz (nivel 2)
```

**¿Por qué acceder a `merkle.tree` directamente?**

Este test es de **caja blanca**: accede a la estructura interna del objeto para verificar que la implementación construye los niveles correctamente, no solo que el resultado final es correcto. Complementa los tests de caja negra que solo verifican el output de `get_root()`.

**Fórmula de niveles:** `log₂(n) + 1` niveles para n transacciones (potencias de 2). Para 4 TXs: `log₂(4) + 1 = 3` niveles.

---

## Tests de Pruebas Merkle (Merkle Proofs)

### `test_merkle_proof_generation`

```python
def test_merkle_proof_generation():
    """Generar prueba Merkle para una transacción"""
    txs = [create_dummy_tx(i) for i in range(4)]
    merkle = MerkleTree(txs)

    proof = merkle.get_proof(0)

    assert proof is not None
    assert isinstance(proof, list)
    assert len(proof) > 0
```

**¿Qué verifica?**

Que `get_proof(0)` retorna una prueba válida (no nula, es una lista, tiene al menos un elemento).

**¿Qué es una prueba Merkle?**

Una lista de hashes "hermanos" que permite reconstruir el camino desde la hoja hasta la raíz:

```
Para tx0 en un árbol de 4 transacciones:
proof = [
    {'hash': 'H2', 'position': 'right'},   ← hermano de H1 en nivel 0
    {'hash': 'H34', 'position': 'right'}   ← hermano de H12 en nivel 1
]
```

**¿Por qué `len(proof) > 0`?**

Una prueba vacía no podría verificar nada. Para cualquier árbol con ≥ 2 transacciones, la prueba debe contener al menos un hash hermano. (Para un árbol de 1 transacción, el caso es especial y podría retornar prueba vacía.)

---

### `test_merkle_proof_verification`

```python
def test_merkle_proof_verification():
    """Verificar prueba Merkle"""
    txs = [create_dummy_tx(i) for i in range(4)]
    merkle = MerkleTree(txs)

    tx_hash = merkle.hash_transaction(txs[0])
    proof = merkle.get_proof(0)
    merkle_root = merkle.get_root()

    is_valid = MerkleTree.verify_proof(tx_hash, merkle_root, proof)

    assert is_valid
```

**¿Qué verifica?**

El flujo completo de SPV (Simplified Payment Verification): que una transacción real en el árbol puede verificarse usando solo su hash, la prueba y el Merkle root.

**Proceso de verificación:**

```
tx_hash = H1                    ← hash de tx0
proof   = [H2 (right), H34 (right)]

Paso 1: current = H1
        hermano H2 está a la right → combinar left+right
        current = SHA256(SHA256(H1 + H2)) = H12

Paso 2: current = H12
        hermano H34 está a la right → combinar left+right
        current = SHA256(SHA256(H12 + H34)) = Root_calculado

Verificar: Root_calculado == merkle_root → True ✅
```

**¿Por qué `verify_proof` es un método de clase (`@staticmethod`)?**

La verificación no requiere el árbol completo. Un nodo ligero (SPV) puede verificar sin conocer las otras transacciones. Al ser static, puede llamarse sin instanciar un `MerkleTree`.

---

### `test_merkle_proof_invalid`

```python
def test_merkle_proof_invalid():
    """Prueba Merkle inválida debe fallar"""
    txs = [create_dummy_tx(i) for i in range(4)]
    merkle = MerkleTree(txs)

    fake_tx = create_dummy_tx(999)
    fake_tx_hash = merkle.hash_transaction(fake_tx)

    proof = merkle.get_proof(0)
    merkle_root = merkle.get_root()

    is_valid = MerkleTree.verify_proof(fake_tx_hash, merkle_root, proof)

    assert not is_valid
```

**¿Qué verifica?**

Que una transacción falsa (no incluida en el árbol) no puede verificarse, incluso usando una prueba legítima de otra transacción.

**¿Por qué usar la prueba de otra TX?**

Este test simula un ataque realista: un atacante intenta hacer creer que su transacción falsa está en el bloque usando una prueba válida robada de otra transacción. El test verifica que esto no funciona.

**¿Por qué falla la verificación?**

```
fake_tx_hash = H_fake               ← hash de transacción que NO está en el árbol
proof de tx0 = [H2 (right), H34 (right)]  ← prueba legítima de tx0

Paso 1: current = H_fake
        hermano H2 → combinar: SHA256(SHA256(H_fake + H2)) = H_fake2
        H_fake2 ≠ H12

Paso 2: current = H_fake2
        hermano H34 → SHA256(SHA256(H_fake2 + H34)) = Root_incorrecto
        Root_incorrecto ≠ merkle_root → False ❌
```

El cambio en el punto de partida (H1 → H_fake) se propaga hacia arriba cambiando todos los hashes intermedios, resultando en una raíz diferente a la real.

---

## Cobertura Completa de la Suite

```
core/merkle.py
    │
    ├── MerkleTree.__init__
    │   └── test_merkle_root_single_transaction ✓
    │
    ├── MerkleTree.hash_transaction
    │   └── test_merkle_proof_verification (usa hash_transaction) ✓
    │   └── test_merkle_proof_invalid (usa hash_transaction) ✓
    │
    ├── MerkleTree.build_tree
    │   ├── test_merkle_root_deterministic ✓
    │   ├── test_merkle_root_changes_with_data ✓
    │   ├── test_merkle_odd_number_of_transactions ✓
    │   ├── test_merkle_even_number_of_transactions ✓
    │   ├── test_merkle_empty_transactions ✓
    │   ├── test_merkle_tree_structure ✓
    │   └── test_merkle_order_matters ✓
    │
    ├── MerkleTree.get_root
    │   └── Cubierto por todos los tests anteriores ✓
    │
    ├── MerkleTree.get_proof
    │   ├── test_merkle_proof_generation ✓
    │   ├── test_merkle_proof_verification ✓
    │   └── test_merkle_proof_invalid ✓
    │
    └── MerkleTree.verify_proof
        ├── test_merkle_proof_verification ✓
        └── test_merkle_proof_invalid ✓
```

---

## Flujo General de los Tests

```
create_dummy_tx(seed)
    │
    ├── timestamp = seed  → Determinismo garantizado
    ├── sender = f"from_{seed}"
    └── recipient = f"to_{seed}"

MerkleTree(txs)
    │
    ├── get_root()        → Root hash (64 chars)
    ├── hash_transaction() → Hash de una TX individual
    ├── get_proof(index)  → Lista de hashes hermanos
    └── verify_proof()    → True/False (método estático)
```

---

## Cómo Ejecutar los Tests

```bash
# Todos los tests de Merkle
pytest tests/test_merkle.py -v

# Solo tests de pruebas Merkle
pytest tests/test_merkle.py -v -k "proof"

# Solo tests de estructura
pytest tests/test_merkle.py -v -k "structure or empty or odd or even"

# Con coverage
pytest tests/test_merkle.py -v --cov=core.merkle --cov-report=term-missing
```

**Salida esperada:**

```
tests/test_merkle.py::test_merkle_root_single_transaction    PASSED
tests/test_merkle.py::test_merkle_root_deterministic         PASSED
tests/test_merkle.py::test_merkle_root_changes_with_data     PASSED
tests/test_merkle.py::test_merkle_odd_number_of_transactions PASSED
tests/test_merkle.py::test_merkle_even_number_of_transactions PASSED
tests/test_merkle.py::test_merkle_empty_transactions          PASSED
tests/test_merkle.py::test_merkle_tree_structure             PASSED
tests/test_merkle.py::test_merkle_order_matters              PASSED
tests/test_merkle.py::test_merkle_proof_generation           PASSED
tests/test_merkle.py::test_merkle_proof_verification         PASSED
tests/test_merkle.py::test_merkle_proof_invalid              PASSED
```

---

*Documento: `DOC_tests_test_merkle.md` — Demo Blockchain Fase 2.2*
