# Documentación Técnica: `core/block.py`

---

## Propósito del Archivo

`block.py` define la unidad fundamental de la blockchain: el **bloque**. Un bloque agrupa un conjunto de transacciones validadas y las sella con un hash criptográfico que lo conecta con el bloque anterior, formando la cadena.

**Analogía:** Un bloque es como una página de un libro contable notariado:
- El **header** es el sello del notario con la fecha, el folio anterior y el resumen del contenido
- Las **transactions** son los movimientos registrados en esa página
- El **hash** es la huella digital única de esa página — si alguien modifica un solo dato, la huella cambia

---

## Estructura de un bloque en este demo vs Bitcoin

| Componente | Bitcoin | Este Demo |
|------------|---------|-----------|
| Header | 80 bytes fijos (6 campos) | Dict JSON serializable |
| Transactions | Formato binario TxIn/TxOut | Objetos Python serializados a JSON |
| Hash del bloque | SHA256d del header binario | SHA256d del header JSON |
| Identificador | Hash del header (256 bits) | Hash del header (256 bits) ✅ |
| Enlace con anterior | Campo `prev_hash` en header | Campo `prev_hash` en header ✅ |

---

## Dependencias

```python
import hashlib
import json
import time
from typing import List, Optional
from core.merkle import MerkleTree
```

| Import | Propósito |
|--------|-----------|
| `hashlib` | SHA256 para el hash del header (double SHA256) |
| `json` | Serialización determinística del header |
| `time` | Timestamp Unix para el header |
| `MerkleTree` | Calcular y verificar el Merkle root de las transacciones |

---

## Clase `BlockHeader`

```python
class BlockHeader:
```

Contiene los metadatos del bloque. En Bitcoin, el header tiene exactamente 80 bytes y es el único dato que se hashea durante el minado — las transacciones no se tocan. En este demo el concepto es idéntico: el PoW opera solo sobre el header.

**Atributos de instancia:**

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `prev_hash` | `str` | Hash del bloque anterior (64 chars hex) |
| `merkle_root` | `str` | Raíz del Merkle tree de las TXs (64 chars hex) |
| `timestamp` | `float` | Unix timestamp de cuando se creó el bloque |
| `difficulty` | `int` | Número de ceros requeridos al inicio del hash |
| `nonce` | `int` | Número encontrado por el PoW para cumplir difficulty |

---

## Función `BlockHeader.__init__`

```python
def __init__(self, prev_hash: str, merkle_root: str,
             timestamp: float, difficulty: int = 4, nonce: int = 0):
```

**¿Qué hace?**

Inicializa los cinco campos del header. El `nonce` empieza en 0 y el minero lo incrementa hasta encontrar un hash válido.

**¿Por qué el nonce empieza en 0?**

El proceso de minado es una búsqueda secuencial: probar nonce=0, 1, 2, 3... hasta que el hash resultante empiece con el número de ceros exigido por `difficulty`. No hay forma matemática de calcular el nonce correcto de antemano — hay que probarlo.

```
nonce=0 → hash="1a2b3c..."  ✗ no cumple
nonce=1 → hash="9f8e7d..."  ✗ no cumple
...
nonce=65432 → hash="0000a3b4..."  ✅ cumple difficulty=4
```

---

## Función `BlockHeader.to_dict`

```python
def to_dict(self) -> dict:
    return {
        'prev_hash': self.prev_hash,
        'merkle_root': self.merkle_root,
        'timestamp': self.timestamp,
        'difficulty': self.difficulty,
        'nonce': self.nonce
    }
```

**¿Qué hace?**

Serializa el header a un diccionario Python. Es el paso previo a convertirlo a JSON para calcular el hash.

**¿Por qué es necesario?**

Python no puede hashear objetos directamente. Necesitamos una representación en texto determinística — el mismo objeto siempre produce el mismo string — para que el hash sea reproducible por cualquier nodo de la red.

---

## Función `BlockHeader.hash`

```python
def hash(self) -> str:
    header_str = json.dumps(self.to_dict(), sort_keys=True)
    hash1 = hashlib.sha256(header_str.encode()).digest()
    hash2 = hashlib.sha256(hash1).hexdigest()
    return hash2
```

**¿Qué hace?**

Calcula el identificador único del bloque mediante double SHA256 del header serializado.

**Proceso completo:**

```
BlockHeader (objeto Python)
        │
        ▼
to_dict()  →  {'prev_hash': '...', 'merkle_root': '...', ...}
        │
        ▼
json.dumps(sort_keys=True)  →  string JSON determinístico
        │
        ▼
.encode()  →  bytes UTF-8
        │
        ▼
SHA256  →  32 bytes (digest, no hexdigest)
        │
        ▼
SHA256  →  32 bytes
        │
        ▼
.hexdigest()  →  64 caracteres hex
        │
        ▼
"0000a3b4c5d6e7f8..."  ← identificador único del bloque
```

**¿Por qué `sort_keys=True` en json.dumps?**

Sin `sort_keys=True`, el orden de las claves en el diccionario puede variar entre versiones de Python o ejecuciones. Con `sort_keys=True`, el JSON siempre produce el mismo string para el mismo contenido, garantizando que el hash sea idéntico en todos los nodos de la red.

**¿Por qué double SHA256 (SHA256d)?**

Bitcoin usa SHA256 dos veces por razones de seguridad:
1. Protección contra ataques de extensión de longitud (length extension attacks) en SHA256
2. Si se descubre una debilidad en SHA256 que permita encontrar colisiones en el primer hash, el segundo SHA256 agrega una capa adicional de protección

En este demo replicamos SHA256d exactamente igual que Bitcoin.

**Diferencia con Bitcoin:**

En Bitcoin el header es un struct binario de 80 bytes exactos y el hash se calcula sobre esos bytes directamente. En este demo el header se serializa a JSON primero. El resultado conceptual es idéntico: un identificador único de 256 bits que cambia si se modifica cualquier campo del header.

---

## Función `BlockHeader.from_dict`

```python
@staticmethod
def from_dict(data: dict) -> 'BlockHeader':
    return BlockHeader(
        prev_hash=data['prev_hash'],
        merkle_root=data['merkle_root'],
        timestamp=data['timestamp'],
        difficulty=data['difficulty'],
        nonce=data['nonce']
    )
```

**¿Qué hace?**

Reconstruye un objeto `BlockHeader` desde un diccionario. Se usa al recibir bloques de la red — el bloque viajó como JSON, y aquí se convierte de vuelta a objeto Python.

**Flujo de deserialización:**

```
Mensaje WebSocket (JSON string)
        │
        ▼
json.loads()  →  dict Python
        │
        ▼
Block.from_dict(data)
        │
        ▼
BlockHeader.from_dict(data['header'])  →  objeto BlockHeader
```

---

## Clase `Block`

```python
class Block:
```

Bloque completo: combina el header con la lista de transacciones. El header identifica y protege al bloque; las transacciones son el contenido real.

**Atributos de instancia:**

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `header` | `BlockHeader` | Metadatos del bloque |
| `transactions` | `List[Transaction]` | Lista de transacciones incluidas |

---

## Propiedad `Block.hash`

```python
@property
def hash(self) -> str:
    return self.header.hash()
```

**¿Qué hace?**

Expone el hash del header como propiedad del bloque. Es el identificador único del bloque en la cadena.

**¿Por qué `@property` y no un atributo?**

Si fuera un atributo (`self.hash = header.hash()`), se calcularía solo al crear el bloque. Como `@property`, se recalcula cada vez que se accede — lo que garantiza que si el header cambia (por ejemplo, durante el minado al actualizar el nonce), el hash refleja siempre el estado actual.

**Uso:**

```python
block.hash  # → "0000a3b4c5d6e7f8..." (64 chars hex)
blockchain.get_block_by_hash(block.hash)
```

---

## Función `Block.validate_merkle_root`

```python
def validate_merkle_root(self) -> bool:
    merkle = MerkleTree(self.transactions)
    calculated_root = merkle.get_root()
    return calculated_root == self.header.merkle_root
```

**¿Qué hace?**

Verifica que el `merkle_root` en el header corresponde exactamente a las transacciones incluidas en el bloque. Si alguien modifica una transacción después de minar el bloque, el Merkle root recalculado no coincidirá.

**¿Por qué el Merkle root protege las transacciones?**

```
TX1  TX2  TX3  TX4
 │    │    │    │
 └──┬─┘    └──┬─┘
   H12        H34
    │           │
    └─────┬─────┘
         ROOT  ←── este valor va en el header
```

Si modificas TX2, cambia H12, lo que cambia ROOT. El ROOT en el header ya no coincide con el recalculado → bloque inválido.

**En Bitcoin:** El Merkle root permite verificar que una TX específica está en un bloque sin descargar todas las TXs (Simplified Payment Verification, SPV). En este demo verificamos el root completo por simplicidad.

---

## Función `Block.validate_pow`

```python
def validate_pow(self) -> bool:
    target = '0' * self.header.difficulty
    return self.hash.startswith(target)
```

**¿Qué hace?**

Verifica que el hash del bloque cumple el requisito de difficulty: debe comenzar con exactamente `difficulty` ceros.

**¿Por qué esto es difícil de falsificar?**

SHA256 es una función de sentido único — no hay forma de calcular qué input produce un hash con N ceros sin probar millones de valores. El único camino es la fuerza bruta: cambiar el nonce e intentar de nuevo.

```
difficulty=4 → target="0000"
hash debe empezar con "0000..."

Probabilidad por intento: 1/16^4 = 1/65536 ≈ 0.0015%
Intentos esperados: ~65,536

difficulty=5 → target="00000"
Intentos esperados: ~1,048,576
```

**Verificación es O(1), minado es O(N):**

Verificar si un bloque cumple PoW toma microsegundos (calcular el hash una vez). Encontrar el nonce correcto puede tomar millones de intentos. Esta asimetría es el fundamento de la seguridad de Bitcoin.

---

## Función `Block.validate_transactions`

```python
def validate_transactions(self) -> bool:
    for tx in self.transactions:
        if not tx.is_valid():
            return False
    return True
```

**¿Qué hace?**

Verifica que todas las transacciones del bloque tienen firmas digitales válidas. Delega a `Transaction.is_valid()` que verifica la firma Ed25519.

**¿Por qué validar TXs dentro del bloque?**

Un nodo malicioso podría construir un bloque con transacciones falsas (sin firmas válidas) y cumplir el PoW. La validación de firmas garantiza que solo el dueño legítimo de los fondos puede crear una TX válida.

**Nota sobre la TX coinbase:**

La TX coinbase (recompensa del minero) tiene `from_address = "COINBASE"` y no tiene firma digital. `Transaction.is_valid()` maneja este caso especialmente — las coinbase siempre son válidas.

---

## Función `Block.to_dict`

```python
def to_dict(self) -> dict:
    return {
        'header': self.header.to_dict(),
        'transactions': [tx.to_dict() for tx in self.transactions]
    }
```

**¿Qué hace?**

Serializa el bloque completo a un diccionario anidado para transmisión por la red o almacenamiento.

**Estructura resultante:**

```python
{
    'header': {
        'prev_hash': '0000a3b4...',
        'merkle_root': '7e6d5c4b...',
        'timestamp': 1707234567.89,
        'difficulty': 4,
        'nonce': 65432
    },
    'transactions': [
        {'from_address': 'COINBASE', 'to_address': '1A2B3C...', 'amount': 50, ...},
        {'from_address': '1A2B3C...', 'to_address': '1X2Y3Z...', 'amount': 10, ...}
    ]
}
```

---

## Función `Block.from_dict`

```python
@staticmethod
def from_dict(data: dict) -> 'Block':
    from core.transaction import Transaction
    header = BlockHeader.from_dict(data['header'])
    transactions = [
        Transaction.from_dict(tx_data)
        for tx_data in data['transactions']
    ]
    return Block(header, transactions)
```

**¿Qué hace?**

Reconstruye un objeto `Block` completo desde un diccionario. Es el proceso inverso a `to_dict()`.

**¿Por qué el import de Transaction está dentro de la función?**

Para evitar importaciones circulares. `block.py` importa de `merkle.py`, y `transaction.py` podría en algún momento importar de `block.py`. Con el import local dentro del método, Python resuelve la dependencia solo cuando se necesita, no al cargar el módulo.

**Flujo de uso en la red:**

```
Nodo A mina un bloque
        │
        ▼
block.to_dict()  →  dict
        │
        ▼
json.dumps()  →  string JSON
        │
        ▼
WebSocket.send()  →  transmisión
        │
        ▼  (en Nodo B)
json.loads()  →  dict
        │
        ▼
Block.from_dict(dict)  →  objeto Block reconstruido
        │
        ▼
blockchain.add_block(block)  →  validar y agregar
```

---

## Flujo Completo de Creación de un Bloque

```python
# 1. Seleccionar transacciones del mempool
pending_txs = blockchain.get_transactions_for_mining()
coinbase = Transaction("COINBASE", miner_address, 50)
block_txs = [coinbase] + pending_txs

# 2. Calcular Merkle root de las TXs
merkle = MerkleTree(block_txs)
merkle_root = merkle.get_root()

# 3. Crear header (nonce=0, se encontrará durante el minado)
header = BlockHeader(
    prev_hash=blockchain.get_latest_block().hash,
    merkle_root=merkle_root,
    timestamp=time.time(),
    difficulty=4,
    nonce=0,
)

# 4. PoW: encontrar nonce que cumple difficulty
pow_solver = ProofOfWork(header, difficulty=4)
header.nonce = pow_solver.mine()
# → header.nonce = 65432 (ejemplo)
# → header.hash() = "0000a3b4..." ✅

# 5. Crear bloque completo
block = Block(header, block_txs)

# 6. Validar y agregar a la cadena
blockchain.add_block(block)
```

---

## Validaciones en `blockchain.add_block`

Al recibir un bloque (propio o de la red), se ejecutan estas validaciones en orden:

| # | Validación | Qué verifica | Si falla |
|---|-----------|--------------|----------|
| 1 | `validate_pow()` | Hash cumple difficulty | Rechazado — nadie puede falsificar PoW |
| 2 | `validate_merkle_root()` | TXs no fueron modificadas | Rechazado — integridad de datos |
| 3 | `prev_hash == latest.hash` | Conecta con el tip de la cadena | Solicita sincronización |
| 4 | `timestamp <= now + 2h` | No viene del futuro | Rechazado — evita manipulación |
| 5 | `transactions[0].from_address == "COINBASE"` | Primera TX es coinbase | Rechazado — protocolo incorrecto |
| 6 | `validate_transactions()` | Todas las firmas son válidas | Rechazado — TX falsa |

---

## Tests Asociados: `tests/test_block.py`

| Test | Función que prueba | Qué verifica |
|------|-------------------|--------------|
| `test_block_header_creation` | `BlockHeader.__init__` | Campos se asignan correctamente |
| `test_block_header_hash` | `BlockHeader.hash` | Hash es string hex de 64 chars |
| `test_block_header_hash_changes_with_nonce` | `BlockHeader.hash` | Cambiar nonce cambia el hash |
| `test_block_header_serialization` | `to_dict` / `from_dict` | Serialización es reversible |
| `test_block_creation` | `Block.__init__` | Block se crea con header y TXs |
| `test_block_hash_property` | `Block.hash` | Propiedad delega a header.hash() |
| `test_validate_pow_valid` | `validate_pow` | Hash con ceros suficientes es válido |
| `test_validate_pow_invalid` | `validate_pow` | Hash sin ceros suficientes es inválido |
| `test_validate_merkle_root` | `validate_merkle_root` | Merkle root correcto retorna True |
| `test_validate_merkle_root_tampered` | `validate_merkle_root` | TX modificada invalida Merkle root |
| `test_block_serialization` | `to_dict` / `from_dict` | Bloque completo es serializable |
| `test_block_hash_is_deterministic` | `Block.hash` | Mismo bloque = mismo hash siempre |

---

*Documento: `DOC_core_block.md` — Demo Blockchain*
