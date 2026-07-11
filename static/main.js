// static/main.js
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

let entities = [];
let selectedEntity = null;
let hoveredEntity = null;
const DPR = window.devicePixelRatio || 1;

let mouseX = 0;
let mouseY = 0;

// --- Zoom / Pan state ---
let zoom = 1.0;
let panX = 0;
let panY = 0;
let isPanning = false;
let panStartX = 0;
let panStartY = 0;
let panOffsetX = 0;
let panOffsetY = 0;

// --- Metaphor state ---
let currentMetaphor = 'city';
let availableMetaphors = [];
let metaphorRenderers = {};

// --- State colors ---
const COLORS = {
    healthy: '#4ade80',
    running: '#60a5fa',
    idle: '#94a3b8',
    warning: '#fbbf24',
    degraded: '#f97316',
    critical: '#ef4444',
    stopped: '#374151',
    pending: '#a78bfa',
    scaling: '#06b6d4',
    unknown: '#6b7280',
};

// ============================================================
// Metaphor Renderer Registry
// ============================================================

/**
 * Each metaphor renderer is an object with:
 *   - computeLayout(entities, width, height) -> { [entityId]: {x, y, w, h} }
 *   - render(ctx, entities, layout, width, height, colors) -> void
 */

metaphorRenderers.city = {
    computeLayout(entities, W, H) {
        const layout = {};
        const byId = {};
        entities.forEach(e => byId[e.id] = e);
        const roots = entities.filter(e => !e.parent);

        const districtW = W / Math.max(roots.length, 1);
        roots.forEach((root, di) => {
            const dx = di * districtW;
            layout[root.id] = { x: dx, y: 0, w: districtW, h: H };

            const children = (root.children || []).map(id => byId[id]).filter(Boolean);
            const blockH = H / Math.max(children.length, 1);
            children.forEach((child, bi) => {
                const by = bi * blockH;
                layout[child.id] = { x: dx + 10, y: by + 10, w: districtW - 20, h: blockH - 20 };

                const grandchildren = (child.children || []).map(id => byId[id]).filter(Boolean);
                if (!grandchildren.length) return;
                const buildingW = (districtW - 40) / Math.max(grandchildren.length, 1);
                grandchildren.forEach((gc, gi) => {
                    const bx = dx + 20 + gi * buildingW;
                    const cpu = (gc.metrics || {}).cpu || 50;
                    const maxBH = blockH - 40;
                    const bh = Math.max(20, maxBH * (cpu / 100));
                    layout[gc.id] = { x: bx, y: by + 10 + (maxBH - bh), w: buildingW - 8, h: bh };
                });
            });
        });
        return layout;
    },

    render(ctx, entities, layout, W, H, COLORS) {
        // Background
        ctx.fillStyle = '#0a0a1a';
        ctx.fillRect(0, 0, W, H);

        // Ground
        ctx.fillStyle = '#1a1a2e';
        ctx.fillRect(0, H - 40, W, 40);

        entities.forEach(entity => {
            const pos = layout[entity.id];
            if (!pos) return;
            const color = COLORS[entity.state] || COLORS.unknown;

            if (entity.type === 'cluster') {
                ctx.strokeStyle = color;
                ctx.lineWidth = 2;
                ctx.strokeRect(pos.x + 2, pos.y + 2, pos.w - 4, pos.h - 4);
                ctx.fillStyle = color;
                ctx.font = 'bold 14px system-ui, sans-serif';
                ctx.fillText(entity.name, pos.x + 8, pos.y + 20);
            } else if (entity.type === 'node') {
                ctx.fillStyle = '#111827';
                ctx.fillRect(pos.x, pos.y, pos.w, pos.h);
                ctx.strokeStyle = '#374151';
                ctx.lineWidth = 1;
                ctx.strokeRect(pos.x, pos.y, pos.w, pos.h);
                ctx.fillStyle = '#9ca3af';
                ctx.font = '11px system-ui, sans-serif';
                ctx.fillText(entity.name, pos.x + 6, pos.y + 16);
            } else if (entity.type === 'service') {
                // Building
                ctx.fillStyle = color;
                ctx.fillRect(pos.x, pos.y, pos.w, pos.h);
                ctx.strokeStyle = '#000';
                ctx.lineWidth = 1;
                ctx.strokeRect(pos.x, pos.y, pos.w, pos.h);

                // Windows
                if (pos.h > 30 && pos.w > 15) {
                    for (let wy = pos.y + 8; wy < pos.y + pos.h - 8; wy += 12) {
                        for (let wx = pos.x + 4; wx < pos.x + pos.w - 4; wx += 10) {
                            if (entity.state === 'healthy' || entity.state === 'running') {
                                ctx.fillStyle = '#fbbf24';
                            } else if (entity.state === 'warning') {
                                ctx.fillStyle = '#f97316';
                            } else {
                                ctx.fillStyle = '#1f2937';
                            }
                            ctx.fillRect(wx, wy, 4, 4);
                        }
                    }
                }

                // Label
                if (pos.w > 30) {
                    ctx.fillStyle = '#fff';
                    ctx.font = '9px system-ui, sans-serif';
                    const label = entity.name.slice(0, 12);
                    ctx.fillText(label, pos.x + 2, pos.y + pos.h + 12);
                }
            } else {
                // Generic fallback: colored rectangle
                ctx.fillStyle = color;
                ctx.globalAlpha = 0.6;
                ctx.fillRect(pos.x, pos.y, pos.w, pos.h);
                ctx.globalAlpha = 1.0;
                ctx.strokeStyle = '#374151';
                ctx.lineWidth = 1;
                ctx.strokeRect(pos.x, pos.y, pos.w, pos.h);
                ctx.fillStyle = '#e5e7eb';
                ctx.font = '10px system-ui, sans-serif';
                ctx.fillText(entity.name, pos.x + 4, pos.y + 14);
            }
        });
    }
};

// Solar System metaphor (placeholder renderer)
metaphorRenderers.solar = {
    computeLayout(entities, W, H) {
        const layout = {};
        const cx = W / 2;
        const cy = H / 2;
        const roots = entities.filter(e => !e.parent);
        const byId = {};
        entities.forEach(e => byId[e.id] = e);

        roots.forEach((root, i) => {
            const orbitR = 60 + i * 70;
            layout[root.id] = { x: cx - 20, y: cy - orbitR - 20, w: 40, h: 40, cx: cx, cy: cy, r: orbitR };

            const children = (root.children || []).map(id => byId[id]).filter(Boolean);
            children.forEach((child, ci) => {
                const angle = (ci / Math.max(children.length, 1)) * Math.PI * 2;
                const px = cx + Math.cos(angle) * orbitR;
                const py = cy + Math.sin(angle) * orbitR;
                const size = 24;
                layout[child.id] = { x: px - size/2, y: py - size/2, w: size, h: size };

                const grandchildren = (child.children || []).map(id => byId[id]).filter(Boolean);
                grandchildren.forEach((gc, gi) => {
                    const subAngle = angle + (gi / Math.max(grandchildren.length, 1)) * Math.PI * 0.5;
                    const subR = 30;
                    const sx = px + Math.cos(subAngle) * subR;
                    const sy = py + Math.sin(subAngle) * subR;
                    const ss = 14;
                    layout[gc.id] = { x: sx - ss/2, y: sy - ss/2, w: ss, h: ss };
                });
            });
        });
        return layout;
    },

    render(ctx, entities, layout, W, H, COLORS) {
        ctx.fillStyle = '#0a0a1a';
        ctx.fillRect(0, 0, W, H);

        // Draw orbits
        const cx = W / 2;
        const cy = H / 2;
        const roots = entities.filter(e => !e.parent);
        roots.forEach((root, i) => {
            const orbitR = 60 + i * 70;
            ctx.beginPath();
            ctx.arc(cx, cy, orbitR, 0, Math.PI * 2);
            ctx.strokeStyle = '#1f2937';
            ctx.lineWidth = 1;
            ctx.stroke();
        });

        // Draw sun
        ctx.beginPath();
        ctx.arc(cx, cy, 20, 0, Math.PI * 2);
        ctx.fillStyle = '#fbbf24';
        ctx.fill();

        // Draw entities as planets
        entities.forEach(entity => {
            const pos = layout[entity.id];
            if (!pos) return;
            const color = COLORS[entity.state] || COLORS.unknown;
            const cx2 = pos.x + pos.w / 2;
            const cy2 = pos.y + pos.h / 2;
            const r = pos.w / 2;

            ctx.beginPath();
            ctx.arc(cx2, cy2, r, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();
            ctx.strokeStyle = '#000';
            ctx.lineWidth = 1;
            ctx.stroke();

            // Label
            ctx.fillStyle = '#e5e7eb';
            ctx.font = '9px system-ui, sans-serif';
            const label = entity.name.slice(0, 10);
            ctx.fillText(label, pos.x, pos.y + pos.h + 12);
        });
    }
};

// Forest metaphor (placeholder renderer)
metaphorRenderers.forest = {
    computeLayout(entities, W, H) {
        const layout = {};
        const byId = {};
        entities.forEach(e => byId[e.id] = e);
        const roots = entities.filter(e => !e.parent);

        const spacing = W / Math.max(roots.length, 1);
        roots.forEach((root, i) => {
            const tx = i * spacing + spacing / 2;
            const trunkH = H * 0.6;
            layout[root.id] = { x: tx - 15, y: H - trunkH - 40, w: 30, h: trunkH };

            const children = (root.children || []).map(id => byId[id]).filter(Boolean);
            const branchSpread = spacing * 0.8;
            children.forEach((child, ci) => {
                const angle = -Math.PI/2 + (ci - (children.length-1)/2) * 0.5;
                const branchLen = 60;
                const bx = tx + Math.cos(angle) * branchLen;
                const by = (H - trunkH - 40) + Math.sin(angle) * branchLen;
                const leafSize = 30;
                layout[child.id] = { x: bx - leafSize/2, y: by - leafSize/2, w: leafSize, h: leafSize };

                const grandchildren = (child.children || []).map(id => byId[id]).filter(Boolean);
                grandchildren.forEach((gc, gi) => {
                    const subAngle = angle + (gi - (grandchildren.length-1)/2) * 0.3;
                    const subLen = 35;
                    const sx = bx + Math.cos(subAngle) * subLen;
                    const sy = by + Math.sin(subAngle) * subLen;
                    const fruitSize = 12;
                    layout[gc.id] = { x: sx - fruitSize/2, y: sy - fruitSize/2, w: fruitSize, h: fruitSize };
                });
            });
        });
        return layout;
    },

    render(ctx, entities, layout, W, H, COLORS) {
        ctx.fillStyle = '#0a0a1a';
        ctx.fillRect(0, 0, W, H);

        // Ground
        ctx.fillStyle = '#1a2e1a';
        ctx.fillRect(0, H - 40, W, 40);

        const byId = {};
        entities.forEach(e => byId[e.id] = e);

        entities.forEach(entity => {
            const pos = layout[entity.id];
            if (!pos) return;
            const color = COLORS[entity.state] || COLORS.unknown;

            if (entity.type === 'cluster') {
                // Tree trunk
                ctx.fillStyle = '#78350f';
                ctx.fillRect(pos.x, pos.y, pos.w, pos.h);
                ctx.fillStyle = color;
                ctx.font = 'bold 11px system-ui, sans-serif';
                ctx.fillText(entity.name, pos.x - 20, pos.y - 8);
            } else if (entity.type === 'node') {
                // Branch / canopy
                ctx.beginPath();
                ctx.arc(pos.x + pos.w/2, pos.y + pos.h/2, pos.w/2, 0, Math.PI * 2);
                ctx.fillStyle = color;
                ctx.globalAlpha = 0.7;
                ctx.fill();
                ctx.globalAlpha = 1.0;
                ctx.fillStyle = '#e5e7eb';
                ctx.font = '9px system-ui, sans-serif';
                ctx.fillText(entity.name.slice(0, 10), pos.x - 5, pos.y - 4);
            } else {
                // Fruit / leaf
                ctx.beginPath();
                ctx.arc(pos.x + pos.w/2, pos.y + pos.h/2, pos.w/2, 0, Math.PI * 2);
                ctx.fillStyle = color;
                ctx.fill();
            }
        });
    }
};

// ============================================================
// Canvas sizing
// ============================================================
function resize() {
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * DPR;
    canvas.height = rect.height * DPR;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    render();
}
window.addEventListener('resize', resize);

// ============================================================
// WebSocket
// ============================================================
let ws;
function connect() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${location.host}/ws/entities`);
    ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === 'entities') {
            entities = data.entities || [];
            render();
            updateStats();
        }
    };
    ws.onclose = () => setTimeout(connect, 3000);
    ws.onerror = () => ws.close();
}

// ============================================================
// Fetch metaphors from API
// ============================================================
async function fetchMetaphors() {
    try {
        const res = await fetch('/api/metaphors');
        const data = await res.json();
        availableMetaphors = data.metaphors || [];
        currentMetaphor = data.default || 'city';
        buildToolbar();
    } catch (e) {
        console.error('Failed to fetch metaphors:', e);
        availableMetaphors = [{ id: 'city', name: 'City', description: 'Default' }];
        buildToolbar();
    }
}

// ============================================================
// Render pipeline
// ============================================================
let currentLayout = {};

function computeLayout() {
    const W = canvas.width / DPR;
    const H = canvas.height / DPR;
    const renderer = metaphorRenderers[currentMetaphor] || metaphorRenderers.city;
    currentLayout = renderer.computeLayout(entities, W, H);
}

function render() {
    const W = canvas.width / DPR;
    const H = canvas.height / DPR;

    ctx.save();
    ctx.setTransform(DPR * zoom, 0, 0, DPR * zoom, DPR * panX, DPR * panY);

    computeLayout();

    const renderer = metaphorRenderers[currentMetaphor] || metaphorRenderers.city;
    renderer.render(ctx, entities, currentLayout, W, H, COLORS);

    // Selection highlight
    if (selectedEntity) {
        const pos = currentLayout[selectedEntity.id];
        if (pos) {
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2 / zoom;
            ctx.strokeRect(pos.x - 2, pos.y - 2, pos.w + 4, pos.h + 4);
        }
    }

    ctx.restore();

    // Tooltip (drawn in screen space, not zoomed)
    if (hoveredEntity) {
        drawTooltip(hoveredEntity, W, H);
    }
}

function drawTooltip(entity, W, H) {
    const lines = [
        `${entity.name} (${entity.type})`,
        `State: ${entity.state}`,
    ];
    const m = entity.metrics || {};
    if (m.cpu !== undefined) lines.push(`CPU: ${m.cpu}%`);
    if (m.mem !== undefined) lines.push(`Mem: ${m.mem}%`);
    if (m.cpu_pct !== undefined) lines.push(`CPU: ${m.cpu_pct}%`);
    if (m.mem_pct !== undefined) lines.push(`Mem: ${m.mem_pct}%`);
    if (m.req_per_sec !== undefined) lines.push(`RPS: ${m.req_per_sec}`);
    if (m.error_rate !== undefined) lines.push(`Errors: ${(m.error_rate * 100).toFixed(1)}%`);
    if (m.count !== undefined) lines.push(`Count: ${m.count}`);
    if (m.uptime_hrs !== undefined) lines.push(`Uptime: ${m.uptime_hrs}h`);

    ctx.font = '12px system-ui, sans-serif';
    const textW = Math.max(...lines.map(l => ctx.measureText(l).width)) + 16;
    const textH = lines.length * 18 + 12;
    const tx = Math.min(mouseX + 12, W - textW - 8);
    const ty = Math.min(mouseY + 12, H - textH - 8);

    ctx.fillStyle = 'rgba(0,0,0,0.85)';
    ctx.fillRect(tx, ty, textW, textH);
    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 1;
    ctx.strokeRect(tx, ty, textW, textH);

    ctx.fillStyle = '#fff';
    lines.forEach((line, i) => {
        ctx.fillText(line, tx + 8, ty + 20 + i * 18);
    });
}

// ============================================================
// Mouse interaction (with zoom/pan transform)
// ============================================================
function screenToWorld(sx, sy) {
    return {
        x: (sx - panX) / zoom,
        y: (sy - panY) / zoom,
    };
}

canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    mouseX = e.clientX - rect.left;
    mouseY = e.clientY - rect.top;

    if (isPanning) {
        panX = panOffsetX + (mouseX - panStartX);
        panY = panOffsetY + (mouseY - panStartY);
        render();
        return;
    }

    const world = screenToWorld(mouseX, mouseY);
    let prevHover = hoveredEntity;
    hoveredEntity = null;
    for (const entity of entities) {
        const pos = currentLayout[entity.id];
        if (!pos) continue;
        if (world.x >= pos.x && world.x <= pos.x + pos.w &&
            world.y >= pos.y && world.y <= pos.y + pos.h) {
            hoveredEntity = entity;
            break;
        }
    }
    canvas.style.cursor = hoveredEntity ? 'pointer' : 'default';
    if (hoveredEntity !== prevHover) {
        render();
    }
});

canvas.addEventListener('mousedown', (e) => {
    if (e.button === 1 || (e.button === 0 && e.shiftKey)) {
        // Middle click or shift+click = pan
        isPanning = true;
        panStartX = mouseX;
        panStartY = mouseY;
        panOffsetX = panX;
        panOffsetY = panY;
        canvas.style.cursor = 'grabbing';
        e.preventDefault();
    }
});

canvas.addEventListener('mouseup', (e) => {
    if (isPanning) {
        isPanning = false;
        canvas.style.cursor = hoveredEntity ? 'pointer' : 'default';
    }
});

canvas.addEventListener('click', (e) => {
    if (isPanning) return;
    if (hoveredEntity) {
        selectedEntity = hoveredEntity;
        render();
        showDetailPanel(hoveredEntity);
    } else {
        selectedEntity = null;
        hideDetailPanel();
        render();
    }
});

canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.max(0.2, Math.min(5.0, zoom * delta));

    // Zoom towards cursor
    const rect = canvas.getBoundingClientRect();
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;
    panX = cx - (cx - panX) * (newZoom / zoom);
    panY = cy - (cy - panY) * (newZoom / zoom);
    zoom = newZoom;
    render();
}, { passive: false });

// ============================================================
// Zoom controls
// ============================================================
document.getElementById('zoom-in').addEventListener('click', () => {
    zoom = Math.min(5.0, zoom * 1.25);
    render();
});

document.getElementById('zoom-out').addEventListener('click', () => {
    zoom = Math.max(0.2, zoom * 0.8);
    render();
});

document.getElementById('zoom-reset').addEventListener('click', () => {
    zoom = 1.0;
    panX = 0;
    panY = 0;
    render();
});

// ============================================================
// Detail panel
// ============================================================
function showDetailPanel(entity) {
    const panel = document.getElementById('detail-panel');
    const title = document.getElementById('detail-title');
    const body = document.getElementById('detail-body');

    title.textContent = entity.name;

    const stateColor = COLORS[entity.state] || COLORS.unknown;
    let html = '';

    // State badge
    html += `<div class="detail-row">
        <span class="detail-key">State</span>
        <span class="detail-state" style="background:${stateColor};color:#000;">${entity.state}</span>
    </div>`;

    // Type
    html += `<div class="detail-row">
        <span class="detail-key">Type</span>
        <span class="detail-value">${entity.type}</span>
    </div>`;

    // ID
    html += `<div class="detail-row">
        <span class="detail-key">ID</span>
        <span class="detail-value" style="font-family:monospace;font-size:10px;">${entity.id}</span>
    </div>`;

    // Source
    if (entity.source) {
        html += `<div class="detail-row">
            <span class="detail-key">Source</span>
            <span class="detail-value">${entity.source}</span>
        </div>`;
    }

    // Parent
    if (entity.parent) {
        html += `<div class="detail-row">
            <span class="detail-key">Parent</span>
            <span class="detail-value">${entity.parent}</span>
        </div>`;
    }

    // Children
    if (entity.children && entity.children.length > 0) {
        html += `<div class="detail-row">
            <span class="detail-key">Children</span>
            <span class="detail-value">${entity.children.length}</span>
        </div>`;
    }

    // Metrics
    const m = entity.metrics || {};
    const metricKeys = Object.keys(m);
    if (metricKeys.length > 0) {
        html += `<div style="margin-top:8px;padding-top:8px;border-top:1px solid #374151;">
            <div style="font-weight:bold;font-size:11px;color:#9ca3af;margin-bottom:4px;">METRICS</div>`;
        metricKeys.forEach(key => {
            let val = m[key];
            if (typeof val === 'number' && !Number.isInteger(val)) {
                val = val.toFixed(2);
            }
            if (key === 'error_rate' && typeof m[key] === 'number') {
                val = (m[key] * 100).toFixed(1) + '%';
            }
            html += `<div class="detail-row">
                <span class="detail-key">${key}</span>
                <span class="detail-value">${val}</span>
            </div>`;
        });
        html += `</div>`;
    }

    // Labels
    const labels = entity.labels || {};
    if (Object.keys(labels).length > 0) {
        html += `<div style="margin-top:8px;padding-top:8px;border-top:1px solid #374151;">
            <div style="font-weight:bold;font-size:11px;color:#9ca3af;margin-bottom:4px;">LABELS</div>`;
        Object.entries(labels).forEach(([k, v]) => {
            html += `<div class="detail-row">
                <span class="detail-key">${k}</span>
                <span class="detail-value">${v}</span>
            </div>`;
        });
        html += `</div>`;
    }

    body.innerHTML = html;
    panel.classList.remove('hidden');
}

function hideDetailPanel() {
    document.getElementById('detail-panel').classList.add('hidden');
}

document.getElementById('detail-close').addEventListener('click', () => {
    selectedEntity = null;
    hideDetailPanel();
    render();
});

// ============================================================
// Toolbar with metaphor selector
// ============================================================
function buildToolbar() {
    const toolbar = document.getElementById('toolbar');

    const metaphorOptions = availableMetaphors.map(m =>
        `<option value="${m.id}" ${m.id === currentMetaphor ? 'selected' : ''}>${m.name}</option>`
    ).join('');

    const currentMeta = availableMetaphors.find(m => m.id === currentMetaphor);
    const desc = currentMeta ? currentMeta.description : '';

    toolbar.innerHTML = `
        <div style="background:#111827;padding:12px;border-radius:8px;border:1px solid #374151;min-width:200px;">
            <div style="font-weight:bold;margin-bottom:4px;">&#127758; Metaphors</div>
            <div style="font-size:11px;color:#6b7280;margin-bottom:8px;">${desc}</div>
            <label style="font-size:11px;color:#9ca3af;display:block;margin-bottom:2px;">Renderer</label>
            <select id="metaphor-select">${metaphorOptions}</select>
            <div id="stats" style="margin-top:8px;font-size:11px;color:#6b7280;"></div>
            <div style="margin-top:6px;font-size:10px;color:#4b5563;">
                Scroll to zoom · Shift+drag to pan
            </div>
        </div>
    `;

    document.getElementById('metaphor-select').addEventListener('change', (e) => {
        currentMetaphor = e.target.value;
        // Update description
        const meta = availableMetaphors.find(m => m.id === currentMetaphor);
        const descEl = toolbar.querySelector('div[style*="font-size:11px;color:#6b7280"]');
        if (descEl && meta) descEl.textContent = meta.description;
        render();
    });
}

function updateStats() {
    const el = document.getElementById('stats');
    if (!el) return;
    const states = {};
    entities.forEach(e => {
        states[e.state] = (states[e.state] || 0) + 1;
    });
    el.innerHTML = Object.entries(states)
        .map(([s, n]) => `<span style="color:${COLORS[s] || '#6b7280'}">${s}: ${n}</span>`)
        .join(' &middot; ');
}

// ============================================================
// Init
// ============================================================
resize();
fetchMetaphors();
connect();
