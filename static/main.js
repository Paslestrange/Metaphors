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
const ZOOM_MIN = 0.5;
const ZOOM_MAX = 5.0;
const PAN_STEP = 40;
const LERP_SPEED = 0.15; // smoothing factor for animated transitions

let zoom = 1.0;
let panX = 0;
let panY = 0;
let targetZoom = 1.0;
let targetPanX = 0;
let targetPanY = 0;
let animatingView = false; // true when lerping toward targets

let isPanning = false;
let panStartX = 0;
let panStartY = 0;
let panOffsetX = 0;
let panOffsetY = 0;
let mouseDownX = 0;
let mouseDownY = 0;
let hasDragged = false;

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

// ============================================================
// City Metaphor — Full Cyberpunk Visual Overhaul (6-layer)
// ============================================================
const _cityState = {
    stars: [],
    farBuildings: [],
    rain: [],
    particles: [],
    initialized: false,
    lastW: 0,
    lastH: 0,
    startTime: performance.now() / 1000,
};

const CITY_STATE_COLORS = {
    healthy: '#4ade80', running: '#60a5fa', warning: '#fbbf24',
    critical: '#ef4444', stopped: '#374151', idle: '#94a3b8',
    degraded: '#f97316', pending: '#a78bfa', scaling: '#06b6d4', unknown: '#6b7280',
};
const CITY_NEON_GLOW = {
    healthy: '#22ff88', running: '#44aaff', warning: '#ffcc00',
    critical: '#ff2222', stopped: '#555555', idle: '#8899aa',
    degraded: '#ff8800', pending: '#bb99ff', scaling: '#00ddff', unknown: '#778899',
};
const CITY_BG = '#0a0a1a';
const CITY_BG_HORIZON = '#0d0d22';
const CITY_GROUND = '#0d0d22';
const CITY_ROAD = '#111128';
const CITY_WALL = '#1a1a3e';
const CITY_WIN_HEALTHY = '#fbbf24';
const CITY_WIN_WARN = '#f97316';
const CITY_WIN_CRIT = '#ff4444';
const CITY_WIN_OFF = '#1a1a2e';
const CITY_NEON_BG = '#0f0f2a';
const TRAFFIC_COLORS = ['#ff00ff', '#00ffff', '#ffff00', '#ff4488'];

function _cityHash(s) {
    let h = 0;
    for (let i = 0; i < s.length; i++) { h = ((h << 5) - h + s.charCodeAt(i)) | 0; }
    return Math.abs(h);
}

function _cityInitScene(W, H) {
    const rng = (seed) => { let s = seed; return () => { s = (s * 16807 + 0) % 2147483647; return s / 2147483647; }; };
    const r = rng(42);
    // Stars
    _cityState.stars = [];
    for (let i = 0; i < 80; i++) {
        _cityState.stars.push({
            x: r() * W, y: r() * H * 0.35,
            size: 0.5 + r() * 1.5, brightness: 0.3 + r() * 0.6,
            twinkle: 0.5 + r() * 2.5, phase: r() * Math.PI * 2,
        });
    }
    // Far buildings
    _cityState.farBuildings = [];
    const horizonY = H * 0.45;
    let fx = 0;
    for (let i = 0; i < 18; i++) {
        const fw = 15 + r() * 35;
        const fh = 20 + r() * (horizonY * 0.6 - 20);
        const wins = [];
        const nc = Math.max(1, Math.floor(fw / 6));
        const nr = Math.max(1, Math.floor(fh / 8));
        for (let row = 0; row < nr; row++) {
            for (let col = 0; col < nc; col++) {
                if (r() < 0.3) {
                    wins.push({ x: 2 + col * (fw / Math.max(nc, 1)), y: row * 8 + 4,
                        c: ['#1a1a3e', '#222244', '#2a2a4a'][Math.floor(r() * 3)] });
                }
            }
        }
        _cityState.farBuildings.push({ x: fx, w: fw, h: fh, wins });
        fx += fw + 2 + r() * 10;
        if (fx > W) break;
    }
    // Rain
    _cityState.rain = [];
    for (let i = 0; i < 120; i++) {
        _cityState.rain.push({
            x: r() * W, y: r() * H,
            speed: 200 + r() * 300, length: 6 + r() * 12,
            alpha: 0.05 + r() * 0.13,
        });
    }
    // Traffic particles
    _cityState.particles = [];
    const roadY = H - 30;
    const np = Math.max(5, Math.min(40, Math.floor(W / 30)));
    for (let i = 0; i < np; i++) {
        _cityState.particles.push({
            x: r() * W, y: roadY + (r() * 20 - 5),
            speed: (30 + r() * 90) * (r() > 0.5 ? 1 : -1),
            color: TRAFFIC_COLORS[Math.floor(r() * 4)],
            size: 1.5 + r() * 2,
        });
    }
    _cityState.initialized = true;
    _cityState.lastW = W;
    _cityState.lastH = H;
}

function _cityUpdateParticles(dt, W, H) {
    _cityState.particles.forEach(p => {
        p.x += p.speed * dt;
        if (p.x > W + 10) p.x = -10;
        if (p.x < -10) p.x = W + 10;
    });
    _cityState.rain.forEach(r => {
        r.y += r.speed * dt;
        if (r.y > H) { r.y = -r.length; r.x = Math.random() * W; }
    });
}

function _cityDrawSky(ctx, W, H, now) {
    ctx.fillStyle = CITY_BG;
    ctx.fillRect(0, 0, W, H);
    // Gradient bands
    for (let i = 0; i < 8; i++) {
        const frac = i / 8;
        ctx.globalAlpha = 0.02 + frac * 0.06;
        ctx.fillStyle = CITY_BG_HORIZON;
        ctx.fillRect(0, frac * H * 0.5, W, H * 0.5 / 8);
    }
    // Purple haze
    ctx.globalAlpha = 0.08;
    ctx.fillStyle = '#1a0a3a';
    ctx.fillRect(0, H * 0.25, W, H * 0.2);
    ctx.globalAlpha = 1.0;
    // Stars
    _cityState.stars.forEach(s => {
        const alpha = s.brightness * (0.5 + 0.5 * Math.sin(now * s.twinkle + s.phase));
        ctx.globalAlpha = alpha;
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(s.x, s.y, s.size, s.size);
    });
    ctx.globalAlpha = 1.0;
}

function _cityDrawFarBuildings(ctx, W, H) {
    const horizonY = H * 0.45;
    _cityState.farBuildings.forEach(fb => {
        ctx.globalAlpha = 0.6;
        ctx.fillStyle = '#0e0e24';
        ctx.fillRect(fb.x, horizonY - fb.h, fb.w, fb.h);
        ctx.globalAlpha = 1.0;
        fb.wins.forEach(w => {
            ctx.globalAlpha = 0.3;
            ctx.fillStyle = w.c;
            ctx.fillRect(fb.x + w.x, horizonY - fb.h + w.y, 3, 3);
        });
        ctx.globalAlpha = 1.0;
    });
}

function _cityDrawGround(ctx, W, H, now) {
    const groundY = H - 50;
    const roadH = 50;
    ctx.fillStyle = CITY_GROUND;
    ctx.fillRect(0, groundY, W, roadH);
    ctx.fillStyle = CITY_ROAD;
    ctx.fillRect(0, groundY + 5, W, roadH - 5);
    // Sidewalk
    ctx.globalAlpha = 0.4;
    ctx.fillStyle = '#1a1a30';
    ctx.fillRect(0, groundY, W, 5);
    ctx.globalAlpha = 1.0;
    // Lane markings
    ctx.fillStyle = '#2a2a4a';
    const lineY = groundY + 5 + (roadH - 5) / 2;
    for (let dx = 0; dx < W; dx += 40) ctx.fillRect(dx, lineY, 20, 1);
    // Second lane
    ctx.globalAlpha = 0.3;
    const l2y = groundY + 5 + (roadH - 5) * 0.25;
    for (let dx = 10; dx < W; dx += 50) ctx.fillRect(dx, l2y, 15, 1);
    ctx.globalAlpha = 1.0;
    // Crosswalks
    const cwInterval = Math.max(150, W / 5);
    for (let cx = cwInterval / 2; cx < W; cx += cwInterval) {
        ctx.globalAlpha = 0.25;
        ctx.fillStyle = '#cccccc';
        const nStripes = Math.floor((roadH - 5) / 7);
        for (let i = 0; i < nStripes; i++) {
            ctx.fillRect(cx - 8, groundY + 5 + i * 7, 16, 3);
        }
        ctx.globalAlpha = 1.0;
        // Traffic light
        const tlx = cx + 15;
        ctx.fillStyle = '#2a2a3a';
        ctx.fillRect(tlx, groundY - 14, 2, 14);
        ctx.fillStyle = '#1a1a2a';
        ctx.fillRect(tlx - 2, groundY - 20, 6, 10);
        const cycle = (now * 0.5 + cx * 0.01) % 6;
        const lc = cycle < 2.5 ? '#ff2222' : cycle < 3.5 ? '#ffaa00' : '#22ff44';
        ctx.globalAlpha = 0.8;
        ctx.fillStyle = lc;
        ctx.fillRect(tlx - 1, groundY - 19, 3, 3);
        ctx.globalAlpha = 1.0;
    }
}

function _cityDrawBuilding(ctx, entity, pos, now) {
    const state = entity.state || 'unknown';
    const color = CITY_STATE_COLORS[state] || CITY_STATE_COLORS.unknown;
    const glow = CITY_NEON_GLOW[state] || CITY_NEON_GLOW.unknown;
    const bx = pos.x, by = pos.y, bw = pos.w, bh = pos.h;
    const seed = _cityHash(entity.id || 'x') % 10000;

    // Roof cornice (ledge at top)
    if (bw > 14) {
        ctx.fillStyle = '#222244';
        ctx.fillRect(bx - 1, by - 2, bw + 2, 3);
        ctx.globalAlpha = 0.3;
        ctx.fillStyle = '#3a3a5e';
        ctx.fillRect(bx - 1, by - 3, bw + 2, 1);
        ctx.globalAlpha = 1.0;
    }

    // Roof cornice (ledge at top)
    if (bw > 14) {
        ctx.fillStyle = '#222244';
        ctx.fillRect(bx - 1, by - 2, bw + 2, 3);
        ctx.globalAlpha = 0.3;
        ctx.fillStyle = '#3a3a5e';
        ctx.fillRect(bx - 1, by - 3, bw + 2, 1);
        ctx.globalAlpha = 1.0;
    }

    // Building body
    ctx.fillStyle = CITY_WALL;
    ctx.fillRect(bx, by, bw, bh);
    // Side shading
    ctx.globalAlpha = 0.15;
    ctx.fillStyle = '#000000';
    ctx.fillRect(bx, by, bw * 0.15, bh);
    ctx.globalAlpha = 0.08;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(bx + bw * 0.85, by, bw * 0.15, bh);
    ctx.globalAlpha = 1.0;

    // Neon outline glow
    ctx.shadowBlur = state === 'critical' ? 12 : state === 'warning' ? 8 : 4;
    ctx.shadowColor = glow;
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.strokeRect(bx, by, bw, bh);
    ctx.shadowBlur = 0;

    // Floor separators
    if (bh > 30 && bw > 14) {
        const floorGap = Math.max(12, bh / 6);
        ctx.globalAlpha = 0.2;
        ctx.fillStyle = '#2a2a4e';
        for (let fy = by + floorGap; fy < by + bh - 8; fy += floorGap) {
            ctx.fillRect(bx + 1, fy, bw - 2, 1);
        }
        ctx.globalAlpha = 1.0;
    }

    // Windows
    if (bh > 25 && bw > 14) {
        const winW = Math.max(3, Math.min(5, bw / 8));
        const winH = Math.max(3, Math.min(5, bh / 10));
        const gapX = Math.max(winW + 2, bw / Math.max(2, Math.floor(bw / 8)));
        const gapY = Math.max(winH + 3, bh / Math.max(2, Math.floor(bh / 8)));
        const seed = _cityHash(entity.id || 'x') % 10000;
        let row = 0;
        for (let wy = by + 5; wy < by + bh - 8; wy += gapY, row++) {
            let col = 0;
            for (let wx = bx + 3; wx < bx + bw - 5; wx += gapX, col++) {
                const wh = (seed + row * 31 + col * 17) % 100;
                if (state === 'stopped') {
                    ctx.fillStyle = wh < 5 ? '#334455' : CITY_WIN_OFF;
                } else if (state === 'healthy') {
                    if (wh < 15) ctx.fillStyle = CITY_WIN_OFF;
                    else {
                        ctx.fillStyle = CITY_WIN_HEALTHY;
                        if (wh < 20) ctx.globalAlpha = 0.6 + 0.4 * Math.sin(now * 6 + wh);
                    }
                } else if (state === 'running') {
                    ctx.fillStyle = wh < 10 ? CITY_WIN_OFF : '#88bbff';
                } else if (state === 'warning') {
                    const pulse = 0.5 + 0.5 * Math.sin(now * 4 + row * 0.5);
                    if (wh < 25) ctx.fillStyle = CITY_WIN_OFF;
                    else { ctx.fillStyle = CITY_WIN_WARN; ctx.globalAlpha = 0.5 + 0.5 * pulse; }
                } else if (state === 'critical') {
                    const strobe = 0.5 + 0.5 * Math.sin(now * 8 + col * 1.2);
                    if (wh < 30) ctx.fillStyle = CITY_WIN_OFF;
                    else { ctx.fillStyle = CITY_WIN_CRIT; ctx.globalAlpha = 0.4 + 0.6 * strobe; }
                } else {
                    ctx.fillStyle = wh < 60 ? CITY_WIN_OFF : '#334455';
                }
                ctx.fillRect(wx, wy, winW, winH);
                ctx.globalAlpha = 1.0;
            }
        }
    }

    // Roof details (HVAC, antenna)
    if (bw > 16 && bh > 20) {
        const hvacW = Math.max(3, bw * 0.12);
        const hvacH = Math.max(2, Math.min(5, bh * 0.05));
        ctx.fillStyle = '#2a2a40';
        ctx.fillRect(bx + bw * 0.15, by - hvacH, hvacW, hvacH);
        if (bw > 30) ctx.fillRect(bx + bw * 0.6, by - hvacH, hvacW, hvacH);
        if (bw > 20) {
            const ax = bx + bw * 0.5;
            const ah = Math.max(6, bh * 0.08);
            ctx.fillStyle = '#3a3a5a';
            ctx.fillRect(ax, by - hvacH - ah, 1, ah);
            if (Math.sin(now * 3) > 0.3) {
                ctx.globalAlpha = 0.9;
                ctx.fillStyle = state === 'critical' ? '#ff2222' : '#ff4444';
                ctx.fillRect(ax - 1, by - hvacH - ah - 1, 2, 2);
                ctx.globalAlpha = 1.0;
            }
        }
    }

    // Entrance (awning, double doors, handles, light spill)
    if (bh > 35 && bw > 18) {
        const doorW = Math.max(6, bw * 0.2);
        const doorH = Math.max(6, Math.min(12, bh * 0.12));
        const doorX = bx + (bw - doorW) / 2;
        const doorY = by + bh - doorH;
        // Door frame
        ctx.fillStyle = '#1a1a30';
        ctx.fillRect(doorX - 1, doorY - 1, doorW + 2, doorH + 1);
        // Double doors
        const halfW = doorW / 2 - 0.5;
        ctx.fillStyle = '#0a0a18';
        ctx.fillRect(doorX, doorY, halfW, doorH);
        ctx.fillRect(doorX + halfW + 1, doorY, halfW, doorH);
        // Door handles
        ctx.fillStyle = color;
        ctx.globalAlpha = 0.7;
        ctx.fillRect(doorX + halfW - 1.5, doorY + doorH * 0.55, 1, 1);
        ctx.fillRect(doorX + halfW + 1.5, doorY + doorH * 0.55, 1, 1);
        ctx.globalAlpha = 1.0;
        // Awning
        const awningW = doorW + 8;
        const awningX = doorX - 4;
        const awningY = doorY - 4;
        ctx.globalAlpha = 0.4;
        ctx.fillStyle = color;
        ctx.fillRect(awningX, awningY, awningW, 2);
        ctx.globalAlpha = 0.25;
        ctx.fillRect(awningX + 1, awningY + 2, awningW - 2, 1);
        ctx.globalAlpha = 1.0;
        // Light spill on ground
        ctx.globalAlpha = 0.1;
        ctx.fillStyle = color;
        ctx.fillRect(doorX - 3, by + bh - 1, doorW + 6, 4);
        ctx.globalAlpha = 1.0;
    }

    // Neon sign
    if (bw > 20) {
        const name = (entity.name || '').slice(0, 12);
        const signW = Math.min(bw + 6, name.length * 7 + 8);
        const signH = 14;
        const signX = bx + (bw - signW) / 2;
        let signY = by - signH - 2;
        if (signY < 0) signY = by + 2;
        ctx.fillStyle = CITY_NEON_BG;
        ctx.fillRect(signX, signY, signW, signH);
        ctx.shadowBlur = 6;
        ctx.shadowColor = glow;
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.strokeRect(signX, signY, signW, signH);
        const flicker = 0.85 + 0.15 * Math.sin(now * 12 + _cityHash(entity.id || '') % 10);
        ctx.globalAlpha = flicker;
        ctx.fillStyle = color;
        ctx.font = "bold 9px 'Courier New', monospace";
        ctx.fillText(name, signX + 4, signY + 10);
        ctx.globalAlpha = 1.0;
        ctx.shadowBlur = 0;
    }

    // Fire/smoke for critical
    if (state === 'critical') {
        const fireC = ['#ff4400', '#ff6600', '#ffaa00', '#ff2200'];
        for (let i = 0; i < 5; i++) {
            const fx2 = bx + ((seed + i * 73) % 100) / 100 * bw;
            const phase = Math.sin(now * 8 + i * 1.3);
            const fy2 = by - 2 - ((seed + i * 37) % 100) / 100 * 10 + phase * 3;
            ctx.globalAlpha = 0.6 + 0.3 * Math.abs(phase);
            ctx.fillStyle = fireC[i % 4];
            ctx.fillRect(fx2, fy2, 3, 4);
        }
        ctx.globalAlpha = 1.0;
        for (let i = 0; i < 3; i++) {
            const sx = bx + bw / 2 + Math.sin(now * 2 + i) * 8;
            const sy = by - 15 - i * 6 + Math.sin(now * 3 + i * 0.7) * 2;
            ctx.globalAlpha = 0.2 - i * 0.05;
            ctx.fillStyle = '#444444';
            ctx.fillRect(sx - 4, sy, 8, 5);
        }
        ctx.globalAlpha = 1.0;
    }
}

function _cityDrawDistrict(ctx, entity, pos) {
    const state = entity.state || 'unknown';
    const color = CITY_STATE_COLORS[state] || CITY_STATE_COLORS.unknown;
    const glow = CITY_NEON_GLOW[state] || CITY_NEON_GLOW.unknown;
    ctx.shadowBlur = 12;
    ctx.shadowColor = glow;
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.strokeRect(pos.x + 2, pos.y + 2, pos.w - 4, pos.h - 4);
    ctx.shadowBlur = 0;
    // Label
    ctx.fillStyle = CITY_NEON_BG;
    const lw = Math.min(160, pos.w - 16);
    ctx.fillRect(pos.x + 8, pos.y + 4, lw, 22);
    ctx.shadowBlur = 8;
    ctx.shadowColor = glow;
    ctx.fillStyle = color;
    ctx.font = "bold 13px 'Courier New', monospace";
    ctx.fillText((entity.name || '').slice(0, 20), pos.x + 14, pos.y + 19);
    ctx.shadowBlur = 0;
}

function _cityDrawBlock(ctx, entity, pos) {
    ctx.fillStyle = '#0a0a18';
    ctx.fillRect(pos.x, pos.y, pos.w, pos.h);
    ctx.strokeStyle = '#1a1a3a';
    ctx.lineWidth = 1;
    ctx.strokeRect(pos.x, pos.y, pos.w, pos.h);
    ctx.fillStyle = '#4a4a6a';
    ctx.font = "10px 'Courier New', monospace";
    ctx.fillText((entity.name || '').slice(0, 16), pos.x + 4, pos.y + 14);
}

function _cityDrawRain(ctx) {
    _cityState.rain.forEach(d => {
        ctx.globalAlpha = d.alpha;
        ctx.fillStyle = '#8899cc';
        ctx.fillRect(d.x, d.y, 1, d.length);
    });
    ctx.globalAlpha = 1.0;
}

function _cityDrawTraffic(ctx) {
    _cityState.particles.forEach(p => {
        ctx.globalAlpha = 0.8;
        ctx.fillStyle = p.color;
        ctx.fillRect(p.x, p.y, p.size, p.size * 0.5);
    });
    ctx.globalAlpha = 1.0;
}

function _cityDrawReflections(ctx, entities, layout, W, H, now) {
    const groundY = H - 50;
    const roadY = groundY + 5;
    const roadH = H - roadY;
    // Wet shimmer
    const shimmer = Math.sin(now * 1.5);
    ctx.globalAlpha = 0.04 + 0.02 * shimmer;
    ctx.fillStyle = '#4488ff';
    ctx.fillRect(0, roadY, W, roadH);
    ctx.globalAlpha = 1.0;
    // Building reflections
    entities.forEach(e => {
        if (e.type !== 'service') return;
        const pos = layout[e.id];
        if (!pos) return;
        const color = CITY_STATE_COLORS[e.state || 'unknown'] || CITY_STATE_COLORS.unknown;
        ctx.globalAlpha = 0.05 + 0.02 * Math.sin(now * 2 + pos.x * 0.01);
        ctx.fillStyle = color;
        ctx.fillRect(pos.x, roadY + 2, pos.w, Math.min(roadH - 4, pos.h * 0.3));
    });
    ctx.globalAlpha = 1.0;
    // Neon reflections
    const rc = ['#ff00ff', '#00ffff', '#ffff00'];
    rc.forEach((c, i) => {
        const rx = (W / (rc.length + 1)) * (i + 1);
        const rw = 40 + 20 * Math.sin(now * 2 + i);
        ctx.globalAlpha = 0.06 + 0.03 * Math.sin(now * 3 + i * 1.5);
        ctx.fillStyle = c;
        ctx.fillRect(rx - rw / 2, roadY + 5, rw, roadH - 10);
    });
    ctx.globalAlpha = 1.0;
}

metaphorRenderers.city = {
    computeLayout(entities, W, H) {
        const layout = {};
        const byId = {};
        entities.forEach(e => byId[e.id] = e);
        const roots = entities.filter(e => !e.parent);
        if (!roots.length) return layout;

        const districtW = W / Math.max(roots.length, 1);
        const groundY = H - 50;
        
        roots.forEach((root, di) => {
            const dx = di * districtW;
            layout[root.id] = { x: dx, y: 0, w: districtW, h: H };

            const children = (root.children || []).map(id => byId[id]).filter(Boolean);
            if (!children.length) return;
            
            const blockW = districtW - 20;
            const blockSpacing = 30;
            const startX = dx + 10;
            
            children.forEach((child, bi) => {
                const cx = startX + bi * (blockW + blockSpacing);
                if (cx > W - 50) return;
                
                const blockY = groundY - 140;
                const blockH = 140;
                layout[child.id] = { x: cx, y: blockY, w: blockW, h: blockH };

                const grandchildren = (child.children || []).map(id => byId[id]).filter(Boolean);
                if (!grandchildren.length) return;
                
                const buildingsPerRow = Math.min(4, grandchildren.length);
                const buildingSlotW = blockW / buildingsPerRow;
                
                grandchildren.forEach((gc, gi) => {
                    const metrics = gc.metrics || {};
                    const cpu = Math.max(0, Math.min(100, metrics.cpu || 50));
                    const mem = Math.max(0, Math.min(100, metrics.mem || 50));
                    
                    const bw2 = Math.max(20, Math.min(50, 20 + (mem / 100) * 30));
                    const bh2 = Math.max(30, Math.min(120, 30 + (cpu / 100) * 90));
                    
                    const col = gi % buildingsPerRow;
                    const row = Math.floor(gi / buildingsPerRow);
                    const bx2 = cx + col * buildingSlotW + (buildingSlotW - bw2) / 2;
                    const by2 = groundY - bh2 - 5 - row * 15;
                    
                    layout[gc.id] = { x: bx2, y: by2, w: bw2, h: bh2 };
                });
            });
        });
        return layout;
    },

    render(ctx, entities, layout, W, H, COLORS) {
        // Init scene if needed
        if (!_cityState.initialized || _cityState.lastW !== W || _cityState.lastH !== H) {
            _cityInitScene(W, H);
        }
        const now = performance.now() / 1000 - _cityState.startTime;
        const dt = 0.016;
        _cityUpdateParticles(dt, W, H);

        // Layer 0: Sky + Stars
        _cityDrawSky(ctx, W, H, now);
        // Layer 1: Far buildings
        _cityDrawFarBuildings(ctx, W, H);
        // Layer 2: Ground + Roads
        _cityDrawGround(ctx, W, H, now);

        // Districts
        entities.forEach(e => {
            const pos = layout[e.id];
            if (!pos || e.type !== 'cluster') return;
            _cityDrawDistrict(ctx, e, pos);
        });
        // Blocks
        entities.forEach(e => {
            const pos = layout[e.id];
            if (!pos || e.type !== 'node') return;
            _cityDrawBlock(ctx, e, pos);
        });
        // Layer 3: Buildings
        entities.forEach(e => {
            const pos = layout[e.id];
            if (!pos || e.type !== 'service') return;
            _cityDrawBuilding(ctx, e, pos, now);
        });

        // Layer 4: Rain + Traffic
        _cityDrawRain(ctx);
        _cityDrawTraffic(ctx);
        // Layer 2b: Ground reflections
        _cityDrawReflections(ctx, entities, layout, W, H, now);
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

// Forest metaphor — Full Visual Overhaul (6-layer depth)
// Mapping: Cluster=Grove, Node=Tree, Service=Canopy, Container=Leaf cluster
const _forestState = {
    initialized: false,
    lastW: 0,
    lastH: 0,
    startTime: performance.now() / 1000,
    stars: [],
    distantTrees: [],
    grassTufts: [],
    rocks: [],
    undergrowth: [],
    fireflies: [],
    petals: [],
    waterParticles: [],
    sunX: 0,
    sunY: 0,
};

const FOREST_SKY_TOP = '#87ceeb';
const FOREST_SKY_BOTTOM = '#1a0a2e';
const FOREST_SOIL = '#3d2817';
const FOREST_GRASS = '#228b22';
const FOREST_BARK = '#5d3a1a';
const FOREST_LEAF_HEALTHY = '#4ade80';
const FOREST_LEAF_WARN = '#fbbf24';
const FOREST_LEAF_CRIT = '#ef4444';
const FOREST_LEAF_DEAD = '#8b4513';
const FOREST_WATER = '#4488ff';

const FOREST_STATE_COLORS = {
    healthy: '#4ade80', running: '#60a5fa', warning: '#fbbf24',
    critical: '#ef4444', stopped: '#374151', idle: '#94a3b8',
    degraded: '#f97316', pending: '#a78bfa', scaling: '#06b6d4', unknown: '#6b7280',
};

function _forestHash(s) {
    let h = 0;
    for (let i = 0; i < s.length; i++) { h = ((h << 5) - h + s.charCodeAt(i)) | 0; }
    return h;
}

function _forestInitScene(W, H) {
    const rng = (seed) => {
        let s = seed;
        return () => { s = (s * 16807 + 0) % 2147483647; return s / 2147483647; };
    };

    // Stars
    const r1 = rng(12345);
    _forestState.stars = [];
    for (let i = 0; i < 60; i++) {
        _forestState.stars.push({ x: r1() * W, y: r1() * H * 0.4, brightness: 0.2 + r1() * 0.8, size: 0.5 + r1() * 1.5 });
    }

    // Distant tree silhouettes (horizon)
    const r2 = rng(54321);
    _forestState.distantTrees = [];
    const horizonY = H * 0.45;
    for (let i = 0; i < 25; i++) {
        _forestState.distantTrees.push({
            x: r2() * W,
            y: horizonY - 10 + r2() * 20,
            w: 15 + r2() * 30,
            h: 30 + r2() * 60,
            shade: r2(),
        });
    }

    // Grass tufts on ground
    const r3 = rng(11111);
    _forestState.grassTufts = [];
    const groundY = H * 0.75;
    for (let i = 0; i < 80; i++) {
        _forestState.grassTufts.push({
            x: r3() * W,
            y: groundY + r3() * (H - groundY),
            blades: 2 + Math.floor(r3() * 4),
            height: 4 + r3() * 10,
            phase: r3() * Math.PI * 2,
        });
    }

    // Rocks
    const r4 = rng(22222);
    _forestState.rocks = [];
    for (let i = 0; i < 12; i++) {
        _forestState.rocks.push({
            x: r4() * W,
            y: groundY + 10 + r4() * (H - groundY - 20),
            r: 2 + r4() * 5,
            shade: 0.3 + r4() * 0.4,
        });
    }

    // Undergrowth (bushes, ferns, mushrooms)
    const r5 = rng(33333);
    _forestState.undergrowth = [];
    for (let i = 0; i < 20; i++) {
        const kind = r5() < 0.5 ? 'bush' : (r5() < 0.7 ? 'fern' : 'mushroom');
        _forestState.undergrowth.push({
            x: r5() * W,
            y: groundY + 5 + r5() * (H - groundY - 15),
            kind: kind,
            size: 6 + r5() * 12,
            phase: r5() * Math.PI * 2,
        });
    }

    // Fireflies
    const r6 = rng(44444);
    _forestState.fireflies = [];
    for (let i = 0; i < 20; i++) {
        _forestState.fireflies.push({
            x: r6() * W,
            y: H * 0.3 + r6() * H * 0.5,
            vx: (r6() - 0.5) * 15,
            vy: (r6() - 0.5) * 10,
            phase: r6() * Math.PI * 2,
            brightness: 0.3 + r6() * 0.7,
        });
    }

    // Falling petals
    const r7 = rng(55555);
    _forestState.petals = [];
    for (let i = 0; i < 30; i++) {
        _forestState.petals.push({
            x: r7() * W,
            y: r7() * H * 0.6,
            vy: 8 + r7() * 20,
            vx: (r7() - 0.5) * 15,
            size: 1.5 + r7() * 3,
            rot: r7() * Math.PI * 2,
            rotSpeed: (r7() - 0.5) * 2,
            color: r7() < 0.5 ? '#ff9ecd' : '#ffc8e0',
        });
    }

    // Water particles (for stream)
    const r8 = rng(66666);
    _forestState.waterParticles = [];
    for (let i = 0; i < 15; i++) {
        _forestState.waterParticles.push({
            offset: r8(),
            speed: 0.02 + r8() * 0.04,
        });
    }

    // Sun position
    _forestState.sunX = W * 0.75;
    _forestState.sunY = H * 0.12;

    _forestState.initialized = true;
    _forestState.lastW = W;
    _forestState.lastH = H;
}

function _forestDrawSky(ctx, W, H, now) {
    // Gradient sky — time-based cycle
    const cycle = (Math.sin(now * 0.05) + 1) / 2; // 0..1
    const grad = ctx.createLinearGradient(0, 0, 0, H * 0.75);
    // Interpolate between day and dusk
    const topR = Math.round(135 - cycle * 109);
    const topG = Math.round(206 - cycle * 196);
    const topB = Math.round(235 - cycle * 189);
    const botR = Math.round(26 + cycle * 60);
    const botG = Math.round(10 + cycle * 40);
    const botB = Math.round(46 + cycle * 80);
    grad.addColorStop(0, `rgb(${topR},${topG},${topB})`);
    grad.addColorStop(1, `rgb(${botR},${botG},${botB})`);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);

    // Stars (visible more during dusk)
    const starAlpha = 0.1 + cycle * 0.6;
    _forestState.stars.forEach(star => {
        const twinkle = 0.5 + 0.5 * Math.sin(now * 2 + star.x);
        ctx.fillStyle = `rgba(255,255,240,${starAlpha * star.brightness * twinkle})`;
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
        ctx.fill();
    });

    // Sun/moon
    const sunY = _forestState.sunY + cycle * 20;
    const sunGrad = ctx.createRadialGradient(_forestState.sunX, sunY, 0, _forestState.sunX, sunY, 40);
    const sunAlpha = 0.9 - cycle * 0.5;
    sunGrad.addColorStop(0, `rgba(255,220,100,${sunAlpha})`);
    sunGrad.addColorStop(0.3, `rgba(255,180,60,${sunAlpha * 0.6})`);
    sunGrad.addColorStop(1, 'rgba(255,180,60,0)');
    ctx.fillStyle = sunGrad;
    ctx.beginPath();
    ctx.arc(_forestState.sunX, sunY, 40, 0, Math.PI * 2);
    ctx.fill();
    // Sun core
    ctx.fillStyle = `rgba(255,240,180,${sunAlpha})`;
    ctx.beginPath();
    ctx.arc(_forestState.sunX, sunY, 12, 0, Math.PI * 2);
    ctx.fill();

    // Light rays from sun
    ctx.save();
    ctx.globalAlpha = 0.05 + cycle * 0.03;
    for (let i = 0; i < 5; i++) {
        const angle = -0.5 + i * 0.25 + Math.sin(now * 0.3 + i) * 0.05;
        const rayLen = H * 0.7;
        ctx.strokeStyle = 'rgba(255,230,150,0.15)';
        ctx.lineWidth = 8 + i * 3;
        ctx.beginPath();
        ctx.moveTo(_forestState.sunX, sunY);
        ctx.lineTo(_forestState.sunX + Math.cos(angle + 1) * rayLen, sunY + Math.sin(angle + 1) * rayLen);
        ctx.stroke();
    }
    ctx.restore();
}

function _forestDrawDistantTrees(ctx, W, H) {
    const horizonY = H * 0.45;
    // Distant hill/mist
    const mistGrad = ctx.createLinearGradient(0, horizonY - 30, 0, horizonY + 40);
    mistGrad.addColorStop(0, 'rgba(20,60,20,0.3)');
    mistGrad.addColorStop(1, 'rgba(20,60,20,0)');
    ctx.fillStyle = mistGrad;
    ctx.fillRect(0, horizonY - 30, W, 70);

    // Silhouette trees
    _forestState.distantTrees.forEach(tree => {
        const darkGreen = `rgba(${15 + tree.shade * 20},${40 + tree.shade * 20},${15 + tree.shade * 10},0.8)`;
        // Trunk
        ctx.fillStyle = `rgba(30,20,10,0.6)`;
        ctx.fillRect(tree.x - 2, tree.y, 4, tree.h * 0.4);
        // Canopy — triangular
        ctx.fillStyle = darkGreen;
        ctx.beginPath();
        ctx.moveTo(tree.x, tree.y - tree.h * 0.3);
        ctx.lineTo(tree.x - tree.w / 2, tree.y + tree.h * 0.3);
        ctx.lineTo(tree.x + tree.w / 2, tree.y + tree.h * 0.3);
        ctx.closePath();
        ctx.fill();
    });
}

function _forestDrawGround(ctx, W, H, now) {
    const groundY = H * 0.75;

    // Ground gradient — soil
    const soilGrad = ctx.createLinearGradient(0, groundY, 0, H);
    soilGrad.addColorStop(0, '#3d6b2e'); // grass top
    soilGrad.addColorStop(0.05, '#2d5a1e');
    soilGrad.addColorStop(0.15, '#3d2817'); // soil
    soilGrad.addColorStop(1, '#2a1a0f');
    ctx.fillStyle = soilGrad;
    ctx.fillRect(0, groundY, W, H - groundY);

    // Soil texture — small dots
    const seed = 777;
    let s = seed;
    const nextR = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
    ctx.fillStyle = 'rgba(80,50,30,0.4)';
    for (let i = 0; i < 100; i++) {
        const px = nextR() * W;
        const py = groundY + 15 + nextR() * (H - groundY - 20);
        const pr = 1 + nextR() * 2;
        ctx.beginPath();
        ctx.arc(px, py, pr, 0, Math.PI * 2);
        ctx.fill();
    }

    // Pebbles
    _forestState.rocks.forEach(rock => {
        ctx.fillStyle = `rgba(${Math.round(100 * rock.shade)},${Math.round(90 * rock.shade)},${Math.round(80 * rock.shade)},0.7)`;
        ctx.beginPath();
        ctx.ellipse(rock.x, rock.y, rock.r, rock.r * 0.7, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = 'rgba(40,30,20,0.3)';
        ctx.lineWidth = 0.5;
        ctx.stroke();
    });

    // Grass tufts
    _forestState.grassTufts.forEach(tuft => {
        const sway = Math.sin(now * 1.5 + tuft.phase) * 2;
        ctx.strokeStyle = '#2d8a2d';
        ctx.lineWidth = 1.2;
        for (let b = 0; b < tuft.blades; b++) {
            const bx = tuft.x + (b - tuft.blades / 2) * 2;
            const swayB = sway * (b % 2 === 0 ? 1 : -0.5);
            ctx.beginPath();
            ctx.moveTo(bx, tuft.y);
            ctx.quadraticCurveTo(bx + swayB, tuft.y - tuft.height * 0.6, bx + swayB * 1.5, tuft.y - tuft.height);
            ctx.stroke();
        }
    });

    // Path/water stream
    const streamY = groundY + (H - groundY) * 0.4;
    ctx.save();
    ctx.globalAlpha = 0.5;
    ctx.strokeStyle = FOREST_WATER;
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.moveTo(0, streamY);
    for (let x = 0; x <= W; x += 20) {
        const sy = streamY + Math.sin(x * 0.02 + now * 0.8) * 3;
        ctx.lineTo(x, sy);
    }
    ctx.stroke();
    // Stream highlight
    ctx.strokeStyle = 'rgba(150,200,255,0.3)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, streamY - 1);
    for (let x = 0; x <= W; x += 20) {
        const sy = streamY - 1 + Math.sin(x * 0.03 + now * 1.2) * 2;
        ctx.lineTo(x, sy);
    }
    ctx.stroke();
    // Water particles
    _forestState.waterParticles.forEach(wp => {
        const px = ((wp.offset + now * wp.speed) % 1) * W;
        const py = streamY + Math.sin(px * 0.02 + now * 0.8) * 3;
        ctx.fillStyle = 'rgba(200,230,255,0.6)';
        ctx.beginPath();
        ctx.arc(px, py, 1.5, 0, Math.PI * 2);
        ctx.fill();
    });
    ctx.restore();
}

function _forestDrawTree(ctx, entity, pos, now, layout) {
    const cx = pos.x + pos.w / 2;
    const baseY = pos.y + pos.h; // bottom of trunk area
    const trunkTop = pos.y;
    const trunkW = Math.max(8, pos.w * 0.35);
    const h = baseY - trunkTop;
    const seed = Math.abs(_forestHash(entity.id || ''));
    const rng = (() => { let s = seed; return () => { s = (s * 16807) % 2147483647; return s / 2147483647; }; })();

    // Shadow on ground
    const shadowOffset = 15 + (cx / (pos.w || 1)) * 5;
    ctx.fillStyle = 'rgba(0,0,0,0.15)';
    ctx.beginPath();
    ctx.ellipse(cx + shadowOffset, baseY + 5, trunkW * 2, 6, 0, 0, Math.PI * 2);
    ctx.fill();

    // Trunk with bark texture
    const trunkX = cx - trunkW / 2;
    ctx.fillStyle = FOREST_BARK;
    ctx.fillRect(trunkX, trunkTop + h * 0.15, trunkW, h * 0.85);

    // Bark texture — vertical lines with color variation
    ctx.save();
    for (let i = 0; i < 8; i++) {
        const lx = trunkX + rng() * trunkW;
        const ly = trunkTop + h * 0.15 + rng() * h * 0.1;
        const lh = h * 0.5 + rng() * h * 0.3;
        const shade = Math.round(60 + rng() * 40);
        ctx.strokeStyle = `rgba(${shade},${Math.round(shade * 0.6)},${Math.round(shade * 0.3)},0.5)`;
        ctx.lineWidth = 0.8 + rng() * 1.2;
        ctx.beginPath();
        ctx.moveTo(lx, ly);
        ctx.lineTo(lx + (rng() - 0.5) * 3, ly + lh);
        ctx.stroke();
    }
    // Bark knots
    for (let i = 0; i < 2; i++) {
        const kx = trunkX + 2 + rng() * (trunkW - 4);
        const ky = trunkTop + h * 0.3 + rng() * h * 0.5;
        ctx.fillStyle = 'rgba(40,25,10,0.5)';
        ctx.beginPath();
        ctx.ellipse(kx, ky, 2, 3, rng() * Math.PI, 0, Math.PI * 2);
        ctx.fill();
    }
    ctx.restore();

    // Trunk highlight (sun-facing side)
    const highlightX = cx > pos.w ? trunkX + trunkW - 2 : trunkX;
    ctx.fillStyle = 'rgba(120,80,40,0.3)';
    ctx.fillRect(highlightX, trunkTop + h * 0.2, 2, h * 0.6);

    // Root flare
    ctx.fillStyle = '#4a2a10';
    ctx.beginPath();
    ctx.moveTo(trunkX - 4, baseY);
    ctx.quadraticCurveTo(trunkX, baseY - 8, trunkX + trunkW * 0.3, baseY - 3);
    ctx.lineTo(trunkX + trunkW * 0.7, baseY - 3);
    ctx.quadraticCurveTo(trunkX + trunkW, baseY - 8, trunkX + trunkW + 4, baseY);
    ctx.closePath();
    ctx.fill();

    // Branches connecting trunk to canopy
    const children = entity.children || [];
    const stateColor = FOREST_STATE_COLORS[entity.state] || FOREST_STATE_COLORS.unknown;
    const cpu = (entity.metrics || {}).cpu || 50;
    const numBranches = Math.max(2, Math.min(5, Math.ceil(children.length * 0.5) + 1));

    for (let b = 0; b < numBranches; b++) {
        const angle = -Math.PI / 2 + (b - (numBranches - 1) / 2) * 0.6;
        const branchLen = h * 0.3 + rng() * h * 0.15;
        const bx1 = cx;
        const by1 = trunkTop + h * 0.15 + rng() * h * 0.1;
        const bx2 = cx + Math.cos(angle) * branchLen;
        const by2 = by1 + Math.sin(angle) * branchLen;
        const sway = Math.sin(now * 0.8 + b) * 1.5;

        ctx.strokeStyle = FOREST_BARK;
        ctx.lineWidth = 2 + rng() * 2;
        ctx.beginPath();
        ctx.moveTo(bx1, by1);
        ctx.quadraticCurveTo(
            (bx1 + bx2) / 2 + sway,
            (by1 + by2) / 2 - 5,
            bx2 + sway, by2
        );
        ctx.stroke();
    }
}

function _forestDrawCanopy(ctx, entity, pos, now, layout) {
    const cx = pos.x + pos.w / 2;
    const cy = pos.y + pos.h / 2;
    const state = entity.state || 'unknown';
    const cpu = (entity.metrics || {}).cpu || 50;
    const baseR = Math.max(8, pos.w / 2);
    const seed = Math.abs(_forestHash(entity.id || ''));
    const rng = (() => { let s = seed; return () => { s = (s * 16807) % 2147483647; return s / 2147483647; }; })();

    // Leaf cluster color based on state
    let leafColor, leafDark, leafLight;
    if (state === 'healthy' || state === 'running') {
        leafColor = '#4ade80'; leafDark = '#228b22'; leafLight = '#6aff90';
    } else if (state === 'warning' || state === 'idle') {
        leafColor = '#fbbf24'; leafDark = '#b8860b'; leafLight = '#ffe066';
    } else if (state === 'critical' || state === 'degraded') {
        leafColor = '#ef4444'; leafDark = '#8b0000'; leafLight = '#ff7777';
    } else if (state === 'stopped') {
        leafColor = '#8b4513'; leafDark = '#5c2d0e'; leafLight = '#a0522d';
    } else {
        leafColor = FOREST_STATE_COLORS[state] || '#6b7280';
        leafDark = '#3a3a3a'; leafLight = '#9a9a9a';
    }

    // Draw individual leaf clusters (not a solid blob)
    const numClusters = 5 + Math.floor(cpu / 20);
    const swayBase = Math.sin(now * 1.2 + seed * 0.01) * 2;

    for (let i = 0; i < numClusters; i++) {
        const angle = (i / numClusters) * Math.PI * 2 + rng() * 0.5;
        const dist = rng() * baseR * 0.8;
        const clusterR = 4 + rng() * (baseR * 0.4);
        const lx = cx + Math.cos(angle) * dist + swayBase * (1 + rng() * 0.5);
        const ly = cy + Math.sin(angle) * dist * 0.7 - baseR * 0.2;

        // Leaf cluster — irregular shape
        const shade = rng();
        const col = shade < 0.33 ? leafDark : (shade < 0.66 ? leafColor : leafLight);
        ctx.fillStyle = col;
        ctx.beginPath();
        // Organic blob shape
        const pts = 6;
        for (let p = 0; p <= pts; p++) {
            const a = (p / pts) * Math.PI * 2;
            const r = clusterR * (0.7 + rng() * 0.5);
            const px = lx + Math.cos(a) * r;
            const py = ly + Math.sin(a) * r * 0.8;
            if (p === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.fill();
    }

    // Canopy highlight (sun)
    ctx.fillStyle = `rgba(255,255,200,0.08)`;
    ctx.beginPath();
    ctx.arc(cx - baseR * 0.3, cy - baseR * 0.4, baseR * 0.5, 0, Math.PI * 2);
    ctx.fill();

    // Shadow under canopy
    ctx.fillStyle = 'rgba(0,30,0,0.15)';
    ctx.beginPath();
    ctx.ellipse(cx, cy + baseR * 0.8, baseR * 0.9, baseR * 0.25, 0, 0, Math.PI * 2);
    ctx.fill();
}

function _forestDrawLeafCluster(ctx, entity, pos, now) {
    const cx = pos.x + pos.w / 2;
    const cy = pos.y + pos.h / 2;
    const state = entity.state || 'unknown';
    const r = Math.max(3, pos.w / 2);
    const seed = Math.abs(_forestHash(entity.id || ''));

    let color;
    if (state === 'healthy' || state === 'running') color = '#4ade80';
    else if (state === 'warning' || state === 'idle') color = '#fbbf24';
    else if (state === 'critical') color = '#ef4444';
    else if (state === 'stopped') color = '#8b4513';
    else color = FOREST_STATE_COLORS[state] || '#6b7280';

    const sway = Math.sin(now * 1.5 + seed * 0.01) * 1;

    // Small leaf cluster
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(cx + sway, cy, r, 0, Math.PI * 2);
    ctx.fill();

    // Leaf detail
    ctx.fillStyle = 'rgba(255,255,255,0.1)';
    ctx.beginPath();
    ctx.arc(cx + sway - r * 0.3, cy - r * 0.3, r * 0.3, 0, Math.PI * 2);
    ctx.fill();
}

function _forestDrawUndergrowth(ctx, W, H, now) {
    _forestState.undergrowth.forEach(ug => {
        const sway = Math.sin(now * 0.8 + ug.phase) * 1.5;
        if (ug.kind === 'bush') {
            ctx.fillStyle = '#1a5c1a';
            ctx.beginPath();
            ctx.arc(ug.x + sway, ug.y, ug.size, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = '#2a7a2a';
            ctx.beginPath();
            ctx.arc(ug.x + sway - 2, ug.y - 2, ug.size * 0.6, 0, Math.PI * 2);
            ctx.fill();
        } else if (ug.kind === 'fern') {
            ctx.strokeStyle = '#2d6b2d';
            ctx.lineWidth = 1;
            for (let f = 0; f < 3; f++) {
                const fx = ug.x + (f - 1) * 4 + sway;
                ctx.beginPath();
                ctx.moveTo(fx, ug.y);
                ctx.quadraticCurveTo(fx + sway * 2, ug.y - ug.size * 0.7, fx + sway * 3, ug.y - ug.size);
                ctx.stroke();
                // Fern fronds
                for (let ff = 0; ff < 3; ff++) {
                    const fy = ug.y - ug.size * (ff + 1) * 0.25;
                    ctx.beginPath();
                    ctx.moveTo(fx + sway, fy);
                    ctx.lineTo(fx + sway + 3, fy - 2);
                    ctx.stroke();
                    ctx.beginPath();
                    ctx.moveTo(fx + sway, fy);
                    ctx.lineTo(fx + sway - 3, fy - 2);
                    ctx.stroke();
                }
            }
        } else if (ug.kind === 'mushroom') {
            // Stem
            ctx.fillStyle = '#e8d8c0';
            ctx.fillRect(ug.x - 1, ug.y - ug.size * 0.4, 3, ug.size * 0.4);
            // Cap
            ctx.fillStyle = '#cc3333';
            ctx.beginPath();
            ctx.arc(ug.x + 0.5, ug.y - ug.size * 0.4, ug.size * 0.35, Math.PI, 0);
            ctx.fill();
            // Spots
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.arc(ug.x - 1, ug.y - ug.size * 0.5, 1, 0, Math.PI * 2);
            ctx.fill();
            ctx.beginPath();
            ctx.arc(ug.x + 2, ug.y - ug.size * 0.55, 0.8, 0, Math.PI * 2);
            ctx.fill();
        }
    });
}

function _forestDrawFireflies(ctx, W, H, now) {
    _forestState.fireflies.forEach(ff => {
        // Update position
        ff.x += ff.vx * 0.016;
        ff.y += ff.vy * 0.016;
        ff.vx += (Math.sin(now + ff.phase) * 5 - ff.vx * 0.5) * 0.016;
        ff.vy += (Math.cos(now * 0.7 + ff.phase) * 3 - ff.vy * 0.5) * 0.016;
        // Wrap
        if (ff.x < 0) ff.x = W;
        if (ff.x > W) ff.x = 0;
        if (ff.y < H * 0.2) ff.y = H * 0.7;
        if (ff.y > H * 0.8) ff.y = H * 0.3;

        const glow = ff.brightness * (0.5 + 0.5 * Math.sin(now * 3 + ff.phase));
        // Glow
        const grad = ctx.createRadialGradient(ff.x, ff.y, 0, ff.x, ff.y, 6);
        grad.addColorStop(0, `rgba(200,255,100,${glow * 0.6})`);
        grad.addColorStop(1, 'rgba(200,255,100,0)');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(ff.x, ff.y, 6, 0, Math.PI * 2);
        ctx.fill();
        // Core
        ctx.fillStyle = `rgba(255,255,180,${glow})`;
        ctx.beginPath();
        ctx.arc(ff.x, ff.y, 1.5, 0, Math.PI * 2);
        ctx.fill();
    });
}

function _forestDrawPetals(ctx, W, H, now) {
    _forestState.petals.forEach(petal => {
        petal.y += petal.vy * 0.016;
        petal.x += petal.vx * 0.016 + Math.sin(now * 2 + petal.rot) * 0.3;
        petal.rot += petal.rotSpeed * 0.016;
        // Reset if off screen
        if (petal.y > H) {
            petal.y = -5;
            petal.x = Math.random() * W;
        }
        ctx.save();
        ctx.translate(petal.x, petal.y);
        ctx.rotate(petal.rot);
        ctx.fillStyle = petal.color;
        ctx.globalAlpha = 0.6;
        ctx.beginPath();
        ctx.ellipse(0, 0, petal.size, petal.size * 0.5, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    });
}

metaphorRenderers.forest = {
    computeLayout(entities, W, H) {
        const layout = {};
        const byId = {};
        entities.forEach(e => byId[e.id] = e);
        const roots = entities.filter(e => !e.parent);

        const spacing = W / Math.max(roots.length, 1);
        roots.forEach((root, i) => {
            const tx = i * spacing + spacing / 2;
            const trunkH = H * 0.35;
            const trunkW = 30 + ((root.metrics || {}).mem || 50) / 100 * 20;
            // Trunk (cluster/grove) — bottom half of canvas
            layout[root.id] = {
                x: tx - trunkW / 2,
                y: H * 0.35,
                w: trunkW,
                h: trunkH,
            };

            const children = (root.children || []).map(id => byId[id]).filter(Boolean);
            children.forEach((child, ci) => {
                // Canopy (node/tree) positioned around trunk top
                const angle = -Math.PI / 2 + (ci - (children.length - 1) / 2) * 0.7;
                const branchLen = 40 + ((child.metrics || {}).cpu || 50) / 100 * 30;
                const bx = tx + Math.cos(angle) * branchLen;
                const by = H * 0.35 + Math.sin(angle) * branchLen;
                const canopySize = 25 + ((child.metrics || {}).mem || 50) / 100 * 20;
                layout[child.id] = {
                    x: bx - canopySize / 2,
                    y: by - canopySize / 2,
                    w: canopySize,
                    h: canopySize,
                };

                const grandchildren = (child.children || []).map(id => byId[id]).filter(Boolean);
                grandchildren.forEach((gc, gi) => {
                    // Leaf clusters (container) around canopy
                    const subAngle = angle + (gi - (grandchildren.length - 1) / 2) * 0.4;
                    const subLen = 15 + gi * 5;
                    const sx = bx + Math.cos(subAngle) * subLen;
                    const sy = by + Math.sin(subAngle) * subLen;
                    const leafSize = 8 + ((gc.metrics || {}).cpu || 30) / 100 * 6;
                    layout[gc.id] = {
                        x: sx - leafSize / 2,
                        y: sy - leafSize / 2,
                        w: leafSize,
                        h: leafSize,
                    };
                });
            });
        });
        return layout;
    },

    render(ctx, entities, layout, W, H, COLORS) {
        // Init scene
        if (!_forestState.initialized || _forestState.lastW !== W || _forestState.lastH !== H) {
            _forestInitScene(W, H);
        }
        const now = performance.now() / 1000 - _forestState.startTime;

        // Layer 0: Sky gradient + sun + stars
        _forestDrawSky(ctx, W, H, now);

        // Layer 1: Distant tree silhouettes
        _forestDrawDistantTrees(ctx, W, H);

        // Layer 2: Ground with soil, grass, rocks, stream
        _forestDrawGround(ctx, W, H, now);

        // Layer 3: Trees — trunks (clusters)
        entities.forEach(entity => {
            const pos = layout[entity.id];
            if (!pos || entity.type !== 'cluster') return;
            _forestDrawTree(ctx, entity, pos, now, layout);
        });

        // Layer 3b: Canopies (nodes)
        entities.forEach(entity => {
            const pos = layout[entity.id];
            if (!pos || entity.type !== 'node') return;
            _forestDrawCanopy(ctx, entity, pos, now, layout);
        });

        // Layer 3c: Leaf clusters (containers)
        entities.forEach(entity => {
            const pos = layout[entity.id];
            if (!pos || entity.type !== 'container') return;
            _forestDrawLeafCluster(ctx, entity, pos, now);
        });

        // Layer 4: Undergrowth
        _forestDrawUndergrowth(ctx, W, H, now);

        // Layer 4b: Fireflies
        _forestDrawFireflies(ctx, W, H, now);

        // Layer 4c: Falling petals
        _forestDrawPetals(ctx, W, H, now);

        // Layer 5: Labels
        entities.forEach(entity => {
            const pos = layout[entity.id];
            if (!pos) return;
            if (entity.type === 'cluster') {
                // Grove label
                ctx.fillStyle = 'rgba(255,255,220,0.9)';
                ctx.font = 'bold 11px system-ui, sans-serif';
                ctx.fillText(entity.name || '', pos.x - 10, pos.y - 5);
            } else if (entity.type === 'node') {
                // Tree label
                ctx.fillStyle = 'rgba(230,255,230,0.8)';
                ctx.font = '9px system-ui, sans-serif';
                ctx.fillText((entity.name || '').slice(0, 12), pos.x - 3, pos.y - 3);
            }
        });
    }
};


// Traffic Light metaphor - Urban intersection with signal colors
metaphorRenderers.traffic_light = {
    computeLayout(entities, W, H) {
        const layout = {};
        const byId = {};
        entities.forEach(e => byId[e.id] = e);
        const roots = entities.filter(e => !e.parent);

        const intersectionW = W / Math.max(roots.length, 1);
        roots.forEach((root, i) => {
            const ix = i * intersectionW;
            layout[root.id] = { x: ix, y: 0, w: intersectionW, h: H };

            const children = (root.children || []).map(id => byId[id]).filter(Boolean);
            if (!children.length) return;
            const laneW = (intersectionW - 20) / children.length;

            children.forEach((child, li) => {
                const lx = ix + 10 + li * laneW;
                layout[child.id] = { x: lx, y: 10, w: laneW - 4, h: H - 20 };

                const grandchildren = (child.children || []).map(id => byId[id]).filter(Boolean);
                if (!grandchildren.length) return;

                const lightH = Math.min(80, (H - 40) / grandchildren.length);
                grandchildren.forEach((gc, gi) => {
                    const cpu = (gc.metrics || {}).cpu || 50;
                    const lightW = 20 + (laneW - 30) * (cpu / 100);
                    const gx = lx + (laneW - lightW) / 2;
                    const gy = 20 + gi * lightH;
                    layout[gc.id] = { x: gx, y: gy, w: lightW, h: lightH - 8 };
                });
            });
        });
        return layout;
    },

    render(ctx, entities, layout, W, H, COLORS) {
        ctx.fillStyle = '#1e1e1e';
        ctx.fillRect(0, 0, W, H);

        const TL_COLORS = {
            healthy: '#22c55e', running: '#22c55e', idle: '#eab308',
            warning: '#eab308', degraded: '#f97316', critical: '#ef4444',
            stopped: '#6b7280', pending: '#a78bfa', scaling: '#06b6d4', unknown: '#4b5563',
        };

        entities.forEach(entity => {
            const pos = layout[entity.id];
            if (!pos) return;
            const color = TL_COLORS[entity.state] || TL_COLORS.unknown;

            if (entity.type === 'cluster') {
                ctx.fillStyle = '#252525';
                ctx.fillRect(pos.x + 2, pos.y + 2, pos.w - 4, pos.h - 4);
                ctx.fillStyle = '#fbbf24';
                ctx.fillRect(pos.x + pos.w / 2 - 1, pos.y, 2, pos.h);
                ctx.fillStyle = '#9ca3af';
                ctx.font = "bold 13px monospace";
                ctx.fillText(entity.name || '', pos.x + 8, pos.y + 18);
            } else if (entity.type === 'node') {
                ctx.fillStyle = '#2a2a2a';
                ctx.fillRect(pos.x, pos.y, pos.w, pos.h);
                ctx.fillStyle = '#fbbf24';
                let dy = pos.y + 10;
                while (dy < pos.y + pos.h - 10) {
                    ctx.fillRect(pos.x + pos.w / 2 - 1, dy, 2, 8);
                    dy += 16;
                }
                ctx.fillStyle = '#6b7280';
                ctx.font = "10px monospace";
                ctx.fillText((entity.name || '').slice(0, 16), pos.x + 4, pos.y + 14);
            } else if (entity.type === 'service') {
                ctx.fillStyle = '#111827';
                ctx.fillRect(pos.x, pos.y, pos.w, pos.h);
                ctx.strokeStyle = '#374151';
                ctx.lineWidth = 2;
                ctx.strokeRect(pos.x, pos.y, pos.w, pos.h);
                const cx = pos.x + pos.w / 2;
                const cy = pos.y + pos.h / 2;
                const radius = Math.min(pos.w, pos.h) / 3;
                ctx.beginPath();
                ctx.arc(cx, cy, radius, 0, Math.PI * 2);
                ctx.fillStyle = color;
                ctx.fill();
                ctx.shadowBlur = 8;
                ctx.shadowColor = color;
                ctx.fill();
                ctx.shadowBlur = 0;
                ctx.fillStyle = '#d1d5db';
                ctx.font = "9px monospace";
                ctx.fillText((entity.name || '').slice(0, 10), pos.x + 2, pos.y + pos.h + 12);
            }
        });
    }
};

// Space Station metaphor - Deep space with orbital layout
metaphorRenderers.space = {
    computeLayout(entities, W, H) {
        const layout = {};
        const cx = W / 2;
        const cy = H / 2;
        const roots = entities.filter(e => !e.parent);
        const byId = {};
        entities.forEach(e => byId[e.id] = e);

        roots.forEach((root, i) => {
            const orbitR = 80 + i * 90;
            const angle = (i / Math.max(roots.length, 1)) * Math.PI * 2;
            const px = cx + Math.cos(angle) * orbitR;
            const py = cy + Math.sin(angle) * orbitR;
            layout[root.id] = { x: px - 20, y: py - 20, w: 40, h: 40 };

            const children = (root.children || []).map(id => byId[id]).filter(Boolean);
            children.forEach((child, ci) => {
                const childAngle = angle + (ci / Math.max(children.length, 1)) * Math.PI * 0.5;
                const childR = 30;
                const sx = px + Math.cos(childAngle) * childR;
                const sy = py + Math.sin(childAngle) * childR;
                const size = 24;
                layout[child.id] = { x: sx - size/2, y: sy - size/2, w: size, h: size };

                const grandchildren = (child.children || []).map(id => byId[id]).filter(Boolean);
                grandchildren.forEach((gc, gi) => {
                    const subAngle = childAngle + (gi / Math.max(grandchildren.length, 1)) * Math.PI * 0.3;
                    const subR = 18;
                    const gx = sx + Math.cos(subAngle) * subR;
                    const gy = sy + Math.sin(subAngle) * subR;
                    const ss = 14;
                    layout[gc.id] = { x: gx - ss/2, y: gy - ss/2, w: ss, h: ss };
                });
            });
        });
        return layout;
    },

    render(ctx, entities, layout, W, H, COLORS) {
        const gradient = ctx.createLinearGradient(0, 0, 0, H);
        gradient.addColorStop(0, '#000011');
        gradient.addColorStop(1, '#0a0a1a');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, W, H);

        const now = performance.now() / 1000;
        for (let i = 0; i < 100; i++) {
            const x = (i * 137.5) % W;
            const y = (i * 97.3) % H;
            const twinkle = 0.3 + 0.7 * Math.abs(Math.sin(now * 0.5 + i));
            ctx.globalAlpha = twinkle;
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(x, y, 1, 1);
        }
        ctx.globalAlpha = 1.0;

        const cx = W / 2;
        const cy = H / 2;
        ctx.beginPath();
        ctx.arc(cx, cy, 25, 0, Math.PI * 2);
        ctx.fillStyle = '#fbbf24';
        ctx.fill();
        ctx.shadowBlur = 12;
        ctx.shadowColor = '#fbbf24';
        ctx.fill();
        ctx.shadowBlur = 0;

        const roots = entities.filter(e => !e.parent);
        roots.forEach((root, i) => {
            const orbitR = 80 + i * 90;
            ctx.beginPath();
            ctx.arc(cx, cy, orbitR, 0, Math.PI * 2);
            ctx.strokeStyle = 'rgba(96, 165, 250, 0.2)';
            ctx.lineWidth = 1;
            ctx.stroke();
        });

        entities.forEach(entity => {
            const pos = layout[entity.id];
            if (!pos) return;
            const color = COLORS[entity.state] || COLORS.unknown;
            const ecx = pos.x + pos.w / 2;
            const ecy = pos.y + pos.h / 2;
            const r = pos.w / 2;

            ctx.beginPath();
            ctx.arc(ecx, ecy, r, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();
            ctx.shadowBlur = 6;
            ctx.shadowColor = color;
            ctx.fill();
            ctx.shadowBlur = 0;

            ctx.fillStyle = '#e5e7eb';
            ctx.font = '9px monospace';
            ctx.fillText((entity.name || '').slice(0, 10), pos.x, pos.y + pos.h + 12);
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
            _ensureAnimLoop();
            // Refresh detail panel if an entity is selected (real-time update)
            if (selectedEntity) {
                const updated = entities.find(en => en.id === selectedEntity.id);
                if (updated) {
                    selectedEntity = updated;
                    showDetailPanel(updated);
                } else {
                    selectedEntity = null;
                    showDetailPlaceholder();
                }
            }
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
let _animFrameId = null;
let _lastAnimTime = 0;

function _animLoop(ts) {
    _animFrameId = requestAnimationFrame(_animLoop);
    // Throttle to ~30fps for city animation
    if (ts - _lastAnimTime < 33) return;
    _lastAnimTime = ts;
    
    // Smooth zoom/pan animation
    if (animatingView && !isPanning) {
        const epsilon = 0.001;
        const dz = targetZoom - zoom;
        const dx = targetPanX - panX;
        const dy = targetPanY - panY;
        
        if (Math.abs(dz) > epsilon || Math.abs(dx) > epsilon || Math.abs(dy) > epsilon) {
            // Lerp toward targets
            zoom += dz * LERP_SPEED;
            panX += dx * LERP_SPEED;
            panY += dy * LERP_SPEED;
        } else {
            // Snap to target
            zoom = targetZoom;
            panX = targetPanX;
            panY = targetPanY;
            animatingView = false;
        }
    }
    
    // Always render when animating or when city needs animation frames
    const needsRender = animatingView || isPanning || (currentMetaphor === 'city' && entities.length);
    if (needsRender) {
        render();
    }
}
function _ensureAnimLoop() {
    if (!_animFrameId) _animFrameId = requestAnimationFrame(_animLoop);
}

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
    
    // Sync animation targets to new position
    targetPanX = panX;
    targetPanY = panY;
    targetZoom = zoom;
    
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
        const dx = mouseX - panStartX;
        const dy = mouseY - panStartY;
        // Mark as dragged if moved more than 3 pixels
        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
            hasDragged = true;
        }
        panX = panOffsetX + dx;
        panY = panOffsetY + dy;
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
    canvas.style.cursor = hoveredEntity ? 'pointer' : 'grab';
    if (hoveredEntity !== prevHover) {
        render();
    }
});

canvas.addEventListener('mousedown', (e) => {
    if (e.button === 0) { // Left mouse button
        isPanning = true;
        hasDragged = false;
        mouseDownX = mouseX;
        mouseDownY = mouseY;
        panStartX = mouseX;
        panStartY = mouseY;
        panOffsetX = panX;
        panOffsetY = panY;
        // Cancel any ongoing animation and sync targets to current position
        animatingView = false;
        targetZoom = zoom;
        targetPanX = panX;
        targetPanY = panY;
        canvas.style.cursor = 'grabbing';
        e.preventDefault();
    } else if (e.button === 1) { // Middle mouse button
        isPanning = true;
        hasDragged = false;
        panStartX = mouseX;
        panStartY = mouseY;
        panOffsetX = panX;
        panOffsetY = panY;
        // Cancel any ongoing animation and sync targets to current position
        animatingView = false;
        targetZoom = zoom;
        targetPanX = panX;
        targetPanY = panY;
        canvas.style.cursor = 'grabbing';
        e.preventDefault();
    }
});

canvas.addEventListener('mouseup', (e) => {
    if (isPanning) {
        isPanning = false;
        // Sync animation targets to new position after drag
        targetZoom = zoom;
        targetPanX = panX;
        targetPanY = panY;
        canvas.style.cursor = hoveredEntity ? 'pointer' : 'grab';
    }
});

canvas.addEventListener('mouseleave', (e) => {
    if (isPanning) {
        isPanning = false;
        canvas.style.cursor = 'grab';
    }
});

canvas.addEventListener('click', (e) => {
    // Ignore if user was dragging
    if (hasDragged) return;
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
    const newZoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, zoom * delta));

    const rect = canvas.getBoundingClientRect();
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;

    // Snap current values first so we compute from the live state, not stale targets
    const baseZoom = zoom;
    const basePanX = panX;
    const basePanY = panY;

    // Calculate new pan to keep cursor position stable
    const newPanX = cx - (cx - basePanX) * (newZoom / baseZoom);
    const newPanY = cy - (cy - basePanY) * (newZoom / baseZoom);

    // Animate to new values
    targetZoom = newZoom;
    targetPanX = newPanX;
    targetPanY = newPanY;
    animatingView = true;
}, { passive: false });

// ============================================================
// Zoom controls
// ============================================================
document.getElementById('zoom-in').addEventListener('click', () => {
    targetZoom = Math.min(ZOOM_MAX, zoom * 1.25);
    // Zoom centered on canvas center
    const W = canvas.width / DPR;
    const H = canvas.height / DPR;
    const cx = W / 2;
    const cy = H / 2;
    targetPanX = cx - (cx - panX) * (targetZoom / zoom);
    targetPanY = cy - (cy - panY) * (targetZoom / zoom);
    animatingView = true;
});

document.getElementById('zoom-out').addEventListener('click', () => {
    targetZoom = Math.max(ZOOM_MIN, zoom * 0.8);
    // Zoom centered on canvas center
    const W = canvas.width / DPR;
    const H = canvas.height / DPR;
    const cx = W / 2;
    const cy = H / 2;
    targetPanX = cx - (cx - panX) * (targetZoom / zoom);
    targetPanY = cy - (cy - panY) * (targetZoom / zoom);
    animatingView = true;
});

document.getElementById('zoom-reset').addEventListener('click', () => {
    targetZoom = 1.0;
    targetPanX = 0;
    targetPanY = 0;
    animatingView = true;
});

// ============================================================
// Keyboard shortcuts
// ============================================================
document.addEventListener('keydown', (e) => {
    // Don't capture when typing in inputs
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;

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

        // +/- for zoom (animated, centered)
        case '+': case '=': {
            const W = canvas.width / DPR;
            const H = canvas.height / DPR;
            const cx = W / 2;
            const cy = H / 2;
            targetZoom = Math.min(ZOOM_MAX, zoom * 1.25);
            targetPanX = cx - (cx - panX) * (targetZoom / zoom);
            targetPanY = cy - (cy - panY) * (targetZoom / zoom);
            animatingView = true;
            break;
        }
        case '-': case '_': {
            const W = canvas.width / DPR;
            const H = canvas.height / DPR;
            const cx = W / 2;
            const cy = H / 2;
            targetZoom = Math.max(ZOOM_MIN, zoom * 0.8);
            targetPanX = cx - (cx - panX) * (targetZoom / zoom);
            targetPanY = cy - (cy - panY) * (targetZoom / zoom);
            animatingView = true;
            break;
        }

        // Arrow keys for pan (animated)
        case 'ArrowLeft':
            targetPanX = panX + PAN_STEP;
            targetPanY = panY;
            targetZoom = zoom;
            animatingView = true;
            e.preventDefault();
            break;
        case 'ArrowRight':
            targetPanX = panX - PAN_STEP;
            targetPanY = panY;
            targetZoom = zoom;
            animatingView = true;
            e.preventDefault();
            break;
        case 'ArrowUp':
            targetPanX = panX;
            targetPanY = panY + PAN_STEP;
            targetZoom = zoom;
            animatingView = true;
            e.preventDefault();
            break;
        case 'ArrowDown':
            targetPanX = panX;
            targetPanY = panY - PAN_STEP;
            targetZoom = zoom;
            animatingView = true;
            e.preventDefault();
            break;

        // Escape: deselect / close detail panel
        case 'Escape':
            selectedEntity = null;
            hideDetailPanel();
            render();
            break;

        // 0 or Home: reset view (animated)
        case '0':
        case 'Home':
            targetZoom = 1.0;
            targetPanX = 0;
            targetPanY = 0;
            animatingView = true;
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

    // CPU usage with progress bar
    const m = entity.metrics || {};
    const cpu = m.cpu !== undefined ? m.cpu : m.cpu_pct;
    if (cpu !== undefined) {
        const cpuColor = cpu > 80 ? '#ef4444' : cpu > 60 ? '#fbbf24' : '#4ade80';
        html += `<div class="detail-row detail-progress">
            <span class="detail-key">CPU</span>
            <span class="detail-value">${cpu.toFixed(1)}%</span>
        </div>
        <div class="detail-progress-bar">
            <div class="detail-progress-fill" style="width:${cpu}%;background:${cpuColor};"></div>
        </div>`;
    }

    // Memory usage with progress bar
    const mem = m.mem !== undefined ? m.mem : m.mem_pct;
    if (mem !== undefined) {
        const memColor = mem > 80 ? '#ef4444' : mem > 60 ? '#fbbf24' : '#4ade80';
        html += `<div class="detail-row detail-progress">
            <span class="detail-key">Memory</span>
            <span class="detail-value">${mem.toFixed(1)}%</span>
        </div>
        <div class="detail-progress-bar">
            <div class="detail-progress-fill" style="width:${mem}%;background:${memColor};"></div>
        </div>`;
    }

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

    const metricKeys = Object.keys(m);
    const skipMetrics = ['cpu', 'cpu_pct', 'mem', 'mem_pct'];
    const otherMetrics = metricKeys.filter(k => !skipMetrics.includes(k));
    if (otherMetrics.length > 0) {
        html += `<div style="margin-top:8px;padding-top:8px;border-top:1px solid #374151;">
            <div style="font-weight:bold;font-size:11px;color:#9ca3af;margin-bottom:4px;">METRICS</div>`;
        otherMetrics.forEach(key => {
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

function showDetailPlaceholder() {
    const title = document.getElementById('detail-title');
    const body = document.getElementById('detail-body');
    title.textContent = 'Entity Details';
    body.innerHTML = '<div class="detail-placeholder">Click an entity for details</div>';
}

function hideDetailPanel() {
    showDetailPlaceholder();
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
showDetailPlaceholder();
