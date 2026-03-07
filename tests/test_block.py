"""
Tests para Block y BlockHeader
"""

import pytest
import time
from core.block import Block, BlockHeader
from core.transaction import Transaction
from core.wallet import Wallet
from core.merkle import MerkleTree
from core.pow import ProofOfWork


def create_dummy_tx(seed: int):
    """Helper: crea transacción dummy para testing"""
    wallet = Wallet()
    tx = Transaction(f"from_{seed}", f"to_{seed}", seed)
    tx.timestamp = seed
    return tx


def test_create_block_header():
    """BlockHeader se crea correctamente"""
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root='a' * 64,
        timestamp=1234567890,
        difficulty=4,
        nonce=0
    )
    
    assert header.prev_hash == '0' * 64
    assert header.merkle_root == 'a' * 64
    assert header.timestamp == 1234567890
    assert header.difficulty == 4
    assert header.nonce == 0


def test_block_header_hash():
    """Hash de BlockHeader es determinístico"""
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root='a' * 64,
        timestamp=1234567890,
        difficulty=4,
        nonce=42
    )
    
    hash1 = header.hash()
    hash2 = header.hash()
    
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 = 64 caracteres hex


def test_block_header_hash_changes_with_nonce():
    """Hash cambia cuando cambia el nonce"""
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root='a' * 64,
        timestamp=1234567890,
        difficulty=4,
        nonce=0
    )
    
    hash1 = header.hash()
    
    header.nonce = 1
    hash2 = header.hash()
    
    assert hash1 != hash2


def test_block_header_serialization():
    """BlockHeader se serializa y deserializa correctamente"""
    header1 = BlockHeader(
        prev_hash='0' * 64,
        merkle_root='a' * 64,
        timestamp=1234567890,
        difficulty=4,
        nonce=42
    )
    
    # Serializar
    data = header1.to_dict()
    
    # Deserializar
    header2 = BlockHeader.from_dict(data)
    
    assert header2.prev_hash == header1.prev_hash
    assert header2.merkle_root == header1.merkle_root
    assert header2.timestamp == header1.timestamp
    assert header2.difficulty == header1.difficulty
    assert header2.nonce == header1.nonce
    assert header2.hash() == header1.hash()


def test_create_block():
    """Block se crea correctamente"""
    txs = [create_dummy_tx(i) for i in range(3)]
    merkle = MerkleTree(txs)
    
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=time.time(),
        difficulty=3,
        nonce=0
    )
    
    block = Block(header, txs)
    
    assert block.header == header
    assert len(block.transactions) == 3
    assert block.hash == header.hash()


def test_block_validate_merkle_root_valid():
    """Merkle root válido pasa validación"""
    txs = [create_dummy_tx(i) for i in range(3)]
    merkle = MerkleTree(txs)
    
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=time.time(),
        difficulty=3,
        nonce=0
    )
    
    block = Block(header, txs)
    
    assert block.validate_merkle_root()


def test_block_validate_merkle_root_invalid():
    """Merkle root inválido falla validación"""
    txs = [create_dummy_tx(i) for i in range(3)]
    
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root='wrong_merkle_root' + 'a' * 46,  # 64 chars pero incorrecto
        timestamp=time.time(),
        difficulty=3,
        nonce=0
    )
    
    block = Block(header, txs)
    
    assert not block.validate_merkle_root()


def test_block_validate_pow_valid():
    """Bloque con PoW válido pasa validación"""
    txs = [create_dummy_tx(i) for i in range(2)]
    merkle = MerkleTree(txs)
    
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=time.time(),
        difficulty=3,
        nonce=0
    )
    
    # Minar para encontrar nonce válido
    pow_solver = ProofOfWork(header, difficulty=3)
    nonce = pow_solver.mine()
    header.nonce = nonce
    
    block = Block(header, txs)
    
    assert block.validate_pow()


def test_block_validate_pow_invalid():
    """Bloque sin PoW correcto falla validación"""
    txs = [create_dummy_tx(i) for i in range(2)]
    merkle = MerkleTree(txs)
    
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=time.time(),
        difficulty=4,
        nonce=12345  # Nonce aleatorio (probablemente inválido)
    )
    
    block = Block(header, txs)
    
    # Muy probablemente no cumpla difficulty 4
    assert not block.validate_pow()


def test_block_validate_transactions_valid():
    """Bloque con TXs válidas pasa validación"""
    # Crear TXs firmadas
    alice = Wallet()
    bob = Wallet()
    
    tx = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    
    merkle = MerkleTree([tx])
    
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=time.time(),
        difficulty=3,
        nonce=0
    )
    
    block = Block(header, [tx])
    
    assert block.validate_transactions()


def test_block_validate_transactions_invalid():
    """Bloque con TX sin firma falla validación"""
    tx = Transaction("alice", "bob", 10)
    # NO firmar
    
    merkle = MerkleTree([tx])
    
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=time.time(),
        difficulty=3,
        nonce=0
    )
    
    block = Block(header, [tx])
    
    assert not block.validate_transactions()


def test_block_serialization():
    """Block se serializa y deserializa correctamente"""
    alice = Wallet()
    bob = Wallet()
    
    tx = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    
    merkle = MerkleTree([tx])
    
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=1234567890,
        difficulty=3,
        nonce=42
    )
    
    block1 = Block(header, [tx])
    
    # Serializar
    data = block1.to_dict()
    
    # Deserializar
    block2 = Block.from_dict(data)
    
    assert block2.hash == block1.hash
    assert len(block2.transactions) == len(block1.transactions)
    assert block2.header.nonce == block1.header.nonce


def test_block_hash_immutable():
    """Hash del bloque es inmutable (no cambia después de crear)"""
    txs = [create_dummy_tx(i) for i in range(2)]
    merkle = MerkleTree(txs)
    
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=time.time(),
        difficulty=3,
        nonce=42
    )
    
    block = Block(header, txs)
    
    hash1 = block.hash
    hash2 = block.hash
    
    assert hash1 == hash2


def test_block_tampering_detected():
    """Modificar TX después de crear bloque invalida Merkle"""
    txs = [create_dummy_tx(i) for i in range(2)]
    merkle = MerkleTree(txs)
    
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=time.time(),
        difficulty=3,
        nonce=0
    )
    
    block = Block(header, txs)
    
    # Merkle válido inicialmente
    assert block.validate_merkle_root()
    
    # Modificar TX
    block.transactions[0].amount = 999999
    
    # Merkle ya no es válido
    assert not block.validate_merkle_root()