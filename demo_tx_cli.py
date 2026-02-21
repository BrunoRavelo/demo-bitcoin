"""
Demo CLI - Propagación de Transacciones P2P
Levanta 5 nodos y muestra TXs propagándose
"""

import asyncio
from network.p2p_node import P2PNode

# Configuración de nodos
NODES_CONFIG = [
    {'port': 5000, 'bootstrap': []},
    {'port': 5001, 'bootstrap': [('localhost', 5000)]},
    {'port': 5002, 'bootstrap': [('localhost', 5000)]},
    {'port': 5003, 'bootstrap': [('localhost', 5001)]},
    {'port': 5004, 'bootstrap': [('localhost', 5002)]},
]

async def start_node(config):
    """Inicia un nodo P2P"""
    node = P2PNode(
        host='localhost',
        port=config['port'],
        bootstrap_peers=config['bootstrap']
    )
    asyncio.create_task(node.start())
    await asyncio.sleep(0.5)  # Esperar a que arranque
    return node

async def main():
    print("\n" + "=" * 70)
    print("  DEMO: Integración P2P + Transacciones")
    print("=" * 70 + "\n")
    
    # 1. Levantar 5 nodos
    print("[1/4] Levantando 5 nodos...")
    nodes = []
    for i, config in enumerate(NODES_CONFIG, 1):
        print(f"      Nodo {i} (puerto {config['port']})...")
        node = await start_node(config)
        nodes.append(node)
    
    print(f"      ✓ 5 nodos iniciados\n")
    
    # 2. Esperar gossip
    print("[2/4] Esperando descubrimiento de peers (gossip protocol)...")
    await asyncio.sleep(8)
    
    # Verificar conectividad
    for i, node in enumerate(nodes, 1):
        print(f"      Nodo {i}: {len(node.peers_connected)} peers conectados")
    print()
    
    # 3. Mostrar wallets
    print("[3/4] Wallets de cada nodo:")
    print("-" * 70)
    for i, node in enumerate(nodes, 1):
        print(f"  Nodo {i}: {node.wallet.address}")
        print(f"           Balance inicial: {node.get_balance()}")
    print()
    
    # 4. Crear y propagar transacciones
    print("[4/4] Creando y propagando transacciones...")
    print("-" * 70)
    
    # TX 1: Nodo 1 → Nodo 2 (10 coins)
    print("\n► TX1: Nodo 1 envía 10 coins a Nodo 2")
    tx1 = nodes[0].create_transaction(nodes[1].wallet.address, 10)
    await nodes[0].broadcast_transaction(tx1)
    await asyncio.sleep(2)
    
    print(f"  Propagación:")
    for i, node in enumerate(nodes, 1):
        count = len(node.mempool)
        print(f"    Nodo {i}: {count} TX en mempool")
    
    # TX 2: Nodo 2 → Nodo 3 (5 coins)
    print("\n► TX2: Nodo 2 envía 5 coins a Nodo 3")
    tx2 = nodes[1].create_transaction(nodes[2].wallet.address, 5)
    await nodes[1].broadcast_transaction(tx2)
    await asyncio.sleep(2)
    
    print(f"  Propagación:")
    for i, node in enumerate(nodes, 1):
        count = len(node.mempool)
        print(f"    Nodo {i}: {count} TXs en mempool")
    
    # TX 3: Nodo 3 → Nodo 4 (2 coins)
    print("\n► TX3: Nodo 3 envía 2 coins a Nodo 4")
    tx3 = nodes[2].create_transaction(nodes[3].wallet.address, 2)
    await nodes[2].broadcast_transaction(tx3)
    await asyncio.sleep(2)
    
    print(f"  Propagación:")
    for i, node in enumerate(nodes, 1):
        count = len(node.mempool)
        print(f"    Nodo {i}: {count} TXs en mempool")
    
    # 5. Balances finales
    print("\n" + "=" * 70)
    print("  RESULTADO FINAL")
    print("=" * 70)
    print("\nBalances:")
    for i, node in enumerate(nodes, 1):
        balance = node.get_balance()
        print(f"  Nodo {i}: {balance:.2f} coins (cambio: {balance - 100:+.2f})")
    
    print(f"\nMempool (sincronizado en todos los nodos):")
    print(f"  {len(nodes[0].mempool)} transacciones confirmadas\n")
    
    for i, tx in enumerate(nodes[0].mempool, 1):
        print(f"  TX{i}: {tx.hash()[:16]}...")
        print(f"       {tx.from_address[:12]}... → {tx.to_address[:12]}...")
        print(f"       Monto: {tx.amount} coins\n")
    
    print("=" * 70)
    print("✓ Demo completado. Presiona Ctrl+C para salir")
    print("=" * 70 + "\n")
    
    # Mantener corriendo
    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        print("\nCerrando nodos...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo terminado.")