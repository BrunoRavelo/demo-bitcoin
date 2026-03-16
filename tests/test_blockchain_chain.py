"""
Tests para replace_chain, longest chain rule y sincronización

Estos tests verifican el comportamiento crítico de consenso:
- Un nodo adopta la cadena más larga
- Un nodo rechaza cadenas más cortas
- Un nodo rechaza cadenas inválidas
- Las TXs huérfanas vuelven al mempool correctamente
"""

import pytest
from core.blockchain import Blockchain
from core.transaction import Transaction
from core.wallet import Wallet


def mine_n_blocks(blockchain: Blockchain, n: int, miner_address: str):
    """Helper: mina n bloques en una blockchain."""
    for _ in range(n):
        blockchain.mine_block(miner_address)


# ──────────────────────────────────────────────────────────
# Tests de replace_chain
# ──────────────────────────────────────────────────────────

def test_replace_chain_accepts_longer_valid_chain():
    """Nodo adopta cadena más larga y válida."""
    bc1 = Blockchain()
    bc2 = Blockchain()

    miner = Wallet()

    # bc2 tiene más bloques que bc1
    mine_n_blocks(bc2, 3, miner.address)

    # bc1 debe adoptar la cadena de bc2
    replaced = bc1.replace_chain(bc2.chain)

    assert replaced is True
    assert len(bc1.chain) == len(bc2.chain)


def test_replace_chain_rejects_shorter_chain():
    """Nodo rechaza cadena más corta."""
    bc1 = Blockchain()
    bc2 = Blockchain()

    miner = Wallet()

    # bc1 tiene más bloques
    mine_n_blocks(bc1, 3, miner.address)

    # bc2 intenta reemplazar con cadena más corta (solo genesis)
    replaced = bc1.replace_chain(bc2.chain)

    assert replaced is False
    assert len(bc1.chain) == 4  # Genesis + 3 bloques


def test_replace_chain_rejects_same_length():
    """Nodo rechaza cadena de igual longitud."""
    bc1 = Blockchain()
    bc2 = Blockchain()

    miner = Wallet()

    mine_n_blocks(bc1, 2, miner.address)
    mine_n_blocks(bc2, 2, miner.address)

    replaced = bc1.replace_chain(bc2.chain)

    assert replaced is False


def test_replace_chain_rejects_invalid_chain():
    """Nodo rechaza cadena más larga pero inválida."""
    bc1 = Blockchain()
    bc2 = Blockchain()

    miner = Wallet()
    mine_n_blocks(bc2, 3, miner.address)

    # Corromper la cadena de bc2
    bc2.chain[1].header.nonce = 99999  # PoW inválido

    replaced = bc1.replace_chain(bc2.chain)

    assert replaced is False


def test_replace_chain_rejects_different_genesis():
    """Nodo rechaza cadena con genesis diferente."""
    bc1 = Blockchain()
    bc2 = Blockchain()

    miner = Wallet()
    mine_n_blocks(bc2, 3, miner.address)

    # Modificar genesis de bc2
    bc2.chain[0].header.nonce = 999

    replaced = bc1.replace_chain(bc2.chain)

    assert replaced is False


def test_replace_chain_updates_height():
    """Después del reemplazo, la altura se actualiza correctamente."""
    bc1 = Blockchain()
    bc2 = Blockchain()

    miner = Wallet()
    mine_n_blocks(bc2, 5, miner.address)

    assert bc1.get_height() == 1  # Solo genesis
    bc1.replace_chain(bc2.chain)
    assert bc1.get_height() == 6  # Genesis + 5 bloques


def test_replace_chain_recovers_orphaned_txs():
    """TXs en bloques huérfanos vuelven al mempool."""
    bc1 = Blockchain()
    bc2 = Blockchain()

    alice  = Wallet()
    bob    = Wallet()
    miner1 = Wallet()
    miner2 = Wallet()

    # Ambas cadenas parten del mismo genesis
    # bc1: miner1 mina → alice tiene fondos
    bc1.mine_block(alice.address)

    # Crear TX en bc1 que quedará huérfana
    tx = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    bc1.add_transaction_to_mempool(tx)
    bc1.mine_block(miner1.address)  # Confirma la TX de alice

    # bc2: cadena más larga sin esa TX
    bc2.mine_block(alice.address)   # alice tiene fondos en bc2 también
    bc2.mine_block(miner2.address)
    bc2.mine_block(miner2.address)  # bc2 es más larga

    tx_hash = tx.hash()

    # bc1 adopta bc2 — la TX de alice queda huérfana
    replaced = bc1.replace_chain(bc2.chain)

    assert replaced is True
    # La TX huérfana volvió al mempool (alice tiene fondos en la nueva cadena)
    mempool_hashes = [t.hash() for t in bc1.mempool]
    assert tx_hash in mempool_hashes


def test_replace_chain_cleans_confirmed_txs_from_mempool():
    """TXs ya confirmadas en la nueva cadena se eliminan del mempool."""
    bc1 = Blockchain()
    bc2 = Blockchain()

    alice  = Wallet()
    miner2 = Wallet()

    # alice mina en bc2 para tener fondos
    bc2.mine_block(alice.address)

    # Crear TX y confirmarla en bc2
    bob = Wallet()
    tx  = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    bc2.add_transaction_to_mempool(tx)
    bc2.mine_block(miner2.address)
    bc2.mine_block(miner2.address)  # bc2 más larga que bc1

    # Agregar la misma TX al mempool de bc1
    bc1.mine_block(alice.address)  # alice tiene fondos en bc1 también
    tx2 = Transaction(alice.address, bob.address, 10)
    tx2.sign(alice)
    # Nota: usamos bc2.chain[2] tiene esa TX confirmada
    # Al reemplazar, bc1 debe limpiar su mempool

    bc1.replace_chain(bc2.chain)

    # El mempool no debe tener TXs ya confirmadas en la nueva cadena
    confirmed_hashes = {
        t.hash()
        for block in bc1.chain
        for t in block.transactions
    }
    for mempool_tx in bc1.mempool:
        assert mempool_tx.hash() not in confirmed_hashes


# ──────────────────────────────────────────────────────────
# Tests de serialización de cadena
# ──────────────────────────────────────────────────────────

def test_get_chain_as_dicts():
    """La cadena se serializa correctamente."""
    bc    = Blockchain()
    miner = Wallet()
    mine_n_blocks(bc, 2, miner.address)

    chain_dicts = bc.get_chain_as_dicts()

    assert len(chain_dicts) == 3  # Genesis + 2
    assert isinstance(chain_dicts[0], dict)
    assert 'header' in chain_dicts[0]
    assert 'transactions' in chain_dicts[0]


def test_chain_from_dicts_roundtrip():
    """Serializar y deserializar una cadena produce el mismo resultado."""
    bc    = Blockchain()
    miner = Wallet()
    mine_n_blocks(bc, 2, miner.address)

    chain_dicts  = bc.get_chain_as_dicts()
    reconstructed = Blockchain.chain_from_dicts(chain_dicts)

    assert len(reconstructed) == len(bc.chain)
    for original, restored in zip(bc.chain, reconstructed):
        assert original.hash == restored.hash


def test_find_fork_point_identical_chains():
    """Fork point en cadenas idénticas es la longitud mínima."""
    bc1 = Blockchain()
    bc2 = Blockchain()

    miner = Wallet()
    mine_n_blocks(bc1, 2, miner.address)
    mine_n_blocks(bc2, 2, miner.address)

    # Cadenas idénticas → fork point al final
    fp = bc1._find_fork_point(bc1.chain)
    assert fp == len(bc1.chain)


# ──────────────────────────────────────────────────────────
# Tests de get_height y get_block_by_hash
# ──────────────────────────────────────────────────────────

def test_get_height():
    """get_height() retorna el número de bloques."""
    bc    = Blockchain()
    miner = Wallet()

    assert bc.get_height() == 1  # Solo genesis

    bc.mine_block(miner.address)
    assert bc.get_height() == 2

    bc.mine_block(miner.address)
    assert bc.get_height() == 3


def test_get_block_by_hash_found():
    """get_block_by_hash encuentra un bloque existente."""
    bc    = Blockchain()
    miner = Wallet()
    block = bc.mine_block(miner.address)

    found = bc.get_block_by_hash(block.hash)

    assert found is not None
    assert found.hash == block.hash


def test_get_block_by_hash_not_found():
    """get_block_by_hash retorna None para hash inexistente."""
    bc    = Blockchain()
    found = bc.get_block_by_hash('0' * 64)

    assert found is None
