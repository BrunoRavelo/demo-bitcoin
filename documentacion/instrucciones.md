# Blockchain Demo — Instrucciones de Ejecución

## Índice

1. [Requisitos previos](#1-requisitos-previos)
2. [Ajustar dificultad antes de arrancar](#2-ajustar-dificultad-antes-de-arrancar)
3. [Modo LOCAL](#3-modo-local)
   - [A. Local Manual](#3a-local-manual)
   - [B. Local Manual + Dashboard Global](#3b-local-manual--dashboard-global)
   - [C. Local Auto](#3c-local-auto)
   - [D. Local Auto + Dashboard Global](#3d-local-auto--dashboard-global)
4. [Modo LAN](#4-modo-lan)
   - [E. LAN estándar](#4e-lan-estándar)
   - [F. LAN sin dashboard global](#4f-lan-sin-dashboard-global)
   - [G. LAN sin orquestador](#4g-lan-sin-orquestador)
   - [H. LAN sin dashboard en los nodos](#4h-lan-sin-dashboard-en-los-nodos)
5. [Combinaciones no factibles](#5-combinaciones-no-factibles)
6. [Referencia de puertos](#6-referencia-de-puertos)
7. [Referencia de parámetros ajustables](#7-referencia-de-parámetros-ajustables)

---

## 1. Requisitos previos

### Instalación manual (una vez por máquina)

```bash
cd blockchain-demo
python -m venv venv

# Activar (Windows)
.\venv\Scripts\activate

# Activar (Linux/Mac)
source venv/bin/activate

pip install -r requirements.txt
```

### Instalación automática en LAN (Windows)

```powershell
# Máquina del instructor — ejecutar primero
powershell -ExecutionPolicy Bypass -File setup_instructor.ps1

# Cada máquina alumno (reemplazar con la IP que mostró el script del instructor)
powershell -ExecutionPolicy Bypass -File setup_alumno.ps1 -SeedHost 192.168.1.X
```

---

## 2. Ajustar dificultad antes de arrancar

**Archivo:** `config.py` — variable `INITIAL_TARGET`

El tiempo de minado depende del hardware. Fórmula:

```
INITIAL_TARGET = MAX_TARGET // (hashrate_h_s × segundos_objetivo)
```

| Tiempo objetivo | Valor de INITIAL_TARGET | Recomendado para |
|---|---|---|
| ~10 segundos | `MAX_TARGET // 500_000` | Demo rápido, clase activa |
| ~30 segundos | `MAX_TARGET // 1_500_000` | **Demo en clase (recomendado)** |
| ~60 segundos | `MAX_TARGET // 3_000_000` | Demo pausado con explicación |
| ~180 segundos | `MAX_TARGET // 9_000_000` | Simulación realista |

> **Consejo:** arranca con `MAX_TARGET // 500_000`. El dashboard muestra los h/s
> reales del minero — con ese dato puedes calcular el target exacto para el tiempo
> que quieres. El ajuste automático de dificultad corrige cada 5 bloques.

---

## 3. Modo LOCAL

Todo corre en **una sola máquina**. Múltiples nodos en puertos distintos.
El seed, cuando existe, también corre en la misma máquina.

> **Por qué launcher_auto tiene seed integrado y launcher_manual no:**
> `launcher_auto.py` necesita un seed para que el orquestador de TXs descubra
> las wallet addresses de todos los nodos. `launcher_manual.py` no tiene
> orquestador, no necesita seed — los nodos se conectan directamente por puertos
> bootstrap hardcodeados en el launcher.
>
> **Impacto en el dashboard global:** necesita un seed corriendo para descubrir
> nodos. En combinaciones con `launcher_manual.py` hay que arrancar un seed
> explícitamente si se quiere dashboard global.

---

### 3A. Local Manual

**Qué incluye:** 5 nodos en modo MANUAL, conexión directa entre nodos (sin seed),
sin orquestador, sin dashboard global.

**Cuándo usarlo:** explicar el flujo básico — minar → recibir coins → enviar TX → confirmar TX.

```bash
python launcher_manual.py
```

**Defaults:**
- Nodos: 5 (P2P 5000–5004, dashboards 8000–8004)
- Modo minado: MANUAL en todos
- Sin seed, sin orquestador, sin dashboard global

```bash
python launcher_manual.py --nodes 3
# → 3 nodos: P2P 5000–5002, dashboards 8000–8002
```

Dashboards:
```
http://localhost:8000  ← Nodo 1
http://localhost:8001  ← Nodo 2
http://localhost:8002  ← Nodo 3
http://localhost:8003  ← Nodo 4
http://localhost:8004  ← Nodo 5
```

Flujo sugerido:
1. Nodo 1 → **Minar un bloque ahora** → obtiene 50 coins
2. Copiar address del Nodo 2 desde su dashboard
3. Nodo 1 → pegar address en "Destinatario" → enviar TX
4. Nodo 1 → **Minar un bloque ahora** → TX confirmada
5. Verificar que el balance del Nodo 2 aumentó

---

### 3B. Local Manual + Dashboard Global

**Qué incluye:** igual que 3A más seed separado y dashboard global del instructor.
Requiere **tres terminales**.

**Cuándo usarlo:** mostrar en proyector el estado de la red mientras se explica el
flujo manual.

> **Por qué `--no-orchestrator`:** `main_global.py` crea un orquestador por
> defecto que envía TXs automáticas a los 30s — contradice el modo manual.
>
> **Por qué `main_seed.py` por separado:** `launcher_manual.py` no arranca seed.
> Sin seed, el dashboard global ve la red vacía.

**Terminal 1:**
```bash
python main_seed.py
# Default: 0.0.0.0:8888
```

**Terminal 2** (esperar ~2s):
```bash
python launcher_manual.py
# Default: 5 nodos, se registran automáticamente con el seed en localhost:8888
```

**Terminal 3** (esperar ~3s):
```bash
python main_global.py --no-orchestrator
# Default: seed en localhost:8888, dashboard en puerto 9000
```

Dashboards:
```
http://localhost:9000  ← Dashboard global (proyector)
http://localhost:8000  ← Nodo 1  ...  http://localhost:8004 ← Nodo 5
```

---

### 3C. Local Auto

**Qué incluye:** 5 nodos, seed integrado, orquestador de TXs. Los nodos arrancan
en modo **MANUAL** — el usuario activa AUTO desde cada dashboard cuando esté listo.
El orquestador inicia TXs automáticas ~30s después del arranque.

**Cuándo usarlo:** demostrar minado competitivo, forks, TXs automáticas.

```bash
python launcher_auto.py
```

**Defaults:**
- Nodos: 5 (P2P 5000–5004, dashboards 8000–8004)
- Modo minado inicial: **MANUAL** — activar AUTO desde el dashboard cuando estés listo
- Seed integrado en puerto 8888
- Orquestador activo (primeras TXs a los ~30s)
- Sin dashboard global

```bash
python launcher_auto.py --nodes 3
# → 3 nodos: P2P 5000–5002, dashboards 8000–8002
```

Flujo sugerido:
1. Esperar que todos los dashboards carguen (~5s)
2. Abrir `http://localhost:8000` a `http://localhost:8004`
3. En cada nodo → click en **AUTO** para activar minado
4. Los nodos compiten por bloques
5. A los ~30s el orquestador genera TXs entre nodos automáticamente

---

### 3D. Local Auto + Dashboard Global

**Qué incluye:** igual que 3C más dashboard global. Requiere **dos terminales**.

> **Sobre el orquestador:** `launcher_auto.py` ya incluye uno propio. `main_global.py`
> crea un segundo por defecto. Para no duplicar TXs usar `--no-orchestrator`.

**Terminal 1:**
```bash
python launcher_auto.py
# Default: 5 nodos, seed en 8888, orquestador integrado, nodos en MANUAL
```

**Terminal 2** (esperar ~3s):
```bash
python main_global.py --no-orchestrator
# Default: seed en localhost:8888, dashboard en puerto 9000
```

Dashboards:
```
http://localhost:9000  ← Dashboard global (proyector)
http://localhost:8000  ← Nodo 1  ...  http://localhost:8004 ← Nodo 5
```

---

## 4. Modo LAN

Cada máquina corre **un solo nodo**. El seed y el dashboard global corren
en la máquina del instructor.

### Preparación para todas las variantes LAN

**En `config.py` de TODAS las máquinas** cambiar:
```python
SEED_HOST = '192.168.1.X'   # IP real del instructor
```

Esto es suficiente para que cada nodo se registre automáticamente con el seed.
**No es necesario pasar `--bootstrap`** — el único argumento requerido al arrancar
un nodo es `--host` con la IP propia de esa máquina.

---

### 4E. LAN estándar

**Seed + nodos + dashboard global + orquestador**

Configuración completa recomendada para el laboratorio con 30 máquinas.

**Instructor — Terminal 1:**
```bash
python main_seed.py
# Default: 0.0.0.0:8888
```

**Instructor — Terminal 2:**
```bash
python main_global.py
# Default: seed desde config.py SEED_HOST:8888, dashboard en 9000
# Si no modificaste config.py en la máquina del instructor:
python main_global.py --seed-host 192.168.1.X
```

**Cada alumno:**
```bash
python main.py --host 192.168.1.Y
# Solo --host es necesario. Defaults:
#   --port 5000        puerto P2P
#   --dashboard 8000   puerto dashboard
#   seed: desde config.py SEED_HOST
```

Orden obligatorio:
```
1. main_seed.py              (instructor)
2. main_global.py            (instructor, segunda ventana)
3. main.py --host ...  × N   (alumnos, cualquier orden)
```

Dashboard instructor: `http://192.168.1.X:9000`
Dashboard alumno:     `http://192.168.1.Y:8000`

---

### 4F. LAN sin dashboard global

**Seed + nodos, sin vista centralizada**

```bash
# Instructor
python main_seed.py
# Default: 0.0.0.0:8888

# Cada alumno
python main.py --host 192.168.1.Y
# Default: puerto 5000, dashboard 8000, seed desde config.py
```

Cada alumno ve solo su propio nodo en `http://localhost:8000`.

---

### 4G. LAN sin orquestador

**Seed + nodos + dashboard global, TXs solo manuales**

```bash
# Instructor — Terminal 1
python main_seed.py

# Instructor — Terminal 2
python main_global.py --no-orchestrator

# Cada alumno
python main.py --host 192.168.1.Y
```

---

### 4H. LAN sin dashboard en los nodos

**Seed + nodos sin UI + dashboard global**

Reduce carga en máquinas alumno. Toda la visualización en el proyector.

```bash
# Instructor — Terminal 1
python main_seed.py

# Instructor — Terminal 2
python main_global.py

# Cada alumno (sin Flask local)
python main.py --host 192.168.1.Y --no-dashboard
# El nodo mina y participa normalmente, sin UI
```

---

## 5. Combinaciones no factibles

| Combinación | Por qué no funciona |
|---|---|
| **Local Manual + Dashboard Global sin seed explícito** | `launcher_manual.py` no arranca seed. El dashboard global necesita seed para descubrir nodos. Solución: combinación 3B con tres terminales. |
| **Local Auto sin seed** | Imposible: `launcher_auto.py` requiere seed para el orquestador. El seed siempre está integrado en `launcher_auto.py`. |
| **LAN sin seed** | Sin punto de rendezvous, las 30 máquinas no pueden descubrirse entre sí. `--bootstrap` solo sirve si se conoce de antemano la IP de al menos un nodo activo, lo que no es práctico en laboratorio. |
| **Orquestador sin seed** | El orquestador obtiene las wallets de los nodos desde `/addresses` del seed. Sin seed no tiene a quién enviarle TXs. |
| **Dashboard global sin seed** | Depende de `get_addresses()` del seed. Sin seed retorna lista vacía y el dashboard no ve ningún nodo. |
| **Dos instancias de cualquier launcher simultáneamente** | Conflicto de puertos (5000–5004, 8000–8004, 8888). La segunda instancia falla con `Address already in use`. |

---

## 6. Referencia de puertos

| Puerto | Componente | Dónde cambiarlo |
|---|---|---|
| `5000–5004` | P2P (nodos locales) | hardcoded en `launcher_*.py` |
| `5000` | P2P (nodo LAN) | `--port` en `main.py` o `P2P_PORT` en `config.py` |
| `8000–8004` | Dashboards (local) | hardcoded en `launcher_*.py` |
| `8000` | Dashboard (LAN) | `--dashboard` en `main.py` o `DASHBOARD_PORT` en `config.py` |
| `8888` | Seed node | `SEED_PORT` en `config.py` |
| `9000` | Dashboard global | hardcoded en `main_global.py` |

---

## 7. Referencia de parámetros ajustables

Todos en `config.py`:

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
| `MINING_AUTO_START` | `True` | Modo de minado al arrancar con `main.py` (LAN). No afecta a launchers. |
