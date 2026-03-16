"""
Tests para SeedNode y SeedClient

Nota: estos tests levantan un servidor Flask real en un thread,
por eso usan threading y requests en lugar de asyncio.
"""

import time
import threading
import pytest
import requests
from network.seed_node import SeedNode


# ──────────────────────────────────────────────
# Fixture: seed node en thread separado
# ──────────────────────────────────────────────

TEST_PORT = 18888  # Puerto exclusivo para tests (no conflicto con dev)


@pytest.fixture(scope='module')
def seed_server():
    """
    Levanta un SeedNode real en un thread para los tests.
    Se comparte entre todos los tests del módulo (scope='module').
    """
    seed = SeedNode(host='127.0.0.1', port=TEST_PORT)
    seed.PEER_TIMEOUT = 5  # Timeout corto para test de limpieza

    thread = threading.Thread(target=seed.run, daemon=True)
    thread.start()

    # Esperar a que Flask esté listo
    base_url = f"http://127.0.0.1:{TEST_PORT}"
    for _ in range(20):
        try:
            requests.get(f"{base_url}/health", timeout=1)
            break
        except Exception:
            time.sleep(0.2)

    yield base_url

    # El thread es daemon — se cierra automáticamente al terminar los tests


# ──────────────────────────────────────────────
# Tests de /health
# ──────────────────────────────────────────────

def test_health_endpoint(seed_server):
    """Seed responde correctamente en /health"""
    r = requests.get(f"{seed_server}/health")

    assert r.status_code == 200
    data = r.json()
    assert data['status'] == 'ok'
    assert 'peers_count' in data
    assert 'timestamp' in data


# ──────────────────────────────────────────────
# Tests de /register
# ──────────────────────────────────────────────

def test_register_new_node(seed_server):
    """Registrar un nodo nuevo devuelve ok"""
    r = requests.post(f"{seed_server}/register", json={
        'host': '192.168.1.10',
        'port': 5000,
        'node_id': 'node_5000'
    })

    assert r.status_code == 200
    data = r.json()
    assert data['status'] == 'ok'
    assert data['addr'] == '192.168.1.10:5000'


def test_register_without_host_fails(seed_server):
    """Registro sin host falla con 400"""
    r = requests.post(f"{seed_server}/register", json={
        'port': 5000
    })
    assert r.status_code == 400


def test_register_without_port_fails(seed_server):
    """Registro sin port falla con 400"""
    r = requests.post(f"{seed_server}/register", json={
        'host': '192.168.1.10'
    })
    assert r.status_code == 400


def test_register_without_body_fails(seed_server):
    """Registro sin body JSON falla con 400"""
    r = requests.post(f"{seed_server}/register")
    assert r.status_code == 400


def test_register_updates_existing_node(seed_server):
    """Re-registrar un nodo actualiza su last_seen"""
    payload = {'host': '192.168.1.20', 'port': 5001, 'node_id': 'node_5001'}

    r1 = requests.post(f"{seed_server}/register", json=payload)
    time.sleep(0.1)
    r2 = requests.post(f"{seed_server}/register", json=payload)

    assert r1.status_code == 200
    assert r2.status_code == 200


# ──────────────────────────────────────────────
# Tests de /peers
# ──────────────────────────────────────────────

def test_get_peers_returns_registered_nodes(seed_server):
    """GET /peers devuelve nodos registrados"""
    # Registrar dos nodos
    requests.post(f"{seed_server}/register", json={
        'host': '192.168.1.30', 'port': 5002, 'node_id': 'node_5002'
    })
    requests.post(f"{seed_server}/register", json={
        'host': '192.168.1.31', 'port': 5003, 'node_id': 'node_5003'
    })

    r = requests.get(f"{seed_server}/peers")
    assert r.status_code == 200

    data = r.json()
    assert 'peers' in data
    assert 'count' in data
    assert data['count'] >= 2

    hosts = [p['host'] for p in data['peers']]
    assert '192.168.1.30' in hosts
    assert '192.168.1.31' in hosts


def test_get_peers_excludes_self(seed_server):
    """GET /peers con exclude_host/port no devuelve el nodo que pregunta"""
    requests.post(f"{seed_server}/register", json={
        'host': '192.168.1.40', 'port': 5004, 'node_id': 'node_5004'
    })

    r = requests.get(f"{seed_server}/peers", params={
        'exclude_host': '192.168.1.40',
        'exclude_port': 5004
    })

    data = r.json()
    for peer in data['peers']:
        assert not (peer['host'] == '192.168.1.40' and peer['port'] == 5004)


def test_get_peers_response_structure(seed_server):
    """Cada peer en la lista tiene host, port y node_id"""
    r = requests.get(f"{seed_server}/peers")
    data = r.json()

    for peer in data['peers']:
        assert 'host' in peer
        assert 'port' in peer
        assert 'node_id' in peer


# ──────────────────────────────────────────────
# Tests de /peers/all
# ──────────────────────────────────────────────

def test_get_all_peers_has_active_field(seed_server):
    """GET /peers/all incluye campo 'active' por peer"""
    r = requests.get(f"{seed_server}/peers/all")
    assert r.status_code == 200

    data = r.json()
    for peer in data['peers']:
        assert 'active' in peer
        assert 'last_seen' in peer
        assert 'first_seen' in peer


# ──────────────────────────────────────────────
# Tests de SeedClient
# ──────────────────────────────────────────────

def test_seed_client_register(seed_server):
    """SeedClient.register() retorna True cuando seed está activo"""
    from network.seed_client import SeedClient

    client = SeedClient(
        node_id='node_test',
        host='192.168.1.50',
        port=5010,
        seed_host='127.0.0.1',
        seed_port=TEST_PORT
    )

    result = client.register()
    assert result is True


def test_seed_client_get_peers(seed_server):
    """SeedClient.get_peers() retorna lista de peers"""
    from network.seed_client import SeedClient

    client = SeedClient(
        node_id='node_test2',
        host='192.168.1.51',
        port=5011,
        seed_host='127.0.0.1',
        seed_port=TEST_PORT
    )

    client.register()
    peers = client.get_peers()

    assert isinstance(peers, list)


def test_seed_client_is_available(seed_server):
    """SeedClient.is_seed_available() retorna True cuando seed está activo"""
    from network.seed_client import SeedClient

    client = SeedClient(
        node_id='node_test3',
        host='192.168.1.52',
        port=5012,
        seed_host='127.0.0.1',
        seed_port=TEST_PORT
    )

    assert client.is_seed_available() is True


def test_seed_client_unavailable_seed():
    """SeedClient falla silenciosamente cuando seed no está disponible"""
    from network.seed_client import SeedClient

    client = SeedClient(
        node_id='node_test4',
        host='192.168.1.53',
        port=5013,
        seed_host='127.0.0.1',
        seed_port=19999  # Puerto que no existe
    )

    # No debe lanzar excepción — falla silenciosamente
    assert client.register() is False
    assert client.get_peers() == []
    assert client.is_seed_available() is False
