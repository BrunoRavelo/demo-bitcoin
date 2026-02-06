"""
Launcher principal para nodos P2P
Ejecutar desde terminal con argumentos
"""

import asyncio
import argparse
from network.p2p_node import P2PNode


async def main():
    """Función principal asíncrona"""
    
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Nodo P2P Blockchain - Fase 1')
    
    parser.add_argument(
        '--port',
        type=int,
        required=True,
        help='Puerto para escuchar (ej. 5000)'
    )
    
    parser.add_argument(
        '--bootstrap',
        type=str,
        default='',
        help='Peers bootstrap separados por coma (ej. localhost:5000,localhost:5001)'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='localhost',
        help='Host para escuchar (default: localhost)'
    )
    
    args = parser.parse_args()
    
    # Parsear bootstrap peers
    bootstrap_peers = []
    if args.bootstrap:
        for peer in args.bootstrap.split(','):
            peer = peer.strip()
            if ':' in peer:
                host, port = peer.split(':')
                bootstrap_peers.append((host, int(port)))
    
    # Crear nodo
    node = P2PNode(
        host=args.host,
        port=args.port,
        bootstrap_peers=bootstrap_peers
    )
    
    print(f"""
╔════════════════════════════════════════════╗
║     NODO P2P - BLOCKCHAIN DEMO FASE 1      ║
╚════════════════════════════════════════════╝

  Node ID: {node.id}
  Escuchando: ws://{node.host}:{node.port}
  Bootstrap peers: {len(bootstrap_peers)}
  
  Presiona Ctrl+C para detener
  
""")
    
    try:
        # Iniciar nodo
        await node.start()
    except KeyboardInterrupt:
        print("\n\nDeteniendo nodo...")
        print(f"Nodo {node.id} detenido correctamente\n")


if __name__ == '__main__':
    # Ejecutar el loop asíncrono
    asyncio.run(main())