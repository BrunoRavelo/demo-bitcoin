# Documentación Técnica: `config.py`

---

## Propósito del Archivo

`config.py` es el archivo de configuración central del demo. Define todos los parámetros del sistema en un solo lugar — cambiar un valor aquí afecta a todos los componentes que lo importan. Es el único lugar donde se deben ajustar los parámetros del demo para adaptar el comportamiento de la red.

**Principio de diseño:** Single Source of Truth (fuente única de verdad). Ningún componente hardcodea valores — todos importan de `config.py`.

---

## Dependencias

```python
import os
```

Todos los parámetros soportan sobrescritura mediante **variables de entorno**. Esto permite cambiar el comportamiento sin modificar el código:

```bash
# Windows (PowerShell)
$env:SEED_HOST = "192.168.1.1"
python main.py

# Linux/Mac
SEED_HOST=192.168.1.1 python main.py
```

El patrón `os.environ.get('VAR', default)` lee la variable de entorno si existe, o usa el valor por defecto del código.

---

## Sección: Red

```python
SEED_HOST = os.environ.get('SEED_HOST', 'localhost')
SEED_PORT = int(os.environ.get('SEED_PORT', 8888))

P2P_PORT       = int(os.environ.get('P2P_PORT', 5000))
DASHBOARD_PORT = int(os.environ.get('DASHBOARD_PORT', 8000))
```

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `SEED_HOST` | `'localhost'` | IP del seed node. Cambiar a la IP del instructor en demos LAN |
| `SEED_PORT` | `8888` | Puerto HTTP del seed node |
| `P2P_PORT` | `5000` | Puerto WebSocket del nodo P2P (usado como default en `main.py`) |
| `DASHBOARD_PORT` | `8000` | Puerto Flask del dashboard individual |

**Uso en LAN:**

```bash
# config.py del alumno — apuntar al instructor
SEED_HOST = '192.168.1.1'   # IP del instructor
```

O con variable de entorno:
```powershell
$env:SEED_HOST = "192.168.1.1"
python main.py --host 192.168.1.X
```

---

```python
MAX_OUTBOUND_CONNECTIONS = 8
MAX_INBOUND_CONNECTIONS  = 8
MAX_PEERS_TO_SHARE       = 10
```

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `MAX_OUTBOUND_CONNECTIONS` | 8 | Máximo de conexiones salientes que un nodo intenta mantener |
| `MAX_INBOUND_CONNECTIONS` | 8 | Máximo de conexiones entrantes aceptadas |
| `MAX_PEERS_TO_SHARE` | 10 | Máximo de peers que se comparten en respuesta a `MSG_GETADDR` |

**Diferencia con Bitcoin:** Bitcoin Core tiene un default de 8 conexiones salientes y 125 entrantes. Para un demo de laboratorio con 30 nodos, 8 de cada tipo es más que suficiente.

---

```python
CONNECT_TIMEOUT  = 5    # segundos
GOSSIP_INTERVAL  = 30   # segundos entre ciclos de gossip
PING_INTERVAL    = 30   # segundos entre pings
CLEANUP_INTERVAL = 60   # segundos entre limpiezas
```

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `CONNECT_TIMEOUT` | 5s | Tiempo máximo para establecer conexión WebSocket con un peer |
| `GOSSIP_INTERVAL` | 30s | Frecuencia del ciclo gossip (descubrimiento de peers) |
| `PING_INTERVAL` | 30s | Frecuencia de pings keep-alive a peers conectados |
| `CLEANUP_INTERVAL` | 60s | Frecuencia del cleanup de mensajes viejos y peers inactivos |

---

## Sección: Difficulty (Estilo Bitcoin)

```python
MAX_TARGET = 2**256 - 1

INITIAL_TARGET = MAX_TARGET // 1_500_000

TARGET_BLOCK_TIME = 180  # 3 minutos

DIFFICULTY_ADJUSTMENT_INTERVAL = 5

MAX_ADJUSTMENT_FACTOR = 4
```

Esta sección implementa el sistema de difficulty **numérico** de Bitcoin, más preciso que el sistema de "prefijo de ceros" que se usaba en versiones anteriores.

**¿Cómo funciona el target numérico?**

En Bitcoin, un bloque es válido si `SHA256(SHA256(header)) < target`. El target es un número de 256 bits — cuanto más pequeño, más difícil encontrar un hash válido.

```
MAX_TARGET = 2^256 - 1  →  cualquier hash es válido (difficulty=0)
target = MAX_TARGET // N  →  probabilidad de éxito ≈ 1/N por intento
```

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `MAX_TARGET` | 2²⁵⁶ - 1 | Target máximo — dificultad mínima (todo hash válido) |
| `INITIAL_TARGET` | MAX_TARGET // 1,500,000 | Calibrado para ~180s por bloque a 50,000 h/s |
| `TARGET_BLOCK_TIME` | 180s | Tiempo objetivo entre bloques (3 minutos) |
| `DIFFICULTY_ADJUSTMENT_INTERVAL` | 5 bloques | Frecuencia del ajuste automático de difficulty |
| `MAX_ADJUSTMENT_FACTOR` | 4 | Límite de ajuste por ciclo (igual que Bitcoin: máximo ×4 o ÷4) |

**Calibración del INITIAL_TARGET:**

```
50,000 hashes/segundo × 30 segundos promedio = 1,500,000 hashes esperados
INITIAL_TARGET = MAX_TARGET // 1,500,000
→ probabilidad de éxito ≈ 1/1,500,000 por hash
→ tiempo esperado ≈ 1,500,000 / 50,000 h/s = 30 segundos
```

**¿Por qué 3 minutos (`TARGET_BLOCK_TIME = 180`)?**

Con CPUs de demo (~50,000 h/s), 3 minutos da tiempo suficiente para observar el proceso sin que el demo sea demasiado lento. Bitcoin usa 10 minutos porque su red tiene petahashes/segundo.

**Ajuste automático (como Bitcoin 2016):**

Cada `DIFFICULTY_ADJUSTMENT_INTERVAL` bloques, el sistema compara el tiempo real contra `TARGET_BLOCK_TIME`:

```python
ratio = tiempo_real / tiempo_esperado
ratio = max(1/MAX_FACTOR, min(MAX_FACTOR, ratio))  # limitado a ×4 o ÷4
nuevo_target = target_actual * ratio
```

Si los bloques se minan demasiado rápido → target se reduce (más difícil).
Si los bloques tardan demasiado → target aumenta (más fácil).

---

## Sección: Blockchain

```python
BLOCK_REWARD       = 50
MAX_MEMPOOL_SIZE   = 100
MAX_TXS_PER_BLOCK  = 10
```

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `BLOCK_REWARD` | 50 | Coins que recibe el minero por cada bloque (coinbase TX) |
| `MAX_MEMPOOL_SIZE` | 100 | Máximo de TXs que puede tener el mempool simultáneamente |
| `MAX_TXS_PER_BLOCK` | 10 | Máximo de TXs por bloque (incluye coinbase) |

**Diferencia con Bitcoin:**

Bitcoin comenzó con un `BLOCK_REWARD` de 50 BTC (ahora 3.125 BTC después de 4 halvings). `MAX_TXS_PER_BLOCK` en Bitcoin no es un número fijo — está limitado por el tamaño máximo del bloque (1 MB para legacy, 4 MB con SegWit).

---

## Sección: Minado

```python
MINING_AUTO_START = True
```

| Valor | Comportamiento |
|-------|---------------|
| `True` | Los nodos arrancan en modo AUTO — comienzan a minar inmediatamente |
| `False` | Los nodos arrancan en modo PAUSED — esperan instrucción manual |

**¿Cuándo usar `False`?**

En tests, donde el minado automático interferiría con las pruebas. Los launchers locales (`launcher_manual.py`) fuerzan `MINING_MANUAL` directamente en el nodo, ignorando esta variable.

---

## Sección: Orquestador de TXs Automáticas

```python
TX_AUTO_START         = True
TX_AUTO_BASE_INTERVAL = 15     # segundos
TX_AUTO_JITTER        = 10     # segundos
TX_AUTO_MAX_FRACTION  = 0.2
```

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `TX_AUTO_START` | True | Si el orquestador arranca en modo AUTO automáticamente |
| `TX_AUTO_BASE_INTERVAL` | 15s | Intervalo base entre TXs automáticas |
| `TX_AUTO_JITTER` | 10s | Variación aleatoria del intervalo (15s + random(0, 10s)) |
| `TX_AUTO_MAX_FRACTION` | 0.2 | Fracción máxima del balance que se envía por TX automática |

**¿Por qué el jitter?**

Sin jitter, las TXs llegarían exactamente cada 15 segundos — demasiado regular para simular comportamiento real de usuarios. El jitter hace que el intervalo varíe entre 15s y 25s, más parecido a usuarios reales.

**¿Por qué `TX_AUTO_MAX_FRACTION = 0.2`?**

Limita el monto de cada TX automática al 20% del balance disponible. Esto evita que el orquestador vacíe el balance de un nodo en una sola TX, garantizando que la red siempre tenga actividad económica distribuida.

---

## Importación en otros módulos

```python
# En blockchain.py:
from config import BLOCK_REWARD, DIFFICULTY, MAX_MEMPOOL_SIZE, MAX_TXS_PER_BLOCK

# En p2p_node.py:
from config import GOSSIP_INTERVAL, PING_INTERVAL, CLEANUP_INTERVAL, MAX_OUTBOUND_CONNECTIONS

# En tx_orchestrator.py:
from config import SEED_HOST, SEED_PORT, TX_AUTO_BASE_INTERVAL, TX_AUTO_JITTER, TX_AUTO_MAX_FRACTION

# En seed_node.py, seed_client.py, dashboard/app.py, dashboard_global/app.py:
from config import SEED_HOST, SEED_PORT
```

---

## Parámetros Clave para Ajustar en Demo

### Demo en computadoras lentas (ajustar difficulty):
```python
INITIAL_TARGET = MAX_TARGET // 500_000   # más fácil — ~10s por bloque
TARGET_BLOCK_TIME = 30
```

### Demo para clase con poco tiempo:
```python
INITIAL_TARGET = MAX_TARGET // 100_000   # muy fácil — ~2s por bloque
TX_AUTO_BASE_INTERVAL = 5
TX_AUTO_JITTER = 3
```

### Demo de laboratorio LAN:
```python
SEED_HOST = '192.168.1.1'               # IP del instructor
TARGET_BLOCK_TIME = 180                 # 3 minutos (más realista)
DIFFICULTY_ADJUSTMENT_INTERVAL = 5
```

---

*Documento: `DOC_config.md` — Demo Blockchain*
