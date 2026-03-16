# Documentación Técnica: `core/pow.py`

---

## Propósito del Archivo

`pow.py` implementa el algoritmo de **Proof of Work (PoW)**, el mecanismo de consenso que hace que minar un bloque requiera trabajo computacional real. Es el corazón del sistema de seguridad de Bitcoin.

**Analogía:** Proof of Work es como buscar una llave específica entre millones de llaves idénticas por fuera. No hay atajo: hay que probar una por una hasta encontrar la que abre la cerradura. Pero una vez encontrada, cualquiera puede verificarla instantáneamente.

**¿Por qué es fundamental para blockchain?**

El PoW cumple tres funciones críticas:

1. **Seguridad económica:** Reescribir la historia de la blockchain requeriría repetir todo el trabajo computacional de los bloques anteriores, haciendo el ataque prohibitivamente costoso
2. **Consenso descentralizado:** Sin autoridad central, el PoW permite que todos los nodos acuerden cuál es la cadena válida (la cadena más larga/más trabajo acumulado)
3. **Emisión controlada:** El minado es el único mecanismo para introducir nuevas monedas al sistema (recompensa de bloque)

---

## Proof of Work en Bitcoin vs Este Demo

| Aspecto | Bitcoin Real | Este Demo |
|---------|--------------|-----------|
| Algoritmo de hash | Double SHA256 | Double SHA256 ✅ (idéntico) |
| Target | Número de 256 bits | Prefijo de ceros (simplificado) |
| Ajuste de difficulty | Cada 2016 bloques (~2 semanas) | Fija por instancia |
| Objetivo de tiempo | ~10 minutos por bloque | Sin objetivo temporal |
| Nonce | 32 bits (0 a 4,294,967,295) | Entero sin límite (int Python) |
| Recompensa | Coinbase TX (subsidy + fees) | No implementada aún |
| Hardware | ASICs especializados | CPU (demo educativo) |

**Diferencia principal en el target:** Bitcoin define la difficulty como un número de 256 bits; si el hash interpretado como número es menor al target, el bloque es válido. Este demo simplifica eso a contar ceros al inicio del hash hex, lo cual es conceptualmente equivalente y mucho más legible.

---

## Dependencias

```python
import hashlib
import json
import time
```

| Import | Propósito |
|--------|-----------|
| `hashlib` | SHA256 para validación interna (el hash real lo calcula `block_header`) |
| `json` | Serialización en el `MockBlockHeader` de los tests |
| `time` | Medir el tiempo de minado y calcular la tasa de hashes/segundo |

---

## Clase `ProofOfWork`

```python
class ProofOfWork:
```

Encapsula toda la lógica de minado: buscar el nonce correcto y validar que un nonce encontrado efectivamente cumple la difficulty requerida.

**Atributos de instancia:**

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `header` | `BlockHeader` | Objeto del header del bloque a minar. Su `nonce` se modifica durante el proceso |
| `difficulty` | `int` | Número de ceros hexadecimales requeridos al inicio del hash |
| `target` | `str` | String de ceros objetivo. Ejemplo: `"0000"` para difficulty 4 |

**Relación entre difficulty y esfuerzo computacional:**

```
Difficulty 3  → target "000..."    → P(éxito) = 1/4,096       → ~4K   intentos
Difficulty 4  → target "0000..."   → P(éxito) = 1/65,536      → ~65K  intentos
Difficulty 5  → target "00000..."  → P(éxito) = 1/1,048,576   → ~1M   intentos
Difficulty 6  → target "000000..." → P(éxito) = 1/16,777,216  → ~16M  intentos
```

Cada nivel de difficulty multiplica el trabajo esperado por 16 (base hexadecimal).

---

## Función `__init__`

```python
def __init__(self, block_header, difficulty: int = 4):
    self.header = block_header
    self.difficulty = difficulty
    self.target = '0' * difficulty
```

**¿Qué hace?**

Inicializa el solver de PoW, almacena la referencia al header del bloque y precalcula el `target` string que deberá ser prefijo del hash válido.

**Proceso:**

```
block_header  ─────────────────────────►  self.header
difficulty (int)  ──────────────────────►  self.difficulty
'0' * difficulty  ──────────────────────►  self.target
                                           Ej: difficulty=4 → "0000"
```

**¿Por qué guardar una referencia al header y no una copia?**

El método `mine()` necesita mutar el campo `nonce` del header en cada iteración. Al guardar referencia, los cambios se reflejan directamente en el objeto original, lo que permite que el header quede con el nonce correcto al finalizar el minado, listo para ser incluido en el bloque.

**En Bitcoin:** El proceso es equivalente. El minero modifica el campo `nonce` del block header (4 bytes) en cada intento de hash.

---

## Función `mine`

```python
def mine(self) -> int:
    nonce = 0
    start_time = time.time()

    print(f"[MINING] Iniciando minado (difficulty={self.difficulty})...")

    while True:
        self.header.nonce = nonce
        block_hash = self.header.hash()

        if block_hash.startswith(self.target):
            elapsed = time.time() - start_time
            print(f"[MINED] ¡Bloque minado!")
            print(f"        Nonce: {nonce}")
            print(f"        Hash: {block_hash}")
            print(f"        Tiempo: {elapsed:.2f}s")
            print(f"        Intentos: {nonce + 1:,}")
            return nonce

        nonce += 1

        if nonce > 0 and nonce % 10000 == 0:
            elapsed = time.time() - start_time
            rate = nonce / elapsed if elapsed > 0 else 0
            print(f"[MINING] Intentos: {nonce:,} ({rate:,.0f} hashes/s)")
```

**¿Qué hace?**

Ejecuta el bucle de minado: prueba nonces de forma secuencial (0, 1, 2, …) hasta encontrar uno cuyo hash cumpla la difficulty.

**Proceso detallado:**

```
nonce = 0
    │
    ▼
header.nonce ← nonce           ← Inyecta nonce en el header
    │
    ▼
block_hash = header.hash()     ← Calcula SHA256(SHA256(header))
    │
    ▼
¿hash.startswith(target)?
    │
    ├── SÍ ──► Imprimir stats → return nonce ✅
    │
    └── NO ──► nonce += 1 → repetir
```

**Ejemplo con difficulty=3:**

```
Intento 0:    hash = "a3f2c1d8..." → NO empieza con "000" → siguiente
Intento 1:    hash = "7b9e4f2a..." → NO empieza con "000" → siguiente
...
Intento 4127: hash = "000bc4f7..." → SÍ empieza con "000" → ¡MINADO! ✅
```

**¿Por qué el bucle es determinístico?**

Dado un header con los mismos valores (prev_hash, merkle_root, timestamp, difficulty), el hash para cada nonce siempre será el mismo. Esto hace que el proceso sea reproducible: el mismo header encontrará siempre el mismo nonce ganador.

**El logging cada 10,000 intentos:**

Sirve como feedback visual durante el desarrollo y para medir la tasa de hashes/segundo de la máquina. En producción (Bitcoin), los miners tienen dashboards completos mostrando GH/s o TH/s en tiempo real.

**¿Por qué `nonce` empieza en 0 y no en un valor aleatorio?**

Para determinismo en el demo. Bitcoin permite que el nonce empiece en cualquier punto, y muchos miners aleatorizan el punto de inicio para evitar que múltiples miners trabajen en la misma secuencia simultáneamente.

---

## Función `validate`

```python
def validate(self, nonce: int) -> bool:
    self.header.nonce = nonce
    block_hash = self.header.hash()
    return block_hash.startswith(self.target)
```

**¿Qué hace?**

Verifica que un nonce dado produce un hash que cumple la difficulty. Es el mecanismo de verificación que usan los demás nodos al recibir un bloque minado.

**Proceso:**

```
nonce (int)
    │
    ▼
header.nonce ← nonce           ← Reconstruye el estado del header
    │
    ▼
block_hash = header.hash()     ← Recalcula el hash
    │
    ▼
hash.startswith(target)        ← True si válido, False si no
```

**Asimetría fundamental del PoW:**

```
MINAR:    O(n) trabajo esperado     → miles de intentos hasta encontrar
VALIDAR:  O(1) trabajo              → un solo hash para verificar
```

Esta asimetría es el pilar del sistema. Minar es difícil; verificar es trivial. Cualquier nodo puede confirmar en microsegundos que un bloque fue minado correctamente, sin repetir todo el trabajo.

**En Bitcoin:** Los nodos completos validan cada bloque recibido exactamente con este proceso: aplican el nonce al header, calculan el double SHA256 y verifican que el resultado sea menor al target de difficulty actual.

**Efectos secundarios importantes:**

La función modifica `self.header.nonce` como efecto secundario. Esto no es un problema cuando se llama después de `mine()` (ya tiene el nonce correcto), pero hay que tenerlo en cuenta si se valida un nonce diferente al que tiene el header en ese momento.

---

## Función `__repr__`

```python
def __repr__(self):
    return f"ProofOfWork(difficulty={self.difficulty}, target={self.target})"
```

**¿Qué hace?**

Define la representación en texto del objeto. Muestra la difficulty y el target para identificación rápida durante debugging.

**Ejemplo:**

```python
pow_solver = ProofOfWork(header, difficulty=4)
print(pow_solver)
# → ProofOfWork(difficulty=4, target=0000)
```

---

## El Algoritmo de Hash: Double SHA256

Tanto `mine()` como `validate()` delegan el cálculo del hash al método `header.hash()`. En `MockBlockHeader` (usado en tests) y en el `BlockHeader` real, el proceso es:

```python
def hash(self):
    import hashlib, json
    data = {
        'prev_hash': self.prev_hash,
        'merkle_root': self.merkle_root,
        'timestamp': self.timestamp,
        'nonce': self.nonce,          # ← Único campo que cambia en cada intento
        'difficulty': self.difficulty
    }
    header_str = json.dumps(data, sort_keys=True)
    hash1 = hashlib.sha256(header_str.encode()).digest()
    hash2 = hashlib.sha256(hash1).hexdigest()
    return hash2
```

**Campos del header que afectan el hash:**

| Campo | ¿Cambia durante minado? | Descripción |
|-------|------------------------|-------------|
| `prev_hash` | No | Hash del bloque anterior (encadenamiento) |
| `merkle_root` | No | Resumen de todas las transacciones del bloque |
| `timestamp` | No | Momento de creación del bloque |
| `nonce` | **Sí** | La única variable que el miner controla |
| `difficulty` | No | Nivel de dificultad actual |

El **nonce es la única variable de control del miner**. Todos los demás campos están fijos al empezar a minar.

**¿Qué ocurre si se agotan todos los nonces?**

En Bitcoin, el nonce es de 32 bits (0 a 4,294,967,295). Con hardware moderno, esto se agota en milisegundos. La solución real de Bitcoin es modificar el campo `timestamp` (extranonce) o el campo `coinbase` de la transacción de recompensa para "refrescar" el espacio de búsqueda. Este demo usa enteros Python de tamaño ilimitado, por lo que el agotamiento no es un problema.

---

## Diferencias Clave con Bitcoin Real

| Aspecto | Bitcoin Real | Este Demo | ¿Afecta concepto? |
|---------|--------------|-----------|-------------------|
| Representación del target | Número de 256 bits (campo `bits`) | Prefijo de ceros en hex | ❌ No (equivalente) |
| Ajuste de difficulty | Automático cada 2016 bloques | Manual por instancia | ❌ No (fuera del scope) |
| Límite del nonce | 32 bits (overflow → usa extranonce) | Sin límite (int Python) | ❌ No |
| Algoritmo de hash | Double SHA256 del header binario | Double SHA256 del header JSON | Mínimo |
| Paralelismo | Múltiples cores/ASICs en paralelo | Un solo hilo | ❌ No (demo educativo) |
| Recompensa por bloque | Coinbase TX (subsidy + fees) | No implementada | Medio (fase futura) |

**Conclusión:** El algoritmo central (buscar nonce tal que SHA256(SHA256(header)) cumpla el target) es idéntico. Las diferencias son de representación, escala y características de producción que no afectan la comprensión del concepto.

---

## Por Qué Bitcoin Usa Proof of Work

**El problema que resuelve:** En una red descentralizada sin autoridad central, ¿quién tiene derecho a añadir el siguiente bloque?

**Sin PoW (problemático):**

```
Nodo A propone bloque con TX "Alice → Bob"
Nodo B propone bloque con TX "Alice → Charlie"  ← double spend
¿A quién le creemos?
```

No hay forma de decidir sin una autoridad central. Cualquiera puede proponer bloques falsos sin costo.

**Con PoW (solución):**

```
Nodo A encuentra nonce válido (trabajó ~10 min de cómputo)
Nodo B también encuentra nonce válido (trabajó ~10 min de cómputo)
→ Red acumula la cadena con más trabajo total (regla de la cadena más pesada)
→ Atacante necesitaría >50% del poder de cómputo total de la red para reescribir historia
```

**Las tres propiedades clave del PoW:**

| Propiedad | Descripción |
|-----------|-------------|
| **Costoso de producir** | Requiere trabajo computacional real (electricidad, hardware) |
| **Fácil de verificar** | Cualquier nodo verifica un bloque en microsegundos |
| **Infalsificable** | No hay atajo matemático; solo fuerza bruta |

---

## Flujo Completo de Uso

```python
# 1. Construir el header del bloque
header = BlockHeader(
    prev_hash="000abc...",      # Hash del bloque anterior
    merkle_root="a3f2c1...",    # Merkle root de las transacciones
    timestamp=1707234567,
    difficulty=4
)

# 2. Crear el solver de PoW
pow_solver = ProofOfWork(header, difficulty=4)
# → ProofOfWork(difficulty=4, target=0000)

# 3. Minar (puede tardar varios segundos)
nonce = pow_solver.mine()
# [MINING] Iniciando minado (difficulty=4)...
# [MINING] Intentos: 10,000 (42,371 hashes/s)
# [MINED] ¡Bloque minado!
#         Nonce: 73842
#         Hash: 0000a3f2c1d8e9b47c6d5e4f3c2b1a09...
#         Tiempo: 1.74s
#         Intentos: 73,843

# 4. El header ahora tiene el nonce correcto
assert header.hash().startswith('0000')

# 5. Otros nodos validan el bloque recibido
validator = ProofOfWork(received_header, difficulty=4)
is_valid = validator.validate(received_header.nonce)
# → True ✅ (verificación instantánea)
```

---

## Visualización del Proceso de Minado

```
BlockHeader (fijo durante minado):
┌─────────────────────────────────────────────────────┐
│ prev_hash:   "000abc4f7d..."                        │
│ merkle_root: "a3f2c1d8..."                          │
│ timestamp:   1707234567                             │
│ difficulty:  4                                      │
│ nonce:       ← VARIABLE (0, 1, 2, ...)             │
└─────────────────────────────────────────────────────┘
         │ nonce=0             │ nonce=1
         ▼                     ▼
SHA256(SHA256(...))     SHA256(SHA256(...))
= "a3f2c1d8..."         = "7b9e4f2a..."
  ← NO cumple            ← NO cumple
                                          ...
         │ nonce=73842
         ▼
SHA256(SHA256(...))
= "0000a3f2c1d8..."
  ← ¡SÍ CUMPLE! → return 73842 ✅
```

---

## Casos de Uso en Blockchain

**1. Minado de un nuevo bloque:**

```python
# Miner recoge transacciones del mempool
txs = mempool.get_pending_transactions()
merkle_root = MerkleTree(txs).get_root()

header = BlockHeader(
    prev_hash=blockchain.last_block_hash(),
    merkle_root=merkle_root,
    timestamp=time.time(),
    difficulty=blockchain.current_difficulty()
)

pow_solver = ProofOfWork(header, difficulty=header.difficulty)
nonce = pow_solver.mine()

# Crear bloque con nonce encontrado
new_block = Block(header=header, transactions=txs)
blockchain.add_block(new_block)
```

**2. Validación al recibir bloque de otro nodo:**

```python
def on_receive_block(block):
    # Verificar PoW
    pow_validator = ProofOfWork(block.header, difficulty=block.header.difficulty)
    if not pow_validator.validate(block.header.nonce):
        raise InvalidBlockError("PoW inválido: el nonce no cumple la difficulty")
    
    # Continuar con otras validaciones (Merkle root, firmas de TXs, etc.)
    ...
```

---

## Tests Asociados: `tests/test_pow.py`

| Test | Función que prueba | Qué verifica |
|------|-------------------|--------------|
| `test_pow_difficulty_3` | `mine` | Mina exitosamente con difficulty 3 en <10s |
| `test_pow_difficulty_4` | `mine` | Mina exitosamente con difficulty 4 en <30s |
| `test_pow_validate_correct_nonce` | `validate` | El nonce encontrado por `mine()` pasa validación |
| `test_pow_validate_incorrect_nonce` | `validate` | Nonce arbitrario no válido es rechazado |
| `test_pow_deterministic` | `mine` | Mismo header → mismo nonce ganador |
| `test_pow_different_header_different_nonce` | `mine` | Headers distintos → nonces distintos |
| `test_pow_hash_has_enough_zeros` | `mine` + `validate` | Hash resultante tiene al menos `difficulty` ceros |
| `test_pow_more_zeros_than_minimum_still_valid` | `validate` | Difficulty menor también acepta el nonce |

---

## Mejoras Futuras

**1. Ajuste dinámico de difficulty:**

Bitcoin ajusta la difficulty cada 2016 bloques para mantener ~10 minutos por bloque.

```python
def adjust_difficulty(blockchain):
    last_2016_blocks = blockchain.get_last_n_blocks(2016)
    actual_time = last_2016_blocks[-1].timestamp - last_2016_blocks[0].timestamp
    target_time = 2016 * 10 * 60  # 2016 bloques × 10 min × 60 seg

    ratio = actual_time / target_time
    ratio = max(0.25, min(4.0, ratio))  # Límite: ×4 o ÷4 por ajuste

    new_difficulty = current_difficulty / ratio
    return new_difficulty
```

**2. Paralelismo:**

```python
import concurrent.futures

def mine_parallel(header, difficulty, num_workers=4):
    chunk_size = 100_000
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(mine_range, header, difficulty, i * chunk_size, (i+1) * chunk_size)
            for i in range(num_workers)
        ]
        # El primero que encuentre un nonce válido gana
```

**3. Recompensa de bloque (Coinbase):**

```python
def create_coinbase_tx(miner_address, block_height):
    subsidy = 50 * (0.5 ** (block_height // 210000))  # Halvings cada 210,000 bloques
    return Transaction("coinbase", miner_address, subsidy)
```

---

*Documento: `DOC_core_pow.md` — Demo Blockchain Fase 2.3*
