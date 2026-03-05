# Documentación Técnica: `network/protocol.py`

---

## Propósito del Archivo

`protocol.py` define el formato estándar de los mensajes P2P y proporciona funciones para crear y validar mensajes. Asegura que todos los nodos hablen el mismo "idioma" y detecta mensajes corruptos o malformados.

**Analogía:** El protocolo es como el formato de una carta postal:
- **Remitente** (id + timestamp) → quién y cuándo
- **Tipo** (msg_type) → qué clase de mensaje
- **Contenido** (payload) → los datos reales
- **Sello de seguridad** (checksum) → verifica integridad

---

## Diseño del Protocolo

Este archivo implementa un **protocolo de mensajes genérico** que soporta cualquier tipo de mensaje sin necesidad de modificar el código base.

**¿Por qué un protocolo genérico?**

Bitcoin tiene ~25 tipos de mensajes diferentes. En lugar de crear una función específica para cada uno, usamos un formato común que se adapta a todos:

```python
# Enfoque NO escalable:
def create_version_message(...)
def create_verack_message(...)
def create_ping_message(...)
# ... 25 funciones diferentes

# Enfoque escalable (este archivo):
def create_message(msg_type, payload)
# Una función sirve para todos los tipos
```

---

## Dependencias

```python
import json
import hashlib
import uuid
from datetime import datetime
```

| Import | Propósito |
|--------|-----------|
| `json` | Serialización del payload |
| `hashlib` | SHA256 para checksum |
| `uuid` | IDs únicos para cada mensaje |
| `datetime` | Timestamp de creación |

---

## Formato de Mensaje

Todos los mensajes P2P siguen esta estructura:

```json
{
    "type": "tx",
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": 1707234567.123,
    "payload": {
        "from": "1AliceAddress...",
        "to": "1BobAddress...",
        "amount": 10
    },
    "checksum": "a3f2c1d8e9b4..."
}
```

**Campos:**

| Campo | Tipo | Descripción | Propósito |
|-------|------|-------------|-----------|
| `type` | `str` | Tipo de mensaje (`tx`, `ping`, `addr`, etc.) | Router del mensaje |
| `id` | `str` | UUID único | Anti-loop, tracking |
| `timestamp` | `float` | Unix timestamp | Debugging, ordenamiento |
| `payload` | `dict` | Datos del mensaje | Contenido variable |
| `checksum` | `str` | SHA256(payload) en hex | Integridad |

---

## Función `create_message`

```python
def create_message(msg_type: str, payload: dict) -> dict:
    payload_str = json.dumps(payload, sort_keys=True)
    checksum = hashlib.sha256(payload_str.encode()).hexdigest()
    
    return {
        'type': msg_type,
        'id': str(uuid.uuid4()),
        'timestamp': datetime.now().timestamp(),
        'payload': payload,
        'checksum': checksum
    }
```

**¿Qué hace?**

Crea un mensaje P2P con todos los campos requeridos, calculando automáticamente el checksum del payload.

**Proceso paso a paso:**

```
1. Serializar payload a JSON
   └─ sort_keys=True garantiza orden determinístico

2. Calcular checksum
   └─ SHA256(payload_json) → 64 caracteres hex

3. Generar ID único
   └─ UUID4 aleatorio

4. Capturar timestamp actual
   └─ datetime.now().timestamp()

5. Ensamblar diccionario completo
   └─ Retornar mensaje listo para enviar
```

**¿Por qué `sort_keys=True`?**

Los diccionarios en Python no garantizan orden. Sin `sort_keys=True`, el mismo payload podría producir checksums diferentes:

```python
# Sin sort_keys:
payload1 = {"a": 1, "b": 2}
payload2 = {"b": 2, "a": 1}

json.dumps(payload1)  # → '{"a": 1, "b": 2}'
json.dumps(payload2)  # → '{"b": 2, "a": 1}'
# Checksums DIFERENTES para el mismo contenido

# Con sort_keys=True:
json.dumps(payload1, sort_keys=True)  # → '{"a": 1, "b": 2}'
json.dumps(payload2, sort_keys=True)  # → '{"a": 1, "b": 2}'
# Checksums IDÉNTICOS
```

**¿Por qué UUID4?**

Garantiza IDs únicos sin coordinación entre nodos:
- No requiere contador global
- No hay colisiones (probabilidad: 1 en 10^38)
- Cada nodo puede generar IDs independientemente

**Ejemplo de uso:**

```python
# Crear mensaje de transacción
tx_msg = create_message('tx', {
    'from': '1AliceAddr...',
    'to': '1BobAddr...',
    'amount': 10
})

# Resultado:
# {
#     'type': 'tx',
#     'id': '550e8400-...',
#     'timestamp': 1707234567.123,
#     'payload': {'from': '1AliceAddr...', 'to': '1BobAddr...', 'amount': 10},
#     'checksum': 'a3f2c1d8e9b4a7c6d5e4f3c2b1a0987654321...'
# }

# Enviar por WebSocket
await websocket.send(json.dumps(tx_msg))
```

---

## Función `validate_message`

```python
def validate_message(msg: dict) -> bool:
    # Verificar campos requeridos
    required = ['type', 'id', 'timestamp', 'payload', 'checksum']
    if not all(field in msg for field in required):
        return False
    
    # Verificar checksum
    payload_str = json.dumps(msg['payload'], sort_keys=True)
    calculated_checksum = hashlib.sha256(payload_str.encode()).hexdigest()
    
    return calculated_checksum == msg['checksum']
```

**¿Qué hace?**

Valida que un mensaje recibido tenga todos los campos requeridos y que el checksum sea correcto.

**Proceso paso a paso:**

```
1. Verificar estructura
   └─ ¿Tiene los 5 campos obligatorios?
   └─ Si falta alguno → return False

2. Recalcular checksum
   └─ Serializar payload (sort_keys=True)
   └─ SHA256(payload_json)

3. Comparar checksums
   └─ checksum_recibido == checksum_calculado?
   └─ Si coinciden → return True
   └─ Si difieren → return False
```

**Casos que devuelven `False`:**

| Caso | Por qué falla |
|------|---------------|
| Falta campo `type` | Estructura incompleta |
| Falta campo `id` | Estructura incompleta |
| Falta campo `payload` | Estructura incompleta |
| Falta campo `checksum` | Estructura incompleta |
| Checksum no coincide | Payload corrupto o modificado |

**¿Por qué validar checksum?**

Detecta dos tipos de problemas:

**1. Corrupción en tránsito:**
```
Mensaje original: {"amount": 10}
Transmisión: bits se corrompen
Mensaje recibido: {"amount": 18}  ← Error de red
Checksum: NO coincide → rechazado
```

**2. Modificación maliciosa:**
```
Atacante intercepta: {"amount": 10}
Atacante modifica: {"amount": 99999}
Atacante NO puede recalcular checksum (no tiene la clave)
Nodo receptor: checksum NO coincide → rechazado
```

**Ejemplo de uso:**

```python
# Recibir mensaje
raw_message = await websocket.recv()
msg = json.loads(raw_message)

# Validar antes de procesar
if validate_message(msg):
    # Mensaje válido, procesar
    await handle_message(msg)
else:
    # Mensaje corrupto, ignorar
    logger.warning("Mensaje inválido recibido")
```

---

## Tipos de Mensajes Soportados

Aunque el protocolo es genérico, estos son los tipos de mensajes actualmente en uso:

| Tipo | Payload | Propósito |
|------|---------|-----------|
| `version` | `{node_id, host, port}` | Handshake inicial |
| `verack` | `{node_id}` | Confirmación de handshake |
| `ping` | `{nonce}` | Keep-alive |
| `pong` | `{nonce}` | Respuesta a ping |
| `getaddr` | `{}` | Solicitar lista de peers |
| `addr` | `{peers: [...]}` | Responder con peers |
| `tx` | `{from, to, amount, ...}` | Transacción de blockchain |
| `hello` | `{data}` | Mensaje de prueba (Fase 1) |

**Agregar nuevos tipos:**

No requiere modificar `protocol.py`:

```python
# En cualquier otro archivo:
inv_msg = create_message('inv', {
    'type': 'block',
    'hash': 'abc123...'
})

# El protocolo lo maneja automáticamente
```

---

## Seguridad: Checksum vs Firma Digital

**Este archivo usa checksum SHA256, NO firma digital.**

### ¿Cuándo usar checksum (este archivo)?

**Para mensajes P2P no críticos:**
- `ping/pong` → Solo verifica que no se corrompió
- `getaddr/addr` → Lista de peers públicos
- `hello` → Mensajes de prueba

**Protege contra:**
- ✅ Corrupción accidental en red
- ✅ Errores de transmisión
- ❌ NO protege contra modificación intencional

### ¿Cuándo usar firma digital (Transaction)?

**Para datos críticos:**
- `tx` → Transacciones de dinero
- Contenido dentro del payload requiere firma

**Protege contra:**
- ✅ Corrupción accidental
- ✅ Modificación maliciosa
- ✅ Falsificación de identidad

### Arquitectura de doble capa:

```
Mensaje P2P (protocol.py)
├─ Checksum: valida integridad del mensaje
└─ Payload:
    └─ Transaction (transaction.py)
        └─ Firma Ed25519: valida autenticidad del contenido
```

**Ejemplo:**

```python
# Capa 1: Protocolo (checksum)
tx_message = create_message('tx', tx.to_dict())
# Checksum valida que el mensaje no se corrompa

# Capa 2: Transacción (firma)
tx.sign(wallet)
# Firma valida que solo el dueño autorizó la TX
```

---

## Comparación con Bitcoin

| Aspecto | Bitcoin P2P | Este Demo |
|---------|-------------|-----------|
| Formato base | Binario (80 bytes header) | JSON (texto) |
| Checksum | Primeros 4 bytes de double SHA256 | SHA256 completo (64 chars hex) |
| ID de mensaje | No existe | UUID4 |
| Timestamp | No en todos los mensajes | En todos |
| Serialización | Formato binario custom | JSON estándar |
| Tipos de mensaje | ~25 tipos | 8 tipos (extensible) |
| Validación | Checksum + magic bytes + longitud | Checksum + estructura |

**¿Por qué Bitcoin usa binario?**

- Eficiencia: mensajes más pequeños (menos bandwidth)
- Velocidad: parsing más rápido que JSON
- Creado en 2009: JSON menos maduro

**¿Por qué este demo usa JSON?**

- Legibilidad: puedes leer los mensajes
- Debugging: fácil de inspeccionar
- Simplicidad: no requiere parser custom
- Suficiente para demo educativo

---

## Anti-Patrones Prevenidos

### ❌ **Anti-patrón 1: Crear mensajes manualmente**

```python
# MAL - propenso a errores
msg = {
    'type': 'tx',
    'payload': {...}
    # Olvidé id, timestamp, checksum
}
```

```python
# BIEN - usa la función
msg = create_message('tx', {...})
# Todos los campos garantizados
```

### ❌ **Anti-patrón 2: No validar antes de procesar**

```python
# MAL - procesa mensaje sin validar
msg = json.loads(raw_message)
process_message(msg)  # Puede fallar si corrupto
```

```python
# BIEN - valida primero
msg = json.loads(raw_message)
if validate_message(msg):
    process_message(msg)
```

### ❌ **Anti-patrón 3: Calcular checksum sin sort_keys**

```python
# MAL - orden no determinístico
checksum = hashlib.sha256(json.dumps(payload).encode()).hexdigest()
# Mismo payload puede dar checksums diferentes
```

```python
# BIEN - orden determinístico
checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
# Siempre produce mismo checksum
```

---

## Flujo Completo de Mensaje

```
NODO A                                    NODO B
  │                                          │
  │  1. Crear TX                             │
  │  tx = Transaction(...)                   │
  │  tx.sign(wallet)                         │
  │                                          │
  │  2. Crear mensaje P2P                    │
  │  msg = create_message('tx', tx.to_dict())│
  │  └─ Agrega: id, timestamp, checksum     │
  │                                          │
  │  3. Serializar y enviar                  │
  │  await websocket.send(json.dumps(msg))   │
  ├─────────────────────────────────────────►│
  │                                          │
  │                              4. Recibir y parsear
  │                              raw = await websocket.recv()
  │                              msg = json.loads(raw)
  │                                          │
  │                              5. Validar mensaje
  │                              if validate_message(msg):
  │                                ├─ Checksum ✅
  │                                └─ Estructura ✅
  │                                          │
  │                              6. Validar TX (payload)
  │                              tx = Transaction.from_dict(msg['payload'])
  │                              if tx.is_valid():
  │                                └─ Firma Ed25519 ✅
  │                                          │
  │                              7. Procesar TX
  │                              mempool.append(tx)
  │                              await broadcast_transaction(tx)
```

---

## Extensibilidad

Agregar un nuevo tipo de mensaje es trivial:

**Paso 1: Definir en documentación (opcional)**
```python
# Nuevo tipo: 'block'
# Payload: {hash, prev_hash, transactions, nonce}
```

**Paso 2: Crear mensaje**
```python
block_msg = create_message('block', {
    'hash': '...',
    'prev_hash': '...',
    'transactions': [...],
    'nonce': 12345
})
```

**Paso 3: Agregar handler en p2p_node.py**
```python
elif msg_type == 'block':
    await self.handle_block(msg['payload'])
```

**No se necesita modificar protocol.py.**

---

## Tests Implícitos

Aunque `protocol.py` no tiene archivo de tests dedicado, se prueba indirectamente en:

| Test | Función probada | Cómo |
|------|----------------|------|
| `test_network.py` | `create_message()` | Crea mensajes version/verack/ping |
| `test_network.py` | `validate_message()` | Valida mensajes recibidos |
| `demo_tx_cli.py` | Ambas funciones | Crea y valida TXs en red real |
| `launcher_dashboard.py` | Ambas funciones | Dashboard usa mensajes P2P |

**Validación en producción:**

Cada mensaje enviado/recibido en la red pasa por estas funciones, probándolas constantemente.

---

*Documento: `DOC_network_protocol.md` — Demo Blockchain Fases 1 y 1.5*
