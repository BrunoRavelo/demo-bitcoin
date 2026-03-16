"""
Seed Client — Cliente HTTP para comunicarse con el Seed Node
Usado por cada P2PNode al arrancar para registrarse y obtener peers

Separado de P2PNode para mantener responsabilidades claras:
- SeedClient  → habla con el seed node (HTTP)
- P2PNode     → habla con otros nodos (WebSocket)
"""

import requests
from typing import List, Optional
from utils.logger import setup_logger
from config import SEED_HOST, SEED_PORT


class SeedClient:
    """
    Cliente HTTP para el seed node.

    Uso típico en P2PNode:
        client = SeedClient(node_id='node_5000', host='192.168.1.5', port=5000)
        client.register()                    # anunciarse
        peers = client.get_peers()           # obtener lista inicial
    """

    def __init__(
        self,
        node_id:   str,
        host:      str,
        port:      int,
        seed_host: str = SEED_HOST,
        seed_port: int = SEED_PORT
    ):
        """
        Args:
            node_id:   Identificador del nodo (ej: 'node_5000')
            host:      IP propia del nodo (la que otros usarán para conectarse)
            port:      Puerto P2P propio
            seed_host: IP del seed node (de config.py)
            seed_port: Puerto del seed node (de config.py)
        """
        self.node_id   = node_id
        self.host      = host
        self.port      = port
        self.seed_url  = f"http://{seed_host}:{seed_port}"
        self.logger    = setup_logger(node_id)

    # ──────────────────────────────────────────────
    # Métodos públicos
    # ──────────────────────────────────────────────

    def register(self) -> bool:
        """
        Registra este nodo en el seed.
        Llamar al arrancar y periódicamente como keep-alive.

        Returns:
            True si el registro fue exitoso.
        """
        try:
            response = requests.post(
                f"{self.seed_url}/register",
                json={
                    'host':    self.host,
                    'port':    self.port,
                    'node_id': self.node_id
                },
                timeout=5
            )
            if response.status_code == 200:
                self.logger.info(
                    f"[SEED] Registrado en seed {self.seed_url}"
                )
                return True
            else:
                self.logger.warning(
                    f"[SEED] Registro falló: {response.status_code}"
                )
                return False

        except requests.exceptions.ConnectionError:
            self.logger.warning(
                f"[SEED] No se pudo conectar al seed {self.seed_url} "
                f"— continuando sin seed"
            )
            return False
        except requests.exceptions.Timeout:
            self.logger.warning(f"[SEED] Timeout al registrar en seed")
            return False
        except Exception as e:
            self.logger.error(f"[SEED] Error inesperado al registrar: {e}")
            return False

    def get_peers(self) -> List[dict]:
        """
        Obtiene la lista de nodos activos del seed.
        Excluye automáticamente este mismo nodo.

        Returns:
            Lista de dicts con 'host', 'port', 'node_id'.
            Lista vacía si el seed no está disponible.
        """
        try:
            response = requests.get(
                f"{self.seed_url}/peers",
                params={
                    'exclude_host': self.host,
                    'exclude_port': self.port
                },
                timeout=5
            )
            if response.status_code == 200:
                data  = response.json()
                peers = data.get('peers', [])
                self.logger.info(
                    f"[SEED] {len(peers)} peers obtenidos del seed"
                )
                return peers
            else:
                self.logger.warning(
                    f"[SEED] get_peers falló: {response.status_code}"
                )
                return []

        except requests.exceptions.ConnectionError:
            self.logger.warning(
                f"[SEED] Seed no disponible — iniciando sin peers del seed"
            )
            return []
        except Exception as e:
            self.logger.error(f"[SEED] Error obteniendo peers: {e}")
            return []

    def is_seed_available(self) -> bool:
        """
        Verifica si el seed está activo.
        Útil para diagnóstico y el dashboard.

        Returns:
            True si el seed responde en /health.
        """
        try:
            response = requests.get(
                f"{self.seed_url}/health",
                timeout=3
            )
            return response.status_code == 200
        except Exception:
            return False
