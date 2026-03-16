"""
Tests para Proof of Work
Cubre mine(), validate() y cancelación via threading.Event
"""

import threading
import time
import pytest
from core.pow import ProofOfWork


class MockBlockHeader:
    """Header mínimo para testing — idéntico al de test_pow.py original."""
    def __init__(self):
        self.prev_hash   = '0' * 64
        self.merkle_root = 'a' * 64
        self.timestamp   = 1234567890
        self.nonce       = 0
        self.difficulty  = 3

    def hash(self):
        import hashlib, json
        data = {
            'prev_hash':   self.prev_hash,
            'merkle_root': self.merkle_root,
            'timestamp':   self.timestamp,
            'nonce':       self.nonce,
            'difficulty':  self.difficulty,
        }
        s      = json.dumps(data, sort_keys=True)
        hash1  = hashlib.sha256(s.encode()).digest()
        return hashlib.sha256(hash1).hexdigest()


# ──────────────────────────────────────────────────────────
# Tests originales (sin cambios)
# ──────────────────────────────────────────────────────────

def test_pow_difficulty_3():
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=3)
    nonce      = pow_solver.mine()
    assert nonce is not None
    assert nonce >= 0
    assert header.hash().startswith('000')


def test_pow_difficulty_4():
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=4)
    start      = time.time()
    nonce      = pow_solver.mine()
    elapsed    = time.time() - start
    assert nonce is not None
    assert header.hash().startswith('0000')
    assert elapsed < 60


def test_pow_validate_correct_nonce():
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=3)
    nonce      = pow_solver.mine()
    assert pow_solver.validate(nonce)


def test_pow_validate_incorrect_nonce():
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=4)
    assert not pow_solver.validate(12345)


def test_pow_deterministic():
    header1            = MockBlockHeader()
    header1.timestamp  = 1111111111
    header2            = MockBlockHeader()
    header2.timestamp  = 1111111111

    pow1  = ProofOfWork(header1, difficulty=3)
    pow2  = ProofOfWork(header2, difficulty=3)
    assert pow1.mine() == pow2.mine()


def test_pow_different_header_different_nonce():
    header1           = MockBlockHeader()
    header1.timestamp = 1111111111
    header2           = MockBlockHeader()
    header2.timestamp = 2222222222

    pow1 = ProofOfWork(header1, difficulty=3)
    pow2 = ProofOfWork(header2, difficulty=3)
    assert pow1.mine() != pow2.mine()


def test_pow_hash_has_enough_zeros():
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=4)
    nonce      = pow_solver.mine()
    header.nonce = nonce

    zeros = 0
    for c in header.hash():
        if c == '0':
            zeros += 1
        else:
            break
    assert zeros >= 4


def test_pow_more_zeros_than_minimum_still_valid():
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=3)
    nonce      = pow_solver.mine()

    assert pow_solver.validate(nonce)

    pow_lower = ProofOfWork(header, difficulty=2)
    assert pow_lower.validate(nonce)


# ──────────────────────────────────────────────────────────
# Tests de cancelación (Sprint 4.3)
# ──────────────────────────────────────────────────────────

def test_mine_returns_none_when_stop_event_set_before():
    """Si el stop_event ya está activo, mine() retorna None inmediatamente."""
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=4)

    stop_event = threading.Event()
    stop_event.set()  # Activar ANTES de llamar mine()

    result = pow_solver.mine(stop_event=stop_event)

    assert result is None


def test_mine_cancels_mid_execution():
    """
    mine() se cancela mientras está corriendo.

    Lanza el minado en un thread y activa el stop_event
    después de 100ms. El resultado debe ser None.
    """
    header     = MockBlockHeader()
    header.difficulty = 5  # Difficulty alta para que tarde lo suficiente
    pow_solver = ProofOfWork(header, difficulty=5)

    stop_event = threading.Event()
    result     = [None]  # Lista para capturar resultado del thread

    def mine_thread():
        result[0] = pow_solver.mine(stop_event=stop_event)

    t = threading.Thread(target=mine_thread)
    t.start()

    # Dejar correr 100ms y luego cancelar
    time.sleep(0.1)
    stop_event.set()

    t.join(timeout=5)

    assert result[0] is None


def test_mine_without_stop_event_works_normally():
    """mine() sin stop_event funciona igual que antes."""
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=3)

    # Sin stop_event — comportamiento original
    nonce = pow_solver.mine(stop_event=None)

    assert nonce is not None
    assert nonce >= 0
    assert header.hash().startswith('000')


def test_mine_completes_before_cancellation():
    """
    Si mine() termina antes de que se active stop_event,
    retorna el nonce normalmente.
    """
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=3)

    stop_event = threading.Event()

    # Minar con difficulty baja — terminará antes del timeout
    nonce = pow_solver.mine(stop_event=stop_event)

    # No activamos stop_event → debe retornar nonce válido
    assert nonce is not None
    assert pow_solver.validate(nonce)


def test_stop_event_cleared_for_reuse():
    """
    Un stop_event limpiado con clear() permite minar de nuevo.
    Simula el comportamiento del loop: cancelar → clear → reiniciar.
    """
    header     = MockBlockHeader()
    pow_solver = ProofOfWork(header, difficulty=3)

    stop_event = threading.Event()

    # Primer intento: cancelado
    stop_event.set()
    result1 = pow_solver.mine(stop_event=stop_event)
    assert result1 is None

    # Limpiar el evento y reintentar
    stop_event.clear()
    result2 = pow_solver.mine(stop_event=stop_event)
    assert result2 is not None
