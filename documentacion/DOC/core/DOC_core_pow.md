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
| Target | Número de 256 bits | Número de 256 bits ✅ (idéntico) |
| Ajuste de difficulty | Cada 2016 bloques (~2 semanas) | Cada `DIFFICULTY_ADJUSTMENT_INTERVAL` bloques (5 por defecto) |
| Objetivo de tiempo | ~10 minutos por bloque | `TARGET_BLOCK_TIME` (180s por defecto) |
| Nonce | 32 bits (0 a 4,294,967,295) | Entero sin límite (int Python) |
| Recompensa | Coinbase TX (subsidy + fees) | Coinbase TX (`BLOCK_REWARD` fijo, sin fees) |
| Hardware | ASICs especializados | CPU (demo educativo) |

**El target en este demo:** Igual que en Bitcoin, el target es un entero de 256 bits guardado en `header.target`. Un bloque es válido si `int(hash, 16) < target` — cuanto más pequeño el target, más difícil encontrar un hash válido. No se usa un esquema de "prefijo de ceros"; ese fue un diseño de una versión anterior del proyecto, reemplazado en el Sprint 9.2 por el target numérico real para que el demo refleje fielmente el mecanismo de Bitcoin.

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

Encapsula toda la lógica de minado: buscar el nonce correcto y validar que un nonce encontrado efectivamente produce un hash menor al target requerido.

**Atributos de instancia:**

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `header` | `BlockHeader` | Objeto del header del bloque a minar. Su `nonce` se modifica durante el proceso |
| `target` | `int` | Entero de 256 bits — el bloque es válido si `int(hash, 16) < target` |

**Relación entre target y esfuerzo computacional:**

```
target = MAX_TARGET // 1,500,000   → P(éxito) ≈ 1/1,500,000 por intento → ~1.5M intentos esperados
target = MAX_TARGET // 500,000     → P(éxito) ≈ 1/500,000   por intento → ~500K  intentos esperados
target = MAX_TARGET // 100,000     → P(éxito) ≈ 1/100,000   por intento → ~100K  intentos esperados
```

Cuanto menor el target (más cerca de 0), menor la probabilidad de éxito por intento y mayor el trabajo esperado. La relación es inversamente proporcional: `P(éxito) = target / MAX_TARGET`.

---

## Función `__init__`

```python
def __init__(self, block_header, target: int):
    self.header = block_header
    self.target = target
```

**¿Qué hace?**

Inicializa el solver de PoW, almacena la referencia al header del bloque y el `target` numérico contra el cual se compararán los hashes generados.

**Proceso:**

```
block_header  ─────────────────────────►  self.header
target (int, 256 bits)  ────────────────►  self.target
```

**¿Por qué guardar una referencia al header y no una copia?**

El método `mine()` necesita mutar el campo `nonce` del header en cada iteración. Al guardar referencia, los cambios se reflejan directamente en el objeto original, lo que permite que el header quede con el nonce correcto al finalizar el minado, listo para ser incluido en el bloque.

**En Bitcoin:** El proceso es equivalente. El minero modifica el campo `nonce` del block header (4 bytes) en cada intento de hash.

---

## Función `mine`

```python
def mine(self, stop_event=None, progress_callback=None) -> Optional[int]:
    nonce = 0
    start_time = time.time()

    print(f"[MINING] Iniciando minado (target={hex(self.target)[2:18]}...)...")

    while True:
        if stop_event is not None and stop_event.is_set():
            print("[MINING] Cancelado externamente")
            return None

        self.header.nonce = nonce
        block_hash = self.header.hash()

        if int(block_hash, 16) < self.target:
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
            if progress_callback:
                progress_callback(nonce, rate)
```

**¿Qué hace?**

Ejecuta el bucle de minado: prueba nonces de forma secuencial (0, 1, 2, …) hasta encontrar uno cuyo hash, interpretado como entero, sea menor al `target`.

**Proceso detallado:**

```
nonce = 0
    │
    ▼
¿stop_event activado?  ──► SÍ ──► return None (minado cancelado)
    │
    NO
    ▼
header.nonce ← nonce           ← Inyecta nonce en el header
    │
    ▼
block_hash = header.hash()     ← Calcula SHA256(SHA256(header))
    │
    ▼
¿int(block_hash, 16) < target?
    │
    ├── SÍ ──► Imprimir stats → return nonce ✅
    │
    └── NO ──► nonce += 1 → repetir
```

**Ejemplo con un target de demo:**

```
Intento 0:    hash = "a3f2c1d8..." → int(hash,16) >= target → siguiente
Intento 1:    hash = "7b9e4f2a..." → int(hash,16) >= target → siguiente
...
Intento 4127: hash = "000bc4f7..." → int(hash,16) <  target → ¡MINADO! ✅
```

**¿Por qué el bucle es determinístico?**

Dado un header con los mismos valores (`prev_hash`, `merkle_root`, `timestamp`, `target`), el hash para cada nonce siempre será el mismo. Esto hace que el proceso sea reproducible: el mismo header encontrará siempre el mismo nonce ganador.

**El logging cada 10,000 intentos:**

Sirve como feedback visual durante el desarrollo y para medir la tasa de hashes/segundo de la máquina. También alimenta `progress_callback`, usado por el dashboard para mostrar el progreso de minado en tiempo real. En producción (Bitcoin), los miners tienen dashboards completos mostrando GH/s o TH/s en tiempo real.

**¿Por qué `stop_event`?**

Permite cancelar el minado en curso cuando llega un bloque externo válido desde otro nodo de la red — evita seguir minando un bloque que ya quedó obsoleto. Es el mecanismo que usa `mine_block_cancellable()` en `blockchain.py`.

**¿Por qué `nonce` empieza en 0 y no en un valor aleatorio?**

Para determinismo en el demo. Bitcoin permite que el nonce empiece en cualquier punto, y muchos miners aleatorizan el punto de inicio para evitar que múltiples miners trabajen en la misma secuencia simultáneamente.

---

## Función `validate`

```python
def validate(self, nonce: int) -> bool:
    self.header.nonce = nonce
    block_hash = self.header.hash()
    return int(block_hash, 16) < self.target
```

**¿Qué hace?**

Verifica que un nonce dado produce un hash menor al target. Es el mecanismo de verificación que usan los demás nodos al recibir un bloque minado — equivalente a `Block.validate_pow()`.

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
int(block_hash, 16) < target   ← True si válido, False si no
```

**Asimetría fundamental del PoW:**

```
MINAR:    O(n) trabajo esperado     → miles/millones de intentos hasta encontrar
VALIDAR:  O(1) trabajo              → un solo hash para verificar
```

Esta asimetría es el pilar del sistema. Minar es difícil; verificar es trivial. Cualquier nodo puede confirmar en microsegundos que un bloque fue minado correctamente, sin repetir todo el trabajo.

**En Bitcoin:** Los nodos completos validan cada bloque recibido exactamente con este proceso: aplican el nonce al header, calculan el double SHA256 y verifican que el resultado, interpretado como número, sea menor al target vigente.

**Efectos secundarios importantes:**

La función modifica `self.header.nonce` como efecto secundario. Esto no es un problema cuando se llama después de `mine()` (ya tiene el nonce correcto), pero hay que tenerlo en cuenta si se valida un nonce diferente al que tiene el header en ese momento.

---

## Función `__repr__`

```python
def __repr__(self):
    return f"ProofOfWork(target={hex(self.target)[2:18]}...)"
```

**¿Qué hace?**

Define la representación en texto del objeto. Muestra el target (abreviado en hex) para identificación rápida durante debugging.

**Ejemplo:**

```python
pow_solver = ProofOfWork(header, target=CURRENT_TARGET)
print(pow_solver)
# → ProofOfWork(target=00000a3f2c1d8e9b...)
```

---

## El Algoritmo de Hash: Double SHA256

Tanto `mine()` como `validate()` delegan el cálculo del hash al método `header.hash()`. En el `BlockHeader` real, el proceso es:

```python
def hash(self):
    import hashlib, json
    data = {
        'prev_hash':   self.prev_hash,
        'merkle_root': self.merkle_root,
        'timestamp':   self.timestamp,
        'target':      self.target,
        'nonce':       self.nonce,    # ← Único campo que cambia en cada intento
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
| `target` | No | Target vigente al momento de minar el bloque |

El **nonce es la única variable de control del miner**. Todos los demás campos están fijos al empezar a minar. El `target` no afecta la búsqueda del nonce en sí — solo define el umbral contra el cual se compara cada hash.

**¿Qué ocurre si se agotan todos los nonces?**

En Bitcoin, el nonce es de 32 bits (0 a 4,294,967,295). Con hardware moderno, esto se agota en milisegundos. La solución real de Bitcoin es modificar el campo `timestamp` (extranonce) o el campo `coinbase` de la transacción de recompensa para "refrescar" el espacio de búsqueda. Este demo usa enteros Python de tamaño ilimitado, por lo que el agotamiento no es un problema.

---

## Diferencias Clave con Bitcoin Real

| Aspecto | Bitcoin Real | Este Demo | ¿Afecta concepto? |
|---------|--------------|-----------|-------------------|
| Representación del target | Número de 256 bits (campo `bits`) | Número de 256 bits (campo `target`) | ❌ No (idéntico) |
| Ajuste de difficulty | Automático cada 2016 bloques | Automático cada `DIFFICULTY_ADJUSTMENT_INTERVAL` bloques | ❌ No (mismo mecanismo, escala distinta) |
| Límite del nonce | 32 bits (overflow → usa extranonce) | Sin límite (int Python) | ❌ No |
| Algoritmo de hash | Double SHA256 del header binario | Double SHA256 del header JSON | Mínimo |
| Paralelismo | Múltiples cores/ASICs en paralelo | Un solo hilo | ❌ No (demo educativo) |
| Recompensa por bloque | Coinbase TX (subsidy + fees) | Coinbase TX (`BLOCK_REWARD` fijo, sin fees) | Menor |

**Conclusión:** El algoritmo central (buscar nonce tal que `int(SHA256(SHA256(header)), 16) < target`) es idéntico a Bitcoin, incluyendo el ajuste dinámico de dificultad. Las diferencias restantes son de escala y características de producción (paralelismo, fees, tamaño del nonce) que no afectan la comprensión del concepto.

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
Nodo A encuentra nonce válido (trabajó ~3 min de cómputo en este demo)
Nodo B también encuentra nonce válido (trabajó ~3 min de cómputo en este demo)
→ Red acumula la cadena con más trabajo total (regla de la cadena más larga)
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
    target=blockchain.CURRENT_TARGET,
    nonce=0,
)

# 2. Crear el solver de PoW
pow_solver = ProofOfWork(header, target=blockchain.CURRENT_TARGET)
# → ProofOfWork(target=00000a3f2c1d8e9b...)

# 3. Minar (puede tardar varios segundos a varios minutos)
nonce = pow_solver.mine()
# [MINING] Iniciando minado (target=00000a3f2c1d8e9b...)...
# [MINING] Intentos: 10,000 (42,371 hashes/s)
# [MINED] ¡Bloque minado!
#         Nonce: 73842
#         Hash: 00000a3f2c1d8e9b47c6d5e4f3c2b1a09...
#         Tiempo: 1.74s
#         Intentos: 73,843

# 4. El header ahora tiene el nonce correcto
assert int(header.hash(), 16) < blockchain.CURRENT_TARGET

# 5. Otros nodos validan el bloque recibido
validator = ProofOfWork(received_header, target=received_header.target)
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
│ target:      00000a3f2c1d8e9b... (256 bits)         │
│ nonce:       ← VARIABLE (0, 1, 2, ...)              │
└─────────────────────────────────────────────────────┘
         │ nonce=0             │ nonce=1
         ▼                     ▼
SHA256(SHA256(...))     SHA256(SHA256(...))
= int(...) >= target    = int(...) >= target
  ← NO cumple             ← NO cumple
                                          ...
         │ nonce=73842
         ▼
SHA256(SHA256(...))
= int(...) < target
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
    target=blockchain.CURRENT_TARGET,
)

pow_solver = ProofOfWork(header, target=blockchain.CURRENT_TARGET)
nonce = pow_solver.mine()

# Crear bloque con nonce encontrado
new_block = Block(header=header, transactions=txs)
blockchain.add_block(new_block)
```

**2. Validación al recibir bloque de otro nodo:**

```python
def on_receive_block(block):
    # Verificar PoW
    pow_validator = ProofOfWork(block.header, target=block.header.target)
    if not pow_validator.validate(block.header.nonce):
        raise InvalidBlockError("PoW inválido: el hash no es menor al target")

    # Continuar con otras validaciones (Merkle root, firmas de TXs, etc.)
    ...
```

---

## Ajuste Dinámico de Difficulty (implementado)

A diferencia de versiones anteriores del proyecto, el ajuste de dificultad **ya está implementado** y vive en `blockchain.py`, no en `pow.py`. `ProofOfWork` no conoce el historial de bloques — solo recibe el `target` vigente en cada llamada. Es `Blockchain._maybe_adjust_target()` quien decide ese target:

```python
ratio = actual_time / expected_time
ratio = max(1/MAX_ADJUSTMENT_FACTOR, min(MAX_ADJUSTMENT_FACTOR, ratio))
new_target = int(old_target * ratio)
```

Cada `DIFFICULTY_ADJUSTMENT_INTERVAL` bloques (5 por defecto) se compara el tiempo real transcurrido contra `TARGET_BLOCK_TIME * DIFFICULTY_ADJUSTMENT_INTERVAL`. El ajuste está acotado a `MAX_ADJUSTMENT_FACTOR` (×4 o ÷4 por ciclo, igual que Bitcoin) y nunca excede `MAX_TARGET` ni baja de 1. Ver `DOC_core_blockchain.md` para el detalle completo de `_maybe_adjust_target()` y `_recompute_target_from_chain()`.

---

## Tests Asociados: `tests/test_pow.py`

| Test | Función que prueba | Qué verifica |
|------|-------------------|--------------|
| `test_pow_mine_easy_target` | `mine` | Mina exitosamente con un target permisivo en <10s |
| `test_pow_mine_moderate_target` | `mine` | Mina exitosamente con un target intermedio en <30s |
| `test_pow_validate_correct_nonce` | `validate` | El nonce encontrado por `mine()` pasa validación |
| `test_pow_validate_incorrect_nonce` | `validate` | Nonce arbitrario no válido es rechazado |
| `test_pow_deterministic` | `mine` | Mismo header → mismo nonce ganador |
| `test_pow_different_header_different_nonce` | `mine` | Headers distintos → nonces distintos |
| `test_pow_hash_below_target` | `mine` + `validate` | Hash resultante, como entero, es menor al target |
| `test_pow_smaller_target_still_valid` | `validate` | Un target más permisivo también acepta el nonce |
| `test_pow_cancellable` | `mine` | `stop_event` activado interrumpe el minado y retorna `None` |

---

*Documento: `DOC_core_pow.md` — Demo Blockchain (corregido para reflejar Sprint 9.2: target numérico de 256 bits)*
