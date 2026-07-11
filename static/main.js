// static/main.js
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

let entities = [];
let layout = {};
let selectedEntity = null;
let hoveredEntity = null;
const DPR = window.devicePixelRatio || 1;

let mouseX = 0;
let mouseY = 0;

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

// --- Canvas sizing ---
function resize() {
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * DPR;
    canvas.height = rect.height * DPR;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    computeLayout();
    render();
}
window.addEventListener('resize', resize);

// --- WebSocket ---
let ws;
function connect() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${location.host}/ws/entities`);
    ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === 'entities') {
            entities = data.entities || [];
            computeLayout();
            render();
            updateStats();
        }
    };
    ws.onclose = () => setTimeout(connect, 3000);
    ws.onerror = () => ws.close();
}

// --- Layout engine (City metaphor) ---
function computeLayout() {
    layout = {};
    const W = canvas.width / DPR;
    const H = canvas.height / DPR;
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
}

// --- Render ---
function render() {
    const W = canvas.width / DPR;
    const H = canvas.height / DPR;
    ctx.clearRect(0, 0, W, H);

    // Background
    ctx.fillStyle = '#0a0a1a';
    ctx.fillRect(0, 0, W, H);

    // Ground
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, H - 40, W, 40);

    const byId = {};
    entities.forEach(e => byId[e.id] = e);

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
        }
    });

    // Selection highlight
    if (selectedEntity) {
        const pos = layout[selectedEntity.id];
        if (pos) {
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2;
            ctx.strokeRect(pos.x - 2, pos.y - 2, pos.w + 4, pos.h + 4);
        }
    }

    // Tooltip
    if (hoveredEntity) {
        const lines = [
            `${hoveredEntity.name} (${hoveredEntity.type})`,
            `State: ${hoveredEntity.state}`,
        ];
        const m = hoveredEntity.metrics || {};
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
}

// --- Mouse interaction ---
canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    mouseX = e.clientX - rect.left;
    mouseY = e.clientY - rect.top;

    let prevHover = hoveredEntity;
    hoveredEntity = null;
    for (const entity of entities) {
        const pos = layout[entity.id];
        if (!pos) continue;
        if (mouseX >= pos.x && mouseX <= pos.x + pos.w &&
            mouseY >= pos.y && mouseY <= pos.y + pos.h) {
            hoveredEntity = entity;
            break;
        }
    }
    canvas.style.cursor = hoveredEntity ? 'pointer' : 'default';
    if (hoveredEntity !== prevHover) {
        render();
    }
});

canvas.addEventListener('click', () => {
    if (hoveredEntity) {
        selectedEntity = hoveredEntity;
        render();
        showDetailPanel(hoveredEntity);
    } else {
        selectedEntity = null;
        render();
    }
});

function showDetailPanel(entity) {
    console.log('Selected:', entity);
}

// --- Toolbar ---
function createToolbar() {
    const toolbar = document.getElementById('toolbar');
    toolbar.innerHTML = `
        <div style=\"background:#111827;padding:12px;border-radius:8px;border:1px solid #374151;min-width:180px;\">
            <div style=\"font-weight:bold;margin-bottom:8px;\">&#127751; City View</div>
            <div style=\"font-size:12px;color:#9ca3af;\">
                Click buildings to inspect<br>
                Real-time updates via WebSocket
            </div>
            <div id=\"stats\" style=\"margin-top:8px;font-size:11px;color:#6b7280;\"></div>
        </div>
    `;
}

function updateStats() {
    const el = document.getElementById('stats');
    if (!el) return;
    const states = {};
    entities.forEach(e => {
        states[e.state] = (states[e.state] || 0) + 1;
    });
    el.innerHTML = Object.entries(states)
        .map(([s, n]) => `<span style=\"color:${COLORS[s] || '#6b7280'}\">${s}: ${n}</span>`)
        .join(' &middot; ');
}

// --- Init ---
resize();
connect();
createToolbar();
