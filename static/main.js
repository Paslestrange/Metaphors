// static/main.js
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const minimapCanvas = document.getElementById('minimap');
const minimapCtx = minimapCanvas.getContext('2d');

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
let currentMetaphor = localStorage.getItem('metaphor') || 'city';
let availableMetaphors = [];
let metaphorRenderers = {};
let isTransitioning = false;

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
        ctx.fillStyle = '#0a0a1a';
        ctx.fillRect(0, 0, W, H);
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
                ctx.fillStyle = color;
                ctx.fillRect(pos.x, pos.y, pos.w, pos.h);
                ctx.strokeStyle = '#000';
                ctx.lineWidth = 1;
                ctx.strokeRect(pos.x, pos.y, pos.w, pos.h);

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

                if (pos.w > 30) {
                    ctx.fillStyle = '#fff';
                    ctx.font = '9px system-ui, sans-serif';
                    const label = entity.name.slice(0, 12);
                    ctx.fillText(label, pos.x + 2, pos.y + pos.h + 12);
                }
            } else {
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

// Solar System metaphor
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
            layout[root.id] = { x: cx - 20, y: cy - orbitR - 20, w: 40, h: 40 };

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

        ctx.beginPath();
        ctx.arc(cx, cy, 20, 0, Math.PI * 2);
        ctx.fillStyle = '#fbbf24';
        ctx.fill();

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

            ctx.fillStyle = '#e5e7eb';
            ctx.font = '9px system-ui, sans-serif';
            const label = entity.name.slice(0, 10);
            ctx.fillText(label, pos.x, pos.y + pos.h + 12);
        });
    }
};

// Forest metaphor
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
        ctx.fillStyle = '#1a2e1a';
        ctx.fillRect(0, H - 40, W, 40);

        entities.forEach(entity => {
            const pos = layout[entity.id];
            if (!pos) return;
            const color = COLORS[entity.state] || COLORS.unknown;

            if (entity.type === 'cluster') {
                ctx.fillStyle = '#78350f';
                ctx.fillRect(pos.x, pos.y, pos.w, pos.h);
                ctx.fillStyle = color;
                ctx.font = 'bold 11px system-ui, sans-serif';
                ctx.fillText(entity.name, pos.x - 20, pos.y - 8);
            } else if (entity.type === 'node') {
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

    // Minimap sizing
    const mmRect = minimapCanvas.getBoundingClientRect();
    minimapCanvas.width = mmRect.width * DPR;
    minimapCanvas.height = mmRect.height * DPR;
    minimapCtx.setTransform(DPR, 0, 0, DPR, 0, 0);

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
        // Restore from localStorage or use server default
        const saved = localStorage.getItem('metaphor');
        if (saved && availableMetaphors.some(m => m.id === saved)) {
            currentMetaphor = saved;
        } else {
            currentMetaphor = data.default || data.active || 'city';
        }
        buildToolbar();
    } catch (e) {
        console.error('Failed to fetch metaphors:', e);
        availableMetaphors = [
            { id: 'city', name: 'City', description: 'Infrastructure as a cityscape' },
            { id: 'solar', name: 'Solar', description: 'Systems as orbiting celestial bodies' },
            { id: 'forest', name: 'Forest', description: 'Services as a living forest ecosystem' },
        ];
        buildToolbar();
    }
}

// ============================================================
// Metaphor switching with fade transition
// ============================================================
function switchMetaphor(newMetaphor) {
    if (newMetaphor === currentMetaphor || isTransitioning) return;
    if (!metaphorRenderers[newMetaphor]) return;

    isTransitioning = true;
    const overlay = document.getElementById('fade-overlay');

    // Fade out
    overlay.classList.add('active');

    setTimeout(() => {
        currentMetaphor = newMetaphor;
        localStorage.setItem('metaphor', newMetaphor);

        // Update toolbar description
        const meta = availableMetaphors.find(m => m.id === newMetaphor);
        const descEl = document.querySelector('#toolbar div[style*="font-size:11px;color:#6b7280"]');
        if (descEl && meta) descEl.textContent = meta.description;

        // Update select
        const select = document.getElementById('metaphor-select');
        if (select) select.value = newMetaphor;

        render();

        // Fade in
        setTimeout(() => {
            overlay.classList.remove('active');
            isTransitioning = false;
        }, 50);
    }, 250);
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

    // Render minimap
    renderMinimap(W, H);
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
// Minimap
// ============================================================
function renderMinimap(mainW, mainH) {
    const mmW = minimapCanvas.width / DPR;
    const mmH = minimapCanvas.height / DPR;

    minimapCtx.clearRect(0, 0, mmW, mmH);
    minimapCtx.fillStyle = '#111827';
    minimapCtx.fillRect(0, 0, mmW, mmH);

    if (!entities.length || !Object.keys(currentLayout).length) return;

    // Compute bounding box of all entities in world space
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    entities.forEach(e => {
        const pos = currentLayout[e.id];
        if (!pos) return;
        minX = Math.min(minX, pos.x);
        minY = Math.min(minY, pos.y);
        maxX = Math.max(maxX, pos.x + pos.w);
        maxY = Math.max(maxY, pos.y + pos.h);
    });

    if (minX === Infinity) return;

    const worldW = maxX - minX || 1;
    const worldH = maxY - minY || 1;
    const padding = 8;
    const scaleX = (mmW - padding * 2) / worldW;
    const scaleY = (mmH - padding * 2) / worldH;
    const scale = Math.min(scaleX, scaleY);

    const offsetX = padding + ((mmW - padding * 2) - worldW * scale) / 2;
    const offsetY = padding + ((mmH - padding * 2) - worldH * scale) / 2;

    // Draw entities as colored dots
    entities.forEach(e => {
        const pos = currentLayout[e.id];
        if (!pos) return;
        const color = COLORS[e.state] || COLORS.unknown;
        const x = offsetX + (pos.x - minX) * scale;
        const y = offsetY + (pos.y - minY) * scale;
        const w = Math.max(2, pos.w * scale);
        const h = Math.max(2, pos.h * scale);
        minimapCtx.fillStyle = color;
        minimapCtx.globalAlpha = 0.7;
        minimapCtx.fillRect(x, y, w, h);
    });
    minimapCtx.globalAlpha = 1.0;

    // Draw viewport rectangle
    const vpLeft = (-panX / zoom);
    const vpTop = (-panY / zoom);
    const vpRight = vpLeft + (mainW / zoom);
    const vpBottom = vpTop + (mainH / zoom);

    const vpX = offsetX + (vpLeft - minX) * scale;
    const vpY = offsetY + (vpTop - minY) * scale;
    const vpW = (vpRight - vpLeft) * scale;
    const vpH = (vpBottom - vpTop) * scale;

    minimapCtx.strokeStyle = '#60a5fa';
    minimapCtx.lineWidth = 1.5;
    minimapCtx.strokeRect(vpX, vpY, vpW, vpH);
}

// Minimap click to navigate
minimapCanvas.addEventListener('click', (e) => {
    const mmRect = minimapCanvas.getBoundingClientRect();
    const mx = e.clientX - mmRect.left;
    const my = e.clientY - mmRect.top;
    const mmW = minimapCanvas.width / DPR;
    const mmH = minimapCanvas.height / DPR;

    if (!entities.length || !Object.keys(currentLayout).length) return;

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    entities.forEach(ent => {
        const pos = currentLayout[ent.id];
        if (!pos) return;
        minX = Math.min(minX, pos.x);
        minY = Math.min(minY, pos.y);
        maxX = Math.max(maxX, pos.x + pos.w);
        maxY = Math.max(maxY, pos.y + pos.h);
    });
    if (minX === Infinity) return;

    const worldW = maxX - minX || 1;
    const worldH = maxY - minY || 1;
    const padding = 8;
    const scaleX = (mmW - padding * 2) / worldW;
    const scaleY = (mmH - padding * 2) / worldH;
    const scale = Math.min(scaleX, scaleY);
    const offsetX = padding + ((mmW - padding * 2) - worldW * scale) / 2;
    const offsetY = padding + ((mmH - padding * 2) - worldH * scale) / 2;

    // Convert minimap click to world coordinates
    const worldX = minX + (mx - offsetX) / scale;
    const worldY = minY + (my - offsetY) / scale;

    // Center view on that world position
    const mainW = canvas.width / DPR;
    const mainH = canvas.height / DPR;
    panX = -(worldX * zoom - mainW / 2);
    panY = -(worldY * zoom - mainH / 2);
    render();
});

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
// Keyboard shortcuts
// ============================================================
document.addEventListener('keydown', (e) => {
    // Don't capture when typing in inputs
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;

    const PAN_STEP = 40;

    switch (e.key) {
        // Number keys 1-9: switch metaphor
        case '1': case '2': case '3': case '4': case '5':
        case '6': case '7': case '8': case '9': {
            const idx = parseInt(e.key) - 1;
            if (idx < availableMetaphors.length) {
                switchMetaphor(availableMetaphors[idx].id);
            }
            break;
        }

        // +/- for zoom
        case '+': case '=':
            zoom = Math.min(5.0, zoom * 1.25);
            render();
            break;
        case '-': case '_':
            zoom = Math.max(0.2, zoom * 0.8);
            render();
            break;

        // Arrow keys for pan
        case 'ArrowLeft':
            panX += PAN_STEP;
            render();
            e.preventDefault();
            break;
        case 'ArrowRight':
            panX -= PAN_STEP;
            render();
            e.preventDefault();
            break;
        case 'ArrowUp':
            panY += PAN_STEP;
            render();
            e.preventDefault();
            break;
        case 'ArrowDown':
            panY -= PAN_STEP;
            render();
            e.preventDefault();
            break;

        // Escape: deselect / close detail panel
        case 'Escape':
            selectedEntity = null;
            hideDetailPanel();
            render();
            break;

        // 0 or Home: reset view
        case '0':
        case 'Home':
            zoom = 1.0;
            panX = 0;
            panY = 0;
            render();
            break;
    }
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

    html += `<div class="detail-row">
        <span class="detail-key">State</span>
        <span class="detail-state" style="background:${stateColor};color:#000;">${entity.state}</span>
    </div>`;

    html += `<div class="detail-row">
        <span class="detail-key">Type</span>
        <span class="detail-value">${entity.type}</span>
    </div>`;

    html += `<div class="detail-row">
        <span class="detail-key">ID</span>
        <span class="detail-value" style="font-family:monospace;font-size:10px;">${entity.id}</span>
    </div>`;

    if (entity.source) {
        html += `<div class="detail-row">
            <span class="detail-key">Source</span>
            <span class="detail-value">${entity.source}</span>
        </div>`;
    }

    if (entity.parent) {
        html += `<div class="detail-row">
            <span class="detail-key">Parent</span>
            <span class="detail-value">${entity.parent}</span>
        </div>`;
    }

    if (entity.children && entity.children.length > 0) {
        html += `<div class="detail-row">
            <span class="detail-key">Children</span>
            <span class="detail-value">${entity.children.length}</span>
        </div>`;
    }

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

    const metaphorOptions = availableMetaphors.map((m, i) =>
        `<option value="${m.id}" ${m.id === currentMetaphor ? 'selected' : ''}>${i + 1}. ${m.name}</option>`
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
            <div class="shortcut-hint">
                <kbd>1</kbd>-<kbd>9</kbd> metaphor &middot; <kbd>+</kbd><kbd>-</kbd> zoom &middot; <kbd>&uarr;&darr;&larr;&rarr;</kbd> pan &middot; <kbd>Esc</kbd> deselect
            </div>
        </div>
    `;

    document.getElementById('metaphor-select').addEventListener('change', (e) => {
        switchMetaphor(e.target.value);
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
