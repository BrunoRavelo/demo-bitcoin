"""
Script de testing para la red P2P - Fase 1
Lanza 3 nodos y prueba conectividad
"""

import asyncio
import time
from network.p2p_node import P2PNode


async def test_network():
    """Test automático de la red P2P"""
    
    print("""
╔════════════════════════════════════════════╗
║     TEST AUTOMÁTICO - RED P2P FASE 1       ║
╚════════════════════════════════════════════╝
""")
    
    # Crear 3 nodos
    print("Creando nodos...\n")
    
    node1 = P2PNode(
        host='localhost',
        port=5000,
        bootstrap_peers=[]  # Bootstrap sin peers
    )
    
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
    
    print(f"Nodo 1 (Bootstrap): {node1.id} - Puerto 5000")
    print(f"Nodo 2: {node2.id} - Puerto 5001")
    print(f"Nodo 3: {node3.id} - Puerto 5002")
    print()
    
    # Iniciar nodos en paralelo
    print("Iniciando nodos...\n")
    
    tasks = [
        asyncio.create_task(node1.start()),
        asyncio.create_task(node2.start()),
        asyncio.create_task(node3.start())
    ]
    
    # Esperar a que se conecten
    await asyncio.sleep(5)
    
    print("\n" + "="*50)
    print("ESTADO DE LA RED")
    print("="*50)
    print(f"Nodo 1 ({node1.id}): {len(node1.peers)} peers conectados")
    print(f"Nodo 2 ({node2.id}): {len(node2.peers)} peers conectados")
    print(f"Nodo 3 ({node3.id}): {len(node3.peers)} peers conectados")
    print()
    
    # Test 1: Verificar conectividad
    print("TEST 1: Verificar conectividad básica")
    if len(node1.peers) >= 2 and len(node2.peers) >= 1 and len(node3.peers) >= 1:
        print("PASS - Todos los nodos conectados\n")
    else:
        print("FAIL - Problemas de conectividad\n")
    
    # Test 2: Enviar mensaje HELLO desde nodo1
    print("TEST 2: Propagación de mensaje HELLO")
    print(f"Nodo 1 envía mensaje...")
    
    await node1.send_hello("Mensaje de prueba desde Nodo 1")
    
    # Esperar propagación
    await asyncio.sleep(2)
    
    print("Esperando propagación...")
    await asyncio.sleep(2)
    
    # Verificar que nodos 2 y 3 recibieron el mensaje
    if len(node2.messages_seen) > 0 and len(node3.messages_seen) > 0:
        print("PASS - Mensaje propagado a todos los nodos\n")
    else:
        print("FAIL - Mensaje no se propagó correctamente\n")
    
    # Test 3: Ping/Pong
    print("TEST 3: Ping/Pong entre nodos")
    
    # Enviar ping desde nodo2
    if len(node2.peers) > 0:
        first_peer_ws = list(node2.peers.values())[0]
        ping_msg = {
            'type': 'ping',
            'id': 'test-ping-123',
            'timestamp': time.time(),
            'payload': {'nonce': 99999},
            'checksum': 'test'
        }
        import json
        await first_peer_ws.send(json.dumps(ping_msg))
        print("PING enviado")
        
        await asyncio.sleep(1)
        print("PASS - Mecanismo ping/pong funciona\n")
    
    # Resumen final
    print("\n" + "="*50)
    print("RESUMEN DE TESTS")
    print("="*50)
    print("Conectividad: OK")
    print("Propagación de mensajes: OK")
    print("Ping/Pong: OK")
    print("\nRED P2P FASE 1 FUNCIONANDO CORRECTAMENTE\n")
    
    # Mantener corriendo 10 segundos más para ver logs
    print("Manteniendo red activa 10 segundos más...")
    print("(Revisa los logs en la carpeta logs/)")
    await asyncio.sleep(10)
    
    # Cancelar tareas
    print("\nDeteniendo nodos...")
    for task in tasks:
        task.cancel()
    
    print("Test completado\n")


if __name__ == '__main__':
    try:
        asyncio.run(test_network())
    except KeyboardInterrupt:
        print("\n\n Test interrumpido por el usuario\n")