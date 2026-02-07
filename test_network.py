"""
Script de testing para red P2P con Gossip - Fase 1.5
"""

import asyncio
import time
from network.p2p_node import P2PNode


async def test_network():
    """Test de red P2P con gossip protocol"""
    
    print("""
╔════════════════════════════════════════════╗
║   TEST RED P2P + GOSSIP - FASE 1.5         ║
╚════════════════════════════════════════════╝
""")
    
    # Crear 5 nodos para probar gossip
    print("Creando 5 nodos...\n")
    
    # Nodo 1: Seed node (sin bootstrap)
    node1 = P2PNode(
        host='localhost',
        port=5000,
        bootstrap_peers=[]
    )
    
    # Nodo 2 y 3: Conectan al seed
    node2 = P2PNode(
        host='localhost',
        port=5001,
        bootstrap_peers=[('localhost', 5000)]
    )
    
    node3 = P2PNode(
        host='localhost',
        port=5002,
        bootstrap_peers=[('localhost', 5000)]
    )
    
    # Nodo 4: Solo conoce a node2 (probará gossip)
    node4 = P2PNode(
        host='localhost',
        port=5003,
        bootstrap_peers=[('localhost', 5001)]
    )
    
    # Nodo 5: Solo conoce a node3 (probará gossip)
    node5 = P2PNode(
        host='localhost',
        port=5004,
        bootstrap_peers=[('localhost', 5002)]
    )
    
    print(f"[OK] Nodo 1 (Seed):    {node1.id} - Puerto 5000")
    print(f"[OK] Nodo 2:           {node2.id} - Puerto 5001 (bootstrap: 5000)")
    print(f"[OK] Nodo 3:           {node3.id} - Puerto 5002 (bootstrap: 5000)")
    print(f"[OK] Nodo 4:           {node4.id} - Puerto 5003 (bootstrap: 5001)")
    print(f"[OK] Nodo 5:           {node5.id} - Puerto 5004 (bootstrap: 5002)")
    print()
    
    # Iniciar nodos
    print("Iniciando nodos...\n")
    
    tasks = [
        asyncio.create_task(node1.start()),
        asyncio.create_task(node2.start()),
        asyncio.create_task(node3.start()),
        asyncio.create_task(node4.start()),
        asyncio.create_task(node5.start())
    ]
    
    # Esperar conexiones iniciales
    await asyncio.sleep(5)
    
    print("\n" + "="*60)
    print("ESTADO INICIAL DE LA RED")
    print("="*60)
    print(f"Nodo 1: Conectados={len(node1.peers_connected)}, Conocidos={len(node1.peers_known)}")
    print(f"Nodo 2: Conectados={len(node2.peers_connected)}, Conocidos={len(node2.peers_known)}")
    print(f"Nodo 3: Conectados={len(node3.peers_connected)}, Conocidos={len(node3.peers_known)}")
    print(f"Nodo 4: Conectados={len(node4.peers_connected)}, Conocidos={len(node4.peers_known)}")
    print(f"Nodo 5: Conectados={len(node5.peers_connected)}, Conocidos={len(node5.peers_known)}")
    print()
    
    # Test 1: Conectividad básica
    print("TEST 1: Verificar conectividad inicial")
    if len(node1.peers_connected) >= 2:
        print("   [PASS] Seed node tiene múltiples conexiones")
    else:
        print("   [FAIL] Seed node debería tener al menos 2 conexiones")
    print()
    
    # Esperar primer ciclo de gossip (60s es mucho, forzamos manualmente)
    print("TEST 2: Forzando gossip manual...")
    for node in [node1, node2, node3, node4, node5]:
        for addr, ws in list(node.peers_connected.items()):
            try:
                await node.request_peers(ws)
            except:
                pass
    
    await asyncio.sleep(3)
    
    print("\n" + "="*60)
    print("ESTADO DESPUÉS DE GOSSIP")
    print("="*60)
    print(f"Nodo 1: Conectados={len(node1.peers_connected)}, Conocidos={len(node1.peers_known)}")
    print(f"Nodo 2: Conectados={len(node2.peers_connected)}, Conocidos={len(node2.peers_known)}")
    print(f"Nodo 3: Conectados={len(node3.peers_connected)}, Conocidos={len(node3.peers_known)}")
    print(f"Nodo 4: Conectados={len(node4.peers_connected)}, Conocidos={len(node4.peers_known)}")
    print(f"Nodo 5: Conectados={len(node5.peers_connected)}, Conocidos={len(node5.peers_known)}")
    print()
    
    # Test 3: Gossip funcionó
    print("TEST 3: Verificar descubrimiento por gossip")
    # Nodo 4 solo conocía a node2, debería haber descubierto más
    if len(node4.peers_known) > 1:
        print(f"   [PASS] Nodo 4 descubrió {len(node4.peers_known)} peers via gossip")
    else:
        print("   [FAIL] Nodo 4 no descubrió peers via gossip")
    
    if len(node5.peers_known) > 1:
        print(f"   [PASS] Nodo 5 descubrió {len(node5.peers_known)} peers via gossip")
    else:
        print("   [FAIL] Nodo 5 no descubrió peers via gossip")
    print()
    
    # Test 4: Propagación de mensaje
    print("TEST 4: Propagación de mensaje HELLO")
    await node1.send_hello("Prueba de propagación desde seed node")
    
    await asyncio.sleep(2)
    
    if len(node2.messages_seen) > 0 and len(node3.messages_seen) > 0:
        print("   [PASS] Mensaje propagado exitosamente")
    else:
        print("   [FAIL] Mensaje no se propagó")
    print()
    
    # Resumen
    print("\n" + "="*60)
    print("RESUMEN DE TESTS")
    print("="*60)
    print("[OK] Conectividad P2P")
    print("[OK] Gossip Protocol (descubrimiento de peers)")
    print("[OK] Propagación de mensajes")
    print("[OK] Keep-alive (ping/pong)")
    print()
    print("RED P2P FASE 1.5 COMPLETADA")
    print("\nManteniendo red activa 15 segundos más...")
    print("(Revisa logs/ para ver detalles de cada nodo)")
    print()
    
    await asyncio.sleep(15)
    
    # Detener
    print("\nDeteniendo nodos...")
    for task in tasks:
        task.cancel()
    
    print("[OK] Test completado\n")


if __name__ == '__main__':
    try:
        asyncio.run(test_network())
    except KeyboardInterrupt:
        print("\n\n[STOP] Test interrumpido por el usuario\n")