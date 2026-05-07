# Documentación Técnica: `main.py`

---

## Propósito del Archivo

`main.py` es el **punto de entrada para modo LAN** — un nodo P2P por máquina. En un laboratorio de 30 alumnos, cada alumno ejecuta este script en su computadora para unirse a la red del instructor.

**¿Cuándo usar `main.py`?**

| Escenario | Script a usar |
|-----------|--------------|
| Demo local (1 máquina, múltiples nodos) | `launcher_manual.py` o `launcher_auto.py` |
| **LAN: cada alumno en su propia máquina** | **`main.py`** |
| Solo el dashboard global | `main_global.py` |
| Solo el seed node | `main_seed.py` |

---

## Dependencias

```python
import asyncio
import argparse
from core.blockchain import Blockchain
from network.p2p_node import P2PNode
from config import P2P_PORT, DASHBOARD_PORT, SEED_HOST, SEED_PORT
```

| Import | Propósito |
|--------|-----------|
| `asyncio` | Event loop para el nodo P2P asíncrono |
| `argparse` | Parsing de argumentos de línea de comandos |
| `Blockchain` | Fuente de verdad — se instancia antes que el nodo |
| `P2PNode` | Nodo completo: red P2P + wallet + minado |
| `config.*` | Valores por defecto para los argumentos |

---

## Argumentos de Línea de Comandos

```bash
python main.py [--port PORT] [--host HOST] [--bootstrap PEERS]
               [--dashboard PORT] [--no-dashboard] [--seed-host IP]
```

| Argumento | Default | Descripción |
|-----------|---------|-------------|
| `--port` | 5000 | Puerto WebSocket P2P |
| `--host` | `localhost` | IP donde escuchar (usar la IP de red en LAN) |
| `--bootstrap` | `''` | Peers iniciales: `host:port,host:port` |
| `--dashboard` | 8000 | Puerto Flask del dashboard web |
| `--no-dashboard` | False | Arrancar sin dashboard (solo P2P, útil en servidores) |
| `--seed-host` | `localhost` | IP del seed node (IP del instructor en LAN) |

---

## Función `main`

### Paso 1: Parsear argumentos

```python
parser = argparse.ArgumentParser(description='Nodo P2P Blockchain Demo')
# ... definir argumentos
args = parser.parse_args()
```

### Paso 2: Parsear bootstrap peers

```python
bootstrap_peers = []
if args.bootstrap:
    for peer in args.bootstrap.split(','):
        peer = peer.strip()
        if ':' in peer:
            h, p = peer.split(':')
            bootstrap_peers.append((h, int(p)))
```

Los bootstrap peers son la lista de nodos a los que conectar al arrancar, antes de que el seed entregue la lista completa. Formato: `192.168.1.1:5000,192.168.1.2:5000`.

**¿Por qué `strip()`?**

Permite espacios en la lista: `--bootstrap "192.168.1.1:5000, 192.168.1.2:5000"` funciona correctamente.

### Paso 3: Instanciar Blockchain y P2PNode

```python
blockchain = Blockchain()

node = P2PNode(
    host=args.host,
    port=args.port,
    bootstrap_peers=bootstrap_peers,
    blockchain=blockchain,
    seed_host=args.seed_host,
)
```

**¿Por qué instanciar `Blockchain` separado del `P2PNode`?**

Separación de responsabilidades. La blockchain puede existir sin red. Los tests instancian `Blockchain` directamente sin crear un `P2PNode`. En `main.py` se crea primero para que el nodo lo reciba ya inicializado (con bloque génesis).

### Paso 4: Arrancar dashboard (opcional)

```python
if not args.no_dashboard:
    import threading
    from dashboard.app import NodeDashboard
    dashboard = NodeDashboard(node, args.dashboard)
    dashboard_thread = threading.Thread(
        target=dashboard.run, daemon=True
    )
    dashboard_thread.start()
```

Flask corre en un thread daemon separado. `daemon=True` asegura que el thread se cierra cuando el proceso principal termina (Ctrl+C).

**¿Por qué el import dentro del `if`?**

Si `--no-dashboard` está activo, Flask ni siquiera se importa — reduce el tiempo de arranque y las dependencias necesarias para servidores sin interfaz gráfica.

### Paso 5: Arrancar nodo

```python
try:
    await node.start()
except KeyboardInterrupt:
    print(f"\nNodo {node.id} detenido.\n")
```

`node.start()` es una coroutine que corre indefinidamente. El Ctrl+C interrumpe el event loop limpiamente.

---

## Uso Típico en LAN

### Instructor (máquina con IP fija, ej. 192.168.1.1):

```powershell
# Terminal 1: seed node
python main_seed.py

# Terminal 2: dashboard global + orquestador
python main_global.py --seed-host 192.168.1.1
```

### Cada alumno (ej. alumno con IP 192.168.1.5):

```powershell
python main.py --host 192.168.1.5 --seed-host 192.168.1.1
```

El nodo se registra en el seed del instructor, descubre a los demás alumnos y comienza a participar en la red.

---

## Output al Arrancar

```
╔══════════════════════════════════════════════╗
║         NODO P2P — BLOCKCHAIN DEMO           ║
╚══════════════════════════════════════════════╝

  Node ID:    node_5000
  P2P:        ws://192.168.1.5:5000
  Dashboard:  http://192.168.1.5:8000
  Wallet:     1A2B3CXyz4D5E6F...
  Seed:       192.168.1.1:8888

  Bootstrap peers: 0
  Presiona Ctrl+C para detener
```

---

## Diferencia con los Launchers

| Aspecto | `main.py` | `launcher_manual.py` / `launcher_auto.py` |
|---------|-----------|------------------------------------------|
| Nodos | 1 por ejecución | 5 (o N) en un solo proceso |
| Uso | LAN, 1 máquina = 1 nodo | Demo local, múltiples nodos en 1 máquina |
| Seed | Externo (`main_seed.py`) | Integrado (en `launcher_auto.py`) |
| Dashboard | Opcional (`--no-dashboard`) | Siempre activo |
| Configuración | Via argumentos CLI | Hardcoded en el script |

---

## Bloque `if __name__ == '__main__'`

```python
if __name__ == '__main__':
    asyncio.run(main())
```

`asyncio.run()` crea el event loop, ejecuta la coroutine `main()` y lo cierra al terminar. Es el punto de entrada estándar para programas async en Python 3.7+.

---

*Documento: `DOC_main.md` — Demo Blockchain*
