# Documentación Técnica: `launcher_manual.py`

---

## Propósito del Archivo

`launcher_manual.py` levanta un demo local completo con **control total del usuario**: N nodos P2P en una sola máquina, todos en modo MANUAL. Ni el minado ni las transacciones ocurren automáticamente — el usuario decide todo desde los dashboards.

**¿Cuándo usar `launcher_manual.py`?**

| Escenario | Launcher |
|-----------|----------|
| Demo interactivo para clase — el alumno controla todo | `launcher_manual.py` |
| Demo autónomo para observar el comportamiento de la red | `launcher_auto.py` |
| Despliegue en red LAN real | `main.py` + `main_seed.py` + `main_global.py` |

---

## Dependencias

```python
import asyncio
import argparse
import threading
from core.blockchain import Blockchain
from network.p2p_node import P2PNode, MINING_MANUAL
from dashboard.app import NodeDashboard
```

---

## Características

- **Sin seed node** — los nodos se conectan directamente via bootstrap (topología de árbol)
- **Sin orquestador** — todas las TXs son manuales desde el formulario del dashboard
- **Modo MANUAL** — el usuario presiona "Minar ahora" o cambia a AUTO desde el dashboard
- **Balance inicial: 0** — el usuario debe minar su primer bloque para obtener 50 coins

---

## Función `build_config`

```python
def build_config(num_nodes: int) -> list:
```

**¿Qué hace?**

Genera la configuración de N nodos con una topología de árbol para el bootstrap inicial.

**Topología generada (ejemplo con 5 nodos):**

```
Nodo 0 (5000) ← raíz — sin bootstrap
    │
    ├── Nodo 1 (5001) ← bootstrap: [5000]
    │
    ├── Nodo 2 (5002) ← bootstrap: [5000]
    │       │
    │       └── Nodo 4 (5004) ← bootstrap: [5002]
    │
    └── Nodo 3 (5003) ← bootstrap: [5001]

Después del gossip (~10s):
    Todos conectados a todos (red mesh completa)
```

**Lógica de asignación de bootstrap:**

```python
if i == 1 or i == 2:
    bootstrap = [('localhost', 5000)]       # Conectan al nodo 0
elif i > 2:
    bootstrap = [('localhost', 5000 + (i % 2))]  # Alternan entre nodo 0 y 1
```

**¿Por qué topología de árbol y no estrella (todos a nodo 0)?**

Con 5 nodos conectando al mismo nodo simultáneamente, el nodo 0 podría rechazar conexiones por exceder `MAX_INBOUND_CONNECTIONS`. El árbol distribuye la carga de forma más natural.

---

## Función `start_node_with_dashboard`

```python
async def start_node_with_dashboard(config: dict):
```

**¿Qué hace?**

Instancia y arranca un nodo P2P en modo MANUAL con su dashboard Flask en thread separado.

**Proceso:**

```
1. Instanciar Blockchain (con bloque génesis)
        │
        ▼
2. Instanciar P2PNode (modo MANUAL forzado)
        │
        ▼
3. asyncio.create_task(node.start())  ← nodo P2P en background
        │
        ▼
4. await asyncio.sleep(0.8)           ← esperar que arranque el WS server
        │
        ▼
5. NodeDashboard(node, port, dashboard_mode='manual')
        │
        ▼
6. threading.Thread(target=dashboard.run, daemon=True).start()
        │
        ▼
7. return node, dashboard
```

**¿Por qué `node.mining_mode = MINING_MANUAL` en lugar de confiar en `config.py`?**

`config.py` tiene `MINING_AUTO_START = True`. El launcher manual necesita sobrescribir esto para garantizar que los nodos no empiecen a minar solos, independientemente de la configuración global.

**¿Por qué `await asyncio.sleep(0.8)`?**

El servidor WebSocket necesita tiempo para inicializarse. Sin el sleep, el dashboard podría intentar acceder a `node.wallet` o `node.blockchain` antes de que estén completamente inicializados.

**¿Por qué `daemon=True` en el thread Flask?**

Los threads daemon se cierran automáticamente cuando el proceso principal termina. Sin `daemon=True`, los servidores Flask seguirían corriendo después de Ctrl+C, dejando el proceso colgado.

---

## Función `main`

```python
async def main(num_nodes: int = 5):
```

**Secuencia de arranque:**

```
1. Imprimir banner
        │
        ▼
2. build_config(num_nodes) → lista de configuraciones
        │
        ▼
3. Para cada config:
   start_node_with_dashboard(config)
   await asyncio.sleep(0.3)  ← inicio escalonado
        │
        ▼
4. await asyncio.sleep(3)  ← esperar que la red se conecte
        │
        ▼
5. Imprimir URLs de dashboards
        │
        ▼
6. await asyncio.Future()  ← correr indefinidamente
        │
        ▼
7. KeyboardInterrupt → imprimir resumen y salir
```

**¿Por qué `await asyncio.sleep(0.3)` entre nodos?**

Inicio escalonado evita que todos los nodos intenten conectarse al nodo 0 simultáneamente antes de que esté listo.

**¿Por qué `await asyncio.sleep(3)` al final?**

Espera a que el gossip protocol descubra y conecte todos los nodos entre sí. En 3 segundos, la topología de árbol se convierte en una red mesh completa.

---

## Resumen Final (al presionar Ctrl+C)

```
  Resumen final:
    node_5000: altura=8, minados=3, balance=150.00 coins
    node_5001: altura=8, minados=2, balance=100.00 coins
    node_5002: altura=8, minados=3, balance=100.00 coins
    node_5003: altura=8, minados=0, balance=0.00 coins
    node_5004: altura=8, minados=0, balance=0.00 coins
```

---

## Uso

```powershell
# 5 nodos (default)
python launcher_manual.py

# 3 nodos
python launcher_manual.py --nodes 3
```

**URLs disponibles:**

```
Nodo 1: http://localhost:8000
Nodo 2: http://localhost:8001
Nodo 3: http://localhost:8002
Nodo 4: http://localhost:8003
Nodo 5: http://localhost:8004
```

---

## Flujo de Demo Paso a Paso

```
1. Ejecutar: python launcher_manual.py
        │
        ▼
2. Abrir http://localhost:8000 en el navegador
   → Balance: 0 coins
        │
        ▼
3. Clic en "Minar ahora"
   → Esperar ~30s (difficulty 4)
   → Balance: 50 coins (recompensa del bloque)
        │
        ▼
4. Abrir http://localhost:8001 en otra pestaña
   → Copiar la address del Nodo 2
        │
        ▼
5. En Nodo 1: pegar address en "Destinatario"
   → Cantidad: 10
   → Clic "Enviar Transacción"
   → TX aparece en Mempool de ambos nodos
        │
        ▼
6. Minar otro bloque en cualquier nodo
   → TX se confirma
   → Balance Nodo 1: 90 coins, Nodo 2: 10 coins
```

---

## Diferencias con `launcher_auto.py`

| Aspecto | `launcher_manual.py` | `launcher_auto.py` |
|---------|---------------------|-------------------|
| Minado | MANUAL (usuario decide) | MANUAL al inicio, luego AUTO desde dashboard |
| TXs | Solo manuales | TxOrchestrator automático |
| Seed | No necesario | Integrado (thread interno) |
| Dashboard mode | `'manual'` (sin controles AUTO) | `'auto'` (con todos los controles) |
| Orquestador | No | Sí (TxOrchestrator) |
| Uso típico | Clase práctica | Demo autónomo |

---

*Documento: `DOC_launcher_manual.md` — Demo Blockchain*
