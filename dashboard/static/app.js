// Auto-refresh y manejo de datos del dashboard

// Función principal de actualización
async function updateData() {
    try {
        // Obtener info general
        const info = await fetch('/api/info').then(r => r.json());
        
        // Actualizar wallet
        document.getElementById('wallet-address').textContent = info.address;
        document.getElementById('wallet-balance').textContent = info.balance.toFixed(2);
        
        // Actualizar contadores
        document.getElementById('peers-count').textContent = info.peers_count;
        document.getElementById('mempool-count').textContent = info.mempool_count;
        
        // Actualizar lista de peers
        await updatePeers();
        
        // Actualizar mempool
        await updateMempool();
        
    } catch (error) {
        console.error('Error actualizando datos:', error);
    }
}

// Actualizar lista de peers
async function updatePeers() {
    try {
        const peers = await fetch('/api/peers').then(r => r.json());
        const peersList = document.getElementById('peers-list');
        
        if (peers.length === 0) {
            peersList.innerHTML = '<li class="empty">Sin peers conectados</li>';
        } else {
            peersList.innerHTML = peers.map(peer => 
                `<li>${peer.address}</li>`
            ).join('');
        }
    } catch (error) {
        console.error('Error actualizando peers:', error);
    }
}

// Actualizar mempool
async function updateMempool() {
    try {
        const mempool = await fetch('/api/mempool').then(r => r.json());
        const mempoolList = document.getElementById('mempool-list');
        
        if (mempool.length === 0) {
            mempoolList.innerHTML = '<div class="empty">Sin transacciones pendientes</div>';
        } else {
            mempoolList.innerHTML = mempool.map(tx => `
                <div class="tx-item">
                    <div class="tx-hash">${tx.txid}</div>
                    <div class="tx-details">
                        <span>${tx.from} → ${tx.to}</span>
                        <span class="tx-amount">${tx.amount} coins</span>
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error actualizando mempool:', error);
    }
}

// Copiar address al portapapeles
function copyAddress() {
    const address = document.getElementById('wallet-address').textContent;
    navigator.clipboard.writeText(address).then(() => {
        alert('Address copiada: ' + address);
    }).catch(err => {
        console.error('Error copiando:', err);
    });
}

// Inicialización cuando carga la página
document.addEventListener('DOMContentLoaded', function() {
    updateData();
    setInterval(updateData, 2000);
});