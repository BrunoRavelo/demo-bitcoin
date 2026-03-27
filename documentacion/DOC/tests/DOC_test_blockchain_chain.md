# Documentación: `tests/test_blockchain_chain.py`

## Propósito

Verifica `replace_chain()` — la longest chain rule y el mecanismo de consenso. Son los tests más críticos del sistema porque prueban cómo se resuelven los forks.

## Helper

```python
def mine_n_blocks(blockchain, n, miner_address):
    for _ in range(n):
        blockchain.mine_block(miner_address)
```

## Tests de `replace_chain`

| Test | Qué verifica |
|------|--------------|
| `test_replace_chain_accepts_longer_valid_chain` | Cadena más larga y válida es adoptada |
| `test_replace_chain_rejects_shorter_chain` | Cadena más corta es rechazada |
| `test_replace_chain_rejects_same_length` | Cadena de igual longitud es rechazada (`>`, no `>=`) |
| `test_replace_chain_rejects_invalid_chain` | Cadena más larga pero con PoW inválido es rechazada |
| `test_replace_chain_rejects_different_genesis` | Genesis diferente siempre rechazado |
| `test_replace_chain_updates_height` | La altura se actualiza correctamente tras reemplazo |
| `test_replace_chain_recovers_orphaned_txs` | TXs en bloques huérfanos vuelven al mempool |
| `test_replace_chain_cleans_confirmed_txs_from_mempool` | TXs ya confirmadas se eliminan del mempool |

## Tests de serialización

| Test | Qué verifica |
|------|--------------|
| `test_get_chain_as_dicts` | Cadena serializada tiene estructura correcta |
| `test_chain_from_dicts_roundtrip` | Serializar + deserializar produce hashes idénticos |
| `test_find_fork_point_identical_chains` | Fork point en cadenas idénticas es la longitud |

## Tests de utilidades

| Test | Qué verifica |
|------|--------------|
| `test_get_height` | Altura = número de bloques |
| `test_get_block_by_hash_found` | Encuentra bloque existente por hash |
| `test_get_block_by_hash_not_found` | Retorna None para hash inexistente |

## Test más importante

`test_replace_chain_recovers_orphaned_txs` — simula un fork real:

```
bc1: Genesis → alice_mina → [TX confirmada Alice→Bob]
bc2: Genesis → alice_mina → bloque2 → bloque3  ← más larga

bc1 adopta bc2 → TX Alice→Bob queda huérfana
→ TX vuelve al mempool de bc1 ✅
```

---

*Documento: `DOC_test_blockchain_chain.md` — Demo Blockchain*
