"""
TxOrchestrator — Orquestador central de transacciones automáticas

Responsabilidad única:
    Decidir quién envía, a quién, cuánto y cuándo — y
    ejecutar esa decisión via el dashboard de cada nodo.

Es un "bot" externo al protocolo P2P:
    - No es un nodo Bitcoin
    - No conoce el protocolo WebSocket
    - Solo hace POST HTTP al dashboard de cada nodo
    - Los nodos no saben si la TX viene de un humano o del orquestador

Modos:
    AUTO   → genera TXs automáticamente con intervalo + jitter
    MANUAL → inactivo, el instructor genera TXs manualmente

El orquestador corre en la máquina del instructor junto con
el seed node y el dashboard global.
"""

import asyncio
import random
import time
import requests
from typing import List, Optional
from utils.logger import setup_logger
from network.seed_client import SeedClient
from config import (
    SEED_HOST, SEED_PORT,
    TX_AUTO_BASE_INTERVAL,
    TX_AUTO_JITTER,
    TX_AUTO_MAX_FRACTION,
    TX_AUTO_START,
)

# Modos del orquestador
ORCH_AUTO   = 'auto'    # Genera TXs automáticamente
ORCH_MANUAL = 'manual'  # Solo cuando el instructor lo pide


class TxOrchestrator:
    """
    Orquestador central de transacciones automáticas.

    Flujo en modo AUTO:
    1. Obtener lista de addresses del seed (GET /addresses)
    2. Elegir remitente y destinatario aleatoriamente
    3. Calcular monto (fracción aleatoria del balance del remitente)
    4. Enviar instrucción al dashboard del remitente (POST /api/tx/create)
    5. El nodo crea, firma y propaga la TX normalmente
    6. Esperar BASE_INTERVAL + random(0, JITTER) segundos
    7. Repetir

    El orquestador no conoce el protocolo P2P — solo HTTP.
    Los nodos no distinguen TXs automáticas de manuales.
    """

    def __init__(
        self,
        seed_host:     str = SEED_HOST,
        seed_port:     int = SEED_PORT,
        dashboard_port: int = 8000,
    ):
        """
        Args:
            seed_host:      IP del seed node.
            seed_port:      Puerto del seed node.
            dashboard_port: Puerto del dashboard de cada nodo.
                            Se asume el mismo en todas las máquinas.
        """
        self.dashboard_port = dashboard_port
        self.mode           = ORCH_AUTO if TX_AUTO_START else ORCH_MANUAL
        self.running        = False

        # SeedClient sin node_id/host/port propios — solo lee del seed
        self.seed_client = SeedClient(
            node_id='orchestrator',
            host='orchestrator',
            port=0,
            seed_host=seed_host,
            seed_port=seed_port,
        )

        # Stats
        self.txs_sent:   int   = 0
        self.txs_failed: int   = 0
        self.last_tx_at: float = 0.0

        self.logger = setup_logger('tx_orchestrator')

    # ──────────────────────────────────────────────────────────
    # Control de modo
    # ──────────────────────────────────────────────────────────

    def set_mode(self, mode: str):
        """
        Cambia el modo del orquestador.

        Args:
            mode: ORCH_AUTO o ORCH_MANUAL
        """
        if mode not in (ORCH_AUTO, ORCH_MANUAL):
            raise ValueError(f"Modo inválido: {mode}")
        old       = self.mode
        self.mode = mode
        self.logger.info(f"[ORCH] Modo: {old} → {mode}")

    # ──────────────────────────────────────────────────────────
    # Loop automático
    # ──────────────────────────────────────────────────────────

    async def start(self):
        """
        Inicia el orquestador en modo AUTO.
        Corre indefinidamente hasta que se llame stop().
        """
        self.running = True
        self.logger.info(
            f"[ORCH] Iniciando en modo {self.mode} "
            f"(intervalo={TX_AUTO_BASE_INTERVAL}s ± {TX_AUTO_JITTER}s)"
        )

        while self.running:
            if self.mode == ORCH_AUTO:
                await self._auto_cycle()

            # Esperar intervalo + jitter
            interval = TX_AUTO_BASE_INTERVAL + random.uniform(0, TX_AUTO_JITTER)
            self.logger.debug(f"[ORCH] Próxima TX en {interval:.1f}s")
            await asyncio.sleep(interval)

    def stop(self):
        """Detiene el loop automático."""
        self.running = False
        self.logger.info("[ORCH] Detenido")

    async def _auto_cycle(self):
        """Un ciclo del modo AUTO: elegir nodos y enviar TX."""
        addresses = await self._get_addresses()

        if len(addresses) < 2:
            self.logger.debug(
                f"[ORCH] Solo {len(addresses)} address(es) conocidas — "
                f"necesito al menos 2 para generar TX"
            )
            return

        # Elegir remitente y destinatario aleatoriamente
        sender    = random.choice(addresses)
        remaining = [a for a in addresses if a['wallet_address'] != sender['wallet_address']]
        recipient = random.choice(remaining)

        # Consultar balance del remitente
        balance = await self._get_balance(sender)

        if balance <= 0:
            self.logger.debug(
                f"[ORCH] {sender['node_id']} sin balance — saltando"
            )
            return

        # Monto: fracción aleatoria del balance disponible
        max_amount = balance * TX_AUTO_MAX_FRACTION
        amount     = round(random.uniform(0.01, max(0.01, max_amount)), 2)

        self.logger.info(
            f"[ORCH] TX automática: {sender['node_id']} → "
            f"{recipient['node_id']} ({amount} coins)"
        )

        await self.send_tx(
            sender_host=sender['host'],
            sender_port=sender['port'],
            to_address=recipient['wallet_address'],
            amount=amount,
            dashboard_port=sender.get('dashboard_port', self.dashboard_port),
        )

    # ──────────────────────────────────────────────────────────
    # Envío manual de TX
    # ──────────────────────────────────────────────────────────

    async def send_tx(
        self,
        sender_host: str,
        sender_port: int,
        to_address:  str,
        amount:      float,
        dashboard_port: int = None,   # ← agregar
    ) -> bool:
        port = dashboard_port or self.dashboard_port  # ← agregar
        dashboard_url = (
            f"http://{sender_host}:{port}"            # ← cambiar self.dashboard_port por port
            f"/api/tx/create"
        )

        try:
            loop     = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    dashboard_url,
                    json={'to_address': to_address, 'amount': amount},
                    timeout=5,
                )
            )

            if response.status_code == 200:
                self.txs_sent   += 1
                self.last_tx_at  = time.time()
                self.logger.info(
                    f"[ORCH] TX enviada a {sender_host}:{sender_port} "
                    f"(total: {self.txs_sent})"
                )
                return True
            else:
                self.txs_failed += 1
                self.logger.warning(
                    f"[ORCH] TX rechazada por {sender_host}:{sender_port}: "
                    f"{response.status_code} — {response.text[:100]}"
                )
                return False

        except requests.exceptions.ConnectionError:
            self.txs_failed += 1
            self.logger.warning(
                f"[ORCH] Nodo no disponible: {sender_host}:{sender_port}"
            )
            return False
        except Exception as e:
            self.txs_failed += 1
            self.logger.error(f"[ORCH] Error enviando TX: {e}")
            return False

    # ──────────────────────────────────────────────────────────
    # Consultas al seed y nodos
    # ──────────────────────────────────────────────────────────

    async def _get_addresses(self) -> List[dict]:
        """Obtiene addresses del seed en executor (requests es síncrono)."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.seed_client.get_addresses
        )

    async def _get_balance(self, node_info: dict) -> float:
        """
        Consulta el balance de un nodo via su dashboard.

        Args:
            node_info: Dict con 'host' y 'port' del nodo.

        Returns:
            Balance del nodo, 0.0 si no está disponible.
        """
        url = (
            f"http://{node_info['host']}:{node_info.get('dashboard_port', self.dashboard_port)}/api/wallet"
        )
        try:
            loop     = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(url, timeout=3)
            )
            if response.status_code == 200:
                return response.json().get('balance', 0.0)
            return 0.0
        except Exception:
            return 0.0

    # ──────────────────────────────────────────────────────────
    # Stats
    # ──────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Retorna estadísticas del orquestador para el dashboard global."""
        return {
            'mode':        self.mode,
            'running':     self.running,
            'txs_sent':    self.txs_sent,
            'txs_failed':  self.txs_failed,
            'last_tx_at':  self.last_tx_at,
            'success_rate': (
                self.txs_sent / (self.txs_sent + self.txs_failed)
                if (self.txs_sent + self.txs_failed) > 0 else 0.0
            ),
        }

    def __repr__(self):
        return (
            f"TxOrchestrator("
            f"mode={self.mode}, "
            f"sent={self.txs_sent}, "
            f"failed={self.txs_failed})"
        )
