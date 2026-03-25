# Documentación Técnica: `dashboard/`

---

## Propósito

El dashboard es la interfaz visual de cada nodo — un panel web que muestra el estado en tiempo real y permite interactuar con el nodo sin necesidad de usar la línea de comandos. Es el equivalente al cliente visual de un wallet de Bitcoin.

El dashboard corre como un servidor Flask en un thread separado — no bloquea el event loop de asyncio que maneja la red P2P.

---

## Archivos del módulo

```
dashboard/
├── __init__.py
├── app.py                  ← Servidor Flask + endpoints API
├── templates/
│   └── dashboard.html      ← UI HTML con Jinja2
└── static/
    ├── app.js              ← Lógica frontend (auto-refresh, llamadas API)
    └── style.css           ← Estilos visuales
```

---

# `dashboard/app.py`

## Clase `NodeDashboard`

```python
class NodeDashboard:
    def __init__(
        self,
        node,
        dashboard_port:  int,
        dashboard_mode:  str = 'manual',
        orchestrator     = None,
    ):
```

**Modos:**

| `dashboard_mode` | Descripción | Usado en |
|-----------------|-------------|---------|
| `'manual'` | Solo wallet, TX manual, minar | `launcher_manual.py`, LAN individual |
| `'auto'` | Además: toggle minado, TXs automáticas | `launcher_auto.py` |

**`orchestrator`:** Si se pasa una instancia de `TxOrchestrator`, los endpoints `/api/tx/*` la controlan directamente. `None` en modo manual y en nodos LAN individuales.

---

## Endpoints de la API

### Estado y consulta

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Página principal (dashboard.html) |
| `/api/status` | GET | Estado completo del nodo |
| `/api/wallet` | GET | Address y balance |
| `/api/peers` | GET | Peers conectados |
| `/api/mempool` | GET | TXs pendientes |
| `/api/chain` | GET | Últimos 5 bloques |
| `/api/block/<hash>` | GET | Detalle de un bloque |
| `/api/all_nodes` | GET | Nodos via seed |
| `/api/addresses` | GET | Wallet addresses para dropdown TX |

### Control de minado

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/mine/auto` | POST | Activar minado automático |
| `/api/mine/manual` | POST | Cambiar a minado manual |
| `/api/mine/once` | POST | Minar un bloque ahora |

### Control de TXs automáticas

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/tx/auto` | POST | Activar orquestador (requiere orchestrator) |
| `/api/tx/manual` | POST | Pausar orquestador (requiere orchestrator) |
| `/api/tx/status` | GET | Estado del orquestador |

### Envío de transacciones

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/send_tx` | POST | TX manual (form data, redirect) |
| `/api/tx/create` | POST | TX via JSON (para orquestador) |

---

## Detalle de endpoints clave

### `GET /api/status`

```json
{
    "node_id":        "node_5000",
    "address":        "1A2B3C...",
    "balance":        250.00,
    "chain_height":   42,
    "mempool_count":  3,
    "peers_count":    2,
    "mining_mode":    "auto",
    "blocks_mined":   15,
    "mining_rewards": 750.0,
    "dashboard_mode": "auto"
}
```

Es el endpoint más consultado — el JS lo llama cada 2 segundos para actualizar la UI.

### `GET /api/chain`

```json
{
    "height":      42,
    "latest_hash": "0000a3b4...",
    "blocks": [
        {
            "hash":      "0000a3b4...",
            "full_hash": "0000a3b4c5d6e7f8...",
            "height":    41,
            "txs":       2,
            "timestamp": 1707234567.0,
            "nonce":     65432,
            "difficulty": 4,
            "mined_by":  "1A2B3C..."
        }
    ]
}
```

Retorna los últimos 5 bloques en orden descendente. `full_hash` se usa para llamar a `/api/block/<hash>`.

### `POST /api/mine/once`

```python
asyncio.run_coroutine_threadsafe(
    self.node.mine_once(),
    self.node.loop,
)
```

Flask corre en un thread separado. Para llamar a una función async del nodo desde Flask, se usa `run_coroutine_threadsafe()` que agenda el coroutine en el event loop del nodo y retorna inmediatamente sin esperar el resultado.

### `POST /api/tx/create`

Usado por el orquestador. Acepta JSON con `to_address` y `amount`. El nodo crea la TX con su propia wallet, la firma y la propaga. Retorna el TXID.

### `GET /api/tx/status`

```json
{
    "available": true,
    "tx_mode":   "auto",
    "txs_sent":  42,
    "running":   true
}
```

Si `orchestrator` es `None` retorna `{"available": false, "tx_mode": "manual"}` sin error.

---

# `dashboard/templates/dashboard.html`

## Secciones de la UI

```
┌─────────────────────────────────────────────────────┐
│  Header: node_id │ P2P: 5000 │ Dashboard: 8000 │ Altura │ Modo
├─────────────────────────────────────────────────────┤
│  Wallet                                             │
│    Address: 1A2B3C... [Copiar]                      │
│    Balance: 250.00 coins                            │
├─────────────────────────────────────────────────────┤
│  Enviar Transacción                                 │
│    Destinatario: [input] [dropdown conocidos*]      │
│    Cantidad: [input]                                │
│    [Enviar Transacción]                             │
│    ─────────────────────────────────────────────── │
│    TXs automáticas: ⚙ Automático*    [AUTO][MANUAL]*│
├─────────────────────────────────────────────────────┤
│  Minero                                             │
│    Bloques minados: 15                              │
│    Recompensas: 750.00 coins                        │
│    Modo: [AUTO][MANUAL]*                            │
│    [⛏ Minar un bloque ahora]                       │
├─────────────────────────────────────────────────────┤
│  Blockchain                                         │
│    Altura: 42 │ Último: 0000a3b4...                 │
│    [#41][#40][#39][#38][#37]  (clickeables)        │
├─────────────────────────────────────────────────────┤
│  Red P2P                                            │
│    Peers: 2                                         │
│    ● localhost:5001                                 │
│    ● localhost:5002                                 │
├─────────────────────────────────────────────────────┤
│  Mempool                                            │
│    TXs pendientes: 3                                │
│    [txid] from → to: amount coins                  │
└─────────────────────────────────────────────────────┘
* Solo visible en dashboard_mode == 'auto'
```

## Lógica Jinja2

```html
{% if dashboard_mode == 'auto' %}
    <!-- dropdown de addresses conocidas -->
    <!-- toggle TXs automáticas -->
    <!-- toggle minado AUTO/MANUAL -->
{% endif %}

<!-- botón "Minar ahora" — SIEMPRE VISIBLE en ambos modos -->
```

`dashboard_mode` se pasa al template desde Flask y también se inyecta en JavaScript:

```html
<script>
    const DASHBOARD_MODE = '{{ dashboard_mode }}';
</script>
```

---

# `dashboard/static/app.js`

## Loop principal

```javascript
async function updateData() {
    const [status, chain, peers, mempool] = await Promise.all([
        fetch('/api/status').then(r => r.json()),
        fetch('/api/chain').then(r => r.json()),
        fetch('/api/peers').then(r => r.json()),
        fetch('/api/mempool').then(r => r.json()),
    ]);
    // actualizar UI...
}

setInterval(updateData, 2000);  // cada 2 segundos
```

**¿Por qué `Promise.all()`?**

Las 4 llamadas se hacen en paralelo — no hay que esperar que termine una para empezar la siguiente. El tiempo total es el de la llamada más lenta, no la suma de todas.

## Funciones principales

| Función | Descripción |
|---------|-------------|
| `updateWallet(status)` | Actualiza address y balance |
| `updateHeader(status, chain)` | Actualiza altura en el header |
| `updateMining(status)` | Actualiza modo, stats y botones (solo auto) |
| `updateChain(chain)` | Renderiza lista de bloques |
| `updatePeers(peers)` | Actualiza lista de peers |
| `updateMempool(mempool)` | Renderiza TXs pendientes |
| `updateAddressDropdown()` | Carga dropdown de addresses conocidas |
| `updateTxStatus()` | Actualiza estado del orquestador |

## Interacciones del usuario

| Función | Qué hace |
|---------|---------|
| `setMiningMode(mode)` | POST /api/mine/auto o /api/mine/manual |
| `mineOnce()` | POST /api/mine/once, deshabilita botón mientras mina |
| `setTxMode(mode)` | POST /api/tx/auto o /api/tx/manual |
| `copyAddress()` | Copia address al clipboard |
| `fillAddress(value)` | Rellena campo destinatario desde dropdown |
| `showBlockDetail(hash)` | GET /api/block/:hash, muestra alert con detalles |

## `showBlockDetail`

```javascript
async function showBlockDetail(fullHash) {
    const block = await fetch(`/api/block/${fullHash}`).then(r => r.json());
    const info = `Hash: ${block.hash}\nNonce: ${block.nonce}\n\n` +
        block.txs.map(tx =>
            `${tx.type === 'coinbase' ? '[COINBASE]' : '[TX]'} ${tx.from} → ${tx.to}: ${tx.amount}`
        ).join('\n');
    alert(info);
}
```

Al hacer clic en un bloque de la lista, muestra un `alert()` con el detalle completo incluyendo todas las transacciones. En el Sprint 9.1 esto se mejorará con un panel visual propio.

---

## Arquitectura Flask + asyncio

Flask y asyncio corren en threads separados. La comunicación entre ellos usa `run_coroutine_threadsafe`:

```
Thread Flask (HTTP requests)              Thread asyncio (P2P + minado)
        │                                           │
        │── POST /api/mine/once ──────────────────► │
        │   asyncio.run_coroutine_threadsafe(       │
        │       node.mine_once(),                   │
        │       node.loop,                          │
        │   )                                       │
        │◄── 200 OK (inmediato)                     │
        │                              (background) │
        │                         node.mine_once()  │
        │                                      done │
```

Flask retorna 200 inmediatamente — el minado ocurre en background sin bloquear al cliente HTTP.

---

*Documento: `DOC_dashboard.md` — Demo Blockchain*
