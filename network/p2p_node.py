"""
Nodo P2P básico - FASE 1
Conecta peers, hace handshake, y propaga mensajes simples
"""

import asyncio
import websockets
import json
import uuid
from typing import Dict, Set
from datetime import datetime

from utils.logger import setup_logger
from network.protocol import create_message, validate_message


class P2PNode:
    """
    Nodo P2P que actúa como servidor y cliente simultáneamente
    """
    
    def __init__(self, host: str, port: int, bootstrap_peers: list):
        """
        Inicializa un nodo P2P
        
        Args:
            host: IP o hostname (ej. 'localhost')
            port: Puerto para escuchar (ej. 5000)
            bootstrap_peers: Lista de tuplas [(host, port)] para conectar inicialmente
        """
        self.id = str(uuid.uuid4())[:8]  # ID corto del nodo
        self.host = host
        self.port = port
        self.bootstrap_peers = bootstrap_peers
        
        # Gestión de peers conectados
        # Formato: {peer_id: websocket}
        self.peers: Dict[str, websockets.WebSocketServerProtocol] = {}
        
        # Control de mensajes ya vistos (evitar loops infinitos)
        self.messages_seen: Set[str] = set()
        
        # Límites de red
        self.MAX_PEERS = 8
        
        # Logger
        self.logger = setup_logger(self.id)
        
    async def start(self):
        """Inicia el nodo: servidor + conexión a bootstrap peers"""
        self.logger.info(f"Iniciando nodo {self.id} en {self.host}:{self.port}")
        
        # Iniciar servidor WebSocket
        server = await websockets.serve(
            self.handle_incoming_connection,
            self.host,
            self.port
        )
        
        self.logger.info(f"Servidor escuchando en ws://{self.host}:{self.port}")
        
        # Conectar a bootstrap peers
        asyncio.create_task(self.connect_to_bootstrap())
        
        # Mantener servidor corriendo
        await asyncio.Future()  # Espera indefinidamente
        
    async def handle_incoming_connection(self, websocket, path):
        """
        Maneja una conexión entrante de otro peer
        
        Args:
            websocket: Conexión WebSocket
            path: Ruta del WebSocket (no usado)
        """
        peer_id = None
        
        try:
            self.logger.info(f"Conexión entrante desde {websocket.remote_address}")
            
            # Escuchar mensajes de este peer
            async for raw_message in websocket:
                msg = json.loads(raw_message)
                
                # Validar mensaje
                if not validate_message(msg):
                    self.logger.warning(f"Mensaje inválido recibido")
                    continue
                
                # Procesar según tipo
                if msg['type'] == 'version':
                    # Handshake inicial
                    peer_id = msg['payload']['node_id']
                    self.peers[peer_id] = websocket
                    self.logger.info(f"Peer conectado: {peer_id}")
                    
                    # Responder con VERACK
                    verack = create_message('verack', {
                        'node_id': self.id
                    })
                    await websocket.send(json.dumps(verack))
                    
                else:
                    # Otros mensajes
                    await self.handle_message(msg, websocket)
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning(f"Conexión cerrada: {peer_id}")
        except Exception as e:
            self.logger.error(f"Error en conexión: {e}")
        finally:
            # Limpiar peer desconectado
            if peer_id and peer_id in self.peers:
                del self.peers[peer_id]
                self.logger.info(f"Peer removido: {peer_id}")
    
    async def connect_to_bootstrap(self):
        """Conecta a los peers bootstrap iniciales"""
        # Esperar un poco para que el servidor esté listo
        await asyncio.sleep(2)
        
        self.logger.info(f"Conectando a bootstrap peers...")
        
        for host, port in self.bootstrap_peers:
            # No conectar a uno mismo
            if port == self.port and host == self.host:
                continue
            
            try:
                uri = f"ws://{host}:{port}"
                self.logger.info(f"Intentando conectar a {uri}")
                
                websocket = await websockets.connect(uri)
                
                # Enviar VERSION (handshake)
                version_msg = create_message('version', {
                    'node_id': self.id,
                    'version': '1.0'
                })
                await websocket.send(json.dumps(version_msg))
                
                # Esperar VERACK
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                verack = json.loads(response)
                
                if verack['type'] == 'verack':
                    peer_id = f"{host}:{port}"
                    self.peers[peer_id] = websocket
                    self.logger.info(f"Conectado a bootstrap: {peer_id}")
                    
                    # Iniciar listener para este peer
                    asyncio.create_task(self.listen_to_peer(websocket, peer_id))
                
            except asyncio.TimeoutError:
                self.logger.error(f"Timeout conectando a {host}:{port}")
            except Exception as e:
                self.logger.error(f"No se pudo conectar a {host}:{port} - {e}")
    
    async def listen_to_peer(self, websocket, peer_id: str):
        """
        Escucha mensajes continuos de un peer específico
        
        Args:
            websocket: Conexión WebSocket
            peer_id: Identificador del peer
        """
        try:
            async for raw_message in websocket:
                msg = json.loads(raw_message)
                
                if validate_message(msg):
                    await self.handle_message(msg, websocket)
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning(f"Peer desconectado: {peer_id}")
        except Exception as e:
            self.logger.error(f"Error escuchando a {peer_id}: {e}")
        finally:
            if peer_id in self.peers:
                del self.peers[peer_id]
    
    async def handle_message(self, msg: dict, sender_ws):
        """
        Procesa un mensaje recibido
        
        Args:
            msg: Mensaje validado
            sender_ws: WebSocket del remitente
        """
        msg_id = msg['id']
        msg_type = msg['type']
        
        # Evitar procesar mensajes duplicados (loops)
        if msg_id in self.messages_seen:
            return
        
        self.messages_seen.add(msg_id)
        
        self.logger.info(f"Mensaje recibido: {msg_type} (ID: {msg_id[:8]}...)")
        
        # Procesar según tipo
        if msg_type == 'ping':
            # Responder PONG
            pong = create_message('pong', {
                'nonce': msg['payload']['nonce']
            })
            await sender_ws.send(json.dumps(pong))
            self.logger.info(f"PONG enviado")
            
        elif msg_type == 'pong':
            self.logger.info(f"PONG recibido")
            
        elif msg_type == 'hello':
            # Mensaje de prueba - solo loggear y propagar
            data = msg['payload'].get('data', '')
            self.logger.info(f"HELLO recibido: {data}")
            
            # Propagar a otros peers (broadcast)
            await self.broadcast_message(msg, exclude_ws=sender_ws)
        
        else:
            self.logger.warning(f"Tipo de mensaje desconocido: {msg_type}")
    
    async def broadcast_message(self, msg: dict, exclude_ws=None):
        """
        Envía un mensaje a todos los peers conectados
        
        Args:
            msg: Mensaje a enviar
            exclude_ws: WebSocket a excluir (ej. el remitente original)
        """
        count = 0
        
        for peer_id, ws in list(self.peers.items()):
            # No reenviar al remitente
            if ws == exclude_ws:
                continue
            
            try:
                await ws.send(json.dumps(msg))
                count += 1
            except Exception as e:
                self.logger.error(f"Error enviando a {peer_id}: {e}")
        
        self.logger.info(f"Mensaje propagado a {count} peers")
    
    async def send_hello(self, message: str):
        """
        Envía un mensaje HELLO de prueba a todos los peers
        
        Args:
            message: Contenido del mensaje
        """
        hello = create_message('hello', {
            'data': message,
            'sender': self.id
        })
        
        self.logger.info(f"Enviando HELLO: {message}")
        await self.broadcast_message(hello)