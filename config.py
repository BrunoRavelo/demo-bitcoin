"""
Configuración central del demo de blockchain
Modifica este archivo para ajustar el comportamiento de toda la red

Para el laboratorio: cambia SEED_HOST a la IP de la máquina del instructor
"""

import os

# ─────────────────────────────────────────────
# RED
# ─────────────────────────────────────────────

# IP y puerto del seed node (máquina del instructor)
# En desarrollo local usar 'localhost'
# En laboratorio usar la IP real: '192.168.1.X'
SEED_HOST = os.environ.get('SEED_HOST', 'localhost')
SEED_PORT = int(os.environ.get('SEED_PORT', 8888))

# Puerto base para nodos P2P
# Cada nodo usa P2P_PORT + offset si corren varios en la misma máquina
P2P_PORT = int(os.environ.get('P2P_PORT', 5000))

# Puerto base para dashboards Flask
DASHBOARD_PORT = int(os.environ.get('DASHBOARD_PORT', 8000))

# Puerto para el dashboard global (observador)
GLOBAL_DASHBOARD_PORT = int(os.environ.get('GLOBAL_DASHBOARD_PORT', 9000))

# Límites de conexiones (igual que Bitcoin)
MAX_OUTBOUND_CONNECTIONS = 8
MAX_INBOUND_CONNECTIONS = 125
MAX_PEERS_TO_SHARE = 10

# ─────────────────────────────────────────────
# BLOCKCHAIN
# ─────────────────────────────────────────────

# Número de ceros requeridos al inicio del hash
# 3 → ~500 intentos   (~0.1s)   — para demos rápidos
# 4 → ~65,000 intentos (~5-15s) — default actual
# 5 → ~1M intentos    (~60s)    — para demos lentos/dramáticos
DIFFICULTY = int(os.environ.get('DIFFICULTY', 4))

# Recompensa por minar un bloque (coins)
BLOCK_REWARD = 50

# Máximo de transacciones por bloque
MAX_TXS_PER_BLOCK = 10

# Máximo de transacciones en el mempool
MAX_MEMPOOL_SIZE = 1000

# ─────────────────────────────────────────────
# MINADO AUTOMÁTICO
# ─────────────────────────────────────────────

# Si True, cada nodo mina automáticamente al arrancar
MINING_AUTO_START = True

# ─────────────────────────────────────────────
# TRANSACCIONES AUTOMÁTICAS
# ─────────────────────────────────────────────

# Si True, cada nodo genera transacciones automáticas al arrancar
TX_AUTO_START = True

# Intervalo base entre transacciones automáticas (segundos)
TX_AUTO_BASE_INTERVAL = 15

# Jitter máximo para el intervalo (segundos)
# Intervalo real = BASE + random(0, JITTER)
# Evita que todos los nodos envíen TXs simultáneamente
TX_AUTO_JITTER = 10

# Monto máximo de una transacción automática (fracción del balance)
TX_AUTO_MAX_FRACTION = 0.2  # Máximo 20% del balance disponible

# ─────────────────────────────────────────────
# INTERVALOS DE RED
# ─────────────────────────────────────────────

# Cada cuántos segundos solicitar peers (gossip)
GOSSIP_INTERVAL = 60

# Cada cuántos segundos enviar ping (keep-alive)
PING_INTERVAL = 30

# Cada cuántos segundos limpiar peers y mensajes vistos
CLEANUP_INTERVAL = 300

# Tiempo máximo de espera para conectar a un peer (segundos)
CONNECT_TIMEOUT = 5.0

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

# Directorio donde se guardan los logs de cada nodo
LOG_DIR = 'logs'

# Nivel de logging: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
