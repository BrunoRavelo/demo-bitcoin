# Documentación Técnica: `utils/logger.py`

---

## Propósito del Archivo

`utils/logger.py` configura el sistema de logging del demo. Cada nodo tiene su propio logger identificado por `node_id`, que escribe simultáneamente a consola y a un archivo en `logs/`.

---

## Dependencias

```python
import logging
import os
```

| Import | Propósito |
|--------|-----------|
| `logging` | Módulo estándar de Python para logging |
| `os` | Crear la carpeta `logs/` si no existe |

---

## Función `setup_logger`

```python
def setup_logger(node_id: str, level=logging.INFO) -> logging.Logger:
```

**¿Qué hace?**

Configura y retorna un logger para un nodo específico. Si el logger ya existe (llamadas repetidas con el mismo `node_id`), retorna el logger existente sin duplicar handlers.

**Proceso:**

```
1. os.makedirs('logs', exist_ok=True)
        │
        ▼
2. log_filename = f'logs/{node_id}.log'
        │
        ▼
3. logger = logging.getLogger(node_id)
        │
        ▼
4. ¿logger.handlers ya existe?
   Sí → return logger  (evitar duplicar handlers)
        │
        ▼
5. Crear Formatter (formato de mensajes)
        │
        ▼
6. Crear FileHandler (escribe a archivo)
        │
        ▼
7. Crear StreamHandler (escribe a consola)
        │
        ▼
8. logger.addHandler(file_handler)
   logger.addHandler(console_handler)
        │
        ▼
9. return logger
```

---

## Parámetros

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `node_id` | `str` | — | Identificador único del nodo (ej. `node_5000`) |
| `level` | `int` | `logging.INFO` | Nivel mínimo de severidad a registrar |

**Niveles de logging:**

| Nivel | Valor | Uso |
|-------|-------|-----|
| `DEBUG` | 10 | Información de diagnóstico detallada |
| `INFO` | 20 | Eventos normales del sistema (default) |
| `WARNING` | 30 | Advertencias — algo inesperado pero no fatal |
| `ERROR` | 40 | Errores que impiden una operación |
| `CRITICAL` | 50 | Errores graves que pueden crashear el sistema |

---

## Formato de Mensajes

```python
formatter = logging.Formatter(
    fmt='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
```

**Ejemplo de output:**

```
14:32:15 | INFO     | [node_5000] Conectado a peer 192.168.1.6:5000
14:32:16 | INFO     | [node_5000] TX abc123... agregada al mempool
14:32:45 | INFO     | [MINED] ¡Bloque minado! nonce=73842, hash=0000a3f2...
14:33:01 | WARNING  | [node_5000] Peer 192.168.1.7:5000 no responde
14:33:01 | INFO     | [node_5000] Peer eliminado de peers_connected
```

**Columnas del formato:**

| Columna | Descripción |
|---------|-------------|
| `%(asctime)s` | Hora en formato `HH:MM:SS` |
| `%(levelname)-8s` | Nivel con padding de 8 chars (alineado) |
| `%(message)s` | Mensaje del log |

---

## Archivo de Log

```python
log_filename = f'logs/{node_id}.log'
file_handler = logging.FileHandler(log_filename, mode='w', encoding='utf-8')
```

**Características:**

- **Nombre:** `logs/node_5000.log`, `logs/node_5001.log`, etc.
- **Modo `'w'`:** Sobrescribe el archivo en cada ejecución (no acumula logs de sesiones anteriores)
- **Encoding `utf-8`:** Soporta caracteres especiales y emojis en los mensajes

**¿Por qué `mode='w'` y no `mode='a'` (append)?**

En un demo educativo, los logs de sesiones anteriores son ruido. Con `mode='w'`, cada ejecución comienza con un log limpio, facilitando el debugging de la sesión actual.

---

## Guard de Duplicación

```python
if logger.handlers:
    return logger
```

**¿Por qué es necesario?**

`logging.getLogger(node_id)` retorna el mismo objeto logger si ya existe (el módulo `logging` mantiene un registro global de loggers). Sin este guard, llamar a `setup_logger('node_5000')` dos veces agregaría handlers duplicados, produciendo cada mensaje de log dos veces.

```python
# Sin el guard:
setup_logger('node_5000')  # agrega FileHandler + StreamHandler
setup_logger('node_5000')  # agrega OTROS FileHandler + StreamHandler
# Resultado: cada mensaje se imprime 2 veces y se escribe 2 veces al archivo

# Con el guard:
setup_logger('node_5000')  # agrega FileHandler + StreamHandler
setup_logger('node_5000')  # retorna logger existente sin cambios ✅
```

---

## Uso en los Módulos

```python
# En p2p_node.py:
from utils.logger import setup_logger

class P2PNode:
    def __init__(self, host, port, ...):
        self.logger = setup_logger(f'node_{port}')
        self.logger.info(f"Nodo iniciado en {host}:{port}")

# En seed_node.py:
from utils.logger import setup_logger

class SeedNode:
    def __init__(self, host, port):
        self.logger = setup_logger('seed_node')

# En tx_orchestrator.py:
from utils.logger import setup_logger

class TxOrchestrator:
    def __init__(self, ...):
        self.logger = setup_logger('orchestrator')
```

---

## Archivos Generados

```
logs/
├── node_5000.log  ← Nodo en puerto 5000
├── node_5001.log  ← Nodo en puerto 5001
├── node_5002.log  ← Nodo en puerto 5002
├── seed_node.log  ← Seed node
└── orchestrator.log ← TxOrchestrator
```

Estos archivos están excluidos del repositorio via `.gitignore`:

```
# .gitignore
logs/
```

---

## Diagnóstico con Logs

Los logs son especialmente útiles para diagnosticar:

| Problema | Qué buscar en el log |
|----------|---------------------|
| Nodo no se conecta | `WARNING` sobre conexión fallida |
| TX rechazada | `WARNING` sobre firma inválida o balance insuficiente |
| Fork detectado | `INFO` sobre `replace_chain` exitoso |
| Bloque rechazado | `WARNING` sobre PoW o Merkle inválido |
| Seed no disponible | `WARNING` sobre `ConnectionError` al registrar |

---

*Documento: `DOC_utils_logger.md` — Demo Blockchain*
