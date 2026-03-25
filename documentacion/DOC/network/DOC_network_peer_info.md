# Documentación Técnica: `network/peer_info.py`

---

## Propósito del Archivo

`peer_info.py` implementa `PeerInfo` — una estructura de datos que representa el conocimiento que un nodo tiene sobre otro nodo de la red. Es el equivalente a la libreta de contactos del nodo P2P.

**Analogía:** `PeerInfo` es como una ficha de contacto en una libreta de direcciones donde además de los datos de contacto (IP y puerto), guardas cuándo lo viste por última vez, si está disponible en este momento y cuántas veces has intentado llamarle sin éxito.

**Equivalente en Bitcoin:** `CAddress` en el código fuente de Bitcoin Core — estructura que guarda información sobre peers conocidos incluyendo timestamps y estadísticas de conectividad.

---

## Clase `PeerInfo`

```python
class PeerInfo:
```

**Atributos de instancia:**

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `host` | `str` | IP o hostname del peer |
| `port` | `int` | Puerto P2P WebSocket |
| `node_id` | `Optional[str]` | Identificador del nodo (ej. `node_5000`) |
| `first_seen` | `float` | Unix timestamp de primera vez visto |
| `last_seen` | `float` | Unix timestamp de última actividad |
| `last_attempt` | `Optional[float]` | Unix timestamp del último intento de conexión |
| `is_connected` | `bool` | True si hay conexión activa ahora |
| `connection_failures` | `int` | Contador de fallos de conexión consecutivos |

---

## Ciclo de vida de un `PeerInfo`

```
PeerInfo creado (descubierto via gossip o bootstrap)
        │
        ▼
mark_attempt()  ← intentando conectar
        │
        ├── Éxito → mark_connected()
        │               is_connected = True
        │               connection_failures = 0
        │               last_seen = now
        │
        └── Fallo → mark_failure()
                        connection_failures += 1
                        is_connected = False

Durante conexión activa:
    mark_seen()  ← al recibir mensajes (actualiza last_seen)

Al desconectar:
    mark_disconnected()  ← is_connected = False
```

---

## Funciones de estado

### `mark_seen`
```python
def mark_seen(self):
    self.last_seen = datetime.now().timestamp()
```
Actualiza `last_seen`. Se llama al recibir cualquier mensaje del peer. El cleanup loop elimina peers que llevan más de 24 horas sin actividad.

### `mark_attempt`
```python
def mark_attempt(self):
    self.last_attempt = datetime.now().timestamp()
```
Registra cuándo se intentó conectar. Útil para evitar reintentos demasiado frecuentes.

### `mark_failure`
```python
def mark_failure(self):
    self.connection_failures += 1
    self.is_connected = False
```
Incrementa el contador de fallos. Los peers con muchos fallos consecutivos se consideran inaccesibles y se priorizan menos en los intentos de conexión.

### `mark_connected`
```python
def mark_connected(self):
    self.is_connected = True
    self.connection_failures = 0
    self.mark_seen()
```
Marca conexión exitosa, resetea los fallos y actualiza `last_seen`.

### `mark_disconnected`
```python
def mark_disconnected(self):
    self.is_connected = False
```
Marca que la conexión se cerró. No incrementa `connection_failures` — una desconexión normal no es un fallo.

---

## Serialización

### `to_dict`
```python
def to_dict(self) -> dict:
    return {
        'host':      self.host,
        'port':      self.port,
        'node_id':   self.node_id,
        'last_seen': self.last_seen
    }
```

Se usa al enviar `MSG_ADDR` — compartir la lista de peers conocidos con otros nodos. Solo se incluyen los datos esenciales para que el destinatario pueda conectarse.

**¿Por qué no incluir `connection_failures` o `is_connected`?**

Son datos locales — el fallo de conexión desde tu nodo no significa que otros nodos también fallen. Cada nodo mantiene sus propias estadísticas.

### `from_dict`
```python
@staticmethod
def from_dict(data: dict) -> 'PeerInfo':
    peer = PeerInfo(data['host'], data['port'], data.get('node_id'))
    peer.last_seen = data.get('last_seen', datetime.now().timestamp())
    return peer
```

Reconstruye un `PeerInfo` desde un mensaje `MSG_ADDR` recibido. El `last_seen` se preserva del mensaje original para mantener información histórica.

---

## Uso en `P2PNode`

```python
# Dos diccionarios en P2PNode:
self.peers_known:     Dict[str, PeerInfo] = {}  # todos los conocidos
self.peers_connected: Dict[str, ws]       = {}  # solo los activos ahora

# Al recibir MSG_ADDR (gossip):
if addr not in self.peers_known:
    self.peers_known[addr] = PeerInfo.from_dict(peer_data)

# Al conectar exitosamente:
self.peers_known[addr].mark_connected()
self.peers_connected[addr] = websocket

# Al desconectar:
self.peers_connected.pop(addr)
self.peers_known[addr].mark_disconnected()

# Al hacer cleanup (cada CLEANUP_INTERVAL segundos):
for addr, peer in self.peers_known.items():
    if not peer.is_connected and (now - peer.last_seen) > 86400:
        del self.peers_known[addr]  # 24h sin actividad → eliminar
```

---

## Diferencia con Bitcoin

En Bitcoin, `CAddress` tiene campos adicionales como `nServices` (qué servicios expone el nodo: full node, segwit, etc.) y se almacena persistentemente en disco en `peers.dat`. En este demo `PeerInfo` es más simple y vive solo en memoria — al reiniciar el nodo, pierde el conocimiento de sus peers y debe redescubrirlos via seed o bootstrap.

---

*Documento: `DOC_network_peer_info.md` — Demo Blockchain*
