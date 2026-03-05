# Documentación Técnica: `demo_tx_cli.py`

---

## Propósito del Archivo

`demo_tx_cli.py` es un script de demostración que verifica la funcionalidad completa de la integración P2P + Transacciones mediante un demo automatizado en terminal. Levanta 5 nodos, crea 3 transacciones hardcodeadas y muestra la propagación en tiempo real.

**Analogía:** Este demo es como una prueba de sonido antes de un concierto:
- **Rápida** → Verifica que todo funciona en 15 segundos
- **Automática** → No requiere interacción del usuario
- **Visual** → Muestra claramente qué sucede
- **Validación** → Confirma que la red funciona correctamente

---

## Diferencia con `launcher_dashboard.py`

| Aspecto | `demo_tx_cli.py` (Fase A) | `launcher_dashboard.py` (Fase B) |
|---------|---------------------------|----------------------------------|
| Propósito | Verificar funcionalidad | Demo interactivo para evaluador |
| Interfaz | Terminal (texto) | Navegador web (GUI) |
| Interacción | Automática (hardcoded) | Manual (usuario crea TXs) |
| TXs creadas | 3 fijas | Ilimitadas (usuario decide) |
| Visualización | Print statements | HTML + CSS + JavaScript |
| Auto-refresh | ❌ | ✅ Cada 2 segundos |
| Dashboard Flask | ❌ | ✅ 5 dashboards |
| Duración | ~15 segundos + espera final | Indefinida |
| Uso típico | Testing rápido | Presentación formal |
| Threads | 1 (solo asyncio) | 6 (asyncio + 5 Flask) |

---

## Dependencias

```python
import asyncio
from network.p2p_node import P2PNode
```

| Import | Propósito |
|--------|-----------|
| `asyncio` | Programación asíncrona para múltiples nodos |
| `P2PNode` | Nodo P2P completo (red + wallet + mempool) |

**Nota:** No requiere Flask, threading ni ninguna dependencia de UI.

---

## Configuración: `NODES_CONFIG`

```python
NODES_CONFIG = [
    {'port': 5000, 'bootstrap': []},
    {'port': 5001, 'bootstrap': [('localhost', 5000)]},
    {'port': 5002, 'bootstrap': [('localhost', 5000)]},
    {'port': 5003, 'bootstrap': [('localhost', 5001)]},
    {'port': 5004, 'bootstrap': [('localhost', 5002)]},
]
```

**Diferencia con `launcher_dashboard.py`:**

- ❌ NO tiene `dashboard_port` (no hay Flask)
- ✅ Solo tiene `port` (P2P) y `bootstrap`

**Topología idéntica:**

```
Nodo 1 (5000) ← Seed
  ↑
  ├──── Nodo 2 (5001)
  │       ↑
  │       └──── Nodo 4 (5003)
  │
  └──── Nodo 3 (5002)
          ↑
          └──── Nodo 5 (5004)
```

---

## Función `start_node`

```python
async def start_node(config):
    node = P2PNode(
        host='localhost',
        port=config['port'],
        bootstrap_peers=config['bootstrap']
    )
    asyncio.create_task(node.start())
    await asyncio.sleep(0.5)
    return node
```

**¿Qué hace?**

Crea e inicia un nodo P2P de forma simplificada (sin dashboard).

**Diferencia con `launcher_dashboard.py`:**

```python
# demo_tx_cli.py (simple):
node = P2PNode(...)
asyncio.create_task(node.start())
return node

# launcher_dashboard.py (complejo):
node = P2PNode(...)
node.loop = asyncio.get_event_loop()  # Para Flask
node.start_task = asyncio.create_task(node.start())
dashboard = NodeDashboard(node, port)  # Crear dashboard
threading.Thread(target=dashboard.run).start()  # Thread Flask
return node, dashboard
```

**¿Por qué es más simple?**

No necesita coordinar con Flask, por lo tanto:
- ❌ No guarda `node.loop`
- ❌ No crea dashboard
- ❌ No maneja threads
- ✅ Solo inicia el nodo P2P

---

## Función `main`

La función `main` tiene 5 fases claramente marcadas:

### **Fase 1: Levantar 5 nodos**

```python
print("[1/4] Levantando 5 nodos...")
nodes = []
for i, config in enumerate(NODES_CONFIG, 1):
    print(f"      Nodo {i} (puerto {config['port']})...")
    node = await start_node(config)
    nodes.append(node)

print(f"      ✓ 5 nodos iniciados\n")
```

**¿Qué hace?**

Inicializa los 5 nodos secuencialmente, mostrando progreso visual.

**Output esperado:**

```
[1/4] Levantando 5 nodos...
      Nodo 1 (puerto 5000)...
      Nodo 2 (puerto 5001)...
      Nodo 3 (puerto 5002)...
      Nodo 4 (puerto 5003)...
      Nodo 5 (puerto 5004)...
      ✓ 5 nodos iniciados
```

**Timeline:**

```
T=0.0s: Nodo 1 inicia
T=0.5s: Nodo 2 inicia (sleep en start_node)
T=1.0s: Nodo 3 inicia
T=1.5s: Nodo 4 inicia
T=2.0s: Nodo 5 inicia
T=2.5s: Todos iniciados
```

---

### **Fase 2: Esperar gossip**

```python
print("[2/4] Esperando descubrimiento de peers (gossip protocol)...")
await asyncio.sleep(8)

for i, node in enumerate(nodes, 1):
    print(f"      Nodo {i}: {len(node.peers_connected)} peers conectados")
print()
```

**¿Qué hace?**

Da tiempo al gossip protocol para descubrir todos los peers y conectarlos.

**¿Por qué 8 segundos?**

```
T=0s: Nodos 2,3 conectan a Nodo 1
T=2s: Nodos 4,5 conectan a Nodos 2,3
T=3s: Primer gossip loop (60s configurado, pero algunos nodos piden antes)
T=5s: Gossip completa el descubrimiento
T=8s: Todos conectados y estables
```

**Output esperado:**

```
[2/4] Esperando descubrimiento de peers (gossip protocol)...
      Nodo 1: 4 peers conectados
      Nodo 2: 4 peers conectados
      Nodo 3: 4 peers conectados
      Nodo 4: 4 peers conectados
      Nodo 5: 4 peers conectados
```

**Si algún nodo muestra <4 peers:**

Significa que el gossip no completó. Posibles causas:
- Timeout muy corto (aumentar a 10s)
- Nodo falló al iniciar
- Puerto ocupado

---

### **Fase 3: Mostrar wallets**

```python
print("[3/4] Wallets de cada nodo:")
print("-" * 70)
for i, node in enumerate(nodes, 1):
    print(f"  Nodo {i}: {node.wallet.address}")
    print(f"           Balance inicial: {node.get_balance()}")
print()
```

**¿Qué hace?**

Muestra las addresses únicas y balances iniciales de cada nodo.

**Output esperado:**

```
[3/4] Wallets de cada nodo:
----------------------------------------------------------------------
  Nodo 1: 1HydBLQ77qugdXUW9KmTXkSKNukWg7JhUm
           Balance inicial: 100.0
  Nodo 2: 1Mq361PiGkLQeQzkrAbvkhRVyHFp8cRU2U
           Balance inicial: 100.0
  Nodo 3: 1Bt4CAkXbz6qXkfZPeKM99oDeUu7VLTaT3
           Balance inicial: 100.0
  Nodo 4: 1KhUGZWJA5JGN6Dxu8mEpzSq8kWwwUjoPj
           Balance inicial: 100.0
  Nodo 5: 19wuWUNEJTojiBHWTawDb894UMRCrQwnct
           Balance inicial: 100.0
```

**¿Por qué mostrar esto?**

Demuestra que:
- ✅ Cada nodo tiene wallet única (addresses diferentes)
- ✅ Todas usan Base58Check (empiezan con '1')
- ✅ Balance inicial correcto (100.0 hardcoded)

---

### **Fase 4: Crear y propagar transacciones**

```python
print("[4/4] Creando y propagando transacciones...")
print("-" * 70)

# TX 1: Nodo 1 → Nodo 2 (10 coins)
print("\n► TX1: Nodo 1 envía 10 coins a Nodo 2")
tx1 = nodes[0].create_transaction(nodes[1].wallet.address, 10)
await nodes[0].broadcast_transaction(tx1)
await asyncio.sleep(2)

print(f"  Propagación:")
for i, node in enumerate(nodes, 1):
    count = len(node.mempool)
    print(f"    Nodo {i}: {count} TX en mempool")
```

**¿Qué hace?**

Crea una TX en el Nodo 1, la propaga por la red y verifica que llegó a todos.

**Proceso detallado:**

```
1. Crear TX
   └─ nodes[0].create_transaction(addr_nodo2, 10)
   └─ Firma con wallet de Nodo 1
   └─ Agrega a mempool local de Nodo 1

2. Propagar TX
   └─ nodes[0].broadcast_transaction(tx1)
   └─ Envía a 4 peers conectados

3. Esperar propagación
   └─ await asyncio.sleep(2)
   └─ Tiempo para que llegue a todos

4. Verificar propagación
   └─ Revisar len(mempool) en los 5 nodos
   └─ Todos deberían tener 1 TX
```

**Output esperado:**

```
► TX1: Nodo 1 envía 10 coins a Nodo 2
  Propagación:
    Nodo 1: 1 TX en mempool
    Nodo 2: 1 TX en mempool
    Nodo 3: 1 TX en mempool
    Nodo 4: 1 TX en mempool
    Nodo 5: 1 TX en mempool
```

**TX 2 y TX 3:**

Mismo proceso, creando cadena de transacciones:

```
TX1: Nodo 1 → Nodo 2 (10 coins)
TX2: Nodo 2 → Nodo 3 (5 coins)
TX3: Nodo 3 → Nodo 4 (2 coins)
```

**¿Por qué `await asyncio.sleep(2)` entre TXs?**

Dar tiempo a que la propagación P2P complete antes de crear la siguiente:

```
Sin delay:
  T=0s: TX1, TX2, TX3 creadas simultáneamente
  T=1s: Red saturada procesando 3 TXs al mismo tiempo
  
Con delay de 2s:
  T=0s: TX1 creada
  T=2s: TX1 propagada, TX2 creada
  T=4s: TX2 propagada, TX3 creada
  T=6s: TX3 propagada
```

---

### **Fase 5: Resultado final**

```python
print("\n" + "=" * 70)
print("  RESULTADO FINAL")
print("=" * 70)
print("\nBalances:")
for i, node in enumerate(nodes, 1):
    balance = node.get_balance()
    print(f"  Nodo {i}: {balance:.2f} coins (cambio: {balance - 100:+.2f})")

print(f"\nMempool (sincronizado en todos los nodos):")
print(f"  {len(nodes[0].mempool)} transacciones confirmadas\n")

for i, tx in enumerate(nodes[0].mempool, 1):
    print(f"  TX{i}: {tx.hash()[:16]}...")
    print(f"       {tx.from_address[:12]}... → {tx.to_address[:12]}...")
    print(f"       Monto: {tx.amount} coins\n")
```

**¿Qué hace?**

Muestra el estado final: balances actualizados y lista completa de TXs.

**Output esperado:**

```
======================================================================
  RESULTADO FINAL
======================================================================

Balances:
  Nodo 1: 90.00 coins (cambio: -10.00)
  Nodo 2: 105.00 coins (cambio: +5.00)
  Nodo 3: 103.00 coins (cambio: +3.00)
  Nodo 4: 102.00 coins (cambio: +2.00)
  Nodo 5: 100.00 coins (cambio: +0.00)

Mempool (sincronizado en todos los nodos):
  3 transacciones confirmadas

  TX1: ef8e23b3006f6730...
       1HydBLQ77qug... → 1Mq361PiGkLQ...
       Monto: 10 coins

  TX2: db2050263c47801a...
       1Mq361PiGkLQ... → 1Bt4CAkXbz6q...
       Monto: 5 coins

  TX3: 0bcc97a25dd35022...
       1Bt4CAkXbz6q... → 1KhUGZWJA5JG...
       Monto: 2 coins
```

**Validación de balances:**

```
Nodo 1: 100 - 10 = 90  ✅
Nodo 2: 100 + 10 - 5 = 105  ✅
Nodo 3: 100 + 5 - 2 = 103  ✅
Nodo 4: 100 + 2 = 102  ✅
Nodo 5: 100 (sin TXs) = 100  ✅

Total: 90 + 105 + 103 + 102 + 100 = 500
Balance global conservado ✅
```

**¿Por qué mostrar solo el mempool de `nodes[0]`?**

Porque todos los nodos tienen el mismo mempool (sincronizado). Mostrarlo 5 veces sería redundante.

---

### **Mantener corriendo**

```python
print("=" * 70)
print("✓ Demo completado. Presiona Ctrl+C para salir")
print("=" * 70 + "\n")

try:
    await asyncio.Future()
except KeyboardInterrupt:
    print("\nCerrando nodos...")
```

**¿Qué hace?**

Mantiene el programa corriendo hasta que el usuario presione Ctrl+C.

**¿Por qué mantener corriendo después del demo?**

Para poder inspeccionar los logs:

```
Demo completado
[Usuario presiona Ctrl+C después de revisar logs]
Cerrando nodos...
```

Sin esto, el programa terminaría automáticamente y no habría tiempo de revisar.

---

## Bloque `if __name__ == "__main__"`

```python
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo terminado.")
```

**Idéntico a `launcher_dashboard.py`:**
- Ejecuta `main()` con asyncio
- Maneja Ctrl+C limpiamente

---

## Flujo Temporal Completo

```
T=0s     [1/4] Levantando nodos
T=2.5s   ✓ 5 nodos iniciados

T=2.5s   [2/4] Esperando gossip
T=10.5s  Gossip completado (4 peers cada nodo)

T=10.5s  [3/4] Mostrar wallets
         5 addresses únicas mostradas

T=11s    [4/4] Crear TXs
T=11s    TX1 creada y propagada
T=13s    Verificar: 5 nodos tienen 1 TX
T=13s    TX2 creada y propagada
T=15s    Verificar: 5 nodos tienen 2 TXs
T=15s    TX3 creada y propagada
T=17s    Verificar: 5 nodos tienen 3 TXs

T=17s    RESULTADO FINAL
         Balances: 90, 105, 103, 102, 100
         Mempool: 3 TXs sincronizadas

T=17s    ✓ Demo completado
T=∞      await asyncio.Future() (hasta Ctrl+C)
```

**Duración total:** ~17 segundos (sin contar espera final)

---

## Casos de Éxito vs Fallo

### ✅ **Éxito:**

```
[2/4] Esperando gossip...
      Nodo 1: 4 peers conectados  ← Todos con 4
      Nodo 2: 4 peers conectados
      Nodo 3: 4 peers conectados
      Nodo 4: 4 peers conectados
      Nodo 5: 4 peers conectados

► TX1: Nodo 1 envía 10 coins a Nodo 2
  Propagación:
    Nodo 1: 1 TX en mempool  ← Todos con 1
    Nodo 2: 1 TX en mempool
    Nodo 3: 1 TX en mempool
    Nodo 4: 1 TX en mempool
    Nodo 5: 1 TX en mempool

Balances:
  Nodo 1: 90.00 coins (cambio: -10.00)  ← Cambios correctos
  Nodo 2: 105.00 coins (cambio: +5.00)
```

### ❌ **Fallo - Gossip incompleto:**

```
[2/4] Esperando gossip...
      Nodo 1: 2 peers conectados  ← NO todos con 4
      Nodo 2: 3 peers conectados
      Nodo 3: 1 peers conectados
      Nodo 4: 2 peers conectados
      Nodo 5: 0 peers conectados

Problema: Aumentar sleep de 8s a 12s
```

### ❌ **Fallo - Propagación incompleta:**

```
► TX1: Nodo 1 envía 10 coins a Nodo 2
  Propagación:
    Nodo 1: 1 TX en mempool
    Nodo 2: 1 TX en mempool
    Nodo 3: 0 TX en mempool  ← Nodo 3 no recibió
    Nodo 4: 1 TX en mempool
    Nodo 5: 1 TX en mempool

Problema: Nodo 3 no está bien conectado
```

---

## Comparación de Outputs

### `demo_tx_cli.py` (este archivo):

```
[1/4] Levantando 5 nodos...
[2/4] Esperando gossip...
[3/4] Wallets de cada nodo:
[4/4] Creando transacciones...

Balances:
  Nodo 1: 90.00 coins
  ...

✓ Demo completado
```

### `launcher_dashboard.py`:

```
[1/5] Iniciando Nodo 1...
        P2P:       localhost:5000
        Dashboard: http://localhost:8000
[2/5] Iniciando Nodo 2...
...

Abre tu navegador en estas URLs:
  Nodo 1: http://localhost:8000
  ...

Presiona Ctrl+C para detener
```

**Diferencia clave:**
- CLI: Muestra resultados en terminal
- Dashboard: Da URLs para navegador

---

## Uso Típico

### **Durante desarrollo:**

```bash
# Verificar cambios rápidamente
python demo_tx_cli.py

# Output en 17 segundos
# ✓ Todo funciona
```

### **Antes de presentar al evaluador:**

```bash
# 1. Verificar con CLI
python demo_tx_cli.py
# ✓ Funciona

# 2. Presentar con Dashboard
python launcher_dashboard.py
# Mostrar navegador al evaluador
```

---

## Troubleshooting

### Problema: "Nodo X: 0 peers conectados"

**Causa:** Puerto ocupado o nodo no inició

**Solución:**
```bash
# Verificar puertos
netstat -an | grep 5000

# Matar procesos previos
pkill -f demo_tx_cli.py
```

### Problema: "Nodo 3: 0 TX en mempool"

**Causa:** Propagación falló (desconectado)

**Verificar:**
- ¿Cuántos peers tiene Nodo 3?
- Si tiene 0 peers, aumentar sleep del gossip

### Problema: Balances incorrectos

**Causa:** Bug en get_balance() o TXs duplicadas

**Verificar:**
```python
# En cada nodo
print(f"Mempool size: {len(node.mempool)}")
for tx in node.mempool:
    print(f"  {tx.hash()}")
# ¿Hay TXIDs duplicados?
```

---

## Extensiones Posibles

### Agregar más TXs:

```python
# TX 4: Nodo 4 → Nodo 5 (1 coin)
tx4 = nodes[3].create_transaction(nodes[4].wallet.address, 1)
await nodes[3].broadcast_transaction(tx4)
await asyncio.sleep(2)

# TX 5: Nodo 5 → Nodo 1 (3 coins)
tx5 = nodes[4].create_transaction(nodes[0].wallet.address, 3)
await nodes[4].broadcast_transaction(tx5)
```

### Verificar TXIDs únicos:

```python
# Después de crear todas las TXs
txids = [tx.hash() for tx in nodes[0].mempool]
print(f"\nTXIDs únicos: {len(set(txids))} de {len(txids)}")
# Debe ser 3 de 3 (sin duplicados)
```

### Simular fallo de propagación:

```python
# Desconectar Nodo 3 antes de TX2
node3_peers = list(nodes[2].peers_connected.values())
for ws in node3_peers:
    await ws.close()

# TX2 NO llegará a Nodo 3
tx2 = nodes[1].create_transaction(nodes[2].wallet.address, 5)
await nodes[1].broadcast_transaction(tx2)

# Verificar:
print(f"Nodo 3: {len(nodes[2].mempool)} TXs")  # → 1 (solo TX1)
```

---

## Ventajas y Desventajas

### ✅ **Ventajas:**

- Rápido (17 segundos)
- Automatizado (no requiere interacción)
- Reproducible (siempre mismo resultado)
- Simple (sin UI compleja)
- Ideal para testing continuo

### ❌ **Desventajas:**

- No interactivo (TXs hardcoded)
- No visual (solo texto)
- No impresiona al evaluador
- Difícil de demostrar conceptos a no-técnicos

---

## Cuándo Usar Cada Demo

| Situación | Usar |
|-----------|------|
| Testing rápido durante desarrollo | `demo_tx_cli.py` |
| Verificar que todo funciona | `demo_tx_cli.py` |
| Presentar al evaluador | `launcher_dashboard.py` |
| Demo para no-técnicos | `launcher_dashboard.py` |
| Debugging de red | `demo_tx_cli.py` |
| Mostrar UI/UX | `launcher_dashboard.py` |

---

*Documento: `DOC_demo_tx_cli.md` — Demo Blockchain Fase A (CLI Automatizado)*
