"""
Configuración central del demo blockchain.

Todos los parámetros del sistema se definen aquí.
Cambiar este archivo afecta a todos los componentes.
"""

import os

# ──────────────────────────────────────────────────────────
# Red
# ──────────────────────────────────────────────────────────

SEED_HOST = os.environ.get('SEED_HOST', 'localhost')
SEED_PORT = int(os.environ.get('SEED_PORT', 8888))

P2P_PORT       = int(os.environ.get('P2P_PORT', 5000))
DASHBOARD_PORT = int(os.environ.get('DASHBOARD_PORT', 8000))

MAX_OUTBOUND_CONNECTIONS = 8
MAX_INBOUND_CONNECTIONS  = 8
MAX_PEERS_TO_SHARE       = 10

CONNECT_TIMEOUT  = 5    # segundos
GOSSIP_INTERVAL  = 30   # segundos entre ciclos de gossip
PING_INTERVAL    = 30   # segundos entre pings
CLEANUP_INTERVAL = 60   # segundos entre limpiezas

# ──────────────────────────────────────────────────────────
# Difficulty ajustable — target numérico (estilo Bitcoin)
# ──────────────────────────────────────────────────────────

# Target máximo posible (cualquier hash es válido)
MAX_TARGET = 2**256 - 1

# Target inicial calibrado para ~180s por bloque a 50,000 h/s:
#   50,000 h/s × 30s = 1,500,000 hashes esperados
#   INITIAL_TARGET = MAX_TARGET // 1_500_000
INITIAL_TARGET = MAX_TARGET // 1_500_000

# Tiempo objetivo por bloque en segundos
TARGET_BLOCK_TIME = 180  # 3 minutos

# Ajustar difficulty cada N bloques (como Bitcoin usa 2016)
DIFFICULTY_ADJUSTMENT_INTERVAL = 5

# Factor máximo de ajuste por ciclo (4x = igual que Bitcoin)
MAX_ADJUSTMENT_FACTOR = 4

# ──────────────────────────────────────────────────────────
# Blockchain
# ──────────────────────────────────────────────────────────

BLOCK_REWARD       = 50
MAX_MEMPOOL_SIZE   = 100
MAX_TXS_PER_BLOCK  = 10

# ──────────────────────────────────────────────────────────
# Minado
# ──────────────────────────────────────────────────────────

# True  → nodos arrancan minando automáticamente
# False → nodos arrancan en modo PAUSED (tests, demo manual)
MINING_AUTO_START = True

# ──────────────────────────────────────────────────────────
# Orquestador de TXs automáticas
# ──────────────────────────────────────────────────────────

TX_AUTO_START         = True   # True → ORCH_AUTO al arrancar
TX_AUTO_BASE_INTERVAL = 15     # segundos entre TXs automáticas
TX_AUTO_JITTER        = 10     # variación aleatoria (evita sincronización)
TX_AUTO_MAX_FRACTION  = 0.2    # máximo 20% del balance por TX automática
