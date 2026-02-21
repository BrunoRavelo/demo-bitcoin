"""
Dashboard Flask para cada nodo P2P
"""

from flask import Flask, render_template, jsonify, request, redirect
import asyncio

class NodeDashboard:
    """Dashboard web para un nodo P2P"""
    
    def __init__(self, node, dashboard_port):
        """
        Args:
            node: Instancia de P2PNode
            dashboard_port: Puerto para el servidor Flask
        """
        self.node = node
        self.dashboard_port = dashboard_port
        self.app = Flask(__name__)
        self.setup_routes()
    
    def setup_routes(self):
        """Configura las rutas del dashboard"""
        
        @self.app.route('/')
        def index():
            """Página principal del dashboard"""
            return render_template('dashboard.html',
                node_id=self.node.id,
                p2p_port=self.node.port,
                dashboard_port=self.dashboard_port
            )
        
        @self.app.route('/api/info')
        def api_info():
            """Info general del nodo"""
            return jsonify({
                'node_id': self.node.id,
                'address': self.node.wallet.address,
                'balance': self.node.get_balance(),
                'peers_count': len(self.node.peers_connected),
                'mempool_count': len(self.node.mempool)
            })
        
        @self.app.route('/api/wallet')
        def api_wallet():
            """Info de la wallet"""
            return jsonify({
                'address': self.node.wallet.address,
                'balance': self.node.get_balance()
            })
        
        @self.app.route('/api/peers')
        def api_peers():
            """Lista de peers conectados"""
            peers = []
            for peer_addr in self.node.peers_connected.keys():
                peers.append({
                    'address': peer_addr,
                    'status': 'connected'
                })
            return jsonify(peers)
        
        @self.app.route('/api/mempool')
        def api_mempool():
            """Transacciones en mempool"""
            txs = []
            for tx in self.node.mempool:
                txs.append({
                    'txid': tx.hash()[:16] + '...',
                    'from': tx.from_address[:12] + '...',
                    'to': tx.to_address[:12] + '...',
                    'amount': tx.amount,
                    'timestamp': tx.timestamp
                })
            return jsonify(txs)
        
        @self.app.route('/api/all_nodes')
        def api_all_nodes():
            """Lista hardcodeada de todos los nodos (para dropdown)"""
            nodes = []
            for i in range(5):
                p2p_port = 5000 + i
                dashboard_port = 8000 + i
                nodes.append({
                    'name': f'Nodo {i+1}',
                    'p2p_port': p2p_port,
                    'dashboard_port': dashboard_port
                })
            return jsonify(nodes)
        
        @self.app.route('/send_tx', methods=['POST'])
        def send_tx():
            """Crear y enviar transacción"""
            try:
                to_address = request.form['to_address']
                amount = float(request.form['amount'])
                
                # Crear TX
                tx = self.node.create_transaction(to_address, amount)
                
                # Broadcast (asyncio desde thread de Flask)
                asyncio.run_coroutine_threadsafe(
                    self.node.broadcast_transaction(tx),
                    self.node.loop
                )
                
                return redirect('/')
            except Exception as e:
                return f"Error: {e}", 400
    
    def run(self):
        """Inicia servidor Flask"""
        self.app.run(
            host='0.0.0.0',
            port=self.dashboard_port,
            debug=False,
            use_reloader=False  # Importante: evita doble inicio
        )