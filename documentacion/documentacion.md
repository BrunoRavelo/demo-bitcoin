# Documento Técnico de Arquitectura
## Demo Blockchain - MT
---

## 1. Visión General

Este proyecto es un demo educativo de blockchain tipo Bitcoin implementado en Python. Demuestra los principios fundamentales de una red descentralizada: peer-to-peer, propagación de mensajes, criptografía, firmas digitales y validación de transacciones.

### Estado Actual del Proyecto

**Fases completadas:**
- Red P2P básica
- Gossip Protocol
- Wallets y Transacciones
- Integración P2P + TX (Demo CLI)
- Dashboard Web Interactivo

**Trabajo futuro:**
- Merkle Trees
- Bloques y Blockchain
- Proof of Work (PoW)
- Propagación P2P de bloques
- Evluación de alternativas de escalabilidad

### Objetivos

- Replicar la arquitectura P2P de Bitcoin a pequeña escala
- Demostrar descubrimiento de peers mediante gossip protocol
- Implementar firmas digitales con EdDSA (Ed25519)
- Proporcionar interfaz gráfica para visualización en tiempo real
- Construir la base para blockchain, PoW y consenso en fases posteriores

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

## 6. Despliegue y Visualización

### Arquitectura de Despliegue

El sistema actual permite dos modos de ejecución:

**Modo A: Demo CLI (Automatizado)**
```bash
python demo_tx_cli.py
```
- 5 nodos P2P (puertos 5000-5004)
- 3 transacciones hardcodeadas
- Salida en terminal
- Duración: ~17 segundos
- Propósito: Testing rápido

**Modo B: Dashboard Web (Interactivo)**
```bash
python launcher_dashboard.py
```
- 5 nodos P2P (puertos 5000-5004)
- 5 servidores Flask (puertos 8000-8004)
- Interfaz gráfica en navegador
- Transacciones creadas manualmente
- Propósito: Demo para evaluador

### Mapeo de Puertos

Cada nodo utiliza dos puertos:

| Nodo | Puerto WebSocket (P2P) | Puerto HTTP (Dashboard) | Propósito |
|------|------------------------|-------------------------|-----------|
| Nodo 1 | 5000 | 8000 | Red P2P / UI Web |
| Nodo 2 | 5001 | 8001 | Red P2P / UI Web |
| Nodo 3 | 5002 | 8002 | Red P2P / UI Web |
| Nodo 4 | 5003 | 8003 | Red P2P / UI Web |
| Nodo 5 | 5004 | 8004 | Red P2P / UI Web |

**WebSocket (5000-5004):**
- Protocolo: `ws://localhost:5000`
- Uso: Comunicación P2P entre nodos
- Mensajes: version, verack, ping, pong, getaddr, addr, tx

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

## 7. Seguridad

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

## 8. Simplificaciones vs Bitcoin

| Concepto | Bitcoin Real | Este Demo | Impacto Educativo |
|----------|-------------|-----------|-------------------|
| Algoritmo de firma | ECDSA secp256k1 | EdDSA Ed25519 | Bajo (conceptos idénticos) |
| Identificación de TX | TXID doble SHA256 | SHA256 simple | Mínimo |
| Mensajes P2P de TX | Script engine completo | Validación simple | Medio |
| Modelo de balance | UTXO (complejo) | Suma/resta simple | Alto (se implementará UTXO) |
| Peers en disco | peers.dat (LevelDB) | Solo en memoria | Bajo |
| Transport layer | TCP puro | WebSockets | Mínimo |
| Nonce de firma | RFC 6979 (HMAC) | Determinístico Ed25519 | Mínimo |
| Descubrimiento inicial | DNS Seeds | Delays hardcoded | Medio (DNS pendiente) |

---

## 9. Estructura de Archivos

```
blockchain-demo/
│
├── core/                      ← Lógica de blockchain
│   ├── __init__.py
│   ├── wallet.py              ← Ed25519, Base58Check addresses
│   └── transaction.py         ← Transacciones firmadas
│
├── network/                   ← Red P2P
│   ├── __init__.py
│   ├── protocol.py            ← Formato de mensajes, checksum
│   ├── peer_info.py           ← Metadata de peers para gossip
│   └── p2p_node.py            ← Nodo P2P completo + mempool
│
├── dashboard/                 ← Interfaz web (Fase B)
│   ├── __init__.py
│   ├── app.py                 ← Servidor Flask
│   ├── templates/
│   │   └── dashboard.html     ← UI del dashboard
│   └── static/
│       ├── style.css          ← Estilos
│       └── app.js             ← Auto-refresh, interacción
│
├── utils/                     ← Utilidades
│   ├── __init__.py
│   └── logger.py              ← Logging por nodo (node_5000.log)
│
├── tests/                     ← Suite de tests
│   ├── __init__.py
│   ├── test_wallet.py         ← 10 tests (Ed25519, firmas, addresses)
│   └── test_transaction.py    ← 13 tests (crear, firmar, validar)
│
├── documentacion/             ← Documentación técnica
│   ├── documentacion.md       ← Este documento (general)
│   └── DOC/                   ← Documentación detallada por archivo
│       ├── DOC_core_wallet.md
│       ├── DOC_core_transaction.md
│       ├── DOC_network_p2p_node.md
│       ├── DOC_network_protocol.md
│       ├── DOC_network_peer_info.md
│       ├── DOC_launcher_dashboard.md
│       ├── DOC_demo_tx_cli.md
│       ├── DOC_dashboard_app.md
│       ├── DOC_dashboard_static_app_js.md
│       └── DOC_dashboard_templates_dashboard_html.md
│
├── logs/                      ← Logs generados (no en git)
│   ├── node_5000.log
│   ├── node_5001.log
│   └── ...
│
├── demo_tx_cli.py             ← Demo CLI automatizado (Fase A)
├── launcher_dashboard.py      ← Launcher dashboard web (Fase B)
├── test_network.py            ← Test manual de red (5 nodos)
├── setup.py                   ← Registro de paquete (pip install -e .)
├── requirements.txt           ← Dependencias
└── .gitignore                 ← Excluye venv/, logs/, __pycache__/
```

### Dependencias (requirements.txt)

```
websockets==12.0         ← Comunicación P2P
cryptography==41.0.7     ← EdDSA Ed25519, SHA256
pycryptodome==3.19.0     ← RIPEMD160, Base58
flask==3.0.0             ← Dashboard web
pytest==7.4.3            ← Testing
pytest-asyncio==0.21.1   ← Tests asíncronos
pytest-cov==4.1.0        ← Coverage
```

---

## 10. Trabajo Futuro

### Fases Pendientes

**Merkle Trees**
- Implementar árbol de Merkle para transacciones
- Merkle root en header de bloque
- Pruebas de inclusión (Merkle proofs)

**Bloques y Blockchain**
- Estructura de bloques
- Encadenamiento con hash del bloque anterior
- Validación de cadena

**Proof of Work**
- Algoritmo de minado (SHA-256)
- Recompensa por bloque (coinbase)
- Validación de PoW

**Propagación P2P de Bloques**
- Mensajes `inv` (inventory)
- Mensajes `getdata` / `block`
- Sincronización de blockchain entre nodos

**Evaluación de Escalabilidad**
- Propuestas de optimización, correcciones o depuración

### Mejoras Pendientes

**Red P2P:**
- DNS Seed Server (reemplazar delays hardcoded)

**Transacciones:**
- Modelo UTXO mejorado
- Prevención de double-spend pre-confirmación

**Dashboard:**
- Historial de transacciones confirmadas
- Visualización de blockchain
---

## Documentación detallada

La documentación técnica detallada de cada componente del sistema se encuentra disponible en el github https://github.com/BrunoRavelo/demo-bitcoin, en donde se encuentran los archivos:

1. **DOC_core_wallet.md** - Sistema de wallets, Ed25519, Base58Check
2. **DOC_core_transaction.md** - Estructura y validación de transacciones
3. **DOC_network_p2p_node.md** - Implementación completa del nodo P2P
4. **DOC_network_protocol.md** - Protocolo de mensajería P2P
5. **DOC_network_peer_info.md** - Gestión de información de peers
6. **DOC_launcher_dashboard.md** - Sistema de lanzamiento del dashboard
7. **DOC_demo_tx_cli.md** - Demo automatizado CLI
8. **DOC_dashboard_app.md** - Backend Flask del dashboard
9. **DOC_dashboard_static_app_js.md** - Frontend JavaScript
10. **DOC_dashboard_templates_dashboard_html.md** - Estructura HTML

Cada documento anexo proporciona análisis detallado de:
- Arquitectura y decisiones de diseño
- Explicación línea por línea del código
- Comparación con Bitcoin real
- Ejemplos de uso y casos de prueba
- Diagramas de flujo y secuencia
