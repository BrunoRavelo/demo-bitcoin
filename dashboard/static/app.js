// Dashboard — lógica completa
// DASHBOARD_MODE viene definido en el HTML por Jinja2

let lastHeight  = 0;
let currentMode = '';

// ──────────────────────────────────────────────────────────
// Loop principal
// ──────────────────────────────────────────────────────────

async function updateData() {
    try {
        const promises = [
            fetch('/api/status').then(r => r.json()),
            fetch('/api/chain').then(r => r.json()),
            fetch('/api/peers').then(r => r.json()),
            fetch('/api/mempool').then(r => r.json()),
        ];

        const [status, chain, peers, mempool] = await Promise.all(promises);

        updateWallet(status);
        updateChain(chain);
        updatePeers(peers);
        updateMempool(mempool);
        updateHeader(status, chain);

        // Secciones exclusivas del modo auto
        if (DASHBOARD_MODE === 'auto') {
            updateMining(status);
            updateAddressDropdown();
            updateTxStatus();
        }

    } catch (err) {
        console.error('Error actualizando dashboard:', err);
    }
}

// ──────────────────────────────────────────────────────────
// Wallet
// ──────────────────────────────────────────────────────────

function updateWallet(status) {
    setText('wallet-address', status.address || '-');
    setText('wallet-balance', status.balance != null
        ? status.balance.toFixed(2) : '-');
}

// ──────────────────────────────────────────────────────────
// Header
// ──────────────────────────────────────────────────────────

function updateHeader(status, chain) {
    setText('chain-badge', `Altura: ${chain.height}`);
}

// ──────────────────────────────────────────────────────────
// Minero (solo modo auto)
// ──────────────────────────────────────────────────────────

function updateMining(status) {
    const mode   = status.mining_mode || 'manual';
    const labels = { auto: '⚙ Automático', manual: '🖐 Manual' };
    const colors = { auto: '#2e7d32',       manual: '#1565c0'   };

    const label = document.getElementById('mining-mode-label');
    if (label) {
        label.textContent = labels[mode] || mode;
        label.style.color = colors[mode] || '#333';
        label.style.fontWeight = '600';
    }

    setText('blocks-mined',   status.blocks_mined   || 0);
    setText('mining-rewards', status.mining_rewards != null
        ? status.mining_rewards.toFixed(2) : '0.00');

    // Resaltar botón activo
    ['auto', 'manual'].forEach(m => {
        const btn = document.getElementById(`btn-${m}`);
        if (btn) btn.classList.toggle('active', m === mode);
    });

    // Botón "minar ahora": en modo auto solo en MANUAL,
    // en modo manual siempre visible (no hay toggle)
    if (DASHBOARD_MODE === 'auto') {
        const section = document.getElementById('mine-once-section');
        if (section) section.style.display = mode === 'manual' ? 'block' : 'none';
    }

    // Indicador de minando solo en AUTO
    const indicator = document.getElementById('mining-indicator');
    if (indicator) {
        indicator.classList.toggle('hidden', mode !== 'auto');
        if (mode === 'auto') setText('mining-height', status.chain_height || '-');
    }

    currentMode = mode;
}

// ──────────────────────────────────────────────────────────
// Control de modo de TXs (solo modo auto)
// ──────────────────────────────────────────────────────────

async function setTxMode(mode) {
    try {
        const endpoint = mode === 'auto' ? '/api/tx/auto' : '/api/tx/manual';
        const res  = await fetch(endpoint, { method: 'POST' });
        const data = await res.json();

        if (data.error) {
            console.warn('TXs:', data.error);
            return;
        }

        updateTxModeUI(data.tx_mode);
    } catch (e) {
        console.error('Error cambiando modo TXs:', e);
    }
}

async function updateTxStatus() {
    try {
        const res  = await fetch('/api/tx/status');
        const data = await res.json();
        if (data.available) {
            updateTxModeUI(data.tx_mode);
            const sent = document.getElementById('tx-sent-count');
            if (sent) sent.textContent = data.txs_sent || 0;
        }
    } catch (e) { /* silencioso */ }
}

function updateTxModeUI(mode) {
    const labels = { auto: '⚙ Automático', manual: '🖐 Manual' };
    setText('tx-mode-label', labels[mode] || mode);

    ['auto', 'manual'].forEach(m => {
        const btn = document.getElementById(`btn-tx-${m}`);
        if (btn) btn.classList.toggle('active', m === mode);
    });
}

// ──────────────────────────────────────────────────────────
// Blockchain
// ──────────────────────────────────────────────────────────

function updateChain(chain) {
    setText('chain-height', chain.height);
    setText('latest-hash',  chain.latest_hash || '-');

    const newHeight = chain.height;
    if (lastHeight > 0 && newHeight > lastHeight) {
        showNotification(`¡Nuevo bloque #${newHeight - 1} añadido!`);
    }
    lastHeight = newHeight;

    const list = document.getElementById('blocks-list');
    if (!list) return;

    if (!chain.blocks || chain.blocks.length === 0) {
        list.innerHTML = '<div class="empty">Solo el bloque génesis</div>';
        return;
    }

    list.innerHTML = chain.blocks.map(b => `
        <div class="block-item" onclick="showBlockDetail('${b.full_hash}')">
            <div class="block-header-row">
                <span class="block-height">#${b.height}</span>
                <span class="block-hash monospace">${b.hash}</span>
                <span class="block-txs">${b.txs} TX${b.txs !== 1 ? 's' : ''}</span>
            </div>
            <div class="block-meta">
                <span>Nonce: ${b.nonce.toLocaleString()}</span>
                <span>${b.mined_by ? 'Por: ' + b.mined_by : ''}</span>
                <span>${formatTime(b.timestamp)}</span>
            </div>
        </div>
    `).join('');
}

async function showBlockDetail(fullHash) {
    try {
        const block = await fetch(`/api/block/${fullHash}`).then(r => r.json());
        if (block.error) return;
        const info = `Bloque #\nHash: ${block.hash.slice(0,32)}...\nNonce: ${block.nonce}\nTXs: ${block.tx_count}\n\n` +
            block.txs.map(tx =>
                `${tx.type === 'coinbase' ? '[COINBASE]' : '[TX]'} ${tx.from} → ${tx.to}: ${tx.amount} coins`
            ).join('\n');
        alert(info);
    } catch (e) {
        console.error('Error obteniendo bloque:', e);
    }
}

// ──────────────────────────────────────────────────────────
// Peers
// ──────────────────────────────────────────────────────────

function updatePeers(peers) {
    setText('peers-count', peers.length);
    const list = document.getElementById('peers-list');
    if (!list) return;

    list.innerHTML = peers.length === 0
        ? '<li class="empty">Sin peers conectados</li>'
        : peers.map(p => `<li><span class="peer-dot">●</span> ${p.address}</li>`).join('');
}

async function updateAddressDropdown() {
    try {
        const addresses = await fetch('/api/addresses').then(r => r.json());
        const select    = document.getElementById('address-select');
        if (!select) return;

        const current = select.value;
        select.innerHTML = '<option value="">— conocidos —</option>' +
            addresses.map(a =>
                `<option value="${a.wallet_address}">${a.node_id}: ${a.wallet_address.slice(0,16)}...</option>`
            ).join('');
        if (current) select.value = current;
    } catch (e) { /* seed no disponible */ }
}

// ──────────────────────────────────────────────────────────
// Mempool
// ──────────────────────────────────────────────────────────

function updateMempool(mempool) {
    setText('mempool-count', mempool.length);
    const list = document.getElementById('mempool-list');
    if (!list) return;

    list.innerHTML = mempool.length === 0
        ? '<div class="empty">Sin transacciones pendientes</div>'
        : mempool.map(tx => `
            <div class="tx-item">
                <div class="tx-hash">${tx.txid}</div>
                <div class="tx-details">
                    <span class="tx-addr">${tx.from} → ${tx.to}</span>
                    <span class="tx-amount">${tx.amount} coins</span>
                </div>
            </div>
        `).join('');
}

// ──────────────────────────────────────────────────────────
// Control de minado
// ──────────────────────────────────────────────────────────

async function setMiningMode(mode) {
    try {
        await fetch(`/api/mine/${mode}`, { method: 'POST' });
        await updateData();
    } catch (e) {
        console.error('Error cambiando modo de minado:', e);
    }
}

async function mineOnce() {
    const btn = document.getElementById('btn-mine-once');
    if (btn) { btn.disabled = true; btn.textContent = '⛏ Minando...'; }
    try {
        const res  = await fetch('/api/mine/once', { method: 'POST' });
        const data = await res.json();
        if (data.error) alert('Error: ' + data.error);
    } catch (e) {
        console.error('Error minando:', e);
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = '⛏ Minar un bloque ahora'; }
    }
}

// ──────────────────────────────────────────────────────────
// Utilidades
// ──────────────────────────────────────────────────────────

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function copyAddress() {
    const address = document.getElementById('wallet-address').textContent;
    navigator.clipboard.writeText(address).then(() => {
        showNotification('Address copiada al portapapeles');
    });
}

function fillAddress(value) {
    if (value) document.getElementById('to_address').value = value;
}

function formatTime(timestamp) {
    if (!timestamp) return '';
    return new Date(timestamp * 1000).toLocaleTimeString();
}

function showNotification(msg) {
    const el = document.getElementById('block-notification');
    if (!el) return;
    el.textContent = msg;
    el.classList.remove('hidden');
    setTimeout(() => el.classList.add('hidden'), 4000);
}

// ──────────────────────────────────────────────────────────
// Inicialización
// ──────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    updateData();
    setInterval(updateData, 2000);
});
