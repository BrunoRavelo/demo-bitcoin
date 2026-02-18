"""
Tests para Wallet (criptografía EdDSA Ed25519)
"""

import pytest
from core.wallet import Wallet


def test_create_wallet():
    wallet = Wallet()
    
    assert wallet.private_key is not None
    assert wallet.public_key is not None
    assert wallet.address is not None
    assert 25 <= len(wallet.address) <= 34  # Base58Check variable
    assert wallet.address[0] == '1'          # Mainnet siempre empieza con '1'
    assert isinstance(wallet.address, str)


def test_wallets_have_different_addresses():
    """Cada wallet tiene dirección única"""
    wallet1 = Wallet()
    wallet2 = Wallet()
    
    assert wallet1.address != wallet2.address


def test_get_public_key_hex():
    """Public key se puede exportar en hex"""
    wallet = Wallet()
    
    pub_hex = wallet.get_public_key_hex()
    
    assert isinstance(pub_hex, str)
    assert len(pub_hex) > 0
    # Ed25519: public key = 32 bytes = 64 caracteres hex
    assert len(pub_hex) == 64


def test_sign_transaction():
    """Wallet puede firmar datos"""
    wallet = Wallet()
    data = {"test": "data", "amount": 10}
    
    signature = wallet.sign_transaction(data)
    
    assert isinstance(signature, str)
    assert len(signature) > 0
    # Ed25519: firma = 64 bytes = 128 caracteres hex
    assert len(signature) == 128


def test_verify_valid_signature():
    """Firma válida se verifica correctamente"""
    wallet = Wallet()
    data = {"from": wallet.address, "to": "recipient", "amount": 10}
    
    # Firmar
    signature = wallet.sign_transaction(data)
    
    # Verificar
    is_valid = Wallet.verify_signature(data, wallet.get_public_key_hex(), signature)
    
    assert is_valid


def test_verify_invalid_signature_wrong_data():
    """Firma no valida si se modifican los datos"""
    wallet = Wallet()
    data = {"from": wallet.address, "to": "recipient", "amount": 10}
    
    # Firmar
    signature = wallet.sign_transaction(data)
    
    # Modificar datos
    data['amount'] = 100
    
    # Verificar (debe fallar)
    is_valid = Wallet.verify_signature(data, wallet.get_public_key_hex(), signature)
    
    assert not is_valid


def test_verify_invalid_signature_wrong_pubkey():
    """Firma no valida si se usa public key incorrecta"""
    wallet1 = Wallet()
    wallet2 = Wallet()
    data = {"from": wallet1.address, "to": "recipient", "amount": 10}
    
    # wallet1 firma
    signature = wallet1.sign_transaction(data)
    
    # Intentar verificar con public key de wallet2
    is_valid = Wallet.verify_signature(data, wallet2.get_public_key_hex(), signature)
    
    assert not is_valid


def test_verify_invalid_signature_corrupted():
    """Firma corrupta no valida"""
    wallet = Wallet()
    data = {"from": wallet.address, "to": "recipient", "amount": 10}
    
    signature = wallet.sign_transaction(data)
    
    # Corromper signature (cambiar últimos 4 caracteres)
    corrupted_sig = signature[:-4] + "0000"
    
    is_valid = Wallet.verify_signature(data, wallet.get_public_key_hex(), corrupted_sig)
    
    assert not is_valid


def test_deterministic_signatures():
    """Ed25519 genera firmas determinísticas (mismo mensaje = misma firma)"""
    wallet = Wallet()
    data = {"message": "test deterministic"}
    
    # Firmar el mismo mensaje dos veces
    signature1 = wallet.sign_transaction(data)
    signature2 = wallet.sign_transaction(data)
    
    # Ed25519 es determinístico: misma firma
    assert signature1 == signature2


def test_different_messages_different_signatures():
    """Mensajes diferentes producen firmas diferentes"""
    wallet = Wallet()
    
    data1 = {"message": "first"}
    data2 = {"message": "second"}
    
    signature1 = wallet.sign_transaction(data1)
    signature2 = wallet.sign_transaction(data2)
    
    assert signature1 != signature2