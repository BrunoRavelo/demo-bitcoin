"""
Implementa descubrimiento de peers estilo Bitcoin
"""

import asyncio
import websockets
import json
from typing import Dict, Set, List
from datetime import datetime, timedelta

from utils.logger import setup_logger
from network.protocol import create_message, validate_message
from network.peer_info import PeerInfo
from core.transaction import Transaction  # ← AGREGAR
from core.wallet import Wallet  # ← AGREGAR


class P2PNode:
    """
    Nodo P2P con capacidades de:
    - Servidor y cliente simultáneo
    - Gossip protocol para descubrimiento
    - Keep-alive con ping/pong
    """
    
    def __init__(self, host: str, port: int, bootstrap_peers: list):
        """
        Inicializa un nodo P2P
        
        Args:
            host: IP o hostname
            port: Puerto para escuchar
            bootstrap_peers: Lista de tuplas [(host, port)] iniciales
        """
        # Identificación basada en puerto (logs consistentes)
        self.id = f"node_{port}"
        self.host = host
        self.port = port
        
        # Peers conectados activamente
        # Formato: {peer_address: websocket}
        self.peers_connected: Dict[str, websockets.WebSocketServerProtocol] = {}
        
        # Todos los peers conocidos (conectados o no)
        # Formato: {peer_address: PeerInfo}
        self.peers_known: Dict[str, PeerInfo] = {}
        
        # Bootstrap peers
        for host, port in bootstrap_peers:
            addr = f"{host}:{port}"
            self.peers_known[addr] = PeerInfo(host, port)
        
        # Control de mensajes (anti-loop)
        self.messages_seen: Set[str] = set()
        self.MAX_MESSAGES_SEEN = 1000
        
        # Límites de red (estilo Bitcoin)
        self.MAX_OUTBOUND_CONNECTIONS = 8   # Conexiones salientes
        self.MAX_INBOUND_CONNECTIONS = 125  # Conexiones entrantes
        self.MAX_PEERS_TO_SHARE = 10        # Peers a compartir en addr
        
        # Intervalos de tiempo
        self.GOSSIP_INTERVAL = 60           # Solicitar peers cada 60s
        self.PING_INTERVAL = 30             # Ping cada 30s
        self.CLEANUP_INTERVAL = 300         # Limpiar cada 5 min
        
        # Wallet y mempool (NUEVO)
        self.wallet = Wallet()
        self.mempool: List[Transaction] = []
        self.balance = 100.0  # Balance inicial hardcoded
        
        # Logger
        self.logger = setup_logger(self.id)
        
    async def start(self):
        """Inicia el nodo: servidor + tareas periódicas"""
        self.logger.info(f"[INIT] Iniciando nodo {self.id} en {self.host}:{self.port}")
        
        # Iniciar servidor WebSocket
        server = await websockets.serve(
            self.handle_incoming_connection,
            self.host,
            self.port
        )
        
        self.logger.info(f"[OK] Servidor escuchando en ws://{self.host}:{self.port}")
        
        # Tareas en background
        asyncio.create_task(self.connect_to_bootstrap())
        asyncio.create_task(self.gossip_loop())
        asyncio.create_task(self.ping_loop())
        asyncio.create_task(self.cleanup_loop())
        
        # Mantener servidor corriendo
        await asyncio.Future()
    
    async def handle_incoming_connection(self, websocket, path):
        """
        Maneja conexión entrante de otro peer
        """
        peer_address = None
        
        try:
            remote = websocket.remote_address
            self.logger.info(f"[INCOMING] Conexión desde {remote}")
            
            # Verificar límite de conexiones entrantes
            if len(self.peers_connected) >= self.MAX_INBOUND_CONNECTIONS:
                self.logger.warning(f"[LIMIT] Rechazando conexión (límite alcanzado)")
                await websocket.close()
                return
            
            # Escuchar mensajes
            async for raw_message in websocket:
                msg = json.loads(raw_message)
                
                if not validate_message(msg):
                    self.logger.warning(f"[FAIL] Mensaje inválido")
                    continue
                
                # Handshake
                if msg['type'] == 'version':
                    node_id = msg['payload']['node_id']
                    peer_host = msg['payload'].get('host', remote[0])
                    peer_port = msg['payload'].get('port', 0)
                    
                    peer_address = f"{peer_host}:{peer_port}"
                    self.peers_connected[peer_address] = websocket
                    
                    # Actualizar peers_known
                    if peer_address not in self.peers_known:
                        self.peers_known[peer_address] = PeerInfo(peer_host, peer_port, node_id)
                    
                    self.peers_known[peer_address].mark_connected()
                    
                    self.logger.info(f"[SUCCESS] Peer conectado: {peer_address}")
                    
                    # Responder VERACK
                    verack = create_message('verack', {'node_id': self.id})
                    await websocket.send(json.dumps(verack))
                    
                else:
                    await self.handle_message(msg, websocket)
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning(f"[DISCONNECT] Conexión cerrada: {peer_address}")
        except Exception as e:
            self.logger.error(f"[ERROR] Error en conexión: {e}")
        finally:
            if peer_address:
                if peer_address in self.peers_connected:
                    del self.peers_connected[peer_address]
                if peer_address in self.peers_known:
                    self.peers_known[peer_address].mark_disconnected()
                self.logger.info(f"[REMOVED] Peer removido: {peer_address}")
    
    async def connect_to_bootstrap(self):
        """Conecta a peers bootstrap y conocidos"""
        await asyncio.sleep(2)  # Esperar a que servidor inicie
        
        self.logger.info(f"[SEARCH] Conectando a peers conocidos...")
        
        # Intentar conectar a todos los peers conocidos no conectados
        for addr, peer_info in list(self.peers_known.items()):
            # No conectar a sí mismo
            if peer_info.port == self.port and peer_info.host in ['localhost', '127.0.0.1', self.host]:
                continue
            
            # No reconectar si ya está conectado
            if peer_info.is_connected:
                continue
            
            # Límite de conexiones salientes
            outbound = sum(1 for p in self.peers_known.values() if p.is_connected)
            if outbound >= self.MAX_OUTBOUND_CONNECTIONS:
                break
            
            await self.connect_to_peer(peer_info)
    
    async def connect_to_peer(self, peer_info: PeerInfo):
        """Intenta conectar a un peer específico"""
        uri = f"ws://{peer_info.host}:{peer_info.port}"
        
        try:
            self.logger.info(f"[CONNECT] Intentando conectar a {uri}")
            peer_info.mark_attempt()
            
            websocket = await asyncio.wait_for(
                websockets.connect(uri),
                timeout=5.0
            )
            
            # Enviar VERSION
            version_msg = create_message('version', {
                'node_id': self.id,
                'version': '1.0',
                'host': self.host,
                'port': self.port
            })
            await websocket.send(json.dumps(version_msg))
            
            # Esperar VERACK
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            verack = json.loads(response)
            
            if verack['type'] == 'verack':
                addr = peer_info.get_address()
                self.peers_connected[addr] = websocket
                peer_info.mark_connected()
                
                self.logger.info(f"[SUCCESS] Conectado a {addr}")
                
                # Iniciar listener
                asyncio.create_task(self.listen_to_peer(websocket, addr))
                
                # Solicitar peers inmediatamente
                await self.request_peers(websocket)
                
        except asyncio.TimeoutError:
            self.logger.error(f"[TIMEOUT] Timeout conectando a {uri}")
            peer_info.mark_failure()
        except Exception as e:
            self.logger.error(f"[FAIL] No se pudo conectar a {uri} - {e}")
            peer_info.mark_failure()
    
    async def listen_to_peer(self, websocket, peer_address: str):
        """Escucha mensajes de un peer específico"""
        try:
            async for raw_message in websocket:
                msg = json.loads(raw_message)
                
                if validate_message(msg):
                    await self.handle_message(msg, websocket)
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning(f"[DISCONNECT] Peer desconectado: {peer_address}")
        except Exception as e:
            self.logger.error(f"[ERROR] Error escuchando a {peer_address}: {e}")
        finally:
            if peer_address in self.peers_connected:
                del self.peers_connected[peer_address]
            if peer_address in self.peers_known:
                self.peers_known[peer_address].mark_disconnected()
    
    async def handle_message(self, msg: dict, sender_ws):
        """Procesa un mensaje recibido"""
        msg_id = msg['id']
        msg_type = msg['type']
        
        # Anti-loop
        if msg_id in self.messages_seen:
            return
        
        self.messages_seen.add(msg_id)
        
        # Limpiar si crece mucho
        if len(self.messages_seen) > self.MAX_MESSAGES_SEEN:
            # Mantener solo los últimos 500
            self.messages_seen = set(list(self.messages_seen)[-500:])
        
        self.logger.info(f"[MSG] Mensaje recibido: {msg_type} (ID: {msg_id[:8]}...)")
        
        # Router de mensajes
        if msg_type == 'ping':
            await self.handle_ping(msg, sender_ws)
        
        elif msg_type == 'pong':
            self.logger.info(f"[PONG] PONG recibido")
        
        elif msg_type == 'getaddr':
            await self.handle_getaddr(sender_ws)
        
        elif msg_type == 'addr':
            await self.handle_addr(msg['payload'])

        elif msg_type == 'hello':
            data = msg['payload'].get('data', '')
            self.logger.info(f"[HELLO] HELLO recibido: {data}")
            await self.broadcast_message(msg, exclude_ws=sender_ws)
        
        elif msg_type == 'tx':  # ← AGREGAR
            await self.handle_tx(msg, sender_ws)
        
        else:
            self.logger.warning(f"[WARN] Tipo de mensaje desconocido: {msg_type}")
    
    async def handle_ping(self, msg: dict, sender_ws):
        """Responde a un PING"""
        pong = create_message('pong', {
            'nonce': msg['payload']['nonce']
        })
        await sender_ws.send(json.dumps(pong))
        self.logger.info(f"[PONG] PONG enviado")
    
    async def handle_getaddr(self, sender_ws):
        """
        Responde con lista de peers conocidos
        Estilo Bitcoin: máximo 10 peers, ordenados por last_seen
        """
        # Filtrar peers válidos (excluyendo el que pregunta)
        valid_peers = [
            p for p in self.peers_known.values()
            if p.is_connected or (datetime.now().timestamp() - p.last_seen < 3600)  # Últimas 1 hora
        ]
        
        # Ordenar por last_seen (más recientes primero)
        valid_peers.sort(key=lambda p: p.last_seen, reverse=True)
        
        # Máximo 10 peers
        peers_to_share = valid_peers[:self.MAX_PEERS_TO_SHARE]
        
        # Serializar
        peers_data = [p.to_dict() for p in peers_to_share]
        
        addr_msg = create_message('addr', {
            'peers': peers_data,
            'count': len(peers_data)
        })
        
        await sender_ws.send(json.dumps(addr_msg))
        self.logger.info(f"[ADDR] Enviados {len(peers_data)} peers")
    
    async def handle_addr(self, payload: dict):
        """
        Procesa lista de peers recibida
        Agrega nuevos peers a peers_known
        """
        peers_data = payload.get('peers', [])
        new_count = 0
        
        for peer_data in peers_data:
            addr = f"{peer_data['host']}:{peer_data['port']}"
            
            # No agregar a sí mismo
            if peer_data['port'] == self.port and peer_data['host'] in ['localhost', '127.0.0.1', self.host]:
                continue
            
            # Si no lo conocemos, agregarlo
            if addr not in self.peers_known:
                peer_info = PeerInfo.from_dict(peer_data)
                self.peers_known[addr] = peer_info
                new_count += 1
                self.logger.info(f"[NEW PEER] Descubierto: {addr}")
            else:
                # Actualizar last_seen
                self.peers_known[addr].last_seen = peer_data.get('last_seen', datetime.now().timestamp())
        
        if new_count > 0:
            self.logger.info(f"[GOSSIP] {new_count} nuevos peers descubiertos. Total conocidos: {len(self.peers_known)}")
            
            # Intentar conectar a algunos nuevos peers
            await self.connect_to_bootstrap()
    
    async def request_peers(self, websocket):
        """Solicita peers a un peer conectado"""
        getaddr = create_message('getaddr', {})
        await websocket.send(json.dumps(getaddr))
        self.logger.info(f"[GETADDR] Solicitando peers")
    
    async def broadcast_message(self, msg: dict, exclude_ws=None):
        """Envía mensaje a todos los peers conectados"""
        count = 0
        
        for addr, ws in list(self.peers_connected.items()):
            if ws == exclude_ws:
                continue
            
            try:
                await ws.send(json.dumps(msg))
                count += 1
            except Exception as e:
                self.logger.error(f"[FAIL] Error enviando a {addr}: {e}")
        
        self.logger.info(f"[BROADCAST] Mensaje propagado a {count} peers")
    
    async def send_hello(self, message: str):
        """Envía mensaje HELLO de prueba"""
        hello = create_message('hello', {
            'data': message,
            'sender': self.id
        })
        
        self.logger.info(f"[SEND] Enviando HELLO: {message}")
        await self.broadcast_message(hello)
    
    # ============ LOOPS PERIÓDICOS ============
    
    async def gossip_loop(self):
        """
        Loop de gossip: solicita peers periódicamente
        Estilo Bitcoin: cada nodo redistribuye su info
        """
        await asyncio.sleep(10)  # Esperar a que haya conexiones
        
        while True:
            try:
                # Solicitar peers a todos los conectados
                for addr, ws in list(self.peers_connected.items()):
                    try:
                        await self.request_peers(ws)
                    except:
                        pass
                
                self.logger.info(f"[GOSSIP] Ciclo de gossip completado. Conocidos: {len(self.peers_known)}, Conectados: {len(self.peers_connected)}")
                
            except Exception as e:
                self.logger.error(f"[ERROR] Error en gossip loop: {e}")
            
            await asyncio.sleep(self.GOSSIP_INTERVAL)
    
    async def ping_loop(self):
        """Loop de ping/pong para keep-alive"""
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
                        self.logger.warning(f"[PING] Ping falló a {addr}: {e}")
                        # WebSocket ya maneja desconexión automáticamente
            
            except Exception as e:
                self.logger.error(f"[ERROR] Error en ping loop: {e}")
            
            await asyncio.sleep(self.PING_INTERVAL)
    
    async def cleanup_loop(self):
        """Limpia mensajes vistos y peers obsoletos"""
        while True:
            await asyncio.sleep(self.CLEANUP_INTERVAL)
            
            try:
                # Limpiar mensajes vistos
                old_count = len(self.messages_seen)
                self.messages_seen = set(list(self.messages_seen)[-500:])
                
                # Eliminar peers no vistos en 24 horas
                now = datetime.now().timestamp()
                to_remove = []
                
                for addr, peer in self.peers_known.items():
                    if not peer.is_connected and (now - peer.last_seen) > 86400:  # 24 horas
                        to_remove.append(addr)
                
                for addr in to_remove:
                    del self.peers_known[addr]
                    self.logger.info(f"[CLEANUP] Peer obsoleto eliminado: {addr}")
                
                self.logger.info(f"[CLEANUP] Mensajes: {old_count} -> {len(self.messages_seen)}, Peers eliminados: {len(to_remove)}")
                
            except Exception as e:
                self.logger.error(f"[ERROR] Error en cleanup: {e}")

    # ==================== TRANSACCIONES ====================
    
    async def handle_tx(self, msg: dict, sender_ws):
        """
        Maneja TX recibida de la red
        1. Deserializar
        2. Validar
        3. Evitar duplicados
        4. Agregar a mempool
        5. Propagar
        """
        try:
            tx_data = msg['payload']
            tx = Transaction.from_dict(tx_data)
            
            # Validar firma
            if not tx.is_valid():
                self.logger.warning(f"[TX] TX inválida recibida")
                return
            
            # Evitar duplicados
            tx_hash = tx.hash()
            if any(t.hash() == tx_hash for t in self.mempool):
                self.logger.info(f"[TX] TX duplicada ignorada: {tx_hash[:16]}...")
                return
            
            # Agregar a mempool
            self.mempool.append(tx)
            self.logger.info(f"[TX] TX agregada al mempool: {tx_hash[:16]}... "
                           f"({tx.from_address[:10]}...→{tx.to_address[:10]}..., {tx.amount})")
            
            # Propagar a otros peers (menos el que la envió)
            await self.broadcast_transaction(tx, exclude_ws=sender_ws)
            
        except Exception as e:
            self.logger.error(f"[TX] Error procesando TX: {e}")
    
    async def broadcast_transaction(self, tx: Transaction, exclude_ws=None):
        """Propaga TX a todos los peers (menos uno)"""
        msg = create_message('tx', tx.to_dict())
        
        for peer_addr, peer_ws in self.peers_connected.items():
            if peer_ws == exclude_ws:
                continue
            
            try:
                await peer_ws.send(json.dumps(msg))
            except Exception as e:
                self.logger.error(f"[TX] Error propagando a {peer_addr}: {e}")
    
    def create_transaction(self, to_address: str, amount: float) -> Transaction:
        """
        Crea TX desde este nodo
        """
        tx = Transaction(
            from_address=self.wallet.address,
            to_address=to_address,
            amount=amount
        )
        tx.sign(self.wallet)
        
        # Agregar a mempool local
        self.mempool.append(tx)
        self.logger.info(f"[TX] TX creada: {tx.hash()[:16]}... ({amount} → {to_address[:10]}...)")
        
        return tx
    
    def get_balance(self) -> float:
        """Calcula balance simulado"""
        balance = self.balance  # Inicial 100
        
        for tx in self.mempool:
            if tx.from_address == self.wallet.address:
                balance -= tx.amount
            if tx.to_address == self.wallet.address:
                balance += tx.amount
        
        return balance