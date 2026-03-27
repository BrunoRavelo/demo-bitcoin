# Documentación: `dashboard_global/static/global.js`

## Propósito

Lógica frontend del dashboard global. Auto-refresh cada 3 segundos, actualiza la tabla de nodos y los controles del orquestador.

## Loop principal

```javascript
async function updateNetwork() {
    const [network, orch] = await Promise.all([
        fetch('/api/network').then(r => r.json()),
        fetch('/api/orchestrator').then(r => r.json()),
    ]);
    updateSeedBadge(network.seed_online);
    updateSummary(network.summary);
    updateNodesTable(network.nodes, network.summary.max_height);
    updateOrchestrator(orch);
    updateRefreshBadge();
}

setInterval(updateNetwork, 3000);
```

**¿Por qué 3s y no 2s?** El dashboard global hace N+2 requests por ciclo (N nodos + seed + orquestador). Con 30 nodos, 3s reduce la carga en la red del laboratorio.

## Funciones

| Función | Descripción |
|---------|-------------|
| `updateSeedBadge(online)` | Verde si seed online, rojo si no |
| `updateRefreshBadge()` | Muestra hora del último refresh |
| `updateSummary(s)` | Actualiza las 8 tarjetas de resumen |
| `updateNodesTable(nodes, maxHeight)` | Renderiza tabla dinámica de nodos |
| `updateOrchestrator(orch)` | Actualiza stats y botones del orquestador |
| `setOrchMode(mode)` | POST /api/orchestrator/auto o /manual |
| `setText(id, value)` | Helper — actualiza textContent de elemento |
| `showNotification(msg)` | Notificación temporal 4s |

## `updateNodesTable`

Renderiza cada fila con clase CSS según estado:

```javascript
const rowClass = !online ? 'row-offline'
               : !inSync ? 'row-desynced'
               : '';

const syncIcon = !online ? '⬛'
               : inSync  ? '✅'
               : lag <= 5 ? '⚠️'
               : '🔴';
```

## `updateSummary` — notificación de nuevo bloque

```javascript
if (lastMaxHeight > 0 && s.max_height > lastMaxHeight) {
    showNotification(`¡Nuevo bloque #${s.max_height - 1} confirmado en la red!`);
}
lastMaxHeight = s.max_height;
```

## `setOrchMode`

```javascript
async function setOrchMode(mode) {
    await fetch(`/api/orchestrator/${mode}`, { method: 'POST' });
    await updateNetwork();  // Refresh inmediato
    showNotification(`TXs automáticas: ${mode === 'auto' ? 'activadas' : 'pausadas'}`);
}
```

---

*Documento: `DOC_dashboard_global_js.md` — Demo Blockchain*
