# Documentación Técnica: `core/blockchain.py`

---

## Propósito del Archivo

`blockchain.py` implementa la cadena de bloques completa: la estructura de datos central que mantiene el historial inmutable de transacciones, gestiona las transacciones pendientes (mempool) y coordina el proceso de minado.

**Analogía:** La blockchain es el libro contable oficial de la red:
- La **chain** es el historial permanente e inmutable de todas las transacciones confirmadas
- El **mempool** es la sala de espera donde las transacciones esperan ser confirmadas
- El **minado** es el proceso de seleccionar TXs del mempool, agruparlas en un bloque y sellarlo criptográficamente
- La **longest chain rule** es el mecanismo de consenso: cuando dos nodos tienen versiones diferentes de la cadena, gana la más larga

---

## Diferencias con Bitcoin

| Aspecto | Bitcoin | Este Demo |
|---------|---------|-----------|
| Modelo de balance | UTXO (Unspent Transaction Outputs) | Account model (suma en cadena) |
| Difficulty | Ajustable cada 2016 bloques | Fija en `config.py` |
| Longest chain | Por trabajo acumulado (suma de difficulty) | Por número de bloques |
| Fees | Sí (incentivo para mineros) | No |
| Persistencia | En disco (LevelDB) | En memoria (lista Python) |
| Max block size | 1-4 MB | Configurable en `MAX_TXS_PER_BLOCK` |

---

## Dependencias

```python
import time
import threading
from typing import List, Optional
from core.block import Block, BlockHeader
from core.transaction import Transaction
from core.merkle import MerkleTree
from core.pow import ProofOfWork
from config import BLOCK_REWARD, DIFFICULTY, MAX_MEMPOOL_SIZE, MAX_TXS_PER_BLOCK
```

| Import | Propósito |
|--------|-----------|
| `Block`, `BlockHeader` | Estructura del bloque |
| `Transaction` | Transacciones en mempool y cadena |
| `MerkleTree` | Calcular Merkle root al minar |
| `ProofOfWork` | Encontrar nonce válido durante el minado |
| `config.*` | Parámetros del sistema (reward, difficulty, límites) |

---

## Clase `Blockchain`

```python
class Blockchain:
```

Gestiona la cadena de bloques completa. Es la fuente de verdad del nodo: mantiene el historial confirmado y el mempool de TXs pendientes.

**Atributos de instancia:**

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `chain` | `List[Block]` | Cadena de bloques desde el génesis |
| `mempool` | `List[Transaction]` | TXs pendientes de confirmación |
| `BLOCK_REWARD` | `float` | Coins que recibe el minero por bloque |
| `DIFFICULTY` | `int` | Número de ceros requeridos en el hash |
| `MAX_MEMPOOL_SIZE` | `int` | Límite máximo de TXs en mempool |
| `MAX_TXS_PER_BLOCK` | `int` | Máximo de TXs por bloque |

---

## Función `__init__`

```python
def __init__(self):
    self.chain   = []
    self.mempool = []
    self.BLOCK_REWARD      = BLOCK_REWARD
    self.DIFFICULTY        = DIFFICULTY
    self.MAX_MEMPOOL_SIZE  = MAX_MEMPOOL_SIZE
    self.MAX_TXS_PER_BLOCK = MAX_TXS_PER_BLOCK
    self.create_genesis_block()
```

**¿Qué hace?**

Inicializa una blockchain vacía y crea inmediatamente el bloque génesis. Cada nodo que arranca tiene exactamente el mismo génesis, lo que garantiza que todos partan del mismo estado.

**¿Por qué copiar las constantes de config a atributos de instancia?**

Permite modificar la difficulty de una instancia específica sin afectar a otras. Esto es esencial para los tests — cada test puede crear una Blockchain con difficulty=1 para que el minado sea instantáneo:

```python
bc = Blockchain()
bc.DIFFICULTY = 1  # solo afecta esta instancia
```

---

## Función `create_genesis_block`

```python
def create_genesis_block(self):
    genesis_tx           = Transaction("COINBASE", "genesis_address", 0)
    genesis_tx.timestamp = 0
    merkle = MerkleTree([genesis_tx])
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=0,
        difficulty=1,
        nonce=0,
    )
    genesis = Block(header, [genesis_tx])
    self.chain.append(genesis)
```

**¿Qué hace?**

Crea el primer bloque de la cadena — el único que no tiene bloque anterior. Todos los nodos de la red crean exactamente el mismo génesis, con los mismos parámetros fijos.

**¿Por qué `prev_hash='0' * 64`?**

El bloque génesis no tiene predecesor. Se usa una cadena de 64 ceros como convención para indicar "este es el principio". Bitcoin hace exactamente lo mismo.

**¿Por qué `timestamp=0` y `amount=0`?**

Para que el hash del génesis sea determinístico e idéntico en todos los nodos. Si usáramos `time.time()`, cada nodo generaría un génesis diferente y nunca podrían sincronizarse.

**¿Por qué `difficulty=1`?**

El génesis no necesita trabajo computacional real — es un bloque especial que todos aceptan por convención. Con difficulty=1 el nonce=0 ya produce un hash válido.

---

## Funciones de Consulta

### `get_latest_block`

```python
def get_latest_block(self) -> Block:
    return self.chain[-1]
```

Retorna el bloque más reciente — el "tip" de la cadena. Se usa como `prev_hash` al minar el siguiente bloque.

---

### `get_height`

```python
def get_height(self) -> int:
    return len(self.chain)
```

Altura actual de la cadena. El génesis tiene altura 1, el siguiente bloque altura 2, etc. Se usa para comparar cadenas y detectar nodos desfasados.

---

### `get_block_by_hash`

```python
def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
    for block in self.chain:
        if block.hash == block_hash:
            return block
    return None
```

Búsqueda lineal O(n) de un bloque por su hash. En Bitcoin se usa un índice en disco. Para el demo con ~100 bloques, O(n) es perfectamente aceptable.

---

### `get_balance`

```python
def get_balance(self, address: str) -> float:
    balance = 0.0
    for block in self.chain:
        for tx in block.transactions:
            if tx.to_address == address:
                balance += tx.amount
            if tx.from_address == address and tx.from_address != "COINBASE":
                balance -= tx.amount
    return balance
```

**¿Qué hace?**

Calcula el balance de una dirección recorriendo toda la cadena y sumando entradas menos salidas. Es el **Account Model** — el balance es una propiedad derivada del historial completo.

**Diferencia con Bitcoin (UTXO):**

Bitcoin no recorre la cadena para calcular balances. Mantiene un conjunto de "salidas no gastadas" (UTXO set) actualizado en tiempo real. Para conocer el balance de una dirección, busca en el UTXO set todas las salidas dirigidas a esa dirección.

```
Account Model (este demo):
    balance = Σ(entradas) - Σ(salidas) ← recorrer toda la cadena

UTXO Model (Bitcoin):
    balance = Σ(UTXOs dirigidos a address) ← consulta directa al UTXO set
```

El Account Model es O(n×m) donde n=bloques y m=TXs por bloque. Para el demo es aceptable. En producción, UTXO es O(1) después de mantener el conjunto actualizado.

---

## Sección: Mempool

### `add_transaction_to_mempool`

```python
def add_transaction_to_mempool(self, tx: Transaction) -> bool:
```

**¿Qué hace?**

Valida y agrega una transacción al mempool. Ejecuta cuatro validaciones en orden:

```
TX recibida
     │
     ▼
¿Mempool lleno? (>MAX_MEMPOOL_SIZE)  → Rechazar
     │
     ▼
¿Firma válida? (Ed25519 verify)       → Rechazar si inválida
     │
     ▼
¿TX duplicada? (mismo hash)           → Rechazar si ya existe
     │
     ▼
¿Balance suficiente? (no aplica a COINBASE) → Rechazar si insuficiente
     │
     ▼
Agregar al mempool ✅
```

**¿Por qué validar balance al agregar al mempool?**

Previene que un nodo malicioso llene el mempool con transacciones imposibles de ejecutar (doble gasto, sin fondos). En Bitcoin este problema se resuelve con fees — las TXs sin fondos no pagan fee y no llegan al mempool.

**¿Por qué excluir COINBASE de la validación de balance?**

Las TXs coinbase las crea el minero al construir el bloque. No tienen `from_address` real y su validez se verifica de otra forma (debe ser la primera TX del bloque, `from_address == "COINBASE"`).

---

### `get_transactions_for_mining`

```python
def get_transactions_for_mining(self, max_count: int = None) -> List[Transaction]:
    if max_count is None:
        max_count = self.MAX_TXS_PER_BLOCK
    return self.mempool[:max_count]
```

Selecciona las primeras `max_count` TXs del mempool para incluir en el próximo bloque. Estrategia **FIFO** (primero en llegar, primero en minarse).

**Diferencia con Bitcoin:**

Bitcoin ordena las TXs por **fee/byte** — el minero selecciona las más rentables. En este demo no hay fees, por lo que FIFO es suficiente.

---

### `remove_transactions`

```python
def remove_transactions(self, tx_hashes: List[str]):
    self.mempool = [
        tx for tx in self.mempool
        if tx.hash() not in tx_hashes
    ]
```

Elimina TXs del mempool que ya fueron confirmadas en un bloque. Se llama después de agregar un bloque exitosamente para limpiar TXs ya procesadas.

---

## Sección: Minado

### `mine_block`

```python
def mine_block(self, miner_address: str) -> Optional[Block]:
    return self.mine_block_cancellable(miner_address, stop_event=None)
```

Alias bloqueante de `mine_block_cancellable`. Útil para tests y uso directo sin red. No puede interrumpirse — corre hasta encontrar el nonce.

---

### `mine_block_cancellable`

```python
def mine_block_cancellable(
    self,
    miner_address: str,
    stop_event: Optional[threading.Event] = None,
) -> Optional[Block]:
```

**¿Qué hace?**

Ejecuta el proceso completo de minado de un bloque con soporte de cancelación via `threading.Event`.

**Proceso completo:**

```
1. Crear TX coinbase (recompensa del minero)
        │
        ▼
2. Seleccionar TXs del mempool (FIFO)
        │
        ▼
3. Calcular Merkle root de [coinbase] + pending_txs
        │
        ▼
4. Crear BlockHeader con prev_hash del tip actual
        │
        ▼
5. ProofOfWork.mine(stop_event)
   ← aquí se gasta tiempo: probar nonce=0,1,2,...
   ← si stop_event.is_set() → retornar None (cancelado)
        │
        ▼
6. Si nonce es None → minado cancelado, retornar None
        │
        ▼
7. Crear Block con header (nonce encontrado) + TXs
        │
        ▼
8. add_block(block) → validar y agregar a chain
        │
        ▼
9. Retornar bloque (o None si validación falla)
```

**¿Por qué `stop_event` es un `threading.Event`?**

El PoW corre en un thread separado del executor (no bloquea el event loop de asyncio). Cuando llega un bloque externo válido, el event loop de asyncio activa el `stop_event`. El thread del PoW verifica `stop_event.is_set()` en cada iteración y retorna `None` limpiamente.

```
asyncio event loop (thread principal)
    │
    ├── WebSocket ← bloque externo recibido
    │       │
    │       └── handle_block() → _cancel_current_mining()
    │                                   │
    │                               stop_event.set()
    │
    └── executor thread (PoW)
            │
            └── while True:
                    if stop_event.is_set():
                        return None  ← cancelado limpiamente
                    # probar siguiente nonce
```

---

## Sección: Validación

### `add_block`

```python
def add_block(self, block: Block) -> bool:
    if not self.validate_block(block):
        return False
    self.chain.append(block)
    confirmed_hashes = [tx.hash() for tx in block.transactions]
    self.remove_transactions(confirmed_hashes)
    return True
```

**¿Qué hace?**

Valida y agrega un bloque a la cadena. Si la validación falla, retorna False sin modificar el estado. Si tiene éxito, agrega el bloque y limpia el mempool.

**¿Por qué limpiar el mempool después de agregar?**

Las TXs del bloque ya están confirmadas — mantenerlas en el mempool causaría intentos de doble gasto en el siguiente bloque.

---

### `validate_block`

```python
def validate_block(self, block: Block) -> bool:
```

Ejecuta seis validaciones en orden. Si alguna falla, retorna False inmediatamente sin continuar.

| Validación | Protege contra |
|-----------|---------------|
| `validate_pow()` | Bloques sin trabajo computacional real |
| `validate_merkle_root()` | TXs modificadas después del minado |
| `prev_hash == latest.hash` | Bloques que no conectan con la cadena actual |
| `timestamp <= now + 7200` | Bloques con timestamp futuro |
| `transactions[0].from_address == "COINBASE"` | Bloques sin recompensa o con recompensa falsa |
| `validate_transactions()` | TXs con firmas inválidas |

---

### `validate_chain`

```python
def validate_chain(self, chain: List[Block]) -> bool:
```

**¿Qué hace?**

Valida una cadena completa de bloques — usada durante la sincronización cuando se recibe una cadena de otro nodo. Verifica:

1. El bloque génesis coincide con el nuestro
2. Cada bloque conecta con el anterior (`prev_hash`)
3. Cada bloque cumple PoW
4. Cada bloque tiene Merkle root válido
5. Cada bloque tiene TXs válidas

**¿Por qué verificar el génesis primero?**

Si el génesis es diferente, los dos nodos están en redes completamente distintas y no tiene sentido continuar la validación.

---

## Sección: Longest Chain Rule

### `replace_chain`

```python
def replace_chain(self, new_chain: List[Block]) -> bool:
```

**¿Qué hace?**

Implementa la regla de consenso principal de Bitcoin: si existe una cadena válida más larga que la nuestra, la adoptamos. Este es el mecanismo que resuelve los forks.

**Proceso:**

```
nueva_cadena recibida
        │
        ▼
¿len(nueva) > len(actual)?  → No: rechazar (la nuestra es más larga)
        │
        ▼
¿validate_chain(nueva)?     → No: rechazar (inválida)
        │
        ▼
Encontrar fork_point (primer bloque que difiere)
        │
        ▼
Recuperar TXs huérfanas (bloques descartados → vuelven al mempool)
        │
        ▼
Reemplazar chain = nueva_cadena
        │
        ▼
Limpiar del mempool TXs ya confirmadas en la nueva cadena
        │
        ▼
Retornar True (reemplazada exitosamente)
```

**¿Qué son las TXs huérfanas?**

Cuando adoptamos una cadena más larga, descartamos algunos de nuestros bloques. Las TXs en esos bloques descartados vuelven al mempool para ser incluidas en futuros bloques — de lo contrario se perderían.

```
Nuestra cadena:  G → A → B → C
Cadena externa:  G → A → B → D → E → F

Fork point: bloque B (el siguiente difiere: C vs D)
Bloques descartados: [C]
TXs huérfanas en C → vuelven al mempool (si no están en D,E,F)
```

**Diferencia con Bitcoin:**

Bitcoin usa "trabajo acumulado" (suma de difficulty de todos los bloques) en lugar de longitud. En este demo la difficulty es fija para todos los nodos, por lo que longitud y trabajo acumulado son equivalentes.

---

### `_find_fork_point`

```python
def _find_fork_point(self, other_chain: List[Block]) -> int:
    min_len = min(len(self.chain), len(other_chain))
    for i in range(min_len):
        if self.chain[i].hash != other_chain[i].hash:
            return i
    return min_len
```

**¿Qué hace?**

Encuentra el índice donde dos cadenas divergen. Compara bloque por bloque desde el génesis hasta encontrar el primero que difiere.

```
Cadena A: G → 1 → 2 → 3 → 4A → 5A
Cadena B: G → 1 → 2 → 3 → 4B → 5B → 6B

G==G ✅, 1==1 ✅, 2==2 ✅, 3==3 ✅, 4A≠4B ← fork_point = 4
```

---

## Sección: Serialización

### `get_chain_as_dicts` y `chain_from_dicts`

```python
def get_chain_as_dicts(self) -> List[dict]:
    return [block.to_dict() for block in self.chain]

@staticmethod
def chain_from_dicts(data: List[dict]) -> List[Block]:
    return [Block.from_dict(d) for d in data]
```

**¿Para qué se usan?**

Para transmitir la cadena completa por la red durante la sincronización. Cuando un nodo nuevo se conecta o detecta que está desfasado, solicita la cadena completa al peer con `MSG_GETBLOCKS`. El peer responde con la cadena serializada en JSON.

**Flujo de sincronización:**

```
Nodo nuevo (altura=1)                Nodo existente (altura=50)
        │                                      │
        │── MSG_GETBLOCKS ──────────────────────►│
        │                                      │
        │                           get_chain_as_dicts()
        │                                      │
        │◄─── MSG_BLOCK (full_chain) ──────────│
        │                                      │
chain_from_dicts()
        │
replace_chain(nueva_cadena)
        │
Altura: 50 ✅
```

---

## Flujo Completo: Del Mempool al Bloque Confirmado

```python
# 1. TX llega al nodo (del usuario o de la red)
tx = Transaction(from_addr, to_addr, amount)
tx.sign(wallet)
blockchain.add_transaction_to_mempool(tx)

# 2. Minero selecciona TXs
pending = blockchain.get_transactions_for_mining()  # FIFO

# 3. Minar con soporte de cancelación
stop_event = threading.Event()
block = blockchain.mine_block_cancellable(miner_address, stop_event)

# 4. Si se encontró un bloque externo durante el minado
if block is None:
    # stop_event fue activado por un bloque externo
    # mine_block_cancellable ya retornó None limpiamente
    # reiniciar el minado con el nuevo prev_hash
    pass

# 5. Si el bloque es propio
if block:
    # ya fue agregado a chain por add_block()
    # mempool ya fue limpiado
    # propagarlo a la red
    await node.broadcast_block(block)
```

---

## Tests Asociados

### `tests/test_blockchain.py`

| Test | Función que prueba | Qué verifica |
|------|-------------------|--------------|
| `test_genesis_block_created` | `create_genesis_block` | Génesis existe al crear Blockchain |
| `test_genesis_hash_is_deterministic` | `create_genesis_block` | Todos los nodos tienen el mismo génesis |
| `test_mine_block` | `mine_block` | Bloque minado cumple difficulty |
| `test_mine_block_increases_height` | `mine_block` + `get_height` | Altura aumenta con cada bloque |
| `test_get_balance_after_mining` | `get_balance` | Minero recibe BLOCK_REWARD |
| `test_transaction_in_mempool` | `add_transaction_to_mempool` | TX válida se agrega |
| `test_reject_insufficient_balance` | `add_transaction_to_mempool` | TX sin fondos es rechazada |
| `test_reject_invalid_signature` | `add_transaction_to_mempool` | TX con firma inválida es rechazada |
| `test_reject_duplicate_tx` | `add_transaction_to_mempool` | TX duplicada es rechazada |
| `test_tx_confirmed_in_block` | `mine_block` | TX del mempool aparece en bloque |
| `test_mempool_cleared_after_mining` | `mine_block` | Mempool se limpia al minar |
| `test_balance_after_transfer` | `get_balance` | Balance refleja TXs confirmadas |
| `test_validate_block` | `validate_block` | Bloque válido retorna True |
| `test_reject_invalid_pow` | `validate_block` | Hash sin ceros suficientes rechazado |

### `tests/test_blockchain_chain.py`

| Test | Función que prueba | Qué verifica |
|------|-------------------|--------------|
| `test_replace_chain_longer` | `replace_chain` | Cadena más larga reemplaza a la actual |
| `test_reject_shorter_chain` | `replace_chain` | Cadena más corta es rechazada |
| `test_reject_invalid_chain` | `replace_chain` | Cadena inválida es rechazada |
| `test_orphaned_txs_return_to_mempool` | `replace_chain` | TXs huérfanas vuelven al mempool |
| `test_chain_serialization` | `get_chain_as_dicts` / `chain_from_dicts` | Serialización es reversible |
| `test_find_fork_point` | `_find_fork_point` | Detecta correctamente el punto de fork |
| `test_get_height` | `get_height` | Altura es número de bloques |
| `test_get_block_by_hash` | `get_block_by_hash` | Encuentra bloque existente |
| `test_get_block_by_hash_not_found` | `get_block_by_hash` | Retorna None si no existe |

---

*Documento: `DOC_core_blockchain.md` — Demo Blockchain*
