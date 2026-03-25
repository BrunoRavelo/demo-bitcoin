# Documentación Técnica: `core/tx_orchestrator.py`

---

## Propósito del Archivo

`tx_orchestrator.py` implementa el **TxOrchestrator** — un bot externo al protocolo P2P que genera transacciones automáticas entre nodos para mantener la red activa durante el demo. Es el equivalente a los usuarios reales que enviarían transacciones en una red Bitcoin de producción.

**Analogía:** El orquestador es como un cajero automático que periódicamente mueve dinero entre cuentas para simular actividad económica real. Los nodos no saben si una transacción viene de un humano o del orquestador — la procesan exactamente igual.

---

## Posición en la arquitectura

```
                    TxOrchestrator
                          │
                          │ GET /addresses (¿quién existe?)
                          ▼
                      Seed Node
                          │
                          │ lista de nodos con dashboard_port
                          ▼
                    TxOrchestrator
                          │
                          │ GET /api/wallet (¿cuánto tiene?)
                          │ POST /api/tx/create (enviar TX)
                          ▼
              Dashboard de cada nodo (HTTP)
                          │
                          │ crea y firma TX internamente
                          ▼
                      P2PNode
                          │
                          │ propaga TX via WebSocket
                          ▼
                    Red P2P completa
```

**El orquestador NO es un nodo Bitcoin** — no conoce el protocolo WebSocket, no tiene blockchain, no mina. Solo hace llamadas HTTP a los dashboards de los nodos.

---

## Diferencias con Bitcoin

| Aspecto | Bitcoin | Este Demo |
|---------|---------|-----------|
| TXs automáticas | Bots externos independientes | TxOrchestrator centralizado |
| Control de TXs | Descentralizado | Instructor puede pausar/reanudar |
| Fees | Sí (incentivo para mineros) | No |
| Selección de remitente | Bots independientes | Aleatorio entre nodos con balance |
| Monto | Definido por el usuario | Fracción aleatoria del balance |
| Destino | Definido por el usuario | Aleatorio entre nodos conocidos |

---

## Dependencias

```python
import asyncio
import random
import time
import requests
from typing import List, Optional
from utils.logger import setup_logger
from network.seed_client import SeedClient
from config import (
    SEED_HOST, SEED_PORT,
    TX_AUTO_BASE_INTERVAL,
    TX_AUTO_JITTER,
    TX_AUTO_MAX_FRACTION,
    TX_AUTO_START,
)
```

| Import | Propósito |
|--------|-----------|
| `asyncio` | Loop async para el ciclo de TXs |
| `random` | Selección aleatoria de nodos y montos |
| `requests` | Llamadas HTTP síncronas a los dashboards |
| `SeedClient` | Obtener lista de nodos del seed |
| `config.*` | Parámetros de intervalos y montos |

---

## Constantes de modo

```python
ORCH_AUTO   = 'auto'    # Genera TXs automáticamente
ORCH_MANUAL = 'manual'  # Inactivo, instructor genera TXs manualmente
```

---

## Clase `TxOrchestrator`

```python
class TxOrchestrator:
```

**Atributos de instancia:**

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `dashboard_port` | `int` | Puerto fallback si el seed no tiene `dashboard_port` |
| `mode` | `str` | Modo actual: `ORCH_AUTO` o `ORCH_MANUAL` |
| `running` | `bool` | True mientras el loop está activo |
| `seed_client` | `SeedClient` | Cliente para consultar el seed |
| `txs_sent` | `int` | Contador de TXs enviadas exitosamente |
| `txs_failed` | `int` | Contador de TXs fallidas |
| `last_tx_at` | `float` | Timestamp de la última TX enviada |

---

## Función `__init__`

```python
def __init__(
    self,
    seed_host:      str = SEED_HOST,
    seed_port:      int = SEED_PORT,
    dashboard_port: int = 8000,
):
```

**¿Qué hace?**

Instancia el orquestador sin arrancarlo. El orquestador no empieza a generar TXs hasta que se llama `start()`.

**¿Por qué `dashboard_port` como parámetro?**

Es el puerto fallback para consultar los dashboards cuando el seed no tiene registrado el `dashboard_port` de un nodo. En la LAN de 30 máquinas donde cada alumno usa el puerto 8000, este valor es suficiente. En demos locales con múltiples nodos en la misma máquina, el seed registra el `dashboard_port` correcto de cada nodo y este fallback no se usa.

**¿Por qué el `SeedClient` del orquestador tiene `host='orchestrator'` y `port=0`?**

El orquestador no es un nodo P2P — no se registra en el seed ni anuncia una wallet address. Solo lee del seed. Con `host='orchestrator'` y `port=0` queda claro en los logs que estas consultas vienen del orquestador, no de un nodo real.

---

## Función `set_mode`

```python
def set_mode(self, mode: str):
```

**¿Qué hace?**

Cambia el modo del orquestador entre `ORCH_AUTO` y `ORCH_MANUAL`. En modo MANUAL el loop sigue corriendo pero `_auto_cycle()` no se ejecuta — el orquestador espera instrucciones manuales.

**¿Quién llama a esta función?**

- Dashboard individual (cuando el instructor presiona AUTO/MANUAL en el dashboard de un nodo)
- Dashboard global (control centralizado de toda la red)

```
Instructor presiona "MANUAL" en dashboard
        │
        ▼
POST /api/tx/manual
        │
        ▼
NodeDashboard.api_tx_manual()
        │
        ▼
self.orchestrator.set_mode(ORCH_MANUAL)
        │
        ▼
Orquestador deja de generar TXs ← afecta a TODA la red
```

---

## Función `start`

```python
async def start(self):
```

**¿Qué hace?**

Inicia el loop automático de generación de TXs. Corre indefinidamente hasta que se llama `stop()`.

**Flujo del loop:**

```
while self.running:
    │
    ▼
¿modo == ORCH_AUTO?
    │
    ├── Sí → _auto_cycle()
    │           │
    │           ▼
    │       Genera una TX
    │
    └── No → saltar
    │
    ▼
Esperar BASE_INTERVAL + random(0, JITTER) segundos
    │
    ▼
Repetir
```

**¿Por qué el jitter?**

Sin jitter, todas las TXs llegarían a intervalos exactamente iguales — poco realista. El jitter agrega variación aleatoria para simular comportamiento humano real:

```python
interval = TX_AUTO_BASE_INTERVAL + random.uniform(0, TX_AUTO_JITTER)
# Con BASE=15s y JITTER=10s → entre 15s y 25s cada TX
```

**¿Por qué `await asyncio.sleep()` y no `time.sleep()`?**

`asyncio.sleep()` cede el control al event loop durante la espera — otros coroutines pueden ejecutarse. `time.sleep()` bloquearía todo el proceso, incluyendo las respuestas HTTP del dashboard. El orquestador corre en el mismo event loop que el seed y los dashboards.

---

## Función `stop`

```python
def stop(self):
    self.running = False
```

Detiene el loop. Se llama al presionar Ctrl+C en el launcher.

---

## Función `_auto_cycle`

```python
async def _auto_cycle(self):
```

**¿Qué hace?**

Ejecuta un ciclo completo de TX automática: seleccionar nodos, verificar balance, calcular monto y enviar.

**Proceso paso a paso:**

```
1. GET seed/addresses → lista de nodos conocidos
        │
        ▼
2. ¿Hay al menos 2 nodos?
   No → salir (no hay a quién enviar)
        │
        ▼
3. Elegir remitente aleatoriamente
        │
        ▼
4. Elegir destinatario aleatoriamente (distinto al remitente)
        │
        ▼
5. GET dashboard_remitente/api/wallet → balance actual
        │
        ▼
6. ¿balance > 0?
   No → salir (no tiene fondos)
        │
        ▼
7. Calcular monto:
   max_amount = balance * TX_AUTO_MAX_FRACTION
   amount = random(0.01, max_amount)
        │
        ▼
8. POST dashboard_remitente/api/tx/create → crear TX
        │
        ▼
9. El nodo crea, firma y propaga la TX normalmente
```

**¿Por qué `TX_AUTO_MAX_FRACTION`?**

Evita que el orquestador vacíe el balance de un nodo en una sola TX. Con `TX_AUTO_MAX_FRACTION = 0.2`, cada TX automática usa máximo el 20% del balance disponible — el nodo siempre conserva fondos para futuras TXs.

---

## Función `send_tx`

```python
async def send_tx(
    self,
    sender_host:    str,
    sender_port:    int,
    to_address:     str,
    amount:         float,
    dashboard_port: int = None,
) -> bool:
```

**¿Qué hace?**

Envía una instrucción de TX al dashboard del nodo remitente via HTTP POST. El nodo recibe la instrucción, crea la TX con su propia wallet, la firma y la propaga.

**¿Por qué el orquestador no crea la TX directamente?**

Porque no tiene la private key del nodo. Solo el nodo conoce su propia private key — el orquestador solo puede decirle "envía X coins a esta address". La firma digital siempre la hace el nodo con su wallet.

```
Orquestador                    Nodo remitente
     │                               │
     │── POST /api/tx/create ────────►│
     │   {to_address, amount}        │
     │                               │── node.create_transaction()
     │                               │── tx.sign(self.wallet)
     │                               │── broadcast_transaction(tx)
     │◄── 200 OK ────────────────────│
     │   {txid, from, to, amount}    │
```

**Manejo de errores:**

| Caso | Comportamiento |
|------|---------------|
| Nodo responde 200 | `txs_sent += 1`, retorna True |
| Nodo responde 4xx/5xx | `txs_failed += 1`, log warning, retorna False |
| Nodo no disponible | `txs_failed += 1`, log warning, retorna False |
| Timeout (5s) | `txs_failed += 1`, log warning, retorna False |

**¿Por qué `run_in_executor` para `requests.get/post`?**

`requests` es una librería síncrona — bloquea el thread hasta recibir respuesta. En un contexto async esto detendría todo el event loop. `run_in_executor` corre el request en un thread separado del pool, permitiendo que asyncio continúe procesando otros eventos mientras espera la respuesta HTTP.

```python
response = await loop.run_in_executor(
    None,                    # usar ThreadPoolExecutor por defecto
    lambda: requests.post(   # llamada síncrona en thread separado
        dashboard_url,
        json={...},
        timeout=5,
    )
)
```

---

## Función `_get_addresses`

```python
async def _get_addresses(self) -> List[dict]:
```

Consulta el seed para obtener la lista de nodos activos. Usa `run_in_executor` por la misma razón que `send_tx` — `requests` es síncrono.

Cada elemento de la lista tiene:
```python
{
    'host':           '192.168.1.X',
    'port':           5000,           # puerto P2P
    'node_id':        'node_5000',
    'wallet_address': '1A2B3C...',
    'dashboard_port': 8000,           # puerto del dashboard
}
```

---

## Función `_get_balance`

```python
async def _get_balance(self, node_info: dict) -> float:
```

Consulta el balance de un nodo via su dashboard. Usa `dashboard_port` del `node_info` si está disponible, o el fallback del constructor.

**¿Por qué consultar el balance antes de enviar la TX?**

Para no intentar enviar TXs a nodos sin fondos. Aunque el dashboard rechazaría la TX (`balance insuficiente`), evitar el intento reduce `txs_failed` y hace los logs más limpios.

---

## Función `get_stats`

```python
def get_stats(self) -> dict:
```

Retorna estadísticas del orquestador para el dashboard global:

```python
{
    'mode':         'auto',     # modo actual
    'running':      True,       # si el loop está activo
    'txs_sent':     42,         # TXs exitosas
    'txs_failed':   3,          # TXs fallidas
    'last_tx_at':   1707234567, # timestamp de última TX
    'success_rate': 0.933,      # 93.3% de éxito
}
```

---

## Uso en los launchers

### `launcher_auto.py` — demo local
```python
# Se crea ANTES de los nodos para pasarlo al dashboard
orchestrator = TxOrchestrator(
    seed_host='localhost',
    seed_port=8888,
)

# Se pasa a cada dashboard para control directo
dashboard = NodeDashboard(
    node, port,
    dashboard_mode='auto',
    orchestrator=orchestrator,   # ← referencia directa
)

# Arranca con delay de 30s
await _start_orchestrator_delayed(orchestrator)
```

### `main_global.py` — LAN con 30 máquinas
```python
# En la máquina del instructor
orchestrator = TxOrchestrator(
    seed_host='192.168.1.1',  # IP del instructor
    seed_port=8888,
)

# Dashboard global tiene la referencia
dashboard = GlobalDashboard(orchestrator=orchestrator)

# Los dashboards individuales de los alumnos NO tienen referencia
# El control es solo desde el dashboard global
```

---

## Flujo completo en demo de 30 máquinas

```
Instructor arranca main_seed.py y main_global.py
        │
        ▼
TxOrchestrator espera 30s (nodos necesitan minar balance)
        │
        ▼
Loop cada 15-25s:
    GET seed:8888/addresses
    → [{node_id: 'node_5000', host: '192.168.1.5', dashboard_port: 8000, ...}, ...]
        │
        ▼
    Elige node_5000 como remitente (tiene balance)
    Elige node_5002 como destinatario
        │
        ▼
    GET 192.168.1.5:8000/api/wallet → {balance: 250.00}
        │
        ▼
    amount = 250 * 0.2 * random() ≈ 32.5 coins
        │
        ▼
    POST 192.168.1.5:8000/api/tx/create
    {to_address: '1XYZ...', amount: 32.5}
        │
        ▼
    node_5000 crea TX, la firma con su private key, la propaga
        │
        ▼
    TX viaja por WebSocket a todos los nodos
        │
        ▼
    Próximo bloque minado confirma la TX
```

---

## Tests Asociados: `tests/test_tx_orchestrator.py`

| Test | Función que prueba | Qué verifica |
|------|-------------------|--------------|
| `test_orchestrator_creation` | `__init__` | Se instancia correctamente |
| `test_set_mode_auto` | `set_mode` | Cambia a ORCH_AUTO |
| `test_set_mode_manual` | `set_mode` | Cambia a ORCH_MANUAL |
| `test_set_mode_invalid` | `set_mode` | Modo inválido lanza ValueError |
| `test_get_stats_initial` | `get_stats` | Stats iniciales son cero |
| `test_send_tx_success` | `send_tx` | TX exitosa incrementa txs_sent |
| `test_send_tx_failure` | `send_tx` | TX fallida incrementa txs_failed |
| `test_send_tx_connection_error` | `send_tx` | Nodo inaccesible manejado limpiamente |
| `test_auto_cycle_no_nodes` | `_auto_cycle` | Sin nodos no genera TX |
| `test_auto_cycle_one_node` | `_auto_cycle` | Un solo nodo no genera TX |
| `test_auto_cycle_no_balance` | `_auto_cycle` | Nodo sin balance no genera TX |
| `test_auto_cycle_generates_tx` | `_auto_cycle` | Con 2 nodos y balance genera TX |
| `test_get_stats_success_rate` | `get_stats` | Tasa de éxito calculada correctamente |
| `test_stop` | `stop` | `running` pasa a False |

---

*Documento: `DOC_core_tx_orchestrator.md` — Demo Blockchain*
