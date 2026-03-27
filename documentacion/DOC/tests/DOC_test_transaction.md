# Documentación: `tests/test_transaction.py`

## Propósito

Verifica `Transaction` — creación, firma, validación y serialización. Incluye los casos especiales de coinbase y Transaction Malleability.

## Tests

| Test | Qué verifica |
|------|--------------|
| `test_create_transaction` | Campos correctos, `signature=None` al crear |
| `test_transaction_hash` | TXID es string hex de 64 chars y determinístico |
| `test_different_transactions_different_hashes` | TXs distintas tienen TXIDs distintos |
| `test_sign_transaction` | Agrega `signature` y `public_key` no nulos |
| `test_cannot_sign_with_wrong_wallet` | Bob no puede firmar TX de Alice → `AssertionError` |
| `test_valid_signed_transaction` | TX firmada correctamente → `is_valid() == True` |
| `test_invalid_transaction_no_signature` | TX sin firma → `is_valid() == False` |
| `test_invalid_transaction_tampered_amount` | Modificar amount post-firma → `is_valid() == False` |
| `test_invalid_transaction_zero_amount` | `amount=0` → `is_valid() == False` |
| `test_coinbase_transaction_valid` | Coinbase sin firma → `is_valid() == True` |
| `test_transaction_to_dict` | Serialización incluye todos los campos |
| `test_transaction_from_dict` | TX deserializada sigue siendo válida |
| `test_transaction_hash_excludes_signature` | TXID idéntico antes y después de firmar |

## Test más importante

`test_transaction_hash_excludes_signature` — verifica que no hay Transaction Malleability:

```python
tx = Transaction(alice.address, "bob", 10)
hash_before = tx.hash()   # → "abc123..."
tx.sign(alice)
hash_after  = tx.hash()   # → "abc123..."  ← idéntico ✅
assert hash_before == hash_after
```

Bitcoin sufrió este problema hasta SegWit (2017). En nuestro demo la firma se excluye del hash por diseño.

---

*Documento: `DOC_test_transaction.md` — Demo Blockchain*
