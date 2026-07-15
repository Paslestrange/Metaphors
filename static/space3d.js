// static/space3d.js - Three.js 3D Space Station Renderer
// Quality pass: matches city visual fidelity with atmospheric effects,
// full entity hierarchy, raycasting, detail panel integration, animations.
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import * as THREE from 'three';

(function() {
    'use strict';

    const STATE_COLORS = {
        healthy: 0x4ade80, running: 0x60a5fa, idle: 0x94a3b8,
        warning: 0xfbbf24, degraded: 0xf97316, critical: 0xef4444,
        stopped: 0x374151, pending: 0xa78bfa, scaling: 0x06b6d4, unknown: 0x6b7280,
    };

    const HULL_DARK = 0x1a1a2e;
    const HULL_MID  = 0x22223a;
    const HULL_ACCENT = 0x2a2a4e;
    const WINDOW_LIT = 0x44ccff;
    const WINDOW_WARM = 0xffdd88;
    const CONDUIT = 0x2255aa;
    const PANEL_SOLAR = 0x1a3a5c;
    const RING_METAL = 0x3a3a5e;

    let scene, camera, renderer, controls, clock;
    let stationGroup, hubMesh;
    let allInteractable = [];   // meshes for raycasting
    let entityMeshMap = new Map(); // entity.id -> mesh
    let starField, dustField, solarWind;
    let ambientLight, sunLight, rimLight;
    let animationId = null;
    let entities = [], entitiesById = {}, roots = [];
    let hoveredMesh = null, selectedMesh = null;
    let raycaster, mouse;
    let _lastRaycastTs = 0;
    const _RAYCAST_MS = 80;

    // ----------------------------------------------------------------
    // INIT
    // ----------------------------------------------------------------
    function initScene(container) {
        const W = container.clientWidth || 1200;
        const H = container.clientHeight || 800;

        scene = new THREE.Scene();
        scene.background = new THREE.Color(0x020010);
        scene.fog = new THREE.FogExp2(0x020010, 0.0008);

        camera = new THREE.PerspectiveCamera(60, W / H, 0.1, 1500);
        camera.position.set(40, 60, 120);
        camera.lookAt(0, 0, 0);

        renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(W, H);
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.1;
        container.appendChild(renderer.domElement);

        clock = new THREE.Clock();
        raycaster = new THREE.Raycaster();
        mouse = new THREE.Vector2(-999, -999);

        stationGroup = new THREE.Group();
        scene.add(stationGroup);

        setupLights();
        createDeepSpace();
        createNebula();
        createDistantPlanet();
        createSolarWind();

        if (OrbitControls) {
            controls = new OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;
            controls.minDistance = 30;
            controls.maxDistance = 350;
            controls.maxPolarAngle = Math.PI * 0.85;
        }

        setupInteraction(container);

        window.addEventListener('resize', () => {
            const w = container.clientWidth;
            const h = container.clientHeight;
            camera.aspect = w / h;
            camera.updateProjectionMatrix();
            renderer.setSize(w, h);
        });
    }

    // ----------------------------------------------------------------
    // LIGHTS
    // ----------------------------------------------------------------
    function setupLights() {
        ambientLight = new THREE.AmbientLight(0x222244, 0.4);
        scene.add(ambientLight);

        // Sun — key light, warm
        sunLight = new THREE.DirectionalLight(0xfff4e6, 1.2);
        sunLight.position.set(100, 80, 60);
        sunLight.castShadow = true;
        sunLight.shadow.camera.left = -100;
        sunLight.shadow.camera.right = 100;
        sunLight.shadow.camera.top = 100;
        sunLight.shadow.camera.bottom = -100;
        sunLight.shadow.camera.near = 0.1;
        sunLight.shadow.camera.far = 400;
        sunLight.shadow.mapSize.width = 2048;
        sunLight.shadow.mapSize.height = 2048;
        scene.add(sunLight);

        // Rim light — cool blue from opposite side
        rimLight = new THREE.DirectionalLight(0x4488ff, 0.4);
        rimLight.position.set(-80, 20, -60);
        scene.add(rimLight);

        // Hemisphere
        const hemi = new THREE.HemisphereLight(0x1a1a3e, 0x000005, 0.3);
        scene.add(hemi);
    }

    // ----------------------------------------------------------------
    // ATMOSPHERE — deep space
    // ----------------------------------------------------------------
    function createDeepSpace() {
        // Star field — 3000 stars in a sphere
        const count = 3000;
        const geo = new THREE.BufferGeometry();
        const pos = new Float32Array(count * 3);
        const col = new Float32Array(count * 3);
        const sizes = new Float32Array(count);

        for (let i = 0; i < count; i++) {
            const r = 400 + Math.random() * 400;
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(2 * Math.random() - 1);
            pos[i*3]   = r * Math.sin(phi) * Math.cos(theta);
            pos[i*3+1] = r * Math.sin(phi) * Math.sin(theta);
            pos[i*3+2] = r * Math.cos(phi);

            const b = 0.6 + Math.random() * 0.4;
            const tint = Math.random();
            col[i*3]   = b * (tint < 0.1 ? 1.0 : tint < 0.2 ? 0.8 : 0.95);
            col[i*3+1] = b * 0.95;
            col[i*3+2] = b * (tint > 0.8 ? 0.7 : 1.0);
            sizes[i] = 0.5 + Math.random() * 2.0;
        }

        geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
        geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
        geo.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

        const mat = new THREE.PointsMaterial({
            size: 1.5, vertexColors: true, sizeAttenuation: true,
            transparent: true, opacity: 0.9
        });
        starField = new THREE.Points(geo, mat);
        scene.add(starField);

        // Cosmic dust — 500 particles near station
        const dustGeo = new THREE.BufferGeometry();
        const dustPos = new Float32Array(500 * 3);
        for (let i = 0; i < 500; i++) {
            dustPos[i*3]   = (Math.random() - 0.5) * 300;
            dustPos[i*3+1] = (Math.random() - 0.5) * 200;
            dustPos[i*3+2] = (Math.random() - 0.5) * 300;
        }
        dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
        const dustMat = new THREE.PointsMaterial({
            color: 0x445566, size: 0.8, transparent: true, opacity: 0.25,
            sizeAttenuation: true
        });
        dustField = new THREE.Points(dustGeo, dustMat);
        scene.add(dustField);
    }

    // ----------------------------------------------------------------
    // ATMOSPHERE — nebula
    // ----------------------------------------------------------------
    function createNebula() {
        const geo = new THREE.SphereGeometry(350, 32, 32);
        const canvas = document.createElement('canvas');
        canvas.width = 1024; canvas.height = 512;
        const ctx = canvas.getContext('2d');

        // Paint nebula clouds
        ctx.fillStyle = '#020010';
        ctx.fillRect(0, 0, 1024, 512);

        // Purple cloud
        let g = ctx.createRadialGradient(300, 200, 0, 300, 200, 250);
        g.addColorStop(0, 'rgba(80, 30, 120, 0.3)');
        g.addColorStop(0.5, 'rgba(40, 15, 80, 0.15)');
        g.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = g; ctx.fillRect(0, 0, 1024, 512);

        // Blue cloud
        g = ctx.createRadialGradient(700, 300, 0, 700, 300, 200);
        g.addColorStop(0, 'rgba(20, 60, 140, 0.25)');
        g.addColorStop(0.6, 'rgba(10, 30, 80, 0.1)');
        g.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = g; ctx.fillRect(0, 0, 1024, 512);

        // Red accent
        g = ctx.createRadialGradient(150, 350, 0, 150, 350, 150);
        g.addColorStop(0, 'rgba(120, 30, 30, 0.15)');
        g.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = g; ctx.fillRect(0, 0, 1024, 512);

        const texture = new THREE.CanvasTexture(canvas);
        const mat = new THREE.MeshBasicMaterial({
            map: texture, transparent: true, opacity: 0.6, side: THREE.BackSide,
            depthWrite: false
        });
        const nebula = new THREE.Mesh(geo, mat);
        scene.add(nebula);
    }

    // ----------------------------------------------------------------
    // ATMOSPHERE — distant planet
    // ----------------------------------------------------------------
    function createDistantPlanet() {
        const canvas = document.createElement('canvas');
        canvas.width = 256; canvas.height = 128;
        const ctx = canvas.getContext('2d');
        // Earth-like bands
        const bands = [
            '#1a5276', '#2e86c1', '#85c1e9', '#27ae60', '#229954',
            '#1a5276', '#5dade2', '#aed6f1', '#27ae60', '#1a5276'
        ];
        const bandH = canvas.height / bands.length;
        bands.forEach((c, i) => {
            ctx.fillStyle = c;
            ctx.fillRect(0, i * bandH, canvas.width, bandH + 1);
        });
        // Add noise/clouds
        for (let i = 0; i < 200; i++) {
            ctx.fillStyle = `rgba(255,255,255,${Math.random()*0.15})`;
            const x = Math.random() * canvas.width;
            const y = Math.random() * canvas.height;
            ctx.beginPath();
            ctx.ellipse(x, y, 5 + Math.random()*15, 3 + Math.random()*5, 0, 0, Math.PI*2);
            ctx.fill();
        }
        const tex = new THREE.CanvasTexture(canvas);

        const geo = new THREE.SphereGeometry(30, 32, 32);
        const mat = new THREE.MeshStandardMaterial({
            map: tex, roughness: 0.8, metalness: 0.1
        });
        const planet = new THREE.Mesh(geo, mat);
        planet.position.set(-200, 40, -250);
        scene.add(planet);

        // Atmosphere glow
        const glowGeo = new THREE.SphereGeometry(33, 32, 32);
        const glowMat = new THREE.MeshBasicMaterial({
            color: 0x4488ff, transparent: true, opacity: 0.12, side: THREE.BackSide
        });
        const glow = new THREE.Mesh(glowGeo, glowMat);
        planet.add(glow);
    }

    // ----------------------------------------------------------------
    // ATMOSPHERE — solar wind particles
    // ----------------------------------------------------------------
    function createSolarWind() {
        const count = 300;
        const geo = new THREE.BufferGeometry();
        const pos = new Float32Array(count * 3);
        for (let i = 0; i < count; i++) {
            pos[i*3]   = (Math.random() - 0.5) * 400;
            pos[i*3+1] = (Math.random() - 0.5) * 300;
            pos[i*3+2] = (Math.random() - 0.5) * 400;
        }
        geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
        const mat = new THREE.PointsMaterial({
            color: 0xffddaa, size: 0.6, transparent: true, opacity: 0.3,
            sizeAttenuation: true, depthWrite: false
        });
        solarWind = new THREE.Points(geo, mat);
        scene.add(solarWind);
    }

    // ----------------------------------------------------------------
    // HULL TEXTURE — procedural panel lines
    // ----------------------------------------------------------------
    function createHullTexture(baseColor, lightColor) {
        const canvas = document.createElement('canvas');
        canvas.width = 128; canvas.height = 128;
        const ctx = canvas.getContext('2d');

        ctx.fillStyle = baseColor || '#1a1a2e';
        ctx.fillRect(0, 0, 128, 128);

        // Horizontal panel lines
        ctx.strokeStyle = lightColor || 'rgba(100,100,180,0.15)';
        ctx.lineWidth = 1;
        for (let y = 0; y < 128; y += 16) {
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(128, y); ctx.stroke();
        }
        // Vertical panel lines
        for (let x = 0; x < 128; x += 32) {
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, 128); ctx.stroke();
        }
        // Rivet dots
        ctx.fillStyle = lightColor || 'rgba(120,120,200,0.1)';
        for (let x = 0; x < 128; x += 32) {
            for (let y = 0; y < 128; y += 16) {
                ctx.beginPath();
                ctx.arc(x, y, 1.5, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        const tex = new THREE.CanvasTexture(canvas);
        tex.wrapS = THREE.RepeatWrapping;
        tex.wrapT = THREE.RepeatWrapping;
        return tex;
    }

    // ----------------------------------------------------------------
    // BUILD STATION — hub
    // ----------------------------------------------------------------
    function buildHub(entity) {
        const cpu = Math.max(0, Math.min(100, entity.metrics?.cpu || 50));
        const stateColor = STATE_COLORS[entity.state] || STATE_COLORS.unknown;
        const radius = 8 + (cpu / 100) * 5;
        const height = 18 + (cpu / 100) * 10;

        // Main cylinder
        const geo = new THREE.CylinderGeometry(radius, radius, height, 32);
        const hullTex = createHullTexture('#1a1a2e', 'rgba(80,120,220,0.15)');
        const mat = new THREE.MeshStandardMaterial({
            color: HULL_DARK, map: hullTex,
            emissive: stateColor, emissiveIntensity: 0.15,
            metalness: 0.85, roughness: 0.25
        });
        const hub = new THREE.Mesh(geo, mat);
        hub.position.set(0, 0, 0);
        hub.castShadow = true;
        hub.receiveShadow = true;
        hub.userData = { entity, type: 'hub' };
        stationGroup.add(hub);
        allInteractable.push(hub);
        entityMeshMap.set(entity.id, hub);
        hubMesh = hub;

        // Glowing ring around equator
        const ringGeo = new THREE.TorusGeometry(radius + 1.5, 0.4, 8, 48);
        const ringMat = new THREE.MeshBasicMaterial({
            color: stateColor, transparent: true, opacity: 0.7
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = Math.PI / 2;
        hub.add(ring);
        hub.userData._ring = ring;

        // Top antenna
        const antGeo = new THREE.CylinderGeometry(0.1, 0.1, 6, 6);
        const antMat = new THREE.MeshStandardMaterial({
            color: RING_METAL, metalness: 0.9, roughness: 0.2
        });
        const antenna = new THREE.Mesh(antGeo, antMat);
        antenna.position.set(0, height/2 + 3, 0);
        hub.add(antenna);

        // Dish
        const dishGeo = new THREE.SphereGeometry(2, 16, 8, 0, Math.PI * 2, 0, Math.PI * 0.4);
        const dishMat = new THREE.MeshStandardMaterial({
            color: 0x444466, metalness: 0.7, roughness: 0.3, side: THREE.DoubleSide
        });
        const dish = new THREE.Mesh(dishGeo, dishMat);
        dish.position.set(0, height/2 + 6, 0);
        dish.rotation.x = Math.PI;
        hub.add(dish);

        // Central point light
        const hubPtLight = new THREE.PointLight(stateColor, 1.5, 80);
        hubPtLight.position.set(0, 0, 0);
        hub.add(hubPtLight);
        hub.userData._pointLight = hubPtLight;

        // LED ring at top
        createLEDs(hub, entity, radius, height/2 - 1);

        return hub;
    }

    // ----------------------------------------------------------------
    // BUILD STATION — modules (nodes)
    // ----------------------------------------------------------------
    function buildModule(entity, index, total) {
        const cpu = Math.max(0, Math.min(100, entity.metrics?.cpu || 50));
        const mem = Math.max(0, Math.min(100, entity.metrics?.mem || 50));
        const state = entity.state || 'unknown';
        const stateColor = STATE_COLORS[state] || STATE_COLORS.unknown;

        const radius = 4 + (mem / 100) * 3;
        const height = 10 + (cpu / 100) * 8;

        // Module body
        const geo = new THREE.CylinderGeometry(radius, radius, height, 24);
        const hullTex = createHullTexture('#1e1e34', 'rgba(100,140,255,0.12)');
        const mat = new THREE.MeshStandardMaterial({
            color: HULL_MID, map: hullTex,
            emissive: stateColor, emissiveIntensity: 0.2,
            metalness: 0.8, roughness: 0.3
        });
        const module_ = new THREE.Mesh(geo, mat);
        module_.castShadow = true;
        module_.receiveShadow = true;
        module_.userData = { entity, type: 'module' };

        // Position radially
        const angle = (index / Math.max(total, 1)) * Math.PI * 2;
        const dist = 45 + (index % 2) * 10;
        const x = Math.cos(angle) * dist;
        const z = Math.sin(angle) * dist;
        const y = (Math.random() - 0.5) * 12;
        module_.position.set(x, y, z);

        stationGroup.add(module_);
        allInteractable.push(module_);
        entityMeshMap.set(entity.id, module_);

        // Corridor to hub
        buildCorridor({ x:0, y:0, z:0 }, { x, y, z });

        // Solar panels
        buildSolarPanels(module_, angle, radius);

        // Window strip
        buildWindowStrip(module_, radius, height, stateColor);

        // LED indicators
        createLEDs(module_, entity, radius, height/2 - 1);

        // Emergency light for critical
        if (state === 'critical') {
            const eLight = new THREE.PointLight(0xff1111, 1.5, 25);
            eLight.position.set(0, height/2 + 2, 0);
            module_.add(eLight);
            module_.userData._emergencyLight = eLight;
        }

        // Point light for healthy/running
        if (state === 'healthy' || state === 'running') {
            const ptLight = new THREE.PointLight(stateColor, 0.8, 35);
            ptLight.position.set(0, 0, radius + 2);
            module_.add(ptLight);
            module_.userData._pointLight = ptLight;
        }

        module_.userData._baseAngle = angle;
        module_.userData._dist = dist;
        module_.userData._baseY = y;

        return module_;
    }

    // ----------------------------------------------------------------
    // CORRIDOR — connecting tube between two points
    // ----------------------------------------------------------------
    function buildCorridor(from, to) {
        const dx = to.x - from.x, dy = to.y - from.y, dz = to.z - from.z;
        const length = Math.sqrt(dx*dx + dy*dy + dz*dz);

        const geo = new THREE.CylinderGeometry(0.6, 0.6, length, 8);
        const mat = new THREE.MeshStandardMaterial({
            color: HULL_ACCENT, metalness: 0.9, roughness: 0.2,
            emissive: CONDUIT, emissiveIntensity: 0.15
        });
        const corridor = new THREE.Mesh(geo, mat);

        corridor.position.set((from.x+to.x)/2, (from.y+to.y)/2, (from.z+to.z)/2);
        corridor.lookAt(new THREE.Vector3(to.x, to.y, to.z));
        corridor.rotateX(Math.PI / 2);
        corridor.castShadow = true;
        stationGroup.add(corridor);

        // Energy flow dots along corridor
        const dotCount = Math.floor(length / 5);
        for (let i = 0; i < dotCount; i++) {
            const t = (i + 0.5) / dotCount;
            const dotGeo = new THREE.SphereGeometry(0.15, 6, 6);
            const dotMat = new THREE.MeshBasicMaterial({
                color: CONDUIT, transparent: true, opacity: 0.6
            });
            const dot = new THREE.Mesh(dotGeo, dotMat);
            dot.position.set(
                from.x + (to.x - from.x) * t,
                from.y + (to.y - from.y) * t,
                from.z + (to.z - from.z) * t
            );
            stationGroup.add(dot);
        }
    }

    // ----------------------------------------------------------------
    // SOLAR PANELS
    // ----------------------------------------------------------------
    function buildSolarPanels(module_, angle, moduleRadius) {
        const canvas = document.createElement('canvas');
        canvas.width = 128; canvas.height = 64;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#0d2244';
        ctx.fillRect(0, 0, 128, 64);
        // Grid lines
        ctx.strokeStyle = '#1a4488';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 8; i++) {
            ctx.beginPath(); ctx.moveTo(i*16, 0); ctx.lineTo(i*16, 64); ctx.stroke();
        }
        for (let j = 0; j <= 4; j++) {
            ctx.beginPath(); ctx.moveTo(0, j*16); ctx.lineTo(128, j*16); ctx.stroke();
        }
        // Cell sheen
        for (let i = 0; i < 8; i++) {
            for (let j = 0; j < 4; j++) {
                if (Math.random() > 0.5) {
                    ctx.fillStyle = `rgba(40,120,220,${0.05 + Math.random()*0.1})`;
                    ctx.fillRect(i*16+1, j*16+1, 14, 14);
                }
            }
        }
        const tex = new THREE.CanvasTexture(canvas);

        const panelW = moduleRadius * 2.5;
        const panelH = moduleRadius * 1.2;

        for (let side = -1; side <= 1; side += 2) {
            // Arm
            const armGeo = new THREE.CylinderGeometry(0.15, 0.15, moduleRadius * 1.5, 6);
            const armMat = new THREE.MeshStandardMaterial({
                color: RING_METAL, metalness: 0.9, roughness: 0.2
            });
            const arm = new THREE.Mesh(armGeo, armMat);
            arm.rotation.z = Math.PI / 2;
            arm.position.set(side * (moduleRadius + moduleRadius * 0.75), 0, 0);
            module_.add(arm);

            // Panel
            const pGeo = new THREE.PlaneGeometry(panelW, panelH);
            const pMat = new THREE.MeshStandardMaterial({
                map: tex, metalness: 0.6, roughness: 0.4,
                emissive: 0x112244, emissiveIntensity: 0.1
            });
            const panel = new THREE.Mesh(pGeo, pMat);
            panel.position.set(side * (moduleRadius * 2.2), 0, 0);
            panel.rotation.y = Math.PI / 2;
            panel.castShadow = true;
            module_.add(panel);
        }
    }

    // ----------------------------------------------------------------
    // WINDOW STRIP — lit windows around module
    // ----------------------------------------------------------------
    function buildWindowStrip(module_, radius, height, stateColor) {
        const winCanvas = document.createElement('canvas');
        winCanvas.width = 256; winCanvas.height = 64;
        const ctx = winCanvas.getContext('2d');
        ctx.fillStyle = 'rgba(0,0,0,0)';
        ctx.clearRect(0, 0, 256, 64);

        const cols = 16; const rows = 4;
        const cw = 256 / cols, rh = 64 / rows;
        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++) {
                if (Math.random() > 0.35) {
                    const warm = Math.random() > 0.5;
                    ctx.fillStyle = warm ? 'rgba(255,220,120,0.8)' : 'rgba(100,200,255,0.7)';
                    ctx.fillRect(c * cw + 3, r * rh + 3, cw - 6, rh - 6);
                }
            }
        }
        const winTex = new THREE.CanvasTexture(winCanvas);

        // Ring of windows
        const winGeo = new THREE.CylinderGeometry(radius + 0.05, radius + 0.05, height * 0.5, 32, 1, true);
        const winMat = new THREE.MeshBasicMaterial({
            map: winTex, transparent: true, opacity: 0.7, side: THREE.DoubleSide,
            depthWrite: false
        });
        const winStrip = new THREE.Mesh(winGeo, winMat);
        module_.add(winStrip);
    }

    // ----------------------------------------------------------------
    // LED INDICATORS
    // ----------------------------------------------------------------
    function createLEDs(parent, entity, radius, yPos) {
        const state = entity.state || 'unknown';
        const ledDefs = [
            { color: 0x44ff44, active: (entity.metrics?.cpu || 0) > 5, label: 'PWR' },
            { color: 0x44aaff, active: (entity.metrics?.req_per_sec || 0) > 0, label: 'DATA' },
            { color: state !== 'critical' && state !== 'stopped' ? 0xffaa44 : 0x333344, active: state !== 'critical', label: 'ENV' },
        ];

        ledDefs.forEach((led, i) => {
            const geo = new THREE.SphereGeometry(0.25, 8, 8);
            const mat = new THREE.MeshBasicMaterial({
                color: led.active ? led.color : 0x222233
            });
            const ledMesh = new THREE.Mesh(geo, mat);
            const a = (i / ledDefs.length) * Math.PI * 2;
            ledMesh.position.set(Math.cos(a) * (radius + 0.5), yPos, Math.sin(a) * (radius + 0.5));
            parent.add(ledMesh);
        });
    }

    // ----------------------------------------------------------------
    // SERVICES (grandchildren) — docked vessels
    // ----------------------------------------------------------------
    function buildService(entity, parentModule) {
        const cpu = Math.max(0, Math.min(100, entity.metrics?.cpu || 50));
        const state = entity.state || 'unknown';
        const stateColor = STATE_COLORS[state] || STATE_COLORS.unknown;

        const radius = 1.5 + (cpu / 100) * 1.5;
        const geo = new THREE.CapsuleGeometry(radius, radius * 1.5, 8, 16);
        const mat = new THREE.MeshStandardMaterial({
            color: HULL_ACCENT,
            emissive: stateColor, emissiveIntensity: 0.3,
            metalness: 0.7, roughness: 0.35
        });
        const service = new THREE.Mesh(geo, mat);
        service.castShadow = true;
        service.userData = { entity, type: 'service' };

        // Position around parent
        const modulePos = parentModule.position;
        const offsetAngle = Math.random() * Math.PI * 2;
        const offsetDist = 10 + Math.random() * 5;
        const sx = modulePos.x + Math.cos(offsetAngle) * offsetDist;
        const sy = modulePos.y + (Math.random() - 0.5) * 6;
        const sz = modulePos.z + Math.sin(offsetAngle) * offsetDist;
        service.position.set(sx, sy, sz);

        stationGroup.add(service);
        allInteractable.push(service);
        entityMeshMap.set(entity.id, service);

        // Small conduit connecting to parent
        const tubeGeo = new THREE.CylinderGeometry(0.12, 0.12, offsetDist * 0.8, 6);
        const tubeMat = new THREE.MeshStandardMaterial({
            color: CONDUIT, emissive: CONDUIT, emissiveIntensity: 0.2,
            metalness: 0.9, roughness: 0.2
        });
        const tube = new THREE.Mesh(tubeGeo, tubeMat);
        tube.position.set((modulePos.x + sx)/2, (modulePos.y + sy)/2, (modulePos.z + sz)/2);
        tube.lookAt(new THREE.Vector3(sx, sy, sz));
        tube.rotateX(Math.PI / 2);
        stationGroup.add(tube);

        // Service point light
        if (state === 'healthy' || state === 'running') {
            const pt = new THREE.PointLight(stateColor, 0.4, 15);
            service.add(pt);
        }

        service.userData._parentModule = parentModule;
        return service;
    }

    // ----------------------------------------------------------------
    // DOCKING RINGS around modules
    // ----------------------------------------------------------------
    function buildDockingRing(module_, entity) {
        const childServices = (entity.children || []).map(id => entitiesById[id]).filter(Boolean);
        if (childServices.length === 0) return;

        const radius = 8;
        const ringGeo = new THREE.TorusGeometry(radius, 0.3, 8, 32);
        const ringMat = new THREE.MeshStandardMaterial({
            color: RING_METAL, metalness: 0.85, roughness: 0.2,
            emissive: 0x222244, emissiveIntensity: 0.1
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = Math.PI / 2;
        ring.position.copy(module_.position);
        stationGroup.add(ring);

        // Docking port markers
        childServices.forEach((svc, i) => {
            const a = (i / childServices.length) * Math.PI * 2;
            const px = Math.cos(a) * radius;
            const pz = Math.sin(a) * radius;
            const portGeo = new THREE.BoxGeometry(1, 0.5, 1);
            const portMat = new THREE.MeshBasicMaterial({
                color: 0x00ff88, transparent: true, opacity: 0.7
            });
            const port = new THREE.Mesh(portGeo, portMat);
            port.position.set(px, 0, pz);
            ring.add(port);
        });
    }

    // ----------------------------------------------------------------
    // CONTAINERS / PROCESSES — small objects at module base
    // ----------------------------------------------------------------
    function buildContainer(entity, parentService) {
        const state = entity.state || 'unknown';
        const stateColor = STATE_COLORS[state] || STATE_COLORS.unknown;
        const geo = new THREE.BoxGeometry(0.6, 0.6, 0.6);
        const mat = new THREE.MeshStandardMaterial({
            color: stateColor, emissive: stateColor, emissiveIntensity: 0.2,
            metalness: 0.5, roughness: 0.5
        });
        const container = new THREE.Mesh(geo, mat);
        container.userData = { entity, type: 'container' };

        const pPos = parentService.position;
        const a = Math.random() * Math.PI * 2;
        const r = 2 + Math.random();
        container.position.set(pPos.x + Math.cos(a)*r, pPos.y - 0.5, pPos.z + Math.sin(a)*r);
        stationGroup.add(container);
        allInteractable.push(container);
        entityMeshMap.set(entity.id, container);
        return container;
    }

    function buildProcess(entity, parentService) {
        const state = entity.state || 'unknown';
        const stateColor = STATE_COLORS[state] || STATE_COLORS.unknown;
        const geo = new THREE.SphereGeometry(0.3, 8, 8);
        const mat = new THREE.MeshBasicMaterial({
            color: stateColor, transparent: true, opacity: 0.8
        });
        const proc = new THREE.Mesh(geo, mat);
        proc.userData = { entity, type: 'process' };

        const pPos = parentService.position;
        const a = Math.random() * Math.PI * 2;
        const r = 2.5 + Math.random() * 0.5;
        proc.position.set(pPos.x + Math.cos(a)*r, pPos.y - 0.3, pPos.z + Math.sin(a)*r);
        stationGroup.add(proc);
        allInteractable.push(proc);
        entityMeshMap.set(entity.id, proc);
        return proc;
    }

    // ----------------------------------------------------------------
    // INTERACTION — hover + click
    // ----------------------------------------------------------------
    function setupInteraction(container) {
        const canvas = renderer.domElement;

        canvas.addEventListener('mousemove', (e) => {
            const now = performance.now();
            if (now - _lastRaycastTs < _RAYCAST_MS) return;
            _lastRaycastTs = now;

            const rect = canvas.getBoundingClientRect();
            mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

            raycaster.setFromCamera(mouse, camera);
            const hits = raycaster.intersectObjects(allInteractable, false);

            if (hits.length > 0) {
                const hit = hits[0].object;
                if (hit !== hoveredMesh) {
                    unhover();
                    hoveredMesh = hit;
                    hover(hit);
                }
                canvas.style.cursor = 'pointer';
            } else {
                unhover();
                canvas.style.cursor = 'grab';
            }
        });

        canvas.addEventListener('mouseleave', () => {
            unhover();
            canvas.style.cursor = 'grab';
        });

        canvas.addEventListener('click', (e) => {
            if (!hoveredMesh) {
                selectedMesh = null;
                if (window.hideDetailPanel) window.hideDetailPanel();
                return;
            }
            selectedMesh = hoveredMesh;
            const ent = hoveredMesh.userData.entity;
            if (ent && window.showDetailPanel) {
                window.showDetailPanel(ent);
            }
        });
    }

    function hover(mesh) {
        if (!mesh || !mesh.material) return;
        mesh.userData._origEmissiveIntensity = mesh.material.emissiveIntensity;
        mesh.material.emissiveIntensity = (mesh.material.emissiveIntensity || 0.2) * 1.8;
    }

    function unhover() {
        if (!hoveredMesh || !hoveredMesh.material) { hoveredMesh = null; return; }
        const orig = hoveredMesh.userData._origEmissiveIntensity;
        if (orig !== undefined) {
            hoveredMesh.material.emissiveIntensity = orig;
            delete hoveredMesh.userData._origEmissiveIntensity;
        }
        hoveredMesh = null;
    }

    // ----------------------------------------------------------------
    // SCENE UPDATE — rebuild from entity data
    // ----------------------------------------------------------------
    function updateScene(newEntities, layout) {
        entities = newEntities;
        entitiesById = {};
        entities.forEach(e => { entitiesById[e.id] = e; });

        // Clear existing station
        allInteractable.forEach(m => {
            if (m.parent) m.parent.remove(m);
            if (m.geometry) m.geometry.dispose();
            if (m.material) {
                if (m.material.map) m.material.map.dispose();
                m.material.dispose();
            }
        });
        // Remove non-interactable station parts
        while (stationGroup.children.length > 0) {
            const child = stationGroup.children[0];
            stationGroup.remove(child);
            if (child.geometry) child.geometry.dispose();
            if (child.material) {
                if (child.material.map) child.material.map.dispose();
                child.material.dispose();
            }
        }
        allInteractable = [];
        entityMeshMap.clear();
        hoveredMesh = null;
        selectedMesh = null;

        // Build hierarchy
        roots = entities.filter(e => !e.parent);

        roots.forEach(root => {
            if (root.type === 'cluster') {
                buildHub(root);
                const modules_ = (root.children || []).map(id => entitiesById[id]).filter(Boolean);

                modules_.forEach((mod, mi) => {
                    if (mod.type === 'node') {
                        const moduleMesh = buildModule(mod, mi, modules_.length);
                        buildDockingRing(moduleMesh, mod);

                        const svcs = (mod.children || []).map(id => entitiesById[id]).filter(Boolean);
                        svcs.forEach(svc => {
                            if (svc.type === 'service') {
                                const svcMesh = buildService(svc, moduleMesh);

                                // Containers
                                const containers_ = (svc.children || []).map(id => entitiesById[id]).filter(Boolean);
                                containers_.forEach(c => {
                                    if (c.type === 'container') {
                                        buildContainer(c, svcMesh);
                                    } else if (c.type === 'process') {
                                        buildProcess(c, svcMesh);
                                    }
                                });
                            } else if (svc.type === 'container') {
                                buildContainer(svc, moduleMesh);
                            } else if (svc.type === 'process') {
                                buildProcess(svc, moduleMesh);
                            }
                        });
                    }
                });
            }
        });
    }

    // ----------------------------------------------------------------
    // ANIMATION LOOP
    // ----------------------------------------------------------------
    function animate() {
        animationId = requestAnimationFrame(animate);
        const delta = clock.getDelta();
        const elapsed = clock.getElapsedTime();

        if (controls) controls.update();

        // Slow star rotation
        if (starField) starField.rotation.y += delta * 0.005;
        if (dustField) dustField.rotation.y -= delta * 0.003;

        // Solar wind drift
        if (solarWind) {
            const pos = solarWind.geometry.attributes.position.array;
            for (let i = 0; i < 300; i++) {
                pos[i*3] -= delta * 8;
                if (pos[i*3] < -200) pos[i*3] = 200;
            }
            solarWind.geometry.attributes.position.needsUpdate = true;
        }

        // Station slow rotation
        if (stationGroup) {
            stationGroup.rotation.y += delta * 0.02;
        }

        // Animate entity meshes
        entityMeshMap.forEach((mesh, id) => {
            if (mesh === hoveredMesh) return;
            const entity = mesh.userData.entity;
            if (!entity) return;
            const state = entity.state || 'unknown';

            if (state === 'critical') {
                const strobe = Math.sin(elapsed * 8) > 0 ? 0.8 : 0.1;
                mesh.material.emissiveIntensity = strobe;
            } else if (state === 'warning' || state === 'degraded') {
                mesh.material.emissiveIntensity = 0.2 + 0.3 * Math.abs(Math.sin(elapsed * 2));
            } else if (state === 'stopped') {
                mesh.material.emissiveIntensity = 0.03;
            } else if (state === 'pending') {
                mesh.material.emissiveIntensity = Math.random() > 0.5 ? 0.25 : 0.08;
            } else if (state === 'scaling') {
                const s = 1 + 0.05 * Math.sin(elapsed * 2);
                mesh.scale.y = s;
            } else {
                mesh.material.emissiveIntensity = 0.3;
            }

            // Emergency light pulse
            if (mesh.userData._emergencyLight) {
                mesh.userData._emergencyLight.intensity = 1.5 + Math.sin(elapsed * 8) * 1.0;
            }

            // Hub ring glow pulse
            if (mesh.userData._ring) {
                mesh.userData._ring.material.opacity = 0.5 + 0.3 * Math.sin(elapsed * 1.5);
            }

            // Hub point light pulse
            if (mesh.userData._pointLight) {
                mesh.userData._pointLight.intensity = 1.0 + 0.5 * Math.sin(elapsed * 1.2);
            }
        });

        renderer.render(scene, camera);
    }

    // ----------------------------------------------------------------
    // CLEANUP
    // ----------------------------------------------------------------
    function dispose() {
        if (animationId) cancelAnimationFrame(animationId);
        allInteractable.forEach(m => {
            if (m.geometry) m.geometry.dispose();
            if (m.material) {
                if (m.material.map) m.material.map.dispose();
                m.material.dispose();
            }
        });
        if (starField) { starField.geometry.dispose(); starField.material.dispose(); }
        if (dustField) { dustField.geometry.dispose(); dustField.material.dispose(); }
        if (solarWind) { solarWind.geometry.dispose(); solarWind.material.dispose(); }
        if (renderer && renderer.domElement && renderer.domElement.parentNode) {
            renderer.domElement.parentNode.removeChild(renderer.domElement);
        }
        if (renderer) renderer.dispose();
    }

    // ----------------------------------------------------------------
    // PUBLIC API
    // ----------------------------------------------------------------
    window.Space3D = {
        init: function(container) {
            initScene(container);
            animate();
        },
        update: function(ents, layout) {
            updateScene(ents, layout);
        },
        dispose: dispose,
    };
})();
