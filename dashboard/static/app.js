let lastHeight  = 0;

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
        updateMining(status);
        updateMiningProgress(status);
        updateTxBadge(status);
        updateTargetNotification(status);
        updateAddressDropdown();

        // Controles TX: solo en modo auto
        if (DASHBOARD_MODE === 'auto') {
            // (updateAddressDropdown ya se llama arriba para ambos modos)
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
// Minero (siempre activo)
// ──────────────────────────────────────────────────────────

function updateMining(status) {
    const mode   = status.mining_mode || 'manual';
    const labels = { auto: '⚙ Automático', manual: '🖐 Manual' };
    const colors = { auto: '#2e7d32',       manual: '#1565c0'   };

    // Stats — siempre actualizados independientemente del modo
    setText('blocks-mined',   status.blocks_mined   ?? 0);
    setText('mining-rewards', status.mining_rewards != null
        ? status.mining_rewards.toFixed(2) : '0.00');

    // Etiqueta de modo
    const label = document.getElementById('mining-mode-label');
    if (label) {
        label.textContent  = labels[mode] || mode;
        label.style.color  = colors[mode] || '#333';
        label.style.fontWeight = '600';
    }

    // Resaltar botón activo
    ['auto', 'manual'].forEach(m => {
        const btn = document.getElementById(`btn-${m}`);
        if (btn) btn.classList.toggle('active', m === mode);
    });

    // Botón minar: visible solo en modo MANUAL
    const mineSection = document.getElementById('mine-once-section');
    if (mineSection) mineSection.style.display = mode === 'manual' ? 'block' : 'none';

    // Indicador "Minando...": visible solo en modo AUTO
    const indicator = document.getElementById('mining-indicator');
    if (indicator) {
        indicator.classList.toggle('hidden', mode !== 'auto');
        if (mode === 'auto') setText('mining-height', status.chain_height || '-');
    }
}

// ──────────────────────────────────────────────────────────
// Progreso del PoW (ambos modos)
// ──────────────────────────────────────────────────────────

function updateMiningProgress(status) {
    const progress    = status.mining_progress || {};
    const progressRow = document.getElementById('mining-progress-row');
    if (!progressRow) return;

    if (progress.active) {
        progressRow.classList.remove('hidden');
        setText('pow-attempts', (progress.attempts || 0).toLocaleString());
        setText('pow-hashrate', Math.round(progress.hashrate || 0).toLocaleString());
    } else {
        progressRow.classList.add('hidden');
    }
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

// Actualiza el badge de TXs en el header (siempre, ambos modos)
async function updateTxBadge(status) {
    try {
        const res  = await fetch('/api/tx/status');
        const data = await res.json();
        const badge = document.getElementById('tx-mode-badge');
        if (!badge) return;
        if (!data.available) {
            badge.textContent = 'TXs: Manuales';
            badge.style.background = '#e3f2fd';
        } else {
            const isAuto = data.tx_mode === 'auto';
            badge.textContent  = isAuto ? 'TXs: ⚙ Auto' : 'TXs: 🖐 Manual';
            badge.style.background = isAuto ? '#e8f5e9' : '#e3f2fd';
            if (DASHBOARD_MODE === 'auto') updateTxModeUI(data.tx_mode);
        }
    } catch (e) { /* seed no disponible */ }
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
        <div class="block-item">
            <div class="block-header-row" onclick="showBlockDetail('${b.full_hash}')" style="cursor:pointer; flex:1;">
                <span class="block-height">#${b.height}</span>
                <span class="block-hash monospace">${b.hash}</span>
                <span class="block-txs">${b.txs} TX${b.txs !== 1 ? 's' : ''}</span>
            </div>
            <div class="block-meta">
                <span>Nonce: ${b.nonce.toLocaleString()}</span>
                <span>${b.mined_by ? 'Por: ' + b.mined_by : ''}</span>
                <span>${formatTime(b.timestamp)}</span>
                <button onclick="showVerifyModal('${b.full_hash}', ${b.height})"
                        class="btn-verify">🔎 Verificar</button>
            </div>
        </div>
    `).join('');
}

async function showBlockDetail(fullHash) {
    try {
        const block = await fetch(`/api/block/${fullHash}`).then(r => r.json());
        if (block.error) return;
        // Show a quick summary notification instead of alert
        showNotification(`Bloque #${block.nonce ? '' : ''} — Nonce: ${(block.nonce||0).toLocaleString()} · ${block.tx_count} TXs`);
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
// Notificación de ajuste de target
// ──────────────────────────────────────────────────────────

let lastSeenAdjustmentBlock = 0;

function updateTargetNotification(status) {
    const adj = status.target_info && status.target_info.adjustment;
    if (!adj) return;
    if (adj.block <= lastSeenAdjustmentBlock) return;
    lastSeenAdjustmentBlock = adj.block;
    const dir   = adj.direction === 'easier' ? '↑ más fácil' : '↓ más difícil';
    const ratio = adj.ratio < 1
        ? `${(1/adj.ratio).toFixed(1)}× más difícil`
        : `${adj.ratio.toFixed(1)}× más fácil`;
    showNotification(`🎯 Target ajustado en bloque #${adj.block} — ${ratio} — ${adj.estimated} por bloque`);
}

// ──────────────────────────────────────────────────────────
// Modal: Vista previa de TX (firma)
// ──────────────────────────────────────────────────────────

async function previewTx() {
    const toAddress = document.getElementById('to_address').value.trim();
    const amount    = document.getElementById('amount').value;
    if (!toAddress || !amount) {
        showNotification('Completa destinatario y cantidad antes de la vista previa');
        return;
    }
    try {
        const res  = await fetch('/api/tx/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ to_address: toAddress, amount: parseFloat(amount) }),
        });
        const data = await res.json();
        if (data.error) { showNotification('Error: ' + data.error); return; }

        setText('prev-from',   data.from);
        setText('prev-to',     data.to);
        setText('prev-amount', `${data.amount} coins`);
        setText('prev-txid',   data.txid);
        setText('prev-sig',    data.signature);
        const validEl = document.getElementById('prev-valid');
        if (validEl) {
            validEl.textContent = data.valid ? '✅ Válida' : '❌ Inválida';
            validEl.style.color = data.valid ? '#2e7d32' : '#c62828';
        }
        document.getElementById('tx-preview-modal').classList.remove('hidden');
    } catch (e) {
        showNotification('Error al generar vista previa');
    }
}

function closeTxPreview() {
    document.getElementById('tx-preview-modal').classList.add('hidden');
}

function confirmTx() {
    closeTxPreview();
    document.getElementById('tx-form').submit();
}

// ──────────────────────────────────────────────────────────
// Modal: Verificación de bloque
// ──────────────────────────────────────────────────────────

async function showVerifyModal(fullHash, height) {
    const modal = document.getElementById('verify-modal');
    if (!modal) return;
    setText('verify-block-height', `#${height}`);
    document.getElementById('verify-results').innerHTML = '<div class="empty">Verificando...</div>';
    modal.classList.remove('hidden');

    try {
        const data = await fetch(`/api/block/${fullHash}/verify`).then(r => r.json());
        if (data.error) {
            document.getElementById('verify-results').innerHTML = `<div class="empty">Error: ${data.error}</div>`;
            return;
        }

        const checks = data.checks;
        const rows   = Object.values(checks).map(c => `
            <div class="check-row ${c.ok ? 'verify-result-ok' : 'verify-result-fail'}">
                <span class="check-icon">${c.ok ? '✅' : '❌'}</span>
                <div class="check-info">
                    <div class="check-label">${c.label}</div>
                    <div class="check-detail">${c.detail}</div>
                </div>
            </div>
        `).join('');

        const summary = data.all_valid
            ? '<div class="verify-all-ok">✅ Bloque completamente válido</div>'
            : '<div class="verify-all-fail">❌ Bloque con errores de validación</div>';

        document.getElementById('verify-results').innerHTML = rows + summary;
    } catch (e) {
        document.getElementById('verify-results').innerHTML = `<div class="empty">Error: ${e.message}</div>`;
    }
}

function closeVerifyModal() {
    document.getElementById('verify-modal').classList.add('hidden');
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
