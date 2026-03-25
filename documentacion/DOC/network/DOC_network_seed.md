# Documentación Técnica: `network/seed_node.py` y `network/seed_client.py`

---

## Propósito

El seed node y el seed client trabajan juntos para resolver el **problema del bootstrap**: ¿cómo se entera un nodo nuevo de que otros nodos existen?

En Bitcoin este problema se resuelve con DNS seeds — dominios especiales que retornan IPs de nodos conocidos. En este demo usamos un servidor HTTP centralizado que cumple la misma función de forma más simple.

**Analogía:** El seed node es como la recepcionista de un edificio de oficinas. Cuando llegas nuevo, ella te dice qué otras personas trabajan ahí y en qué oficina están. También guarda tu nombre y oficina para decírselo a los que lleguen después.

---

## Separación de responsabilidades

El seed tiene dos registros completamente independientes:

```
Seed Node
    │
    ├── Registro P2P (/register + /peers)
    │       Propósito: descubrimiento de nodos
    │       Datos: host, port, node_id, last_seen
    │       Quién lo usa: P2PNode al arrancar
    │
    └── Registro de Addresses (/announce_address + /addresses)
            Propósito: orquestador de TXs automáticas
            Datos: wallet_address, dashboard_port
            Quién lo usa: TxOrchestrator
```

Si el orquestador se elimina en el futuro, solo se quitan los endpoints `/announce_address` y `/addresses` — el resto funciona igual.

---

# `network/seed_node.py`

## Clase `SeedNode`

```python
class SeedNode:
    PEER_TIMEOUT = 300  # 5 minutos sin ping = inactivo
```

**Atributos:**

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `peers` | `dict` | Registro P2P: `{addr: {host, port, node_id, last_seen}}` |
| `addresses` | `dict` | Registro de wallets: `{addr: {wallet_address, dashboard_port}}` |
| `lock` | `threading.Lock` | Protege ambos registros de acceso concurrente |

**¿Por qué `threading.Lock`?**

Flask puede recibir múltiples requests simultáneos en threads separados. Sin el lock, dos nodos registrándose al mismo tiempo podrían corromper el diccionario `peers`. El lock garantiza acceso exclusivo al modificar los registros.

---

## Endpoints del Seed Node

### `GET /health`

```json
{
    "status": "ok",
    "peers_count": 5,
    "addresses_count": 5,
    "timestamp": 1707234567.123
}
```

Verificar que el seed está activo. Útil para el setup del laboratorio — verificar que el instructor arrancó el seed antes de que los alumnos corran sus nodos.

---

### `POST /register`

**Body:**
```json
{
    "host":    "192.168.1.5",
    "port":    5000,
    "node_id": "node_5000"
}
```

**Respuesta:** `{"status": "ok", "addr": "192.168.1.5:5000"}`

Registra la presencia de un nodo. Doble función:
- Primera llamada → registro nuevo (log INFO)
- Llamadas posteriores → keep-alive (actualiza `last_seen`, log DEBUG)

El `seed_register_loop` en `P2PNode` llama a este endpoint cada `CLEANUP_INTERVAL` segundos para mantener el registro activo.

---

### `GET /peers`

**Query params:**
- `exclude_host`: IP a excluir (el propio nodo)
- `exclude_port`: Puerto a excluir (el propio nodo)

**Respuesta:**
```json
{
    "peers": [
        {"host": "192.168.1.6", "port": 5000, "node_id": "node_6"},
        {"host": "192.168.1.7", "port": 5000, "node_id": "node_7"}
    ],
    "count": 2
}
```

Solo retorna peers activos (vistos en los últimos 300 segundos). El propio nodo siempre se excluye para no conectarse a sí mismo.

---

### `GET /peers/all`

Igual que `/peers` pero incluye nodos inactivos con el campo `"active": false`. Útil para debugging — ver qué nodos existieron aunque ya no estén conectados.

---

### `POST /announce_address`

**Body:**
```json
{
    "host":           "192.168.1.5",
    "port":           5000,
    "node_id":        "node_5000",
    "wallet_address": "1A2B3C...",
    "dashboard_port": 8000
}
```

Completamente independiente de `/register`. El nodo anuncia su wallet address para que el orquestador sepa a quién enviar TXs y en qué puerto está su dashboard.

**¿Por qué `dashboard_port` aquí y no en `/register`?**

Separación de responsabilidades. El P2P no necesita saber el dashboard_port — ese es un detalle de administración. Solo el orquestador lo necesita para hacer llamadas HTTP.

---

### `GET /addresses`

**Respuesta:**
```json
{
    "addresses": [
        {
            "host":           "192.168.1.5",
            "port":           5000,
            "node_id":        "node_5000",
            "wallet_address": "1A2B3C...",
            "dashboard_port": 8000
        }
    ],
    "count": 1
}
```

El orquestador consulta este endpoint para saber a quién enviar TXs automáticas.

---

## Limpieza automática

```python
def _cleanup_inactive(self):
```

Corre en un thread daemon cada `CLEANUP_INTERVAL` segundos. Elimina del registro P2P los nodos que no han hecho ping en más de 300 segundos.

**¿Por qué las wallet addresses NO se limpian?**

Porque el orquestador necesita saber las addresses incluso si un nodo se reinicia temporalmente. Si un nodo se cae y vuelve, su wallet address sigue siendo la misma (misma private key en la sesión actual). Limpiarla causaría que el orquestador no pueda enviarle TXs hasta que el nodo vuelva a anunciar su address.

---

# `network/seed_client.py`

## Clase `SeedClient`

Cliente HTTP que encapsula todas las llamadas al seed node. Centraliza el manejo de errores de red — si el seed no está disponible, retorna valores seguros (`False`, `[]`) sin propagar excepciones.

**Quién lo usa:**

| Clase | Para qué |
|-------|---------|
| `P2PNode` | `register()`, `get_peers()`, `announce_address()` |
| `TxOrchestrator` | `get_addresses()` |
| `GlobalDashboard` | `get_addresses()` |

---

## Métodos P2P

### `register() → bool`

Registra el nodo en el seed. Llamado al arrancar y periódicamente.

**Manejo de errores:**

| Error | Comportamiento |
|-------|---------------|
| `ConnectionError` | Log warning, retorna False (seed no disponible) |
| `Timeout` (5s) | Log warning, retorna False |
| HTTP 4xx/5xx | Log warning, retorna False |
| Éxito (200) | Log info, retorna True |

Retornar `False` en lugar de lanzar excepción permite que el nodo continúe funcionando sin seed — solo usará los bootstrap peers configurados.

### `get_peers() → List[dict]`

Obtiene peers activos del seed excluyendo el propio nodo. Retorna lista vacía si el seed no está disponible.

### `is_seed_available() → bool`

Ping rápido al seed. Usado para verificar disponibilidad sin efectos secundarios.

---

## Métodos del Orquestador

### `announce_address(wallet_address, dashboard_port) → bool`

Anuncia la wallet address al seed. Se llama una vez al arrancar, después de registrarse.

**¿Por qué es una llamada separada de `register()`?**

Para mantener el principio de separación de responsabilidades. Un nodo podría registrarse para P2P sin participar en TXs automáticas. Si el orquestador se elimina, solo se quita esta llamada sin tocar el registro P2P.

### `get_addresses(exclude_host, exclude_port) → List[dict]`

Obtiene todas las wallet addresses registradas. El orquestador la llama en cada ciclo para tener la lista actualizada de nodos disponibles.

---

## Flujo completo de arranque de un nodo

```
P2PNode.start()
    │
    ▼
_bootstrap_from_seed()
    │
    ├── seed_client.register()
    │       POST /register → seed guarda host:port
    │       Retorna True/False
    │
    ├── (si register exitoso)
    │   seed_client.announce_address(wallet, dashboard_port)
    │       POST /announce_address → seed guarda wallet_address
    │
    └── seed_client.get_peers()
            GET /peers → lista de otros nodos
            Para cada peer → agregar a peers_known
            → connect_to_bootstrap() intentará conectarse
```

---

## Diferencias con Bitcoin

| Aspecto | Bitcoin | Este Demo |
|---------|---------|-----------|
| Mecanismo | DNS seeds (dominios reales) | HTTP server centralizado |
| Protocolo | DNS queries | HTTP GET/POST |
| Persistencia | IPs hardcodeadas en el código | Dinámico vía HTTP |
| Wallet addresses | No existe (UTXO) | Registro separado para orquestador |
| Descubrimiento | DNS → IPs → conectar P2P | HTTP → IPs → conectar WebSocket |

---

## Tests Asociados: `tests/test_seed_node.py`

| Test | Qué verifica |
|------|--------------|
| `test_seed_node_health` | `/health` retorna 200 |
| `test_register_node` | `/register` agrega al registro |
| `test_register_keepalive` | Doble registro actualiza `last_seen` |
| `test_get_peers` | `/peers` retorna nodos activos |
| `test_get_peers_excludes_self` | El nodo no aparece en su propia lista |
| `test_peer_timeout` | Nodos inactivos no aparecen en `/peers` |
| `test_announce_address` | `/announce_address` registra wallet |
| `test_get_addresses` | `/addresses` retorna wallets registradas |
| `test_get_addresses_excludes` | Excluye nodo especificado |
| `test_seed_client_register` | `SeedClient.register()` funciona |
| `test_seed_client_get_peers` | `SeedClient.get_peers()` funciona |
| `test_seed_client_unavailable` | Sin seed retorna False/[] limpiamente |
| `test_seed_client_announce` | `announce_address()` con dashboard_port |
| `test_seed_client_get_addresses` | `get_addresses()` retorna lista |

---

*Documento: `DOC_network_seed.md` — Demo Blockchain*
