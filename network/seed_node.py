"""
Seed Node — Servidor HTTP de descubrimiento de peers
Equivalente funcional a los DNS seeds de Bitcoin

Responsabilidades:
- Mantener lista de nodos activos en la red
- Permitir que nodos se registren con su IP y puerto
- Responder con lista de peers conocidos
- Limpiar nodos inactivos automáticamente

Cómo funciona en relación a Bitcoin:
- Bitcoin usa DNS real (consulta DNS del SO)
- Nosotros usamos HTTP GET/POST (más simple, mismo propósito)
- En ambos casos: la IP del seed es la única hardcodeada
- En ambos casos: el seed arranca vacío, los nodos se anuncian solos

No tiene blockchain, no mina, no valida transacciones.
Solo conoce IPs y puertos.
"""

import time
import threading
from flask import Flask, jsonify, request
from utils.logger import setup_logger
from config import SEED_PORT, CLEANUP_INTERVAL


class SeedNode:
    """
    Servidor HTTP que mantiene el registro de nodos activos.

    Cada nodo al arrancar hace:
        POST /register  → "aquí estoy, esta es mi IP y puerto"
        GET  /peers     → "dame la lista de todos los que conoces"

    El seed limpia automáticamente nodos que no han hecho
    ping en los últimos PEER_TIMEOUT segundos.
    """

    # Nodo se considera inactivo si no hace ping en 5 minutos
    PEER_TIMEOUT = 300

    def __init__(self, host: str = '0.0.0.0', port: int = SEED_PORT):
        """
        Inicializa el seed node.

        Args:
            host: IP donde escucha (0.0.0.0 = todas las interfaces)
            port: Puerto HTTP (default: SEED_PORT de config.py)
        """
        self.host = host
        self.port = port

        # Registro de peers: {f"{ip}:{port}": {info}}
        self.peers: dict = {}

        # Lock para acceso thread-safe desde Flask
        self.lock = threading.Lock()

        self.logger = setup_logger('seed_node')
        self.app = Flask(__name__)
        self._setup_routes()

    # ──────────────────────────────────────────────
    # Rutas HTTP
    # ──────────────────────────────────────────────

    def _setup_routes(self):
        """Registra los endpoints HTTP del seed."""

        @self.app.route('/health', methods=['GET'])
        def health():
            """
            Verificar que el seed está activo.
            Los nodos pueden usar esto para confirmar conectividad.
            """
            with self.lock:
                count = len(self.peers)

            return jsonify({
                'status': 'ok',
                'peers_count': count,
                'timestamp': time.time()
            })

        @self.app.route('/register', methods=['POST'])
        def register():
            """
            Un nodo anuncia su presencia al seed.

            Body JSON esperado:
                {
                    "host": "192.168.1.X",
                    "port": 5000,
                    "node_id": "node_5000"   (opcional)
                }

            El seed guarda la IP, el puerto y el timestamp.
            Si el nodo ya estaba registrado, actualiza su last_seen.
            """
            data = request.get_json(silent=True)

            if not data:
                return jsonify({'error': 'Body JSON requerido'}), 400

            host = data.get('host')
            port = data.get('port')
            node_id = data.get('node_id', f'node_{port}')

            if not host or not port:
                return jsonify({'error': 'host y port son requeridos'}), 400

            try:
                port = int(port)
            except (ValueError, TypeError):
                return jsonify({'error': 'port debe ser un número'}), 400

            addr = f"{host}:{port}"

            with self.lock:
                is_new = addr not in self.peers
                self.peers[addr] = {
                    'host':      host,
                    'port':      port,
                    'node_id':   node_id,
                    'last_seen': time.time(),
                    'first_seen': self.peers[addr]['first_seen'] if not is_new
                                  else time.time()
                }

            if is_new:
                self.logger.info(f"[REGISTER] Nuevo nodo: {addr} ({node_id})")
            else:
                self.logger.debug(f"[PING] Nodo actualizado: {addr}")

            return jsonify({'status': 'ok', 'addr': addr})

        @self.app.route('/peers', methods=['GET'])
        def get_peers():
            """
            Retorna la lista de nodos activos conocidos.

            Query params opcionales:
                exclude_host: IP a excluir (para que el nodo no se devuelva a sí mismo)
                exclude_port: Puerto a excluir

            Respuesta:
                {
                    "peers": [
                        {"host": "...", "port": ..., "node_id": "..."},
                        ...
                    ],
                    "count": N
                }
            """
            exclude_host = request.args.get('exclude_host')
            exclude_port = request.args.get('exclude_port')

            try:
                exclude_port = int(exclude_port) if exclude_port else None
            except ValueError:
                exclude_port = None

            with self.lock:
                now = time.time()
                active_peers = []

                for addr, info in self.peers.items():
                    # Filtrar inactivos
                    if now - info['last_seen'] > self.PEER_TIMEOUT:
                        continue

                    # Excluir el nodo que pregunta
                    if exclude_host and exclude_port:
                        if info['host'] == exclude_host and info['port'] == exclude_port:
                            continue

                    active_peers.append({
                        'host':    info['host'],
                        'port':    info['port'],
                        'node_id': info['node_id']
                    })

            self.logger.debug(f"[PEERS] Retornando {len(active_peers)} peers activos")

            return jsonify({
                'peers': active_peers,
                'count': len(active_peers)
            })

        @self.app.route('/peers/all', methods=['GET'])
        def get_all_peers():
            """
            Lista de TODOS los peers conocidos, incluyendo inactivos.
            Solo para diagnóstico y el dashboard global del instructor.
            """
            with self.lock:
                all_peers = [
                    {
                        'host':       info['host'],
                        'port':       info['port'],
                        'node_id':    info['node_id'],
                        'last_seen':  info['last_seen'],
                        'first_seen': info['first_seen'],
                        'active':     (time.time() - info['last_seen']) < self.PEER_TIMEOUT
                    }
                    for info in self.peers.values()
                ]

            return jsonify({
                'peers': all_peers,
                'count': len(all_peers)
            })

    # ──────────────────────────────────────────────
    # Limpieza automática
    # ──────────────────────────────────────────────

    def _cleanup_loop(self):
        """
        Loop en background que elimina nodos inactivos.
        Corre en un thread separado.
        Un nodo se considera inactivo si no hizo /register
        en los últimos PEER_TIMEOUT segundos.
        """
        while True:
            time.sleep(CLEANUP_INTERVAL)
            self._cleanup_inactive()

    def _cleanup_inactive(self):
        """Elimina nodos que no han hecho ping recientemente."""
        now = time.time()
        to_remove = []

        with self.lock:
            for addr, info in self.peers.items():
                if now - info['last_seen'] > self.PEER_TIMEOUT:
                    to_remove.append(addr)

            for addr in to_remove:
                del self.peers[addr]
                self.logger.info(f"[CLEANUP] Nodo inactivo eliminado: {addr}")

        if to_remove:
            self.logger.info(
                f"[CLEANUP] {len(to_remove)} nodos eliminados. "
                f"Activos: {len(self.peers)}"
            )

    # ──────────────────────────────────────────────
    # Arranque
    # ──────────────────────────────────────────────

    def run(self):
        """
        Inicia el seed node:
        1. Arranca el loop de limpieza en background
        2. Arranca el servidor Flask
        """
        self.logger.info(
            f"[SEED] Seed node iniciando en http://{self.host}:{self.port}"
        )
        self.logger.info(f"[SEED] Endpoints disponibles:")
        self.logger.info(f"         GET  /health")
        self.logger.info(f"         POST /register")
        self.logger.info(f"         GET  /peers")
        self.logger.info(f"         GET  /peers/all")

        # Cleanup en background
        cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True
        )
        cleanup_thread.start()

        # Servidor Flask
        self.app.run(
            host=self.host,
            port=self.port,
            debug=False,
            use_reloader=False
        )
