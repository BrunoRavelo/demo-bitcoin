"""
Tests de integración P2P

Levanta nodos reales con WebSocket para probar:
- Conexión y handshake entre nodos
- Propagación de transacciones
- Propagación y recepción de bloques
- Sincronización de cadena (longest chain rule en red)

Usa difficulty=1 para que el minado sea inmediato en los tests.
Los nodos usan puertos altos (19000+) para no conflictar con dev.
"""

import asyncio
import pytest
from core.blockchain import Blockchain
from core.wallet import Wallet
from core.transaction import Transaction
from network.p2p_node import P2PNode, MINING_AUTO, MINING_PAUSED

# Puertos exclusivos para tests — no conflictan con desarrollo
BASE_PORT = 19000
DIFFICULTY = 1  # Minado instantáneo en tests


def make_blockchain() -> Blockchain:
    """Blockchain con difficulty 1 para tests rápidos."""
    bc = Blockchain()
    bc.DIFFICULTY = DIFFICULTY
    return bc


def make_node(port: int, bootstrap: list = None) -> P2PNode:
    """
    Crea un nodo de prueba con minado pausado por defecto.
    Los tests controlan el minado explícitamente para evitar
    que bloques minados en background interfieran con las aserciones.
    """
    node = P2PNode(
        host='localhost',
        port=port,
        bootstrap_peers=bootstrap or [],
        blockchain=make_blockchain(),
    )
    node.mining_mode = MINING_PAUSED
    return node


async def start_nodes(*nodes) -> None:
    """Arranca múltiples nodos en background."""
    for node in nodes:
        asyncio.create_task(node.start())
    # Esperar a que todos levanten
    await asyncio.sleep(1.5)


async def wait_for_condition(condition, timeout=10, interval=0.2):
    """Espera hasta que condition() sea True o se agote el timeout."""
    elapsed = 0.0
    while elapsed < timeout:
        if condition():
            return True
        await asyncio.sleep(interval)
        elapsed += interval
    return False


# ──────────────────────────────────────────────────────────
# Tests de conexión
# ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_two_nodes_connect():
    """Dos nodos se conectan correctamente."""
    node1 = make_node(BASE_PORT)
    node2 = make_node(BASE_PORT + 1, bootstrap=[('localhost', BASE_PORT)])

    await start_nodes(node1, node2)

    connected = await wait_for_condition(
        lambda: len(node1.peers_connected) >= 1
    )

    assert connected, "node1 no tiene peers conectados"
    assert len(node1.peers_connected) >= 1
    assert len(node2.peers_connected) >= 1


@pytest.mark.asyncio
async def test_three_nodes_form_network():
    """Tres nodos forman una red conectada."""
    port = BASE_PORT + 10
    node1 = make_node(port)
    node2 = make_node(port + 1, bootstrap=[('localhost', port)])
    node3 = make_node(port + 2, bootstrap=[('localhost', port)])

    await start_nodes(node1, node2, node3)

    connected = await wait_for_condition(
        lambda: len(node1.peers_connected) >= 2
    )

    assert connected
    assert len(node1.peers_connected) >= 2


# ──────────────────────────────────────────────────────────
# Tests de propagación de transacciones
# ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tx_propagates_to_peer():
    """TX creada en nodo1 llega al mempool de nodo2."""
    port  = BASE_PORT + 20
    node1 = make_node(port)
    node2 = make_node(port + 1, bootstrap=[('localhost', port)])

    await start_nodes(node1, node2)
    await wait_for_condition(lambda: len(node1.peers_connected) >= 1)

    # Minar en node1 y propagar el bloque a node2 primero
    block = node1.blockchain.mine_block(node1.wallet.address)
    await node1.broadcast_block(block)

    # Esperar que node2 reciba y procese el bloque
    await wait_for_condition(
        lambda: node2.blockchain.get_height() >= 2
    )

    # Ahora sí crear y propagar la TX — node2 ya conoce el balance
    tx = node1.create_transaction(node2.wallet.address, 10.0)
    await node1.broadcast_transaction(tx)

    propagated = await wait_for_condition(
        lambda: any(
            t.hash() == tx.hash()
            for t in node2.blockchain.mempool
        )
    )

    assert propagated, "TX no llegó al mempool de node2"


@pytest.mark.asyncio
async def test_tx_with_insufficient_balance_rejected():
    """TX sin balance suficiente es rechazada localmente."""
    port  = BASE_PORT + 30
    node1 = make_node(port)

    # Sin minar — balance = 0
    with pytest.raises(ValueError, match="Balance insuficiente"):
        node1.create_transaction("1SomeAddress123456789012345678", 10.0)


# ──────────────────────────────────────────────────────────
# Tests de propagación de bloques
# ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_block_propagates_to_peer():
    """Bloque minado en nodo1 llega a nodo2."""
    port  = BASE_PORT + 40
    node1 = make_node(port)
    node2 = make_node(port + 1, bootstrap=[('localhost', port)])

    await start_nodes(node1, node2)

    height_before = node2.blockchain.get_height()

    # Minar en node1 y broadcast manual
    block = node1.blockchain.mine_block(node1.wallet.address)
    assert block is not None

    await node1.broadcast_block(block)

    # Esperar a que node2 reciba y procese el bloque
    updated = await wait_for_condition(
        lambda: node2.blockchain.get_height() > height_before,
        timeout=5,
    )

    assert updated, "node2 no recibió el bloque de node1"
    assert node2.blockchain.get_height() >= height_before + 1


@pytest.mark.asyncio
async def test_miner_receives_reward_after_block():
    """Minero recibe la recompensa después de que el bloque se confirma."""
    port  = BASE_PORT + 50
    node1 = make_node(port)

    block = node1.blockchain.mine_block(node1.wallet.address)

    assert block is not None
    balance = node1.get_balance()
    assert balance == node1.blockchain.BLOCK_REWARD


# ──────────────────────────────────────────────────────────
# Tests de sincronización de cadena
# ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_late_node_syncs_chain():
    """
    Nodo que se une tarde adopta la cadena más larga.

    node1 mina 3 bloques.
    node2 se conecta después con solo genesis.
    node2 debe sincronizar y quedar a la misma altura.
    """
    port  = BASE_PORT + 60
    node1 = make_node(port)

    # node1 arranca solo y mina
    asyncio.create_task(node1.start())
    await asyncio.sleep(0.5)

    for _ in range(3):
        node1.blockchain.mine_block(node1.wallet.address)

    assert node1.blockchain.get_height() == 4  # Genesis + 3

    # node2 se une tarde
    node2 = make_node(port + 1, bootstrap=[('localhost', port)])
    asyncio.create_task(node2.start())
    await asyncio.sleep(1.0)

    # Forzar sincronización
    for ws in node1.peers_connected.values():
        await node1._request_chain_sync(ws)
        break

    synced = await wait_for_condition(
        lambda: node2.blockchain.get_height() >= 4,
        timeout=8,
    )

    assert synced, (
        f"node2 no sincronizó — altura: {node2.blockchain.get_height()}"
    )


@pytest.mark.asyncio
async def test_longest_chain_wins():
    """
    Longest chain rule: nodo con cadena más corta adopta la más larga.

    node1 mina 2 bloques.
    node2 mina 4 bloques (independiente).
    Al conectarse, node1 debe adoptar la cadena de node2.
    """
    port  = BASE_PORT + 70
    node1 = make_node(port)
    node2 = make_node(port + 1)  # Sin bootstrap — independiente

    # Minar en ambos por separado
    for _ in range(2):
        node1.blockchain.mine_block(node1.wallet.address)
    for _ in range(4):
        node2.blockchain.mine_block(node2.wallet.address)

    assert node1.blockchain.get_height() == 3  # Genesis + 2
    assert node2.blockchain.get_height() == 5  # Genesis + 4

    # Ahora conectar y forzar sincronización
    asyncio.create_task(node1.start())
    asyncio.create_task(node2.start())
    await asyncio.sleep(1.5)

    # Enviar cadena de node2 a node1
    chain_data = node2.blockchain.get_chain_as_dicts()
    replaced   = node1.blockchain.replace_chain(
        Blockchain.chain_from_dicts(chain_data)
    )

    assert replaced is True
    assert node1.blockchain.get_height() == node2.blockchain.get_height()


# ──────────────────────────────────────────────────────────
# Tests de mining_mode
# ──────────────────────────────────────────────────────────

def test_node_initial_mining_mode():
    """Modo de minado inicial viene de config — sin forzar PAUSED."""
    from config import MINING_AUTO_START
    from network.p2p_node import MINING_AUTO, MINING_PAUSED

    # Crear nodo directamente sin make_node() para no forzar PAUSED
    node = P2PNode(
        host='localhost',
        port=BASE_PORT + 80,
        bootstrap_peers=[],
        blockchain=make_blockchain(),
    )
    expected = MINING_AUTO if MINING_AUTO_START else MINING_PAUSED
    assert node.mining_mode == expected


def test_set_mining_mode_paused():
    """Cambiar a modo PAUSED activa el stop_event."""
    from network.p2p_node import MINING_PAUSED
    node = make_node(BASE_PORT + 81)
    node.set_mining_mode(MINING_PAUSED)
    assert node.mining_mode == MINING_PAUSED


def test_node_balance_zero_initially():
    """Balance inicial es 0 (sin minar)."""
    node = make_node(BASE_PORT + 82)
    assert node.get_balance() == 0.0


def test_node_balance_after_mining():
    """Balance aumenta después de minar."""
    node  = make_node(BASE_PORT + 83)
    block = node.blockchain.mine_block(node.wallet.address)
    assert block is not None
    assert node.get_balance() == node.blockchain.BLOCK_REWARD
