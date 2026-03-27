# Documentación: `tests/test_blockchain.py`

## Propósito

Verifica el comportamiento completo de `Blockchain` — inicialización, mempool, minado, balances y validación de cadena.

## Tests

| Test | Qué verifica |
|------|--------------|
| `test_blockchain_initialization` | Chain con genesis, mempool vacío, constantes correctas |
| `test_genesis_block` | Genesis tiene `prev_hash='0'*64`, `timestamp=0`, coinbase |
| `test_get_latest_block` | Retorna el último bloque de la cadena |
| `test_add_transaction_to_mempool_valid` | TX válida con balance suficiente se agrega |
| `test_add_transaction_to_mempool_insufficient_balance` | TX sin fondos es rechazada |
| `test_add_transaction_to_mempool_invalid_signature` | TX sin firma es rechazada |
| `test_add_transaction_to_mempool_duplicate` | Segunda TX idéntica es rechazada |
| `test_mine_block_only_coinbase` | Bloque con solo coinbase: TX correcta, altura aumenta |
| `test_mine_block_with_transactions` | TXs del mempool se incluyen y el mempool se limpia |
| `test_get_balance` | Balance refleja coins recibidos menos enviados |
| `test_has_sufficient_balance` | True si balance >= amount, False si no |
| `test_validate_block_invalid_pow` | Bloque con nonce modificado falla PoW |
| `test_validate_chain_valid` | Cadena de 3 bloques pasa validación completa |
| `test_validate_chain_invalid_genesis` | Genesis diferente rechaza la cadena |
| `test_validate_chain_broken_link` | `prev_hash` incorrecto invalida la cadena |
| `test_full_workflow` | Flujo completo: minar, enviar, minar, verificar balances |
| `test_mempool_cleanup_after_mining` | Mempool queda vacío después de minar |
| `test_coinbase_always_first_transaction` | `transactions[0].from_address == "COINBASE"` |

## Test más importante

`test_full_workflow` — el único test que verifica el sistema completo de extremo a extremo:

```python
# Alice mina → 50 coins
# Alice → Bob: 10 coins  
# Alice → Charlie: 5 coins
# Bob mina (confirma ambas) → 50 + 10 = 60 coins
# Balances finales: Alice=35, Bob=60, Charlie=5
assert bc.get_balance(alice.address) == 35
assert bc.get_balance(bob.address)   == 60
assert bc.get_balance(charlie.address) == 5
```

---

*Documento: `DOC_test_blockchain.md` — Demo Blockchain*
