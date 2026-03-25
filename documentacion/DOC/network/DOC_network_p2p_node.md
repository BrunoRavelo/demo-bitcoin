# Documentación Técnica: `network/p2p_node.py`

---

## Propósito del Archivo

`p2p_node.py` es el componente central de la red — el nodo P2P completo. Coordina todos los demás componentes: recibe y envía mensajes WebSocket, propaga transacciones y bloques, mina en background sin bloquear la red, y sincroniza la cadena con otros nodos.

**Analogía:** El nodo P2P es como un empleado de banco que simultáneamente atiende clientes (mensajes entrantes), habla con otras sucursales (mensajes salientes), actualiza el libro contable (blockchain), y busca el siguiente folio válido (minado) — todo al mismo tiempo sin que una tarea bloquee las demás.

---

## Modos de Minado

```python
MINING_AUTO   = 'auto'    # Mina continuamente, cancela al recibir bloque externo
MINING_MANUAL = 'manual'  # Solo mina al llamar mine_once()
MINING_PAUSED = 'paused'  # No mina, estado inicial en tests
```

| Modo | Quién lo usa | Cuándo |
|------|-------------|--------|
| `AUTO` | `launcher_auto.py` | Demo con TXs automáticas |
| `MANUAL` | `launcher_manual.py` | Demo interactivo para alumnos |
| `PAUSED` | Tests, `demo_tx_cli.py` | Para controlar el minado en tests |

---

## Clase `P2PNode`

**Atributos principales:**

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `id` | `str` | Identificador único: `node_{port}` |
| `host` | `str` | IP donde escucha |
| `port` | `int` | Puerto WebSocket P2P |
| `blockchain` | `Blockchain` | Fuente de verdad — cadena y mempool |
| `wallet` | `Wallet` | Identidad criptográfica del nodo |
| `peers_connected` | `Dict[str, WebSocket]` | Conexiones activas ahora |
| `peers_known` | `Dict[str, PeerInfo]` | Todos los peers conocidos |
| `messages_seen` | `Set[str]` | IDs de mensajes procesados (anti-loop) |
| `mining_mode` | `str` | Modo actual de minado |
| `_stop_mining_event` | `threading.Event` | Señal para cancelar PoW en curso |
| `blocks_mined` | `int` | Stats para el dashboard |
| `mining_rewards` | `float` | Stats para el dashboard |
| `dashboard_port` | `int` | Puerto del dashboard (para el seed) |
| `loop` | `EventLoop` | Event loop capturado al arrancar |

---

## Función `start`

```python
async def start(self):
```

**¿Qué hace?**

Punto de entrada del nodo. Captura el event loop, registra en el seed, levanta el servidor WebSocket y arranca todos los loops periódicos.

**Secuencia de arranque:**

```
1. self.loop = asyncio.get_running_loop()
        │
        ▼
2. _bootstrap_from_seed()
   → register en seed
   → announce_address al seed
   → get_peers del seed → agregar a peers_known
        │
        ▼
3. websockets.serve(handle_incoming_connection)
   → servidor WebSocket escuchando
        │
        ▼
4. asyncio.create_task() para cada loop:
   → connect_to_bootstrap()   — conectar a peers conocidos
   → gossip_loop()            — descubrir más peers
   → ping_loop()              — keep-alive
   → cleanup_loop()           — limpiar mensajes y peers viejos
   → seed_register_loop()     — re-registro periódico
        │
        ▼
5. Si mining_mode == AUTO:
   → start_mining_loop()
        │
        ▼
6. await asyncio.Future()  — correr para siempre
```

**¿Por qué `asyncio.create_task()` en lugar de `await`?**

`await` bloquearía la ejecución hasta que el coroutine termine. Con `create_task()` todos los loops corren concurrentemente — cada uno cede el control al event loop con `await asyncio.sleep()` y el event loop los alterna.

---

## Minado Asíncrono

### `start_mining_loop`

```python
async def start_mining_loop(self):
```

Loop que mina bloques indefinidamente en modo AUTO.

**¿Por qué el PoW no bloquea la red?**

```python
block = await loop.run_in_executor(
    None,                                    # ThreadPoolExecutor por defecto
    self.blockchain.mine_block_cancellable,  # función síncrona
    self.wallet.address,
    self._stop_mining_event,
)
```

`run_in_executor()` corre el PoW en un thread separado del pool. El event loop queda libre para procesar mensajes WebSocket mientras se mina. Cuando el PoW termina (éxito o cancelación), el resultado vuelve al event loop.

**Diagrama de threads:**

```
Thread principal (asyncio event loop)
    │
    ├── handle_incoming_connection()  ← mensajes entrantes
    ├── listen_to_peer()              ← mensajes salientes
    ├── gossip_loop()                 ← descubrimiento
    ├── ping_loop()                   ← keep-alive
    └── start_mining_loop()
            │
            └── run_in_executor()
                    │
                    ▼
            Thread del pool (PoW)
                mine_block_cancellable()
                    │
                    └── ProofOfWork.mine(stop_event)
                            └── while not stop_event.is_set():
                                    probar nonce...
```

### `mine_once`

```python
async def mine_once(self):
```

Mina exactamente un bloque en modo MANUAL. Llamado desde el dashboard cuando el usuario presiona "Minar ahora". No lanza un loop — mina y retorna.

### `set_mining_mode`

```python
def set_mining_mode(self, mode: str):
```

Cambia el modo de minado. Si había minado activo en AUTO, cancela el PoW en curso activando `_stop_mining_event`. Si el nuevo modo es AUTO, arranca el mining loop.

### `_cancel_current_mining`

```python
def _cancel_current_mining(self):
```

Activa `_stop_mining_event` para cancelar el PoW en curso. Se llama cuando llega un bloque externo válido — el prev_hash cambió, el bloque en el que trabajábamos ya no es válido.

---

## Handshake y Conexiones

### `handle_incoming_connection`

```python
async def handle_incoming_connection(self, websocket, path=None):
```

Handler de conexiones entrantes. El primer mensaje debe ser `MSG_VERSION` — si no, la conexión se descarta.

**Flujo:**
```
Peer conecta
    │
    ▼
Primer mensaje:
    ¿MSG_VERSION?
    ├── Sí → registrar en peers_connected, responder MSG_VERACK
    └── No → ignorar (protocolo incorrecto)

Mensajes siguientes:
    → handle_message() (router)
```

**¿Por qué `path=None`?**

Compatibilidad con websockets 12.x que eliminó el parámetro `path` del handler. Con `=None` funciona con ambas versiones.

### `connect_to_peer`

```python
async def connect_to_peer(self, peer_info: PeerInfo):
```

Inicia una conexión saliente. Envía `MSG_VERSION`, espera `MSG_VERACK` y luego pide peers y sincronización de cadena.

---

## Router de Mensajes

```python
async def handle_message(self, msg: dict, sender_ws):
```

**Anti-loop:** Si `msg['id']` ya está en `messages_seen` → descartar inmediatamente.

**Routing:**

| Tipo | Handler |
|------|---------|
| `MSG_PING` | `_handle_ping` → responder `MSG_PONG` |
| `MSG_PONG` | ignorar (solo confirma que el peer vive) |
| `MSG_GETADDR` | `handle_getaddr` → enviar lista de peers |
| `MSG_ADDR` | `handle_addr` → agregar nuevos peers |
| `MSG_TX` | `handle_tx` → validar y propagar TX |
| `MSG_BLOCK` | `handle_block` → validar y propagar bloque |
| `MSG_INV` | `handle_inv` → verificar si ya tenemos el bloque |
| `MSG_GETBLOCKS` | `handle_getblocks` → enviar cadena completa |

---

## Propagación de Bloques

### `handle_block`

```python
async def handle_block(self, msg: dict, sender_ws):
```

Dos casos:

**Caso 1 — Bloque individual:**
```
Recibir bloque
    │
    ▼
blockchain.add_block(block)
    ├── True  → _cancel_current_mining()
    │            broadcast_block(block, exclude=sender)
    └── False → _request_chain_sync(sender_ws)
                (prev_hash no conecta — pedir cadena completa)
```

**Caso 2 — Cadena completa (respuesta a getblocks):**
```
Recibir full_chain
    │
    ▼
_process_full_chain(chain_data)
    │
    ▼
blockchain.replace_chain(new_chain)
    ├── True  → _cancel_current_mining()
    └── False → mantener cadena actual
```

### `handle_inv`

Recibe anuncio de bloque nuevo (solo hash y altura). Si el peer tiene altura mayor → solicitar sincronización. Si ya tenemos el bloque → ignorar.

### `broadcast_block`

```python
async def broadcast_block(self, block: Block, exclude_ws=None):
```

Envía `MSG_INV` seguido de `MSG_BLOCK` a todos los peers conectados excepto el que nos lo envió. El `exclude_ws` evita enviar el bloque de vuelta al mismo peer que nos lo mandó.

---

## Loops Periódicos

### `gossip_loop`

Cada `GOSSIP_INTERVAL` segundos pide la lista de peers a todos los peers conectados (`MSG_GETADDR`). Al recibir nuevos peers (`MSG_ADDR`), intenta conectarse a ellos vía `connect_to_bootstrap()`.

### `ping_loop`

Cada `PING_INTERVAL` segundos envía `MSG_PING` a todos los peers conectados. Si un peer no responde, la conexión se cierra eventualmente.

### `cleanup_loop`

Cada `CLEANUP_INTERVAL` segundos:
- Recorta `messages_seen` a los últimos 500 (evita crecimiento infinito)
- Elimina de `peers_known` los peers inactivos más de 24 horas

### `seed_register_loop`

Cada `CLEANUP_INTERVAL` segundos hace re-registro en el seed para mantener el keep-alive. El seed elimina nodos que no hacen ping en 300 segundos.

---

## Flujo completo: TX creada por usuario

```
Usuario en dashboard envía TX (POST /send_tx)
        │
        ▼
node.create_transaction(to, amount)
    │── validar balance
    │── crear Transaction
    │── tx.sign(self.wallet)
    │── blockchain.add_transaction_to_mempool(tx)
    └── retornar tx
        │
        ▼
asyncio.run_coroutine_threadsafe(
    node.broadcast_transaction(tx),
    node.loop,
)
        │
        ▼
broadcast_message(MSG_TX, tx.to_dict())
        │
        ├──► Peer 1: handle_tx() → mempool → broadcast...
        └──► Peer 2: handle_tx() → mempool → broadcast...
```

---

## Tests Asociados: `tests/test_p2p_node.py`

| Test | Qué verifica |
|------|--------------|
| `test_node_creation` | Nodo se instancia correctamente |
| `test_nodes_connect` | Dos nodos establecen conexión WebSocket |
| `test_peer_discovery` | Gossip descubre nuevos peers |
| `test_block_broadcast` | Bloque minado se propaga a peers |
| `test_tx_propagation` | TX se propaga por la red |
| `test_chain_sync` | Nodo nuevo sincroniza cadena al conectar |
| `test_mining_auto` | Modo AUTO mina bloques automáticamente |
| `test_mining_manual` | Modo MANUAL no mina solo |
| `test_mining_cancel` | Bloque externo cancela PoW en curso |
| `test_fork_resolution` | Cadena más larga gana el fork |
| `test_ping_pong` | Keep-alive funciona correctamente |
| `test_message_dedup` | Mensajes duplicados se descartan |

---

*Documento: `DOC_network_p2p_node.md` — Demo Blockchain*
