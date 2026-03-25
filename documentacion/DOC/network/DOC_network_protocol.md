# Documentación Técnica: `network/protocol.py`

---

## Propósito del Archivo

`protocol.py` define el **lenguaje común** de la red P2P — los tipos de mensajes y el formato estándar que todos los nodos usan para comunicarse. Sin un protocolo común, los nodos no podrían entenderse entre sí.

**Analogía:** El protocolo es como el idioma oficial de una organización internacional. Todos los participantes deben hablar el mismo idioma con las mismas reglas gramaticales para que la comunicación funcione.

---

## Protocolo Bitcoin vs Este Demo

| Aspecto | Bitcoin | Este Demo |
|---------|---------|-----------|
| Transporte | TCP binario con magic bytes | WebSocket + JSON |
| Tipos de mensaje | ~30 tipos | 10 esenciales |
| Identificación | Magic bytes (4 bytes fijos) | Checksum SHA256 |
| Detección de errores | Checksum en header | Checksum SHA256 del payload |
| Handshake | version → verack | version → verack ✅ |
| Keep-alive | ping → pong | ping → pong ✅ |
| Gossip | addr/getaddr | addr/getaddr ✅ |
| Bloques | inv/getblocks/block | inv/getblocks/block ✅ |
| Transacciones | tx | tx ✅ |

---

## Tipos de Mensaje

### Handshake
```python
MSG_VERSION = 'version'  # Presentación inicial al conectar
MSG_VERACK  = 'verack'   # Confirmación del handshake
```

Cuando dos nodos se conectan, el primero envía `version` con su información. El otro responde con `verack`. Sin este handshake no hay comunicación posterior.

```
Nodo A ──── MSG_VERSION ────► Nodo B
Nodo A ◄─── MSG_VERACK  ──── Nodo B
            (conectados)
```

### Keep-alive
```python
MSG_PING = 'ping'  # Verificar que el peer sigue activo
MSG_PONG = 'pong'  # Respuesta al ping
```

Cada 30 segundos (configurable) cada nodo hace ping a sus peers. Si no responden, se marcan como desconectados.

### Gossip de peers
```python
MSG_GETADDR = 'getaddr'  # Pedir lista de peers conocidos
MSG_ADDR    = 'addr'     # Responder con lista de peers
```

El mecanismo de descubrimiento de nodos. Al conectarse, un nodo pide la lista de peers conocidos del otro. Así la red se auto-descubre sin necesitar un directorio central.

### Transacciones
```python
MSG_TX = 'tx'  # Propagar una transacción firmada
```

Cuando un nodo crea o recibe una TX válida, la propaga a todos sus peers con este mensaje.

### Bloques
```python
MSG_INV       = 'inv'       # Anunciar bloque nuevo por hash
MSG_GETBLOCKS = 'getblocks' # Solicitar cadena desde cierta altura
MSG_BLOCK     = 'block'     # Enviar bloque completo
```

El flujo de propagación de bloques usa tres mensajes:
```
Minero ──── MSG_INV (hash) ────► Peer
            "tengo el bloque X"

Peer   ──── MSG_GETBLOCKS ─────► Minero  (si no lo tiene)
            "dame bloques desde altura N"

Minero ──── MSG_BLOCK ─────────► Peer
            (bloque completo)
```

---

## Función `create_message`

```python
def create_message(msg_type: str, payload: dict) -> dict:
```

**¿Qué hace?**

Crea un mensaje P2P con formato estándar. Todos los mensajes de la red pasan por esta función.

**Formato del mensaje:**

```python
{
    'type':      'block',           # Tipo (constante MSG_*)
    'id':        'uuid-unico',      # UUID v4 — para anti-loop
    'timestamp': 1707234567.123,    # Unix timestamp
    'payload':   {...},             # Datos del mensaje
    'checksum':  'sha256hex...',    # SHA256 del payload
}
```

**¿Para qué sirve el `id` UUID?**

Para prevenir que un mensaje circule infinitamente en la red (broadcast storm). Cada nodo guarda los IDs de mensajes que ya vio en `messages_seen`. Si llega un mensaje con un ID ya conocido, se descarta sin procesar ni reenviar.

```
Nodo A mina un bloque
    │
    ▼
broadcast(MSG_BLOCK, id="abc123")
    │
    ├──► Nodo B recibe id="abc123" → nuevo → procesar + reenviar
    │
    └──► Nodo C recibe id="abc123" → nuevo → procesar + reenviar
              │
              └──► Nodo B recibe id="abc123" de nuevo → ya visto → DESCARTAR
```

**¿Para qué sirve el `checksum`?**

Detecta mensajes corruptos durante la transmisión. Se calcula como SHA256 del payload serializado. Al recibir un mensaje, se recalcula el checksum y se compara.

```python
# Al crear:
payload_str = json.dumps(payload, sort_keys=True)
checksum    = hashlib.sha256(payload_str.encode()).hexdigest()

# Al validar:
recalculado = hashlib.sha256(json.dumps(msg['payload'], sort_keys=True).encode()).hexdigest()
válido      = recalculado == msg['checksum']
```

---

## Función `validate_message`

```python
def validate_message(msg: dict) -> bool:
```

**¿Qué hace?**

Valida que un mensaje recibido tenga el formato correcto y el checksum válido. Se llama en `handle_message()` antes de procesar cualquier mensaje.

**Validaciones:**

1. Que tenga todos los campos requeridos: `type`, `id`, `timestamp`, `payload`, `checksum`
2. Que el checksum coincida con el payload recibido

**¿Por qué validar antes de procesar?**

Protege contra mensajes malformados, corruptos o de versiones incompatibles del protocolo. Un mensaje inválido se descarta silenciosamente sin romper el nodo.

---

## Flujo completo de un mensaje

```python
# Nodo A — crear y enviar
block_msg = create_message(MSG_BLOCK, block.to_dict())
await websocket.send(json.dumps(block_msg))

# Nodo B — recibir y validar
raw = await websocket.recv()
msg = json.loads(raw)

if not validate_message(msg):
    return  # Mensaje inválido — descartar

if msg['id'] in messages_seen:
    return  # Ya procesado — descartar (anti-loop)

messages_seen.add(msg['id'])

# Procesar según tipo
if msg['type'] == MSG_BLOCK:
    await handle_block(msg, sender_ws)
```

---

## Tests Asociados: `tests/test_protocol.py`

| Test | Función que prueba | Qué verifica |
|------|-------------------|--------------|
| `test_create_message_structure` | `create_message` | Mensaje tiene todos los campos |
| `test_create_message_types` | `create_message` | Acepta todos los MSG_* |
| `test_message_id_is_unique` | `create_message` | Cada mensaje tiene UUID único |
| `test_message_has_timestamp` | `create_message` | Timestamp es float válido |
| `test_validate_valid_message` | `validate_message` | Mensaje válido retorna True |
| `test_validate_missing_field` | `validate_message` | Campo faltante retorna False |
| `test_validate_wrong_checksum` | `validate_message` | Checksum incorrecto retorna False |
| `test_validate_tampered_payload` | `validate_message` | Payload modificado retorna False |
| `test_all_message_constants` | constantes MSG_* | Todas las constantes existen |

---

*Documento: `DOC_network_protocol.md` — Demo Blockchain*
