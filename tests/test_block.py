"""
Tests para Block y BlockHeader — Sprint 9.2
Actualizado para target numérico en lugar de difficulty.
"""

import pytest
import time
from core.block import Block, BlockHeader
from core.transaction import Transaction
from core.wallet import Wallet
from core.merkle import MerkleTree
from core.pow import ProofOfWork
from config import MAX_TARGET, INITIAL_TARGET


# Target fácil para tests (equivale a dificultad ~1 zero)
EASY_TARGET = MAX_TARGET // 16


def create_dummy_tx(seed: int):
    """Helper: crea transacción dummy para testing."""
    tx = Transaction(f"from_{seed}", f"to_{seed}", seed)
    tx.timestamp = seed
    return tx


def test_create_block_header():
    """BlockHeader se crea correctamente."""
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root='a' * 64,
        timestamp=1234567890,
        target=EASY_TARGET,
        nonce=0,
    )
    assert header.prev_hash   == '0' * 64
    assert header.merkle_root == 'a' * 64
    assert header.timestamp   == 1234567890
    assert header.target      == EASY_TARGET
    assert header.nonce       == 0


def test_block_header_hash():
    """Hash de BlockHeader es determinístico y tiene 64 chars."""
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root='a' * 64,
        timestamp=1234567890,
        target=EASY_TARGET,
        nonce=42,
    )
    assert header.hash() == header.hash()
    assert len(header.hash()) == 64


def test_block_header_hash_changes_with_nonce():
    """Hash cambia cuando cambia el nonce."""
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root='a' * 64,
        timestamp=1234567890,
        target=EASY_TARGET,
        nonce=0,
    )
    hash1         = header.hash()
    header.nonce  = 1
    assert hash1 != header.hash()


def test_block_header_serialization():
    """BlockHeader se serializa y deserializa correctamente."""
    header1 = BlockHeader(
        prev_hash='0' * 64,
        merkle_root='a' * 64,
        timestamp=1234567890,
        target=EASY_TARGET,
        nonce=42,
    )
    header2 = BlockHeader.from_dict(header1.to_dict())

    assert header2.prev_hash   == header1.prev_hash
    assert header2.merkle_root == header1.merkle_root
    assert header2.timestamp   == header1.timestamp
    assert header2.target      == header1.target
    assert header2.nonce       == header1.nonce
    assert header2.hash()      == header1.hash()


def test_create_block():
    """Block se crea correctamente."""
    txs    = [create_dummy_tx(i) for i in range(3)]
    merkle = MerkleTree(txs)
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=time.time(),
        target=EASY_TARGET,
        nonce=0,
    )
    block = Block(header, txs)
    assert block.header == header
    assert len(block.transactions) == 3
    assert block.hash == header.hash()


def test_block_validate_merkle_root_valid():
    """Merkle root válido pasa validación."""
    txs    = [create_dummy_tx(i) for i in range(3)]
    merkle = MerkleTree(txs)
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=time.time(),
        target=EASY_TARGET,
        nonce=0,
    )
    assert Block(header, txs).validate_merkle_root()


def test_block_validate_merkle_root_invalid():
    """Merkle root incorrecto falla validación."""
    txs    = [create_dummy_tx(i) for i in range(3)]
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root='wrong' + 'a' * 59,
        timestamp=time.time(),
        target=EASY_TARGET,
        nonce=0,
    )
    assert not Block(header, txs).validate_merkle_root()


def test_block_validate_pow_valid():
    """Bloque con PoW válido pasa validación."""
    txs    = [create_dummy_tx(i) for i in range(2)]
    merkle = MerkleTree(txs)
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=time.time(),
        target=EASY_TARGET,
        nonce=0,
    )
    pow_solver   = ProofOfWork(header, EASY_TARGET)
    header.nonce = pow_solver.mine()
    assert Block(header, txs).validate_pow()


def test_block_validate_pow_invalid():
    """Bloque sin PoW correcto falla validación — target muy estricto."""
    txs    = [create_dummy_tx(i) for i in range(2)]
    merkle = MerkleTree(txs)
    # Target muy bajo (casi imposible que nonce=12345 lo cumpla)
    hard_target = 1
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=time.time(),
        target=hard_target,
        nonce=12345,
    )
    assert not Block(header, txs).validate_pow()


def test_block_validate_transactions_valid():
    """Bloque con TXs válidas pasa validación."""
    alice = Wallet()
    bob   = Wallet()
    tx    = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)

    merkle = MerkleTree([tx])
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=time.time(),
        target=EASY_TARGET,
        nonce=0,
    )
    assert Block(header, [tx]).validate_transactions()


def test_block_validate_transactions_invalid():
    """Bloque con TX sin firma falla validación."""
    tx     = Transaction("alice", "bob", 10)
    merkle = MerkleTree([tx])
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=time.time(),
        target=EASY_TARGET,
        nonce=0,
    )
    assert not Block(header, [tx]).validate_transactions()


def test_block_serialization():
    """Block se serializa y deserializa correctamente."""
    alice  = Wallet()
    bob    = Wallet()
    tx     = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    merkle = MerkleTree([tx])
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=1234567890,
        target=EASY_TARGET,
        nonce=42,
    )
    block1 = Block(header, [tx])
    block2 = Block.from_dict(block1.to_dict())

    assert block2.hash == block1.hash
    assert block2.header.target == block1.header.target
    assert block2.header.nonce  == block1.header.nonce


def test_block_hash_immutable():
    """Hash del bloque es consistente."""
    txs    = [create_dummy_tx(i) for i in range(2)]
    merkle = MerkleTree(txs)
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=time.time(),
        target=EASY_TARGET,
        nonce=42,
    )
    block = Block(header, txs)
    assert block.hash == block.hash


def test_block_tampering_detected():
    """Modificar TX después de crear el bloque invalida Merkle."""
    txs    = [create_dummy_tx(i) for i in range(2)]
    merkle = MerkleTree(txs)
    header = BlockHeader(
        prev_hash='0' * 64,
        merkle_root=merkle.get_root(),
        timestamp=time.time(),
        target=EASY_TARGET,
        nonce=0,
    )
    block = Block(header, txs)
    assert block.validate_merkle_root()

    block.transactions[0].amount = 999999
    assert not block.validate_merkle_root()
