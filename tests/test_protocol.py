"""
Tests para network/protocol.py
Cubre create_message(), validate_message() y constantes MSG_*
"""

import time
import pytest
from network.protocol import (
    create_message, validate_message,
    MSG_VERSION, MSG_VERACK,
    MSG_PING, MSG_PONG,
    MSG_GETADDR, MSG_ADDR,
    MSG_TX, MSG_INV, MSG_GETBLOCKS, MSG_BLOCK,
)


# ──────────────────────────────────────────────────────────
# Tests de constantes
# ──────────────────────────────────────────────────────────

def test_all_message_constants_are_strings():
    """Todas las constantes MSG_* son strings no vacíos."""
    constants = [
        MSG_VERSION, MSG_VERACK,
        MSG_PING, MSG_PONG,
        MSG_GETADDR, MSG_ADDR,
        MSG_TX, MSG_INV, MSG_GETBLOCKS, MSG_BLOCK,
    ]
    for c in constants:
        assert isinstance(c, str)
        assert len(c) > 0


def test_all_message_constants_are_unique():
    """No hay dos constantes MSG_* con el mismo valor."""
    constants = [
        MSG_VERSION, MSG_VERACK,
        MSG_PING, MSG_PONG,
        MSG_GETADDR, MSG_ADDR,
        MSG_TX, MSG_INV, MSG_GETBLOCKS, MSG_BLOCK,
    ]
    assert len(constants) == len(set(constants))


# ──────────────────────────────────────────────────────────
# Tests de create_message
# ──────────────────────────────────────────────────────────

def test_create_message_has_required_fields():
    """create_message incluye todos los campos requeridos."""
    msg = create_message(MSG_PING, {'nonce': 12345})

    assert 'type'      in msg
    assert 'id'        in msg
    assert 'timestamp' in msg
    assert 'payload'   in msg
    assert 'checksum'  in msg


def test_create_message_type_matches():
    """El tipo del mensaje coincide con el argumento."""
    msg = create_message(MSG_TX, {'from': 'alice', 'amount': 10})
    assert msg['type'] == MSG_TX


def test_create_message_payload_preserved():
    """El payload se conserva intacto."""
    payload = {'key': 'value', 'number': 42, 'nested': {'a': 1}}
    msg = create_message(MSG_BLOCK, payload)
    assert msg['payload'] == payload


def test_create_message_id_is_unique():
    """Cada mensaje tiene un ID único."""
    msg1 = create_message(MSG_PING, {})
    msg2 = create_message(MSG_PING, {})
    assert msg1['id'] != msg2['id']


def test_create_message_timestamp_is_recent():
    """El timestamp del mensaje coincide con el momento de creación."""
    from unittest.mock import patch

    fixed_time = 1700000000.0

    with patch('network.protocol.datetime') as mock_dt:
        mock_dt.now.return_value.timestamp.return_value = fixed_time
        msg = create_message(MSG_VERSION, {})

    assert msg['timestamp'] == fixed_time


def test_create_message_checksum_is_sha256_hex():
    """El checksum es un hash SHA256 en formato hex (64 caracteres)."""
    msg = create_message(MSG_ADDR, {'peers': []})
    assert isinstance(msg['checksum'], str)
    assert len(msg['checksum']) == 64
    assert all(c in '0123456789abcdef' for c in msg['checksum'])


def test_create_message_empty_payload():
    """create_message funciona con payload vacío."""
    msg = create_message(MSG_GETBLOCKS, {})
    assert msg['payload'] == {}
    assert msg['checksum'] is not None


# ──────────────────────────────────────────────────────────
# Tests de validate_message
# ──────────────────────────────────────────────────────────

def test_validate_message_valid():
    """Mensaje creado con create_message es válido."""
    msg = create_message(MSG_TX, {'amount': 50})
    assert validate_message(msg) is True


def test_validate_message_missing_type():
    """Mensaje sin 'type' es inválido."""
    msg = create_message(MSG_PING, {})
    del msg['type']
    assert validate_message(msg) is False


def test_validate_message_missing_id():
    """Mensaje sin 'id' es inválido."""
    msg = create_message(MSG_PING, {})
    del msg['id']
    assert validate_message(msg) is False


def test_validate_message_missing_payload():
    """Mensaje sin 'payload' es inválido."""
    msg = create_message(MSG_PING, {})
    del msg['payload']
    assert validate_message(msg) is False


def test_validate_message_missing_checksum():
    """Mensaje sin 'checksum' es inválido."""
    msg = create_message(MSG_PING, {})
    del msg['checksum']
    assert validate_message(msg) is False


def test_validate_message_tampered_payload():
    """Mensaje con payload modificado falla el checksum."""
    msg = create_message(MSG_TX, {'amount': 10})
    msg['payload']['amount'] = 9999  # Modificar sin recalcular checksum
    assert validate_message(msg) is False


def test_validate_message_tampered_checksum():
    """Mensaje con checksum modificado es inválido."""
    msg = create_message(MSG_BLOCK, {'height': 5})
    msg['checksum'] = 'a' * 64  # Checksum falso
    assert validate_message(msg) is False


def test_validate_message_empty_dict():
    """Diccionario vacío es inválido."""
    assert validate_message({}) is False


def test_validate_message_all_types():
    """Mensajes de todos los tipos pasan la validación."""
    types = [
        MSG_VERSION, MSG_VERACK, MSG_PING, MSG_PONG,
        MSG_GETADDR, MSG_ADDR, MSG_TX,
        MSG_INV, MSG_GETBLOCKS, MSG_BLOCK,
    ]
    for msg_type in types:
        msg = create_message(msg_type, {'data': msg_type})
        assert validate_message(msg) is True, f"Falló para tipo: {msg_type}"


def test_checksum_deterministic():
    """El mismo payload siempre produce el mismo checksum."""
    payload = {'from': 'alice', 'to': 'bob', 'amount': 10}
    msg1 = create_message(MSG_TX, payload)
    msg2 = create_message(MSG_TX, payload)
    assert msg1['checksum'] == msg2['checksum']


def test_different_payloads_different_checksums():
    """Payloads distintos producen checksums distintos."""
    msg1 = create_message(MSG_TX, {'amount': 10})
    msg2 = create_message(MSG_TX, {'amount': 20})
    assert msg1['checksum'] != msg2['checksum']