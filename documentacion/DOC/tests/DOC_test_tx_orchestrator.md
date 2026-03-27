# Documentación: `tests/test_tx_orchestrator.py`

## Propósito

Tests de integración para `TxOrchestrator` usando mocks HTTP. No levanta nodos reales — simula sus respuestas con `unittest.mock`.

## Fixture `orchestrator`

```python
@pytest.fixture
def orchestrator():
    with patch('core.tx_orchestrator.TX_AUTO_START', False):
        orch = TxOrchestrator(seed_host='localhost', seed_port=18888)
    return orch
```

`TX_AUTO_START=False` garantiza modo MANUAL al iniciar — el orquestador no genera TXs automáticamente durante los tests.

## Por qué mocks HTTP

```python
mock_response = MagicMock()
mock_response.status_code = 200

with patch('requests.post', return_value=mock_response):
    result = await orchestrator.send_tx(...)
```

Permite verificar el comportamiento del orquestador sin depender de nodos reales corriendo. Tests deterministas y rápidos.

## Tests de inicialización

| Test | Qué verifica |
|------|--------------|
| `test_orchestrator_initial_mode_manual` | Arranca en MANUAL con `TX_AUTO_START=False` |
| `test_orchestrator_initial_stats` | `txs_sent=0`, `txs_failed=0`, `running=False` |
| `test_orchestrator_auto_mode_on_start` | Arranca en AUTO con `TX_AUTO_START=True` |

## Tests de control de modo

| Test | Qué verifica |
|------|--------------|
| `test_set_mode_auto` | Cambia a ORCH_AUTO correctamente |
| `test_set_mode_manual` | Cambia a ORCH_MANUAL correctamente |
| `test_set_mode_invalid` | Modo inválido lanza `ValueError` |

## Tests de `send_tx`

| Test | Qué verifica |
|------|--------------|
| `test_send_tx_success` | HTTP 200 → True, `txs_sent += 1` |
| `test_send_tx_failure_400` | HTTP 400 → False, `txs_failed += 1` |
| `test_send_tx_connection_error` | `ConnectionError` → False, `txs_failed += 1` |

## Tests de `_auto_cycle`

| Test | Qué verifica |
|------|--------------|
| `test_auto_cycle_needs_at_least_2_addresses` | Con 1 address no envía TX |
| `test_auto_cycle_skips_zero_balance` | Balance 0 → no envía TX |
| `test_auto_cycle_sends_tx_with_balance` | Balance > 0 con 2+ nodos → envía TX |

## Tests de stats

| Test | Qué verifica |
|------|--------------|
| `test_get_stats_structure` | Contiene todos los campos esperados |
| `test_success_rate_calculation` | 2 éxitos + 1 fallo → `success_rate ≈ 0.667` |
| `test_repr` | `repr()` contiene `TxOrchestrator` y `mode` |

---

*Documento: `DOC_test_tx_orchestrator.md` — Demo Blockchain*
