# Documentación: `tests/test_block.py`

## Propósito

Verifica que `Block` y `BlockHeader` funcionan correctamente — creación, hashing, validación de PoW, Merkle root y transacciones, y serialización.

## Helper

```python
def create_dummy_tx(seed: int):
    tx = Transaction(f"from_{seed}", f"to_{seed}", seed)
    tx.timestamp = seed  # Timestamp fijo para determinismo
    return tx
```

Crea transacciones con datos predecibles. El `timestamp` fijo garantiza que el hash sea idéntico en cada ejecución.

## Tests

| Test | Qué verifica |
|------|--------------|
| `test_create_block_header` | Los 5 campos del header se asignan correctamente |
| `test_block_header_hash` | Hash es string hex de 64 chars y es determinístico |
| `test_block_header_hash_changes_with_nonce` | Cambiar nonce cambia el hash — base del PoW |
| `test_block_header_serialization` | `to_dict()` / `from_dict()` es reversible |
| `test_create_block` | Block agrupa header y transacciones correctamente |
| `test_block_validate_merkle_root_valid` | Merkle root correcto pasa validación |
| `test_block_validate_merkle_root_invalid` | Merkle root incorrecto falla validación |
| `test_block_validate_pow_valid` | Hash con ceros suficientes es válido |
| `test_block_validate_pow_invalid` | Nonce arbitrario (12345) probablemente no cumple difficulty 4 |
| `test_block_validate_transactions_valid` | TX firmada correctamente pasa validación |
| `test_block_validate_transactions_invalid` | TX sin firma falla validación |
| `test_block_serialization` | Block completo se serializa y deserializa correctamente |
| `test_block_hash_immutable` | Misma instancia retorna siempre el mismo hash |
| `test_block_tampering_detected` | Modificar `amount` de TX invalida el Merkle root |

## Test más importante

`test_block_tampering_detected` — modifica el amount de una TX después de crear el bloque y verifica que `validate_merkle_root()` falla. Es la prueba de integridad de datos más directa del sistema.

---

*Documento: `DOC_test_block.md` — Demo Blockchain*
