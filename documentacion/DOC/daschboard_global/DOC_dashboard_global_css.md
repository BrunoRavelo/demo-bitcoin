# Documentación: `dashboard_global/static/global.css`

## Propósito

Estilos del dashboard global del instructor. Fondo oscuro degradado, tarjetas de resumen con color por categoría, tabla de nodos con filas coloreadas según estado de sincronización.

## Fondo

```css
body {
    background: linear-gradient(135deg, #0a0a1a 0%, #0d1b2a 50%, #1a2940 100%);
}
```

Degradado azul oscuro — diferencia visualmente el dashboard global del dashboard individual (fondo más claro).

## Tarjetas de resumen

```css
.summary-card              { border-top: 4px solid #667eea; } /* default */
.summary-card.green        { border-top-color: #4CAF50; }     /* online, mining */
.summary-card.red          { border-top-color: #f44336; }     /* offline */
.summary-card.blue         { border-top-color: #2196F3; }     /* altura */
.summary-card.orange       { border-top-color: #FF9800; }     /* desfasados */
.summary-card.purple       { border-top-color: #9C27B0; }     /* mempool */
```

El borde superior de color permite identificar la categoría de un vistazo.

## Filas de la tabla

```css
.row-offline  { opacity: 0.5; }           /* nodo sin respuesta */
.row-desynced { background: #fff8e1; }    /* fondo amarillo — desfasado */
```

## Botones de modo del orquestador

```css
.btn-mode.active[id="btn-orch-auto"]   { background: #e8f5e9; border-color: #4CAF50; color: #2e7d32; }
.btn-mode.active[id="btn-orch-manual"] { background: #e3f2fd; border-color: #2196F3; color: #1565c0; }
```

Verde para AUTO, azul para MANUAL — mismo esquema que el dashboard individual para consistencia visual.

## Grid del orquestador

```css
.orch-grid {
    display: grid;
    grid-template-columns: 1fr auto;
}
```

Stats a la izquierda, botones a la derecha. En móvil se apila verticalmente.

## Responsive

```css
@media (max-width: 768px) {
    .orch-grid  { grid-template-columns: 1fr; }
    .orch-stats { grid-template-columns: 1fr; }
    .header     { flex-direction: column; }
}
```

---

*Documento: `DOC_dashboard_global_css.md` — Demo Blockchain*
