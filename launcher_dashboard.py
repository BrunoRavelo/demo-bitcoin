"""
Launcher que levanta 5 nodos P2P + 5 dashboards Flask
"""

import asyncio
import threading
from network.p2p_node import P2PNode
from dashboard.app import NodeDashboard

# Configuración de nodos
NODES_CONFIG = [
    {'p2p_port': 5000, 'dashboard_port': 8000, 'bootstrap': []},
    {'p2p_port': 5001, 'dashboard_port': 8001, 'bootstrap': [('localhost', 5000)]},
    {'p2p_port': 5002, 'dashboard_port': 8002, 'bootstrap': [('localhost', 5000)]},
    {'p2p_port': 5003, 'dashboard_port': 8003, 'bootstrap': [('localhost', 5001)]},
    {'p2p_port': 5004, 'dashboard_port': 8004, 'bootstrap': [('localhost', 5002)]},
]

async def start_node_with_dashboard(config):
    """
    Inicia un nodo P2P con su dashboard Flask
    
    Args:
        config: Diccionario con p2p_port, dashboard_port, bootstrap
    
    Returns:
        Tupla (node, dashboard)
    """
    # Crear nodo P2P
    node = P2PNode(
        host='localhost',
        port=config['p2p_port'],
        bootstrap_peers=config['bootstrap']
    )
    
    # Guardar loop para uso de Flask
    node.loop = asyncio.get_event_loop()
    
    # Iniciar nodo en background
    node.start_task = asyncio.create_task(node.start())
    
    # Esperar a que arranque
    await asyncio.sleep(0.5)
    
    # Crear dashboard
    dashboard = NodeDashboard(node, config['dashboard_port'])
    
    # Iniciar dashboard en thread separado
    dashboard_thread = threading.Thread(
        target=dashboard.run,
        daemon=True
    )
    dashboard_thread.start()
    
    return node, dashboard

async def main():
    print("\n" + "=" * 70)
    print("  BLOCKCHAIN DEMO - Dashboard Interactivo")
    print("=" * 70)
    print()
    
    # Levantar todos los nodos
    nodes = []
    dashboards = []
    
    for i, config in enumerate(NODES_CONFIG, 1):
        print(f"[{i}/5] Iniciando Nodo {i}...")
        print(f"        P2P:       localhost:{config['p2p_port']}")
        print(f"        Dashboard: http://localhost:{config['dashboard_port']}")
        
        node, dashboard = await start_node_with_dashboard(config)
        nodes.append(node)
        dashboards.append(dashboard)
        
        await asyncio.sleep(1)
    
    print()
    print("=" * 70)
    print("  Todos los nodos iniciados correctamente")
    print("=" * 70)
    print()
    print("Abre tu navegador en estas URLs:")
    for i, config in enumerate(NODES_CONFIG, 1):
        print(f"  Nodo {i}: http://localhost:{config['dashboard_port']}")
    print()
    print("Presiona Ctrl+C para detener todos los nodos")
    print("=" * 70)
    print()
    
    # Mantener corriendo
    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        print("\n\nCerrando nodos...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo terminado.")