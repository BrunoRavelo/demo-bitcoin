# Documentación Técnica: `main_seed.py`

---

## Propósito del Archivo

`main_seed.py` es el **punto de entrada del seed node** — el servidor de descubrimiento de peers. En un demo LAN, el instructor ejecuta este script en su máquina antes de que cualquier alumno arranque su nodo.

**¿Por qué debe ejecutarse primero?**

Sin el seed node activo, los nodos no pueden descubrirse entre sí. El seed es el directorio central que permite a un nodo nuevo encontrar a los demás. Una vez que los nodos se conocen y están conectados directamente, el seed puede caerse sin afectar la red (no es un punto de falla crítico para el funcionamiento).

---

## Dependencias

```python
import argparse
from network.seed_node import SeedNode
from config import SEED_PORT
```

| Import | Propósito |
|--------|-----------|
| `argparse` | Parsing de argumentos CLI |
| `SeedNode` | Clase que implementa el servidor HTTP de descubrimiento |
| `SEED_PORT` | Puerto por defecto (8888) |

---

## Argumentos de Línea de Comandos

```bash
python main_seed.py [--port PORT] [--host HOST]
```

| Argumento | Default | Descripción |
|-----------|---------|-------------|
| `--port` | 8888 | Puerto HTTP donde escucha el seed |
| `--host` | `0.0.0.0` | Interfaz de red (`0.0.0.0` = todas las interfaces) |

**¿Por qué `--host 0.0.0.0` por defecto?**

`0.0.0.0` significa "escuchar en todas las interfaces de red disponibles". Esto permite que los nodos de toda la LAN alcancen el seed, independientemente de en qué IP esté la máquina del instructor. En contraste, `localhost` solo aceptaría conexiones desde la misma máquina.

---

## Función `main`

```python
def main():
    # 1. Parsear argumentos
    parser = argparse.ArgumentParser(...)
    args = parser.parse_args()

    # 2. Imprimir banner informativo
    print(f"""
╔══════════════════════════════════════════════╗
║         SEED NODE — BLOCKCHAIN DEMO          ║
...
  Endpoints:
    GET  /health      — verificar estado
    POST /register    — registrar nodo
    GET  /peers       — obtener lista de peers
    GET  /peers/all   — todos (incluye inactivos)
""")

    # 3. Instanciar y arrancar SeedNode (bloqueante)
    seed = SeedNode(host=args.host, port=args.port)
    seed.run()
```

**¿Por qué `main()` es síncrona (no `async`)?**

El seed node está implementado con **Flask**, que es un framework web síncrono. A diferencia de los nodos P2P que usan asyncio + WebSockets, el seed solo maneja requests HTTP simples — Flask es perfectamente adecuado y más simple que asyncio para este caso.

**`seed.run()` bloquea** hasta que se presiona Ctrl+C, igual que cualquier servidor Flask.

---

## Output al Arrancar

```
╔══════════════════════════════════════════════╗
║         SEED NODE — BLOCKCHAIN DEMO          ║
╚══════════════════════════════════════════════╝

  Escuchando en: http://0.0.0.0:8888

  Endpoints:
    GET  /health      — verificar estado
    POST /register    — registrar nodo
    GET  /peers       — obtener lista de peers
    GET  /peers/all   — todos (incluye inactivos)

  Arranca este nodo PRIMERO.
  Configura SEED_HOST=0.0.0.0 en config.py
  de todas las máquinas del laboratorio.

  Presiona Ctrl+C para detener.
```

---

## Uso en Demo LAN

### Instrucciones para el instructor:

```powershell
# 1. Verificar tu IP de red local
ipconfig
# Encontrar la IP LAN (ej. 192.168.1.1)

# 2. Arrancar el seed
python main_seed.py
# Queda escuchando en 0.0.0.0:8888

# 3. Verificar que funciona
# En el navegador: http://localhost:8888/health
# Debería mostrar: {"status": "ok", "peers_count": 0, ...}
```

### Los alumnos configuran:

```python
# config.py de cada alumno:
SEED_HOST = '192.168.1.1'  # IP del instructor
```

O por argumento:
```powershell
python main.py --host 192.168.1.X --seed-host 192.168.1.1
```

---

## Verificar Estado del Seed

### Via navegador:

```
http://192.168.1.1:8888/health
```

Respuesta esperada:
```json
{
    "status": "ok",
    "peers_count": 15,
    "addresses_count": 15,
    "timestamp": 1707234567.123
}
```

### Via curl/PowerShell:
```powershell
Invoke-RestMethod http://192.168.1.1:8888/health
Invoke-RestMethod http://192.168.1.1:8888/peers/all
```

---

## Rol del Seed en la Red

```
Alumno A arranca main.py
    │
    ├── POST /register → Seed guarda {host: 192.168.1.5, port: 5000}
    │
    └── GET /peers → Seed responde [{host: 192.168.1.6, port: 5000}, ...]
              │
              └── Alumno A conecta directamente a los peers → red P2P formada
                  (el seed ya no es necesario para el funcionamiento)
```

**El seed no participa en el consenso** — no tiene blockchain, no valida TXs ni bloques. Es únicamente un directorio de contactos.

---

## Diferencia con el Seed Integrado de `launcher_auto.py`

| Aspecto | `main_seed.py` | Seed en `launcher_auto.py` |
|---------|---------------|---------------------------|
| Uso | Demo LAN | Demo local |
| Proceso | Independiente | Thread dentro del launcher |
| Puerto | Configurable (default 8888) | Hardcoded 8888 |
| Host | Configurable (default 0.0.0.0) | Hardcoded 0.0.0.0 |
| Cómo arrancar | `python main_seed.py` | Automático con `launcher_auto.py` |

En demo local con `launcher_auto.py`, el seed se arranca automáticamente sin necesidad de `main_seed.py`.

---

*Documento: `DOC_main_seed.md` — Demo Blockchain*
