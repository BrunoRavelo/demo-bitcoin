"""
Demo CLI — Stack completo funcional
Levanta 5 nodos con blockchain real, minado automático y TXs automáticas

Uso:
    python demo_tx_cli.py

Muestra en tiempo real:
    - Conexión de nodos y gossip
    - Bloques minados y propagados
    - Transacciones automáticas
    - Balances actualizados
    - Altura de cadena por nodo

Presiona Ctrl+C para ver el resumen final.
"""

import asyncio
import random
from core.blockchain import Blockchain
from core.transaction import Transaction
from network.p2p_node import P2PNode, MINING_AUTO, MINING_PAUSED
from network.seed_node import SeedNode
import threading

# ──────────────────────────────────────────────────────────
# Configuración del demo
# ──────────────────────────────────────────────────────────

NUM_NODES  = 5
BASE_PORT  = 6000
DIFFICULTY = 3   # Rápido para el demo (~0.5s por bloque)

NODES_CONFIG = [
    {'port': BASE_PORT,     'bootstrap': []},
    {'port': BASE_PORT + 1, 'bootstrap': [('localhost', BASE_PORT)]},
    {'port': BASE_PORT + 2, 'bootstrap': [('localhost', BASE_PORT)]},
    {'port': BASE_PORT + 3, 'bootstrap': [('localhost', BASE_PORT + 1)]},
    {'port': BASE_PORT + 4, 'bootstrap': [('localhost', BASE_PORT + 2)]},
]

# ──────────────────────────────────────────────────────────
# Helpers de display
# ──────────────────────────────────────────────────────────

SEP   = "─" * 70
SEP2  = "═" * 70

def header(title: str):
    print(f"\n{SEP2}")
    print(f"  {title}")
    print(SEP2)

def section(title: str):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)

def status_table(nodes):
    """Imprime tabla de estado de todos los nodos."""
    print(f"\n  {'Nodo':<12} {'Altura':>7} {'Balance':>10} {'Peers':>6} {'Mempool':>8} {'Minados':>8}")
    print(f"  {'-'*12} {'-'*7} {'-'*10} {'-'*6} {'-'*8} {'-'*8}")
    for node in nodes:
        print(
            f"  {node.id:<12} "
            f"{node.blockchain.get_height():>7} "
            f"{node.get_balance():>10.2f} "
            f"{len(node.peers_connected):>6} "
            f"{len(node.blockchain.mempool):>8} "
            f"{node.blocks_mined:>8}"
        )

# ──────────────────────────────────────────────────────────
# Creación de nodos
# ──────────────────────────────────────────────────────────

def make_node(config: dict) -> P2PNode:
    """Crea un nodo con blockchain configurada para el demo."""
    bc = Blockchain()
    bc.DIFFICULTY = DIFFICULTY

    node = P2PNode(
        host='localhost',
        port=config['port'],
        bootstrap_peers=config['bootstrap'],
        blockchain=bc,
    )
    # Modo PAUSED al inicio — activamos manualmente después
    node.mining_mode = MINING_PAUSED
    return node

# ──────────────────────────────────────────────────────────
# Demo de TXs manuales
# ──────────────────────────────────────────────────────────

async def demo_manual_txs(nodes):
    """Demuestra TXs manuales entre nodos con balance."""
    section("DEMO: Transacciones manuales")

    # Encontrar nodos con balance
    senders = [n for n in nodes if n.get_balance() > 0]
    if len(senders) < 2:
        print("  ⚠ Pocos nodos con balance — esperando más bloques...")
        return

    sender    = senders[0]
    recipient = random.choice([n for n in nodes if n != sender])

    amount = round(sender.get_balance() * 0.15, 2)
    if amount < 0.01:
        print("  ⚠ Balance insuficiente para TX manual")
        return

    print(f"\n  TX manual: {sender.id} → {recipient.id} ({amount} coins)")
    print(f"  From:   {sender.wallet.address[:20]}...")
    print(f"  To:     {recipient.wallet.address[:20]}...")
    print(f"  Amount: {amount}")

    try:
        tx = sender.create_transaction(recipient.wallet.address, amount)
        await sender.broadcast_transaction(tx)
        print(f"  ✓ TX propagada: {tx.short_hash()}")
        await asyncio.sleep(2)

        # Verificar propagación
        count = sum(
            1 for n in nodes
            if any(t.hash() == tx.hash() for t in n.blockchain.mempool)
        )
        print(f"  ✓ TX en mempool de {count}/{len(nodes)} nodos")

    except ValueError as e:
        print(f"  ✗ Error: {e}")

# ──────────────────────────────────────────────────────────
# Demo de TXs automáticas
# ──────────────────────────────────────────────────────────

async def demo_auto_txs(nodes, count: int = 5):
    """Genera TXs automáticas entre nodos con balance."""
    section(f"DEMO: {count} transacciones automáticas")

    sent = 0
    for i in range(count):
        senders = [n for n in nodes if n.get_balance() > 5]
        if not senders:
            print(f"  ⚠ Ningún nodo con balance suficiente")
            break

        sender    = random.choice(senders)
        recipient = random.choice([n for n in nodes if n != sender])
        amount    = round(random.uniform(1.0, sender.get_balance() * 0.1), 2)
        amount    = max(0.01, amount)

        try:
            tx = sender.create_transaction(recipient.wallet.address, amount)
            await sender.broadcast_transaction(tx)
            print(
                f"  TX {i+1}: {sender.id} → {recipient.id} "
                f"({amount:.2f} coins) — {tx.short_hash()}"
            )
            sent += 1
        except ValueError:
            pass

        await asyncio.sleep(0.5)

    print(f"\n  ✓ {sent} TXs automáticas enviadas")

# ──────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────

async def main():
    header("BLOCKCHAIN DEMO — CLI Stack Completo")
    print(f"""
  Nodos:      {NUM_NODES}
  Difficulty: {DIFFICULTY} (~0.5s por bloque)
  Puertos:    {BASE_PORT} – {BASE_PORT + NUM_NODES - 1}

  Presiona Ctrl+C para ver el resumen final.
""")

    # ── 1. Levantar nodos ──────────────────────────────────
    section("1. Levantando nodos P2P")
    nodes = []
    for i, config in enumerate(NODES_CONFIG, 1):
        node = make_node(config)
        nodes.append(node)
        asyncio.create_task(node.start())
        print(f"  [{i}/{NUM_NODES}] {node.id} en puerto {config['port']}")
        await asyncio.sleep(0.3)

    print(f"\n  Esperando conexiones...")
    await asyncio.sleep(3)

    section("Estado inicial de la red")
    status_table(nodes)

    # ── 2. Minar bloques iniciales ─────────────────────────
    section("2. Minando bloques iniciales (para generar balance)")
    print("  Activando minado en todos los nodos...")

    for node in nodes:
        node.set_mining_mode(MINING_AUTO)

    print("  Esperando que se minen algunos bloques...")
    await asyncio.sleep(8)

    section("Estado después del minado inicial")
    status_table(nodes)

    # ── 3. TXs manuales ───────────────────────────────────
    await demo_manual_txs(nodes)

    await asyncio.sleep(2)
    section("Estado después de TXs manuales")
    status_table(nodes)

    # ── 4. TXs automáticas ────────────────────────────────
    await demo_auto_txs(nodes, count=5)

    print("\n  Esperando que las TXs se confirmen en bloques...")
    await asyncio.sleep(6)

    # ── 5. Resumen final ──────────────────────────────────
    section("5. Resumen final")
    status_table(nodes)

    total_blocks = sum(n.blocks_mined for n in nodes)
    total_txs    = sum(
        len([tx for block in n.blockchain.chain for tx in block.transactions
             if not tx.is_coinbase()])
        for n in nodes
    ) // len(nodes)  # Promedio (cada nodo tiene la misma cadena)

    print(f"""
  Bloques minados (total red): {total_blocks}
  Altura de cadena:            {nodes[0].blockchain.get_height()}
  TXs confirmadas (aprox):     {total_txs}

  ✓ Demo completado correctamente
""")

    header("Red activa — Presiona Ctrl+C para detener")

    try:
        await asyncio.Future()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass

    # ── Resumen al salir ──────────────────────────────────
    print(f"\n\n{SEP}")
    print("  RESUMEN FINAL")
    print(SEP)
    status_table(nodes)

    print(f"\n  Wallets:")
    for node in nodes:
        print(f"    {node.id}: {node.wallet.address}")

    print(f"\n  Demo terminado.\n")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n  Demo interrumpido.\n")
