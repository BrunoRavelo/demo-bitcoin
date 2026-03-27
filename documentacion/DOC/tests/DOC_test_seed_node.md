# Documentación: `tests/test_seed_node.py`

## Propósito

Tests de integración para `SeedNode` y `SeedClient`. Levanta un servidor Flask real en un thread y hace requests HTTP reales.

## Configuración

```python
TEST_PORT = 18888  # Puerto exclusivo — no conflicta con desarrollo (8888)
```

## Fixture `seed_server`

```python
@pytest.fixture(scope='module')
def seed_server():
    seed   = SeedNode(host='127.0.0.1', port=TEST_PORT)
    thread = threading.Thread(target=seed.run, daemon=True)
    thread.start()
    yield base_url
```

`scope='module'` — el servidor Flask se levanta **una sola vez** para todos los tests del módulo. Más rápido que levantar/bajar por cada test y evita problemas de puerto en uso.

## Tests de `/health`

| Test | Qué verifica |
|------|--------------|
| `test_health_endpoint` | Retorna 200 con `status='ok'`, `peers_count`, `timestamp` |

## Tests de `/register`

| Test | Qué verifica |
|------|--------------|
| `test_register_new_node` | Registro exitoso retorna `status='ok'` y `addr` |
| `test_register_without_host_fails` | Sin `host` → 400 |
| `test_register_without_port_fails` | Sin `port` → 400 |
| `test_register_without_body_fails` | Sin body JSON → 400 |
| `test_register_updates_existing_node` | Re-registro exitoso (keep-alive) |

## Tests de `/peers`

| Test | Qué verifica |
|------|--------------|
| `test_get_peers_returns_registered_nodes` | Nodos registrados aparecen en la lista |
| `test_get_peers_excludes_self` | Parámetro `exclude_host/port` funciona |
| `test_get_peers_response_structure` | Cada peer tiene `host`, `port`, `node_id` |

## Tests de `/peers/all`

| Test | Qué verifica |
|------|--------------|
| `test_get_all_peers_has_active_field` | Cada peer tiene `active`, `last_seen`, `first_seen` |

## Tests de `SeedClient`

| Test | Qué verifica |
|------|--------------|
| `test_seed_client_register` | `register()` retorna True con seed activo |
| `test_seed_client_get_peers` | `get_peers()` retorna lista |
| `test_seed_client_is_available` | `is_seed_available()` retorna True |
| `test_seed_client_unavailable_seed` | Puerto inexistente → False/[] sin excepción |

## Test más importante

`test_seed_client_unavailable_seed` — el nodo debe arrancar aunque el seed no esté disponible:

```python
client = SeedClient(..., seed_port=19999)  # Puerto inexistente
assert client.register()          is False  # ✅ Sin excepción
assert client.get_peers()         == []     # ✅ Lista vacía
assert client.is_seed_available() is False  # ✅ Sin excepción
```

---

*Documento: `DOC_test_seed_node.md` — Demo Blockchain*
