"""
Tests para TxOrchestrator

Usa mocks HTTP para no depender de nodos reales corriendo.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from core.tx_orchestrator import TxOrchestrator, ORCH_AUTO, ORCH_MANUAL


# ──────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────

@pytest.fixture
def orchestrator():
    """Orquestador con auto-start desactivado para tests."""
    with patch('core.tx_orchestrator.TX_AUTO_START', False):
        orch = TxOrchestrator(
            seed_host='localhost',
            seed_port=18888,
            dashboard_port=18000,
        )
    return orch


MOCK_ADDRESSES = [
    {
        'host':           'localhost',
        'port':           5000,
        'node_id':        'node_5000',
        'wallet_address': '1Alice123456789012345678901234',
    },
    {
        'host':           'localhost',
        'port':           5001,
        'node_id':        'node_5001',
        'wallet_address': '1Bob12345678901234567890123456',
    },
    {
        'host':           'localhost',
        'port':           5002,
        'node_id':        'node_5002',
        'wallet_address': '1Charlie2345678901234567890123',
    },
]


# ──────────────────────────────────────────────────────────
# Tests de inicialización
# ──────────────────────────────────────────────────────────

def test_orchestrator_initial_mode_manual(orchestrator):
    """Orquestador inicia en modo MANUAL cuando TX_AUTO_START=False."""
    assert orchestrator.mode == ORCH_MANUAL


def test_orchestrator_initial_stats(orchestrator):
    """Stats iniciales en cero."""
    stats = orchestrator.get_stats()
    assert stats['txs_sent']   == 0
    assert stats['txs_failed'] == 0
    assert stats['running']    is False


def test_orchestrator_auto_mode_on_start():
    """Orquestador inicia en modo AUTO cuando TX_AUTO_START=True."""
    with patch('core.tx_orchestrator.TX_AUTO_START', True):
        orch = TxOrchestrator(seed_host='localhost', seed_port=18888)
    assert orch.mode == ORCH_AUTO


# ──────────────────────────────────────────────────────────
# Tests de control de modo
# ──────────────────────────────────────────────────────────

def test_set_mode_auto(orchestrator):
    """Cambiar a modo AUTO."""
    orchestrator.set_mode(ORCH_AUTO)
    assert orchestrator.mode == ORCH_AUTO


def test_set_mode_manual(orchestrator):
    """Cambiar a modo MANUAL."""
    orchestrator.set_mode(ORCH_AUTO)
    orchestrator.set_mode(ORCH_MANUAL)
    assert orchestrator.mode == ORCH_MANUAL


def test_set_mode_invalid(orchestrator):
    """Modo inválido lanza ValueError."""
    with pytest.raises(ValueError):
        orchestrator.set_mode('invalid_mode')


# ──────────────────────────────────────────────────────────
# Tests de send_tx
# ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_tx_success(orchestrator):
    """send_tx retorna True cuando el nodo acepta la TX."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch('requests.post', return_value=mock_response):
        result = await orchestrator.send_tx(
            sender_host='localhost',
            sender_port=5000,
            to_address='1Bob12345678901234567890123456',
            amount=10.0,
        )

    assert result is True
    assert orchestrator.txs_sent   == 1
    assert orchestrator.txs_failed == 0


@pytest.mark.asyncio
async def test_send_tx_failure_400(orchestrator):
    """send_tx retorna False cuando el nodo rechaza la TX (400)."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text        = 'Balance insuficiente'

    with patch('requests.post', return_value=mock_response):
        result = await orchestrator.send_tx(
            sender_host='localhost',
            sender_port=5000,
            to_address='1Bob12345678901234567890123456',
            amount=99999.0,
        )

    assert result is False
    assert orchestrator.txs_sent   == 0
    assert orchestrator.txs_failed == 1


@pytest.mark.asyncio
async def test_send_tx_connection_error(orchestrator):
    """send_tx retorna False cuando el nodo no está disponible."""
    import requests as req

    with patch('requests.post', side_effect=req.exceptions.ConnectionError):
        result = await orchestrator.send_tx(
            sender_host='localhost',
            sender_port=5000,
            to_address='1Bob12345678901234567890123456',
            amount=10.0,
        )

    assert result is False
    assert orchestrator.txs_failed == 1


# ──────────────────────────────────────────────────────────
# Tests de _auto_cycle
# ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auto_cycle_needs_at_least_2_addresses(orchestrator):
    """_auto_cycle no hace nada si hay menos de 2 addresses."""
    with patch.object(
        orchestrator, '_get_addresses',
        new=AsyncMock(return_value=[MOCK_ADDRESSES[0]])
    ):
        # No debe lanzar excepción ni enviar TX
        await orchestrator._auto_cycle()
        assert orchestrator.txs_sent == 0


@pytest.mark.asyncio
async def test_auto_cycle_skips_zero_balance(orchestrator):
    """_auto_cycle no envía TX si el remitente tiene balance 0."""
    with patch.object(
        orchestrator, '_get_addresses',
        new=AsyncMock(return_value=MOCK_ADDRESSES)
    ):
        with patch.object(
            orchestrator, '_get_balance',
            new=AsyncMock(return_value=0.0)
        ):
            await orchestrator._auto_cycle()
            assert orchestrator.txs_sent == 0


@pytest.mark.asyncio
async def test_auto_cycle_sends_tx_with_balance(orchestrator):
    """_auto_cycle envía TX cuando el remitente tiene balance."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(
        orchestrator, '_get_addresses',
        new=AsyncMock(return_value=MOCK_ADDRESSES)
    ):
        with patch.object(
            orchestrator, '_get_balance',
            new=AsyncMock(return_value=50.0)
        ):
            with patch('requests.post', return_value=mock_response):
                await orchestrator._auto_cycle()
                assert orchestrator.txs_sent == 1


# ──────────────────────────────────────────────────────────
# Tests de stats
# ──────────────────────────────────────────────────────────

def test_get_stats_structure(orchestrator):
    """get_stats retorna todos los campos esperados."""
    stats = orchestrator.get_stats()

    assert 'mode'         in stats
    assert 'running'      in stats
    assert 'txs_sent'     in stats
    assert 'txs_failed'   in stats
    assert 'last_tx_at'   in stats
    assert 'success_rate' in stats


@pytest.mark.asyncio
async def test_success_rate_calculation(orchestrator):
    """success_rate se calcula correctamente."""
    mock_ok  = MagicMock(status_code=200)
    mock_err = MagicMock(status_code=400, text='error')

    with patch('requests.post', return_value=mock_ok):
        await orchestrator.send_tx('localhost', 5000, '1Bob', 10.0)
        await orchestrator.send_tx('localhost', 5000, '1Bob', 10.0)

    with patch('requests.post', return_value=mock_err):
        await orchestrator.send_tx('localhost', 5000, '1Bob', 10.0)

    stats = orchestrator.get_stats()
    assert stats['txs_sent']    == 2
    assert stats['txs_failed']  == 1
    assert abs(stats['success_rate'] - 2/3) < 0.001


def test_repr(orchestrator):
    """__repr__ retorna string informativo."""
    r = repr(orchestrator)
    assert 'TxOrchestrator' in r
    assert 'mode'           in r
