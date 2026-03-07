"""
Tests para Merkle Tree
"""

import pytest
from core.merkle import MerkleTree
from core.transaction import Transaction
from core.wallet import Wallet


def create_dummy_tx(seed: int):
    """Helper: crea transacción dummy para testing"""
    wallet = Wallet()
    tx = Transaction(f"from_{seed}", f"to_{seed}", seed)
    tx.timestamp = seed  # Timestamp fijo para determinismo
    return tx


def test_merkle_root_single_transaction():
    """Merkle tree con 1 transacción"""
    tx = create_dummy_tx(1)
    merkle = MerkleTree([tx])
    
    root = merkle.get_root()
    
    assert root is not None
    assert len(root) == 64  # SHA256 = 64 caracteres hex
    assert isinstance(root, str)


def test_merkle_root_deterministic():
    """Merkle root es determinístico (mismo input = mismo output)"""
    tx1 = create_dummy_tx(1)
    tx2 = create_dummy_tx(2)
    
    merkle1 = MerkleTree([tx1, tx2])
    merkle2 = MerkleTree([tx1, tx2])
    
    assert merkle1.get_root() == merkle2.get_root()


def test_merkle_root_changes_with_data():
    """Merkle root cambia si cambian las transacciones"""
    tx1 = create_dummy_tx(1)
    tx2 = create_dummy_tx(2)
    tx3 = create_dummy_tx(3)
    
    merkle1 = MerkleTree([tx1, tx2])
    merkle2 = MerkleTree([tx1, tx3])
    
    assert merkle1.get_root() != merkle2.get_root()


def test_merkle_odd_number_of_transactions():
    """Merkle tree con número impar de transacciones (duplica última)"""
    txs = [create_dummy_tx(i) for i in range(3)]
    merkle = MerkleTree(txs)
    
    root = merkle.get_root()
    
    assert root is not None
    assert len(root) == 64


def test_merkle_even_number_of_transactions():
    """Merkle tree con número par de transacciones"""
    txs = [create_dummy_tx(i) for i in range(4)]
    merkle = MerkleTree(txs)
    
    root = merkle.get_root()
    
    assert root is not None
    assert len(root) == 64


def test_merkle_empty_transactions():
    """Merkle tree vacío retorna hash de ceros"""
    merkle = MerkleTree([])
    
    root = merkle.get_root()
    
    assert root == '0' * 64


def test_merkle_tree_structure():
    """Verificar estructura del árbol (niveles)"""
    txs = [create_dummy_tx(i) for i in range(4)]
    merkle = MerkleTree(txs)
    
    # Con 4 TXs:
    # Nivel 0: 4 hashes (hojas)
    # Nivel 1: 2 hashes (H12, H34)
    # Nivel 2: 1 hash (root)
    
    assert len(merkle.tree) == 3
    assert len(merkle.tree[0]) == 4  # Hojas
    assert len(merkle.tree[1]) == 2  # Nivel medio
    assert len(merkle.tree[2]) == 1  # Raíz


def test_merkle_order_matters():
    """Orden de transacciones afecta el Merkle root"""
    tx1 = create_dummy_tx(1)
    tx2 = create_dummy_tx(2)
    
    merkle1 = MerkleTree([tx1, tx2])
    merkle2 = MerkleTree([tx2, tx1])  # Orden invertido
    
    # Roots deben ser diferentes
    assert merkle1.get_root() != merkle2.get_root()


def test_merkle_proof_generation():
    """Generar prueba Merkle para una transacción"""
    txs = [create_dummy_tx(i) for i in range(4)]
    merkle = MerkleTree(txs)
    
    # Obtener prueba para TX en índice 0
    proof = merkle.get_proof(0)
    
    assert proof is not None
    assert isinstance(proof, list)
    assert len(proof) > 0


def test_merkle_proof_verification():
    """Verificar prueba Merkle"""
    txs = [create_dummy_tx(i) for i in range(4)]
    merkle = MerkleTree(txs)
    
    # Prueba para primera TX
    tx_hash = merkle.hash_transaction(txs[0])
    proof = merkle.get_proof(0)
    merkle_root = merkle.get_root()
    
    # Verificar
    is_valid = MerkleTree.verify_proof(tx_hash, merkle_root, proof)
    
    assert is_valid


def test_merkle_proof_invalid():
    """Prueba Merkle inválida debe fallar"""
    txs = [create_dummy_tx(i) for i in range(4)]
    merkle = MerkleTree(txs)
    
    # TX que NO está en el árbol
    fake_tx = create_dummy_tx(999)
    fake_tx_hash = merkle.hash_transaction(fake_tx)
    
    # Usar prueba de otra TX
    proof = merkle.get_proof(0)
    merkle_root = merkle.get_root()
    
    # Verificar (debe fallar)
    is_valid = MerkleTree.verify_proof(fake_tx_hash, merkle_root, proof)
    
    assert not is_valid