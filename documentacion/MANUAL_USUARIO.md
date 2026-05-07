# Manual de Usuario — Blockchain Demo

## ¿Qué es este programa?

Este proyecto es una **simulación funcional de una red blockchain** estilo Bitcoin. Permite observar y experimentar con los conceptos fundamentales de blockchain en tiempo real: minado con Proof of Work, transacciones firmadas digitalmente, propagación P2P, consenso entre nodos y detección de forks.

La red puede correrse de dos formas:
- **Local:** múltiples nodos simulados en una sola computadora
- **LAN:** cada alumno corre un nodo en su propia máquina del laboratorio

---

## Requisitos Previos

### Software

- Python 3.10 o superior
- Google Chrome, Firefox, o cualquier navegador moderno

### Verificar Python

```powershell
python --version
# Debe mostrar: Python 3.10.x o superior
```

### Instalación (primera vez)

```powershell
# 1. Crear entorno virtual
python -m venv venv

# 2. Activar entorno virtual
venv\Scripts\activate          # Windows PowerShell
# source venv/bin/activate     # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt
```

Verificar instalación correcta:

```powershell
python -c "import websockets, flask, cryptography; print('OK')"
# Debe imprimir: OK
```

---

## Modos de Ejecución

El programa tiene **tres modos principales**:

| Modo | Cuándo usar | Script |
|------|-------------|--------|
| **Local Manual** | Demo interactivo — el usuario controla todo | `launcher_manual.py` |
| **Local Auto** | Demo autónomo — la red funciona sola | `launcher_auto.py` |
| **LAN** | Laboratorio — cada alumno en su máquina | `main.py` + `main_seed.py` |

---

## Modo 1: Local Manual

### ¿Qué es?

5 nodos P2P en tu computadora. Nada ocurre automáticamente — tú decides cuándo minar y cuándo enviar transacciones. Ideal para entender paso a paso cómo funciona la blockchain.

### Cómo arrancar

```powershell
# Activar entorno virtual (si no está activo)
venv\Scripts\activate

# Arrancar demo con 5 nodos
python launcher_manual.py

# O con menos nodos (más rápido para demos cortos)
python launcher_manual.py --nodes 3
```

### Qué verás en la terminal

```
╔══════════════════════════════════════════════════════════════════════╗
║           BLOCKCHAIN DEMO — Launcher Manual                          ║
╚══════════════════════════════════════════════════════════════════════╝

  Modo:       MANUAL
  Nodos:      5
  Balance inicial: 0 coins (mina tu primer bloque para obtener 50 coins)

  [1/5] Nodo 1 (P2P:5000 Dashboard:8000)...
  [2/5] Nodo 2 (P2P:5001 Dashboard:8001)...
  ...

  Todos los nodos listos. Abre en tu navegador:

    Nodo 1: http://localhost:8000
    Nodo 2: http://localhost:8001
    Nodo 3: http://localhost:8002
    Nodo 4: http://localhost:8003
    Nodo 5: http://localhost:8004
```

### Cómo usar el dashboard individual

Abre `http://localhost:8000` en tu navegador. Verás:

```
┌─────────────────────────────────────────────────────┐
│  node_5000  │  P2P: 5000  │  Dashboard: 8000        │
│  Altura: 1  │  Modo: MANUAL                         │
├──────────────────────────────────────────────────────┤
│  Mi Wallet                                           │
│  Address: 1A2B3CXyz...  [Copiar]                    │
│  Balance: 0.00 coins                                 │
├──────────────────────────────────────────────────────┤
│  Enviar Transacción                                  │
│  Destinatario: ________________                      │
│  Cantidad:     ________________                      │
│  [Enviar Transacción]                                │
├──────────────────────────────────────────────────────┤
│  Minero                                              │
│  Bloques minados: 0  │  Recompensas: 0.00           │
│  [⛏ Minar un bloque ahora]                          │
├──────────────────────────────────────────────────────┤
│  Blockchain  │  Altura: 1  │  Último: 00000000...   │
│  [Génesis]                                           │
├──────────────────────────────────────────────────────┤
│  Red P2P  │  Peers: 4                               │
│  ● localhost:5001  ● localhost:5002  ...             │
├──────────────────────────────────────────────────────┤
│  Mempool  │  TXs pendientes: 0                      │
└─────────────────────────────────────────────────────┘
```

### Demo Paso a Paso

**Paso 1 — Minar tu primer bloque:**

1. En `http://localhost:8000`, haz clic en **"Minar un bloque ahora"**
2. Espera ~30 segundos (el PoW prueba miles de nonces)
3. Al completarse:
   - Tu balance sube a **50 coins** (recompensa)
   - La blockchain muestra un nuevo bloque `#1`
   - Los 5 nodos sincronizan el bloque automáticamente

**Paso 2 — Crear una transacción:**

1. Abre `http://localhost:8001` en otra pestaña
2. Copia la **address** del Nodo 2 (clic en el botón "Copiar")
3. Vuelve a `http://localhost:8000`
4. Pega la address en "Destinatario"
5. Escribe `10` en "Cantidad"
6. Haz clic en **"Enviar Transacción"**
7. La TX aparece en el **Mempool** de ambos nodos

**Paso 3 — Confirmar la transacción:**

1. Haz clic en **"Minar un bloque ahora"** (o desde cualquier otro nodo)
2. La TX se incluye en el bloque y se confirma
3. Los balances se actualizan:
   - Nodo 1: 90 coins (envió 10, recibió 50 de recompensa)
   - Nodo 2: 10 coins (recibió la TX)

**Paso 4 — Ver detalles de un bloque:**

1. En la sección "Blockchain", haz clic en cualquier bloque (ej. `#1`)
2. Aparece un popup con:
   - Hash del bloque
   - Nonce encontrado
   - Lista de transacciones (coinbase + TXs)

---

## Modo 2: Local Auto

### ¿Qué es?

5 nodos que minan y generan transacciones automáticamente. El usuario puede observar el funcionamiento o intervenir cambiando modos desde el dashboard. Ideal para demostrar el comportamiento de la red sin intervención manual.

### Cómo arrancar

```powershell
python launcher_auto.py

# O con 3 nodos
python launcher_auto.py --nodes 3
```

### Flujo automático

```
T=0s    → Nodos arrancan (modo MANUAL)
T=4s    → Nodos conectados entre sí y registrados en seed
T=30s   → Orquestador empieza TXs automáticas
T=~30s  → Primer bloque minado (si activas AUTO en un nodo)
T=~45s  → Primer TX automática enviada (cuando hay balance)
```

### Activar minado automático

Desde cualquier dashboard (`http://localhost:8000`), en la sección **Minero**:
- Clic **"AUTO"** → el nodo empieza a minar continuamente
- Clic **"MANUAL"** → el nodo deja de minar automáticamente
- Clic **"Minar ahora"** → mina exactamente un bloque

### Activar/pausar TXs automáticas

En la sección **Enviar Transacción**:
- Clic **"AUTO"** → el orquestador genera TXs automáticamente para TODA la red
- Clic **"MANUAL"** → el orquestador se pausa (TXs solo manuales)

> **Nota:** Los controles de TXs afectan a todos los nodos. Si pausa las TXs en el Nodo 1, se pausan para todos.

---

## Modo 3: LAN (Laboratorio)

### ¿Qué es?

Cada alumno corre un nodo en su computadora del laboratorio. El instructor corre el seed node y el dashboard global desde su máquina.

### Instrucciones para el INSTRUCTOR

#### Paso 1: Configurar la IP en `config.py`

Encontrar la IP de red del instructor:
```powershell
ipconfig
# Buscar "Dirección IPv4" en la adaptador de red LAN
# Ejemplo: 192.168.1.1
```

Modificar `config.py`:
```python
SEED_HOST = '192.168.1.1'  # IP del instructor
```

#### Paso 2: Arrancar el Seed Node

```powershell
# Terminal 1
python main_seed.py
```

Verificar que funciona:
```
http://192.168.1.1:8888/health
→ {"status": "ok", "peers_count": 0, ...}
```

#### Paso 3: Arrancar el Dashboard Global

```powershell
# Terminal 2
python main_global.py --seed-host 192.168.1.1
```

El dashboard global del instructor estará en:
```
http://localhost:9000
```

#### Paso 4: Dar instrucciones a los alumnos

Comunicar a todos la IP del instructor: `192.168.1.1`

---

### Instrucciones para el ALUMNO

#### Paso 1: Configurar la IP del seed

Opción A — Modificar `config.py`:
```python
SEED_HOST = '192.168.1.1'  # IP del instructor (la que dé el profesor)
```

Opción B — Variable de entorno (sin modificar código):
```powershell
$env:SEED_HOST = "192.168.1.1"
```

#### Paso 2: Encontrar tu propia IP

```powershell
ipconfig
# Ejemplo: 192.168.1.5
```

#### Paso 3: Arrancar tu nodo

```powershell
python main.py --host 192.168.1.5 --seed-host 192.168.1.1
```

Tu dashboard estará en:
```
http://localhost:8000
```

O desde otra computadora de la red:
```
http://192.168.1.5:8000
```

#### Paso 4: Verificar conexión

En tu dashboard:
- La sección **Red P2P** debe mostrar peers conectados
- La **Blockchain** debe mostrar la misma altura que otros nodos

---

## Dashboard Individual — Referencia Completa

### Secciones

| Sección | Qué muestra | Frecuencia de actualización |
|---------|-------------|----------------------------|
| **Header** | Node ID, puertos, altura, modo | 2 segundos |
| **Wallet** | Address y balance actual | 2 segundos |
| **Enviar TX** | Formulario de transacción | — |
| **Minero** | Stats y controles de minado | 2 segundos |
| **Blockchain** | Últimos 5 bloques | 2 segundos |
| **Red P2P** | Peers conectados | 2 segundos |
| **Mempool** | TXs pendientes | 2 segundos |

### Operaciones Disponibles

#### Enviar una Transacción

1. Ingresar la **address** del destinatario (formato: `1A2B3CXyz...`)
2. Ingresar la **cantidad** en coins (número positivo, máximo = balance)
3. Clic **"Enviar Transacción"**
4. La TX aparece en el Mempool hasta que se mine un bloque

> Si el destinatario no está en el dropdown, escribir la address manualmente.

#### Minar un Bloque

- **"Minar ahora"** → mina un solo bloque (disponible en ambos modos)
- **Botón "AUTO"** (solo en modo auto) → minado continuo

Al minar un bloque:
- Recibes **50 coins** de recompensa (coinbase TX)
- Las TXs del mempool se confirman
- El bloque se propaga a todos los peers automáticamente

#### Ver Detalle de un Bloque

- Hacer clic en cualquier bloque de la lista `[#40][#39]...`
- Muestra: hash, nonce, difficulty, timestamp y lista de TXs

#### Copiar tu Address

- Clic en el botón **"Copiar"** junto a tu address
- La address queda en el portapapeles para compartirla

---

## Dashboard Global (Instructor)

Disponible en `http://localhost:9000` (o `http://192.168.1.1:9000` desde la LAN).

### Qué muestra

```
┌──────────────── Resumen de la red ──────────────────┐
│ Total: 30  │ Online: 28  │ Offline: 2  │ Altura: 45 │
│ Desfasados: 1  │ Mempool total: 8  │ AUTO: 20       │
├──────────────────────────────────────────────────────┤
│ Control TXs Automáticas                              │
│ Modo: AUTO  │ TXs enviadas: 142  │ Tasa: 97.8%      │
│ [Activar AUTO]  [Pausar (MANUAL)]                    │
├──────────────────────────────────────────────────────┤
│ Nodo         │ Altura │ Sync │ Balance │ Peers │ ...  │
│ node_5000    │  45    │ ✅   │ 450.00  │  4    │ ...  │
│ node_5001    │  43    │ ⚠️   │ 200.00  │  3    │ ...  │
│ node_5002    │  45    │ ✅   │ 300.50  │  4    │ ...  │
│ (offline)    │  --    │ ⬛   │  ---    │ ---   │ ...  │
└──────────────────────────────────────────────────────┘
```

### Iconos de Sincronización

| Icono | Significado |
|-------|-------------|
| ✅ | Sincronizado (lag ≤ 2 bloques) |
| ⚠️ | Ligeramente desfasado (lag 3-5 bloques) |
| 🔴 | Muy desfasado (lag > 5 bloques) |
| ⬛ | Offline (no responde) |

### Control del Orquestador

Desde el dashboard global, el instructor puede:
- **Activar TXs automáticas** para toda la red
- **Pausar TXs automáticas** (demo explicativo sin distracciones)
- Ver estadísticas de TXs generadas y tasa de éxito

---

## Configuración Avanzada

### Ajustar la Dificultad de Minado

Editar `config.py`:

```python
# Más fácil (bloques en ~10 segundos)
INITIAL_TARGET = MAX_TARGET // 500_000

# Más difícil (bloques en ~5 minutos)
INITIAL_TARGET = MAX_TARGET // 15_000_000

# Tiempo objetivo por bloque
TARGET_BLOCK_TIME = 60   # 1 minuto
TARGET_BLOCK_TIME = 180  # 3 minutos (default)
```

### Ajustar TXs Automáticas

```python
# Más frecuentes (cada 5-8 segundos)
TX_AUTO_BASE_INTERVAL = 5
TX_AUTO_JITTER = 3

# Menos frecuentes (cada 30-45 segundos)
TX_AUTO_BASE_INTERVAL = 30
TX_AUTO_JITTER = 15
```

### Número de TXs por Bloque

```python
MAX_TXS_PER_BLOCK = 10   # default
MAX_TXS_PER_BLOCK = 5    # bloques más pequeños
MAX_TXS_PER_BLOCK = 20   # bloques más grandes
```

---

## Solución de Problemas

### "Address already in use"

```
Error: [Errno 98] Address already in use
```

**Causa:** Puerto ocupado por una ejecución anterior no terminada.

**Solución:**
```powershell
# Buscar proceso en el puerto
netstat -ano | findstr :8000
netstat -ano | findstr :5000

# Terminar el proceso (reemplazar PID con el número encontrado)
taskkill /PID <PID> /F
```

O simplemente cerrar la terminal anterior y esperar 30 segundos.

---

### Dashboard no carga

**Síntoma:** El navegador muestra "No se puede acceder a este sitio"

**Verificar:**

1. Que el launcher sigue corriendo en la terminal
2. Que el puerto es correcto (8000 para Nodo 1, 8001 para Nodo 2, etc.)
3. Que Flask arrancó correctamente:

```powershell
# Debe aparecer en la terminal del launcher:
* Running on http://127.0.0.1:8000
```

---

### Los peers no se conectan

**Síntoma:** Dashboard muestra "Peers: 0" después de 10+ segundos

**Verificar:**

1. Que todos los nodos están corriendo (ver terminal del launcher)
2. Que los puertos 5000-5004 no están bloqueados por el firewall
3. En modo LAN: que el seed está activo y la IP está configurada correctamente:

```
http://192.168.1.1:8888/health
→ {"status": "ok", ...}
```

---

### El balance no actualiza

**Síntoma:** Envié una TX pero el balance no cambia

**Causa:** Las TXs en el **mempool** no están confirmadas — necesitan ser incluidas en un bloque.

**Solución:** Minar un bloque (en cualquier nodo). Al minar, la TX se confirma y los balances se actualizan.

---

### Nodo desfasado en el dashboard global

**Síntoma:** Un nodo muestra ⚠️ o 🔴 en el dashboard global

**Causa:** El nodo tiene una versión más antigua de la blockchain que los demás.

**Qué ocurre automáticamente:** El protocolo P2P detecta el desfase y solicita la cadena completa al peer con mayor altura. En ~30 segundos el nodo debería sincronizarse solo.

**Si persiste:** El nodo puede estar desconectado. Verificar que el dashboard individual de ese nodo responde.

---

### Error al instalar dependencias

```
ERROR: Could not find a version that satisfies the requirement...
```

**Solución:**

```powershell
# Actualizar pip primero
python -m pip install --upgrade pip

# Reinstalar dependencias
pip install -r requirements.txt
```

---

## Conceptos Clave

### Wallet y Dirección

Cada nodo tiene una **wallet** única con un par de llaves criptográficas:
- **Llave privada:** Secreta. Se usa para firmar transacciones. Nunca se comparte.
- **Llave pública:** Pública. Se usa para verificar firmas.
- **Address:** Versión compacta de la llave pública en formato `1A2B3C...`. Es lo que compartes para recibir coins.

> Analogía: La address es como tu número de cuenta bancaria — cualquiera puede enviarte dinero, pero solo tú puedes autorizar transferencias.

### Transacción

Una transacción registra la transferencia de coins de una address a otra. Para ser válida, debe estar **firmada digitalmente** por el remitente con su llave privada.

Tipos:
- **TX normal:** `Alice → Bob: 10 coins` (requiere firma de Alice)
- **TX coinbase:** `COINBASE → Minero: 50 coins` (sin firma — crea coins nuevos)

### Mempool

El "pool de memoria" donde esperan las transacciones antes de ser confirmadas. Las TXs en el mempool son visibles en la red pero aún no están en la blockchain.

### Minado (Proof of Work)

El proceso de encontrar un número especial (**nonce**) tal que el hash del bloque empiece con suficientes ceros. Es computacionalmente difícil (miles de intentos) pero fácil de verificar (un solo cálculo).

```
Bloque = {prev_hash, transacciones, nonce}
hash(Bloque) debe empezar con "0000..." para ser válido
```

El minero que encuentra el nonce primero propaga el bloque a la red y recibe la **recompensa de bloque** (50 coins).

### Blockchain

La cadena de bloques — cada bloque contiene el hash del bloque anterior, formando una cadena inmutable. Para modificar un bloque antiguo, habría que recalcular todos los bloques posteriores — algo computacionalmente inviable.

### Regla de la Cadena Más Larga

Cuando dos nodos tienen versiones diferentes de la blockchain (**fork**), la red adopta la cadena más larga (con más trabajo acumulado). Esto garantiza que todos los nodos lleguen al mismo estado eventualmente.

---

## Referencia de Puertos

| Puerto | Servicio | Script |
|--------|---------|--------|
| 5000-5004 | P2P WebSocket (nodos 0-4) | `launcher_manual.py` / `launcher_auto.py` |
| 8000-8004 | Dashboard Flask (nodos 0-4) | `launcher_manual.py` / `launcher_auto.py` |
| 8888 | Seed node HTTP | `launcher_auto.py` / `main_seed.py` |
| 9000 | Dashboard Global | `main_global.py` |
| 5000 | P2P WebSocket (LAN, 1 nodo) | `main.py` |
| 8000 | Dashboard Flask (LAN, 1 nodo) | `main.py` |

---

## Ejecutar los Tests

```powershell
# Activar entorno virtual
venv\Scripts\activate

# Todos los tests
pytest

# Tests específicos
pytest tests/test_wallet.py
pytest tests/test_blockchain.py

# Con cobertura
pytest --cov=core --cov=network

# Verbose (ver nombre de cada test)
pytest -v
```

---

## Estructura del Proyecto

```
blockchain-demo/
├── core/               ← Lógica de blockchain
│   ├── wallet.py       ← Identidad criptográfica (Ed25519)
│   ├── transaction.py  ← Transacciones firmadas
│   ├── block.py        ← Estructura del bloque
│   ├── blockchain.py   ← Cadena, mempool, consenso
│   ├── merkle.py       ← Árbol de Merkle
│   ├── pow.py          ← Proof of Work
│   └── tx_orchestrator.py ← Bot generador de TXs
├── network/            ← Red P2P
│   ├── p2p_node.py     ← Nodo completo
│   ├── protocol.py     ← Mensajes WebSocket
│   ├── seed_node.py    ← Servidor de descubrimiento
│   └── seed_client.py  ← Cliente del seed
├── dashboard/          ← UI por nodo
│   ├── app.py          ← Backend Flask
│   └── templates/      ← HTML + JS + CSS
├── dashboard_global/   ← UI del instructor
│   ├── app.py          ← Backend Flask
│   └── templates/      ← HTML + JS + CSS
├── tests/              ← Suite pytest (38 archivos)
├── utils/logger.py     ← Logging por nodo
├── config.py           ← Configuración central
├── main.py             ← Entry point LAN (1 nodo)
├── main_seed.py        ← Entry point seed
├── main_global.py      ← Entry point dashboard global
├── launcher_manual.py  ← Demo local manual
└── launcher_auto.py    ← Demo local automático
```

---

*Manual de Usuario — Demo Blockchain v0.3.0*
