"""
Punto de entrada principal — un nodo por máquina
Uso en laboratorio: python main.py --host 192.168.1.X --port 5000

Sprint 3.3: instancia Blockchain antes que P2PNode
"""

import asyncio
import argparse
from core.blockchain import Blockchain
from network.p2p_node import P2PNode
from config import P2P_PORT, DASHBOARD_PORT, DIFFICULTY


async def main():
    parser = argparse.ArgumentParser(
        description='Nodo P2P Blockchain Demo'
    )
    parser.add_argument(
        '--port', type=int, default=P2P_PORT,
        help=f'Puerto P2P WebSocket (default: {P2P_PORT})'
    )
    parser.add_argument(
        '--host', type=str, default='localhost',
        help='IP donde escuchar (default: localhost)'
    )
    parser.add_argument(
        '--bootstrap', type=str, default='',
        help='Peers iniciales: host:port,host:port'
    )
    parser.add_argument(
        '--dashboard', type=int, default=DASHBOARD_PORT,
        help=f'Puerto dashboard Flask (default: {DASHBOARD_PORT})'
    )
    parser.add_argument(
        '--no-dashboard', action='store_true',
        help='Arrancar sin dashboard web'
    )
    args = parser.parse_args()

    # Parsear bootstrap peers
    bootstrap_peers = []
    if args.bootstrap:
        for peer in args.bootstrap.split(','):
            peer = peer.strip()
            if ':' in peer:
                h, p = peer.split(':')
                bootstrap_peers.append((h, int(p)))

    # Instanciar Blockchain (fuente de verdad)
    blockchain = Blockchain()

    # Instanciar nodo P2P con la blockchain
    node = P2PNode(
        host=args.host,
        port=args.port,
        bootstrap_peers=bootstrap_peers,
        blockchain=blockchain,
    )

    # Arrancar dashboard en thread separado (opcional)
    if not args.no_dashboard:
        import threading
        from dashboard.app import NodeDashboard
        dashboard = NodeDashboard(node, args.dashboard)
        dashboard_thread = threading.Thread(
            target=dashboard.run, daemon=True
        )
        dashboard_thread.start()
        dashboard_url = f"http://{args.host}:{args.dashboard}"
    else:
        dashboard_url = "(desactivado)"

    print(f"""
╔══════════════════════════════════════════════╗
║         NODO P2P — BLOCKCHAIN DEMO           ║
╚══════════════════════════════════════════════╝

  Node ID:    {node.id}
  P2P:        ws://{node.host}:{node.port}
  Dashboard:  {dashboard_url}
  Wallet:     {node.wallet.address}
  Difficulty: {DIFFICULTY}

  Bootstrap peers: {len(bootstrap_peers)}
  Presiona Ctrl+C para detener
""")

    try:
        await node.start()
    except KeyboardInterrupt:
        print(f"\nNodo {node.id} detenido.\n")


if __name__ == '__main__':
    asyncio.run(main())
