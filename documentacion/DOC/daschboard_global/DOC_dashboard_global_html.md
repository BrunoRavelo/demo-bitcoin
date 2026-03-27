# Documentación: `dashboard_global/templates/global.html`

## Propósito

UI del dashboard global del instructor. Muestra estado de toda la red en tiempo real con 8 tarjetas de resumen, control del orquestador y tabla de nodos.

## Secciones

### Header
```html
<div class="header">
    <h1>🌐 Dashboard Global</h1>
    <span id="seed-badge">Seed: ...</span>
    <span id="refresh-badge">Actualizando...</span>
</div>
```
Muestra estado del seed (verde/rojo) y timestamp del último refresh.

### Resumen de la red (8 tarjetas)

| ID | Contenido |
|----|-----------|
| `s-total-nodes` | Nodos totales registrados en seed |
| `s-online` | Nodos respondiendo (verde) |
| `s-offline` | Nodos sin respuesta (rojo) |
| `s-height` | Altura máxima de la red (azul) |
| `s-out-sync` | Nodos desfasados > 2 bloques (naranja) |
| `s-mempool` | TXs pendientes en toda la red (morado) |
| `s-mined` | Total de bloques minados por todos |
| `s-mining-auto` | Nodos actualmente en modo AUTO (verde) |

### Control del orquestador
```html
{% if has_orchestrator %}
<div class="card">
    <!-- stats: modo, txs_sent, txs_failed, success_rate -->
    <!-- botones: [AUTO] [MANUAL] -->
</div>
{% endif %}
```
Solo visible si `main_global.py` tiene un orquestador activo.

### Tabla de nodos

Columnas: Nodo | Estado | Altura | Sync | Balance | Peers | Mempool | Minado | Bloques | Dashboard

**Filas con color:**
- Normal: sin clase
- Desfasado: `.row-desynced` (fondo amarillo)
- Offline: `.row-offline` (opacidad 50%)

**Iconos de sync:**

| Icono | Condición |
|-------|-----------|
| ✅ | `in_sync = True` |
| ⚠️ | `lag ≤ 5` |
| 🔴 | `lag > 5` |
| ⬛ | Offline |

**Link al dashboard individual:**
```html
<a href="http://HOSTNAME:dashboard_port" target="_blank">:8000</a>
```
Usa `window.location.hostname` para funcionar tanto en local como en LAN.

---

*Documento: `DOC_dashboard_global_html.md` — Demo Blockchain*
