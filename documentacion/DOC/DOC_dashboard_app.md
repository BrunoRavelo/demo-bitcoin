# Documentación Técnica: `dashboard/app.py`

---

## Propósito del Archivo

`dashboard/app.py` implementa el servidor web Flask que proporciona la interfaz gráfica para cada nodo P2P. Cada nodo tiene su propio dashboard que muestra información en tiempo real y permite crear transacciones manualmente.

**Analogía:** El dashboard es como el panel de control de un avión:
- **Muestra estado** → wallet, balance, peers, mempool
- **Permite acciones** → crear y enviar transacciones
- **Actualización continua** → auto-refresh cada 2 segundos
- **Interfaz intuitiva** → accesible desde navegador web

---

## Arquitectura Flask + AsyncIO

Este archivo presenta un desafío técnico importante: **Flask es síncrono, pero P2PNode es asíncrono**.

**El problema:**

```python
# Flask corre en thread síncrono
@app.route('/send_tx', methods=['POST'])
def send_tx():
    tx = node.create_transaction(...)
    
    # ¿Cómo llamar a esta función asíncrona?
    await node.broadcast_transaction(tx)  # ← Error: 'await' fuera de async
```

**La solución: `asyncio.run_coroutine_threadsafe()`**

```python
asyncio.run_coroutine_threadsafe(
    node.broadcast_transaction(tx),
    node.loop  # Event loop del nodo
)
```

Esto permite que Flask (síncrono) ejecute código asyncio del nodo.

---

## Dependencias

```python
from flask import Flask, render_template, jsonify, request, redirect
import asyncio
```

| Import | Propósito |
|--------|-----------|
| `Flask` | Servidor web HTTP |
| `render_template` | Renderizar HTML con variables |
| `jsonify` | Convertir Python dict → JSON response |
| `request` | Acceder a datos del formulario POST |
| `redirect` | Redirigir después de enviar TX |
| `asyncio` | Bridge entre Flask y código asíncrono |

---

## Clase `NodeDashboard`

```python
class NodeDashboard:
```

Encapsula el servidor Flask para un nodo P2P específico.

**¿Por qué una clase?**

Cada dashboard necesita su propia instancia de Flask con su propio puerto:

```python
# Sin clase (no funciona):
app = Flask(__name__)  # ← Global, un solo app

# Con clase (funciona):
dashboard1 = NodeDashboard(node1, 8000)  # Puerto 8000
dashboard2 = NodeDashboard(node2, 8001)  # Puerto 8001
# Cada uno independiente
```

**Atributos de instancia:**

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `node` | `P2PNode` | Referencia al nodo P2P |
| `dashboard_port` | `int` | Puerto HTTP del dashboard |
| `app` | `Flask` | Instancia de Flask |

---

## Función `__init__`

```python
def __init__(self, node, dashboard_port):
    self.node = node
    self.dashboard_port = dashboard_port
    self.app = Flask(__name__)
    self.setup_routes()
```

**¿Qué hace?**

Inicializa el dashboard vinculándolo a un nodo P2P y configurando las rutas HTTP.

**Proceso:**

```
1. Guardar referencia al nodo
   └─ self.node = node

2. Guardar puerto del dashboard
   └─ self.dashboard_port = dashboard_port

3. Crear instancia de Flask
   └─ self.app = Flask(__name__)

4. Configurar todas las rutas
   └─ self.setup_routes()
```

**¿Por qué `Flask(__name__)`?**

El argumento `__name__` ayuda a Flask a localizar templates y archivos estáticos:

```
dashboard/
├── app.py  ← __name__ = "dashboard.app"
├── templates/
│   └── dashboard.html
└── static/
    ├── style.css
    └── app.js

Flask usa __name__ para encontrar templates/ y static/
```

---

## Función `setup_routes`

```python
def setup_routes(self):
```

Define todas las rutas HTTP (endpoints) del dashboard. Las rutas se definen como decoradores dentro de esta función.

**Rutas definidas:**

| Ruta | Método | Tipo | Propósito |
|------|--------|------|-----------|
| `/` | GET | HTML | Página principal |
| `/api/info` | GET | JSON | Info general del nodo |
| `/api/wallet` | GET | JSON | Info de la wallet |
| `/api/peers` | GET | JSON | Lista de peers |
| `/api/mempool` | GET | JSON | Transacciones en mempool |
| `/api/all_nodes` | GET | JSON | Lista de todos los nodos |
| `/send_tx` | POST | Form | Crear y enviar TX |

---

### Ruta: `/` (Página principal)

```python
@self.app.route('/')
def index():
    return render_template('dashboard.html',
        node_id=self.node.id,
        p2p_port=self.node.port,
        dashboard_port=self.dashboard_port
    )
```

**¿Qué hace?**

Renderiza la página HTML del dashboard, pasando variables del nodo.

**Variables pasadas al template:**

| Variable | Ejemplo | Uso en HTML |
|----------|---------|-------------|
| `node_id` | `"node_5000"` | Título del dashboard |
| `p2p_port` | `5000` | Mostrar puerto P2P |
| `dashboard_port` | `8000` | Mostrar puerto dashboard |

**En el template HTML:**

```html
<h1>{{ node_id }}</h1>
<span>P2P: {{ p2p_port }}</span>
<span>Dashboard: {{ dashboard_port }}</span>
```

**Flujo:**

```
Usuario navega a http://localhost:8000
  │
  ▼
Flask recibe request GET /
  │
  ▼
Llama a index()
  │
  ▼
render_template('dashboard.html', ...)
  │
  ▼
Reemplaza {{ variables }} en HTML
  │
  ▼
Retorna HTML completo
  │
  ▼
Navegador muestra página
```

---

### Ruta: `/api/info` (Info general)

```python
@self.app.route('/api/info')
def api_info():
    return jsonify({
        'node_id': self.node.id,
        'address': self.node.wallet.address,
        'balance': self.node.get_balance(),
        'peers_count': len(self.node.peers_connected),
        'mempool_count': len(self.node.mempool)
    })
```

**¿Qué hace?**

Retorna información general del nodo en formato JSON.

**Respuesta JSON:**

```json
{
    "node_id": "node_5000",
    "address": "1HydBLQ77qugdXUW9KmTXkSKNukWg7JhUm",
    "balance": 90.0,
    "peers_count": 4,
    "mempool_count": 3
}
```

**¿Quién la usa?**

JavaScript en `app.js` hace fetch cada 2 segundos:

```javascript
// En app.js:
const info = await fetch('/api/info').then(r => r.json());
document.getElementById('wallet-balance').textContent = info.balance;
document.getElementById('peers-count').textContent = info.peers_count;
```

**¿Por qué JSON y no HTML?**

Para permitir actualización parcial sin recargar página:

```
Con HTML:
  Actualización → recargar página completa → flicker

Con JSON:
  Actualización → fetch JSON → actualizar solo números → smooth
```

---

### Ruta: `/api/wallet` (Info de wallet)

```python
@self.app.route('/api/wallet')
def api_wallet():
    return jsonify({
        'address': self.node.wallet.address,
        'balance': self.node.get_balance()
    })
```

**¿Qué hace?**

Retorna información de la wallet del nodo.

**¿Por qué existe si `/api/info` ya incluye esto?**

Originalmente se usaba para el dropdown (descartado). Ahora es redundante pero se mantiene por compatibilidad.

**Podría eliminarse sin afectar funcionalidad actual.**

---

### Ruta: `/api/peers` (Lista de peers)

```python
@self.app.route('/api/peers')
def api_peers():
    peers = []
    for peer_addr in self.node.peers_connected.keys():
        peers.append({
            'address': peer_addr,
            'status': 'connected'
        })
    return jsonify(peers)
```

**¿Qué hace?**

Retorna lista de peers actualmente conectados.

**Respuesta JSON:**

```json
[
    {
        "address": "localhost:5001",
        "status": "connected"
    },
    {
        "address": "localhost:5002",
        "status": "connected"
    },
    {
        "address": "localhost:5003",
        "status": "connected"
    },
    {
        "address": "localhost:5004",
        "status": "connected"
    }
]
```

**Uso en frontend:**

```javascript
// En app.js:
const peers = await fetch('/api/peers').then(r => r.json());
peersList.innerHTML = peers.map(p => `<li>${p.address}</li>`).join('');
```

**¿Por qué `status: 'connected'` está hardcoded?**

Porque `peers_connected` solo contiene peers conectados. Si estuviera desconectado, no estaría en el diccionario.

---

### Ruta: `/api/mempool` (Transacciones)

```python
@self.app.route('/api/mempool')
def api_mempool():
    txs = []
    for tx in self.node.mempool:
        txs.append({
            'txid': tx.hash()[:16] + '...',
            'from': tx.from_address[:12] + '...',
            'to': tx.to_address[:12] + '...',
            'amount': tx.amount,
            'timestamp': tx.timestamp
        })
    return jsonify(txs)
```

**¿Qué hace?**

Retorna lista de transacciones en el mempool con formato simplificado.

**Respuesta JSON:**

```json
[
    {
        "txid": "ef8e23b3006f6730...",
        "from": "1HydBLQ77qug...",
        "to": "1Mq361PiGkLQ...",
        "amount": 10,
        "timestamp": 1707234567.123
    },
    {
        "txid": "db2050263c47801a...",
        "from": "1Mq361PiGkLQ...",
        "to": "1Bt4CAkXbz6q...",
        "amount": 5,
        "timestamp": 1707234568.456
    }
]
```

**¿Por qué truncar TXID y addresses?**

Para legibilidad en UI:

```
# Sin truncar:
ef8e23b3006f67305e4f3c2b1a0987654321fedcba0123456789abcdef0123
1HydBLQ77qugdXUW9KmTXkSKNukWg7JhUm

# Truncado:
ef8e23b3006f6730...
1HydBLQ77qug...

Más compacto visualmente
```

**Uso en frontend:**

```javascript
const mempool = await fetch('/api/mempool').then(r => r.json());
mempoolList.innerHTML = mempool.map(tx => `
    <div class="tx-item">
        <div class="tx-hash">${tx.txid}</div>
        <div>${tx.from} → ${tx.to}</div>
        <span>${tx.amount} coins</span>
    </div>
`).join('');
```

---

### Ruta: `/api/all_nodes` (Lista de nodos)

```python
@self.app.route('/api/all_nodes')
def api_all_nodes():
    nodes = []
    for i in range(5):
        p2p_port = 5000 + i
        dashboard_port = 8000 + i
        nodes.append({
            'name': f'Nodo {i+1}',
            'p2p_port': p2p_port,
            'dashboard_port': dashboard_port
        })
    return jsonify(nodes)
```

**¿Qué hace?**

Retorna lista hardcodeada de todos los nodos del sistema.

**Respuesta JSON:**

```json
[
    {"name": "Nodo 1", "p2p_port": 5000, "dashboard_port": 8000},
    {"name": "Nodo 2", "p2p_port": 5001, "dashboard_port": 8001},
    {"name": "Nodo 3", "p2p_port": 5002, "dashboard_port": 8002},
    {"name": "Nodo 4", "p2p_port": 5003, "dashboard_port": 8003},
    {"name": "Nodo 5", "p2p_port": 5004, "dashboard_port": 8004}
]
```

**¿Por qué hardcoded?**

Originalmente se usaba para el dropdown de destinatarios. Ahora es legado pero se mantiene.

**Estado actual:** No se usa en el frontend (dropdown fue reemplazado por input de texto).

---

### Ruta: `/send_tx` (Enviar transacción)

```python
@self.app.route('/send_tx', methods=['POST'])
def send_tx():
    try:
        to_address = request.form['to_address']
        amount = float(request.form['amount'])
        
        # Crear TX
        tx = self.node.create_transaction(to_address, amount)
        
        # Broadcast (asyncio desde thread Flask)
        asyncio.run_coroutine_threadsafe(
            self.node.broadcast_transaction(tx),
            self.node.loop
        )
        
        return redirect('/')
    except Exception as e:
        return f"Error: {e}", 400
```

**¿Qué hace?**

Recibe formulario POST, crea transacción, la propaga por la red y redirige a la página principal.

**Flujo completo:**

```
1. Usuario llena formulario
   └─ Destinatario: 1BobAddress...
   └─ Cantidad: 10

2. Usuario click "Enviar Transaccion"
   └─ POST a /send_tx

3. Flask recibe request
   └─ to_address = request.form['to_address']
   └─ amount = request.form['amount']

4. Crear TX
   └─ tx = node.create_transaction(to_address, amount)
   └─ Firma con wallet del nodo
   └─ Agrega a mempool local

5. Propagar TX (CRÍTICO)
   └─ asyncio.run_coroutine_threadsafe(
         node.broadcast_transaction(tx),
         node.loop
      )
   └─ Envía TX a todos los peers

6. Redirigir
   └─ return redirect('/')
   └─ Usuario vuelve a ver dashboard

7. Auto-refresh actualiza
   └─ 2 segundos después, JavaScript actualiza mempool
   └─ TX aparece en la lista
```

**El truco: `asyncio.run_coroutine_threadsafe()`**

Este es el puente entre Flask (síncrono) y P2PNode (asíncrono):

```python
# Flask corre en Thread A (síncrono)
def send_tx():
    tx = node.create_transaction(...)  # OK (función síncrona)
    
    # node.broadcast_transaction() es async
    # No podemos hacer: await node.broadcast_transaction(tx)
    # Porque no estamos en función async
    
    # Solución: ejecutar en el event loop del nodo
    asyncio.run_coroutine_threadsafe(
        node.broadcast_transaction(tx),  # Coroutine a ejecutar
        node.loop                        # Event loop donde ejecutar
    )
    # No esperamos el resultado, fire-and-forget
```

**Diagrama de threads:**

```
Thread Flask (síncrono)          Thread Main (asyncio)
       │                                │
       │  send_tx() ejecuta             │
       │                                │
       ├─► run_coroutine_threadsafe ───►│
       │                                │
       │  return redirect('/')          │  broadcast_transaction()
       │                                │  ejecuta aquí
       │                                │
       ▼                                ▼
   Usuario ve dashboard           TX se propaga por red
```

**¿Por qué `redirect('/')`?**

Pattern POST-Redirect-GET:

```
Sin redirect:
  POST /send_tx → responde HTML → Si usuario recarga (F5) → reenvía POST → TX duplicada

Con redirect:
  POST /send_tx → redirect → GET / → Si usuario recarga → solo recarga página
```

**Manejo de errores:**

```python
try:
    # ... crear y enviar TX
except Exception as e:
    return f"Error: {e}", 400
```

Captura cualquier error (address inválida, cantidad negativa, etc.) y lo muestra al usuario.

---

## Función `run`

```python
def run(self):
    self.app.run(
        host='0.0.0.0',
        port=self.dashboard_port,
        debug=False,
        use_reloader=False
    )
```

**¿Qué hace?**

Inicia el servidor Flask en el puerto configurado.

**Parámetros:**

| Parámetro | Valor | Por qué |
|-----------|-------|---------|
| `host` | `'0.0.0.0'` | Escucha en todas las interfaces de red |
| `port` | `self.dashboard_port` | Puerto específico del nodo (8000-8004) |
| `debug` | `False` | No mostrar errores detallados (producción) |
| `use_reloader` | `False` | No reiniciar al cambiar archivos |

**¿Por qué `host='0.0.0.0'`?**

Permite acceso desde cualquier IP:

```
host='localhost' → Solo http://localhost:8000
host='0.0.0.0'   → http://localhost:8000
                   http://192.168.1.100:8000
                   http://10.0.0.5:8000
```

Útil si quieres acceder desde otro dispositivo en la red.

**¿Por qué `use_reloader=False`?**

El reloader de Flask reinicia el servidor cuando detecta cambios en archivos. Esto causaría problemas:

```
Con reloader:
  Cambio en código → Flask reinicia → Nodo P2P pierde conexiones → red se rompe

Sin reloader:
  Cambio en código → Flask ignora → Nodo P2P sigue corriendo
```

**¿Por qué `debug=False`?**

En modo debug, Flask muestra stack traces completos al usuario. En producción:
- Revela estructura interna del código
- Confunde al usuario
- No es necesario

---

## Integración con `launcher_dashboard.py`

**Cómo se usa esta clase:**

```python
# En launcher_dashboard.py:

# 1. Crear nodo P2P
node = P2PNode(host='localhost', port=5000, bootstrap_peers=[])

# 2. Guardar loop para uso de Flask
node.loop = asyncio.get_event_loop()

# 3. Iniciar nodo en background
asyncio.create_task(node.start())

# 4. Crear dashboard
dashboard = NodeDashboard(node, 8000)

# 5. Iniciar dashboard en thread separado
threading.Thread(target=dashboard.run, daemon=True).start()
```

**Resultado:**

```
Nodo P2P (asyncio)     Dashboard Flask (thread)
      │                         │
      │  node.wallet ◄──────────┤ GET /api/wallet
      │                         │
      │  node.mempool ◄─────────┤ GET /api/mempool
      │                         │
      │  node.create_tx() ◄─────┤ POST /send_tx
      │                         │
      │  node.broadcast_tx() ◄──┤ (via run_coroutine_threadsafe)
```

---

## Flujo Completo de Usuario

```
1. Usuario abre http://localhost:8000
   └─ GET / → render_template('dashboard.html')
   └─ Navegador muestra página

2. JavaScript inicia (app.js)
   └─ updateData() cada 2 segundos
   └─ GET /api/info → actualiza balance, peers, mempool
   └─ GET /api/peers → actualiza lista de peers
   └─ GET /api/mempool → actualiza lista de TXs

3. Usuario completa formulario
   └─ Destinatario: 1BobAddress...
   └─ Cantidad: 10
   └─ Click "Enviar Transaccion"

4. Browser envía POST /send_tx
   └─ Flask recibe
   └─ Crea TX
   └─ Propaga vía asyncio.run_coroutine_threadsafe()
   └─ redirect('/')

5. Browser recarga página (GET /)
   └─ JavaScript reinicia auto-refresh
   └─ 2 segundos después → TX aparece en mempool
```

---

## Comparación con Otros Frameworks

### Flask vs Django

| Aspecto | Flask (usado aquí) | Django |
|---------|-------------------|---------|
| Complejidad | Simple | Complejo |
| Líneas de código | ~80 | ~300+ |
| Base de datos | No necesita | ORM obligatorio |
| Templates | Jinja2 | Django templates |
| Setup | Mínimo | settings.py extenso |

**Para este demo:** Flask es perfecto (simple y suficiente).

### Flask vs FastAPI

| Aspecto | Flask | FastAPI |
|---------|-------|---------|
| Async nativo | ❌ | ✅ |
| Necesita bridge | ✅ run_coroutine_threadsafe | ❌ |
| API docs auto | ❌ | ✅ |
| Popularidad | Mayor | Creciente |

**Por qué Flask:** Más familiar, suficiente para el demo.

---

## Troubleshooting

### Problema: "Address already in use"

**Causa:** Dashboard anterior no cerró

**Solución:**
```bash
# Linux/Mac:
lsof -ti:8000 | xargs kill -9

# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Problema: TX no se propaga

**Causa:** `node.loop` no existe

**Verificar en launcher:**
```python
node.loop = asyncio.get_event_loop()  # ← Debe estar antes de NodeDashboard
```

### Problema: Auto-refresh no funciona

**Causa:** JavaScript no carga

**Verificar:**
- Abrir DevTools (F12)
- Console tab
- ¿Hay error "Failed to fetch /api/info"?

### Problema: Formulario no envía TX

**Causa:** Error en POST handler

**Verificar logs de Flask:**
```
Terminal donde corre launcher_dashboard.py
→ Flask imprime errores aquí
```

---

## Extensiones Posibles

### Agregar autenticación:

```python
from flask_httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    return username == "admin" and password == "secret"

@self.app.route('/')
@auth.login_required
def index():
    # ...
```

### Agregar WebSockets para updates en tiempo real:

```python
from flask_socketio import SocketIO
socketio = SocketIO(self.app)

# En lugar de polling cada 2s, push updates
@socketio.on('connect')
def handle_connect():
    emit('update', {'balance': node.get_balance()})
```

### Agregar historial de TXs:

```python
@self.app.route('/api/history')
def api_history():
    # Guardar TXs confirmadas en lista separada
    return jsonify(self.node.tx_history)
```

---

*Documento: `DOC_dashboard_app.md` — Demo Blockchain Fase B (Backend del Dashboard)*
