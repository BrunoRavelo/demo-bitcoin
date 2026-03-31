"""
Dashboard Flask para cada nodo P2P
"""
import asyncio
from flask import Flask, render_template, jsonify, request, redirect
from network.p2p_node import MINING_AUTO, MINING_MANUAL


class NodeDashboard:
    def __init__(self, node, dashboard_port, dashboard_mode='manual', orchestrator=None):
        self.node           = node
        self.dashboard_port = dashboard_port
        self.dashboard_mode = dashboard_mode
        self.orchestrator   = orchestrator
        self.app            = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):

        @self.app.route('/')
        def index():
            return render_template('dashboard.html',
                node_id=self.node.id,
                p2p_port=self.node.port,
                dashboard_port=self.dashboard_port,
                dashboard_mode=self.dashboard_mode,
            )

        @self.app.route('/api/status')
        def api_status():
            return jsonify({
                'node_id':         self.node.id,
                'address':         self.node.wallet.address,
                'balance':         self.node.get_balance(),
                'chain_height':    self.node.blockchain.get_height(),
                'mempool_count':   len(self.node.blockchain.mempool),
                'peers_count':     len(self.node.peers_connected),
                'mining_mode':     self.node.mining_mode,
                'blocks_mined':    self.node.blocks_mined,
                'mining_rewards':  self.node.mining_rewards,
                'dashboard_mode':  self.dashboard_mode,
                'mining_progress': self.node.mining_progress,
                'latest_hash':     self.node.blockchain.get_latest_block().hash[:16] if self.node.blockchain.chain else None,
                'target_info': {
                    'display':    self.node.blockchain.get_target_hex(),
                    'estimated':  self.node.blockchain.get_estimated_block_time(),
                    'adjustment': self.node.blockchain._last_adjustment,
                },
            })

        @self.app.route('/api/wallet')
        def api_wallet():
            return jsonify({'address': self.node.wallet.address, 'balance': self.node.get_balance()})

        @self.app.route('/api/peers')
        def api_peers():
            return jsonify([{'address': addr, 'status': 'connected'} for addr in self.node.peers_connected.keys()])

        @self.app.route('/api/mempool')
        def api_mempool():
            return jsonify([{
                'txid':      tx.short_hash(),
                'from':      tx.from_address[:16] + '...',
                'to':        tx.to_address[:16]   + '...',
                'amount':    tx.amount,
                'timestamp': tx.timestamp,
            } for tx in self.node.blockchain.mempool])

        @self.app.route('/api/chain')
        def api_chain():
            chain  = self.node.blockchain.chain
            recent = []
            for block in reversed(chain[-5:]):
                coinbase_to = None
                for tx in block.transactions:
                    if tx.is_coinbase():
                        coinbase_to = tx.to_address[:16] + '...'
                        break
                recent.append({
                    'hash':      block.hash[:16] + '...',
                    'full_hash': block.hash,
                    'height':    chain.index(block),
                    'txs':       len(block.transactions),
                    'timestamp': block.header.timestamp,
                    'nonce':     block.header.nonce,
                    'target':    block.header.difficulty_display,
                    'mined_by':  coinbase_to,
                })
            return jsonify({'height': len(chain), 'latest_hash': chain[-1].hash[:16] + '...' if chain else None, 'blocks': recent})

        @self.app.route('/api/block/<block_hash>')
        def api_block(block_hash):
            block = self.node.blockchain.get_block_by_hash(block_hash)
            if not block:
                return jsonify({'error': 'Bloque no encontrado'}), 404
            return jsonify({
                'hash':        block.hash,
                'prev_hash':   block.header.prev_hash[:16] + '...',
                'merkle_root': block.header.merkle_root[:16] + '...',
                'timestamp':   block.header.timestamp,
                'nonce':       block.header.nonce,
                'target':      block.header.difficulty_display,
                'txs': [{
                    'txid':   tx.short_hash(),
                    'from':   tx.from_address[:16] + '...',
                    'to':     tx.to_address[:16]   + '...',
                    'amount': tx.amount,
                    'type':   'coinbase' if tx.is_coinbase() else 'normal',
                } for tx in block.transactions],
                'tx_count': len(block.transactions),
            })

        @self.app.route('/api/block/<block_hash>/verify')
        def api_block_verify(block_hash):
            block = self.node.blockchain.get_block_by_hash(block_hash)
            if not block:
                return jsonify({'error': 'Bloque no encontrado'}), 404

            chain  = self.node.blockchain.chain
            idx    = next((i for i, b in enumerate(chain) if b.hash == block_hash), None)
            pow_ok    = block.validate_pow()
            merkle_ok = block.validate_merkle_root()
            txs_ok    = block.validate_transactions()
            if idx == 0:
                prev_ok = True   # genesis
            elif idx is not None:
                prev_ok = block.header.prev_hash == chain[idx - 1].hash
            else:
                prev_ok = False

            return jsonify({
                'hash':      block_hash,
                'height':    idx,
                'all_valid': pow_ok and merkle_ok and prev_ok and txs_ok,
                'checks': {
                    'pow':    {'ok': pow_ok,    'label': 'Prueba de Trabajo',  'detail': 'int(hash,16) < target'},
                    'merkle': {'ok': merkle_ok, 'label': 'Merkle Root',        'detail': 'Raíz del árbol de TXs correcta'},
                    'prev':   {'ok': prev_ok,   'label': 'Enlace prev_hash',   'detail': 'Conecta con el bloque anterior'},
                    'txs':    {'ok': txs_ok,    'label': 'Firmas de TXs',      'detail': f'{len(block.transactions)} transacciones verificadas'},
                },
            })

        @self.app.route('/api/tx/preview', methods=['POST'])
        def api_tx_preview():
            try:
                data = request.get_json(silent=True)
                if not data:
                    return jsonify({'error': 'Body JSON requerido'}), 400
                to_address = data.get('to_address')
                amount     = data.get('amount')
                if not to_address or amount is None:
                    return jsonify({'error': 'to_address y amount requeridos'}), 400
                tx      = self.node.create_transaction(to_address, float(amount))
                sig_hex = tx.signature.hex() if hasattr(tx, 'signature') and tx.signature else 'N/A'
                return jsonify({
                    'txid':      tx.hash(),
                    'from':      tx.from_address,
                    'to':        tx.to_address,
                    'amount':    tx.amount,
                    'signature': sig_hex[:48] + '...' if len(sig_hex) > 48 else sig_hex,
                    'valid':     tx.is_valid(),
                })
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/all_nodes')
        def api_all_nodes():
            try:
                peers = self.node.seed_client.get_peers()
                nodes = [{'name': p.get('node_id', f"node_{p['port']}"), 'host': p['host'], 'p2p_port': p['port']} for p in peers]
                nodes.insert(0, {'name': self.node.id + ' (este nodo)', 'host': self.node.host, 'p2p_port': self.node.port})
                return jsonify(nodes)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/addresses')
        def api_addresses():
            try:
                return jsonify(self.node.seed_client.get_addresses(exclude_host=self.node.host, exclude_port=self.node.port))
            except Exception:
                return jsonify([])

        @self.app.route('/api/mine/auto', methods=['POST'])
        def api_mine_auto():
            try:
                self.node.set_mining_mode(MINING_AUTO)
                return jsonify({'status': 'ok', 'mode': MINING_AUTO})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/mine/manual', methods=['POST'])
        def api_mine_manual():
            try:
                self.node.set_mining_mode(MINING_MANUAL)
                return jsonify({'status': 'ok', 'mode': MINING_MANUAL})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/mine/once', methods=['POST'])
        def api_mine_once():
            try:
                if self.node.loop is None:
                    return jsonify({'error': 'Nodo no iniciado aún'}), 503
                asyncio.run_coroutine_threadsafe(self.node.mine_once(), self.node.loop)
                return jsonify({'status': 'ok'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/tx/auto', methods=['POST'])
        def api_tx_auto():
            if self.orchestrator is None:
                return jsonify({'error': 'Orquestador no disponible'}), 404
            try:
                from core.tx_orchestrator import ORCH_AUTO
                self.orchestrator.set_mode(ORCH_AUTO)
                return jsonify({'status': 'ok', 'tx_mode': ORCH_AUTO})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/tx/manual', methods=['POST'])
        def api_tx_manual():
            if self.orchestrator is None:
                return jsonify({'error': 'Orquestador no disponible'}), 404
            try:
                from core.tx_orchestrator import ORCH_MANUAL
                self.orchestrator.set_mode(ORCH_MANUAL)
                return jsonify({'status': 'ok', 'tx_mode': ORCH_MANUAL})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/tx/status', methods=['GET'])
        def api_tx_status():
            if self.orchestrator is None:
                return jsonify({'available': False, 'tx_mode': 'manual'})
            stats = self.orchestrator.get_stats()
            return jsonify({'available': True, 'tx_mode': stats['mode'], 'txs_sent': stats['txs_sent'], 'running': stats['running']})

        @self.app.route('/send_tx', methods=['POST'])
        def send_tx():
            try:
                to_address = request.form['to_address']
                amount     = float(request.form['amount'])
                tx         = self.node.create_transaction(to_address, amount)
                asyncio.run_coroutine_threadsafe(self.node.broadcast_transaction(tx), self.node.loop)
                return redirect('/')
            except ValueError as e:
                return f"Error: {e}", 400
            except Exception as e:
                return f"Error inesperado: {e}", 500

        @self.app.route('/api/tx/create', methods=['POST'])
        def api_tx_create():
            try:
                data = request.get_json(silent=True)
                if not data:
                    return jsonify({'error': 'Body JSON requerido'}), 400
                to_address = data.get('to_address')
                amount     = data.get('amount')
                if not to_address or amount is None:
                    return jsonify({'error': 'to_address y amount requeridos'}), 400
                tx = self.node.create_transaction(to_address, float(amount))
                asyncio.run_coroutine_threadsafe(self.node.broadcast_transaction(tx), self.node.loop)
                return jsonify({'status': 'ok', 'txid': tx.hash(), 'from': tx.from_address, 'to': tx.to_address, 'amount': tx.amount})
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                return jsonify({'error': f'Error inesperado: {e}'}), 500

    def run(self):
        self.app.run(host='0.0.0.0', port=self.dashboard_port, debug=False, use_reloader=False)
