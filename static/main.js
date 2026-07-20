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

// Three.js integration
let threeRenderer = null;
let useThreeJS = false;

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


// Space Station metaphor - 3D Three.js renderer
metaphorRenderers.space = {
    _initialized: false,
    _container: null,
    
    computeLayout(entities, W, H) {
        return {};
    },

    render(ctx, entities, layout, W, H, COLORS) {
        // Clear the 2D canvas so the city doesn't show through
        ctx.clearRect(0, 0, W, H);
        
        // Ensure 2D canvas is hidden behind the 3D view
        const canvas2d = document.getElementById('canvas');
        if (canvas2d) canvas2d.style.display = 'none';
        
        // Initialize 3D renderer on first call
        if (!this._initialized) {
            const container = document.getElementById('space3d-container');
            if (container && window.Space3D) {
                this._container = container;
                // Make container fill the viewport
                container.style.position = 'absolute';
                container.style.top = '0';
                container.style.left = '0';
                container.style.width = '100%';
                container.style.height = '100%';
                container.style.zIndex = '5';
                container.style.display = 'block';
                
                // Make app container allow absolute children
                const app = document.getElementById('app');
                if (app) {
                    app.style.position = 'relative';
                    app.style.overflow = 'hidden';
                }
                
                window.Space3D.init(container);
                this._initialized = true;
            }
        }

        // Update 3D scene with new entity data
        if (this._initialized && window.Space3D) {
            window.Space3D.update(entities, layout);
        }
    }
};

// ============================================================
// Garden Metaphor — 3D-style garden with plants, terrain, lighting
// Mapping: Cluster=Garden Bed, Node=Planting Row, Service=Plant/Tree, Container=Branch
// ============================================================
const _gardenState = {
    initialized: false,
    lastW: 0,
    lastH: 0,
    startTime: performance.now() / 1000,
    stars: [],
    fireflies: [],
    butterflies: [],
    grassBlades: [],
    waterRipples: [],
    clouds: [],
    pebbles: [],
    flowers: [],
};

const GARDEN_COLORS = {
    healthy: '#4ade80', running: '#22c55e', warning: '#fbbf24',
    degraded: '#92400e', critical: '#8b4513', stopped: '#6b7280',
    idle: '#86efac', pending: '#a3e635', scaling: '#34d399', unknown: '#6b7280',
};

const GARDEN_SKY_DAY_TOP = '#87ceeb';
const GARDEN_SKY_DAY_BOTTOM = '#b0e0e6';
const GARDEN_SKY_NIGHT_TOP = '#1a0a2e';
const GARDEN_SKY_NIGHT_BOTTOM = '#2d1b4e';
const GARDEN_SOIL_DARK = '#3d2817';
const GARDEN_SOIL_MID = '#5c3d2e';
const GARDEN_SOIL_LIGHT = '#6b4c3b';
const GARDEN_GRASS = '#228b22';
const GARDEN_GRASS_LIGHT = '#32cd32';
const GARDEN_FENCE_POST = '#8B6914';
const GARDEN_FENCE_RAIL = '#A0824A';
const GARDEN_WATER = '#4488ff';
const GARDEN_FIREFLY = '#ffd700';
const GARDEN_PATH = '#c4a882';
const GARDEN_FLOWER_COLORS = ['#ff69b4', '#f472b6', '#fb923c', '#a78bfa', '#f87171', '#38bdf8', '#facc15'];
const GARDEN_BUTTERFLY_COLORS = ['#c084fc', '#fb7185', '#38bdf8', '#fbbf24', '#f472b6'];

function _gardenHash(s) {
    let h = 0;
    for (let i = 0; i < s.length; i++) { h = ((h << 5) - h + s.charCodeAt(i)) | 0; }
    return Math.abs(h);
}

function _gardenLerpColor(c1, c2, t) {
    t = Math.max(0, Math.min(1, t));
    const r1 = parseInt(c1.slice(1,3), 16), g1 = parseInt(c1.slice(3,5), 16), b1 = parseInt(c1.slice(5,7), 16);
    const r2 = parseInt(c2.slice(1,3), 16), g2 = parseInt(c2.slice(3,5), 16), b2 = parseInt(c2.slice(5,7), 16);
    const r = Math.round(r1 + (r2 - r1) * t);
    const g = Math.round(g1 + (g2 - g1) * t);
    const b = Math.round(b1 + (b2 - b1) * t);
    return `#${r.toString(16).padStart(2,'0')}${g.toString(16).padStart(2,'0')}${b.toString(16).padStart(2,'0')}`;
}

function _gardenGetTimeOfDay() {
    return (Date.now() / 1000 % 86400) / 86400.0;
}

function _gardenIsNight(tod) {
    return tod < 0.25 || tod > 0.833;
}

function _gardenSkyColors(tod) {
    if (tod < 0.25) return [GARDEN_SKY_NIGHT_TOP, GARDEN_SKY_NIGHT_BOTTOM];
    if (tod < 0.33) {
        const t = (tod - 0.25) / 0.08;
        return [_gardenLerpColor(GARDEN_SKY_NIGHT_TOP, '#ff7e5f', t), _gardenLerpColor(GARDEN_SKY_NIGHT_BOTTOM, '#feb47b', t)];
    }
    if (tod < 0.42) {
        const t = (tod - 0.33) / 0.09;
        return [_gardenLerpColor('#ff7e5f', GARDEN_SKY_DAY_TOP, t), _gardenLerpColor('#feb47b', GARDEN_SKY_DAY_BOTTOM, t)];
    }
    if (tod < 0.75) return [GARDEN_SKY_DAY_TOP, GARDEN_SKY_DAY_BOTTOM];
    if (tod < 0.833) {
        const t = (tod - 0.75) / 0.083;
        return [_gardenLerpColor(GARDEN_SKY_DAY_TOP, '#ff7e5f', t), _gardenLerpColor(GARDEN_SKY_DAY_BOTTOM, '#feb47b', t)];
    }
    const t = (tod - 0.833) / 0.167;
    return [_gardenLerpColor('#ff7e5f', GARDEN_SKY_NIGHT_TOP, t), _gardenLerpColor('#feb47b', GARDEN_SKY_NIGHT_BOTTOM, t)];
}

function _gardenSunPos(tod, W, H) {
    if (tod < 0.25 || tod > 0.833) return { x: -100, y: -100, r: 0 };
    const t = (tod - 0.25) / 0.583;
    const angle = Math.PI * t;
    const skyH = H * 0.35;
    const x = W * 0.1 + (W * 0.8) * t;
    const y = skyH - Math.sin(angle) * (skyH * 0.7) + skyH * 0.3;
    const r = 20 + 10 * Math.sin(angle);
    return { x, y, r };
}

function _gardenInitScene(W, H) {
    const rng = (seed) => { let s = seed; return () => { s = (s * 16807 + 0) % 2147483647; return s / 2147483647; }; };

    // Stars
    const r1 = rng(77777);
    _gardenState.stars = [];
    for (let i = 0; i < 50; i++) {
        _gardenState.stars.push({
            x: r1() * W, y: r1() * H * 0.3,
            size: 0.5 + r1() * 1.5, brightness: 0.3 + r1() * 0.7,
            twinkle: 0.5 + r1() * 2.5, phase: r1() * Math.PI * 2,
        });
    }

    // Fireflies
    const r2 = rng(88888);
    _gardenState.fireflies = [];
    for (let i = 0; i < 25; i++) {
        _gardenState.fireflies.push({
            x: r2() * W, y: H * 0.3 + r2() * H * 0.5,
            vx: (r2() - 0.5) * 12, vy: (r2() - 0.5) * 8,
            phase: r2() * Math.PI * 2, brightness: 0.4 + r2() * 0.6,
        });
    }

    // Butterflies
    const r3 = rng(99999);
    _gardenState.butterflies = [];
    for (let i = 0; i < 8; i++) {
        _gardenState.butterflies.push({
            x: r3() * W, y: H * 0.35 + r3() * H * 0.4,
            targetX: r3() * W, targetY: H * 0.35 + r3() * H * 0.4,
            color: GARDEN_BUTTERFLY_COLORS[Math.floor(r3() * GARDEN_BUTTERFLY_COLORS.length)],
            wingPhase: r3() * Math.PI * 2, speed: 0.3 + r3() * 0.5,
            moveTimer: r3() * 5,
        });
    }

    // Grass blades (foreground)
    const r4 = rng(11112);
    _gardenState.grassBlades = [];
    const groundY = H * 0.88;
    for (let i = 0; i < 120; i++) {
        _gardenState.grassBlades.push({
            x: r4() * W, y: groundY + r4() * (H - groundY) * 0.3,
            height: 5 + r4() * 12, phase: r4() * Math.PI * 2,
            shade: r4(),
        });
    }

    // Water ripples
    const r5 = rng(22223);
    _gardenState.waterRipples = [];
    for (let i = 0; i < 12; i++) {
        _gardenState.waterRipples.push({
            offset: r5(), speed: 0.03 + r5() * 0.05,
            amplitude: 1 + r5() * 2,
        });
    }

    // Clouds
    const r6 = rng(33334);
    _gardenState.clouds = [];
    for (let i = 0; i < 4; i++) {
        _gardenState.clouds.push({
            x: r6() * W, y: H * 0.05 + r6() * H * 0.15,
            w: 60 + r6() * 80, h: 15 + r6() * 15,
            speed: 2 + r6() * 4, alpha: 0.15 + r6() * 0.2,
        });
    }

    // Pebbles
    const r7 = rng(44445);
    _gardenState.pebbles = [];
    for (let i = 0; i < 40; i++) {
        _gardenState.pebbles.push({
            x: r7() * W, y: groundY + 5 + r7() * (H - groundY - 10),
            r: 1 + r7() * 2.5, shade: 0.3 + r7() * 0.4,
        });
    }

    // Scattered flowers (decorative)
    const r8 = rng(55556);
    _gardenState.flowers = [];
    for (let i = 0; i < 15; i++) {
        _gardenState.flowers.push({
            x: r8() * W, y: groundY - 2 + r8() * 8,
            color: GARDEN_FLOWER_COLORS[Math.floor(r8() * GARDEN_FLOWER_COLORS.length)],
            size: 2 + r8() * 3, phase: r8() * Math.PI * 2,
        });
    }

    _gardenState.initialized = true;
    _gardenState.lastW = W;
    _gardenState.lastH = H;
}

function _gardenDrawSky(ctx, W, H, now, tod) {
    const [skyTop, skyBottom] = _gardenSkyColors(tod);
    const skyH = H * 0.35;
    const grad = ctx.createLinearGradient(0, 0, 0, skyH);
    grad.addColorStop(0, skyTop);
    grad.addColorStop(1, skyBottom);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, skyH);

    // Fill below sky with a transition color until ground
    ctx.fillStyle = skyBottom;
    ctx.fillRect(0, skyH, W, H * 0.05);

    // Stars at night
    if (_gardenIsNight(tod)) {
        _gardenState.stars.forEach(s => {
            const alpha = s.brightness * (0.5 + 0.5 * Math.sin(now * s.twinkle + s.phase));
            ctx.globalAlpha = alpha;
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
            ctx.fill();
        });
        ctx.globalAlpha = 1.0;
    }

    // Clouds (daytime only)
    if (!_gardenIsNight(tod)) {
        _gardenState.clouds.forEach(cloud => {
            cloud.x += cloud.speed * 0.016;
            if (cloud.x > W + cloud.w) cloud.x = -cloud.w;
            ctx.globalAlpha = cloud.alpha;
            ctx.fillStyle = '#ffffff';
            // Fluffy cloud shape
            ctx.beginPath();
            ctx.ellipse(cloud.x, cloud.y, cloud.w * 0.4, cloud.h * 0.6, 0, 0, Math.PI * 2);
            ctx.fill();
            ctx.beginPath();
            ctx.ellipse(cloud.x - cloud.w * 0.25, cloud.y + 3, cloud.w * 0.3, cloud.h * 0.5, 0, 0, Math.PI * 2);
            ctx.fill();
            ctx.beginPath();
            ctx.ellipse(cloud.x + cloud.w * 0.25, cloud.y + 2, cloud.w * 0.35, cloud.h * 0.55, 0, 0, Math.PI * 2);
            ctx.fill();
        });
        ctx.globalAlpha = 1.0;
    }
}

function _gardenDrawSun(ctx, W, H, tod, entities) {
    const sun = _gardenSunPos(tod, W, H);
    if (sun.r <= 0) return;

    // Sun color based on cluster health
    const roots = entities.filter(e => !e.parent && e.type === 'cluster');
    let sunColor = '#ffd700';
    if (roots.length > 0) {
        const worst = roots.reduce((a, b) => {
            const pri = { healthy: 0, running: 0, idle: 1, warning: 2, degraded: 3, critical: 4, stopped: 5, unknown: 3 };
            return (pri[b.state] || 3) > (pri[a.state] || 3) ? b : a;
        });
        const stateSunColors = { healthy: '#ffd700', running: '#f59e0b', idle: '#fde68a', warning: '#f97316', degraded: '#ef4444', critical: '#991b1b', stopped: '#374151' };
        sunColor = stateSunColors[worst.state] || '#ffd700';
    }

    // Outer glow
    ctx.save();
    ctx.globalAlpha = 0.15;
    ctx.fillStyle = sunColor;
    ctx.beginPath();
    ctx.arc(sun.x, sun.y, sun.r + 25, 0, Math.PI * 2);
    ctx.fill();
    // Mid glow
    ctx.globalAlpha = 0.3;
    ctx.beginPath();
    ctx.arc(sun.x, sun.y, sun.r + 12, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // Sun body
    const sunGrad = ctx.createRadialGradient(sun.x, sun.y, 0, sun.x, sun.y, sun.r);
    sunGrad.addColorStop(0, '#fffde0');
    sunGrad.addColorStop(0.6, sunColor);
    sunGrad.addColorStop(1, sunColor);
    ctx.fillStyle = sunGrad;
    ctx.beginPath();
    ctx.arc(sun.x, sun.y, sun.r, 0, Math.PI * 2);
    ctx.fill();

    // Sun rays
    ctx.save();
    ctx.strokeStyle = sunColor;
    ctx.lineWidth = 1.5;
    ctx.globalAlpha = 0.4;
    for (let i = 0; i < 12; i++) {
        const angle = (Math.PI * 2 / 12) * i + Date.now() * 0.0001;
        const inner = sun.r + 4;
        const outer = sun.r + 14 + 4 * Math.sin(Date.now() * 0.003 + i);
        ctx.beginPath();
        ctx.moveTo(sun.x + Math.cos(angle) * inner, sun.y + Math.sin(angle) * inner);
        ctx.lineTo(sun.x + Math.cos(angle) * outer, sun.y + Math.sin(angle) * outer);
        ctx.stroke();
    }
    ctx.restore();
}

function _gardenDrawTerrain(ctx, W, H, now) {
    const groundY = H * 0.35;

    // Base grass gradient
    const grassGrad = ctx.createLinearGradient(0, groundY, 0, H);
    grassGrad.addColorStop(0, '#4a8c3f');
    grassGrad.addColorStop(0.05, '#3d7a32');
    grassGrad.addColorStop(0.15, '#2d5a1e');
    grassGrad.addColorStop(0.4, GARDEN_SOIL_DARK);
    grassGrad.addColorStop(1, '#2a1a0f');
    ctx.fillStyle = grassGrad;
    ctx.fillRect(0, groundY, W, H - groundY);

    // Noise displacement — rolling hills effect
    ctx.fillStyle = '#3d7a32';
    for (let x = 0; x < W; x += 4) {
        const hillH = 3 + Math.sin(x * 0.02) * 4 + Math.sin(x * 0.007) * 6;
        ctx.fillRect(x, groundY - hillH, 4, hillH);
    }

    // Grass texture top layer
    ctx.fillStyle = GARDEN_GRASS;
    for (let x = 0; x < W; x += 3) {
        const gh = 3 + Math.sin(x * 0.05) * 2 + Math.sin(x * 0.13) * 1.5;
        ctx.fillRect(x, groundY - gh, 2, gh);
        ctx.fillStyle = GARDEN_GRASS_LIGHT;
        ctx.fillRect(x + 1, groundY - gh + 1, 1, gh - 1);
        ctx.fillStyle = GARDEN_GRASS;
    }

    // Soil texture
    ctx.fillStyle = GARDEN_SOIL_MID;
    for (let x = 0; x < W; x += 12) {
        const py = groundY + (H - groundY) * 0.3 + Math.sin(x * 0.03) * 10;
        ctx.fillRect(x, py, 8, 2);
    }

    // Pebbles
    _gardenState.pebbles.forEach(p => {
        ctx.fillStyle = `rgba(${Math.round(140 * p.shade)},${Math.round(120 * p.shade)},${Math.round(100 * p.shade)},0.6)`;
        ctx.beginPath();
        ctx.ellipse(p.x, p.y, p.r, p.r * 0.7, 0, 0, Math.PI * 2);
        ctx.fill();
    });
}

function _gardenDrawPathways(ctx, entities, layout, W, H) {
    const roots = entities.filter(e => !e.parent && e.type === 'cluster');
    if (roots.length < 2) return;

    const gardenTop = H * 0.35;
    const gardenBottom = H * 0.88;

    for (let i = 0; i < roots.length - 1; i++) {
        const posA = layout[roots[i].id];
        const posB = layout[roots[i + 1].id];
        if (!posA || !posB) continue;

        const pathLeft = posA.x + posA.w;
        const pathRight = posB.x;
        const pathW = pathRight - pathLeft;
        if (pathW <= 0) continue;

        // Path fill
        ctx.fillStyle = GARDEN_PATH;
        ctx.fillRect(pathLeft, gardenTop, pathW, gardenBottom - gardenTop);

        // Path edges
        ctx.strokeStyle = '#a08060';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(pathLeft + 1, gardenTop);
        ctx.lineTo(pathLeft + 1, gardenBottom);
        ctx.moveTo(pathRight - 1, gardenTop);
        ctx.lineTo(pathRight - 1, gardenBottom);
        ctx.stroke();

        // Footprint texture
        ctx.fillStyle = '#b09870';
        for (let j = gardenTop; j < gardenBottom; j += 18) {
            const fx = pathLeft + pathW * 0.3 + ((j * 7) % (pathW * 0.4));
            ctx.beginPath();
            ctx.arc(fx, j, 1.5, 0, Math.PI * 2);
            ctx.fill();
        }
    }
}

function _gardenDrawBed(ctx, entity, pos, now) {
    const x = pos.x, y = pos.y, w = pos.w, h = pos.h;

    // Rich soil
    const soilGrad = ctx.createLinearGradient(x, y, x, y + h);
    soilGrad.addColorStop(0, '#5c3d2e');
    soilGrad.addColorStop(0.5, GARDEN_SOIL_DARK);
    soilGrad.addColorStop(1, '#2a1a0f');
    ctx.fillStyle = soilGrad;
    ctx.fillRect(x, y, w, h);

    // Soil strata lines
    ctx.fillStyle = GARDEN_SOIL_MID;
    for (let i = 0; i < h; i += 8) {
        ctx.fillRect(x + 2, y + i, w - 4, 2);
    }

    // Soil detail spots
    ctx.fillStyle = GARDEN_SOIL_LIGHT;
    const seed = _gardenHash(entity.id || 'bed');
    let s = seed;
    const nextR = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
    for (let i = 0; i < w; i += 10) {
        for (let j = 0; j < h; j += 12) {
            const dx = nextR() * (w - 8);
            const dy = nextR() * (h - 8);
            ctx.fillRect(x + 4 + dx, y + 4 + dy, 3, 2);
        }
    }

    // Wooden fence
    _gardenDrawFence(ctx, x, y, w, h);

    // Label sign
    const name = (entity.name || '').slice(0, 14);
    const signW = Math.min(name.length * 7 + 12, w - 10);
    ctx.fillStyle = '#a0824a';
    ctx.fillRect(x + 6, y + 4, signW, 16);
    ctx.strokeStyle = '#6b5030';
    ctx.lineWidth = 1;
    ctx.strokeRect(x + 6, y + 4, signW, 16);
    ctx.fillStyle = '#3f2010';
    ctx.font = "bold 10px Georgia, serif";
    ctx.fillText(name, x + 12, y + 16);
}

function _gardenDrawFence(ctx, x, y, w, h) {
    const postW = 4, postH = 10;

    // Posts
    const positions = [x, x + w / 2 - postW / 2, x + w - postW];
    positions.forEach(px => {
        ctx.fillStyle = GARDEN_FENCE_POST;
        ctx.fillRect(px, y - postH + 2, postW, postH + 4);
        ctx.fillStyle = GARDEN_FENCE_RAIL;
        ctx.fillRect(px - 1, y - postH, postW + 2, 3);
    });

    // Rails
    ctx.fillStyle = GARDEN_FENCE_RAIL;
    ctx.fillRect(x, y - 2, w, 2);
    ctx.fillRect(x, y + 4, w, 2);

    // Bottom fence
    const botY = y + h;
    positions.forEach(px => {
        ctx.fillStyle = GARDEN_FENCE_POST;
        ctx.fillRect(px, botY - 2, postW, postH);
        ctx.fillStyle = GARDEN_FENCE_RAIL;
        ctx.fillRect(px - 1, botY + postH - 4, postW + 2, 3);
    });
    ctx.fillStyle = GARDEN_FENCE_RAIL;
    ctx.fillRect(x, botY, w, 2);
    ctx.fillRect(x, botY + 5, w, 2);
}

function _gardenDrawPlant(ctx, entity, pos, now) {
    const state = entity.state || 'unknown';
    const cpu = (entity.metrics || {}).cpu || 30;
    const leafColor = GARDEN_COLORS[state] || GARDEN_COLORS.unknown;
    const x = pos.x + pos.w / 2;
    const bottom = pos.y + pos.h;
    const h = pos.h;
    const w = pos.w;
    const seed = _gardenHash(entity.id || '');

    // Determine plant type by hash
    const plantType = ['tree', 'flower', 'bush'][seed % 3];

    if (plantType === 'tree') {
        _gardenDrawTree(ctx, x, bottom, w, h, leafColor, state, cpu, seed, now);
    } else if (plantType === 'flower') {
        _gardenDrawFlower(ctx, x, bottom, w, h, leafColor, state, entity, seed, now);
    } else {
        _gardenDrawBush(ctx, x, bottom, w, h, leafColor, state, cpu, seed, now);
    }

    // Dew drops for idle
    if (state === 'idle') {
        ctx.save();
        ctx.globalAlpha = 0.6;
        const drops = [[x - 4, pos.y + h * 0.3, 2.5], [x + 5, pos.y + h * 0.5, 2], [x - 2, pos.y + h * 0.7, 1.8]];
        drops.forEach(([dx, dy, dr]) => {
            ctx.fillStyle = '#bae6fd';
            ctx.beginPath(); ctx.arc(dx, dy, dr, 0, Math.PI * 2); ctx.fill();
            ctx.globalAlpha = 0.8;
            ctx.fillStyle = '#ffffff';
            ctx.beginPath(); ctx.arc(dx - dr * 0.3, dy - dr * 0.3, dr * 0.3, 0, Math.PI * 2); ctx.fill();
            ctx.globalAlpha = 0.6;
        });
        ctx.restore();
    }

    // Weeds for critical/degraded
    if (state === 'critical' || state === 'degraded') {
        ctx.strokeStyle = '#4b5563';
        ctx.lineWidth = 1.5;
        const wx = pos.x + pos.w + 4;
        const wy = bottom;
        for (let j = 0; j < 3; j++) {
            const ox = j * 3;
            ctx.beginPath();
            ctx.moveTo(wx + ox, wy);
            ctx.lineTo(wx + ox + 2, wy - 8 - j * 3);
            ctx.lineTo(wx + ox - 1, wy - 12 - j * 2);
            ctx.lineTo(wx + ox + 3, wy - 18 - j * 2);
            ctx.stroke();
        }
        ctx.fillStyle = '#6b7280';
        ctx.beginPath();
        ctx.arc(wx + 2, wy - 14, 2.5, 0, Math.PI * 2);
        ctx.fill();
    }

    // Label
    ctx.fillStyle = '#1a3a1a';
    ctx.font = "8px Georgia, serif";
    ctx.fillText((entity.name || '').slice(0, 12), pos.x, pos.y + pos.h + 10);
}

function _gardenDrawTree(ctx, x, bottom, w, h, leafColor, state, cpu, seed, now) {
    const trunkW = Math.max(3, w * 0.15);
    const trunkH = h * 0.45;
    const canopyR = Math.max(6, w * 0.4);

    // Shadow
    ctx.fillStyle = 'rgba(0,0,0,0.12)';
    ctx.beginPath();
    ctx.ellipse(x + 8, bottom + 3, canopyR * 1.2, 4, 0, 0, Math.PI * 2);
    ctx.fill();

    // Trunk
    const trunkGrad = ctx.createLinearGradient(x - trunkW / 2, bottom - trunkH, x + trunkW / 2, bottom - trunkH);
    trunkGrad.addColorStop(0, '#4a2e1f');
    trunkGrad.addColorStop(0.5, '#5c3d2e');
    trunkGrad.addColorStop(1, '#4a2e1f');
    ctx.fillStyle = trunkGrad;
    ctx.fillRect(x - trunkW / 2, bottom - trunkH, trunkW, trunkH);

    // Bark texture
    ctx.strokeStyle = '#3d2010';
    ctx.lineWidth = 0.5;
    for (let i = 0; i < 4; i++) {
        const ty = bottom - trunkH + 4 + i * (trunkH / 4);
        ctx.beginPath();
        ctx.moveTo(x - trunkW / 2 + 1, ty);
        ctx.lineTo(x + trunkW / 2 - 1, ty + 2);
        ctx.stroke();
    }

    // Canopy — layered circles for 3D feel
    const canopyY = bottom - trunkH - canopyR * 0.3;
    const sway = Math.sin(now * 0.8 + seed * 0.01) * 1.5;

    // Back canopy (darker — depth)
    const darkLeaf = _gardenLerpColor(leafColor, '#000000', 0.25);
    ctx.fillStyle = darkLeaf;
    ctx.beginPath();
    ctx.arc(x - canopyR * 0.3 + sway, canopyY + 2, canopyR * 0.7, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(x + canopyR * 0.3 + sway, canopyY + 3, canopyR * 0.65, 0, Math.PI * 2);
    ctx.fill();

    // Front canopy (main)
    ctx.fillStyle = leafColor;
    ctx.beginPath();
    ctx.arc(x + sway, canopyY - 2, canopyR * 0.8, 0, Math.PI * 2);
    ctx.fill();

    // Canopy highlight (sun-facing)
    ctx.save();
    ctx.globalAlpha = 0.3;
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(x - canopyR * 0.2 + sway, canopyY - canopyR * 0.3, canopyR * 0.25, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // Flowers on tree for active states
    if (state === 'healthy' || state === 'running' || state === 'scaling') {
        const flowerC = GARDEN_FLOWER_COLORS[seed % GARDEN_FLOWER_COLORS.length];
        for (let i = 0; i < 4; i++) {
            const angle = (Math.PI * 2 / 4) * i + 0.5;
            const fx = x + Math.cos(angle) * canopyR * 0.5 + sway;
            const fy = canopyY + Math.sin(angle) * canopyR * 0.4;
            ctx.fillStyle = flowerC;
            ctx.beginPath();
            ctx.arc(fx, fy, 2.5, 0, Math.PI * 2);
            ctx.fill();
            // Petal highlight
            ctx.fillStyle = '#ffffff';
            ctx.globalAlpha = 0.3;
            ctx.beginPath();
            ctx.arc(fx - 0.5, fy - 0.5, 1, 0, Math.PI * 2);
            ctx.fill();
            ctx.globalAlpha = 1.0;
        }
    }
}

function _gardenDrawFlower(ctx, x, bottom, w, h, leafColor, state, entity, seed, now) {
    const stemH = h * 0.7;
    const petalR = Math.max(4, w * 0.25);
    const sway = Math.sin(now * 1.5 + seed * 0.01) * 2;

    // Stem
    ctx.strokeStyle = '#166534';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x, bottom);
    ctx.quadraticCurveTo(x + sway * 0.5, bottom - stemH * 0.5, x + sway, bottom - stemH);
    ctx.stroke();

    // Leaves on stem
    ctx.fillStyle = leafColor;
    ctx.beginPath();
    ctx.ellipse(x - 4 + sway * 0.3, bottom - stemH * 0.4, 4, 2.5, -0.3, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(x + 5 + sway * 0.3, bottom - stemH * 0.6, 3.5, 2, 0.3, 0, Math.PI * 2);
    ctx.fill();

    // Flower head
    const flowerTop = bottom - stemH;
    if (state === 'healthy' || state === 'running' || state === 'scaling') {
        const flowerC = GARDEN_FLOWER_COLORS[seed % GARDEN_FLOWER_COLORS.length];
        const nPetals = 6;
        for (let i = 0; i < nPetals; i++) {
            const angle = (Math.PI * 2 / nPetals) * i + now * 0.1;
            const px = x + sway + Math.cos(angle) * petalR * 0.6;
            const py = flowerTop + Math.sin(angle) * petalR * 0.6;
            ctx.fillStyle = flowerC;
            ctx.beginPath();
            ctx.arc(px, py, petalR * 0.45, 0, Math.PI * 2);
            ctx.fill();
        }
        // Center
        ctx.fillStyle = '#facc15';
        ctx.beginPath();
        ctx.arc(x + sway, flowerTop, petalR * 0.3, 0, Math.PI * 2);
        ctx.fill();
        // Center highlight
        ctx.fillStyle = '#ffffff';
        ctx.globalAlpha = 0.4;
        ctx.beginPath();
        ctx.arc(x + sway - 1, flowerTop - 1, petalR * 0.12, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1.0;
    } else {
        // Closed/wilting
        ctx.fillStyle = leafColor;
        ctx.beginPath();
        ctx.arc(x + sway, flowerTop, petalR * 0.4, 0, Math.PI * 2);
        ctx.fill();
    }
}

function _gardenDrawBush(ctx, x, bottom, w, h, leafColor, state, cpu, seed, now) {
    const bushW = Math.max(8, w * 0.7);
    const bushH = Math.max(6, h * 0.5);
    const bushY = bottom - bushH;
    const sway = Math.sin(now * 0.6 + seed * 0.01) * 1;

    // Shadow
    ctx.fillStyle = 'rgba(0,0,0,0.1)';
    ctx.beginPath();
    ctx.ellipse(x, bottom + 2, bushW * 0.6, 3, 0, 0, Math.PI * 2);
    ctx.fill();

    // Bush body — overlapping circles for 3D
    const dark = _gardenLerpColor(leafColor, '#000000', 0.2);
    ctx.fillStyle = dark;
    ctx.beginPath();
    ctx.arc(x - bushW * 0.25 + sway, bushY + bushH * 0.3, bushW * 0.35, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(x + bushW * 0.25 + sway, bushY + bushH * 0.3, bushW * 0.35, 0, Math.PI * 2);
    ctx.fill();

    // Main body
    ctx.fillStyle = leafColor;
    ctx.beginPath();
    ctx.arc(x + sway, bushY + bushH * 0.2, bushW * 0.4, 0, Math.PI * 2);
    ctx.fill();

    // Top
    ctx.beginPath();
    ctx.arc(x + sway, bushY, bushW * 0.3, 0, Math.PI * 2);
    ctx.fill();

    // Highlight
    ctx.save();
    ctx.globalAlpha = 0.25;
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(x - bushW * 0.1 + sway, bushY - bushW * 0.1, bushW * 0.15, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // Small berries/flowers for active states
    if (state === 'healthy' || state === 'running') {
        const berryC = GARDEN_FLOWER_COLORS[seed % GARDEN_FLOWER_COLORS.length];
        for (let i = 0; i < 3; i++) {
            const bx = x + (i - 1) * bushW * 0.25 + sway;
            const by = bushY + bushH * 0.1 + Math.sin(i * 2) * 3;
            ctx.fillStyle = berryC;
            ctx.beginPath();
            ctx.arc(bx, by, 2, 0, Math.PI * 2);
            ctx.fill();
        }
    }
}

function _gardenDrawWater(ctx, W, H, now) {
    // Water feature — horizontal stream near bottom of garden area
    const waterY = H * 0.78;
    const waterH = 8;

    // Water body
    ctx.save();
    ctx.globalAlpha = 0.6;
    const waterGrad = ctx.createLinearGradient(0, waterY, 0, waterY + waterH);
    waterGrad.addColorStop(0, '#7dd3fc');
    waterGrad.addColorStop(0.5, GARDEN_WATER);
    waterGrad.addColorStop(1, '#2563eb');
    ctx.fillStyle = waterGrad;
    ctx.fillRect(0, waterY, W, waterH);

    // Animated ripple highlights
    ctx.globalAlpha = 0.4;
    ctx.fillStyle = '#bae6fd';
    _gardenState.waterRipples.forEach(rip => {
        const px = ((rip.offset + now * rip.speed) % 1) * W;
        const py = waterY + 2 + Math.sin(px * 0.03 + now * 1.5) * rip.amplitude;
        ctx.beginPath();
        ctx.ellipse(px, py, 4, 1.5, 0, 0, Math.PI * 2);
        ctx.fill();
    });

    // Sparkle
    ctx.globalAlpha = 0.5;
    ctx.fillStyle = '#ffffff';
    for (let x = 0; x < W; x += 25) {
        const sparkleX = x + (now * 15) % 25;
        const sparkleAlpha = 0.3 + 0.3 * Math.sin(now * 3 + sparkleX * 0.1);
        ctx.globalAlpha = sparkleAlpha;
        ctx.beginPath();
        ctx.arc(sparkleX, waterY + 3, 1, 0, Math.PI * 2);
        ctx.fill();
    }
    ctx.restore();
}

function _gardenDrawFireflies(ctx, W, H, now) {
    _gardenState.fireflies.forEach(ff => {
        ff.x += ff.vx * 0.016;
        ff.y += ff.vy * 0.016;
        ff.vx += (Math.sin(now + ff.phase) * 4 - ff.vx * 0.5) * 0.016;
        ff.vy += (Math.cos(now * 0.7 + ff.phase) * 3 - ff.vy * 0.5) * 0.016;
        if (ff.x < 0) ff.x = W;
        if (ff.x > W) ff.x = 0;
        if (ff.y < H * 0.2) ff.y = H * 0.7;
        if (ff.y > H * 0.85) ff.y = H * 0.3;

        const glow = ff.brightness * (0.5 + 0.5 * Math.sin(now * 3 + ff.phase));
        if (glow < 0.2) return;

        // Glow halo
        const grad = ctx.createRadialGradient(ff.x, ff.y, 0, ff.x, ff.y, 8);
        grad.addColorStop(0, `rgba(255,215,0,${glow * 0.5})`);
        grad.addColorStop(1, 'rgba(255,215,0,0)');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(ff.x, ff.y, 8, 0, Math.PI * 2);
        ctx.fill();

        // Core
        ctx.fillStyle = `rgba(255,255,180,${glow})`;
        ctx.beginPath();
        ctx.arc(ff.x, ff.y, 1.5, 0, Math.PI * 2);
        ctx.fill();
    });
}

function _gardenDrawButterflies(ctx, W, H, now) {
    _gardenState.butterflies.forEach(bf => {
        bf.moveTimer -= 0.016;
        if (bf.moveTimer <= 0) {
            bf.targetX = Math.random() * W;
            bf.targetY = H * 0.3 + Math.random() * H * 0.45;
            bf.moveTimer = 3 + Math.random() * 5;
        }
        // Smooth movement
        bf.x += (bf.targetX - bf.x) * bf.speed * 0.016;
        bf.y += (bf.targetY - bf.y) * bf.speed * 0.016;
        bf.wingPhase += 8 * 0.016;

        const wingAngle = Math.sin(bf.wingPhase) * 0.8;
        const wingSize = 5;

        ctx.save();
        ctx.translate(bf.x, bf.y);

        // Left wing
        ctx.fillStyle = bf.color;
        ctx.save();
        ctx.scale(Math.cos(wingAngle), 1);
        ctx.beginPath();
        ctx.ellipse(-2, 0, wingSize, wingSize * 0.6, -0.3, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();

        // Right wing
        ctx.save();
        ctx.scale(Math.cos(wingAngle + 0.5), 1);
        ctx.beginPath();
        ctx.ellipse(2, 0, wingSize, wingSize * 0.6, 0.3, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();

        // Body
        ctx.fillStyle = '#1a1a1a';
        ctx.fillRect(-0.5, -3, 1, 6);

        // Antennae
        ctx.strokeStyle = '#1a1a1a';
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.moveTo(0, -3);
        ctx.lineTo(-2, -6);
        ctx.moveTo(0, -3);
        ctx.lineTo(2, -6);
        ctx.stroke();

        ctx.restore();
    });
}

function _gardenDrawBranch(ctx, entity, pos, now) {
    const cx = pos.x + pos.w / 2;
    const cy = pos.y + pos.h / 2;
    const state = entity.state || 'unknown';
    const r = Math.max(3, pos.w / 2);

    let color = GARDEN_COLORS[state] || GARDEN_COLORS.unknown;
    const sway = Math.sin(now * 1.5 + _gardenHash(entity.id || '') * 0.01) * 1;

    // Small leaf cluster
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(cx + sway, cy, r, 0, Math.PI * 2);
    ctx.fill();

    // Leaf highlight
    ctx.fillStyle = 'rgba(255,255,255,0.15)';
    ctx.beginPath();
    ctx.arc(cx + sway - r * 0.3, cy - r * 0.3, r * 0.3, 0, Math.PI * 2);
    ctx.fill();
}

metaphorRenderers.garden = {
    computeLayout(entities, W, H) {
        const layout = {};
        const byId = {};
        entities.forEach(e => byId[e.id] = e);
        const roots = entities.filter(e => !e.parent);
        if (!roots.length) return layout;

        // Reserve top 25% for sky, bottom 12% for foreground grass
        const skyH = H * 0.25;
        const groundH = H * 0.12;
        const gardenTop = skyH;
        const gardenH = H - skyH - groundH;

        // Garden beds spread horizontally with pathway gaps
        const nRoots = Math.max(roots.length, 1);
        const pathwayW = 16;
        const bedGap = pathwayW + 8;
        const totalGap = bedGap * (nRoots + 1);
        const bedW = Math.max(40, (W - totalGap) / nRoots);

        roots.forEach((root, di) => {
            const bx = bedGap + di * (bedW + bedGap);
            const by = gardenTop;
            layout[root.id] = { x: bx, y: by, w: bedW, h: gardenH };

            // Planting rows (nodes) stack vertically
            const children = (root.children || []).map(id => byId[id]).filter(Boolean);
            const nChildren = Math.max(children.length, 1);
            const rowGap = 10;
            const rowH = (gardenH - rowGap * (nChildren + 1)) / Math.max(nChildren, 1);

            children.forEach((child, ri) => {
                const rx = bx + rowGap;
                const ry = by + rowGap + ri * (rowH + rowGap);
                const rw = bedW - 2 * rowGap;
                layout[child.id] = { x: rx, y: ry, w: rw, h: rowH };

                // Plants (services) spread along the row
                const grandchildren = (child.children || []).map(id => byId[id]).filter(Boolean);
                if (!grandchildren.length) return;
                const nGc = grandchildren.length;
                const plantGap = 8;
                const plantW = Math.max(12, (rw - plantGap * (nGc + 1)) / nGc);

                grandchildren.forEach((gc, gi) => {
                    const cpu = (gc.metrics || {}).cpu || 30;
                    const maxPh = rowH - 20;
                    const ph = Math.max(20, maxPh * (cpu / 100));
                    const px = rx + plantGap + gi * (plantW + plantGap);
                    const py = ry + rowH - ph;
                    layout[gc.id] = { x: px, y: py, w: plantW, h: ph };

                    // Containers (branches) as sub-elements
                    const greatGrandchildren = (gc.children || []).map(id => byId[id]).filter(Boolean);
                    if (!greatGrandchildren.length) return;
                    const nGgc = greatGrandchildren.length;
                    const branchH = ph / Math.max(nGgc, 1);
                    greatGrandchildren.forEach((ggc, bi) => {
                        const branchY = py + bi * branchH;
                        layout[ggc.id] = {
                            x: px + plantW * 0.2,
                            y: branchY,
                            w: plantW * 0.6,
                            h: branchH * 0.8,
                        };
                    });
                });
            });
        });
        return layout;
    },

    render(ctx, entities, layout, W, H, COLORS) {
        if (!_gardenState.initialized || _gardenState.lastW !== W || _gardenState.lastH !== H) {
            _gardenInitScene(W, H);
        }
        const now = performance.now() / 1000 - _gardenState.startTime;
        const tod = _gardenGetTimeOfDay();
        const night = _gardenIsNight(tod);

        // Layer 0: Sky gradient with clouds/stars
        _gardenDrawSky(ctx, W, H, now, tod);

        // Layer 1: Sun
        _gardenDrawSun(ctx, W, H, tod, entities);

        // Layer 2: Terrain (grass, soil, noise)
        _gardenDrawTerrain(ctx, W, H, now);

        // Layer 3: Pathways between beds
        _gardenDrawPathways(ctx, entities, layout, W, H);

        // Layer 4: Garden beds with fence and soil
        entities.forEach(e => {
            const pos = layout[e.id];
            if (!pos || e.type !== 'cluster') return;
            _gardenDrawBed(ctx, e, pos, now);
        });

        // Layer 5: Water feature
        _gardenDrawWater(ctx, W, H, now);

        // Layer 6: Plants (services) — trees, flowers, bushes
        entities.forEach(e => {
            const pos = layout[e.id];
            if (!pos || e.type !== 'service') return;
            _gardenDrawPlant(ctx, e, pos, now);
        });

        // Layer 7: Branches (containers)
        entities.forEach(e => {
            const pos = layout[e.id];
            if (!pos || e.type !== 'container') return;
            _gardenDrawBranch(ctx, e, pos, now);
        });

        // Layer 8: Foreground grass blades
        _gardenState.grassBlades.forEach(tuft => {
            const sway = Math.sin(now * 1.5 + tuft.phase) * 2;
            const col = tuft.shade > 0.5 ? GARDEN_GRASS : GARDEN_GRASS_LIGHT;
            ctx.strokeStyle = col;
            ctx.lineWidth = 1.2;
            ctx.beginPath();
            ctx.moveTo(tuft.x, tuft.y);
            ctx.quadraticCurveTo(tuft.x + sway, tuft.y - tuft.height * 0.6, tuft.x + sway * 1.5, tuft.y - tuft.height);
            ctx.stroke();
        });

        // Layer 9: Decorative flowers
        _gardenState.flowers.forEach(f => {
            const bob = Math.sin(now * 1.2 + f.phase) * 1;
            ctx.fillStyle = f.color;
            ctx.beginPath();
            ctx.arc(f.x, f.y + bob, f.size, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = '#facc15';
            ctx.beginPath();
            ctx.arc(f.x, f.y + bob, f.size * 0.35, 0, Math.PI * 2);
            ctx.fill();
        });

        // Layer 10: Butterflies
        _gardenDrawButterflies(ctx, W, H, now);

        // Layer 11: Fireflies at night
        if (night) {
            _gardenDrawFireflies(ctx, W, H, now);
        }
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
            if (useThreeJS && threeRenderer) threeRenderer.updateEntities(entities);
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

        // Toggle canvases for 3D metaphors
        const canvas2d = document.getElementById('canvas');
        const canvas3d = document.getElementById('canvas3d');
        const space3dContainer = document.getElementById('space3d-container');
        
        if (canvas2d) {
            // Hide 2D canvas for 3D metaphors
            if (newMetaphor === 'space' || newMetaphor === 'city3d') {
                canvas2d.style.display = 'none';
            } else {
                canvas2d.style.display = 'block';
            }
        }
        
        if (canvas3d) {
            if (newMetaphor === 'city3d') {
                canvas3d.style.display = 'block';
            } else {
                canvas3d.style.display = 'none';
            }
        }
        
        if (space3dContainer) {
            if (newMetaphor === 'space') {
                space3dContainer.style.display = 'block';
            } else {
                space3dContainer.style.display = 'none';
            }
        }

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
    if (useThreeJS) return;
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

    // Uptime display
    const uptime = m.uptime || m.uptime_hrs;
    if (uptime !== undefined) {
        let uptimeText;
        if (typeof uptime === 'string') {
            uptimeText = uptime; // Docker returns "Up 2 hours" format
        } else {
            // Numeric hours
            if (uptime < 1) {
                uptimeText = `${Math.round(uptime * 60)} min`;
            } else if (uptime < 24) {
                uptimeText = `${uptime.toFixed(1)} hrs`;
            } else {
                uptimeText = `${(uptime / 24).toFixed(1)} days`;
            }
        }
        html += `<div class="detail-row">
            <span class="detail-key">Uptime</span>
            <span class="detail-value">${uptimeText}</span>
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
    const skipMetrics = ['cpu', 'cpu_pct', 'mem', 'mem_pct', 'uptime', 'uptime_hrs'];
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

    // Logs link
    const logsLink = buildLogsLink(entity);
    if (logsLink) {
        html += `<div style="margin-top:12px;padding-top:8px;border-top:1px solid #374151;">
            <a href="${logsLink}" target="_blank" style="color:#60a5fa;text-decoration:none;font-size:11px;">
                📋 View Logs →
            </a>
        </div>`;
    }

    body.innerHTML = html;
    panel.classList.remove('hidden');
}

function buildLogsLink(entity) {
    const m = entity.metrics || {};
    const src = entity.source || '';

    // Docker containers — link to container logs endpoint
    if (src === 'docker' && (entity.type === 'container' || entity.id.startsWith('dctr-'))) {
        const containerId = entity.labels?.container_id || entity.id.replace('dctr-', '');
        return `/api/logs/docker/${containerId}`;
    }

    // Prometheus nodes — link to node logs endpoint
    if (src === 'prometheus' && entity.type === 'node') {
        const instance = entity.labels?.instance || entity.name;
        return `/api/logs/prometheus?instance=${encodeURIComponent(instance)}`;
    }

    // Process source — link to process logs
    if (src === 'processes' && entity.type === 'process') {
        return `/api/logs/process?name=${encodeURIComponent(entity.name)}`;
    }

    return null;
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
// Three.js integration
// ============================================================
function initThreeJS() {
    if (typeof CityRenderer3D !== 'undefined' && !threeRenderer) {
        const container = document.getElementById('canvas').parentElement;
        threeRenderer = new CityRenderer3D(container);
        threeRenderer.init();
        if (currentMetaphor === 'city') {
            useThreeJS = true;
            canvas.style.display = 'none';
            if (entities.length > 0) {
                threeRenderer.updateEntities(entities);
            }
        }
        console.log('Three.js renderer initialized');
    }
}

// Poll until the ES module loads (modules load async)
const _threeCheckInterval = setInterval(() => {
    if (typeof CityRenderer3D !== 'undefined') {
        clearInterval(_threeCheckInterval);
        initThreeJS();
    }
}, 100);

// Override switchMetaphor to toggle Three.js for city metaphor
const _origSwitchMetaphor = switchMetaphor;
switchMetaphor = function(newMetaphor) {
    _origSwitchMetaphor(newMetaphor);
    if (threeRenderer) {
        if (newMetaphor === 'city') {
            useThreeJS = true;
            canvas.style.display = 'none';
            threeRenderer.resize();
            if (entities.length > 0) {
                threeRenderer.updateEntities(entities);
            }
        } else {
            useThreeJS = false;
            canvas.style.display = 'block';
        }
    }
};

// ============================================================
// Init
// ============================================================
resize();
fetchMetaphors();
connect();
showDetailPlaceholder();
