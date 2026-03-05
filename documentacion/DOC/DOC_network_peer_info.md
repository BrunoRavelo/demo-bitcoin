# Documentación Técnica: `network/peer_info.py`

---

## Propósito del Archivo

`peer_info.py` define la clase que almacena información sobre otros nodos de la red. Cada instancia representa un peer (conectado o no) con su historial de conexiones, timestamps y estado actual.

**Analogía:** Un `PeerInfo` es como una tarjeta de contacto que contiene:
- **Dirección** (host:port) → cómo contactarlo
- **Estado** (conectado/desconectado) → si está disponible ahora
- **Historial** (intentos, fallos) → qué tan confiable es
- **Última vez visto** → qué tan reciente es la info

---

## Inspiración: Bitcoin's CAddress

Esta clase está inspirada en `CAddress` de Bitcoin Core, que almacena información de peers en la red.

**Comparación:**

| Aspecto | Bitcoin CAddress | Este Demo PeerInfo |
|---------|-----------------|-------------------|
| Host/Port | ✅ IPv4/IPv6 + puerto | ✅ host + port |
| Timestamp | ✅ nTime (última vez visto) | ✅ first_seen, last_seen |
| Estado de conexión | ✅ Implícito en lógica | ✅ is_connected |
| Intentos de conexión | ✅ nAttempts | ✅ connection_failures |
| Serialización | ✅ Binaria | ✅ JSON (to_dict) |
| Concepto | ✅ Idéntico | ✅ Idéntico |

---

## Dependencias

```python
from datetime import datetime
from typing import Optional
```

| Import | Propósito |
|--------|-----------|
| `datetime` | Timestamps de conexiones |
| `Optional` | Type hint para campos opcionales |

---

## Clase `PeerInfo`

```python
class PeerInfo:
```

Representa información sobre un peer en la red, incluyendo su dirección, estado de conexión y estadísticas.

**Atributos de instancia:**

| Atributo | Tipo | Descripción | Cuándo se actualiza |
|----------|------|-------------|---------------------|
| `host` | `str` | IP o hostname | `__init__` |
| `port` | `int` | Puerto WebSocket | `__init__` |
| `node_id` | `Optional[str]` | ID del nodo (ej: "node_5000") | `__init__` o handshake |
| `first_seen` | `float` | Timestamp de primera vez conocido | `__init__` |
| `last_seen` | `float` | Timestamp de última vez visto | `mark_seen()` |
| `last_attempt` | `Optional[float]` | Timestamp de último intento de conexión | `mark_attempt()` |
| `is_connected` | `bool` | ¿Conectado actualmente? | `mark_connected()` / `mark_disconnected()` |
| `connection_failures` | `int` | Contador de fallos consecutivos | `mark_failure()` / reset en `mark_connected()` |

---

## Función `__init__`

```python
def __init__(self, host: str, port: int, node_id: Optional[str] = None):
    self.host = host
    self.port = port
    self.node_id = node_id
    
    self.first_seen = datetime.now().timestamp()
    self.last_seen = datetime.now().timestamp()
    self.last_attempt = None
    
    self.is_connected = False
    self.connection_failures = 0
```

**¿Qué hace?**

Crea un registro de peer con información básica e inicializa todos los timestamps y contadores.

**Proceso:**

```
1. Guardar dirección de red
   ├─ host: "localhost" o "192.168.1.100"
   └─ port: 5000, 5001, etc.

2. Guardar identificador (opcional)
   └─ node_id: "node_5000" (conocido después del handshake)

3. Inicializar timestamps
   ├─ first_seen: ahora (nunca cambia)
   ├─ last_seen: ahora (se actualiza)
   └─ last_attempt: None (todavía no intentamos conectar)

4. Inicializar estado
   ├─ is_connected: False (recién descubierto)
   └─ connection_failures: 0 (sin fallos todavía)
```

**¿Por qué `node_id` es opcional?**

Al descubrir un peer mediante gossip, solo conoces su dirección:

```python
# Descubrimiento por gossip:
peer = PeerInfo("localhost", 5001)
# node_id = None (todavía no sabemos su ID)

# Después del handshake:
peer.node_id = "node_5001"
# Ahora sí conocemos su ID
```

**Ejemplo:**

```python
# Bootstrap peer (dirección conocida)
peer = PeerInfo("localhost", 5000)
# peer.first_seen = 1707234567.123
# peer.last_seen = 1707234567.123
# peer.is_connected = False
# peer.connection_failures = 0
```

---

## Función `to_dict`

```python
def to_dict(self) -> dict:
    return {
        'host': self.host,
        'port': self.port,
        'node_id': self.node_id,
        'last_seen': self.last_seen
    }
```

**¿Qué hace?**

Serializa el peer a un diccionario para transmitir por la red en mensajes `addr`.

**¿Qué campos se envían?**

| Campo | ¿Se envía? | Por qué |
|-------|-----------|---------|
| `host` | ✅ Sí | Necesario para conectar |
| `port` | ✅ Sí | Necesario para conectar |
| `node_id` | ✅ Sí | Identificación del peer |
| `last_seen` | ✅ Sí | Indica qué tan reciente es la info |
| `first_seen` | ❌ No | Solo relevante localmente |
| `last_attempt` | ❌ No | Solo relevante localmente |
| `is_connected` | ❌ No | Cambia constantemente |
| `connection_failures` | ❌ No | Información privada |

**¿Por qué NO enviar todo?**

- **Privacidad:** `connection_failures` es info interna
- **Eficiencia:** Menos datos = mensajes más pequeños
- **Relevancia:** `is_connected` solo importa al remitente

**Uso típico:**

```python
# Nodo A comparte sus peers conocidos
peers_to_share = [peer1, peer2, peer3]

addr_msg = create_message('addr', {
    'peers': [p.to_dict() for p in peers_to_share]
})

# Resultado:
# {
#   'type': 'addr',
#   'payload': {
#     'peers': [
#       {'host': 'localhost', 'port': 5001, 'node_id': 'node_5001', 'last_seen': 1707234567},
#       {'host': 'localhost', 'port': 5002, 'node_id': 'node_5002', 'last_seen': 1707234568}
#     ]
#   }
# }
```

---

## Función estática `from_dict`

```python
@staticmethod
def from_dict(data: dict) -> 'PeerInfo':
    peer = PeerInfo(data['host'], data['port'], data.get('node_id'))
    peer.last_seen = data.get('last_seen', datetime.now().timestamp())
    return peer
```

**¿Qué hace?**

Deserializa un peer desde un diccionario recibido por la red (inverso de `to_dict`).

**¿Por qué es `@staticmethod`?**

Porque crea una **nueva instancia** desde datos, no opera sobre una instancia existente.

**Proceso:**

```
1. Crear instancia base
   peer = PeerInfo(host, port, node_id)
   └─ Inicializa todos los campos

2. Sobrescribir last_seen
   peer.last_seen = received_timestamp
   └─ Usar timestamp del remitente (más preciso)

3. Retornar instancia completa
```

**¿Por qué `data.get()` en lugar de `data[]`?**

Tolerancia a cambios de protocolo:

```python
# Con data[] (frágil):
node_id = data['node_id']  # KeyError si no existe

# Con data.get() (robusto):
node_id = data.get('node_id')  # None si no existe, no falla
```

**Uso típico:**

```python
# Nodo B recibe mensaje addr
addr_msg = await websocket.recv()
payload = json.loads(addr_msg)['payload']

# Reconstruir peers
for peer_data in payload['peers']:
    peer = PeerInfo.from_dict(peer_data)
    
    if peer.get_address() not in self.peers_known:
        self.peers_known[peer.get_address()] = peer
```

---

## Función `mark_seen`

```python
def mark_seen(self):
    self.last_seen = datetime.now().timestamp()
```

**¿Qué hace?**

Actualiza el timestamp de última vez visto a ahora.

**¿Cuándo se llama?**

Cuando recibimos cualquier mensaje del peer:

```python
# En p2p_node.py:
async def listen_to_peer(self, websocket, peer_address):
    async for raw_message in websocket:
        # Recibimos mensaje
        peer_info = self.peers_known[peer_address]
        peer_info.mark_seen()  # ← Actualizar timestamp
        
        await self.handle_message(...)
```

**¿Por qué es importante?**

Para el gossip protocol y limpieza:

```python
# Gossip: compartir solo peers recientes
valid_peers = [
    p for p in peers_known.values()
    if datetime.now().timestamp() - p.last_seen < 3600  # última hora
]

# Cleanup: eliminar peers obsoletos
if datetime.now().timestamp() - peer.last_seen > 86400:  # 24 horas
    del peers_known[peer.get_address()]
```

---

## Función `mark_attempt`

```python
def mark_attempt(self):
    self.last_attempt = datetime.now().timestamp()
```

**¿Qué hace?**

Registra que intentamos conectar a este peer.

**¿Cuándo se llama?**

Justo antes de iniciar una conexión:

```python
# En p2p_node.py:
async def connect_to_peer(self, peer_info):
    peer_info.mark_attempt()  # ← Registrar intento
    
    try:
        websocket = await websockets.connect(uri, timeout=10)
        # ...
```

**¿Para qué sirve?**

Estadísticas y debugging:

```python
# ¿Cuánto tiempo hace que intentamos conectar?
time_since_attempt = datetime.now().timestamp() - peer.last_attempt

# Si han pasado 5 minutos sin éxito, quizás el peer está caído
if time_since_attempt > 300 and not peer.is_connected:
    logger.warning(f"Peer {peer.get_address()} no responde hace 5 min")
```

---

## Función `mark_failure`

```python
def mark_failure(self):
    self.connection_failures += 1
    self.is_connected = False
```

**¿Qué hace?**

Incrementa el contador de fallos y marca el peer como desconectado.

**¿Cuándo se llama?**

Cuando una conexión falla:

```python
# En p2p_node.py:
try:
    websocket = await websockets.connect(uri, timeout=10)
except asyncio.TimeoutError:
    peer_info.mark_failure()  # ← Registrar fallo
except Exception as e:
    peer_info.mark_failure()  # ← Registrar fallo
```

**¿Para qué sirve el contador?**

Priorización y filtering:

```python
# No intentar conectar a peers con muchos fallos
reliable_peers = [
    p for p in peers_known.values()
    if p.connection_failures < 3
]

# Ordenar por confiabilidad
peers_by_reliability = sorted(
    peers_known.values(),
    key=lambda p: p.connection_failures
)
```

**Comportamiento acumulativo:**

```
Intento 1: Fallo → connection_failures = 1
Intento 2: Fallo → connection_failures = 2
Intento 3: Fallo → connection_failures = 3
Intento 4: Éxito → connection_failures = 0  (reset en mark_connected)
```

---

## Función `mark_connected`

```python
def mark_connected(self):
    self.is_connected = True
    self.connection_failures = 0
    self.mark_seen()
```

**¿Qué hace?**

Marca el peer como conectado exitosamente y resetea el contador de fallos.

**¿Cuándo se llama?**

Después de completar el handshake:

```python
# En p2p_node.py:
if verack['type'] == 'verack':
    peer_info.mark_connected()  # ← Éxito
    self.peers_connected[addr] = websocket
```

**¿Por qué resetear `connection_failures`?**

El peer demostró estar funcional. Fallos previos eran temporales (congestión de red, restart del peer, etc.).

**Estado después de llamar:**

```python
peer.is_connected = True
peer.connection_failures = 0
peer.last_seen = datetime.now().timestamp()  # Actualizado
```

---

## Función `mark_disconnected`

```python
def mark_disconnected(self):
    self.is_connected = False
```

**¿Qué hace?**

Marca el peer como desconectado (pero NO incrementa fallos).

**¿Cuándo se llama?**

Cuando una conexión existente se cierra:

```python
# En p2p_node.py:
async def listen_to_peer(self, websocket, peer_address):
    try:
        async for raw_message in websocket:
            # ... procesar mensajes
    except websockets.exceptions.ConnectionClosed:
        peer_info.mark_disconnected()  # ← Desconexión normal
```

**Diferencia con `mark_failure()`:**

| Función | Uso | Incrementa fallos |
|---------|-----|-------------------|
| `mark_failure()` | Intento de conexión falló | ✅ Sí |
| `mark_disconnected()` | Conexión existente se cerró | ❌ No |

**Razón:**

Una desconexión normal (peer se cerró limpiamente) no es un "fallo". Solo marca que ya no está conectado.

---

## Función `get_address`

```python
def get_address(self) -> str:
    return f"{self.host}:{self.port}"
```

**¿Qué hace?**

Retorna la dirección en formato estándar `"host:port"`.

**¿Por qué una función dedicada?**

Consistencia y uso como clave de diccionario:

```python
# En p2p_node.py:
self.peers_connected: Dict[str, WebSocket] = {}
self.peers_known: Dict[str, PeerInfo] = {}

# Usar como clave
addr = peer_info.get_address()  # "localhost:5000"
self.peers_connected[addr] = websocket
self.peers_known[addr] = peer_info
```

**Alternativa (NO recomendada):**

```python
# Calcular manualmente cada vez (propenso a errores)
addr1 = f"{peer.host}:{peer.port}"
addr2 = peer.host + ":" + str(peer.port)  # Inconsistente
addr3 = f"{peer.port}:{peer.host}"  # ¡Error! Orden invertido
```

---

## Función `__repr__`

```python
def __repr__(self):
    status = "CONNECTED" if self.is_connected else "KNOWN"
    return f"PeerInfo({self.get_address()}, {status}, failures={self.connection_failures})"
```

**¿Qué hace?**

Define cómo se muestra el peer al imprimirlo o en logs.

**Ejemplos:**

```python
peer1 = PeerInfo("localhost", 5000)
print(peer1)
# → PeerInfo(localhost:5000, KNOWN, failures=0)

peer1.mark_connected()
print(peer1)
# → PeerInfo(localhost:5000, CONNECTED, failures=0)

peer2 = PeerInfo("localhost", 5001)
peer2.mark_failure()
peer2.mark_failure()
print(peer2)
# → PeerInfo(localhost:5001, KNOWN, failures=2)
```

---

## Ciclo de Vida de un PeerInfo

```
1. DESCUBRIMIENTO
   peer = PeerInfo("localhost", 5001)
   Estado: KNOWN, failures=0

2. INTENTO DE CONEXIÓN
   peer.mark_attempt()
   Estado: KNOWN, last_attempt=now

3a. ÉXITO
    peer.mark_connected()
    Estado: CONNECTED, failures=0

3b. FALLO
    peer.mark_failure()
    Estado: KNOWN, failures=1

4. DESCONEXIÓN
   peer.mark_disconnected()
   Estado: KNOWN, failures=0 (no cambió)

5. RECONEXIÓN
   peer.mark_attempt()
   peer.mark_connected()
   Estado: CONNECTED, failures=0

6. OBSOLESCENCIA
   if now - peer.last_seen > 24h:
       del peers_known[peer.get_address()]
   Estado: ELIMINADO
```

---

## Máquina de Estados

```
      ┌───────────────────────────────────┐
      │                                   │
      ▼                                   │
   [KNOWN]                                │
      │                                   │
      │ mark_attempt()                    │
      │                                   │
      ▼                                   │
   [ATTEMPTING]                           │
      │                                   │
      ├─► mark_connected()                │
      │        │                          │
      │        ▼                          │
      │   [CONNECTED] ─────────────────┐  │
      │        │                       │  │
      │        │ mark_disconnected()   │  │
      │        └───────────────────────┘  │
      │                                   │
      └─► mark_failure() ─────────────────┘
```

---

## Uso en P2PNode

**Estructura de datos en `p2p_node.py`:**

```python
class P2PNode:
    def __init__(self, ...):
        # Todos los peers conocidos (historial)
        self.peers_known: Dict[str, PeerInfo] = {}
        
        # Subset de peers_known que están conectados actualmente
        self.peers_connected: Dict[str, WebSocket] = {}
```

**Relación:**

```
peers_known = {
    "localhost:5000": PeerInfo(is_connected=True),   ← También en peers_connected
    "localhost:5001": PeerInfo(is_connected=True),   ← También en peers_connected
    "localhost:5002": PeerInfo(is_connected=False),  ← NO en peers_connected
    "localhost:5003": PeerInfo(is_connected=False)   ← NO en peers_connected
}

peers_connected = {
    "localhost:5000": <WebSocket>,
    "localhost:5001": <WebSocket>
}

len(peers_known) >= len(peers_connected)  ← Siempre True
```

---

## Comparación con Bitcoin

| Aspecto | Bitcoin CAddress | Este Demo PeerInfo |
|---------|-----------------|-------------------|
| Estructura | Struct en C++ | Clase en Python |
| Dirección | IP (IPv4/IPv6) + puerto | host (str) + port (int) |
| Timestamp | nTime (uint64) | last_seen (float) |
| Estado | nAttempts, nLastSuccess | connection_failures, is_connected |
| Serialización | Binaria (CDataStream) | JSON (to_dict) |
| Almacenamiento | peers.dat en disco | Solo en memoria |
| Persistencia | ✅ Sobrevive a restart | ❌ Se pierde al cerrar |
| Concepto | ✅ Idéntico | ✅ Idéntico |

**¿Por qué Bitcoin persiste en disco?**

Para recordar buenos peers después de un restart:

```
Bitcoin node cierra:
  peers.dat → guarda 1000 mejores peers

Bitcoin node reinicia:
  peers.dat → carga peers históricos
  Conecta inmediatamente a peers confiables
```

**¿Por qué este demo NO persiste?**

Simplicidad educativa. Para un demo de 5 nodos locales, no es necesario.

---

## Ejemplo Completo

```python
# Descubrir peer por gossip
peer = PeerInfo("localhost", 5001)
print(peer)
# → PeerInfo(localhost:5001, KNOWN, failures=0)

# Primer intento de conexión
peer.mark_attempt()
# Falla por timeout
peer.mark_failure()
print(peer)
# → PeerInfo(localhost:5001, KNOWN, failures=1)

# Segundo intento
peer.mark_attempt()
# Éxito
peer.mark_connected()
print(peer)
# → PeerInfo(localhost:5001, CONNECTED, failures=0)

# Recibir mensaje del peer
peer.mark_seen()
# last_seen actualizado

# Peer se desconecta
peer.mark_disconnected()
print(peer)
# → PeerInfo(localhost:5001, KNOWN, failures=0)

# Serializar para gossip
data = peer.to_dict()
# {'host': 'localhost', 'port': 5001, 'node_id': None, 'last_seen': 1707234567.123}

# Otro nodo deserializa
peer2 = PeerInfo.from_dict(data)
print(peer2)
# → PeerInfo(localhost:5001, KNOWN, failures=0)
```

---

*Documento: `DOC_network_peer_info.md` — Demo Blockchain Fase 1.5 (Gossip Protocol)*
