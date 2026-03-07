"""
Tests para Blockchain
"""

import pytest
import time
from core.blockchain import Blockchain
from core.transaction import Transaction
from core.wallet import Wallet


def test_blockchain_initialization():
    """Blockchain se inicializa con genesis block"""
    bc = Blockchain()
    
    assert len(bc.chain) == 1
    assert len(bc.mempool) == 0
    assert bc.BLOCK_REWARD == 50
    assert bc.DIFFICULTY == 4


def test_genesis_block():
    """Genesis block tiene características correctas"""
    bc = Blockchain()
    genesis = bc.chain[0]
    
    assert genesis.header.prev_hash == '0' * 64
    assert genesis.header.timestamp == 0
    assert genesis.header.nonce == 0
    assert len(genesis.transactions) == 1
    assert genesis.transactions[0].from_address == "COINBASE"


def test_get_latest_block():
    """get_latest_block retorna el último bloque"""
    bc = Blockchain()
    
    latest = bc.get_latest_block()
    
    assert latest == bc.chain[-1]
    assert latest == bc.chain[0]  # Solo genesis por ahora


def test_add_transaction_to_mempool_valid():
    """TX válida se agrega al mempool"""
    bc = Blockchain()
    
    alice = Wallet()
    bob = Wallet()
    
    # Alice mina primero para tener fondos
    bc.mine_block(alice.address)
    
    # Alice envía a Bob
    tx = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    
    result = bc.add_transaction_to_mempool(tx)
    
    assert result
    assert len(bc.mempool) == 1


def test_add_transaction_to_mempool_insufficient_balance():
    """TX sin fondos suficientes es rechazada"""
    bc = Blockchain()
    
    alice = Wallet()
    bob = Wallet()
    
    # Alice NO tiene fondos (no ha minado)
    tx = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    
    result = bc.add_transaction_to_mempool(tx)
    
    assert not result
    assert len(bc.mempool) == 0


def test_add_transaction_to_mempool_invalid_signature():
    """TX con firma inválida es rechazada"""
    bc = Blockchain()
    
    tx = Transaction("alice", "bob", 10)
    # NO firmar
    
    result = bc.add_transaction_to_mempool(tx)
    
    assert not result
    assert len(bc.mempool) == 0


def test_add_transaction_to_mempool_duplicate():
    """TX duplicada es rechazada"""
    bc = Blockchain()
    
    alice = Wallet()
    bob = Wallet()
    
    bc.mine_block(alice.address)
    
    tx = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    
    # Agregar primera vez
    assert bc.add_transaction_to_mempool(tx)
    
    # Intentar agregar de nuevo
    assert not bc.add_transaction_to_mempool(tx)
    assert len(bc.mempool) == 1


def test_mine_block_only_coinbase():
    """Minar bloque con solo coinbase TX"""
    bc = Blockchain()
    miner = Wallet()
    
    block = bc.mine_block(miner.address)
    
    assert block is not None
    assert len(bc.chain) == 2  # Genesis + nuevo
    assert len(block.transactions) == 1  # Solo coinbase
    assert block.transactions[0].from_address == "COINBASE"
    assert block.transactions[0].to_address == miner.address
    assert block.transactions[0].amount == 50


def test_mine_block_with_transactions():
    """Minar bloque con TXs del mempool"""
    bc = Blockchain()
    
    alice = Wallet()
    bob = Wallet()
    charlie = Wallet()
    
    # Alice mina (tiene fondos)
    bc.mine_block(alice.address)
    
    # Alice envía a Bob
    tx = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    bc.add_transaction_to_mempool(tx)
    
    # Charlie mina (incluye TX de Alice)
    block = bc.mine_block(charlie.address)
    
    assert len(bc.chain) == 3  # Genesis + Alice + Charlie
    assert len(block.transactions) == 2  # Coinbase + TX de Alice
    assert len(bc.mempool) == 0  # Mempool limpiado


def test_get_balance():
    """Balance se calcula correctamente"""
    bc = Blockchain()
    
    alice = Wallet()
    bob = Wallet()
    
    # Estado inicial: todos en 0
    assert bc.get_balance(alice.address) == 0
    assert bc.get_balance(bob.address) == 0
    
    # Alice mina (recibe 50)
    bc.mine_block(alice.address)
    assert bc.get_balance(alice.address) == 50
    
    # Alice envía 10 a Bob
    tx = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    bc.add_transaction_to_mempool(tx)
    
    # Charlie mina (confirma TX)
    charlie = Wallet()
    bc.mine_block(charlie.address)
    
    assert bc.get_balance(alice.address) == 40  # 50 - 10
    assert bc.get_balance(bob.address) == 10
    assert bc.get_balance(charlie.address) == 50


def test_has_sufficient_balance():
    """has_sufficient_balance funciona correctamente"""
    bc = Blockchain()
    
    alice = Wallet()
    
    # Sin fondos
    assert not bc.has_sufficient_balance(alice.address, 10)
    
    # Minar (tiene 50)
    bc.mine_block(alice.address)
    
    assert bc.has_sufficient_balance(alice.address, 10)
    assert bc.has_sufficient_balance(alice.address, 50)
    assert not bc.has_sufficient_balance(alice.address, 51)

"""
def test_validate_block_valid():
    #Bloque válido pasa validación
    bc = Blockchain()
    miner = Wallet()
    
    block = bc.mine_block(miner.address)
    
    # Ya está en cadena, pero validar de nuevo
    assert bc.validate_block(block)"""


def test_validate_block_invalid_pow():
    """Bloque con PoW inválido falla validación"""
    bc = Blockchain()
    
    alice = Wallet()
    bc.mine_block(alice.address)
    
    # Tomar último bloque y modificar nonce
    invalid_block = bc.chain[-1]
    invalid_block.header.nonce = 99999
    
    # Validar (debería fallar)
    # Nota: esto modifica la cadena, solo para demo de validación
    assert not invalid_block.validate_pow()


def test_validate_chain_valid():
    """Cadena válida pasa validación"""
    bc = Blockchain()
    
    alice = Wallet()
    
    # Minar 3 bloques
    for _ in range(3):
        bc.mine_block(alice.address)
    
    assert bc.validate_chain(bc.chain)


def test_validate_chain_invalid_genesis():
    """Cadena con genesis diferente falla"""
    bc1 = Blockchain()
    bc2 = Blockchain()
    
    # Modificar genesis de bc2 (hack para testing)
    bc2.chain[0].header.nonce = 999
    
    # bc1 rechaza cadena de bc2 (genesis diferente)
    assert not bc1.validate_chain(bc2.chain)


def test_validate_chain_broken_link():
    """Cadena con enlace roto falla validación"""
    bc = Blockchain()
    
    alice = Wallet()
    bc.mine_block(alice.address)
    bc.mine_block(alice.address)
    
    # Romper enlace: modificar prev_hash del último bloque
    bc.chain[-1].header.prev_hash = '0' * 64
    
    assert not bc.validate_chain(bc.chain)


def test_full_workflow():
    """Test de flujo completo: minar, enviar, minar"""
    bc = Blockchain()
    
    alice = Wallet()
    bob = Wallet()
    charlie = Wallet()
    
    # 1. Alice mina (recibe reward)
    bc.mine_block(alice.address)
    assert bc.get_balance(alice.address) == 50
    
    # 2. Alice envía a Bob
    tx1 = Transaction(alice.address, bob.address, 10)
    tx1.sign(alice)
    bc.add_transaction_to_mempool(tx1)
    
    # 3. Alice envía a Charlie
    tx2 = Transaction(alice.address, charlie.address, 5)
    tx2.sign(alice)
    bc.add_transaction_to_mempool(tx2)
    
    # 4. Bob mina (confirma ambas TXs)
    bc.mine_block(bob.address)
    
    # 5. Verificar balances
    assert bc.get_balance(alice.address) == 35    # 50 - 10 - 5
    assert bc.get_balance(bob.address) == 60      # 10 + 50 (reward)
    assert bc.get_balance(charlie.address) == 5
    
    # 6. Verificar cadena
    assert len(bc.chain) == 3  # Genesis + Alice + Bob
    assert bc.validate_chain(bc.chain)


def test_mempool_cleanup_after_mining():
    """Mempool se limpia después de minar"""
    bc = Blockchain()
    
    alice = Wallet()
    bob = Wallet()
    
    bc.mine_block(alice.address)
    
    # Agregar TX
    tx = Transaction(alice.address, bob.address, 10)
    tx.sign(alice)
    bc.add_transaction_to_mempool(tx)
    
    assert len(bc.mempool) == 1
    
    # Minar
    bc.mine_block(bob.address)
    
    # Mempool limpio
    assert len(bc.mempool) == 0


def test_coinbase_always_first_transaction():
    """Coinbase siempre es la primera TX del bloque"""
    bc = Blockchain()
    
    alice = Wallet()
    bob = Wallet()
    
    bc.mine_block(alice.address)
    
    # Agregar TXs
    for i in range(3):
        tx = Transaction(alice.address, bob.address, 1)
        tx.sign(alice)
        bc.add_transaction_to_mempool(tx)
    
    # Minar
    block = bc.mine_block(bob.address)
    
    # Primera TX debe ser coinbase
    assert block.transactions[0].from_address == "COINBASE"