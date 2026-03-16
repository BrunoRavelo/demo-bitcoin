"""
Nodo P2P completo
Combina red WebSocket con lógica de blockchain

Sprint 4.1/4.2:
- Handlers para MSG_BLOCK, MSG_INV, MSG_GETBLOCKS
- broadcast_block() para propagar bloques minados
- Sincronización de cadena al conectar a un peer nuevo
- Longest chain rule via blockchain.replace_chain()
"""

import asyncio
import websockets
import json
from typing import Dict, Set, Optional
from datetime import datetime

from utils.logger import setup_logger
from network.protocol import (
    create_message, validate_message,
    MSG_VERSION, MSG_VERACK, MSG_PING, MSG_PONG,
    MSG_GETADDR, MSG_ADDR, MSG_TX,
    MSG_INV, MSG_GETBLOCKS, MSG_BLOCK,
)
from network.peer_info import PeerInfo
from network.seed_client import SeedClient
from core.transaction import Transaction
from core.block import Block
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
    Nodo P2P completo: red + blockchain.

    Responsabilidades:
    - Servidor/cliente WebSocket
    - Gossip protocol
    - Propagación de TXs y bloques
    - Sincronización de cadena al conectar
    - Longest chain rule via Blockchain.replace_chain()
    """

    def __init__(
        self,
        host:            str,
        port:            int,
        bootstrap_peers: list,
        blockchain:      Blockchain,
    ):
        self.id   = f"node_{port}"
        self.host = host
        self.port = port

        self.blockchain = blockchain
        self.wallet     = Wallet()

        self.peers_connected: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.peers_known:     Dict[str, PeerInfo] = {}

        for b_host, b_port in bootstrap_peers:
            addr = f"{b_host}:{b_port}"
            self.peers_known[addr] = PeerInfo(b_host, b_port)

        self.messages_seen:    Set[str] = set()
        self.MAX_MESSAGES_SEEN = 1000

        self.MAX_OUTBOUND_CONNECTIONS = MAX_OUTBOUND_CONNECTIONS
        self.MAX_INBOUND_CONNECTIONS  = MAX_INBOUND_CONNECTIONS
        self.MAX_PEERS_TO_SHARE       = MAX_PEERS_TO_SHARE

        self.GOSSIP_INTERVAL  = GOSSIP_INTERVAL
        self.PING_INTERVAL    = PING_INTERVAL
        self.CLEANUP_INTERVAL = CLEANUP_INTERVAL

        self.seed_client = SeedClient(
            node_id=self.id,
            host=self.host,
            port=self.port,
            seed_host=SEED_HOST,
            seed_port=SEED_PORT,
        )

        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.logger = setup_logger(self.id)

    # ──────────────────────────────────────────────────────────
    # Arranque
    # ──────────────────────────────────────────────────────────

    async def start(self):
        self.loop = asyncio.get_running_loop()

        self.logger.info(f"[INIT] Iniciando {self.id} en {self.host}:{self.port}")
        self.logger.info(f"[WALLET] Address: {self.wallet.address}")
        self.logger.info(f"[CHAIN] Altura inicial: {self.blockchain.get_height()}")

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

                if msg['type'] == MSG_VERSION:
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

                    verack = create_message(MSG_VERACK, {'node_id': self.id})
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
        uri = f"ws://{peer_info.host}:{peer_info.port}"
        try:
            self.logger.info(f"[CONNECT] {uri}...")
            peer_info.mark_attempt()

            websocket = await asyncio.wait_for(
                websockets.connect(uri), timeout=CONNECT_TIMEOUT
            )

            version_msg = create_message(MSG_VERSION, {
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

            if verack['type'] == MSG_VERACK:
                addr = peer_info.get_address()
                self.peers_connected[addr] = websocket
                peer_info.mark_connected()
                self.logger.info(f"[CONNECTED] {addr}")

                asyncio.create_task(self.listen_to_peer(websocket, addr))
                await self.request_peers(websocket)

                # ── Sincronización de cadena al conectar ──────
                # Solicitar cadena del peer para aplicar longest chain rule
                await self._request_chain_sync(websocket)

        except asyncio.TimeoutError:
            self.logger.warning(f"[TIMEOUT] {uri}")
            peer_info.mark_failure()
        except Exception as e:
            self.logger.warning(f"[FAIL] {uri}: {e}")
            peer_info.mark_failure()

    async def listen_to_peer(self, websocket, peer_address: str):
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
        """Despacha mensajes. Anti-loop por msg_id."""
        msg_id   = msg['id']
        msg_type = msg['type']

        if msg_id in self.messages_seen:
            return
        self.messages_seen.add(msg_id)

        if len(self.messages_seen) > self.MAX_MESSAGES_SEEN:
            self.messages_seen = set(list(self.messages_seen)[-500:])

        self.logger.debug(f"[MSG] {msg_type} (id={msg_id[:8]}...)")

        if   msg_type == MSG_PING:      await self._handle_ping(msg, sender_ws)
        elif msg_type == MSG_PONG:      pass
        elif msg_type == MSG_GETADDR:   await self.handle_getaddr(sender_ws)
        elif msg_type == MSG_ADDR:      await self.handle_addr(msg['payload'])
        elif msg_type == MSG_TX:        await self.handle_tx(msg, sender_ws)
        elif msg_type == MSG_BLOCK:     await self.handle_block(msg, sender_ws)
        elif msg_type == MSG_INV:       await self.handle_inv(msg, sender_ws)
        elif msg_type == MSG_GETBLOCKS: await self.handle_getblocks(sender_ws)
        else:
            self.logger.debug(f"[MSG] Tipo desconocido: {msg_type}")

    # ──────────────────────────────────────────────────────────
    # Handlers — red y gossip
    # ──────────────────────────────────────────────────────────

    async def _handle_ping(self, msg: dict, sender_ws):
        pong = create_message(MSG_PONG, {'nonce': msg['payload']['nonce']})
        await sender_ws.send(json.dumps(pong))

    async def handle_getaddr(self, sender_ws):
        now = datetime.now().timestamp()
        valid = [
            p for p in self.peers_known.values()
            if p.is_connected or (now - p.last_seen < 3600)
        ]
        valid.sort(key=lambda p: p.last_seen, reverse=True)
        share = valid[:self.MAX_PEERS_TO_SHARE]

        msg = create_message(MSG_ADDR, {
            'peers': [p.to_dict() for p in share],
            'count': len(share),
        })
        await sender_ws.send(json.dumps(msg))

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
    # Handlers — bloques (Sprint 4)
    # ──────────────────────────────────────────────────────────

    async def handle_block(self, msg: dict, sender_ws):
        """
        Procesa un bloque recibido de la red.

        Flujo:
        1. Deserializar bloque
        2. Intentar agregar directamente (conecta con nuestro tip)
        3. Si no conecta → solicitar cadena completa al peer
           para aplicar longest chain rule
        4. Si se aceptó → propagarlo al resto de la red
        """
        try:
            block_data = msg['payload']
            block      = Block.from_dict(block_data)
            block_hash = block.hash

            self.logger.info(
                f"[BLOCK] Recibido: {block_hash[:16]}... "
                f"(prev={block.header.prev_hash[:16]}..., "
                f"txs={len(block.transactions)})"
            )

            # Intentar agregar directamente
            if self.blockchain.add_block(block):
                self.logger.info(
                    f"[BLOCK] Aceptado en altura {self.blockchain.get_height()}"
                )
                # Propagar al resto de la red (excepto quien lo envió)
                await self.broadcast_block(block, exclude_ws=sender_ws)

            else:
                # No conectó con nuestro tip — puede ser fork
                # Solicitar cadena completa para aplicar longest chain rule
                self.logger.info(
                    f"[BLOCK] No conecta con nuestro tip "
                    f"(altura={self.blockchain.get_height()}) — "
                    f"solicitando cadena completa"
                )
                await self._request_chain_sync(sender_ws)

        except Exception as e:
            self.logger.error(f"[BLOCK] Error procesando bloque: {e}")

    async def handle_inv(self, msg: dict, sender_ws):
        """
        Procesa anuncio INV: el peer nos avisa que tiene un bloque nuevo.

        INV es más eficiente que enviar el bloque completo directamente:
        el peer anuncia el hash, nosotros pedimos el bloque completo
        solo si no lo tenemos.

        En Bitcoin real: inv → getdata → block
        En nuestro demo: inv → getblocks (pedimos cadena completa si el
        hash no está en nuestra cadena)
        """
        try:
            inv_hash   = msg['payload'].get('hash')
            inv_height = msg['payload'].get('height', 0)

            if not inv_hash:
                return

            # Si ya tenemos ese bloque, ignorar
            if self.blockchain.get_block_by_hash(inv_hash):
                self.logger.debug(f"[INV] Bloque ya conocido: {inv_hash[:16]}...")
                return

            # Si el peer tiene más bloques que nosotros, sincronizar
            if inv_height > self.blockchain.get_height():
                self.logger.info(
                    f"[INV] Peer tiene bloque {inv_hash[:16]}... "
                    f"(altura {inv_height} > nuestra {self.blockchain.get_height()}) "
                    f"— sincronizando"
                )
                await self._request_chain_sync(sender_ws)

        except Exception as e:
            self.logger.error(f"[INV] Error: {e}")

    async def handle_getblocks(self, sender_ws):
        """
        Responde a getblocks enviando nuestra cadena completa.

        En Bitcoin real: getblocks → inv (lista de hashes) → getdata → blocks
        En nuestro demo: getblocks → block (cadena completa serializada)
        Simplificación válida para redes pequeñas (<100 bloques).
        """
        try:
            chain_data = self.blockchain.get_chain_as_dicts()

            msg = create_message(MSG_BLOCK, {
                'chain':  chain_data,
                'height': self.blockchain.get_height(),
                'type':   'full_chain',
            })
            await sender_ws.send(json.dumps(msg))

            self.logger.info(
                f"[GETBLOCKS] Cadena enviada: {self.blockchain.get_height()} bloques"
            )

        except Exception as e:
            self.logger.error(f"[GETBLOCKS] Error enviando cadena: {e}")

    async def _request_chain_sync(self, websocket):
        """
        Solicita la cadena completa a un peer para sincronizar.
        Si la cadena recibida es más larga y válida, reemplaza la nuestra.
        """
        try:
            getblocks_msg = create_message(MSG_GETBLOCKS, {
                'height': self.blockchain.get_height(),
            })
            await websocket.send(json.dumps(getblocks_msg))
            self.logger.debug(
                f"[SYNC] getblocks enviado "
                f"(nuestra altura: {self.blockchain.get_height()})"
            )
        except Exception as e:
            self.logger.error(f"[SYNC] Error solicitando cadena: {e}")

    def _process_full_chain(self, chain_data: list) -> bool:
        """
        Procesa una cadena completa recibida vía getblocks.
        Aplica longest chain rule.

        Args:
            chain_data: Lista de dicts de bloques.

        Returns:
            True si la cadena fue aceptada y reemplazó la nuestra.
        """
        try:
            new_chain = Blockchain.chain_from_dicts(chain_data)
            replaced  = self.blockchain.replace_chain(new_chain)

            if replaced:
                self.logger.info(
                    f"[SYNC] Cadena reemplazada. "
                    f"Nueva altura: {self.blockchain.get_height()}"
                )
            else:
                self.logger.debug(
                    f"[SYNC] Nuestra cadena sigue siendo la más larga "
                    f"({self.blockchain.get_height()} bloques)"
                )

            return replaced

        except Exception as e:
            self.logger.error(f"[SYNC] Error procesando cadena: {e}")
            return False

    # ──────────────────────────────────────────────────────────
    # Broadcast de bloques
    # ──────────────────────────────────────────────────────────

    async def broadcast_block(self, block: Block, exclude_ws=None):
        """
        Propaga un bloque minado a todos los peers conectados.

        Flujo Bitcoin real: minar → inv (anunciar hash) → peers piden con getdata
        Nuestro demo: minar → block (enviar completo directamente)
        Simplificación válida para bloques pequeños en red LAN.

        Args:
            block:      Bloque a propagar.
            exclude_ws: WebSocket a excluir (quien nos lo envió).
        """
        # Anunciar primero con INV (hash + altura)
        inv_msg = create_message(MSG_INV, {
            'hash':   block.hash,
            'height': self.blockchain.get_height(),
        })
        await self.broadcast_message(inv_msg, exclude_ws=exclude_ws)

        # Enviar bloque completo
        block_msg = create_message(MSG_BLOCK, block.to_dict())
        await self.broadcast_message(block_msg, exclude_ws=exclude_ws)

        self.logger.info(
            f"[BROADCAST] Bloque {block.hash[:16]}... "
            f"propagado a {len(self.peers_connected)} peers"
        )

    # ──────────────────────────────────────────────────────────
    # Handlers — transacciones
    # ──────────────────────────────────────────────────────────

    async def handle_tx(self, msg: dict, sender_ws):
        try:
            tx       = Transaction.from_dict(msg['payload'])
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
        msg = create_message(MSG_TX, tx.to_dict())
        await self.broadcast_message(msg, exclude_ws=exclude_ws)

    def create_transaction(self, to_address: str, amount: float) -> Transaction:
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
        return self.blockchain.get_balance(self.wallet.address)

    # ──────────────────────────────────────────────────────────
    # Broadcast genérico y utilidades
    # ──────────────────────────────────────────────────────────

    async def broadcast_message(self, msg: dict, exclude_ws=None):
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
        getaddr = create_message(MSG_GETADDR, {})
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
                        ping = create_message(MSG_PING, {
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
            f"height={self.blockchain.get_height()}, "
            f"mempool={len(self.blockchain.mempool)})"
        )
