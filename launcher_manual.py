"""
Launcher Manual — Demo con control total del usuario

Características:
- Todos los nodos arrancan en modo MANUAL
- Se mina un bloque inicial por nodo (para tener balance desde el inicio)
- Sin seed node (no necesario para demo manual local)
- Sin orquestador (todas las TXs son manuales)
- El usuario controla todo desde los dashboards

Uso:
    python launcher_manual.py             # 5 nodos (default)
    python launcher_manual.py --nodes 3   # 3 nodos

Flujo del demo manual:
    1. Arrancar este script
    2. Abrir dashboards en el navegador
    3. Cambiar nodo a AUTO para minar, o presionar "Minar ahora"
    4. Copiar address de un nodo y enviársela a otro
    5. Crear TX manual desde el formulario
    6. Minar un bloque para confirmar la TX
"""

import asyncio
import argparse
import threading
from core.blockchain import Blockchain
from network.p2p_node import P2PNode, MINING_MANUAL
from dashboard.app import NodeDashboard
from config import DIFFICULTY


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


async def start_node_with_dashboard(config: dict):
    """
    Instancia Blockchain + P2PNode + Dashboard.
    Sin bloque inicial — todos arrancan con solo el genesis (balance 0).
    El usuario mina manualmente desde el dashboard para obtener balance.
    """
    blockchain            = Blockchain()
    blockchain.DIFFICULTY = DIFFICULTY

    node = P2PNode(
        host='localhost',
        port=config['p2p_port'],
        bootstrap_peers=config['bootstrap'],
        blockchain=blockchain,
    )

    # Forzar modo MANUAL — el usuario controla el minado
    node.mining_mode = MINING_MANUAL

    # Arrancar nodo
    asyncio.create_task(node.start())
    await asyncio.sleep(0.8)

    # Dashboard en thread separado con modo manual
    dashboard = NodeDashboard(node, config['dashboard_port'], dashboard_mode='manual')
    t = threading.Thread(target=dashboard.run, daemon=True)
    t.start()

    return node, dashboard


async def main(num_nodes: int = 5):
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║           BLOCKCHAIN DEMO — Launcher Manual                          ║
╚══════════════════════════════════════════════════════════════════════╝

  Modo:       MANUAL (minado y TXs controlados por el usuario)
  Nodos:      {num_nodes}
  Difficulty: {DIFFICULTY}
  Balance inicial: 0 coins (mina tu primer bloque para obtener {50} coins)

  Puertos P2P:       5000 – {5000 + num_nodes - 1}
  Puertos Dashboard: 8000 – {8000 + num_nodes - 1}
""")

    configs = build_config(num_nodes)
    nodes   = []

    print("  Iniciando nodos...")
    for i, config in enumerate(configs, 1):
        print(f"  [{i}/{num_nodes}] Nodo {i} (P2P:{config['p2p_port']} Dashboard:{config['dashboard_port']})...")
        node, _ = await start_node_with_dashboard(config)
        nodes.append(node)
        await asyncio.sleep(0.3)

    # Esperar que la red se conecte
    print("\n  Esperando conexiones entre nodos...")
    await asyncio.sleep(3)

    print(f"""
══════════════════════════════════════════════════════════════════════

  Todos los nodos listos. Abre en tu navegador:
""")
    for i, config in enumerate(configs, 1):
        print(f"    Nodo {i}: http://localhost:{config['dashboard_port']}")

    print(f"""
  Instrucciones:
    1. Abre el dashboard de un nodo y presiona "Minar ahora"
    2. Al completarse obtienes 50 coins de recompensa
    3. Copia la address de otro nodo desde su dashboard
    4. Pégala en "Destinatario" y envía una TX
    5. Mina otro bloque para confirmar la TX

  Presiona Ctrl+C para detener.
══════════════════════════════════════════════════════════════════════
""")

    try:
        await asyncio.Future()
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n\nDeteniendo nodos...")
        print("\n  Resumen final:")
        for node in nodes:
            print(
                f"    {node.id}: "
                f"altura={node.blockchain.get_height()}, "
                f"minados={node.blocks_mined}, "
                f"balance={node.get_balance():.2f} coins"
            )
        print("\n  Demo terminado.\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Launcher Manual — N nodos P2P en modo manual'
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
