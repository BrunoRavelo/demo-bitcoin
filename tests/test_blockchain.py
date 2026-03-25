"""
Tests para Blockchain — Sprint 9.2
Actualizado para target numérico y difficulty ajustable.
"""

import pytest
import time
from core.blockchain import Blockchain
from core.transaction import Transaction
from core.wallet import Wallet
from config import INITIAL_TARGET, MAX_TARGET


def test_blockchain_initialization():
    """Blockchain se inicializa con genesis block y target inicial."""
    bc = Blockchain()
    assert len(bc.chain)      == 1
    assert len(bc.mempool)    == 0
    assert bc.BLOCK_REWARD    == 50
    assert bc.CURRENT_TARGET  == INITIAL_TARGET


def test_genesis_block():
    """Genesis block tiene características correctas."""
    bc      = Blockchain()
    genesis = bc.chain[0]

    assert genesis.header.prev_hash  == '0' * 64
    assert genesis.header.timestamp  == 0
    assert genesis.header.nonce      == 0
    assert genesis.header.target     == MAX_TARGET  # génesis acepta cualquier hash
    assert len(genesis.transactions) == 1
    assert genesis.transactions[0].from_address == "COINBASE"


def test_get_latest_block():
    """get_latest_block retorna el último bloque."""
    bc     = Blockchain()
    latest = bc.get_latest_block()
    assert latest == bc.chain[-1]


def test_add_transaction_to_mempool_valid():
    """TX válida se agrega al mempool."""
    bc    = Blockchain()
    alice = Wallet()
    bob   = Wallet()
    bc.mine_block(alice.address)

    tx = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    assert bc.add_transaction_to_mempool(tx)
    assert len(bc.mempool) == 1


def test_add_transaction_to_mempool_insufficient_balance():
    """TX sin fondos suficientes es rechazada."""
    bc    = Blockchain()
    alice = Wallet()
    bob   = Wallet()

    tx = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    assert not bc.add_transaction_to_mempool(tx)
    assert len(bc.mempool) == 0


def test_add_transaction_to_mempool_invalid_signature():
    """TX con firma inválida es rechazada."""
    bc = Blockchain()
    tx = Transaction("alice", "bob", 10)
    assert not bc.add_transaction_to_mempool(tx)


def test_add_transaction_to_mempool_duplicate():
    """TX duplicada es rechazada."""
    bc    = Blockchain()
    alice = Wallet()
    bob   = Wallet()
    bc.mine_block(alice.address)

    tx = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    assert bc.add_transaction_to_mempool(tx)
    assert not bc.add_transaction_to_mempool(tx)
    assert len(bc.mempool) == 1


def test_mine_block_only_coinbase():
    """Minar bloque con solo coinbase TX."""
    bc    = Blockchain()
    miner = Wallet()
    block = bc.mine_block(miner.address)

    assert block is not None
    assert len(bc.chain)                              == 2
    assert len(block.transactions)                    == 1
    assert block.transactions[0].from_address         == "COINBASE"
    assert block.transactions[0].to_address           == miner.address
    assert block.transactions[0].amount               == 50


def test_mine_block_with_transactions():
    """Minar bloque con TXs del mempool."""
    bc      = Blockchain()
    alice   = Wallet()
    bob     = Wallet()
    charlie = Wallet()

    bc.mine_block(alice.address)
    tx = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    bc.add_transaction_to_mempool(tx)

    block = bc.mine_block(charlie.address)
    assert len(bc.chain)           == 3
    assert len(block.transactions) == 2
    assert len(bc.mempool)         == 0


def test_get_balance():
    """Balance se calcula correctamente."""
    bc      = Blockchain()
    alice   = Wallet()
    bob     = Wallet()
    charlie = Wallet()

    assert bc.get_balance(alice.address) == 0

    bc.mine_block(alice.address)
    assert bc.get_balance(alice.address) == 50

    tx = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    bc.add_transaction_to_mempool(tx)
    bc.mine_block(charlie.address)

    assert bc.get_balance(alice.address)   == 40
    assert bc.get_balance(bob.address)     == 10
    assert bc.get_balance(charlie.address) == 50


def test_has_sufficient_balance():
    """has_sufficient_balance funciona correctamente."""
    bc    = Blockchain()
    alice = Wallet()

    assert not bc.has_sufficient_balance(alice.address, 10)
    bc.mine_block(alice.address)
    assert bc.has_sufficient_balance(alice.address, 10)
    assert bc.has_sufficient_balance(alice.address, 50)
    assert not bc.has_sufficient_balance(alice.address, 51)


def test_validate_block_invalid_pow():
    """Bloque con nonce que no cumple target falla."""
    bc    = Blockchain()
    alice = Wallet()
    bc.mine_block(alice.address)

    invalid_block        = bc.chain[-1]
    original_nonce       = invalid_block.header.nonce
    invalid_block.header.nonce = original_nonce + 1  # Cambiar nonce
    assert not invalid_block.validate_pow()
    invalid_block.header.nonce = original_nonce  # Restaurar


def test_validate_chain_valid():
    """Cadena válida pasa validación."""
    bc    = Blockchain()
    alice = Wallet()
    for _ in range(3):
        bc.mine_block(alice.address)
    assert bc.validate_chain(bc.chain)


def test_validate_chain_invalid_genesis():
    """Cadena con genesis diferente falla."""
    bc1 = Blockchain()
    bc2 = Blockchain()
    bc2.chain[0].header.nonce = 999
    assert not bc1.validate_chain(bc2.chain)


def test_validate_chain_broken_link():
    """Cadena con enlace roto falla validación."""
    bc    = Blockchain()
    alice = Wallet()
    bc.mine_block(alice.address)
    bc.mine_block(alice.address)
    bc.chain[-1].header.prev_hash = '0' * 64
    assert not bc.validate_chain(bc.chain)


def test_target_adjustment_after_interval():
    """
    CURRENT_TARGET se ajusta después de DIFFICULTY_ADJUSTMENT_INTERVAL bloques.
    Con bloques muy rápidos (en tests), el target debe subir (más fácil).
    """
    from config import DIFFICULTY_ADJUSTMENT_INTERVAL
    bc    = Blockchain()
    alice = Wallet()

    target_before = bc.CURRENT_TARGET

    # Minar suficientes bloques para disparar el ajuste
    for _ in range(DIFFICULTY_ADJUSTMENT_INTERVAL + 1):
        bc.mine_block(alice.address)

    # Los bloques en tests se minan casi instantáneamente
    # → tiempo real << tiempo esperado
    # → target sube (más fácil / mayor número)
    assert bc.CURRENT_TARGET > target_before


def test_full_workflow():
    """Test de flujo completo."""
    bc      = Blockchain()
    alice   = Wallet()
    bob     = Wallet()
    charlie = Wallet()

    bc.mine_block(alice.address)
    assert bc.get_balance(alice.address) == 50

    tx1 = Transaction(alice.address, bob.address, 10)
    tx1.sign(alice)
    bc.add_transaction_to_mempool(tx1)

    tx2 = Transaction(alice.address, charlie.address, 5)
    tx2.sign(alice)
    bc.add_transaction_to_mempool(tx2)

    bc.mine_block(bob.address)

    assert bc.get_balance(alice.address)   == 35
    assert bc.get_balance(bob.address)     == 60
    assert bc.get_balance(charlie.address) == 5
    assert len(bc.chain)                   == 3
    assert bc.validate_chain(bc.chain)


def test_mempool_cleanup_after_mining():
    """Mempool se limpia después de minar."""
    bc    = Blockchain()
    alice = Wallet()
    bob   = Wallet()
    bc.mine_block(alice.address)

    tx = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    bc.add_transaction_to_mempool(tx)
    assert len(bc.mempool) == 1

    bc.mine_block(bob.address)
    assert len(bc.mempool) == 0


def test_coinbase_always_first_transaction():
    """Coinbase siempre es la primera TX del bloque."""
    bc    = Blockchain()
    alice = Wallet()
    bob   = Wallet()
    bc.mine_block(alice.address)

    for i in range(3):
        tx = Transaction(alice.address, bob.address, 1)
        tx.sign(alice)
        bc.add_transaction_to_mempool(tx)

    block = bc.mine_block(bob.address)
    assert block.transactions[0].from_address == "COINBASE"


def test_get_target_hex():
    """get_target_hex retorna string no vacío."""
    bc = Blockchain()
    assert isinstance(bc.get_target_hex(), str)
    assert len(bc.get_target_hex()) > 0


def test_get_estimated_block_time():
    """get_estimated_block_time retorna string."""
    bc = Blockchain()
    t  = bc.get_estimated_block_time()
    assert isinstance(t, str)
    assert '~' in t
