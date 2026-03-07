"""
Tests para Proof of Work
"""

import pytest
import time
from core.pow import ProofOfWork


# Mock simple de BlockHeader para testing
class MockBlockHeader:
    def __init__(self):
        self.prev_hash = '0' * 64
        self.merkle_root = 'a' * 64
        self.timestamp = 1234567890
        self.nonce = 0
        self.difficulty = 3
    
    def hash(self):
        import hashlib
        import json
        
        data = {
            'prev_hash': self.prev_hash,
            'merkle_root': self.merkle_root,
            'timestamp': self.timestamp,
            'nonce': self.nonce,
            'difficulty': self.difficulty
        }
        
        header_str = json.dumps(data, sort_keys=True)
        
        # Double SHA256 (como Bitcoin)
        hash1 = hashlib.sha256(header_str.encode()).digest()
        hash2 = hashlib.sha256(hash1).hexdigest()
        
        return hash2


def test_pow_difficulty_3():
    """Minar con difficulty 3 (rápido)"""
    header = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=3)
    
    start = time.time()
    nonce = pow_solver.mine()
    elapsed = time.time() - start
    
    # Verificaciones
    assert nonce >= 0
    assert header.hash().startswith('000')
    assert elapsed < 10  # No debe tardar más de 10 segundos


def test_pow_difficulty_4():
    """Minar con difficulty 4 (moderado)"""
    header = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=4)
    
    start = time.time()
    nonce = pow_solver.mine()
    elapsed = time.time() - start
    
    # Verificaciones
    assert nonce >= 0
    assert header.hash().startswith('0000')
    assert elapsed < 30  # No debe tardar más de 30 segundos


def test_pow_validate_correct_nonce():
    """Validar nonce correcto"""
    header = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=3)
    
    # Minar
    nonce = pow_solver.mine()
    
    # Validar
    assert pow_solver.validate(nonce)


def test_pow_validate_incorrect_nonce():
    """Validar nonce incorrecto"""
    header = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=4)
    
    # Nonce aleatorio (probablemente inválido)
    header.nonce = 12345
    
    # Validar (debería fallar)
    assert not pow_solver.validate(12345)


def test_pow_deterministic():
    """Mismo header → mismo nonce ganador"""
    header1 = MockBlockHeader()
    header1.timestamp = 1111111111  # Timestamp fijo
    
    header2 = MockBlockHeader()
    header2.timestamp = 1111111111  # Mismo timestamp
    
    pow1 = ProofOfWork(header1, difficulty=3)
    pow2 = ProofOfWork(header2, difficulty=3)
    
    nonce1 = pow1.mine()
    nonce2 = pow2.mine()
    
    # Mismo nonce porque header es idéntico
    assert nonce1 == nonce2


def test_pow_different_header_different_nonce():
    """Headers diferentes → nonces diferentes"""
    header1 = MockBlockHeader()
    header1.timestamp = 1111111111
    
    header2 = MockBlockHeader()
    header2.timestamp = 2222222222  # Timestamp diferente
    
    pow1 = ProofOfWork(header1, difficulty=3)
    pow2 = ProofOfWork(header2, difficulty=3)
    
    nonce1 = pow1.mine()
    nonce2 = pow2.mine()
    
    # Nonces diferentes porque headers son diferentes
    assert nonce1 != nonce2


def test_pow_hash_has_enough_zeros():
    """Hash resultante tiene al menos la cantidad de ceros requerida"""
    header = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=4)
    
    nonce = pow_solver.mine()
    header.nonce = nonce
    
    block_hash = header.hash()
    
    # Contar ceros al inicio
    zero_count = 0
    for char in block_hash:
        if char == '0':
            zero_count += 1
        else:
            break
    
    # Debe tener al menos 4 ceros
    assert zero_count >= 4


def test_pow_more_zeros_than_minimum_still_valid():
    """Hash con MÁS ceros del mínimo sigue siendo válido"""
    header = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=3)
    
    # Buscar hasta encontrar uno (podría tener 3, 4, 5+ ceros)
    nonce = pow_solver.mine()
    
    # Validar con difficulty original
    assert pow_solver.validate(nonce)
    
    # También debería ser válido con difficulty menor
    pow_solver_lower = ProofOfWork(header, difficulty=2)
    assert pow_solver_lower.validate(nonce)