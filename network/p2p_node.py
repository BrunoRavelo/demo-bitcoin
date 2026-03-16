"""
Nodo P2P completo
Combina red WebSocket con lógica de blockchain

Cambios Sprint 3.3:
- Recibe Blockchain como dependencia (un solo mempool)
- Integra SeedClient para descubrimiento inicial
- Elimina self.mempool y self.balance hardcoded
- Elimina mensaje 'hello' (era solo para testing)
- self.loop capturado correctamente en start()
- Wallet vive en el nodo (no en Blockchain)
"""

import asyncio
import websockets
import json
from typing import Dict, Set, Optional
from datetime import datetime

from utils.logger import setup_logger
from network.protocol import create_message, validate_message
from network.peer_info import PeerInfo
from network.seed_client import SeedClient
from core.transaction import Transaction
from core.blockchain import Blockchain
from core.wallet import Wallet
from config import (
    MAX_OUTBOUND_CONNECTIONS,
    MAX_INBOUND_CONNECTIONS,
    MAX_PEERS_TO_SHARE,
    GOSSIP_INTERVAL,
    PING_INTERVAL,
    CLEANUP_INTERVAL,
    CONNECT_TIMEOUT,
    SEED_HOST,
    SEED_PORT,
)


class P2PNode:
    """
    Nodo P2P completo: red + blockchain

    Responsabilidades:
    - Servidor WebSocket (recibe conexiones de otros nodos)
    - Cliente WebSocket (se conecta a otros nodos)
    - Gossip protocol (descubrimiento de peers)
    - Propagación de transacciones (bloques en Sprint 4)
    - Delegación de lógica de cadena a Blockchain

    Separación de responsabilidades:
    - P2PNode   → red, wallet propia, coordinación
    - Blockchain → cadena, mempool, validación, balances
    """

    def __init__(
        self,
        host:            str,
        port:            int,
        bootstrap_peers: list,
        blockchain:      Blockchain,
    ):
        """
        Args:
            host:            IP o hostname donde escuchar
            port:            Puerto WebSocket
            bootstrap_peers: Lista de tuplas [(host, port)]
            blockchain:      Instancia de Blockchain compartida
        """
        # ── Identidad ──────────────────────────────────────────
        self.id   = f"node_{port}"
        self.host = host
        self.port = port

        # ── Blockchain (única fuente de verdad) ────────────────
        self.blockchain = blockchain

        # ── Wallet del nodo ────────────────────────────────────
        # La wallet vive en el nodo — Blockchain no gestiona identidades
        self.wallet = Wallet()

        # ── Peers ──────────────────────────────────────────────
        self.peers_connected: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.peers_known:     Dict[str, PeerInfo] = {}

        for b_host, b_port in bootstrap_peers:
            addr = f"{b_host}:{b_port}"
            self.peers_known[addr] = PeerInfo(b_host, b_port)

        # ── Anti-loop ──────────────────────────────────────────
        self.messages_seen:    Set[str] = set()
        self.MAX_MESSAGES_SEEN = 1000

        # ── Límites (estilo Bitcoin) ───────────────────────────
        self.MAX_OUTBOUND_CONNECTIONS = MAX_OUTBOUND_CONNECTIONS
        self.MAX_INBOUND_CONNECTIONS  = MAX_INBOUND_CONNECTIONS
        self.MAX_PEERS_TO_SHARE       = MAX_PEERS_TO_SHARE

        # ── Intervalos ─────────────────────────────────────────
        self.GOSSIP_INTERVAL  = GOSSIP_INTERVAL
        self.PING_INTERVAL    = PING_INTERVAL
        self.CLEANUP_INTERVAL = CLEANUP_INTERVAL

        # ── Seed client ────────────────────────────────────────
        self.seed_client = SeedClient(
            node_id=self.id,
            host=self.host,
            port=self.port,
            seed_host=SEED_HOST,
            seed_port=SEED_PORT,
        )

        # ── Event loop (capturado en start()) ──────────────────
        self.loop: Optional[asyncio.AbstractEventLoop] = None

        # ── Logger ─────────────────────────────────────────────
        self.logger = setup_logger(self.id)

    # ──────────────────────────────────────────────────────────
    # Arranque
    # ──────────────────────────────────────────────────────────

    async def start(self):
        """
        Inicia el nodo:
        1. Captura event loop (para Flask bridge)
        2. Registra en seed y obtiene peers iniciales
        3. Arranca servidor WebSocket
        4. Lanza tareas periódicas
        """
        self.loop = asyncio.get_running_loop()

        self.logger.info(f"[INIT] Iniciando {self.id} en {self.host}:{self.port}")
        self.logger.info(f"[WALLET] Address: {self.wallet.address}")

        await self._bootstrap_from_seed()

        server = await websockets.serve(
            self.handle_incoming_connection,
            self.host,
            self.port,
        )
        self.logger.info(f"[OK] Servidor en ws://{self.host}:{self.port}")

        asyncio.create_task(self.connect_to_bootstrap())
        asyncio.create_task(self.gossip_loop())
        asyncio.create_task(self.ping_loop())
        asyncio.create_task(self.cleanup_loop())
        asyncio.create_task(self.seed_register_loop())

        await asyncio.Future()

    async def _bootstrap_from_seed(self):
        """
        Registra en el seed y agrega los peers que devuelve.
        Usa run_in_executor porque requests es síncrono.
        Falla silenciosamente si el seed no está disponible.
        """
        loop = asyncio.get_running_loop()

        registered = await loop.run_in_executor(None, self.seed_client.register)

        if not registered:
            self.logger.warning("[SEED] No disponible — usando solo bootstrap peers")
            return

        peers_from_seed = await loop.run_in_executor(None, self.seed_client.get_peers)

        for peer_data in peers_from_seed:
            addr = f"{peer_data['host']}:{peer_data['port']}"
            if addr not in self.peers_known:
                self.peers_known[addr] = PeerInfo(
                    peer_data['host'],
                    peer_data['port'],
                    peer_data.get('node_id'),
                )
                self.logger.info(f"[SEED] Peer descubierto: {addr}")

        self.logger.info(
            f"[SEED] {len(peers_from_seed)} peers del seed. "
            f"Total conocidos: {len(self.peers_known)}"
        )

    async def seed_register_loop(self):
        """Re-registra en el seed periódicamente como keep-alive."""
        await asyncio.sleep(30)
        while True:
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self.seed_client.register)
            except Exception as e:
                self.logger.warning(f"[SEED] Error en re-registro: {e}")
            await asyncio.sleep(self.CLEANUP_INTERVAL)

    # ──────────────────────────────────────────────────────────
    # Conexiones entrantes
    # ──────────────────────────────────────────────────────────

    async def handle_incoming_connection(self, websocket, path):
        """Maneja conexión WebSocket entrante de otro nodo."""
        peer_address = None
        try:
            remote = websocket.remote_address
            self.logger.info(f"[INCOMING] Conexión desde {remote}")

            if len(self.peers_connected) >= self.MAX_INBOUND_CONNECTIONS:
                self.logger.warning("[LIMIT] Rechazando — límite alcanzado")
                await websocket.close()
                return

            async for raw_message in websocket:
                msg = json.loads(raw_message)

                if not validate_message(msg):
                    self.logger.warning("[FAIL] Mensaje inválido")
                    continue

                if msg['type'] == 'version':
                    node_id   = msg['payload']['node_id']
                    peer_host = msg['payload'].get('host', remote[0])
                    peer_port = msg['payload'].get('port', 0)
                    peer_address = f"{peer_host}:{peer_port}"

                    self.peers_connected[peer_address] = websocket
                    if peer_address not in self.peers_known:
                        self.peers_known[peer_address] = PeerInfo(
                            peer_host, peer_port, node_id
                        )
                    self.peers_known[peer_address].mark_connected()
                    self.logger.info(f"[CONNECTED] {peer_address} ({node_id})")

                    verack = create_message('verack', {'node_id': self.id})
                    await websocket.send(json.dumps(verack))
                else:
                    await self.handle_message(msg, websocket)

        except websockets.exceptions.ConnectionClosed:
            self.logger.warning(f"[DISCONNECT] {peer_address}")
        except Exception as e:
            self.logger.error(f"[ERROR] Conexión entrante: {e}")
        finally:
            if peer_address:
                self.peers_connected.pop(peer_address, None)
                if peer_address in self.peers_known:
                    self.peers_known[peer_address].mark_disconnected()
                self.logger.info(f"[REMOVED] {peer_address}")

    # ──────────────────────────────────────────────────────────
    # Conexiones salientes
    # ──────────────────────────────────────────────────────────

    async def connect_to_bootstrap(self):
        """Conecta a peers conocidos respetando el límite outbound."""
        await asyncio.sleep(2)
        self.logger.info("[SEARCH] Conectando a peers conocidos...")

        for addr, peer_info in list(self.peers_known.items()):
            if (peer_info.port == self.port and
                    peer_info.host in ('localhost', '127.0.0.1', self.host)):
                continue
            if peer_info.is_connected:
                continue
            outbound = sum(1 for p in self.peers_known.values() if p.is_connected)
            if outbound >= self.MAX_OUTBOUND_CONNECTIONS:
                break
            await self.connect_to_peer(peer_info)

    async def connect_to_peer(self, peer_info: PeerInfo):
        """Intenta conexión WebSocket con un peer específico."""
        uri = f"ws://{peer_info.host}:{peer_info.port}"
        try:
            self.logger.info(f"[CONNECT] {uri}...")
            peer_info.mark_attempt()

            websocket = await asyncio.wait_for(
                websockets.connect(uri), timeout=CONNECT_TIMEOUT
            )

            version_msg = create_message('version', {
                'node_id': self.id,
                'version': '1.0',
                'host':    self.host,
                'port':    self.port,
            })
            await websocket.send(json.dumps(version_msg))

            response = await asyncio.wait_for(
                websocket.recv(), timeout=CONNECT_TIMEOUT
            )
            verack = json.loads(response)

            if verack['type'] == 'verack':
                addr = peer_info.get_address()
                self.peers_connected[addr] = websocket
                peer_info.mark_connected()
                self.logger.info(f"[CONNECTED] {addr}")

                asyncio.create_task(self.listen_to_peer(websocket, addr))
                await self.request_peers(websocket)

        except asyncio.TimeoutError:
            self.logger.warning(f"[TIMEOUT] {uri}")
            peer_info.mark_failure()
        except Exception as e:
            self.logger.warning(f"[FAIL] {uri}: {e}")
            peer_info.mark_failure()

    async def listen_to_peer(self, websocket, peer_address: str):
        """Escucha mensajes de un peer con el que iniciamos la conexión."""
        try:
            async for raw_message in websocket:
                msg = json.loads(raw_message)
                if validate_message(msg):
                    await self.handle_message(msg, websocket)
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning(f"[DISCONNECT] {peer_address}")
        except Exception as e:
            self.logger.error(f"[ERROR] Escuchando a {peer_address}: {e}")
        finally:
            self.peers_connected.pop(peer_address, None)
            if peer_address in self.peers_known:
                self.peers_known[peer_address].mark_disconnected()

    # ──────────────────────────────────────────────────────────
    # Router de mensajes
    # ──────────────────────────────────────────────────────────

    async def handle_message(self, msg: dict, sender_ws):
        """Despacha mensajes. Anti-loop: ignora IDs ya procesados."""
        msg_id   = msg['id']
        msg_type = msg['type']

        if msg_id in self.messages_seen:
            return
        self.messages_seen.add(msg_id)

        if len(self.messages_seen) > self.MAX_MESSAGES_SEEN:
            self.messages_seen = set(list(self.messages_seen)[-500:])

        self.logger.debug(f"[MSG] {msg_type} (id={msg_id[:8]}...)")

        if   msg_type == 'ping':    await self._handle_ping(msg, sender_ws)
        elif msg_type == 'pong':    pass
        elif msg_type == 'getaddr': await self.handle_getaddr(sender_ws)
        elif msg_type == 'addr':    await self.handle_addr(msg['payload'])
        elif msg_type == 'tx':      await self.handle_tx(msg, sender_ws)
        else:
            self.logger.debug(f"[MSG] Tipo desconocido: {msg_type}")

    # ──────────────────────────────────────────────────────────
    # Handlers individuales
    # ──────────────────────────────────────────────────────────

    async def _handle_ping(self, msg: dict, sender_ws):
        pong = create_message('pong', {'nonce': msg['payload']['nonce']})
        await sender_ws.send(json.dumps(pong))

    async def handle_getaddr(self, sender_ws):
        now = datetime.now().timestamp()
        valid = [
            p for p in self.peers_known.values()
            if p.is_connected or (now - p.last_seen < 3600)
        ]
        valid.sort(key=lambda p: p.last_seen, reverse=True)
        share = valid[:self.MAX_PEERS_TO_SHARE]

        msg = create_message('addr', {
            'peers': [p.to_dict() for p in share],
            'count': len(share),
        })
        await sender_ws.send(json.dumps(msg))
        self.logger.debug(f"[ADDR] Enviados {len(share)} peers")

    async def handle_addr(self, payload: dict):
        peers_data = payload.get('peers', [])
        new_count  = 0

        for peer_data in peers_data:
            addr = f"{peer_data['host']}:{peer_data['port']}"
            if (peer_data['port'] == self.port and
                    peer_data['host'] in ('localhost', '127.0.0.1', self.host)):
                continue
            if addr not in self.peers_known:
                self.peers_known[addr] = PeerInfo.from_dict(peer_data)
                new_count += 1
                self.logger.info(f"[GOSSIP] Nuevo peer: {addr}")
            else:
                self.peers_known[addr].last_seen = peer_data.get(
                    'last_seen', datetime.now().timestamp()
                )

        if new_count > 0:
            self.logger.info(
                f"[GOSSIP] {new_count} nuevos. Total: {len(self.peers_known)}"
            )
            await self.connect_to_bootstrap()

    # ──────────────────────────────────────────────────────────
    # Transacciones
    # ──────────────────────────────────────────────────────────

    async def handle_tx(self, msg: dict, sender_ws):
        """
        TX recibida de la red.
        Delega validación y almacenamiento a Blockchain (un solo mempool).
        """
        try:
            tx = Transaction.from_dict(msg['payload'])
            accepted = self.blockchain.add_transaction_to_mempool(tx)

            if accepted:
                self.logger.info(
                    f"[TX] Aceptada: {tx.short_hash()} ({tx.amount} coins)"
                )
                await self.broadcast_transaction(tx, exclude_ws=sender_ws)
            else:
                self.logger.debug(f"[TX] Rechazada: {tx.short_hash()}")

        except Exception as e:
            self.logger.error(f"[TX] Error: {e}")

    async def broadcast_transaction(self, tx: Transaction, exclude_ws=None):
        """Propaga una TX firmada a todos los peers."""
        msg = create_message('tx', tx.to_dict())
        await self.broadcast_message(msg, exclude_ws=exclude_ws)

    def create_transaction(self, to_address: str, amount: float) -> Transaction:
        """
        Crea, firma y agrega al mempool una TX desde este nodo.

        Raises:
            ValueError: Balance insuficiente.
        """
        if not self.blockchain.has_sufficient_balance(self.wallet.address, amount):
            raise ValueError(
                f"Balance insuficiente: "
                f"tienes {self.get_balance():.2f}, "
                f"intentas enviar {amount}"
            )

        tx = Transaction(
            from_address=self.wallet.address,
            to_address=to_address,
            amount=amount,
        )
        tx.sign(self.wallet)
        self.blockchain.add_transaction_to_mempool(tx)

        self.logger.info(
            f"[TX] Creada: {tx.short_hash()} ({amount} → {to_address[:12]}...)"
        )
        return tx

    def get_balance(self) -> float:
        """Balance real desde la blockchain (no del mempool)."""
        return self.blockchain.get_balance(self.wallet.address)

    # ──────────────────────────────────────────────────────────
    # Broadcast genérico y utilidades
    # ──────────────────────────────────────────────────────────

    async def broadcast_message(self, msg: dict, exclude_ws=None):
        """Envía un mensaje a todos los peers conectados."""
        count = 0
        for addr, ws in list(self.peers_connected.items()):
            if ws == exclude_ws:
                continue
            try:
                await ws.send(json.dumps(msg))
                count += 1
            except Exception as e:
                self.logger.error(f"[BROADCAST] Error a {addr}: {e}")
        self.logger.debug(f"[BROADCAST] Enviado a {count} peers")

    async def request_peers(self, websocket):
        """Solicita lista de peers a un peer conectado."""
        getaddr = create_message('getaddr', {})
        await websocket.send(json.dumps(getaddr))

    # ──────────────────────────────────────────────────────────
    # Loops periódicos
    # ──────────────────────────────────────────────────────────

    async def gossip_loop(self):
        await asyncio.sleep(10)
        while True:
            try:
                for addr, ws in list(self.peers_connected.items()):
                    try:
                        await self.request_peers(ws)
                    except Exception:
                        pass
                self.logger.info(
                    f"[GOSSIP] Conocidos: {len(self.peers_known)}, "
                    f"Conectados: {len(self.peers_connected)}"
                )
            except Exception as e:
                self.logger.error(f"[GOSSIP] Error: {e}")
            await asyncio.sleep(self.GOSSIP_INTERVAL)

    async def ping_loop(self):
        await asyncio.sleep(15)
        while True:
            try:
                for addr, ws in list(self.peers_connected.items()):
                    try:
                        ping = create_message('ping', {
                            'nonce': int(datetime.now().timestamp())
                        })
                        await ws.send(json.dumps(ping))
                    except Exception as e:
                        self.logger.warning(f"[PING] Falló a {addr}: {e}")
            except Exception as e:
                self.logger.error(f"[PING] Error: {e}")
            await asyncio.sleep(self.PING_INTERVAL)

    async def cleanup_loop(self):
        while True:
            await asyncio.sleep(self.CLEANUP_INTERVAL)
            try:
                old = len(self.messages_seen)
                self.messages_seen = set(list(self.messages_seen)[-500:])

                now = datetime.now().timestamp()
                to_remove = [
                    addr for addr, peer in self.peers_known.items()
                    if not peer.is_connected and (now - peer.last_seen) > 86400
                ]
                for addr in to_remove:
                    del self.peers_known[addr]

                self.logger.info(
                    f"[CLEANUP] Mensajes: {old}→{len(self.messages_seen)}, "
                    f"Peers eliminados: {len(to_remove)}"
                )
            except Exception as e:
                self.logger.error(f"[CLEANUP] Error: {e}")

    def __repr__(self):
        return (
            f"P2PNode(id={self.id}, "
            f"peers={len(self.peers_connected)}, "
            f"chain={len(self.blockchain.chain)}, "
            f"mempool={len(self.blockchain.mempool)})"
        )
