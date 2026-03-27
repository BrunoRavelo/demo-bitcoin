# Documentación: `tests/test_p2p_node.py`

## Propósito

Tests de integración P2P — los más complejos de la suite. Levantan nodos reales con WebSocket para probar conexión, propagación y sincronización.

## Configuración

```python
BASE_PORT  = 19000  # Puertos exclusivos — no conflictan con desarrollo
DIFFICULTY = 1      # Minado instantáneo en tests
```

## Helpers

### `make_node`
```python
def make_node(port, bootstrap=None) -> P2PNode:
    node = P2PNode(...)
    node.mining_mode = MINING_PAUSED  # No minar en background
    return node
```
Los nodos arrancan en PAUSED para evitar interferencias entre tests.

### `wait_for_condition`
```python
async def wait_for_condition(condition, timeout=10, interval=0.2):
    # Polling hasta que condition() sea True o timeout
```
Las operaciones de red son asíncronas — no se puede verificar el resultado inmediatamente.

## Tests de conexión

| Test | Qué verifica |
|------|--------------|
| `test_two_nodes_connect` | Handshake exitoso entre 2 nodos |
| `test_three_nodes_form_network` | node1 queda conectado a 2 peers |

## Tests de transacciones

| Test | Qué verifica |
|------|--------------|
| `test_tx_propagates_to_peer` | TX llega al mempool del otro nodo |
| `test_tx_with_insufficient_balance_rejected` | Sin balance → `ValueError` local |

## Tests de bloques

| Test | Qué verifica |
|------|--------------|
| `test_block_propagates_to_peer` | Bloque minado llega a otro nodo |
| `test_miner_receives_reward_after_block` | Balance = BLOCK_REWARD después de minar |

## Tests de sincronización

| Test | Qué verifica |
|------|--------------|
| `test_late_node_syncs_chain` | Nodo nuevo adopta cadena existente |
| `test_longest_chain_wins` | Nodo con cadena corta adopta la más larga |

## Tests de modos de minado

| Test | Qué verifica |
|------|--------------|
| `test_node_initial_mining_mode` | Modo inicial viene de `config.py` |
| `test_set_mining_mode_paused` | Cambiar a PAUSED activa el stop_event |
| `test_node_balance_zero_initially` | Balance inicial es 0.0 |
| `test_node_balance_after_mining` | Balance = BLOCK_REWARD después de minar |

## Tests más importantes

### `test_late_node_syncs_chain`
```
node1 mina 3 bloques (solo, altura=4)
node2 se une (solo genesis, altura=1)
forzar sincronización
→ node2 alcanza altura 4 ✅
```
Simula el caso más común en el lab: alumno que arranca tarde.

### `test_longest_chain_wins`
```
node1 mina 2 bloques (aislado)
node2 mina 4 bloques (aislado)
conectar ambos
→ node1 adopta cadena de node2 ✅
```
Prueba directa de la longest chain rule.

## Nota sobre warnings

Los tests generan `RuntimeError: Event loop is closed` al terminar en Windows. Es comportamiento conocido de `websockets 12.x` con `pytest-asyncio` — no indica fallo real.

---

*Documento: `DOC_test_p2p_node.md` — Demo Blockchain*
