"""
Launcher Auto — Demo con blockchain autónoma

Características:
- Seed node integrado (descubrimiento de peers + wallet addresses)
- Todos los nodos arrancan en modo AUTO (minan solos)
- TxOrchestrator genera TXs automáticas entre nodos
- Dashboard con controles de modo para minado y TXs
- El usuario puede cambiar modos desde el dashboard

Uso:
    python launcher_auto.py             # 5 nodos (default)
    python launcher_auto.py --nodes 3   # 3 nodos

Flujo automático:
    1. Seed node arranca y espera registros
    2. Nodos arrancan, se registran en seed y se conectan entre sí
    3. Todos los nodos empiezan a minar en competencia
    4. Cuando un nodo tiene balance, el orquestador genera TXs
    5. Las TXs se propagan y se confirman en bloques

Control desde el dashboard:
    - Minado: cambiar entre AUTO y MANUAL por nodo
    - TXs:    cambiar entre AUTO y MANUAL para toda la red
"""

import asyncio
import argparse
import threading
from core.blockchain import Blockchain
from core.tx_orchestrator import TxOrchestrator, ORCH_AUTO, ORCH_MANUAL
from network.p2p_node import P2PNode, MINING_AUTO
from network.seed_node import SeedNode
from dashboard.app import NodeDashboard
from config import (
    DIFFICULTY, SEED_PORT,
    TX_AUTO_BASE_INTERVAL, TX_AUTO_JITTER,
)

# Puerto del seed integrado en el launcher
LAUNCHER_SEED_PORT = 8888


def build_config(num_nodes: int) -> list:
    """Genera configuración de N nodos con topología en árbol."""
    configs = []
    for i in range(num_nodes):
        bootstrap = []
        if i == 1 or i == 2:
            bootstrap = [('localhost', 5000)]
        elif i > 2:
            bootstrap = [('localhost', 5000 + (i % 2))]

        configs.append({
            'p2p_port':       5000 + i,
            'dashboard_port': 8000 + i,
            'bootstrap':      bootstrap,
        })
    return configs


def start_seed_node():
    """
    Arranca el seed node en un thread separado.
    El seed usa Flask igual que los dashboards.
    """
    seed = SeedNode(host='0.0.0.0', port=LAUNCHER_SEED_PORT)
    t = threading.Thread(target=seed.run, daemon=True)
    t.start()
    return seed


async def start_node_with_dashboard(config: dict, orchestrator=None):
    """
    Instancia Blockchain + P2PNode + Dashboard en modo AUTO.

    Args:
        config:       Configuración del nodo.
        orchestrator: TxOrchestrator compartido (puede ser None al inicio
                      y asignarse después via dashboard.orchestrator = orch).
    """
    blockchain            = Blockchain()
    blockchain.DIFFICULTY = DIFFICULTY

    node = P2PNode(
        host='localhost',
        port=config['p2p_port'],
        bootstrap_peers=config['bootstrap'],
        blockchain=blockchain,
    )

    node.mining_mode = MINING_AUTO
    node.dashboard_port = config['dashboard_port']

    asyncio.create_task(node.start())
    await asyncio.sleep(0.8)

    # Pasar orquestador al dashboard — puede ser None aquí
    # y actualizarse después con dashboard.orchestrator = orch
    dashboard = NodeDashboard(
        node,
        config['dashboard_port'],
        dashboard_mode='auto',
        orchestrator=orchestrator,
    )
    t = threading.Thread(target=dashboard.run, daemon=True)
    t.start()

    return node, dashboard


async def main(num_nodes: int = 5):
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║              BLOCKCHAIN DEMO — Launcher Auto                         ║
╚══════════════════════════════════════════════════════════════════════╝

  Modo:       AUTO (minado y TXs automáticos)
  Nodos:      {num_nodes}
  Difficulty: {DIFFICULTY}
  Seed port:  {LAUNCHER_SEED_PORT}
  TXs auto:   cada {TX_AUTO_BASE_INTERVAL}s ± {TX_AUTO_JITTER}s

  Puertos P2P:       5000 – {5000 + num_nodes - 1}
  Puertos Dashboard: 8000 – {8000 + num_nodes - 1}
""")

    # ── 1. Arrancar seed node ──────────────────────────────
    print("  [1/3] Arrancando seed node...")
    start_seed_node()
    await asyncio.sleep(1)
    print(f"        Seed activo en http://localhost:{LAUNCHER_SEED_PORT}")

    # ── 2. Crear orquestador (antes de los nodos para pasarlo
    #       a cada dashboard desde el inicio) ─────────────────
    print("\n  [2/3] Creando orquestador de TXs...")
    orchestrator = TxOrchestrator(
        seed_host='localhost',
        seed_port=LAUNCHER_SEED_PORT,
        dashboard_port=8000,
    )

    # ── 3. Arrancar nodos ──────────────────────────────────
    print(f"\n  [3/3] Iniciando {num_nodes} nodos en modo AUTO...")
    configs    = build_config(num_nodes)
    nodes      = []
    dashboards = []

    for i, config in enumerate(configs, 1):
        print(f"        [{i}/{num_nodes}] Nodo {i} "
              f"(P2P:{config['p2p_port']} Dashboard:{config['dashboard_port']})...")
        node, dashboard = await start_node_with_dashboard(config, orchestrator=orchestrator)
        nodes.append(node)
        dashboards.append(dashboard)
        await asyncio.sleep(0.5)

    # Esperar que la red se conecte
    print("\n  Esperando conexiones y registros en seed...")
    await asyncio.sleep(4)

    # Arrancar orquestador con delay
    asyncio.create_task(_start_orchestrator_delayed(orchestrator))

    # ── Estado inicial ──────────────────────────────────────
    print(f"""
══════════════════════════════════════════════════════════════════════

  Todos los componentes activos. Abre en tu navegador:
""")
    for i, config in enumerate(configs, 1):
        print(f"    Nodo {i}: http://localhost:{config['dashboard_port']}")

    print(f"""
  El orquestador enviará TXs automáticas en ~30 segundos
  (cuando los nodos hayan minado sus primeros bloques).

  Desde cada dashboard puedes:
    - Cambiar el minado entre AUTO y MANUAL
    - Cambiar las TXs entre AUTO y MANUAL

  Presiona Ctrl+C para detener.
══════════════════════════════════════════════════════════════════════
""")

    try:
        await asyncio.Future()
    except (KeyboardInterrupt, asyncio.CancelledError):
        orchestrator.stop()
        print("\n\nDeteniendo...")

        print("\n  Resumen final:")
        for node in nodes:
            print(
                f"    {node.id}: "
                f"altura={node.blockchain.get_height()}, "
                f"minados={node.blocks_mined}, "
                f"balance={node.get_balance():.2f} coins"
            )
        print(
            f"\n  Orquestador: "
            f"TXs enviadas={orchestrator.txs_sent}, "
            f"fallidas={orchestrator.txs_failed}"
        )
        print("\n  Demo terminado.\n")


async def _start_orchestrator_delayed(orchestrator: TxOrchestrator):
    """
    Espera a que los nodos minen su primer bloque antes de
    empezar a generar TXs automáticas.
    Con difficulty 4 (~15s por bloque) esperamos 30 segundos.
    """
    print("  [ORCH] Esperando 30s para que los nodos tengan balance...")
    await asyncio.sleep(30)
    print("  [ORCH] Iniciando TXs automáticas...")
    orchestrator.set_mode(ORCH_AUTO)
    await orchestrator.start()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Launcher Auto — N nodos P2P con minado y TXs automáticas'
    )
    parser.add_argument(
        '--nodes', type=int, default=5,
        help='Número de nodos (default: 5)'
    )
    args = parser.parse_args()

    try:
        asyncio.run(main(num_nodes=args.nodes))
    except KeyboardInterrupt:
        print("\n  Demo terminado.\n")
