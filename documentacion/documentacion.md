# Documento Técnico de Arquitectura
## Demo Blockchain - MT
---

## 1. Visión General

Este proyecto es un demo educativo de blockchain tipo Bitcoin implementado en Python. Demuestra los principios fundamentales de una red descentralizada: peer-to-peer, propagación de mensajes, criptografía, firmas digitales y validación de transacciones.

### Estado Actual del Proyecto

**Proyecto completo. Todas las fases implementadas:**

- Red P2P con WebSockets y gossip protocol
- Wallets Ed25519 y transacciones firmadas
- Merkle Trees (árbol completo + Merkle root)
- Bloques y Blockchain con encadenamiento por hash
- Proof of Work (SHA-256, dificultad ajustable automáticamente)
- Propagación P2P de bloques y sincronización entre nodos
- Detección y resolución de forks (regla de cadena más larga)
- Seed Node para descubrimiento de peers en LAN
- Orquestador de transacciones automáticas
- Dashboard Web por nodo (Flask + JS)
- Dashboard Global del instructor (vista unificada de toda la red)
- Launchers para modo local (manual y auto) y modo LAN
- Scripts de setup automático para laboratorio (PowerShell)
- Suite de tests completa (11 archivos, 38+ tests)

### Objetivos

- Replicar la arquitectura P2P de Bitcoin a pequeña escala
- Demostrar descubrimiento de peers mediante seed node y gossip protocol
- Implementar firmas digitales con EdDSA (Ed25519)
- Proporcionar interfaz gráfica por nodo y vista global del instructor
- Demostrar minado con Proof of Work, bloques encadenados y consenso
- Operar en red LAN real con múltiples máquinas simultáneas

### Stack Tecnológico

| Componente | Tecnología | Razón |
|------------|------------|-------|
| Lenguaje | Python 3.11 | Legibilidad, librerías criptográficas |
| Red | asyncio + websockets | Conexiones persistentes bidireccionales |
| Criptografía | cryptography (Ed25519) | EdDSA moderno, seguro y eficiente |
| Dashboard | Flask + Vanilla JS | Servidor web simple, sin dependencias frontend |
| Testing | pytest + pytest-asyncio | Framework estándar de Python |
| Entorno | venv | Aislamiento de dependencias |

---

## 2. Decisiones de Diseño

### 2.1 WebSockets en lugar de TCP puro

**Decisión:** Usar WebSockets para comunicación P2P.

**Razón:** Bitcoin usa TCP puro, pero WebSockets proveen:
- Conexiones persistentes bidireccionales (igual que TCP)
- Manejo automático de ping/pong (keep-alive integrado)
- Librería `websockets` en Python maneja reconexión y errores
- Suficiente para demostrar los conceptos sin implementar TCP manualmente

**Implicación:** El protocolo de mensajes es idéntico conceptualmente a Bitcoin. Solo cambia el transporte subyacente.

---

### 2.2 Identificación de Nodos por Puerto

**Decisión:** `node_id = f"node_{port}"` (ej: `node_5000`)

**Razón:** El puerto es único por nodo, predecible y consistente entre ejecuciones. Para el desarrollo y testing, se generan logs por nodo.

**Resultado:**
```
logs/
├── node_5000.log
├── node_5001.log
└── node_5002.log
```

**Bitcoin real:** Identifica nodos por IP:puerto. Esta decisión es fiel a ese concepto.

---

### 2.3 EdDSA Ed25519 en lugar de ECDSA secp256k1

**Decisión:** Wallets usan EdDSA Ed25519 en lugar de ECDSA secp256k1 (Bitcoin).

**Razón:**

| Aspecto | ECDSA secp256k1 (Bitcoin) | EdDSA Ed25519 (Este demo) |
|---------|---------------------------|---------------------------|
| Velocidad | Baseline | 5-10x más rápido |
| Nonce | Aleatorio (riesgo reuso) | Determinístico (seguro) |
| Timing attacks | Vulnerable sin mitigación | Resistente por diseño |
| Complejidad código | Mayor | Menor |

**Nota importante:** Bitcoin usa ECDSA secp256k1. Este demo usa Ed25519 por ser más moderno, seguro y simple de implementar. Los conceptos fundamentales (firmas digitales, validación, direcciones) son **idénticos**.

**¿Por qué Bitcoin no usa Ed25519?** Ed25519 se publicó en 2011, dos años después de Bitcoin (2009). Satoshi Nakamoto eligió ECDSA secp256k1 por ser el estándar disponible. Bitcoin Core ahora usa RFC 6979 (nonces determinísticos) para mitigar el riesgo de nonce reuse en ECDSA.

---

### 2.4 Arquitectura de Seguridad en Dos Capas

**Decisión:** Diferentes mecanismos de seguridad para mensajes P2P vs transacciones.

```
Capa de Red (P2P)          →  Checksum SHA-256
Capa de Blockchain (TXs)   →  Firma EdDSA Ed25519
```

**Justificación:**

**Mensajes P2P (checksum suficiente):**
- Son anuncios públicos (`ping`, `getaddr`, `inv`)
- No representan valor económico
- No requieren autenticación de identidad
- Bitcoin usa checksum en capa de red

**Transacciones (firma obligatoria):**
- Representan transferencia de valor
- Deben probar propiedad de la wallet
- Un checksum puede ser recalculado por un atacante
- Sin firma ECDSA/EdDSA, cualquiera podría crear TXs falsas

---

### 2.5 Setup.py sin install_requires

**Decisión:** Dependencias en `requirements.txt`, `setup.py` solo registra el paquete.

**Razón:** Elimina duplicación entre archivos. Para proyectos educativos, `requirements.txt` es el estándar más familiar. `setup.py` con `pip install -e .` solo resuelve el problema de importaciones entre módulos del proyecto.

---

## 3. Red P2P

### Arquitectura

Cada nodo actúa simultáneamente como **servidor** (acepta conexiones entrantes) y **cliente** (inicia conexiones salientes). Esta arquitectura simétrica es la base de una red verdaderamente descentralizada.

```
                    ┌─────────────────┐
                    │     Nodo A      │
                    │  ┌───────────┐  │
          ┌─────────┤  │  Servidor │  ├─────────┐
          │         │  │  (escucha)│  │         │
          │         │  └─────┬─────┘  │         │
          │         │        │        │         │
          │         │  ┌─────┴─────┐  │         │
          │         │  │  Cliente  │  │         │
          │         │  │(conecta a)│  │         │
          │         └──┤───────────├──┘         │
          │            └─────┬─────┘            │
          ▼                  │                  ▼
   ┌─────────────┐           │           ┌─────────────┐
   │   Nodo B    │◄──────────┘           │   Nodo C    │
   └─────────────┘                       └─────────────┘
```

### Protocolo de Mensajes

**Formato estándar:**
```json
{
    "type": "message_type",
    "id": "uuid-único",
    "timestamp": 1707234567.123,
    "payload": { ... },
    "checksum": "sha256_del_payload"
}
```

**Tipos de mensajes (Fase 1):**

| Mensaje | Propósito | Payload | Estado |
|---------|-----------|---------|--------|
| `version` | Handshake inicial | `{node_id, version, host, port}` | Activo |
| `verack` | Confirmación de handshake | `{node_id}` | Activo |
| `ping` | Keep-alive | `{nonce}` | Activo |
| `pong` | Respuesta a ping | `{nonce}` | Activo |
| `hello` | Mensaje de prueba | `{data, sender}` | Legado* |

**Nota sobre `hello`:** Este mensaje permanece implementado como referencia de la Fase 1 inicial, pero ya no se utiliza en las fases actuales. La propagación de mensajes ahora se demuestra mediante transacciones. Posteriormente será eliminado.

**Comparación con Bitcoin:**

Bitcoin maneja ~25 tipos de mensajes diferentes para coordinar toda la funcionalidad de la red:

| Categoría | Mensajes Bitcoin | Propósito |
|-----------|------------------|-----------|
| Handshake | `version`, `verack` | Idéntico a este demo |
| Keep-alive | `ping`, `pong` | Idéntico a este demo |
| Peer discovery | `getaddr`, `addr` | Implementado en Fase 1.5 |
| Inventario | `inv`, `getdata` | Anunciar/solicitar objetos (TXs, bloques) |
| Transacciones | `tx`, `mempool`, `getmempool` | Propagación de TXs |
| Bloques | `block`, `getblocks`, `getheaders`, `headers` | Sincronización de blockchain |
| Bloom filters | `filterload`, `filteradd`, `filterclear` | SPV wallets |
| Otros | `reject`, `alert`, `notfound`, `sendheaders` | Control y optimización |

**¿Por qué Bitcoin necesita más mensajes?**
- Sincronización inicial de blockchain (gigabytes de datos)
- Optimización de bandwidth (bloom filters, headers-first)
- Múltiples modos de operación (full node, SPV, pruned node)
- 15 años de evolución y optimizaciones

**¿Por qué este demo necesita menos?**
- Sin blockchain sincronizada todavía (Fase 2.3 pendiente)
- Red pequeña (5 nodos vs miles en Bitcoin)
- Propósito educativo: mostrar conceptos sin complejidad innecesaria
- Se agregarán más tipos en fases futuras (`inv`, `getdata`, `block`)

### Handshake

**Este demo:**
```
Nodo A                          Nodo B
   │                               │
   │──── version {node_id} ────►  │
   │                               │  (verifica, registra peer)
   │◄─── verack {node_id} ────────│
   │                               │
   │  Conexión establecida         │
```

**Bitcoin (idéntico conceptualmente):**
```
Nodo A                          Nodo B
   │                               │
   │──── version ────────────────►│
   │  {version=70015,             │
   │   services=NODE_NETWORK,     │
   │   timestamp=...,             │  (valida versión >= mínima)
   │   addr_recv, addr_from,      │  (verifica servicios soportados)
   │   nonce, user_agent,         │  (registra peer)
   │   start_height}              │
   │                               │
   │◄──── verack ─────────────────│
   │                               │
   │  Conexión establecida         │
   │  (pueden enviarse otros      │
   │   mensajes en paralelo)      │
```

**Diferencias:**
- Bitcoin incluye más metadatos (versión de protocolo, altura de blockchain, servicios soportados)
- Bitcoin valida compatibilidad de versiones (rechaza si muy antigua)
- Este demo simplifica el payload pero mantiene el concepto de handshake bidireccional

### Anti-Loop (messages_seen)

**Este demo:**
```python
# Cada nodo mantiene un set de IDs vistos
messages_seen = set()

# Al recibir mensaje:
if msg_id in messages_seen:
    return  # Ignorar duplicado

messages_seen.add(msg_id)
# ... procesar y reenviar
```

**Bitcoin:**

Bitcoin **NO usa anti-loop genérico de message IDs**. En su lugar, usa estrategias específicas por tipo de dato:

**Para Transacciones:**
```python
# Bitcoin usa mempool como anti-loop
if tx.hash() in mempool_txids:
    return  # Ya tenemos esta TX

mempool.add(tx)
# No re-propaga TXs a quien te la envió (exclude sender)
```

**Para Bloques:**
```python
# Bitcoin usa blockchain como anti-loop
if block.hash() in blockchain_hashes:
    return  # Ya tenemos este bloque

blockchain.add(block)
# Propaga solo a peers que NO lo tienen (según inv tracking)
```

**Para Anuncios (INV messages):**
```python
# Bitcoin usa tracking de "quién anunció qué"
for item in inv_message:
    if item.hash in known_inventory[peer_id]:
        continue  # Este peer ya nos lo anunció
    
    known_inventory[peer_id].add(item.hash)
    # Solicitar si no lo tenemos
```

**¿Por qué Bitcoin no usa messages_seen como este demo?**

1. **Eficiencia:** Rastrear hashes de datos (TX, bloques) es más eficiente que rastrear IDs de mensajes
2. **Persistencia:** El mempool y blockchain persisten; un set temporal de message IDs se perdería
3. **Especificidad:** Cada tipo de dato tiene reglas de propagación diferentes
4. **Escala:** Con miles de mensajes/segundo, un set genérico crecería infinitamente

**Implementación futura en este demo:**

En la Fase 2.3 (blockchain), se reemplazará `messages_seen` por:
- Mempool para TXs (como Bitcoin)
- Blockchain confirmada para bloques (como Bitcoin)
- Sistema `inv`/`getdata` para anuncios eficientes

---

## 4. Gossip Protocol

### Problema que Resuelve

En la Fase 1, los nodos solo conocen sus bootstrap peers. Si el bootstrap cae, la red se fragmenta. El gossip protocol permite descubrimiento dinámico y continuo de peers.

### Arquitectura de Peers

Se separa en dos conceptos:

```python
peers_connected: Dict[str, WebSocket]  # Conexiones activas ahora
peers_known: Dict[str, PeerInfo]       # Todos los peers conocidos
```

**Relación:**
```
len(peers_known) >= len(peers_connected)
```

Todo peer conectado está en peers_known, pero no todos los peers conocidos están conectados (pueden estar offline).

**Comparación con Bitcoin:**
```cpp
// peers.dat (en disco, LevelDB)
CAddrMan addrman;  // ~20,000+ addresses conocidas, persisten entre reinicios

// Conexiones activas (en memoria)
std::vector<CNode*> vNodes;  // Máximo 125 conexiones simultáneas
```

**Diferencias clave:**

| Aspecto | Este Demo | Bitcoin |
|---------|-----------|---------|
| Almacenamiento de peers conocidos | Solo en memoria (RAM) | Disco (`peers.dat`) |
| Cantidad típica de peers conocidos | 5-10 | 10,000-50,000+ |
| Persistencia | Se pierde al cerrar | Persiste entre sesiones |
| Conexiones simultáneas | Ilimitado | Máximo 125 (8 outbound + 117 inbound) |
| Criterio de selección | Conecta a todos los conocidos | Selecciona los "mejores" (uptime, latencia, diversidad geográfica) |

**¿Por qué Bitcoin persiste peers en disco?**

Al reiniciar un nodo Bitcoin:
1. Lee `peers.dat` del disco
2. Carga miles de peers previamente conocidos
3. Selecciona los 8 mejores para conectar (outbound)
4. Evita tener que redescubrir la red desde cero

**¿Por qué este demo solo usa memoria?**

- Red pequeña (5 nodos locales)
- Ejecuciones cortas (minutos, no días)
- Propósito educativo: simplificar arquitectura

Todo peer conectado está en peers_known, pero no todos los peers conocidos están conectados (pueden estar offline).

### Mensajes de Gossip

| Mensaje | Dirección | Propósito |
|---------|-----------|-----------|
| `getaddr` | Nodo A → Nodo B | "Dame tu lista de peers" |
| `addr` | Nodo B → Nodo A | "Aquí están mis 10 mejores peers" |

### Flujo de Descubrimiento

**Estado actual (implementación con delay):**

```
T=0s:  Nodo 4 inicia con bootstrap=[Nodo 2]
       └─ peers_known: {Nodo 2}

T=1s:  Conecta a Nodo 2
       └─ Solicita peers (getaddr)

T=2s:  Recibe addr de Nodo 2
       └─ Descubre: [Nodo 1, Nodo 3, Nodo 5]

T=3s:  Conecta a peers nuevos
       └─ peers_connected: {1, 2, 3, 5}

T=8s:  Red completamente conectada (mesh)
       └─ Cada nodo conoce a todos los demás
```

**Implementación futura:**

Actualmente el descubrimiento inicial usa delays hardcodeados (`await asyncio.sleep(8)`). En fases futuras se implementará un **DNS Seed Server** similar al protocolo de Bitcoin, donde:
- Un servidor DNS retorna direcciones IP de nodos activos
- Los nodos nuevos consultan el DNS seed en lugar de esperar delays
- Se elimina la dependencia de tiempos de espera fijos

### Propagación de Peers

```
Nodo 1 conoce: {Nodo 2, Nodo 3}
Nodo 2 conoce: {Nodo 1}
Nodo 3 conoce: {Nodo 1}

Nodo 2 solicita peers a Nodo 1
  → Nodo 1 responde: [Nodo 3]
  → Nodo 2 descubre Nodo 3

Nodo 3 solicita peers a Nodo 1
  → Nodo 1 responde: [Nodo 2]
  → Nodo 3 descubre Nodo 2

Resultado: todos conocen a todos
```

### PeerInfo

Cada peer conocido se almacena con metadatos:

```python
class PeerInfo:
    host: str              # "localhost"
    port: int              # 5001
    node_id: str           # "node_5001"
    first_seen: float      # timestamp
    last_seen: float       # timestamp
    is_connected: bool     # True/False
    connection_failures: int
```

---

## 5. Fase 2.1 - Wallets y Transacciones

### Wallets

Cada nodo genera automáticamente una wallet al iniciar, conteniendo:

**Componentes de la Wallet:**

1. **Private Key (Llave Privada)**
   - Generada aleatoriamente usando la curva elíptica **Ed25519**
   - 32 bytes de entropía criptográficamente segura
   - Nunca se comparte ni se transmite por la red
   - Permite firmar transacciones

2. **Public Key (Llave Pública)**
   - Derivada matemáticamente de la private key
   - Curva **Ed25519** (Edwards-curve Digital Signature Algorithm)
   - 32 bytes
   - Se incluye en las transacciones para verificación

3. **Address (Dirección)**
   - Generada mediante el siguiente algoritmo:
     ```
     Public Key (32 bytes)
         ↓
     SHA-256 hash
         ↓
     SHA-256 hash (doble hash)
         ↓
     Primeros 20 bytes
         ↓
     RIPEMD-160 hash
         ↓
     Agregar version byte (0x00)
         ↓
     Checksum (primeros 4 bytes de doble SHA-256)
         ↓
     Base58Check encoding
         ↓
     Address final (ej: 1HydBLQ77qugdXUW9KmTXkSKNukWg7JhUm)
     ```
   - La address es compatible con el formato Bitcoin (empieza con '1')
   - Longitud típica: ~34 caracteres
   - Se comparte públicamente para recibir fondos

**Proceso de derivación:**

```
Private Key (secreta) 
    ↓ Ed25519 (curva elíptica)
Public Key (pública)
    ↓ SHA-256 + RIPEMD-160 + Base58Check
Address (pública, compartible)
```

### Firmas Determinísticas

Ed25519 genera el nonce de firma de forma determinística:
```
nonce = SHA512(private_key || mensaje)
```

**Implicación:**
```python
# Mismo mensaje + misma key = misma firma SIEMPRE
firma1 = wallet.sign("Hola")  # → "abc123..."
firma2 = wallet.sign("Hola")  # → "abc123..." (idéntica)

# Mensajes diferentes = firmas diferentes
firma3 = wallet.sign("Adiós")  # → "xyz789..." (diferente)
```

### Transacciones

**Estructura de una Transacción:**
```python
Transaction
├── from_address  → Dirección del remitente (o "COINBASE")
├── to_address    → Dirección del destinatario
├── amount        → Cantidad a transferir (float)
├── timestamp     → Timestamp Unix de creación
├── public_key    → Public key del remitente (para verificar firma)
└── signature     → Firma EdDSA del remitente
```

**Comparación con Bitcoin:**

| Campo | Este Demo | Bitcoin |
|-------|-----------|---------|
| Inputs | `from_address` (simple) | Array de UTXOs previos |
| Outputs | `to_address` (simple) | Array de outputs (scriptPubKey) |
| Amount | Un solo monto | Suma de outputs (puede haber cambio) |
| Scripts | No usa scripts | scriptSig (input) + scriptPubKey (output) |
| Fees | No implementado | Diferencia entre inputs y outputs |

**Simplificación del demo:** Una transacción tiene un remitente y un destinatario. Bitcoin usa el modelo UTXO donde una TX consume outputs previos (inputs) y crea nuevos outputs, permitiendo múltiples destinatarios y cambio.

**TXID (Transaction ID):**

El hash de la transacción excluye `public_key` y `signature`:
```python
# Solo campos inmutables
data = {from_address, to_address, amount, timestamp}
txid = SHA256(json_dumps(data, sort_keys=True))
```

Esta decisión replica Bitcoin: el TXID debe ser predecible antes de firmar y no debe cambiar al agregar la firma. Si el TXID incluyera la firma, un atacante podría modificar la firma ligeramente (transaction malleability) generando un TXID diferente para la misma transacción.

**Bitcoin:** Usa doble SHA256 (`SHA256(SHA256(tx_data))`) en lugar de SHA256 simple, pero el concepto es idéntico.

**Flujo de vida de una transacción:**
```
1. Crear TX (sin firma)
   tx = Transaction(alice.address, bob.address, 10)

2. Calcular TXID (antes de firmar)
   txid = tx.hash()  → "abc123..."

3. Firmar
   tx.sign(alice_wallet)
   tx.signature = EdDSA_sign(txid, alice.private_key)

4. TXID sigue igual
   tx.hash()  → "abc123..."  (no cambió)

5. Validar
   tx.is_valid()  → verifica firma EdDSA

6. Agregar a mempool local
   node.mempool.append(tx)

7. Propagar a la red P2P
   node.broadcast_transaction(tx)

8. Otros nodos reciben, validan y agregan a sus mempools
```

**Transacción Coinbase:**
```python
# Primera TX de cada bloque (recompensa al minero)
tx = Transaction("COINBASE", miner_address, 50)

# No requiere firma (no hay remitente real)
tx.is_valid()  → True (caso especial)
```

**Bitcoin:** Idéntico. La coinbase TX es la primera de cada bloque, crea nuevos bitcoins (actualmente 3.125 BTC por bloque después del halving 2024) y no requiere inputs ni firma.

### Validaciones de Transacción
```
is_valid():
  SI from_address == "COINBASE"
    → True (sin verificación adicional)
  SINO
    1. from_address no vacío
    2. to_address no vacío
    3. amount > 0
    4. public_key presente
    5. signature presente
    6. Verificar firma: EdDSA.verify(txid, public_key, signature) == True
       └─ Usa la public_key incluida en la TX
       └─ Valida que coincida con from_address
```

**Bitcoin:** Validación mucho más compleja porque incluye:
- Verificar que los inputs existen en UTXOs disponibles
- Ejecutar scripts (scriptSig + scriptPubKey) usando Script Engine
- Validar que suma(inputs) >= suma(outputs) + fee
- Verificar locktime, sequence numbers, SegWit witness data
- Verificar que no sea double-spend (inputs no gastados previamente)

**Simplificación del demo:** Solo valida firma y campos básicos. No verifica fondos disponibles ni previene double-spend (se hará en blockchain).

### Propagación de Transacciones P2P

**Flujo:**
```
1. Nodo A crea TX y la firma
   └─ tx = node_A.create_transaction(addr_B, 10)

2. Agrega a su mempool local
   └─ node_A.mempool.append(tx)

3. Propaga a peers conectados
   └─ node_A.broadcast_transaction(tx)
   └─ Envía mensaje tipo 'tx' a todos sus peers

4. Nodo B recibe TX
   ├─ Deserializa: Transaction.from_dict()
   ├─ Valida firma: tx.is_valid()
   ├─ Verifica no duplicada: if tx.hash() in mempool
   ├─ Agrega a mempool: mempool.append(tx)
   └─ Re-propaga a sus peers (excepto remitente)

5. Proceso se repite en cadena
   └─ TX alcanza todos los nodos en ~2 segundos
```

**Bitcoin:** Usa un sistema más eficiente en dos pasos:
```
1. Anuncio (INV message)
   Nodo A → Nodo B: "Tengo TX abc123"
   
2. Solicitud (GETDATA message)
   Nodo B → Nodo A: "Envíame TX abc123"
   
3. Envío (TX message)
   Nodo A → Nodo B: [TX completa]
```

**¿Por qué Bitcoin usa INV/GETDATA?**
- Ahorra bandwidth (no envía TXs no solicitadas)
- El receptor puede rechazar TXs que ya tiene sin descargarlas
- Permite priorización (pedir primero TXs con mayor fee)

**Simplificación del demo:** Envía la TX completa inmediatamente a todos los peers (push model vs pull model de Bitcoin). Suficiente para una red de 5 nodos.

**Anti-duplicados:**
```python
# Cada nodo verifica antes de agregar
tx_hash = tx.hash()
if any(t.hash() == tx_hash for t in self.mempool):
    return  # TX duplicada, ignorar
```

**Balance simulado (temporal):**
```python
def get_balance(self):
    balance = 100  # Balance inicial hardcoded
    
    for tx in self.mempool:
        if tx.from_address == self.wallet.address:
            balance -= tx.amount  # Gasté
        if tx.to_address == self.wallet.address:
            balance += tx.amount  # Recibí
    
    return balance
```

**Nota:** Este cálculo es temporal y presenta limitaciones:

**Problema:** No previene double-spend. Un usuario puede crear dos TXs gastando los mismos fondos.

**Ejemplo:**
```python
# Balance: 100
tx1 = Transaction(alice, bob, 100)    # Gasta todo
tx2 = Transaction(alice, charlie, 100) # Gasta todo de nuevo

# Ambas TXs son válidas en mempool
# Balance calculado: 100 - 100 - 100 = -100 ❌
```

**En fases posteriores (blockchain confirmada):**

Se implementará uno de estos modelos:

**Opción 1: UTXO (como Bitcoin)**
```python
# Cada TX consume outputs específicos
utxo_set = {
    "tx1:0": {"address": alice, "amount": 50},
    "tx2:1": {"address": alice, "amount": 30}
}

# TX debe referenciar UTXOs existentes
tx = Transaction(
    inputs=[("tx1:0", 50), ("tx2:1", 30)],
    outputs=[(bob, 70), (alice, 10)]  # 10 de cambio
)

# Una vez gastado un UTXO, no puede gastarse de nuevo
```

**Opción 2: Account Model (como Ethereum)**
```python
# Cada address tiene un balance global y un nonce
accounts = {
    alice: {"balance": 100, "nonce": 0},
    bob: {"balance": 50, "nonce": 0}
}

# TX incluye nonce (previene replay)
tx = Transaction(
    from_address=alice,
    to_address=bob,
    amount=10,
    nonce=0  # Debe incrementar secuencialmente
)

# Blockchain actualiza balances directamente
```

**Diferencias principales que NO se implementarán por ser un demo:**

1. **Replace-by-Fee (RBF):** Reemplazar TX por versión con mayor fee
2. **Child-Pays-for-Parent (CPFP):** Incentivar minado de TX padre
3. **Mempool prioritization:** Ordenar por fee/byte para minado
4. **Mempool expiration:** Eliminar TXs antiguas no confirmadas
5. **Transaction relay policy:** Reglas de qué TXs propagar (dust limit, fee mínimo)

Estas optimizaciones son importantes en producción pero innecesarias para demostrar los conceptos fundamentales de blockchain.

---

## 6. Merkle Trees

### Propósito

El árbol de Merkle permite verificar eficientemente si una transacción está incluida en un bloque sin descargar todas las transacciones.

### Implementación (`core/merkle.py`)

```python
# Construcción del árbol
def build_merkle_tree(tx_hashes: list[str]) -> str:
    # Empareja hashes de a dos
    # Si número impar, duplica el último
    # Hashea cada par: SHA256(left + right)
    # Repite hasta obtener un solo hash (Merkle Root)
```

**Merkle Root:** Se incluye en el header de cada bloque. Si cualquier transacción cambia, el Merkle Root cambia, haciendo inválido el bloque.

**Comparación con Bitcoin:**
- Bitcoin: idéntico algoritmo (doble SHA-256)
- Este demo: SHA-256 simple (mismo concepto)

---

## 7. Bloques y Blockchain

### Estructura de un Bloque (`core/block.py`)

```python
Block
├── index          → Altura en la cadena (0 = génesis)
├── timestamp      → Timestamp Unix de creación
├── transactions   → Lista de Transaction objects
├── previous_hash  → Hash del bloque anterior (encadenamiento)
├── merkle_root    → Raíz del árbol de Merkle de las TXs
├── nonce          → Número encontrado en el minado (PoW)
├── difficulty     → Target de dificultad en este bloque
└── hash           → SHA-256 de todos los campos anteriores
```

**Inmutabilidad:** Si se modifica cualquier campo de un bloque antiguo, su hash cambia. Eso invalida el `previous_hash` del siguiente bloque, y así en cadena. Recalcular toda la cadena requeriría más poder de cómputo que la red entera.

### Blockchain (`core/blockchain.py`)

```python
Blockchain
├── chain[]            → Lista de bloques confirmados
├── mempool[]          → TXs pendientes de confirmación
├── utxo_set{}         → Conjunto de outputs no gastados
└── pending_wallets{}  → Wallets conocidas por el nodo
```

**Validaciones al recibir un bloque:**
1. `previous_hash` apunta al último bloque confirmado
2. Hash del bloque cumple el target de dificultad (PoW válido)
3. Merkle Root coincide con las transacciones incluidas
4. Todas las transacciones tienen firmas válidas
5. No hay double-spend (inputs ya gastados)

**Resolución de forks (regla de cadena más larga):**

Cuando dos nodos tienen versiones diferentes de la cadena:
```
Nodo A: [..., bloque 10a, bloque 11a]  ← altura 11
Nodo B: [..., bloque 10b]              ← altura 10

Nodo B recibe la cadena de A
→ A tiene más altura (más trabajo acumulado)
→ Nodo B adopta la cadena de A
→ TXs del bloque 10b que no están en 10a vuelven al mempool
```

---

## 8. Proof of Work

### Algoritmo (`core/pow.py`)

```python
def mine_block(block, target):
    block.nonce = 0
    while True:
        block.hash = sha256(block.header())
        if int(block.hash, 16) < target:
            return block  # PoW válido encontrado
        block.nonce += 1
```

**Target:** Número de 256 bits. Un hash válido debe ser menor que el target. Cuanto más pequeño el target, más ceros iniciales requiere el hash, más difícil es el minado.

**Dificultad ajustable:** Cada 5 bloques, el protocolo compara el tiempo real con el tiempo objetivo:
```python
# Si los bloques tardaron más → bajar dificultad (subir target)
# Si los bloques tardaron menos → subir dificultad (bajar target)
tiempo_real = timestamp_bloque_actual - timestamp_bloque_hace_5
factor = tiempo_real / (5 × TARGET_BLOCK_TIME)
nuevo_target = target_actual × factor
```

**Comparación con Bitcoin:**
- Bitcoin ajusta cada 2016 bloques (≈2 semanas)
- Este demo ajusta cada 5 bloques (para que las demos no tarden tanto)
- El algoritmo de ajuste es conceptualmente idéntico

---

## 9. Seed Node y Descubrimiento en LAN

### Problema

En modo LAN, 30 máquinas necesitan encontrarse sin conocer de antemano las IPs de las demás.

### Solución: Seed Node (`network/seed_node.py`)

El seed node es un servidor HTTP simple que actúa como punto de rendezvous:

```
GET  /health          → {"status": "ok", "peers_count": N}
POST /register        → Registra un nodo {host, port, node_id, address}
GET  /peers           → Lista de todos los nodos registrados
GET  /addresses       → Lista de wallets (para el orquestador)
```

**Flujo de conexión LAN:**
```
1. Instructor arranca main_seed.py
   └─ Seed escucha en 0.0.0.0:8888

2. Alumno arranca main.py --host 192.168.1.Y
   └─ Nodo llama POST /register al seed
   └─ Nodo llama GET /peers
   └─ Conecta a todos los peers registrados

3. A medida que llegan más alumnos, todos se conectan entre sí
```

**Seed Client (`network/seed_client.py`):** Encapsula las llamadas HTTP al seed desde cada nodo.

---

## 10. Orquestador de Transacciones (`core/tx_orchestrator.py`)

### Propósito

Genera transacciones automáticas entre los nodos para demostrar el funcionamiento de la red sin intervención manual del usuario.

### Comportamiento

```python
# Cada TX_AUTO_BASE_INTERVAL ± TX_AUTO_JITTER segundos:
1. Obtiene lista de wallets desde el seed (/addresses)
2. Elige un nodo remitente con balance > 0 al azar
3. Elige un nodo destinatario diferente al azar
4. Calcula monto: balance × TX_AUTO_MAX_FRACTION (máx 20%)
5. Crea y firma la TX vía API REST del nodo remitente
6. La TX se propaga automáticamente por la red P2P
```

**Control:** Se puede pausar y reanudar desde el dashboard individual (Nodo 1) o desde el dashboard global del instructor.

---

## 11. Dashboard Global del Instructor (`dashboard_global/`)

### Propósito

Vista centralizada de toda la red, diseñada para proyectar en clase. El instructor puede ver el estado de todos los nodos y controlar el orquestador sin tocar los dashboards individuales.

### Componentes

- `dashboard_global/app.py` → Backend Flask, consulta cada nodo vía HTTP
- `dashboard_global/templates/global.html` → UI del dashboard
- `dashboard_global/static/global.js` → Auto-refresh cada 2s
- `dashboard_global/static/global.css` → Estilos

### Datos por nodo

| Campo | Fuente |
|---|---|
| Altura de blockchain | `/api/info` del nodo |
| Sincronización (✅⚠️🔴⬛) | Comparación con altura máxima de la red |
| Balance | `/api/wallet` del nodo |
| Peers conectados | `/api/peers` del nodo |
| Modo de minado | `/api/info` del nodo |
| Mempool | `/api/mempool` del nodo |

### Control del Orquestador desde el Global

```python
# main_global.py crea un orquestador propio
# A menos que se use --no-orchestrator
python main_global.py --no-orchestrator  # Cuando launcher_auto.py ya tiene uno
```

---

## 12. Despliegue y Visualización

### Modos de Despliegue

El sistema soporta cuatro variantes principales:

| Modo | Script | Descripción |
|---|---|---|
| **Local Manual** | `launcher_manual.py` | 5 nodos, el usuario mina y envía TXs manualmente |
| **Local Auto** | `launcher_auto.py` | 5 nodos + seed + orquestador de TXs automáticas |
| **LAN** | `main.py` + `main_seed.py` | 1 nodo por máquina, seed en máquina del instructor |
| **Dashboard Global** | `main_global.py` | Vista unificada de toda la red (complementa cualquier modo) |

### Mapeo de Puertos

| Puerto | Servicio | Script |
|---|---|---|
| 5000–5004 | P2P WebSocket (nodos locales) | `launcher_*.py` |
| 5000 | P2P WebSocket (nodo LAN) | `main.py` |
| 8000–8004 | Dashboard Flask (nodos locales) | `launcher_*.py` |
| 8000 | Dashboard Flask (nodo LAN) | `main.py` |
| 8888 | Seed Node HTTP | `main_seed.py` / `launcher_auto.py` |
| 9000 | Dashboard Global | `main_global.py` |

**WebSocket (5000-5004):**
- Protocolo: `ws://localhost:5000`
- Uso: Comunicación P2P entre nodos
- Mensajes: version, verack, ping, pong, getaddr, addr, tx, block, inv, getblocks

**HTTP (8000-8004):**
- Protocolo: `http://localhost:8000`
- Uso: Dashboard web para usuarios
- Tecnología: Flask (backend) + JavaScript (frontend)

### Interfaz Gráfica (Dashboard)

**Tecnologías:**
- **Backend:** Flask (Python)
- **Frontend:** HTML5 + CSS3 + Vanilla JavaScript
- **Actualización:** Auto-refresh cada 2 segundos

**Componentes del Dashboard:**

1. **Header**
   - ID del nodo (ej: node_5000)
   - Puerto P2P y Dashboard

2. **Wallet Card**
   - Address completa (Base58Check)
   - Balance actual (calculado desde mempool)
   - Botón "Copiar" para address

3. **Enviar Transacción**
   - Input manual de address destino
   - Input de cantidad (validación: min 0.01)
   - Validación de formato con regex: `^1[A-Za-z0-9]{25,34}$`
   - Botón "Enviar Transaccion"

4. **Red P2P**
   - Contador de peers conectados
   - Lista de peers (host:port)
   - Actualización en tiempo real

5. **Mempool**
   - Contador de transacciones pendientes
   - Lista detallada de TXs:
     - TXID truncado
     - From → To (addresses truncadas)
     - Cantidad de coins
   - Sincronizada entre todos los nodos

**Flujo de Uso:**

```
1. Usuario abre http://localhost:8000 en navegador

2. JavaScript ejecuta auto-refresh cada 2s:
   ├─ GET /api/info      → balance, peers_count, mempool_count
   ├─ GET /api/peers     → lista de peers conectados
   └─ GET /api/mempool   → lista de transacciones

3. Usuario completa formulario:
   ├─ Destinatario: 1BobAddress... (pega desde otro dashboard)
   └─ Cantidad: 10

4. Click "Enviar Transaccion"
   └─ POST /send_tx → Flask recibe

5. Backend procesa:
   ├─ node.create_transaction(to_address, amount)
   ├─ Firma con wallet del nodo
   └─ asyncio.run_coroutine_threadsafe(
         node.broadcast_transaction(tx),
         node.loop
      )

6. TX se propaga a la red P2P

7. Auto-refresh actualiza UI (2s después)
   └─ TX aparece en mempool de todos los dashboards
```

**Bridge Flask (sync) ↔ AsyncIO (async):**

Flask corre en thread síncrono, pero los nodos P2P son asíncronos. Se usa:

```python
# En Flask route:
asyncio.run_coroutine_threadsafe(
    node.broadcast_transaction(tx),  # Coroutine asíncrona
    node.loop                        # Event loop del nodo
)
```

Esto permite que Flask ejecute código asyncio sin bloquear su propio thread.

**APIs REST del Dashboard:**

| Endpoint | Método | Retorna |
|----------|--------|---------|
| `/` | GET | HTML del dashboard |
| `/api/info` | GET | `{node_id, address, balance, peers_count, mempool_count}` |
| `/api/wallet` | GET | `{address, balance}` |
| `/api/peers` | GET | `[{address, status}, ...]` |
| `/api/mempool` | GET | `[{txid, from, to, amount, timestamp}, ...]` |
| `/send_tx` | POST | Crea y propaga TX |

---

## 13. Seguridad

### Arquitectura de Seguridad

```
┌─────────────────────────────────────────────────────────┐
│                    CAPA DE RED (P2P)                    │
│                                                         │
│  Mensajes: version, verack, ping, pong, getaddr, addr   │
│  Seguridad: Checksum SHA-256                            │
│  Protege: Corrupción de datos en tránsito               │
│  No protege: Autenticación de remitente                 │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│               CAPA DE BLOCKCHAIN (TXs)                  │
│                                                         │
│  Transacciones, Bloques                                 │
│  Seguridad: Firma EdDSA Ed25519 obligatoria             │
│  Protege: Autenticación, integridad, no repudio         │
│  Garantiza: Solo el dueño puede gastar sus fondos       │
└─────────────────────────────────────────────────────────┘
```

### ¿Por qué Checksum para P2P?

Un atacante puede modificar un mensaje P2P y recalcular el checksum. Sin embargo, el daño es mínimo:

- `inv` falso → nodos piden objeto que no existe → ignorado
- `addr` falso → nodos intentan conectar a IP inexistente → falla silenciosa
- `ping` falso → se responde con `pong` → sin consecuencias

La blockchain se protege en su propia capa. Un mensaje P2P comprometido no puede afectar la integridad de los datos.

### Simplificaciones de Seguridad (Demo)

Las siguientes vulnerabilidades existen intencionalmente para simplificar:

- Sin TLS: mensajes en texto plano (aceptable en red local)
- Sin autenticación de nodos: ataques Sybil posibles
- Sin rate limiting robusto: susceptible a spam
- Double-spend posible en mempool (no en blockchain)
- Sin UTXO: no previene double-spend antes de confirmación

---

## 14. Simplificaciones vs Bitcoin

| Concepto | Bitcoin Real | Este Demo | Impacto Educativo |
|----------|-------------|-----------|-------------------|
| Algoritmo de firma | ECDSA secp256k1 | EdDSA Ed25519 | Bajo (conceptos idénticos) |
| Identificación de TX | TXID doble SHA256 | SHA256 simple | Mínimo |
| Mensajes P2P de TX | Script engine completo | Validación simple | Medio |
| Modelo de balance | UTXO | Account model simplificado | Medio |
| Peers en disco | peers.dat (LevelDB) | Solo en memoria | Bajo |
| Transport layer | TCP puro | WebSockets | Mínimo |
| Nonce de firma | RFC 6979 (HMAC) | Determinístico Ed25519 | Mínimo |
| Descubrimiento inicial | DNS Seeds | Seed node HTTP centralizado | Bajo |
| Ajuste de dificultad | Cada 2016 bloques | Cada 5 bloques | Bajo (misma lógica) |
| Recompensa de bloque | Halving cada 210k bloques | Fija (50 coins) | Bajo |
| Propagación de bloques | `inv`/`getdata` pull model | Push directo | Bajo |

---

## 15. Estructura de Archivos

```
blockchain-demo/
│
├── core/                        ← Lógica de blockchain
│   ├── wallet.py                ← Ed25519, Base58Check addresses
│   ├── transaction.py           ← Transacciones firmadas
│   ├── block.py                 ← Estructura del bloque
│   ├── blockchain.py            ← Cadena, mempool, UTXO, consenso
│   ├── merkle.py                ← Árbol de Merkle y Merkle root
│   ├── pow.py                   ← Proof of Work (SHA-256, ajuste automático)
│   └── tx_orchestrator.py       ← Bot generador de TXs automáticas
│
├── network/                     ← Red P2P
│   ├── p2p_node.py              ← Nodo P2P completo (WebSocket)
│   ├── protocol.py              ← Formato de mensajes, checksum
│   ├── peer_info.py             ← Metadata de peers para gossip
│   ├── seed_node.py             ← Servidor HTTP de descubrimiento
│   └── seed_client.py           ← Cliente del seed node
│
├── dashboard/                   ← Dashboard por nodo
│   ├── app.py                   ← Backend Flask
│   ├── templates/dashboard.html ← UI del nodo
│   └── static/
│       ├── app.js               ← Auto-refresh, interacción
│       └── style.css            ← Estilos
│
├── dashboard_global/            ← Dashboard global del instructor
│   ├── app.py                   ← Backend Flask
│   ├── templates/global.html    ← Vista unificada de la red
│   └── static/
│       ├── global.js            ← Auto-refresh, control orquestador
│       └── global.css           ← Estilos
│
├── setup/                       ← Scripts de setup automático (LAN)
│   ├── setup_instructor.ps1     ← Instala todo + arranca seed y global
│   └── setup_alumno.ps1         ← Instala todo + arranca nodo alumno
│
├── documentacion/               ← Documentación técnica
│   ├── documentacion.md         ← Este documento
│   ├── MANUAL_USUARIO.md        ← Manual completo de uso
│   ├── instrucciones.md         ← Referencia rápida de comandos
│   └── DOC/                     ← Documentación detallada por módulo
│       ├── core/
│       │   ├── DOC_core_wallet.md
│       │   ├── DOC_core_transaction.md
│       │   ├── DOC_core_block.md
│       │   ├── DOC_core_blockchain.md
│       │   ├── DOC_core_merkle.md
│       │   ├── DOC_core_pow.md
│       │   └── DOC_core_tx_orchestrator.md
│       ├── network/
│       │   ├── DOC_network_p2p_node.md
│       │   ├── DOC_network_protocol.md
│       │   ├── DOC_network_peer_info.md
│       │   └── DOC_network_seed.md
│       ├── dashboard/
│       │   └── DOC_dashboard.md
│       ├── daschboard_global/
│       │   ├── DOC_dashboard_global_app.md
│       │   ├── DOC_dashboard_global_html.md
│       │   ├── DOC_dashboard_global_js.md
│       │   └── DOC_dashboard_global_css.md
│       ├── tests/
│       │   ├── DOC_test_wallet.md
│       │   ├── DOC_test_transaction.md
│       │   ├── DOC_test_block.md
│       │   ├── DOC_test_blockchain.md
│       │   ├── DOC_test_blockchain_chain.md
│       │   ├── DOC_test_merkle.md
│       │   ├── DOC_test_pow.md
│       │   ├── DOC_test_p2p_node.md
│       │   ├── DOC_test_protocol.md
│       │   ├── DOC_test_seed_node.md
│       │   └── DOC_test_tx_orchestrator.md
│       ├── DOC_config.md
│       ├── DOC_main.md
│       ├── DOC_main_seed.md
│       ├── DOC_main_global.md
│       ├── DOC_launcher_manual.md
│       └── DOC_launcher_auto.md
│
├── tests/                       ← Suite pytest (11 archivos)
│   ├── test_wallet.py
│   ├── test_transaction.py
│   ├── test_block.py
│   ├── test_blockchain.py
│   ├── test_blockchain_chain.py
│   ├── test_merkle.py
│   ├── test_pow.py
│   ├── test_p2p_node.py
│   ├── test_protocol.py
│   ├── test_seed_node.py
│   └── test_tx_orchestrator.py
│
├── utils/logger.py              ← Logging por nodo
├── config.py                    ← Configuración central (dificultad, puertos, etc.)
├── main.py                      ← Entry point LAN (1 nodo por máquina)
├── main_seed.py                 ← Entry point seed node
├── main_global.py               ← Entry point dashboard global
├── launcher_manual.py           ← Demo local 5 nodos (modo manual)
├── launcher_auto.py             ← Demo local 5 nodos (modo auto + seed)
├── logs/                        ← Logs generados en tiempo de ejecución
├── setup.py                     ← Registro de paquete (pip install -e .)
├── pytest.ini                   ← Configuración de pytest
├── requirements.txt             ← Dependencias Python
└── .gitignore                   ← Excluye venv/, logs/, __pycache__/
```

### Dependencias (requirements.txt)

```
websockets       ← Comunicación P2P (WebSocket)
cryptography     ← EdDSA Ed25519, SHA256
pycryptodome     ← RIPEMD160, Base58Check
flask            ← Dashboard web y dashboard global
pytest           ← Framework de testing
pytest-asyncio   ← Tests asíncronos
pytest-cov       ← Cobertura de tests
requests         ← HTTP client (seed_client, orquestador)
```

---

---

## Documentación Detallada por Módulo

La carpeta `documentacion/DOC/` contiene un archivo Markdown por módulo con análisis detallado de arquitectura, comparación con Bitcoin, flujos y ejemplos.

**Core:**
1. `DOC_core_wallet.md` — Sistema de wallets, Ed25519, Base58Check
2. `DOC_core_transaction.md` — Estructura y validación de transacciones
3. `DOC_core_block.md` — Estructura del bloque y encadenamiento
4. `DOC_core_blockchain.md` — Cadena, mempool, UTXO, consenso, forks
5. `DOC_core_merkle.md` — Árbol de Merkle y Merkle root
6. `DOC_core_pow.md` — Proof of Work y ajuste de dificultad
7. `DOC_core_tx_orchestrator.md` — Orquestador de TXs automáticas

**Network:**
8. `DOC_network_p2p_node.md` — Nodo P2P completo (WebSocket)
9. `DOC_network_protocol.md` — Protocolo de mensajería P2P
10. `DOC_network_peer_info.md` — Gestión de peers y gossip
11. `DOC_network_seed.md` — Seed node HTTP

**Dashboard:**
12. `DOC_dashboard.md` — Dashboard individual (Flask + JS)
13. `DOC_dashboard_global_app.md` — Dashboard global backend
14. `DOC_dashboard_global_html.md` — Dashboard global frontend HTML
15. `DOC_dashboard_global_js.md` — Dashboard global JavaScript
16. `DOC_dashboard_global_css.md` — Dashboard global estilos

**Entry points y config:**
17. `DOC_config.md` — Parámetros de configuración central
18. `DOC_main.md` — Entry point LAN (1 nodo)
19. `DOC_main_seed.md` — Entry point seed node
20. `DOC_main_global.md` — Entry point dashboard global
21. `DOC_launcher_manual.md` — Launcher demo local manual
22. `DOC_launcher_auto.md` — Launcher demo local automático

**Tests:**
23–33. `DOC_test_*.md` — Un archivo por módulo de test

Cada documento proporciona:
- Arquitectura y decisiones de diseño
- Comparación con Bitcoin real
- Flujos de ejecución y diagramas
- Ejemplos de uso
