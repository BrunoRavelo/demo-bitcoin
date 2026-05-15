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

---

## Modos de Ejecución

El programa tiene **seis variantes de ejecución**:

| Modo | Cuándo usar | Scripts |
|------|-------------|---------|
| **1 — Local Manual** | Demo interactivo, control total | `launcher_manual.py` |
| **1B — Local Manual + Dashboard Global** | Igual + vista de red en proyector | `main_seed.py` + `launcher_manual.py` + `main_global.py` |
| **2 — Local Auto** | Demo autónomo con TXs automáticas | `launcher_auto.py` |
| **2B — Local Auto + Dashboard Global** | Igual + vista de red en proyector | `launcher_auto.py` + `main_global.py` |
| **3 — LAN Completa** | Laboratorio con dashboard global y orquestador | `main_seed.py` + `main_global.py` + `main.py` |
| **3F — LAN sin dashboard global** | Laboratorio, cada alumno ve solo su nodo | `main_seed.py` + `main.py` |
| **3G — LAN sin orquestador** | Laboratorio con TXs solo manuales | `main_seed.py` + `main_global.py --no-orchestrator` + `main.py` |
| **3H — LAN sin dashboard en nodos** | Toda la visualización en el proyector del instructor | `main_seed.py` + `main_global.py` + `main.py --no-dashboard` |

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

## Modo 1B: Local Manual + Dashboard Global

### ¿Qué es?

Igual que el Modo 1, pero agrega una vista centralizada en `http://localhost:9000` que el instructor puede proyectar para mostrar el estado de toda la red mientras explica.

### Cuándo usarlo

Cuando se quiere explicar el flujo manual (minar → TX → confirmar) y a la vez mostrar en el proyector cómo se propaga la información entre nodos.

### Cómo arrancar (3 terminales)

> **Por qué 3 terminales:** `launcher_manual.py` no arranca seed (no lo necesita para conectar los nodos). El dashboard global sí necesita seed para descubrir los nodos. Hay que arrancarlo por separado.

**Terminal 1:**
```powershell
venv\Scripts\activate
python main_seed.py
```

**Terminal 2** (esperar ~2s):
```powershell
venv\Scripts\activate
python launcher_manual.py
```

**Terminal 3** (esperar ~3s):
```powershell
venv\Scripts\activate
python main_global.py --no-orchestrator
```

> **Por qué `--no-orchestrator`:** `main_global.py` crea un orquestador de TXs automáticas por defecto. Esto contradice el modo manual. El flag lo desactiva.

### Dashboards

```
http://localhost:9000       ← Dashboard global (proyector)
http://localhost:8000       ← Nodo 1
http://localhost:8001       ← Nodo 2
http://localhost:8002       ← Nodo 3
http://localhost:8003       ← Nodo 4
http://localhost:8004       ← Nodo 5
```

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

## Modo 2B: Local Auto + Dashboard Global

### ¿Qué es?

Igual que el Modo 2, pero agrega el dashboard global en `http://localhost:9000` para proyectar el estado completo de la red.

### Cuándo usarlo

Cuando se quiere mostrar minado competitivo, forks y TXs automáticas, y a la vez el instructor quiere proyectar una vista unificada de todos los nodos.

### Cómo arrancar (2 terminales)

**Terminal 1:**
```powershell
venv\Scripts\activate
python launcher_auto.py
```

**Terminal 2** (esperar ~3s):
```powershell
venv\Scripts\activate
python main_global.py --no-orchestrator
```

> **Por qué `--no-orchestrator`:** `launcher_auto.py` ya incluye su propio orquestador de TXs. Si `main_global.py` crea otro, se duplican las TXs automáticas.

### Dashboards

```
http://localhost:9000       ← Dashboard global (proyector)
http://localhost:8000       ← Nodo 1
http://localhost:8001       ← Nodo 2
http://localhost:8002       ← Nodo 3
http://localhost:8003       ← Nodo 4
http://localhost:8004       ← Nodo 5
```

---

## Modo 3: LAN (Laboratorio)

### ¿Qué es?

Cada alumno corre un nodo en su computadora del laboratorio. El instructor corre el seed node y el dashboard global desde su máquina.

---

### Setup Automático (Recomendado) — Sin Python ni venv

Los scripts en `setup/` hacen todo el trabajo: instalan Python, descargan el proyecto, crean el entorno virtual e instalan dependencias. Solo necesitas PowerShell (incluido en Windows).

#### INSTRUCTOR — `setup/setup_instructor.ps1`

**Paso 1** — Abre PowerShell (búscalo en el menú Inicio).

**Paso 2** — Copia todo el contenido de `setup/setup_instructor.ps1` y pégalo en PowerShell. Presiona Enter.

El script hace automáticamente:
1. Instala Python desde la Microsoft Store
2. Descarga el proyecto desde GitHub al Escritorio (`demo-bitcoin-main`)
3. Crea el entorno virtual e instala todas las dependencias
4. Detecta tu IP de red automáticamente

Al terminar verás:
```
=== Listo ===
IP del instructor: 192.168.1.1
Comparte esta IP con los alumnos.

Arrancar seed node y dashboard global ahora? (s/n)
```

Escribe `s` y presiona Enter para arrancar el seed node y el dashboard global en ventanas separadas. Comunica la IP a todos los alumnos.

---

#### ALUMNO — `setup/setup_alumno.ps1`

**Paso 1** — Abre el archivo `setup/setup_alumno.ps1` con el Bloc de notas o cualquier editor.

**Paso 2** — Cambia la IP del instructor en la primera línea de parámetros:

```powershell
[string]$SeedHost = "192.168.1.100",   # ← Reemplaza con la IP que dio el instructor
```

Por ejemplo, si el instructor dio `192.168.1.1`:

```powershell
[string]$SeedHost = "192.168.1.1",
```

Guarda el archivo.

**Paso 3** — Abre PowerShell.

**Paso 4** — Copia todo el contenido del archivo modificado y pégalo en PowerShell. Presiona Enter.

El script hace automáticamente:
1. Instala Python desde la Microsoft Store
2. Descarga el proyecto desde GitHub al Escritorio
3. Crea el entorno virtual e instala todas las dependencias
4. Detecta tu IP de red automáticamente

Al terminar verás:
```
=== Listo ===
Mi IP:      192.168.1.5
Dashboard:  http://192.168.1.5:8000
Instructor: 192.168.1.1:8888

Arrancar ahora? (s/n)
```

Escribe `s` y presiona Enter. Tu nodo arranca y el dashboard queda en `http://localhost:8000`.

> **Nota:** Si ya se instaló Python en una sesión anterior, la instalación via winget se salta automáticamente y el script continúa con los pasos siguientes.

---

### Verificar conexión (alumno)

En tu dashboard (`http://localhost:8000`):
- La sección **Red P2P** debe mostrar peers conectados
- La **Blockchain** debe mostrar la misma altura que otros nodos

Desde otra computadora de la red también puedes acceder a:
```
http://192.168.1.5:8000
```

---

### Alternativa: Setup Manual (sin scripts)

Si los scripts automáticos no funcionan por restricciones del laboratorio, sigue estos pasos manuales.

#### INSTRUCTOR

Encontrar la IP de red:
```powershell
ipconfig
# Buscar "Dirección IPv4" en el adaptador de red LAN
# Ejemplo: 192.168.1.1
```

```powershell
# Terminal 1 — Seed node
venv\Scripts\activate
python main_seed.py

# Terminal 2 — Dashboard global
venv\Scripts\activate
python main_global.py --seed-host 192.168.1.1
```

Verificar que el seed funciona:
```
http://192.168.1.1:8888/health
→ {"status": "ok", "peers_count": 0, ...}
```

#### ALUMNO

```powershell
# Encontrar tu IP
ipconfig
# Ejemplo: 192.168.1.5

# Arrancar tu nodo
venv\Scripts\activate
python main.py --host 192.168.1.5 --seed-host 192.168.1.1
```

---

### Variantes LAN

#### Modo 3 — LAN Completa (Recomendado)

Seed + nodos + dashboard global + orquestador de TXs automáticas. Configuración estándar para laboratorio con 30 máquinas.

**Orden obligatorio de inicio:**
```
1. main_seed.py          (instructor — primero siempre)
2. main_global.py        (instructor — segunda ventana)
3. main.py --host X  ×N  (alumnos — cualquier orden entre ellos)
```

```powershell
# Instructor — Terminal 1
python main_seed.py

# Instructor — Terminal 2
python main_global.py --seed-host 192.168.1.1

# Cada alumno
python main.py --host 192.168.1.Y
```

Dashboard instructor: `http://192.168.1.1:9000`
Dashboard alumno: `http://192.168.1.Y:8000`

---

#### Modo 3F — LAN sin Dashboard Global

Solo seed + nodos. Cada alumno ve únicamente su propio nodo. Útil si no se necesita vista centralizada.

```powershell
# Instructor
python main_seed.py

# Cada alumno
python main.py --host 192.168.1.Y
```

---

#### Modo 3G — LAN sin Orquestador

Seed + nodos + dashboard global, pero **sin TXs automáticas**. Las transacciones solo ocurren cuando los alumnos las envían manualmente.

```powershell
# Instructor — Terminal 1
python main_seed.py

# Instructor — Terminal 2
python main_global.py --no-orchestrator --seed-host 192.168.1.1

# Cada alumno
python main.py --host 192.168.1.Y
```

---

#### Modo 3H — LAN sin Dashboard en los Nodos

Seed + nodos (sin UI local) + dashboard global. Reduce la carga en las máquinas alumno. Toda la visualización queda en el proyector del instructor.

```powershell
# Instructor — Terminal 1
python main_seed.py

# Instructor — Terminal 2
python main_global.py --seed-host 192.168.1.1

# Cada alumno — el nodo mina y participa, pero sin Flask local
python main.py --host 192.168.1.Y --no-dashboard
```

> **Nota:** Con `--no-dashboard` el nodo sigue minando y propagando bloques normalmente — solo no tiene interfaz web propia.

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

Todos los parámetros están en `config.py`.

### Ajustar la Dificultad de Minado

El tiempo de minado depende del hardware. Ajusta `INITIAL_TARGET` antes de arrancar:

| Tiempo objetivo | Valor de `INITIAL_TARGET` | Recomendado para |
|---|---|---|
| ~10 segundos | `MAX_TARGET // 500_000` | Demo rápido, clase activa |
| ~30 segundos | `MAX_TARGET // 1_500_000` | **Demo en clase (recomendado)** |
| ~60 segundos | `MAX_TARGET // 3_000_000` | Demo pausado con explicación |
| ~180 segundos | `MAX_TARGET // 9_000_000` | Simulación realista |

> **Consejo:** arranca con `MAX_TARGET // 500_000`. El dashboard muestra los h/s reales del minero — con ese dato puedes calcular el target exacto para el tiempo que quieres. El ajuste automático de dificultad corrige cada 5 bloques.

### Referencia Completa de Parámetros

| Variable | Default | Descripción |
|---|---|---|
| `SEED_HOST` | `'localhost'` | IP del seed. **Cambiar a IP del instructor en LAN** |
| `SEED_PORT` | `8888` | Puerto del seed node |
| `INITIAL_TARGET` | `MAX_TARGET // 1_500_000` | Dificultad inicial (~30s/bloque) |
| `TARGET_BLOCK_TIME` | `180` | Tiempo objetivo del ajuste automático (segundos) |
| `DIFFICULTY_ADJUSTMENT_INTERVAL` | `5` | Ajuste automático cada N bloques |
| `BLOCK_REWARD` | `50` | Coins por bloque minado |
| `TX_AUTO_BASE_INTERVAL` | `15` | Segundos entre TXs del orquestador |
| `TX_AUTO_JITTER` | `10` | Variación aleatoria del intervalo |
| `TX_AUTO_MAX_FRACTION` | `0.2` | Máximo 20% del balance por TX automática |
| `MAX_TXS_PER_BLOCK` | `10` | TXs máximas incluidas por bloque |
| `MINING_AUTO_START` | `True` | Modo de minado al arrancar con `main.py` (LAN). No afecta a launchers. |

---


## Combinaciones no Factibles

Errores comunes al intentar combinar modos:

| Combinación | Por qué no funciona | Solución |
|---|---|---|
| **Local Manual + Dashboard Global sin seed explícito** | `launcher_manual.py` no arranca seed. El dashboard global ve la red vacía. | Usar Modo 1B: arrancar `main_seed.py` primero en Terminal 1. |
| **Local Auto sin seed** | Imposible: `launcher_auto.py` requiere seed para el orquestador. | El seed ya está integrado en `launcher_auto.py` — no hace falta arrancarlo aparte. |
| **LAN sin seed** | Sin punto de rendezvous, las máquinas no pueden descubrirse entre sí. | Siempre arrancar `main_seed.py` en la máquina del instructor primero. |
| **Orquestador sin seed** | El orquestador obtiene las wallets desde `/addresses` del seed. Sin seed no tiene a quién enviarle TXs. | Arrancar seed antes que el orquestador. |
| **Dashboard global sin seed** | Depende del seed para descubrir nodos. Sin seed retorna lista vacía. | Arrancar seed antes que `main_global.py`. |
| **Dos instancias del mismo launcher simultáneamente** | Conflicto de puertos (5000–5004, 8000–8004, 8888). La segunda falla con `Address already in use`. | Terminar la primera instancia antes de arrancar otra. |
| **`main_global.py` sin `--no-orchestrator` junto a `launcher_auto.py`** | Se crean dos orquestadores: uno en el launcher y otro en el global. Las TXs automáticas se duplican. | Usar `python main_global.py --no-orchestrator` en Modo 2B. |

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
├── setup/              ← Scripts de setup automático para LAN
│   ├── setup_instructor.ps1  ← Instala todo y arranca seed + dashboard global
│   └── setup_alumno.ps1      ← Instala todo y arranca el nodo del alumno
├── documentacion/      ← Documentación del proyecto
│   └── MANUAL_USUARIO.md
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
