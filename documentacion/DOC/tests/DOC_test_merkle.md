# Documentación: `tests/test_merkle.py`

## Propósito

Verifica `MerkleTree` — construcción del árbol, cálculo del root, manejo de casos especiales (vacío, impar) y pruebas SPV.

## Tests

| Test | Qué verifica |
|------|--------------|
| `test_merkle_root_single_transaction` | 1 TX produce root de 64 chars hex |
| `test_merkle_root_deterministic` | Mismo input siempre produce mismo root |
| `test_merkle_root_changes_with_data` | TX diferente produce root diferente |
| `test_merkle_odd_number_of_transactions` | 3 TXs (impar) no rompe el árbol — duplica la última |
| `test_merkle_even_number_of_transactions` | 4 TXs (par) produce root válido |
| `test_merkle_empty_transactions` | Sin TXs retorna `'0' * 64` |
| `test_merkle_tree_structure` | Con 4 TXs el árbol tiene 3 niveles: 4→2→1 |
| `test_merkle_order_matters` | `[TX1, TX2]` ≠ `[TX2, TX1]` — el orden importa |
| `test_merkle_proof_generation` | `get_proof(0)` retorna lista no vacía |
| `test_merkle_proof_verification` | Prueba SPV válida retorna True |
| `test_merkle_proof_invalid` | TX que no está en el árbol falla la prueba |

## Test más importante

`test_merkle_proof_verification` — verifica SPV (Simplified Payment Verification):

```python
# Dado solo el hash de la TX y el Merkle root,
# se puede probar que la TX está en el bloque
# sin conocer todas las TXs del bloque.
proof    = merkle.get_proof(0)
tx_hash  = merkle.hash_transaction(txs[0])
is_valid = MerkleTree.verify_proof(tx_hash, merkle_root, proof)
assert is_valid  # ✅
```

En Bitcoin, los clientes ligeros (wallets móviles) usan esto para verificar pagos sin descargar toda la blockchain.

---

*Documento: `DOC_test_merkle.md` — Demo Blockchain*
