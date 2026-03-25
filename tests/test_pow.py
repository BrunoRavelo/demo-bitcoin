"""
Tests para Proof of Work — Sprint 9.2
Actualizado para target numérico (int de 256 bits).
"""

import threading
import time
import pytest
from core.pow import ProofOfWork
from config import MAX_TARGET


# Targets de prueba
EASY_TARGET   = MAX_TARGET // 16          # ~1 cero hex  — instantáneo
MEDIUM_TARGET = MAX_TARGET // 16**3       # ~3 ceros hex — muy rápido
HARD_TARGET   = MAX_TARGET // 16**5       # ~5 ceros hex — algunos segundos


class MockBlockHeader:
    """Header mínimo para testing — replica BlockHeader.hash()."""
    def __init__(self):
        self.prev_hash   = '0' * 64
        self.merkle_root = 'a' * 64
        self.timestamp   = 1234567890
        self.nonce       = 0
        self.target      = EASY_TARGET

    def hash(self):
        import hashlib, json
        data   = {
            'prev_hash':   self.prev_hash,
            'merkle_root': self.merkle_root,
            'timestamp':   self.timestamp,
            'target':      self.target,
            'nonce':       self.nonce,
        }
        s      = json.dumps(data, sort_keys=True)
        hash1  = hashlib.sha256(s.encode()).digest()
        return hashlib.sha256(hash1).hexdigest()


# ──────────────────────────────────────────────────────────
# Tests de minado básico
# ──────────────────────────────────────────────────────────

def test_pow_easy_target():
    """Mina con target fácil — hash resultante < target."""
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, EASY_TARGET)
    nonce      = pow_solver.mine()
    assert nonce is not None
    assert int(header.hash(), 16) < EASY_TARGET


def test_pow_medium_target():
    """Mina con target medio en tiempo razonable."""
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, MEDIUM_TARGET)
    start      = time.time()
    nonce      = pow_solver.mine()
    elapsed    = time.time() - start
    assert nonce is not None
    assert int(header.hash(), 16) < MEDIUM_TARGET
    assert elapsed < 30


def test_pow_validate_correct_nonce():
    """Nonce encontrado pasa validate()."""
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, EASY_TARGET)
    nonce      = pow_solver.mine()
    assert pow_solver.validate(nonce)


def test_pow_validate_incorrect_nonce():
    """Nonce arbitrario no cumple target muy estricto."""
    header     = MockBlockHeader()
    hard       = 1  # Target mínimo — imposible con nonce 12345
    pow_solver = ProofOfWork(header, hard)
    assert not pow_solver.validate(12345)


def test_pow_deterministic():
    """Mismo header → mismo nonce ganador."""
    header1           = MockBlockHeader()
    header1.timestamp = 1111111111
    header2           = MockBlockHeader()
    header2.timestamp = 1111111111

    pow1 = ProofOfWork(header1, EASY_TARGET)
    pow2 = ProofOfWork(header2, EASY_TARGET)
    assert pow1.mine() == pow2.mine()


def test_pow_different_header_different_nonce():
    """Headers diferentes producen nonces diferentes."""
    header1           = MockBlockHeader()
    header1.timestamp = 1111111111
    header2           = MockBlockHeader()
    header2.timestamp = 2222222222

    pow1 = ProofOfWork(header1, EASY_TARGET)
    pow2 = ProofOfWork(header2, EASY_TARGET)
    assert pow1.mine() != pow2.mine()


def test_pow_hash_below_target():
    """Hash resultante es estrictamente menor que el target."""
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, MEDIUM_TARGET)
    nonce      = pow_solver.mine()
    header.nonce = nonce
    assert int(header.hash(), 16) < MEDIUM_TARGET


def test_pow_easier_target_also_valid():
    """Un nonce válido para target estricto es válido para target relajado."""
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, MEDIUM_TARGET)
    nonce      = pow_solver.mine()

    # EASY_TARGET > MEDIUM_TARGET → también válido
    pow_easier = ProofOfWork(header, EASY_TARGET)
    assert pow_easier.validate(nonce)


# ──────────────────────────────────────────────────────────
# Tests de cancelación
# ──────────────────────────────────────────────────────────

def test_mine_returns_none_when_stop_event_set_before():
    """Si stop_event ya está activo, mine() retorna None inmediatamente."""
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, HARD_TARGET)
    stop_event = threading.Event()
    stop_event.set()
    assert pow_solver.mine(stop_event=stop_event) is None


def test_mine_cancels_mid_execution():
    """mine() se cancela mientras está corriendo."""
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, HARD_TARGET)
    stop_event = threading.Event()
    result     = [None]

    def mine_thread():
        result[0] = pow_solver.mine(stop_event=stop_event)

    t = threading.Thread(target=mine_thread)
    t.start()
    time.sleep(0.1)
    stop_event.set()
    t.join(timeout=5)

    assert result[0] is None


def test_mine_without_stop_event_works_normally():
    """mine() sin stop_event funciona igual que antes."""
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, EASY_TARGET)
    nonce      = pow_solver.mine(stop_event=None)
    assert nonce is not None
    assert pow_solver.validate(nonce)


def test_mine_completes_before_cancellation():
    """Si mine() termina antes de activar stop_event, retorna nonce válido."""
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, EASY_TARGET)
    stop_event = threading.Event()
    nonce      = pow_solver.mine(stop_event=stop_event)
    assert nonce is not None
    assert pow_solver.validate(nonce)


def test_stop_event_cleared_for_reuse():
    """clear() permite minar de nuevo tras cancelación."""
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, EASY_TARGET)
    stop_event = threading.Event()

    stop_event.set()
    assert pow_solver.mine(stop_event=stop_event) is None

    stop_event.clear()
    result = pow_solver.mine(stop_event=stop_event)
    assert result is not None
