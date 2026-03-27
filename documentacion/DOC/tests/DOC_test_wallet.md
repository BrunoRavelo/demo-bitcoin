# Documentación: `tests/test_wallet.py`

## Propósito

Verifica `Wallet` — generación de llaves Ed25519, derivación de address Bitcoin-compatible, firma y verificación de transacciones.

## Tests

| Test | Qué verifica |
|------|--------------|
| `test_create_wallet` | Address no vacía, empieza con `'1'`, longitud 25-34 chars |
| `test_wallets_have_different_addresses` | Cada wallet genera address única |
| `test_get_public_key_hex` | Public key exportada = 64 chars hex (32 bytes Ed25519) |
| `test_sign_transaction` | Firma = 128 chars hex (64 bytes Ed25519) |
| `test_verify_valid_signature` | Firma propia con datos originales → True |
| `test_verify_invalid_signature_wrong_data` | Datos modificados → False |
| `test_verify_invalid_signature_wrong_pubkey` | Public key de otra wallet → False |
| `test_verify_invalid_signature_corrupted` | Últimos 4 chars cambiados → False |
| `test_deterministic_signatures` | Mismo mensaje + misma llave = misma firma (Ed25519) |
| `test_different_messages_different_signatures` | Mensajes distintos = firmas distintas |

## Test más importante

`test_deterministic_signatures` — verifica la propiedad más importante de Ed25519 vs ECDSA:

```python
signature1 = wallet.sign_transaction(data)
signature2 = wallet.sign_transaction(data)
assert signature1 == signature2  # ✅ Determinístico
```

ECDSA (Bitcoin) usa un nonce aleatorio por firma — si el nonce se repite, la private key queda expuesta (caso PlayStation 3, 2010). Ed25519 calcula el nonce como `SHA512(private_key || mensaje)`, eliminando este riesgo.

## Nota sobre la address

`test_create_wallet` verifica que la address empieza con `'1'`. El byte de versión `0x00` en Base58Check siempre produce una address que empieza con `1` — exactamente como Bitcoin mainnet.

---

*Documento: `DOC_test_wallet.md` — Demo Blockchain*
