"""
Tests para Transaction (transacciones firmadas)
"""

import pytest
import time
from core.wallet import Wallet
from core.transaction import Transaction


def test_create_transaction():
    """Transacción se crea correctamente"""
    tx = Transaction("alice", "bob", 10)
    
    assert tx.from_address == "alice"
    assert tx.to_address == "bob"
    assert tx.amount == 10
    assert tx.timestamp > 0
    assert tx.signature is None  # No firmada todavía


def test_transaction_hash():
    """Hash de transacción es consistente"""
    tx = Transaction("alice", "bob", 10)
    
    hash1 = tx.hash()
    hash2 = tx.hash()
    
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 = 32 bytes = 64 hex chars


def test_different_transactions_different_hashes():
    """Transacciones diferentes tienen hashes diferentes"""
    tx1 = Transaction("alice", "bob", 10)
    tx2 = Transaction("alice", "charlie", 10)
    
    assert tx1.hash() != tx2.hash()


def test_sign_transaction():
    """Transacción se puede firmar"""
    wallet = Wallet()
    tx = Transaction(wallet.address, "bob", 10)
    
    tx.sign(wallet)
    
    assert tx.signature is not None
    assert tx.public_key is not None
    assert len(tx.signature) > 0


def test_cannot_sign_with_wrong_wallet():
    """No se puede firmar con wallet incorrecta"""
    alice = Wallet()
    bob = Wallet()
    
    tx = Transaction(alice.address, "recipient", 10)
    
    # Intentar firmar con wallet de Bob (debe fallar)
    with pytest.raises(AssertionError):
        tx.sign(bob)


def test_valid_signed_transaction():
    """Transacción firmada correctamente es válida"""
    alice = Wallet()
    bob = Wallet()
    
    tx = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    
    assert tx.is_valid()


def test_invalid_transaction_no_signature():
    """Transacción sin firma es inválida"""
    tx = Transaction("alice", "bob", 10)
    
    # No firmar
    
    assert not tx.is_valid()


def test_invalid_transaction_tampered_amount():
    """Transacción firmada y luego modificada es inválida"""
    alice = Wallet()
    bob = Wallet()
    
    tx = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    
    # Modificar después de firmar
    tx.amount = 100
    
    assert not tx.is_valid()


def test_invalid_transaction_zero_amount():
    """Transacción con amount <= 0 es inválida"""
    alice = Wallet()
    bob = Wallet()
    
    tx = Transaction(alice.address, bob.address, 0)
    tx.sign(alice)
    
    assert not tx.is_valid()


def test_coinbase_transaction_valid():
    """Transacción coinbase es válida sin firma"""
    tx = Transaction("COINBASE", "miner_address", 50)
    
    # No firmar (coinbase no requiere firma)
    
    assert tx.is_valid()


def test_transaction_to_dict():
    """Transacción se serializa correctamente"""
    alice = Wallet()
    tx = Transaction(alice.address, "bob", 10)
    tx.sign(alice)
    
    data = tx.to_dict()
    
    assert data['from'] == alice.address
    assert data['to'] == "bob"
    assert data['amount'] == 10
    assert 'signature' in data
    assert 'public_key' in data


def test_transaction_from_dict():
    """Transacción se deserializa correctamente"""
    alice = Wallet()
    tx1 = Transaction(alice.address, "bob", 10)
    tx1.sign(alice)
    
    # Serializar
    data = tx1.to_dict()
    
    # Deserializar
    tx2 = Transaction.from_dict(data)
    
    assert tx2.from_address == tx1.from_address
    assert tx2.to_address == tx1.to_address
    assert tx2.amount == tx1.amount
    assert tx2.signature == tx1.signature
    assert tx2.is_valid()


def test_transaction_hash_excludes_signature():
    """Hash de transacción no cambia al agregar firma"""
    alice = Wallet()
    tx = Transaction(alice.address, "bob", 10)
    
    hash_before = tx.hash()
    
    tx.sign(alice)
    
    hash_after = tx.hash()
    
    # Hash debe ser el mismo (no incluye signature)
    assert hash_before == hash_after