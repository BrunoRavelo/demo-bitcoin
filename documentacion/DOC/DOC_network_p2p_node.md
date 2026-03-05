# Documentación Técnica: `network/p2p_node.py`

---

## Propósito del Archivo

`p2p_node.py` implementa un nodo peer-to-peer completo con capacidades de red descentralizada. Cada nodo actúa simultáneamente como servidor (acepta conexiones) y cliente (inicia conexiones), permitiendo una red verdaderamente distribuida sin punto central de fallo.

**Analogía:** Un nodo P2P es como un teléfono que puede:
- **Recibir llamadas** (servidor: acepta conexiones entrantes)
- **Hacer llamadas** (cliente: conecta con otros)
- **Pasar mensajes** (gossip: comparte info de contactos)
- **Mantener conversaciones** (mempool: comparte transacciones)

---

## Protocolo de Red: WebSockets sobre TCP

Este archivo usa **WebSockets** en lugar de TCP puro (como Bitcoin).

**¿Por qué WebSockets y no TCP puro?**

Bitcoin usa TCP directo porque fue diseñado en 2009 cuando WebSockets no existían (RFC 6455, 2011). WebSockets proveen ventajas para un demo educativo:

| Aspecto | TCP Puro (Bitcoin) | WebSockets (Este Demo) |
|---------|-------------------|------------------------|
| Conexiones persistentes | ✅ Sí | ✅ Sí |
| Bidireccional | ✅ Sí | ✅ Sí |
| Ping/Pong integrado | ❌ Manual | ✅ Automático |
| Manejo de errores | ❌ Manual | ✅ Librería lo maneja |
| Complejidad código | Alta (~500 líneas) | Baja (~100 líneas) |
| Concepto P2P | ✅ Idéntico | ✅ Idéntico |

Los conceptos que este demo enseña (red mesh, gossip, propagación) son **idénticos** independientemente del protocolo de transporte.

---

## Dependencias

```python
import asyncio
import websockets
import json
from typing import Dict, Set, List
from datetime import datetime, timedelta

from utils.logger import setup_logger
from network.protocol import create_message, validate_message
from network.peer_info import PeerInfo
from core.transaction import Transaction
from core.wallet import Wallet
```

| Import | Propósito |
|--------|-----------|
| `asyncio` | Programación asíncrona (múltiples conexiones simultáneas) |
| `websockets` | Servidor y cliente WebSocket |
| `json` | Serialización de mensajes |
| `Dict, Set, List` | Type hints para estructuras de datos |
| `datetime, timedelta` | Timestamps y manejo de tiempo |
| `setup_logger` | Sistema de logs por nodo |
| `create_message, validate_message` | Protocolo de mensajes P2P |
| `PeerInfo` | Información de peers conocidos |
| `Transaction` | Transacciones de blockchain |
| `Wallet` | Identidad criptográfica del nodo |

---

## Clase `P2PNode`

```python
class P2PNode:
```

Representa un nodo completo en la red P2P con capacidades de servidor, cliente, gossip protocol y propagación de transacciones.

**Atributos de instancia:**

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `id` | `str` | Identificador único (`node_{port}`) |
| `host` | `str` | IP o hostname del nodo |
| `port` | `int` | Puerto para escuchar conexiones |
| `peers_connected` | `Dict[str, WebSocket]` | Peers actualmente conectados |
| `peers_known` | `Dict[str, PeerInfo]` | Todos los peers conocidos (historial) |
| `messages_seen` | `Set[str]` | IDs de mensajes ya procesados (anti-loop) |
| `wallet` | `Wallet` | Identidad criptográfica del nodo |
| `mempool` | `List[Transaction]` | Transacciones pendientes |
| `balance` | `float` | Balance simulado inicial (100.0) |

**Constantes de configuración:**

| Constante | Valor | Propósito |
|-----------|-------|-----------|
| `MAX_OUTBOUND_CONNECTIONS` | 8 | Límite de conexiones salientes (como Bitcoin) |
| `MAX_INBOUND_CONNECTIONS` | 125 | Límite de conexiones entrantes (como Bitcoin) |
| `MAX_PEERS_TO_SHARE` | 10 | Máximo de peers a compartir en mensaje `addr` |
| `GOSSIP_INTERVAL` | 60s | Frecuencia de solicitud de peers |
| `PING_INTERVAL` | 30s | Frecuencia de keep-alive |
| `CLEANUP_INTERVAL` | 300s | Frecuencia de limpieza de peers obsoletos |

---

## Función `__init__`

```python
def __init__(self, host: str, port: int, bootstrap_peers: list):
    self.id = f"node_{port}"
    self.host = host
    self.port = port
    
    self.peers_connected: Dict[str, websockets.WebSocketServerProtocol] = {}
    self.peers_known: Dict[str, PeerInfo] = {}
    
    for host, port in bootstrap_peers:
        addr = f"{host}:{port}"
        self.peers_known[addr] = PeerInfo(host, port)
    
    self.messages_seen: Set[str] = set()
    self.MAX_MESSAGES_SEEN = 1000
    
    # ... constantes de configuración ...
    
    self.wallet = Wallet()
    self.mempool: List[Transaction] = []
    self.balance = 100.0
    
    self.logger = setup_logger(self.id)
```

**¿Qué hace?**

Inicializa un nodo P2P con su configuración de red, estructuras de datos para peers, sistema de mensajería, wallet propia y mempool vacío.

**Proceso:**

```
1. Crear identificador único (node_5000, node_5001...)
2. Guardar configuración de red (host, port)
3. Inicializar diccionarios de peers (conectados y conocidos)
4. Registrar bootstrap peers (semillas iniciales)
5. Crear set de mensajes vistos (prevenir loops)
6. Configurar límites de red (conexiones, timeouts)
7. Generar wallet propia (identidad criptográfica)
8. Inicializar mempool vacío
9. Configurar balance inicial (100 coins)
10. Configurar logger (logs/node_5000.log)
```

**¿Por qué bootstrap_peers?**

En una red P2P, necesitas al menos un peer conocido para empezar. Los bootstrap peers son como "puntos de entrada" a la red:

```
Nodo 1 (seed):    bootstrap = []           ← No necesita, es el primero
Nodo 2:           bootstrap = [Nodo 1]     ← Conecta a Nodo 1
Nodo 3:           bootstrap = [Nodo 1]     ← Conecta a Nodo 1
Nodo 4:           bootstrap = [Nodo 2]     ← Conecta a Nodo 2

Después del gossip:
Todos conocen a todos (red mesh completa)
```

**¿Por qué `node_id = f"node_{port}"`?**

Usar el puerto como ID garantiza:
- IDs consistentes entre ejecuciones (mismo puerto = mismo ID)
- Logs predecibles (`logs/node_5000.log` siempre es el mismo archivo)
- Fácil identificación en debugging

Bitcoin usa identificadores aleatorios porque los nodos pueden cambiar de IP/puerto. En este demo, los puertos son fijos.

---

## Función `start`

```python
async def start(self):
    self.logger.info(f"[INIT] Iniciando nodo {self.id} en {self.host}:{self.port}")
    
    server = await websockets.serve(
        self.handle_incoming_connection,
        self.host,
        self.port
    )
    
    self.logger.info(f"[OK] Servidor escuchando en ws://{self.host}:{self.port}")
    
    asyncio.create_task(self.connect_to_bootstrap())
    asyncio.create_task(self.gossip_loop())
    asyncio.create_task(self.ping_loop())
    asyncio.create_task(self.cleanup_loop())
    
    await asyncio.Future()
```

**¿Qué hace?**

Inicia el nodo completo: levanta el servidor WebSocket y lanza todas las tareas en background.

**Proceso paso a paso:**

```
1. Levantar servidor WebSocket
   └─ Escucha en puerto especificado
   └─ Cada conexión entrante → handle_incoming_connection()

2. Iniciar tareas en background:
   ├─ connect_to_bootstrap() → Conecta a peers iniciales
   ├─ gossip_loop()          → Solicita peers cada 60s
   ├─ ping_loop()            → Keep-alive cada 30s
   └─ cleanup_loop()         → Limpia peers obsoletos cada 5min

3. Esperar infinitamente
   └─ await asyncio.Future() mantiene el servidor corriendo
```

**¿Por qué `asyncio.create_task()`?**

Crea tareas que corren en paralelo sin bloquear. Sin esto, el nodo esperaría a que una tarea terminara antes de iniciar la siguiente:

```python
# SIN asyncio.create_task (bloqueante):
await self.gossip_loop()     # ← Se queda aquí para siempre
await self.ping_loop()       # ← NUNCA llega aquí

# CON asyncio.create_task (paralelo):
asyncio.create_task(self.gossip_loop())   # ← Inicia y continúa
asyncio.create_task(self.ping_loop())     # ← Inicia y continúa
# Ambas corren simultáneamente
```

**¿Por qué `await asyncio.Future()`?**

Es un "esperar infinito". Sin esto, la función `start()` terminaría inmediatamente y el servidor se cerraría. Bitcoin hace lo mismo con un loop infinito.

---

## Función `handle_incoming_connection`

```python
async def handle_incoming_connection(self, websocket, path):
    peer_address = None
    
    try:
        remote = websocket.remote_address
        self.logger.info(f"[INCOMING] Conexión desde {remote}")
        
        # Esperar version message
        raw_msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
        msg = json.loads(raw_msg)
        
        if msg['type'] == 'version':
            payload = msg['payload']
            peer_address = f"{payload['host']}:{payload['port']}"
            
            # Registrar peer
            if peer_address not in self.peers_known:
                self.peers_known[peer_address] = PeerInfo(
                    payload['host'],
                    payload['port'],
                    payload.get('node_id')
                )
            
            peer_info = self.peers_known[peer_address]
            
            # Enviar verack
            verack = create_message('verack', {'node_id': self.id})
            await websocket.send(json.dumps(verack))
            
            # Marcar como conectado
            self.peers_connected[peer_address] = websocket
            peer_info.mark_connected()
            
            self.logger.info(f"[SUCCESS] Peer conectado: {peer_address}")
            
            # Escuchar mensajes
            await self.listen_to_peer(websocket, peer_address)
            
    except asyncio.TimeoutError:
        self.logger.error(f"[TIMEOUT] No se recibió version a tiempo")
    except Exception as e:
        self.logger.error(f"[ERROR] Error en conexión entrante: {e}")
    finally:
        if peer_address and peer_address in self.peers_connected:
            del self.peers_connected[peer_address]
            self.peers_known[peer_address].mark_disconnected()
            self.logger.info(f"[REMOVED] Peer removido: {peer_address}")
```

**¿Qué hace?**

Maneja una conexión entrante de otro nodo realizando el handshake y registrando el peer.

**Flujo del handshake (como Bitcoin):**

```
Nodo A (servidor)                    Nodo B (cliente)
      │                                      │
      │◄──────── version {node_id} ──────────┤
      │                                      │
      │  (valida, registra peer)             │
      │                                      │
      ├─────────► verack {node_id} ─────────►│
      │                                      │
      │  Conexión establecida                │
      │  Iniciar listen_to_peer()            │
```

**¿Por qué timeout de 10 segundos?**

Previene ataques de "slow handshake" donde un atacante abre conexiones pero nunca envía el mensaje `version`, consumiendo recursos. Bitcoin usa timeouts similares.

**¿Por qué `try/except/finally`?**

- `try`: Maneja la conexión normalmente
- `except`: Captura errores (timeout, desconexión abrupta)
- `finally`: Limpia recursos **siempre** (incluso si hay error)

---

## Función `connect_to_peer`

```python
async def connect_to_peer(self, peer_info: PeerInfo):
    if peer_info.is_connected:
        return
    
    uri = f"ws://{peer_info.host}:{peer_info.port}"
    self.logger.info(f"[CONNECT] Intentando conectar a {uri}")
    
    peer_info.mark_attempt()
    
    try:
        websocket = await asyncio.wait_for(
            websockets.connect(uri),
            timeout=10.0
        )
        
        # Enviar version
        version = create_message('version', {
            'node_id': self.id,
            'host': self.host,
            'port': self.port
        })
        await websocket.send(json.dumps(version))
        
        # Esperar verack
        raw_msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
        verack = json.loads(raw_msg)
        
        if verack['type'] == 'verack':
            addr = peer_info.get_address()
            self.peers_connected[addr] = websocket
            peer_info.mark_connected()
            
            self.logger.info(f"[SUCCESS] Conectado a {addr}")
            
            asyncio.create_task(self.listen_to_peer(websocket, addr))
            
            # Solicitar peers inmediatamente
            await self.request_peers(websocket)
            
    except asyncio.TimeoutError:
        self.logger.error(f"[TIMEOUT] Timeout conectando a {uri}")
        peer_info.mark_failure()
    except Exception as e:
        self.logger.error(f"[FAIL] No se pudo conectar a {uri} - {e}")
        peer_info.mark_failure()
```

**¿Qué hace?**

Inicia una conexión saliente a otro peer y realiza el handshake como cliente.

**Flujo:**

```
1. Verificar que no esté ya conectado
2. Construir URI (ws://localhost:5000)
3. Marcar intento de conexión (estadísticas)
4. Conectar con timeout de 10s
5. Enviar mensaje version
6. Esperar mensaje verack (timeout 10s)
7. Si recibe verack:
   ├─ Registrar en peers_connected
   ├─ Marcar como conectado
   ├─ Iniciar listen_to_peer() en background
   └─ Solicitar peers inmediatamente (gossip)
8. Si falla:
   └─ Marcar fallo (estadísticas)
```

**¿Por qué solicitar peers inmediatamente?**

Parte del gossip protocol. Apenas te conectas a un peer, le preguntas "¿qué otros peers conoces?". Así la red se descubre rápidamente:

```
T=0s:  Nodo 2 conecta a Nodo 1
T=1s:  Nodo 2 pide peers a Nodo 1
T=2s:  Nodo 1 responde: "Conozco a Nodo 3, 4, 5"
T=3s:  Nodo 2 descubre 3 peers nuevos
T=4s:  Nodo 2 conecta a Nodos 3, 4, 5
```

---

## Función `listen_to_peer`

```python
async def listen_to_peer(self, websocket, peer_address: str):
    try:
        async for raw_message in websocket:
            msg = json.loads(raw_message)
            
            if validate_message(msg):
                await self.handle_message(msg, websocket)
                
    except websockets.exceptions.ConnectionClosed:
        self.logger.warning(f"[DISCONNECT] Peer desconectado: {peer_address}")
    except Exception as e:
        self.logger.error(f"[ERROR] Error escuchando a {peer_address}: {e}")
    finally:
        if peer_address in self.peers_connected:
            del self.peers_connected[peer_address]
        if peer_address in self.peers_known:
            self.peers_known[peer_address].mark_disconnected()
```

**¿Qué hace?**

Loop infinito que escucha mensajes de un peer específico hasta que se desconecta.

**Proceso:**

```
1. Esperar mensaje (async for)
2. Deserializar JSON
3. Validar checksum
4. Procesar con handle_message()
5. Repetir hasta desconexión
6. Limpiar recursos (finally)
```

**¿Por qué `async for`?**

Es la forma Pythonic de iterar sobre un stream asíncrono. Equivalente a:

```python
# Forma explícita:
while True:
    raw_message = await websocket.recv()
    # ... procesar

# Forma Pythonic (async for):
async for raw_message in websocket:
    # ... procesar
```

---

## Función `handle_message`

```python
async def handle_message(self, msg: dict, sender_ws):
    msg_id = msg['id']
    msg_type = msg['type']
    
    # Anti-loop
    if msg_id in self.messages_seen:
        return
    
    self.messages_seen.add(msg_id)
    
    if len(self.messages_seen) > self.MAX_MESSAGES_SEEN:
        self.messages_seen = set(list(self.messages_seen)[-500:])
    
    self.logger.info(f"[MSG] Mensaje recibido: {msg_type} (ID: {msg_id[:8]}...)")
    
    # Router de mensajes
    if msg_type == 'ping':
        await self.handle_ping(msg, sender_ws)
    elif msg_type == 'pong':
        self.logger.info(f"[PONG] PONG recibido")
    elif msg_type == 'getaddr':
        await self.handle_getaddr(sender_ws)
    elif msg_type == 'addr':
        await self.handle_addr(msg['payload'])
    elif msg_type == 'hello':
        data = msg['payload'].get('data', '')
        self.logger.info(f"[HELLO] HELLO recibido: {data}")
        await self.broadcast_message(msg, exclude_ws=sender_ws)
    elif msg_type == 'tx':
        await self.handle_tx(msg, sender_ws)
    else:
        self.logger.warning(f"[WARN] Tipo de mensaje desconocido: {msg_type}")
```

**¿Qué hace?**

Router central que despacha mensajes a sus handlers específicos y previene loops de mensajes.

**Anti-loop mechanism:**

```
Nodo A envía mensaje M (ID: abc123)
  │
  ├─► Nodo B recibe M
  │   └─ Agrega abc123 a messages_seen
  │   └─ Propaga M a Nodos C, D, E
  │
  ├─► Nodo C recibe M
  │   └─ Agrega abc123 a messages_seen
  │   └─ Propaga M a Nodos B, D, E
  │
  ├─► Nodo B recibe M de nuevo (de C)
      └─ abc123 YA en messages_seen
      └─ IGNORA (no propaga)

Sin anti-loop: mensajes circulan infinitamente
Con anti-loop: cada mensaje se procesa una sola vez
```

**¿Por qué limpiar `messages_seen`?**

Si el nodo corre días/semanas, el set crecería infinitamente. Al mantener solo los últimos 500 IDs:
- Previene loops de mensajes recientes
- No consume memoria infinita
- Mensajes muy viejos pueden re-procesarse (no importa)

**Tipos de mensajes:**

| Tipo | Handler | Propósito |
|------|---------|-----------|
| `ping` | `handle_ping()` | Keep-alive, responde con pong |
| `pong` | (log) | Respuesta a ping |
| `getaddr` | `handle_getaddr()` | Solicita lista de peers |
| `addr` | `handle_addr()` | Recibe lista de peers |
| `hello` | `broadcast_message()` | Mensaje de prueba (Fase 1) |
| `tx` | `handle_tx()` | Transacción de blockchain |

---

## Función `handle_tx`

```python
async def handle_tx(self, msg: dict, sender_ws):
    try:
        tx_data = msg['payload']
        tx = Transaction.from_dict(tx_data)
        
        # Validar firma
        if not tx.is_valid():
            self.logger.warning(f"[TX] TX inválida recibida")
            return
        
        # Evitar duplicados
        tx_hash = tx.hash()
        if any(t.hash() == tx_hash for t in self.mempool):
            self.logger.info(f"[TX] TX duplicada ignorada: {tx_hash[:16]}...")
            return
        
        # Agregar a mempool
        self.mempool.append(tx)
        self.logger.info(f"[TX] TX agregada al mempool: {tx_hash[:16]}... "
                       f"({tx.from_address[:10]}...→{tx.to_address[:10]}..., {tx.amount})")
        
        # Propagar a otros peers
        await self.broadcast_transaction(tx, exclude_ws=sender_ws)
        
    except Exception as e:
        self.logger.error(f"[TX] Error procesando TX: {e}")
```

**¿Qué hace?**

Procesa una transacción recibida de la red: valida, agrega al mempool y propaga.

**Flujo de validación:**

```
1. Deserializar TX desde JSON
2. Validar firma digital Ed25519
   └─ Si inválida: rechazar y terminar
3. Calcular TXID (hash)
4. Verificar duplicados en mempool
   └─ Si duplicada: ignorar (ya la tenemos)
5. Agregar a mempool local
6. Propagar a todos los peers (menos el remitente)
```

**¿Por qué `exclude_ws=sender_ws`?**

No reenviar la TX al peer que nos la mandó. Sería ineficiente:

```
Nodo A → TX → Nodo B
Nodo B → TX → Nodo A  ← Innecesario, A ya la tiene
```

**¿Por qué validar firma?**

Prevenir spam y TXs falsas. Sin validación, cualquiera podría crear TXs inválidas y saturar la red.

---

## Función `broadcast_transaction`

```python
async def broadcast_transaction(self, tx: Transaction, exclude_ws=None):
    msg = create_message('tx', tx.to_dict())
    
    for peer_addr, peer_ws in self.peers_connected.items():
        if peer_ws == exclude_ws:
            continue
        
        try:
            await peer_ws.send(json.dumps(msg))
        except Exception as e:
            self.logger.error(f"[TX] Error propagando a {peer_addr}: {e}")
```

**¿Qué hace?**

Propaga una transacción a todos los peers conectados (menos uno opcional).

**Proceso:**

```
1. Crear mensaje tipo 'tx' con la TX serializada
2. Para cada peer conectado:
   ├─ Si es el peer excluido: skip
   ├─ Intentar enviar mensaje
   └─ Si falla: loggear error pero continuar con otros
3. No esperar confirmación (fire-and-forget)
```

**¿Por qué no esperar confirmación?**

Bitcoin tampoco lo hace. La propagación P2P es "best effort":
- Si un peer está caído, el mensaje falla silenciosamente
- Los otros peers eventualmente propagarán la TX
- La red es resiliente por redundancia

---

## Función `create_transaction`

```python
def create_transaction(self, to_address: str, amount: float) -> Transaction:
    tx = Transaction(
        from_address=self.wallet.address,
        to_address=to_address,
        amount=amount
    )
    tx.sign(self.wallet)
    
    self.mempool.append(tx)
    self.logger.info(f"[TX] TX creada: {tx.hash()[:16]}... ({amount} → {to_address[:10]}...)")
    
    return tx
```

**¿Qué hace?**

Crea una nueva transacción desde este nodo, la firma y la agrega al mempool.

**Proceso:**

```
1. Crear TX (from: wallet propia, to: destinatario)
2. Firmar con wallet del nodo (Ed25519)
3. Agregar a mempool local
4. Loggear creación
5. Retornar TX (para broadcast posterior)
```

**¿Por qué no hace broadcast automáticamente?**

Para dar flexibilidad. El llamador decide cuándo propagar:

```python
# Crear y propagar inmediatamente:
tx = node.create_transaction(addr, 10)
await node.broadcast_transaction(tx)

# Crear varias y propagar en batch:
tx1 = node.create_transaction(addr1, 10)
tx2 = node.create_transaction(addr2, 5)
await node.broadcast_transaction(tx1)
await node.broadcast_transaction(tx2)
```

---

## Función `get_balance`

```python
def get_balance(self) -> float:
    balance = self.balance  # Inicial 100
    
    for tx in self.mempool:
        if tx.from_address == self.wallet.address:
            balance -= tx.amount
        if tx.to_address == self.wallet.address:
            balance += tx.amount
    
    return balance
```

**¿Qué hace?**

Calcula el balance actual del nodo sumando/restando transacciones del mempool.

**Proceso:**

```
Balance inicial: 100

Para cada TX en mempool:
  Si TX.from == mi address:
    balance -= TX.amount   (envié fondos)
  
  Si TX.to == mi address:
    balance += TX.amount   (recibí fondos)

Retornar balance final
```

**Ejemplo:**

```
Balance inicial: 100

TX1: Alice → Este nodo (10)
  balance = 100 + 10 = 110

TX2: Este nodo → Bob (5)
  balance = 110 - 5 = 105

Balance final: 105
```

**¿Por qué es "simulado"?**

Sin blockchain confirmada, no hay fuente de verdad. Este balance es optimista (asume que todas las TXs en mempool se confirmarán).

En Bitcoin real, el balance se calcula desde la blockchain confirmada, no del mempool.

---

## Gossip Protocol Functions

### `handle_getaddr`

```python
async def handle_getaddr(self, sender_ws):
    valid_peers = [
        p for p in self.peers_known.values()
        if p.is_connected or (datetime.now().timestamp() - p.last_seen < 3600)
    ]
    
    valid_peers.sort(key=lambda p: p.last_seen, reverse=True)
    
    to_share = valid_peers[:self.MAX_PEERS_TO_SHARE]
    
    addr_msg = create_message('addr', {
        'peers': [p.to_dict() for p in to_share]
    })
    
    await sender_ws.send(json.dumps(addr_msg))
    self.logger.info(f"[ADDR] Enviados {len(to_share)} peers")
```

**¿Qué hace?**

Responde a una solicitud de peers enviando hasta 10 peers válidos.

**Criterios de selección:**

1. **Válidos:** Conectados actualmente O vistos en la última hora
2. **Ordenados:** Los más recientes primero
3. **Limitados:** Máximo 10 (prevenir spam)

**¿Por qué máximo 10?**

Bitcoin también limita (1000 en Bitcoin, 10 en este demo). Previene:
- Mensajes gigantes que consumen bandwidth
- Ataques de amplificación
- Sobrecarga del receptor

### `handle_addr`

```python
async def handle_addr(self, payload: dict):
    peers_list = payload['peers']
    new_peers_count = 0
    
    for peer_data in peers_list:
        addr = f"{peer_data['host']}:{peer_data['port']}"
        
        if addr not in self.peers_known:
            peer = PeerInfo.from_dict(peer_data)
            self.peers_known[addr] = peer
            new_peers_count += 1
            self.logger.info(f"[NEW PEER] Descubierto: {addr}")
    
    if new_peers_count > 0:
        self.logger.info(f"[GOSSIP] {new_peers_count} nuevos peers descubiertos. "
                        f"Total conocidos: {len(self.peers_known)}")
```

**¿Qué hace?**

Procesa una lista de peers recibida, agregando los nuevos al registro de peers conocidos.

**Proceso:**

```
Para cada peer en la lista:
  1. Construir address (host:port)
  2. Si NO está en peers_known:
     ├─ Crear PeerInfo
     ├─ Agregar a peers_known
     └─ Loggear descubrimiento
  3. Si YA está: ignorar (ya lo conocemos)

Loggear total de nuevos descubiertos
```

**Resultado del gossip:**

```
Estado inicial:
  Nodo 4 conoce: [Nodo 2]

Paso 1 - Solicita peers a Nodo 2:
  Nodo 4 → getaddr → Nodo 2

Paso 2 - Recibe respuesta:
  Nodo 2 → addr [Nodo 1, Nodo 3] → Nodo 4

Paso 3 - Procesa con handle_addr:
  Nodo 4 descubre: Nodo 1 (nuevo)
  Nodo 4 descubre: Nodo 3 (nuevo)

Estado final:
  Nodo 4 conoce: [Nodo 1, Nodo 2, Nodo 3]
```

---

## Loops Periódicos

### `gossip_loop`

```python
async def gossip_loop(self):
    await asyncio.sleep(10)  # Espera inicial
    
    while True:
        try:
            self.logger.info(f"[GETADDR] Solicitando peers")
            
            for peer_ws in list(self.peers_connected.values()):
                await self.request_peers(peer_ws)
            
            self.logger.info(f"[GOSSIP] Ciclo de gossip completado. "
                           f"Conocidos: {len(self.peers_known)}, "
                           f"Conectados: {len(self.peers_connected)}")
            
        except Exception as e:
            self.logger.error(f"[ERROR] Error en gossip loop: {e}")
        
        await asyncio.sleep(self.GOSSIP_INTERVAL)
```

**¿Qué hace?**

Loop infinito que solicita peers a todos los conectados cada 60 segundos.

**¿Por qué espera 10s inicial?**

Dar tiempo a que se establezcan conexiones antes del primer gossip.

### `ping_loop`

```python
async def ping_loop(self):
    await asyncio.sleep(15)
    
    while True:
        try:
            for peer_addr, peer_ws in list(self.peers_connected.items()):
                ping = create_message('ping', {'nonce': peer_addr})
                await peer_ws.send(json.dumps(ping))
        except Exception as e:
            self.logger.error(f"[ERROR] Error en ping loop: {e}")
        
        await asyncio.sleep(self.PING_INTERVAL)
```

**¿Qué hace?**

Envía ping a todos los peers cada 30s para mantener conexiones vivas.

**¿Por qué es necesario?**

Detecta peers muertos y previene timeouts de conexión:

```
Sin ping:
  Nodo A ─── conexión idle 10 min ───► Nodo B
  Firewall cierra conexión por inactividad
  Ambos nodos creen que siguen conectados

Con ping:
  Nodo A ─── ping cada 30s ───► Nodo B
  Si ping falla → detecta desconexión inmediatamente
```

### `cleanup_loop`

```python
async def cleanup_loop(self):
    await asyncio.sleep(60)
    
    while True:
        try:
            cutoff = datetime.now().timestamp() - 86400  # 24 horas
            
            to_remove = [
                addr for addr, peer in self.peers_known.items()
                if not peer.is_connected and peer.last_seen < cutoff
            ]
            
            for addr in to_remove:
                del self.peers_known[addr]
                self.logger.info(f"[CLEANUP] Peer obsoleto removido: {addr}")
            
        except Exception as e:
            self.logger.error(f"[ERROR] Error en cleanup: {e}")
        
        await asyncio.sleep(self.CLEANUP_INTERVAL)
```

**¿Qué hace?**

Limpia peers que no se han visto en 24 horas cada 5 minutos.

**¿Por qué limpiar?**

Peers obsoletos consumen memoria. Si un peer no se ve en 24h, probablemente:
- Cambió de IP/puerto
- Se cerró permanentemente
- Ya no es parte de la red

---

## Comparación con Bitcoin

| Aspecto | Bitcoin Core | Este Demo |
|---------|--------------|-----------|
| Protocolo de transporte | TCP puro | WebSockets |
| Handshake | version/verack | version/verack (idéntico) |
| Gossip | getaddr/addr | getaddr/addr (idéntico) |
| Keep-alive | ping/pong | ping/pong (idéntico) |
| Anti-loop | INV messages hash | message ID (similar) |
| Límites de conexión | 8 out / 125 in | 8 out / 125 in (idéntico) |
| Peers compartidos | 1000 max | 10 max (simplificado) |
| Limpieza de peers | 24h | 24h (idéntico) |
| Mempool | UTXO-based | Balance simple |
| Propagación TX | INV→GETDATA→TX | TX directa (simplificado) |

---

## Flujo Completo de Descubrimiento

```
T=0s - Nodo 4 inicia con bootstrap=[Nodo 2]
  └─ peers_known: {Nodo 2}
  └─ peers_connected: {}

T=1s - Conecta a Nodo 2
  └─ Handshake version/verack
  └─ peers_connected: {Nodo 2}
  └─ Solicita peers (getaddr)

T=2s - Recibe addr de Nodo 2
  └─ Descubre: [Nodo 1, Nodo 3, Nodo 5]
  └─ peers_known: {Nodo 1, Nodo 2, Nodo 3, Nodo 5}

T=3s - Conecta a peers nuevos
  └─ Conecta a Nodo 1, 3, 5 en paralelo
  └─ peers_connected: {Nodo 1, Nodo 2, Nodo 3, Nodo 5}

T=4s - Solicita peers a todos
  └─ Descubre peers de segundo nivel
  └─ Red completamente conectada

T=60s - Primer gossip loop
  └─ Solicita peers de nuevo (mantener actualizado)

T=90s - Primer ping loop
  └─ Envía ping a todos (keep-alive)
```

---

## Tests Asociados: `test_network.py`

| Test | Funcionalidad probada |
|------|----------------------|
| Levantar 5 nodos | `__init__`, `start()` |
| Handshake completo | `handle_incoming_connection()`, `connect_to_peer()` |
| Gossip descubre peers | `gossip_loop()`, `handle_getaddr()`, `handle_addr()` |
| Mensajes se propagan | `handle_message()`, `broadcast_message()` |
| TX se propagan | `handle_tx()`, `broadcast_transaction()` |
| Balance actualiza | `create_transaction()`, `get_balance()` |

---

*Documento: `DOC_network_p2p_node.md` — Demo Blockchain Fases 1, 1.5 y 2.1*
