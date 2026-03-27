# Documentación: `tests/test_protocol.py`

## Propósito

Verifica `protocol.py` — constantes `MSG_*`, `create_message()` y `validate_message()`.

## Tests de constantes

| Test | Qué verifica |
|------|--------------|
| `test_all_message_constants_are_strings` | Todos los MSG_* son strings no vacíos |
| `test_all_message_constants_are_unique` | No hay dos MSG_* con el mismo valor |

## Tests de `create_message`

| Test | Qué verifica |
|------|--------------|
| `test_create_message_has_required_fields` | Incluye type, id, timestamp, payload, checksum |
| `test_create_message_type_matches` | El tipo coincide con el argumento |
| `test_create_message_payload_preserved` | El payload se conserva intacto |
| `test_create_message_id_is_unique` | Cada mensaje tiene UUID diferente |
| `test_create_message_timestamp_is_recent` | Timestamp coincide con momento de creación |
| `test_create_message_checksum_is_sha256_hex` | Checksum es string hex de 64 chars |
| `test_create_message_empty_payload` | Funciona con payload vacío `{}` |

## Tests de `validate_message`

| Test | Qué verifica |
|------|--------------|
| `test_validate_message_valid` | Mensaje de `create_message` siempre es válido |
| `test_validate_message_missing_type` | Sin `type` → False |
| `test_validate_message_missing_id` | Sin `id` → False |
| `test_validate_message_missing_payload` | Sin `payload` → False |
| `test_validate_message_missing_checksum` | Sin `checksum` → False |
| `test_validate_message_tampered_payload` | Payload modificado → checksum no coincide → False |
| `test_validate_message_tampered_checksum` | Checksum falso → False |
| `test_validate_message_empty_dict` | Dict vacío → False |
| `test_validate_message_all_types` | Todos los MSG_* pasan validación |
| `test_checksum_deterministic` | Mismo payload → mismo checksum |
| `test_different_payloads_different_checksums` | Payloads distintos → checksums distintos |

## Test más importante

`test_validate_message_tampered_payload` — el nodo no puede procesar mensajes con datos corruptos:

```python
msg = create_message(MSG_TX, {'amount': 10})
msg['payload']['amount'] = 9999  # Modificar sin recalcular checksum
assert validate_message(msg) is False  # ✅ Detectado
```

---

*Documento: `DOC_test_protocol.md` — Demo Blockchain*
