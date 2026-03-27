# Documentación: `main_global.py`

## Propósito

Entry point del dashboard global del instructor. Inicia el `TxOrchestrator` y el `GlobalDashboard` como proceso independiente. Funciona igual en demo local y en LAN de 30 máquinas.

## Uso

```powershell
# Demo local (segunda terminal)
python main_global.py

# LAN — apuntar al seed del instructor
python main_global.py --seed-host 192.168.1.1

# Sin orquestador (si launcher_auto.py ya tiene el suyo)
python main_global.py --no-orchestrator
```

## Argumentos

| Argumento | Default | Descripción |
|-----------|---------|-------------|
| `--seed-host` | `localhost` | IP del seed node |
| `--seed-port` | `8888` | Puerto del seed |
| `--no-orchestrator` | False | Solo observar, sin generar TXs |

## Secuencia de arranque

```
1. (Opcional) Crear TxOrchestrator
2. Crear GlobalDashboard en Flask thread (puerto 9000)
3. (Opcional) asyncio.create_task(_start_orchestrator_delayed)
4. await asyncio.Future()  ← correr para siempre
```

## `_start_orchestrator_delayed`

```python
async def _start_orchestrator_delayed(orchestrator):
    await asyncio.sleep(30)          # Esperar a que haya balance
    orchestrator.set_mode(ORCH_AUTO) # Forzar AUTO independiente de config.py
    await orchestrator.start()
```

El delay de 30 segundos da tiempo a que los nodos minen sus primeros bloques y tengan balance antes de que el orquestador intente enviar TXs.

## Escenarios de uso

### Demo local con `launcher_manual.py`
```powershell
# Terminal 1:
python launcher_manual.py --nodes 3

# Terminal 2:
python main_global.py  # Con orquestador (los nodos son manuales)
```

### Demo local con `launcher_auto.py`
```powershell
# Terminal 1:
python launcher_auto.py --nodes 3  # Ya tiene orquestador

# Terminal 2:
python main_global.py --no-orchestrator  # Solo observer
```

### LAN de 30 máquinas
```powershell
# Instructor:
python main_seed.py    # seed en 8888
python main_global.py  # dashboard + orquestador en 9000

# Cada alumno:
python main.py --host 192.168.1.X --bootstrap 192.168.1.1:5000
```

---

*Documento: `DOC_main_global.md` — Demo Blockchain*
