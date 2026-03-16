"""
Dashboard Flask para cada nodo P2P

Sprint 3.3:
- Todos los endpoints usan self.node.blockchain (un solo mempool)
- self.node.loop ya está correctamente inicializado en P2PNode.start()
- api_all_nodes() ahora consulta el seed en lugar de hardcodear 5 nodos
"""

import asyncio
from flask import Flask, render_template, jsonify, request, redirect


class NodeDashboard:
    """Dashboard web para un nodo P2P."""

    def __init__(self, node, dashboard_port: int):
        """
        Args:
            node:           Instancia de P2PNode
            dashboard_port: Puerto Flask
        """
        self.node           = node
        self.dashboard_port = dashboard_port
        self.app            = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        """Registra todos los endpoints del dashboard."""

        # ── Página principal ───────────────────────────────────

        @self.app.route('/')
        def index():
            return render_template(
                'dashboard.html',
                node_id=self.node.id,
                p2p_port=self.node.port,
                dashboard_port=self.dashboard_port,
            )

        # ── API: info general ──────────────────────────────────

        @self.app.route('/api/info')
        def api_info():
            """Resumen del nodo: wallet, red y blockchain."""
            return jsonify({
                'node_id':      self.node.id,
                'address':      self.node.wallet.address,
                'balance':      self.node.get_balance(),
                'peers_count':  len(self.node.peers_connected),
                'mempool_count': len(self.node.blockchain.mempool),
                'chain_height': len(self.node.blockchain.chain),
            })

        # ── API: wallet ────────────────────────────────────────

        @self.app.route('/api/wallet')
        def api_wallet():
            return jsonify({
                'address': self.node.wallet.address,
                'balance': self.node.get_balance(),
            })

        # ── API: peers ─────────────────────────────────────────

        @self.app.route('/api/peers')
        def api_peers():
            peers = [
                {'address': addr, 'status': 'connected'}
                for addr in self.node.peers_connected.keys()
            ]
            return jsonify(peers)

        # ── API: mempool ───────────────────────────────────────

        @self.app.route('/api/mempool')
        def api_mempool():
            """Transacciones pendientes desde blockchain.mempool."""
            txs = [
                {
                    'txid':      tx.short_hash(),
                    'from':      tx.from_address[:12] + '...',
                    'to':        tx.to_address[:12]   + '...',
                    'amount':    tx.amount,
                    'timestamp': tx.timestamp,
                }
                for tx in self.node.blockchain.mempool
            ]
            return jsonify(txs)

        # ── API: nodos conocidos (desde seed) ──────────────────

        @self.app.route('/api/all_nodes')
        def api_all_nodes():
            """
            Lista de nodos activos obtenida del seed.
            Ya no está hardcodeada a 5 nodos.
            """
            try:
                peers = self.node.seed_client.get_peers()
                nodes = [
                    {
                        'name':     p.get('node_id', f"node_{p['port']}"),
                        'host':     p['host'],
                        'p2p_port': p['port'],
                    }
                    for p in peers
                ]
                # Agregar este mismo nodo al principio
                nodes.insert(0, {
                    'name':     self.node.id + ' (este nodo)',
                    'host':     self.node.host,
                    'p2p_port': self.node.port,
                })
                return jsonify(nodes)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # ── Enviar transacción ─────────────────────────────────

        @self.app.route('/send_tx', methods=['POST'])
        def send_tx():
            """
            Crear TX y propagarla a la red.
            Usa run_coroutine_threadsafe porque Flask corre en un thread
            distinto al event loop de asyncio.
            """
            try:
                to_address = request.form['to_address']
                amount     = float(request.form['amount'])

                # Crear y firmar TX (síncrono — solo lógica local)
                tx = self.node.create_transaction(to_address, amount)

                # Broadcast (asyncio desde thread de Flask)
                # self.node.loop fue capturado en P2PNode.start()
                asyncio.run_coroutine_threadsafe(
                    self.node.broadcast_transaction(tx),
                    self.node.loop,
                )

                return redirect('/')

            except ValueError as e:
                # Balance insuficiente u otro error de validación
                return f"Error: {e}", 400
            except Exception as e:
                return f"Error inesperado: {e}", 500

    # ──────────────────────────────────────────────────────────
    # Arranque
    # ──────────────────────────────────────────────────────────

    def run(self):
        """Inicia el servidor Flask."""
        self.app.run(
            host='0.0.0.0',
            port=self.dashboard_port,
            debug=False,
            use_reloader=False,  # Evita doble inicio en thread
        )
