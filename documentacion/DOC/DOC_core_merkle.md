# Documentación Técnica: `core/merkle.py`

---

## Propósito del Archivo

`merkle.py` implementa un **Merkle Tree** (Árbol de Merkle), una estructura de datos criptográfica que permite resumir eficientemente un conjunto de transacciones en un solo hash (el **Merkle root**).

**Analogía:** Un Merkle Tree es como un árbol genealógico de hashes donde:
- Las **hojas** son los hashes de las transacciones individuales
- Los **nodos padres** combinan los hashes de sus hijos
- La **raíz** (Merkle root) es el hash único que representa TODAS las transacciones

**¿Por qué es fundamental para blockchain?**

El Merkle root permite:
1. **Verificar integridad**: Si cambias UNA transacción, el Merkle root cambia completamente
2. **Almacenamiento eficiente**: Solo necesitas guardar el root (32 bytes) en el block header
3. **Verificación ligera (SPV)**: Puedes probar que una TX está en un bloque sin descargar todas las TXs

---

## Merkle Trees en Bitcoin vs Este Demo

| Aspecto | Bitcoin Real | Este Demo |
|---------|--------------|-----------|
| Algoritmo de hash | Double SHA256 | Double SHA256 ✅ (idéntico) |
| Número impar de hojas | Duplica la última | Duplica la última ✅ (idéntico) |
| Orden de concatenación | left + right | left + right ✅ (idéntico) |
| Serialización de TX | Formato binario complejo | JSON determinístico |
| Merkle proofs (SPV) | Sí, obligatorio | Sí, implementado |
| Uso del root | En block header | En block header ✅ (idéntico) |

**Diferencia principal:** Bitcoin serializa transacciones en formato binario (más eficiente), mientras que este demo usa JSON con `sort_keys=True` para determinismo. El **concepto y algoritmo** son idénticos.

---

## Dependencias

```python
import hashlib
import json
from typing import List, Optional
```

| Import | Propósito |
|--------|-----------|
| `hashlib` | SHA256 para calcular hashes de transacciones y nodos |
| `json` | Serializar transacciones a string determinístico |
| `typing` | Type hints para mejor documentación del código |

---

## Clase `MerkleTree`

```python
class MerkleTree:
```

Representa un árbol binario de hashes donde cada nivel combina pares de hashes hasta llegar a un solo hash raíz (Merkle root).

**Atributos de instancia:**

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `transactions` | `List[Transaction]` | Lista de transacciones del bloque |
| `tree` | `List[List[str]]` | Árbol completo: `tree[0]` = hojas, `tree[-1]` = raíz |

**Estructura visual del árbol con 4 transacciones:**

```
         Root (H1234)
              │
      ┌───────┴───────┐
      │               │
    H12             H34
      │               │
   ┌──┴──┐         ┌──┴──┐
   │     │         │     │
  H1    H2        H3    H4
   │     │         │     │
  TX1   TX2       TX3   TX4
```

Donde:
- `H1 = SHA256(SHA256(TX1))`
- `H12 = SHA256(SHA256(H1 + H2))`
- `Root = SHA256(SHA256(H12 + H34))`

---

## Función `__init__`

```python
def __init__(self, transactions: List):
    self.transactions = transactions
    self.tree = self.build_tree()
```

**¿Qué hace?**

Inicializa el árbol Merkle construyendo inmediatamente todos los niveles desde las hojas hasta la raíz.

**Proceso:**

```
transactions (lista de objetos Transaction)
        │
        ▼
build_tree()  →  Construye árbol completo
        │
        ▼
self.tree = [[H1,H2,H3,H4], [H12,H34], [Root]]
```

**¿Por qué construir el árbol inmediatamente?**

En blockchain, el Merkle root se necesita de inmediato para:
- Incluirlo en el block header
- Calcular el hash del bloque (que depende del Merkle root)
- Permitir verificaciones rápidas sin recalcular

**En Bitcoin:** El proceso es idéntico. Cada bloque construye su Merkle tree una vez y guarda el root en el header.

---

## Función `hash_transaction`

```python
def hash_transaction(self, tx) -> str:
    tx_dict = tx.to_dict(include_signature=False)
    tx_string = json.dumps(tx_dict, sort_keys=True)
    
    hash1 = hashlib.sha256(tx_string.encode()).digest()
    hash2 = hashlib.sha256(hash1).hexdigest()
    
    return hash2
```

**¿Qué hace?**

Calcula el hash de una transacción usando **double SHA256**, el mismo algoritmo que Bitcoin.

**Proceso paso a paso:**

```
Transaction (objeto)
        │
        ▼
to_dict(include_signature=False)  →  dict sin firma
        │
        ▼
json.dumps(sort_keys=True)  →  string determinístico
        │
        ▼
.encode('utf-8')  →  bytes
        │
        ▼
SHA256  →  32 bytes
        │
        ▼
SHA256  →  32 bytes
        │
        ▼
.hexdigest()  →  64 caracteres hex
```

**¿Por qué `include_signature=False`?**

La firma NO se incluye en el hash del Merkle tree porque:
1. La firma ya firmó el `tx_id` (que incluye todos los datos de la TX)
2. Incluir la firma crearía circularidad: `firma = sign(hash(TX + firma))`
3. Bitcoin hace lo mismo: el `txid` se calcula sin incluir las firmas (SegWit)

**¿Por qué double SHA256?**

Bitcoin usa double SHA256 en todos sus hashes por razones históricas de seguridad:
```
SHA256(SHA256(data))
```

Esto protege contra ataques de extensión de longitud (length extension attacks) que afectan a SHA256 simple. Aunque en la práctica moderna es innecesario, Bitcoin lo adoptó en 2009 y se convirtió en estándar.

**Ejemplo:**

```python
# TX: {"from": "Alice", "to": "Bob", "amount": 10, "timestamp": 1707234567}
# JSON: '{"amount":10,"from":"Alice","timestamp":1707234567,"to":"Bob"}'
# SHA256: b'...' (32 bytes binarios)
# SHA256(SHA256): "a3f2c1d8e9b47c6d5e4f3c2b1a098765..." (64 chars hex)
```

**¿Por qué `sort_keys=True`?**

Garantiza que el mismo diccionario siempre produzca el mismo JSON string:

```python
# Sin sort_keys (orden arbitrario):
json.dumps({"amount": 10, "from": "Alice"})  # → '{"amount":10,"from":"Alice"}'
json.dumps({"from": "Alice", "amount": 10})  # → '{"from":"Alice","amount":10}'
# ❌ Mismo contenido, strings diferentes → hashes diferentes

# Con sort_keys=True (orden alfabético):
json.dumps({"amount": 10, "from": "Alice"}, sort_keys=True)  # → '{"amount":10,"from":"Alice"}'
json.dumps({"from": "Alice", "amount": 10}, sort_keys=True)  # → '{"amount":10,"from":"Alice"}'
# ✅ Mismo contenido → mismo string → mismo hash
```

---

## Función `build_tree`

```python
def build_tree(self) -> List[List[str]]:
    if not self.transactions:
        return [['0' * 64]]
    
    current_level = [self.hash_transaction(tx) for tx in self.transactions]
    tree = [current_level.copy()]
    
    while len(current_level) > 1:
        if len(current_level) % 2 != 0:
            current_level.append(current_level[-1])
        
        next_level = []
        for i in range(0, len(current_level), 2):
            combined = current_level[i] + current_level[i + 1]
            
            hash1 = hashlib.sha256(combined.encode()).digest()
            parent_hash = hashlib.sha256(hash1).hexdigest()
            
            next_level.append(parent_hash)
        
        tree.append(next_level)
        current_level = next_level
    
    return tree
```

**¿Qué hace?**

Construye el árbol completo de Merkle combinando hashes en pares hasta llegar a un solo hash raíz.

**Proceso detallado con 4 transacciones:**

```
Paso 1 - Crear nivel 0 (hojas):
[TX1, TX2, TX3, TX4]
    │
    ▼ hash_transaction() cada una
[H1, H2, H3, H4]  ← tree[0]

Paso 2 - Verificar paridad:
len([H1, H2, H3, H4]) = 4  → par ✅ (no duplicar)

Paso 3 - Combinar pares:
H1 + H2 → SHA256(SHA256("H1H2")) → H12
H3 + H4 → SHA256(SHA256("H3H4")) → H34

Nivel 1: [H12, H34]  ← tree[1]

Paso 4 - Verificar paridad:
len([H12, H34]) = 2  → par ✅ (no duplicar)

Paso 5 - Combinar pares:
H12 + H34 → SHA256(SHA256("H12H34")) → Root

Nivel 2: [Root]  ← tree[2]

Paso 6 - Terminar:
len([Root]) = 1  → STOP (raíz alcanzada)

Resultado:
tree = [
    [H1, H2, H3, H4],    # Nivel 0: hojas
    [H12, H34],          # Nivel 1: nodos intermedios
    [Root]               # Nivel 2: raíz
]
```

**Caso especial: número impar de transacciones**

```
Ejemplo con 3 transacciones:

Paso 1 - Hojas:
[H1, H2, H3]  ← tree[0]

Paso 2 - Verificar paridad:
len([H1, H2, H3]) = 3  → impar ❌

Paso 3 - Duplicar última:
[H1, H2, H3, H3]  ← H3 duplicado

Paso 4 - Combinar pares:
H1 + H2 → H12
H3 + H3 → H33  ← nodo con hijo duplicado

Nivel 1: [H12, H33]  ← tree[1]

Paso 5 - Combinar pares:
H12 + H33 → Root

Nivel 2: [Root]  ← tree[2]
```

**¿Por qué duplicar la última hoja?**

Bitcoin adoptó esta convención para mantener la estructura de árbol binario completo sin nodos huérfanos. Alternativas rechazadas:

| Alternativa | Por qué NO se usa |
|-------------|-------------------|
| Dejar huérfano | Rompe la estructura binaria |
| Agregar hash de ceros | Cambiaría el root si agregas TXs |
| Combinar con nodo padre | Complica la verificación |
| **Duplicar última hoja** | ✅ Simple, determinístico, preserva binario |

**Caso especial: bloque vacío**

```python
if not self.transactions:
    return [['0' * 64]]
```

Sin transacciones, retorna un hash de 64 ceros. Esto nunca ocurre en Bitcoin real (siempre hay al menos la coinbase TX), pero en un demo es posible.

**¿Por qué `current_level.copy()` al crear el árbol?**

```python
tree = [current_level.copy()]  # ✅ CORRECTO
```

Si usas:
```python
tree = [current_level]  # ❌ INCORRECTO
```

Cuando modificas `current_level` más adelante (al duplicar hojas), también modificas `tree[0]` porque apuntan a la misma lista en memoria.

**Complejidad algorítmica:**

```
n = número de transacciones
Niveles del árbol = log₂(n)
Nodos totales = 2n - 1

Ejemplo:
n=4  → 3 niveles, 7 nodos
n=8  → 4 niveles, 15 nodos
n=16 → 5 niveles, 31 nodos
```

---

## Función `get_root`

```python
def get_root(self) -> str:
    return self.tree[-1][0]
```

**¿Qué hace?**

Retorna el **Merkle root**, que es el único hash del último nivel del árbol.

**Proceso:**

```
tree = [
    [H1, H2, H3, H4],  # tree[0]
    [H12, H34],        # tree[1]
    [Root]             # tree[2] ← tree[-1]
]

tree[-1]     →  [Root]      # Último nivel
tree[-1][0]  →  Root        # Primer (y único) elemento
```

**¿Por qué el Merkle root es tan importante?**

El Merkle root se almacena en el **block header** y es fundamental para:

1. **Integridad del bloque:**
```
Si cambias: TX2 → TX2'
Entonces:   H2 → H2'
           H12 → H12'
           Root → Root'

❌ El bloque es inválido (root no coincide con el registrado)
```

2. **Hash del bloque:**
```
block_hash = SHA256(SHA256(
    version +
    prev_block_hash +
    merkle_root +      ← Root depende de TODAS las TXs
    timestamp +
    difficulty +
    nonce
))
```

3. **Verificación ligera (SPV):**

Un nodo ligero solo descarga block headers (80 bytes por bloque). Para verificar si una TX está en un bloque, el nodo:
- Solicita la TX + Merkle proof (~300-400 bytes)
- Recalcula el camino hasta la raíz
- Compara con el `merkle_root` del header

**En Bitcoin:**

El block header es exactamente 80 bytes:
```
4 bytes   - version
32 bytes  - prev_block_hash
32 bytes  - merkle_root          ← aquí va get_root()
4 bytes   - timestamp
4 bytes   - difficulty (bits)
4 bytes   - nonce
---------
80 bytes total
```

---

## Función `get_proof`

```python
def get_proof(self, tx_index: int) -> Optional[List[dict]]:
    if tx_index < 0 or tx_index >= len(self.transactions):
        return None
    
    proof = []
    index = tx_index
    
    for level_index in range(len(self.tree) - 1):
        level = self.tree[level_index]
        
        if index % 2 == 0:
            sibling_index = index + 1
            position = 'right'
        else:
            sibling_index = index - 1
            position = 'left'
        
        if sibling_index < len(level):
            proof.append({
                'hash': level[sibling_index],
                'position': position
            })
        
        index = index // 2
    
    return proof
```

**¿Qué hace?**

Genera una **prueba Merkle** (Merkle proof) que permite verificar que una transacción está en el bloque sin necesidad de tener todas las transacciones.

**¿Qué es una prueba Merkle?**

Una lista de hashes hermanos (siblings) necesarios para reconstruir el camino desde una hoja hasta la raíz.

**Ejemplo visual con 4 transacciones (verificando TX1 en índice 0):**

```
         Root
           │
      ┌────┴────┐
      │         │
    H12       H34  ← Necesito H34 (hermano de H12)
      │         
   ┌──┴──┐      
   │     │      
  H1    H2  ← Necesito H2 (hermano de H1)
   │     
  TX1  ← Empiezo aquí (índice 0)
```

**Prueba generada:**
```python
proof = [
    {'hash': 'H2',  'position': 'right'},  # Nivel 0: H2 está a la derecha de H1
    {'hash': 'H34', 'position': 'right'}   # Nivel 1: H34 está a la derecha de H12
]
```

**Proceso paso a paso:**

```
Verificar TX1 (índice 0):

Nivel 0 (hojas):
    index = 0 (TX1)
    0 % 2 == 0  →  par → hermano a la DERECHA
    sibling_index = 0 + 1 = 1 (H2)
    proof.append({'hash': H2, 'position': 'right'})
    index = 0 // 2 = 0  (subir al nivel 1)

Nivel 1:
    index = 0 (H12)
    0 % 2 == 0  →  par → hermano a la DERECHA
    sibling_index = 0 + 1 = 1 (H34)
    proof.append({'hash': H34, 'position': 'right'})
    index = 0 // 2 = 0  (subir al nivel 2)

Nivel 2 (raíz):
    for termina (len(self.tree) - 1 = 2 niveles)

Resultado:
proof = [
    {'hash': H2, 'position': 'right'},
    {'hash': H34, 'position': 'right'}
]
```

**Otro ejemplo: verificar TX2 (índice 1):**

```
         Root
           │
      ┌────┴────┐
      │         │
    H12       H34  ← Necesito H34
      │         
   ┌──┴──┐      
   │     │      
  H1    H2  ← TX2 está aquí, necesito H1
        │
       TX2  ← Índice 1
```

**Prueba generada:**
```python
proof = [
    {'hash': 'H1',  'position': 'left'},   # H1 está a la izquierda de H2
    {'hash': 'H34', 'position': 'right'}   # H34 está a la derecha de H12
]
```

**Proceso:**

```
Nivel 0:
    index = 1 (TX2)
    1 % 2 == 1  →  impar → hermano a la IZQUIERDA
    sibling_index = 1 - 1 = 0 (H1)
    proof.append({'hash': H1, 'position': 'left'})
    index = 1 // 2 = 0  (subir)

Nivel 1:
    index = 0 (H12)
    0 % 2 == 0  →  par → hermano a la DERECHA
    sibling_index = 0 + 1 = 1 (H34)
    proof.append({'hash': H34, 'position': 'right'})
```

**¿Por qué se guarda la posición ('left' o 'right')?**

El orden de concatenación importa al calcular hashes:

```python
# Caso: hermano a la DERECHA
combined = H1 + H2  →  "H1H2"

# Caso: hermano a la IZQUIERDA
combined = H1 + H2  →  "H1H2"

# Si no sabes el orden:
SHA256("H1H2") ≠ SHA256("H2H1")  ❌
```

La posición indica cómo concatenar:
- `'right'` → `current + sibling`
- `'left'` → `sibling + current`

**Eficiencia de las pruebas Merkle:**

```
n = número de transacciones
Tamaño de prueba = log₂(n) hashes

Ejemplos:
100 TXs     → ~7 hashes (~224 bytes)
1,000 TXs   → ~10 hashes (~320 bytes)
10,000 TXs  → ~13 hashes (~416 bytes)

vs descargar todas las TXs:
10,000 TXs × 250 bytes promedio = 2.5 MB

Ahorro: 416 bytes vs 2.5 MB  →  99.98% menos datos
```

**En Bitcoin (SPV - Simplified Payment Verification):**

Los wallets ligeros (como móviles) usan Merkle proofs para verificar transacciones:

1. Descarga solo block headers (80 bytes × ~850,000 bloques = ~68 MB)
2. Para verificar una TX, solicita: TX + prueba Merkle (~400 bytes)
3. Recalcula el root y compara con el header
4. Ahorro vs nodo completo: ~400 bytes vs ~500 GB

---

## Función estática `verify_proof`

```python
@staticmethod
def verify_proof(tx_hash: str, merkle_root: str, proof: List[dict]) -> bool:
    current_hash = tx_hash
    
    for step in proof:
        sibling_hash = step['hash']
        position = step['position']
        
        if position == 'left':
            combined = sibling_hash + current_hash
        else:  # 'right'
            combined = current_hash + sibling_hash
        
        hash1 = hashlib.sha256(combined.encode()).digest()
        current_hash = hashlib.sha256(hash1).hexdigest()
    
    return current_hash == merkle_root
```

**¿Qué hace?**

Verifica que una transacción está en el árbol Merkle usando solo el hash de la TX, el Merkle root y la prueba.

**¿Por qué es `@staticmethod`?**

No necesita acceso a `self` porque solo necesita:
- El hash de la TX a verificar
- El Merkle root (del block header)
- La prueba Merkle

Cualquier nodo puede verificar sin tener el árbol completo ni las transacciones.

**Proceso de verificación para TX1 (índice 0):**

```
Entrada:
    tx_hash = H1
    merkle_root = Root
    proof = [
        {'hash': H2,  'position': 'right'},
        {'hash': H34, 'position': 'right'}
    ]

Paso 1 - Nivel 0:
    current_hash = H1
    sibling_hash = H2
    position = 'right'
    
    combined = H1 + H2  (porque hermano está a la derecha)
    current_hash = SHA256(SHA256("H1H2"))  →  H12

Paso 2 - Nivel 1:
    current_hash = H12
    sibling_hash = H34
    position = 'right'
    
    combined = H12 + H34
    current_hash = SHA256(SHA256("H12H34"))  →  Root'

Paso 3 - Verificar:
    Root' == Root  →  True ✅
```

**Ejemplo con TX modificada (fraude):**

```
Atacante intenta colar TX1' (modificada):

Paso 1:
    current_hash = H1'  ← hash diferente
    combined = H1' + H2
    current_hash = SHA256(SHA256("H1'H2"))  →  H12'  ← diferente

Paso 2:
    current_hash = H12'
    combined = H12' + H34
    current_hash = SHA256(SHA256("H12'H34"))  →  Root''  ← diferente

Paso 3:
    Root'' ≠ Root  →  False ❌  (fraude detectado)
```

**Propiedades de seguridad:**

1. **Resistencia a colisiones:** Computacionalmente imposible encontrar `TX1' ≠ TX1` tal que `Hash(TX1') = Hash(TX1)`

2. **Efecto avalancha:** Cambiar un bit en TX1 → cambia completamente H1 → cambia H12 → cambia Root

3. **Resistencia a preimagen:** Conocer `Root` no revela información sobre las TXs

**Casos que retornan `False`:**

| Caso | Por qué falla |
|------|---------------|
| TX modificada | Hash diferente → camino diferente → root diferente |
| Prueba incorrecta | Hashes de hermanos no coinciden |
| Prueba de otra TX | Camino correcto para otra TX, incorrecto para esta |
| Root incorrecto | Root no corresponde a este árbol |

---

## Función `__repr__`

```python
def __repr__(self):
    return f"MerkleTree(transactions={len(self.transactions)}, root={self.get_root()[:16]}...)"
```

**¿Qué hace?**

Define cómo se muestra el objeto al imprimirlo. Muestra el número de transacciones y los primeros 16 caracteres del Merkle root.

**Ejemplo:**

```python
txs = [create_dummy_tx(i) for i in range(4)]
merkle = MerkleTree(txs)
print(merkle)
# → MerkleTree(transactions=4, root=a3f2c1d8e9b47c6d...)
```

---

## Diferencias Clave con Bitcoin Real

| Aspecto | Bitcoin Real | Este Demo | ¿Afecta concepto? |
|---------|--------------|-----------|-------------------|
| Serialización TX | Formato binario optimizado | JSON con `sort_keys=True` | ❌ No |
| Algoritmo hash | Double SHA256 | Double SHA256 | ✅ Idéntico |
| Número impar | Duplica última | Duplica última | ✅ Idéntico |
| Orden concatenación | left + right | left + right | ✅ Idéntico |
| Tamaño de prueba | ~log₂(n) hashes | ~log₂(n) hashes | ✅ Idéntico |
| Uso en header | Sí, siempre | Sí, siempre | ✅ Idéntico |

**Conclusión:** El algoritmo y concepto son idénticos. La única diferencia es cómo se serializan las transacciones antes de hashearlas (binario vs JSON), pero el proceso de construcción del árbol y las pruebas Merkle funcionan exactamente igual.

---

## Por Qué Bitcoin Usa Merkle Trees

**Problema que resuelve:**

Sin Merkle trees, para verificar que una TX está en un bloque necesitas:
1. Descargar TODAS las transacciones del bloque (~2,000-3,000 TXs)
2. Verificar cada firma (~100ms × 2,000 = 3+ minutos)
3. Almacenar todo (~1-2 MB por bloque)

**Solución con Merkle trees:**

1. Descarga solo el block header (80 bytes)
2. Solicita TX + prueba Merkle (~400 bytes)
3. Verifica el camino al root (~1ms)
4. Ahorro: 99.98% menos datos

**Ventajas adicionales:**

| Ventaja | Descripción |
|---------|-------------|
| **Integridad** | Cambiar 1 TX invalida el bloque completo |
| **Eficiencia** | Verificación O(log n) vs O(n) |
| **SPV wallets** | Wallets móviles sin descargar blockchain |
| **Pruning** | Nodos pueden borrar TXs antiguas, guardar solo headers |
| **Fraud proofs** | Probar que un bloque es inválido con prueba compacta |

---

## Casos de Uso en Blockchain

**1. Validación de bloques:**

```python
# Minero crea bloque:
block = Block(...)
block.merkle_root = MerkleTree(block.transactions).get_root()
block.hash = block.calculate_hash()  # Usa merkle_root

# Nodo valida:
calculated_root = MerkleTree(block.transactions).get_root()
if calculated_root != block.merkle_root:
    raise InvalidBlockError("Merkle root no coincide")
```

**2. SPV (Simplified Payment Verification):**

```python
# Wallet ligero verifica si recibió pago:
tx_hash = hash_transaction(my_tx)
proof = full_node.get_merkle_proof(block_id, tx_hash)
merkle_root = block_header.merkle_root

if MerkleTree.verify_proof(tx_hash, merkle_root, proof):
    print("Pago confirmado ✅")
else:
    print("Pago no está en el bloque ❌")
```

**3. Fraud proofs (pruebas de fraude):**

Si un minero incluye una TX inválida, puedes probar el fraude con:
- La TX inválida
- Prueba Merkle de que está en el bloque
- Razón por la que es inválida (firma incorrecta, doble gasto, etc.)

Total: ~500-1000 bytes vs descargar todo el bloque.

---

## Flujo Completo de Uso

```python
# 1. Crear transacciones
tx1 = Transaction("Alice", "Bob", 10)
tx2 = Transaction("Bob", "Charlie", 5)
tx3 = Transaction("Charlie", "Dave", 3)
tx4 = Transaction("Dave", "Alice", 2)

# 2. Construir árbol Merkle
merkle = MerkleTree([tx1, tx2, tx3, tx4])
# → Construye árbol: [[H1,H2,H3,H4], [H12,H34], [Root]]

# 3. Obtener Merkle root (para block header)
merkle_root = merkle.get_root()
# → "a3f2c1d8e9b47c6d5e4f3c2b1a098765..." (64 chars)

# 4. Incluir en bloque
block = Block(
    transactions=[tx1, tx2, tx3, tx4],
    merkle_root=merkle_root,  ← va al header
    prev_hash=...,
    timestamp=...
)

# 5. Generar prueba para verificación ligera
proof_tx1 = merkle.get_proof(0)  # Prueba para tx1 (índice 0)
# → [
#     {'hash': 'H2', 'position': 'right'},
#     {'hash': 'H34', 'position': 'right'}
#   ]

# 6. Nodo ligero verifica (sin descargar todas las TXs)
tx1_hash = merkle.hash_transaction(tx1)
is_valid = MerkleTree.verify_proof(tx1_hash, merkle_root, proof_tx1)
# → True ✅

# 7. Intentar fraude (modificar TX)
tx1_fake = Transaction("Alice", "Attacker", 999999)  # TX fraudulenta
tx1_fake_hash = merkle.hash_transaction(tx1_fake)
is_valid = MerkleTree.verify_proof(tx1_fake_hash, merkle_root, proof_tx1)
# → False ❌ (fraude detectado)
```

---

## Visualización Completa del Proceso

**Árbol con 8 transacciones:**

```
                    Root (H12345678)
                         │
            ┌────────────┴────────────┐
            │                         │
        H1234                     H5678
            │                         │
      ┌─────┴─────┐           ┌─────┴─────┐
      │           │           │           │
    H12         H34         H56         H78
      │           │           │           │
   ┌──┴──┐     ┌──┴──┐     ┌──┴──┐     ┌──┴──┐
   │     │     │     │     │     │     │     │
  H1    H2    H3    H4    H5    H6    H7    H8
   │     │     │     │     │     │     │     │
  TX1   TX2   TX3   TX4   TX5   TX6   TX7   TX8
```

**Prueba Merkle para TX5 (índice 4):**

```
Camino desde TX5 hasta Root:
TX5 (índice 4)
   │
   ▼ (hermano: H6, position: right)
  H5 + H6 → H56
   │
   ▼ (hermano: H78, position: right)
  H56 + H78 → H5678
   │
   ▼ (hermano: H1234, position: left)
  H1234 + H5678 → Root

Prueba:
[
    {'hash': 'H6', 'position': 'right'},     # Nivel 0
    {'hash': 'H78', 'position': 'right'},    # Nivel 1
    {'hash': 'H1234', 'position': 'left'}    # Nivel 2
]

Tamaño: 3 hashes × 32 bytes = 96 bytes
vs descargar 8 TXs × 250 bytes = 2,000 bytes
Ahorro: 95.2%
```

---

## Tests Asociados: `tests/test_merkle.py`

| Test | Función que prueba | Qué verifica |
|------|-------------------|--------------|
| `test_merkle_root_single_transaction` | `get_root` | Root existe y tiene 64 chars (SHA256) |
| `test_merkle_root_deterministic` | `build_tree`, `get_root` | Mismo input → mismo output |
| `test_merkle_root_changes_with_data` | `build_tree` | Cambiar TXs → cambia root |
| `test_merkle_odd_number_of_transactions` | `build_tree` | Duplica última con número impar |
| `test_merkle_even_number_of_transactions` | `build_tree` | Funciona con número par |
| `test_merkle_empty_transactions` | `build_tree` | Lista vacía → hash de ceros |
| `test_merkle_tree_structure` | `build_tree` | Niveles correctos del árbol |
| `test_merkle_order_matters` | `build_tree` | Orden diferente → root diferente |
| `test_merkle_proof_generation` | `get_proof` | Genera prueba válida |
| `test_merkle_proof_verification` | `verify_proof` | Prueba válida verifica correctamente |
| `test_merkle_proof_invalid` | `verify_proof` | TX falsa no verifica |

---

## Mejoras Futuras (Opcionales)

**1. Optimización de memoria:**

Actualmente se guarda todo el árbol. Bitcoin solo guarda las transacciones y calcula el root cuando se necesita.

```python
# Actual:
self.tree = [[H1,H2,H3,H4], [H12,H34], [Root]]  # Guarda todos los niveles

# Optimizado:
def get_root_optimized(self):
    # Calcula solo el root sin guardar niveles intermedios
    # Ahorro: O(n) espacio vs O(2n) actual
```

**2. Merkle Patricia Tree (Ethereum):**

Ethereum usa una variante más compleja que permite:
- Búsquedas eficientes por clave
- Actualizaciones incrementales
- Pruebas de existencia y no-existencia

**3. Compresión de pruebas:**

Para bloques muy grandes, las pruebas pueden comprimirse usando técnicas como:
- Bloom filters
- Accumuladores criptográficos
- zk-SNARKs (pruebas de conocimiento cero)

---

*Documento: `DOC_core_merkle.md` — Demo Blockchain Fase 2.2*
