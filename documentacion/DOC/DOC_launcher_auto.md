# Documentación Técnica: `launcher_auto.py`

---

## Propósito del Archivo

`launcher_auto.py` levanta un demo local **completamente autónomo**: N nodos P2P, un seed node integrado y un TxOrchestrator que genera transacciones automáticas. Una vez arrancado, la red mina bloques y circula fondos sin intervención del usuario.

**¿Cuándo usar `launcher_auto.py`?**

| Escenario | Launcher |
|-----------|----------|
| Demo autónomo — observar el comportamiento de la red | `launcher_auto.py` |
| Demo interactivo — el alumno controla todo | `launcher_manual.py` |
| Despliegue LAN real | `main.py` + `main_seed.py` + `main_global.py` |

---

## Dependencias

```python
import asyncio
import argparse
import threading
from core.blockchain import Blockchain
from core.tx_orchestrator import TxOrchestrator, ORCH_AUTO, ORCH_MANUAL
from network.p2p_node import P2PNode, MINING_AUTO, MINING_MANUAL
from network.seed_node import SeedNode
from dashboard.app import NodeDashboard
from config import SEED_PORT, TX_AUTO_BASE_INTERVAL, TX_AUTO_JITTER
```

---

## Constantes

```python
LAUNCHER_SEED_PORT = 8888
```

Puerto fijo del seed integrado. Se usa `8888` para que sea consistente con el seed externo de `main_seed.py` y los valores por defecto de `config.py`.

---

## Función `build_config`

Idéntica a la de `launcher_manual.py`. Ver [DOC_launcher_manual.md](DOC_launcher_manual.md) para detalles de la topología de árbol.

---

## Función `start_seed_node`

```python
def start_seed_node():
    seed = SeedNode(host='0.0.0.0', port=LAUNCHER_SEED_PORT)
    t = threading.Thread(target=seed.run, daemon=True)
    t.start()
    return seed
```

**¿Qué hace?**

Arranca el seed node en un thread daemon. El seed es un servidor Flask síncrono — no puede correr en el event loop asyncio, necesita su propio thread.

**¿Por qué `host='0.0.0.0'`?**

Para que el seed esté accesible desde cualquier interfaz, incluyendo si otros dispositivos de la red local quieren conectarse al demo. Con `'localhost'` solo serían accesibles desde la misma máquina.

**¿Por qué `daemon=True`?**

El seed se cierra automáticamente cuando el proceso principal termina (Ctrl+C).

---

## Función `start_node_with_dashboard`

```python
async def start_node_with_dashboard(config: dict, orchestrator=None):
```

Similar a la de `launcher_manual.py`, con estas diferencias clave:

**Dashboard mode `'auto'`:**

```python
dashboard = NodeDashboard(
    node,
    config['dashboard_port'],
    dashboard_mode='auto',     # ← activa controles de minado y TXs
    orchestrator=orchestrator, # ← referencia al orquestador compartido
)
```

El modo `'auto'` activa en el HTML:
- Botones AUTO/MANUAL para minado
- Botones AUTO/MANUAL para TXs automáticas
- Dropdown de addresses conocidas para TX manual

**Minado arranca en MANUAL:**

```python
node.mining_mode = MINING_MANUAL  # arranca pausado
node.dashboard_port = config['dashboard_port']  # para el seed
```

Los nodos arrancan pausados. El usuario activa AUTO desde cada dashboard, o lo hace globalmente desde `main_global.py`. Esto permite que el instructor controle el inicio del demo.

**¿Por qué `node.dashboard_port = config['dashboard_port']`?**

El P2PNode necesita saber su `dashboard_port` para anunciarlo al seed cuando llama a `announce_address()`. El orquestador usa este dato para saber en qué puerto está el dashboard de cada nodo.

---

## Función `main`

```python
async def main(num_nodes: int = 5):
```

**Secuencia de arranque (3 fases):**

```
Fase 1: Seed node
    start_seed_node()
    await asyncio.sleep(1)  ← esperar que Flask arranque

Fase 2: Orquestador
    orchestrator = TxOrchestrator(seed_host='localhost', seed_port=8888)
    (no se arranca aún — esperará 30s después de los nodos)

Fase 3: Nodos (N nodos en secuencia)
    Para cada config:
        start_node_with_dashboard(config, orchestrator=orchestrator)
        await asyncio.sleep(0.5)

Espera inicial:
    await asyncio.sleep(4)  ← que los nodos se registren en seed

Arrancar orquestador con delay:
    asyncio.create_task(_start_orchestrator_delayed(orchestrator))

Correr indefinidamente:
    await asyncio.Future()
```

**¿Por qué crear el orquestador ANTES que los nodos?**

El orquestador se pasa como referencia a cada `NodeDashboard`. Si se creara después, los dashboards no tendrían referencia al orquestador y los botones AUTO/MANUAL de TXs no funcionarían.

**¿Por qué `asyncio.sleep(4)` al final del arranque?**

Da tiempo a que los nodos se registren en el seed y el seed tenga la lista completa de peers. Sin este delay, el orquestador podría consultar el seed y obtener una lista incompleta.

---

## Función `_start_orchestrator_delayed`

```python
async def _start_orchestrator_delayed(orchestrator: TxOrchestrator):
    print("  [ORCH] Esperando 30s para que los nodos tengan balance...")
    await asyncio.sleep(30)
    print("  [ORCH] Iniciando TXs automáticas...")
    orchestrator.set_mode(ORCH_AUTO)
    await orchestrator.start()
```

**¿Por qué 30 segundos de delay?**

Los nodos arrancan con balance 0 (solo el bloque génesis). El orquestador no puede enviar TXs si no hay fondos. Con difficulty calibrada para ~30s por bloque, 30 segundos permite que al menos un nodo mine su primer bloque y tenga 50 coins.

**¿Por qué `set_mode(ORCH_AUTO)` explícitamente?**

Aunque `TX_AUTO_START = True` en `config.py`, el orquestador se instancia sin modo definido. `set_mode(ORCH_AUTO)` activa el modo automático independientemente de la configuración.

---

## Arquitectura de Threads y Tareas

```
Proceso principal
│
├── Event loop asyncio (thread principal)
│   │
│   ├── Task: node_0.start()  ← P2P nodo 0
│   ├── Task: node_1.start()  ← P2P nodo 1
│   ├── ...
│   ├── Task: node_N.start()  ← P2P nodo N
│   │
│   └── Task: _start_orchestrator_delayed()
│               └── TxOrchestrator.start()  ← loop de TXs automáticas
│
├── Thread: SeedNode Flask   ← seed en puerto 8888
│
├── Thread: Dashboard 0 Flask  ← nodo 0 en puerto 8000
├── Thread: Dashboard 1 Flask  ← nodo 1 en puerto 8001
├── ...
└── Thread: Dashboard N Flask  ← nodo N en puerto 800N
```

**Total de threads:** 2 + N (seed + N dashboards)
**Total de tasks asyncio:** N + 1 (N nodos + orquestador)

---

## Uso

```powershell
# 5 nodos (default)
python launcher_auto.py

# 3 nodos
python launcher_auto.py --nodes 3
```

**Output al arrancar:**

```
╔══════════════════════════════════════════════════════════════════════╗
║              BLOCKCHAIN DEMO — Launcher Auto                         ║
╚══════════════════════════════════════════════════════════════════════╝

  Modo:       Nodos arrancan en MANUAL — activa AUTO desde cada dashboard
  Nodos:      5
  Seed port:  8888
  TXs auto:   cada 15s ± 10s

  [1/3] Arrancando seed node...
        Seed activo en http://localhost:8888

  [2/3] Creando orquestador de TXs...

  [3/3] Iniciando 5 nodos en modo AUTO...
        [1/5] Nodo 1 (P2P:5000 Dashboard:8000)...
        [2/5] Nodo 2 (P2P:5001 Dashboard:8001)...
        ...

  Todos los componentes activos. Abre en tu navegador:

    Nodo 1: http://localhost:8000
    ...

  El orquestador enviará TXs automáticas en ~30 segundos
```

---

## Resumen Final (al presionar Ctrl+C)

```
  Resumen final:
    node_5000: altura=25, minados=8, balance=400.00 coins
    node_5001: altura=25, minados=7, balance=218.50 coins
    ...

  Orquestador: TXs enviadas=47, fallidas=2
```

---

## Controles desde el Dashboard

Una vez que los nodos están corriendo en modo MANUAL, el usuario puede:

1. **Activar minado AUTO** en cada nodo individual → botón "AUTO" en sección Minero
2. **Pausar minado** → botón "MANUAL" en sección Minero
3. **Minar manualmente** → botón "Minar ahora"
4. **Activar TXs automáticas** → botón "AUTO" en sección TXs (controla toda la red)
5. **Pausar TXs automáticas** → botón "MANUAL" en sección TXs

---

*Documento: `DOC_launcher_auto.md` — Demo Blockchain*
