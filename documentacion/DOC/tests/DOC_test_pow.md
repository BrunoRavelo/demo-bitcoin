# Documentación: `tests/test_pow.py`

## Propósito

Verifica `ProofOfWork` — minado con diferentes dificultades, validación de nonces y cancelación via `threading.Event`.

## `MockBlockHeader`

Header mínimo que replica `BlockHeader.hash()` sin importar el módulo completo. Permite tests aislados del PoW sin depender de `Block` ni `Blockchain`.

## Tests de minado básico

| Test | Qué verifica |
|------|--------------|
| `test_pow_difficulty_3` | Mina con difficulty 3 — hash empieza con `000` |
| `test_pow_difficulty_4` | Mina con difficulty 4 en menos de 60s |
| `test_pow_validate_correct_nonce` | Nonce encontrado pasa `validate()` |
| `test_pow_validate_incorrect_nonce` | Nonce 12345 no cumple difficulty 4 |
| `test_pow_deterministic` | Mismo header → mismo nonce ganador |
| `test_pow_different_header_different_nonce` | Timestamp diferente → nonce diferente |
| `test_pow_hash_has_enough_zeros` | Hash resultante tiene al menos N ceros |
| `test_pow_more_zeros_than_minimum_still_valid` | Difficulty 2 acepta nonce encontrado con difficulty 3 |

## Tests de cancelación (Sprint 4.3)

| Test | Qué verifica |
|------|--------------|
| `test_mine_returns_none_when_stop_event_set_before` | `stop_event` activo antes → retorna None inmediatamente |
| `test_mine_cancels_mid_execution` | Cancelar desde otro thread mientras mina → retorna None |
| `test_mine_without_stop_event_works_normally` | Sin stop_event funciona como antes |
| `test_mine_completes_before_cancellation` | Termina antes del timeout → retorna nonce válido |
| `test_stop_event_cleared_for_reuse` | `clear()` permite reiniciar el minado |

## Test más importante

`test_mine_cancels_mid_execution` — verifica cancelación real desde otro thread:

```python
# Lanzar PoW con difficulty alta en thread separado
t = threading.Thread(target=mine_thread)
t.start()

# Esperar 100ms y cancelar
time.sleep(0.1)
stop_event.set()

t.join(timeout=5)
assert result[0] is None  # ✅ Cancelado limpiamente
```

Es la base del minado asíncrono: cuando llega un bloque externo, el event loop cancela el PoW en curso y el loop reinicia con el nuevo `prev_hash`.

---

*Documento: `DOC_test_pow.md` — Demo Blockchain*
