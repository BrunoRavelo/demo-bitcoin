# Documentación: `dashboard_global/app.py`

## Propósito

Servidor Flask del dashboard global del instructor. Observer de toda la red — consulta el seed para obtener la lista de nodos y luego hace GET a cada dashboard individual para obtener su estado en tiempo real.

## Clase `GlobalDashboard`

```python
class GlobalDashboard:
    def __init__(
        self,
        seed_host:    str = SEED_HOST,
        seed_port:    int = SEED_PORT,
        port:         int = 9000,
        orchestrator       = None,
    ):
```

| Atributo | Descripción |
|----------|-------------|
| `port` | Puerto Flask (9000) |
| `orchestrator` | `TxOrchestrator` o None — controla TXs de toda la red |
| `seed_client` | Lee nodos del seed |

## Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Página principal |
| `/api/network` | GET | Estado de todos los nodos + resumen |
| `/api/orchestrator` | GET | Estado del orquestador |
| `/api/orchestrator/auto` | POST | Activar TXs automáticas |
| `/api/orchestrator/manual` | POST | Pausar TXs automáticas |

## Flujo de `/api/network`

```
1. seed_client.get_addresses() → lista de nodos
2. Thread por nodo → GET nodo:dashboard_port/api/status
3. Calcular max_height
4. Marcar in_sync (lag ≤ 2 bloques)
5. Construir summary
6. Retornar nodes + summary + seed_online
```

**¿Por qué threads?** `requests` es síncrono. Con 30 nodos, usar un thread por nodo permite consultarlos todos en paralelo — el tiempo total es el de la respuesta más lenta, no la suma.

## Función `_fetch_node_status`

Nunca lanza excepción. Si el nodo no responde retorna `{'online': False, ...}` con datos en cero.

## Función `_build_summary`

Agrega: total/online/offline nodos, in_sync/out_of_sync, max_height, total mempool, total bloques minados, nodos en AUTO.

## Definición de `in_sync`

```python
lag     = max_height - node['chain_height']
in_sync = lag <= 2  # 2 bloques de margen para latencia de red
```

---

*Documento: `DOC_dashboard_global_app.md` — Demo Blockchain*
