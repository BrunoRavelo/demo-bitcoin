// Dashboard Global — lógica frontend
// Auto-refresh cada 3 segundos (más lento que el individual para no saturar)

let lastMaxHeight = 0;

// ──────────────────────────────────────────────────────────
// Loop principal
// ──────────────────────────────────────────────────────────

async function updateNetwork() {
    try {
        const [network, orch] = await Promise.all([
            fetch('/api/network').then(r => r.json()),
            fetch('/api/orchestrator').then(r => r.json()),
        ]);

        updateSeedBadge(network.seed_online);
        updateSummary(network.summary);
        updateNodesTable(network.nodes, network.summary.max_height);
        updateOrchestrator(orch);
        updateRefreshBadge();

    } catch (err) {
        console.error('Error actualizando red:', err);
        document.getElementById('refresh-badge').textContent = '⚠ Error de conexión';
    }
}

// ──────────────────────────────────────────────────────────
// Seed badge
// ──────────────────────────────────────────────────────────

function updateSeedBadge(online) {
    const el = document.getElementById('seed-badge');
    if (!el) return;
    el.textContent = online ? '🟢 Seed online' : '🔴 Seed offline';
    el.style.background = online ? '#e8f5e9' : '#fce4ec';
}

function updateRefreshBadge() {
    const el = document.getElementById('refresh-badge');
    if (!el) return;
    const now = new Date().toLocaleTimeString();
    el.textContent = `Actualizado: ${now}`;
}

// ──────────────────────────────────────────────────────────
// Resumen
// ──────────────────────────────────────────────────────────

function updateSummary(s) {
    setText('s-total-nodes', s.total_nodes);
    setText('s-online',      s.online_nodes);
    setText('s-offline',     s.offline_nodes);
    setText('s-height',      s.max_height);
    setText('s-out-sync',    s.out_of_sync);
    setText('s-mempool',     s.total_mempool);
    setText('s-mined',       s.total_mined);
    setText('s-mining-auto', s.mining_auto);

    // Notificación si la altura aumentó
    if (lastMaxHeight > 0 && s.max_height > lastMaxHeight) {
        showNotification(`¡Nuevo bloque #${s.max_height - 1} confirmado en la red!`);
    }
    lastMaxHeight = s.max_height;

    // Colorear tarjeta de desfasados
    const outCard = document.getElementById('s-out-sync')?.closest('.summary-card');
    if (outCard) {
        outCard.style.background = s.out_of_sync > 0 ? '#fff3e0' : '';
    }
}

// ──────────────────────────────────────────────────────────
// Tabla de nodos
// ──────────────────────────────────────────────────────────

function updateNodesTable(nodes, maxHeight) {
    const tbody = document.getElementById('nodes-tbody');
    if (!tbody) return;

    if (!nodes || nodes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="empty">Sin nodos registrados en el seed</td></tr>';
        return;
    }

    tbody.innerHTML = nodes.map(node => {
        const online      = node.online;
        const lag         = maxHeight - node.chain_height;
        const inSync      = lag <= 2;
        const miningMode  = node.mining_mode || '-';

        const syncIcon  = !online      ? '⬛'
                        : inSync       ? '✅'
                        : lag <= 5     ? '⚠️'
                        : '🔴';

        const syncText  = !online      ? '-'
                        : inSync       ? 'Sync'
                        : `−${lag}`;

        const modeLabel = miningMode === 'auto'   ? '⚙ Auto'
                        : miningMode === 'manual' ? '🖐 Manual'
                        : '-';

        const rowClass  = !online      ? 'row-offline'
                        : !inSync      ? 'row-desynced'
                        : '';

        const dashboardUrl = `http://${node.dashboard_port ? window.location.hostname : 'localhost'}:${node.dashboard_port}`;

        return `
            <tr class="${rowClass}">
                <td class="node-id">${node.node_id || '-'}</td>
                <td>${online ? '<span class="dot green">●</span> Online' : '<span class="dot red">●</span> Offline'}</td>
                <td class="monospace">${online ? node.chain_height : '-'}</td>
                <td>${syncIcon} <span class="sync-text ${inSync ? 'sync-ok' : 'sync-lag'}">${syncText}</span></td>
                <td class="balance">${online ? node.balance.toFixed(2) : '-'}</td>
                <td>${online ? node.peers_count : '-'}</td>
                <td>${online ? node.mempool_count : '-'}</td>
                <td>${online ? modeLabel : '-'}</td>
                <td>${online ? node.blocks_mined : '-'}</td>
                <td>${online ? `<a href="${dashboardUrl}" target="_blank" class="link">:${node.dashboard_port}</a>` : '-'}</td>
            </tr>
        `;
    }).join('');
}

// ──────────────────────────────────────────────────────────
// Orquestador
// ──────────────────────────────────────────────────────────

function updateOrchestrator(orch) {
    if (!orch || !orch.available) return;

    const mode   = orch.mode || 'manual';
    const labels = { auto: '⚙ Automático', manual: '🖐 Manual' };
    const colors = { auto: '#2e7d32', manual: '#1565c0' };

    const modeEl = document.getElementById('orch-mode');
    if (modeEl) {
        modeEl.textContent  = labels[mode] || mode;
        modeEl.style.color  = colors[mode] || '#333';
        modeEl.style.fontWeight = '600';
    }

    setText('orch-sent',   orch.txs_sent   || 0);
    setText('orch-failed', orch.txs_failed || 0);
    setText('orch-rate',   orch.success_rate != null
        ? (orch.success_rate * 100).toFixed(1) + '%' : '-');

    ['auto', 'manual'].forEach(m => {
        const btn = document.getElementById(`btn-orch-${m}`);
        if (btn) btn.classList.toggle('active', m === mode);
    });
}

async function setOrchMode(mode) {
    try {
        await fetch(`/api/orchestrator/${mode}`, { method: 'POST' });
        await updateNetwork();
        showNotification(`TXs automáticas: ${mode === 'auto' ? 'activadas' : 'pausadas'}`);
    } catch (e) {
        console.error('Error cambiando modo orquestador:', e);
    }
}

// ──────────────────────────────────────────────────────────
// Utilidades
// ──────────────────────────────────────────────────────────

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function showNotification(msg) {
    const el = document.getElementById('notification');
    if (!el) return;
    el.textContent = msg;
    el.classList.remove('hidden');
    setTimeout(() => el.classList.add('hidden'), 4000);
}

// ──────────────────────────────────────────────────────────
// Inicialización
// ──────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    updateNetwork();
    setInterval(updateNetwork, 3000);
});
