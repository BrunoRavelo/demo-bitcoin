# Documentación Técnica: `launcher_dashboard.py`

---

## Propósito del Archivo

`launcher_dashboard.py` es el punto de entrada principal para ejecutar el demo completo con interfaz web. Levanta 5 nodos P2P simultáneos, cada uno con su propio dashboard Flask, y coordina su inicio ordenado.

**Analogía:** El launcher es como un director de orquesta que:
- **Prepara los músicos** (configura cada nodo)
- **Los hace entrar en orden** (inicio secuencial con delays)
- **Coordina la actuación** (mantiene todo sincronizado)
- **Gestiona el final** (cierre limpio con Ctrl+C)

---

## Diferencia con `demo_tx_cli.py`

| Aspecto | `demo_tx_cli.py` | `launcher_dashboard.py` |
|---------|------------------|-------------------------|
| Interfaz | Terminal (CLI) | Navegador web (GUI) |
| Interacción | Hardcodeada | Usuario crea TXs manualmente |
| TXs automáticas | ✅ 3 TXs de prueba | ❌ Usuario decide |
| Dashboard Flask | ❌ No | ✅ 5 dashboards (puertos 8000-8004) |
| Propósito | Verificar funcionalidad | Demo para evaluador |
| Auto-refresh | ❌ No | ✅ Cada 2 segundos |

---

## Dependencias

```python
import asyncio
import threading
from network.p2p_node import P2PNode
from dashboard.app import NodeDashboard
```

| Import | Propósito |
|--------|-----------|
| `asyncio` | Programación asíncrona para P2P |
| `threading` | Ejecutar Flask en threads separados |
| `P2PNode` | Nodo P2P completo (red + wallet + mempool) |
| `NodeDashboard` | Servidor web Flask por nodo |

---

## Configuración: `NODES_CONFIG`

```python
NODES_CONFIG = [
    {'p2p_port': 5000, 'dashboard_port': 8000, 'bootstrap': []},
    {'p2p_port': 5001, 'dashboard_port': 8001, 'bootstrap': [('localhost', 5000)]},
    {'p2p_port': 5002, 'dashboard_port': 8002, 'bootstrap': [('localhost', 5000)]},
    {'p2p_port': 5003, 'dashboard_port': 8003, 'bootstrap': [('localhost', 5001)]},
    {'p2p_port': 5004, 'dashboard_port': 8004, 'bootstrap': [('localhost', 5002)]},
]
```

**Estructura de cada entrada:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `p2p_port` | `int` | Puerto WebSocket para P2P (5000-5004) |
| `dashboard_port` | `int` | Puerto HTTP para Flask (8000-8004) |
| `bootstrap` | `list` | Peers iniciales para conectar |

**Topología de bootstrap:**

```
Nodo 1 (5000) ← Seed
  ↑
  ├──── Nodo 2 (5001)
  │       ↑
  │       └──── Nodo 4 (5003)
  │
  ├──── Nodo 3 (5002)
  │       ↑
  │       └──── Nodo 5 (5004)
  
Después del gossip:
  Todos conectados a todos (red mesh)
```

**¿Por qué esta topología?**

- **Nodo 1 es seed:** No tiene bootstrap (es el primero)
- **Nodos 2 y 3:** Conectan a Nodo 1 (descubren la red)
- **Nodos 4 y 5:** Conectan a Nodos 2 y 3 (distribución de carga)
- **Resultado:** Gossip completa la mesh en ~10 segundos

**¿Por qué puertos diferentes?**

Cada servicio necesita su puerto exclusivo:

```
Nodo 1:
  - P2P:       localhost:5000  ← WebSocket para red P2P
  - Dashboard: localhost:8000  ← HTTP para navegador

Nodo 2:
  - P2P:       localhost:5001
  - Dashboard: localhost:8001

... etc
```

Si usaran el mismo puerto, habría conflicto:
```
Error: Address already in use (puerto ocupado)
```

---

## Función `start_node_with_dashboard`

```python
async def start_node_with_dashboard(config):
    # Crear nodo P2P
    node = P2PNode(
        host='localhost',
        port=config['p2p_port'],
        bootstrap_peers=config['bootstrap']
    )
    
    # Guardar loop para uso de Flask
    node.loop = asyncio.get_event_loop()
    
    # Iniciar nodo en background
    node.start_task = asyncio.create_task(node.start())
    
    # Esperar a que arranque
    await asyncio.sleep(0.5)
    
    # Crear dashboard
    dashboard = NodeDashboard(node, config['dashboard_port'])
    
    # Iniciar dashboard en thread separado
    dashboard_thread = threading.Thread(
        target=dashboard.run,
        daemon=True
    )
    dashboard_thread.start()
    
    return node, dashboard
```

**¿Qué hace?**

Inicializa un nodo P2P y su dashboard Flask, coordinándolos para que trabajen juntos.

**Proceso paso a paso:**

```
1. Crear nodo P2P
   └─ P2PNode(host, port, bootstrap_peers)

2. Guardar event loop
   └─ node.loop = asyncio.get_event_loop()
   └─ Flask lo necesita para broadcast_transaction()

3. Iniciar servidor P2P
   └─ asyncio.create_task(node.start())
   └─ Corre en background (no bloquea)

4. Esperar arranque
   └─ await asyncio.sleep(0.5)
   └─ Da tiempo a que WebSocket escuche

5. Crear dashboard Flask
   └─ NodeDashboard(node, dashboard_port)
   └─ Conecta dashboard con el nodo

6. Iniciar Flask en thread
   └─ threading.Thread(target=dashboard.run)
   └─ daemon=True (cierra con el programa)
   └─ .start() inicia el servidor HTTP

7. Retornar referencias
   └─ return (node, dashboard)
   └─ Para mantener vivas las referencias
```

**¿Por qué `node.loop = asyncio.get_event_loop()`?**

Flask corre en un thread síncrono, pero necesita ejecutar código asíncrono:

```python
# En dashboard/app.py:
@app.route('/send_tx', methods=['POST'])
def send_tx():
    tx = node.create_transaction(...)
    
    # Flask está en thread síncrono
    # node.broadcast_transaction() es async
    asyncio.run_coroutine_threadsafe(
        node.broadcast_transaction(tx),
        node.loop  # ← Necesita el loop del nodo
    )
```

**¿Por qué `daemon=True`?**

Los threads daemon se cierran automáticamente cuando el programa principal termina:

```python
# Con daemon=True:
Ctrl+C → main() termina → threads daemon cierran → programa termina

# Sin daemon=True:
Ctrl+C → main() termina → threads siguen corriendo → programa colgado
```

**¿Por qué `await asyncio.sleep(0.5)`?**

Dar tiempo a que el servidor WebSocket arranque antes de crear el dashboard:

```
Sin sleep:
  T=0.00s: create_task(node.start())
  T=0.01s: NodeDashboard(node, ...)  ← node.wallet puede no existir todavía
  T=0.10s: node.start() completa init

Con sleep:
  T=0.00s: create_task(node.start())
  T=0.50s: NodeDashboard(node, ...)  ← node.wallet ya existe
```

---

## Función `main`

```python
async def main():
    print("\n" + "=" * 70)
    print("  BLOCKCHAIN DEMO - Dashboard Interactivo")
    print("=" * 70)
    print()
    
    nodes = []
    dashboards = []
    
    for i, config in enumerate(NODES_CONFIG, 1):
        print(f"[{i}/5] Iniciando Nodo {i}...")
        print(f"        P2P:       localhost:{config['p2p_port']}")
        print(f"        Dashboard: http://localhost:{config['dashboard_port']}")
        
        node, dashboard = await start_node_with_dashboard(config)
        nodes.append(node)
        dashboards.append(dashboard)
        
        await asyncio.sleep(1)
    
    print()
    print("=" * 70)
    print("  Todos los nodos iniciados correctamente")
    print("=" * 70)
    print()
    print("Abre tu navegador en estas URLs:")
    for i, config in enumerate(NODES_CONFIG, 1):
        print(f"  Nodo {i}: http://localhost:{config['dashboard_port']}")
    print()
    print("Presiona Ctrl+C para detener todos los nodos")
    print("=" * 70)
    print()
    
    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        print("\n\nCerrando nodos...")
```

**¿Qué hace?**

Función principal que coordina el inicio de todos los nodos y mantiene el programa corriendo.

**Flujo completo:**

```
1. Imprimir banner
   └─ "BLOCKCHAIN DEMO - Dashboard Interactivo"

2. Inicializar listas
   └─ nodes = []       (referencias a P2PNode)
   └─ dashboards = []  (referencias a NodeDashboard)

3. Loop: para cada config en NODES_CONFIG
   ├─ Imprimir progreso ([1/5], [2/5], ...)
   ├─ Mostrar puertos (P2P: 5000, Dashboard: 8000)
   ├─ Llamar start_node_with_dashboard(config)
   ├─ Guardar referencias (nodes.append, dashboards.append)
   └─ Esperar 1 segundo (inicio escalonado)

4. Imprimir resumen
   └─ "Todos los nodos iniciados correctamente"
   └─ Lista de URLs para el navegador

5. Mantener corriendo
   └─ await asyncio.Future()  (espera infinita)

6. Manejar Ctrl+C
   └─ KeyboardInterrupt → imprimir "Cerrando nodos..."
```

**¿Por qué `await asyncio.sleep(1)` entre nodos?**

Inicio escalonado previene problemas:

```
Sin delay:
  T=0s: Los 5 nodos intentan conectar simultáneamente
  T=0s: Nodo 1 todavía no está escuchando
  T=0s: Nodos 2-5 fallan al conectar
  T=1s: Nodo 1 finalmente escucha (tarde)

Con delay de 1s:
  T=0s: Nodo 1 inicia
  T=1s: Nodo 2 inicia → Nodo 1 ya escucha ✅
  T=2s: Nodo 3 inicia → Nodo 1 ya escucha ✅
  T=3s: Nodo 4 inicia → Nodos 1,2 escuchan ✅
  T=4s: Nodo 5 inicia → Nodos 1,2,3 escuchan ✅
```

**¿Por qué guardar referencias en listas?**

Prevenir garbage collection:

```python
# SIN guardar referencias:
for config in NODES_CONFIG:
    node, dashboard = await start_node_with_dashboard(config)
    # node y dashboard son variables locales
    # Python puede eliminarlos del heap

# CON referencias guardadas:
nodes.append(node)
dashboards.append(dashboard)
# Python mantiene los objetos vivos
```

**¿Por qué `await asyncio.Future()`?**

Es un "esperar para siempre" que mantiene el programa corriendo:

```python
# Sin await asyncio.Future():
async def main():
    # ... iniciar nodos
    print("URLs disponibles")
    # main() termina aquí
    # Programa cierra (nodos se destruyen)

# Con await asyncio.Future():
async def main():
    # ... iniciar nodos
    await asyncio.Future()  # ← Nunca retorna
    # Programa se queda aquí (nodos siguen corriendo)
```

---

## Bloque `if __name__ == "__main__"`

```python
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo terminado.")
```

**¿Qué hace?**

Punto de entrada del script. Ejecuta `main()` y maneja el cierre limpio con Ctrl+C.

**¿Por qué `if __name__ == "__main__"`?**

Previene ejecución accidental al importar:

```python
# Si ejecutas: python launcher_dashboard.py
__name__ = "__main__"  → Se ejecuta el bloque

# Si importas: from launcher_dashboard import NODES_CONFIG
__name__ = "launcher_dashboard"  → NO se ejecuta el bloque
```

**¿Por qué `asyncio.run(main())`?**

Crea el event loop y ejecuta la coroutine principal:

```python
# Equivalente a:
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
try:
    loop.run_until_complete(main())
finally:
    loop.close()
```

**¿Por qué `try/except KeyboardInterrupt`?**

Manejo limpio de Ctrl+C:

```python
# Sin try/except:
Ctrl+C → Traceback largo y feo → confuso

# Con try/except:
Ctrl+C → "Demo terminado." → limpio y claro
```

---

## Output de Ejecución

```
$ python launcher_dashboard.py

======================================================================
  BLOCKCHAIN DEMO - Dashboard Interactivo
======================================================================

[1/5] Iniciando Nodo 1...
        P2P:       localhost:5000
        Dashboard: http://localhost:8000
[2/5] Iniciando Nodo 2...
        P2P:       localhost:5001
        Dashboard: http://localhost:8001
[3/5] Iniciando Nodo 3...
        P2P:       localhost:5002
        Dashboard: http://localhost:8002
[4/5] Iniciando Nodo 4...
        P2P:       localhost:5003
        Dashboard: http://localhost:8003
[5/5] Iniciando Nodo 5...
        P2P:       localhost:5004
        Dashboard: http://localhost:8004

======================================================================
  Todos los nodos iniciados correctamente
======================================================================

Abre tu navegador en estas URLs:
  Nodo 1: http://localhost:8000
  Nodo 2: http://localhost:8001
  Nodo 3: http://localhost:8002
  Nodo 4: http://localhost:8003
  Nodo 5: http://localhost:8004

Presiona Ctrl+C para detener todos los nodos
======================================================================

[logs de red P2P continúan...]
```

---

## Flujo de Usuario

**1. Ejecutar el launcher:**
```bash
python launcher_dashboard.py
```

**2. Esperar a que todos los nodos inicien:**
```
[1/5] Iniciando Nodo 1...
[2/5] Iniciando Nodo 2...
...
Todos los nodos iniciados correctamente
```

**3. Abrir navegador en 5 tabs:**
- Tab 1: http://localhost:8000 (Nodo 1)
- Tab 2: http://localhost:8001 (Nodo 2)
- Tab 3: http://localhost:8002 (Nodo 3)
- Tab 4: http://localhost:8003 (Nodo 4)
- Tab 5: http://localhost:8004 (Nodo 5)

**4. Ver info en cada dashboard:**
- Wallet address única por nodo
- Balance inicial: 100 coins
- Peers conectados: 4 peers
- Mempool: vacío inicialmente

**5. Crear transacción:**
- En Nodo 1: Copiar address
- En Nodo 2: Pegar address en "Destinatario"
- Ingresar cantidad (ej: 10)
- Click "Enviar Transaccion"

**6. Observar propagación:**
- TX aparece en mempool de Nodo 2 instantáneamente
- 2 segundos después: TX aparece en los 5 dashboards
- Balances actualizados:
  - Nodo 1: 90 (envió 10)
  - Nodo 2: 110 (recibió 10)
  - Otros: 100 (sin cambios)

**7. Cerrar todo:**
```
Ctrl+C en terminal
→ "Cerrando nodos..."
→ "Demo terminado."
```

---

## Arquitectura de Threads

```
Main Process
│
├─ Main Thread (asyncio)
│  ├─ Event Loop
│  │  ├─ Nodo 1 (P2PNode.start())  ← Task asyncio
│  │  ├─ Nodo 2 (P2PNode.start())  ← Task asyncio
│  │  ├─ Nodo 3 (P2PNode.start())  ← Task asyncio
│  │  ├─ Nodo 4 (P2PNode.start())  ← Task asyncio
│  │  └─ Nodo 5 (P2PNode.start())  ← Task asyncio
│  │
│  └─ await asyncio.Future()  (mantiene main thread vivo)
│
├─ Thread 1 (Dashboard Nodo 1)
│  └─ Flask server (puerto 8000)
│
├─ Thread 2 (Dashboard Nodo 2)
│  └─ Flask server (puerto 8001)
│
├─ Thread 3 (Dashboard Nodo 3)
│  └─ Flask server (puerto 8002)
│
├─ Thread 4 (Dashboard Nodo 4)
│  └─ Flask server (puerto 8003)
│
└─ Thread 5 (Dashboard Nodo 5)
   └─ Flask server (puerto 8004)
```

**Total: 6 threads**
- 1 thread principal (asyncio con 5 nodos)
- 5 threads Flask (uno por dashboard)

---

## Comparación con Demo CLI

| Aspecto | `demo_tx_cli.py` | `launcher_dashboard.py` |
|---------|------------------|-------------------------|
| Líneas de código | ~100 | ~100 |
| Interfaz | Terminal | Navegador web |
| Interacción | Automática | Manual |
| TXs de prueba | 3 hardcoded | Usuario decide |
| Visualización | Texto plano | HTML + CSS + JS |
| Auto-refresh | ❌ | ✅ Cada 2s |
| Threads | 1 | 6 |
| Propósito | Testing rápido | Demo presentable |
| Requiere navegador | ❌ | ✅ |
| Para evaluador | Opcional | Recomendado |

---

## Troubleshooting

### Problema 1: "Address already in use"

**Causa:** Puertos ocupados por ejecución anterior

**Solución:**
```bash
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac:
lsof -ti:8000 | xargs kill -9
```

### Problema 2: Dashboard no carga

**Causa:** Flask no arrancó correctamente

**Verificar:**
```bash
# ¿Está escuchando?
netstat -an | grep 8000  # Linux/Mac
netstat -an | findstr 8000  # Windows
```

### Problema 3: TXs no se propagan

**Causa:** Nodos no conectados (gossip falló)

**Verificar en dashboard:**
- "Peers conectados" debe mostrar 4
- Si muestra 0-2, esperar 10 segundos más

### Problema 4: Balance no actualiza

**Causa:** JavaScript no ejecutándose

**Verificar:**
- Abrir DevTools (F12)
- Console tab
- ¿Hay errores rojos?

---

## Extensiones Posibles

### Agregar más nodos:

```python
NODES_CONFIG = [
    # ... 5 nodos existentes
    {'p2p_port': 5005, 'dashboard_port': 8005, 'bootstrap': [('localhost', 5002)]},
    {'p2p_port': 5006, 'dashboard_port': 8006, 'bootstrap': [('localhost', 5003)]},
]
```

### Cambiar topología de bootstrap:

```python
# Topología lineal:
NODES_CONFIG = [
    {'p2p_port': 5000, 'dashboard_port': 8000, 'bootstrap': []},
    {'p2p_port': 5001, 'dashboard_port': 8001, 'bootstrap': [('localhost', 5000)]},
    {'p2p_port': 5002, 'dashboard_port': 8002, 'bootstrap': [('localhost', 5001)]},
    {'p2p_port': 5003, 'dashboard_port': 8003, 'bootstrap': [('localhost', 5002)]},
    {'p2p_port': 5004, 'dashboard_port': 8004, 'bootstrap': [('localhost', 5003)]},
]

# Gossip tardará más (cadena en lugar de árbol)
```

### Agregar nodos en red diferente:

```python
NODES_CONFIG = [
    {'p2p_port': 5000, 'dashboard_port': 8000, 'bootstrap': []},
    {'p2p_port': 5001, 'dashboard_port': 8001, 'bootstrap': [('192.168.1.100', 5000)]},
    # Nodo 2 conecta a Nodo 1 en otra máquina
]
```

---

*Documento: `DOC_launcher_dashboard.md` — Demo Blockchain Fase B (Dashboard Interactivo)*
