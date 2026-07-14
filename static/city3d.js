// static/city3d.js — Three.js 3D City Metaphor Renderer
// Infrastructure as a 3D cyberpunk cityscape
// Mapping: Cluster=District, Node=Block, Service=Building
// Building height=CPU, width/depth=memory

/* global THREE */

const City3D = (function () {
  'use strict';

  // ── State → Color Map ──────────────────────────────────────────────
  const STATE_COLORS = {
    healthy:  0x4ade80,
    running:  0x60a5fa,
    warning:  0xfbbf24,
    critical: 0xef4444,
    stopped:  0x374151,
    idle:     0x94a3b8,
    degraded: 0xf97316,
    pending:  0xa78bfa,
    scaling:  0x06b6d4,
    unknown:  0x6b7280,
  };

  const NEON_GLOW = {
    healthy:  0x22ff88,
    running:  0x44aaff,
    warning:  0xffcc00,
    critical: 0xff2222,
    stopped:  0x555555,
    idle:     0x8899aa,
    degraded: 0xff8800,
    pending:  0xbb99ff,
    scaling:  0x00ddff,
    unknown:  0x778899,
  };

  const FOG_COLOR   = 0x0a0a1a;
  const BG_COLOR    = 0x0a0a1a;
  const GROUND_COLOR = 0x111128;
  const ROAD_COLOR  = 0x0d0d20;

  // ── Internal state ─────────────────────────────────────────────────
  let scene, camera, renderer, clock;
  let buildingGroup, roadGroup, districtGroup, particleGroup;
  let rainPoints, rainPositions, rainVelocities;
  let trafficMeshes = [];
  let layout = {};
  let canvasEl = null;
  let animId = null;
  let entities = [];

  const RAIN_COUNT = 500;
  const RAIN_AREA  = 600;
  const RAIN_HEIGHT = 400;

  // ── Helpers ────────────────────────────────────────────────────────

  function mapRange(v, inMin, inMax, outMin, outMax) {
    return outMin + (Math.max(inMin, Math.min(inMax, v)) - inMin) / (inMax - inMin) * (outMax - outMin);
  }

  // ── Scene Setup ────────────────────────────────────────────────────

  function initScene(canvas) {
    canvasEl = canvas;

    // Renderer
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.8;

    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(BG_COLOR);
    scene.fog = new THREE.Fog(FOG_COLOR, 200, 800);

    // Clock
    clock = new THREE.Clock();

    // Camera — perspective, angled view
    const aspect = canvas.clientWidth / canvas.clientHeight;
    camera = new THREE.PerspectiveCamera(55, aspect, 1, 2000);
    camera.position.set(150, 200, 300);
    camera.lookAt(0, 40, 0);

    // Groups
    buildingGroup  = new THREE.Group();
    roadGroup      = new THREE.Group();
    districtGroup  = new THREE.Group();
    particleGroup  = new THREE.Group();

    scene.add(buildingGroup);
    scene.add(roadGroup);
    scene.add(districtGroup);
    scene.add(particleGroup);

    // Lighting
    setupLighting();

    // Ground plane
    setupGround();

    // Roads
    setupRoads();

    // Rain
    setupRain();
  }

  function setupLighting() {
    // Ambient — base visibility
    const ambient = new THREE.AmbientLight(0x1a1a3e, 0.4);
    scene.add(ambient);

    // Directional — moonlight, cool blue tint from above-right
    const moonlight = new THREE.DirectionalLight(0x4466aa, 0.6);
    moonlight.position.set(100, 300, 50);
    moonlight.castShadow = true;
    moonlight.shadow.mapSize.width  = 2048;
    moonlight.shadow.mapSize.height = 2048;
    moonlight.shadow.camera.near = 10;
    moonlight.shadow.camera.far  = 600;
    moonlight.shadow.camera.left   = -300;
    moonlight.shadow.camera.right  =  300;
    moonlight.shadow.camera.top    =  300;
    moonlight.shadow.camera.bottom = -300;
    scene.add(moonlight);

    // Secondary fill — subtle purple from opposite side
    const fill = new THREE.DirectionalLight(0x220044, 0.3);
    fill.position.set(-80, 150, -100);
    scene.add(fill);

    // Hemisphere — sky/ground
    const hemi = new THREE.HemisphereLight(0x1a1a4a, 0x0a0a12, 0.3);
    scene.add(hemi);
  }

  function setupGround() {
    // Large ground plane
    const groundGeo = new THREE.PlaneGeometry(1200, 1200);
    const groundMat = new THREE.MeshStandardMaterial({
      color: GROUND_COLOR,
      metalness: 0.3,
      roughness: 0.7,
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.5;
    ground.receiveShadow = true;
    scene.add(ground);
  }

  function setupRoads() {
    // Main road grid — cross streets
    const roadMat = new THREE.MeshStandardMaterial({
      color: ROAD_COLOR,
      metalness: 0.8,
      roughness: 0.3,
    });

    // Horizontal road
    const hRoadGeo = new THREE.PlaneGeometry(800, 30);
    const hRoad = new THREE.Mesh(hRoadGeo, roadMat);
    hRoad.rotation.x = -Math.PI / 2;
    hRoad.position.set(0, 0.1, 0);
    hRoad.receiveShadow = true;
    roadGroup.add(hRoad);

    // Vertical road
    const vRoadGeo = new THREE.PlaneGeometry(30, 800);
    const vRoad = new THREE.Mesh(vRoadGeo, roadMat);
    vRoad.rotation.x = -Math.PI / 2;
    vRoad.position.set(0, 0.1, 0);
    vRoad.receiveShadow = true;
    roadGroup.add(vRoad);

    // Additional parallel roads
    for (let offset of [-200, 200]) {
      const r1Geo = new THREE.PlaneGeometry(800, 20);
      const r1 = new THREE.Mesh(r1Geo, roadMat);
      r1.rotation.x = -Math.PI / 2;
      r1.position.set(0, 0.1, offset);
      r1.receiveShadow = true;
      roadGroup.add(r1);

      const r2Geo = new THREE.PlaneGeometry(20, 800);
      const r2 = new THREE.Mesh(r2Geo, roadMat);
      r2.rotation.x = -Math.PI / 2;
      r2.position.set(offset, 0.1, 0);
      r2.receiveShadow = true;
      roadGroup.add(r2);
    }

    // Lane markings — dashed lines along roads
    const dashMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const dashGeo = new THREE.PlaneGeometry(8, 0.5);

    // Horizontal dashes (center line)
    for (let x = -380; x < 380; x += 20) {
      for (let zOff of [0, -200, 200]) {
        const dash = new THREE.Mesh(dashGeo, dashMat);
        dash.rotation.x = -Math.PI / 2;
        dash.position.set(x, 0.2, zOff);
        roadGroup.add(dash);
      }
    }

    // Vertical dashes
    const dashGeo2 = new THREE.PlaneGeometry(0.5, 8);
    for (let z = -380; z < 380; z += 20) {
      for (let xOff of [0, -200, 200]) {
        const dash = new THREE.Mesh(dashGeo2, dashMat);
        dash.rotation.x = -Math.PI / 2;
        dash.position.set(xOff, 0.2, z);
        roadGroup.add(dash);
      }
    }
  }

  function setupRain() {
    const geometry = new THREE.BufferGeometry();
    rainPositions = new Float32Array(RAIN_COUNT * 3);
    rainVelocities = new Float32Array(RAIN_COUNT);

    for (let i = 0; i < RAIN_COUNT; i++) {
      rainPositions[i * 3]     = (Math.random() - 0.5) * RAIN_AREA;  // x
      rainPositions[i * 3 + 1] = Math.random() * RAIN_HEIGHT;        // y
      rainPositions[i * 3 + 2] = (Math.random() - 0.5) * RAIN_AREA;  // z
      rainVelocities[i] = 80 + Math.random() * 120;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(rainPositions, 3));

    const rainMat = new THREE.PointsMaterial({
      color: 0x8899cc,
      size: 1.5,
      transparent: true,
      opacity: 0.4,
      sizeAttenuation: true,
    });

    rainPoints = new THREE.Points(geometry, rainMat);
    particleGroup.add(rainPoints);
  }

  // ── Building Creation ──────────────────────────────────────────────

  function createBuilding(entity, posX, posZ) {
    const metrics = entity.metrics || {};
    const cpu = Math.max(0, Math.min(100, metrics.cpu || 50));
    const mem = Math.max(0, Math.min(100, metrics.mem || 50));
    const state = entity.state || 'unknown';
    const color = STATE_COLORS[state] || STATE_COLORS.unknown;
    const neonColor = NEON_GLOW[state] || NEON_GLOW.unknown;

    // Map metrics to dimensions
    const height = mapRange(cpu, 0, 100, 20, 200);
    const width  = mapRange(mem, 0, 100, 10, 40);
    const depth  = mapRange(mem, 0, 100, 10, 40);

    const group = new THREE.Group();
    group.userData = { entityId: entity.id, entityType: 'service' };

    // ── Main body ──
    const bodyGeo = new THREE.BoxGeometry(width, height, depth);
    const bodyMat = new THREE.MeshStandardMaterial({
      color: 0x1a1a3e,
      metalness: 0.2,
      roughness: 0.8,
    });
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    body.position.y = height / 2;
    body.castShadow = true;
    body.receiveShadow = true;
    group.add(body);

    // ── Window grid (emissive) ──
    createWindows(group, width, height, depth, state, neonColor);

    // ── Ground floor base (slightly wider) ──
    const baseGeo = new THREE.BoxGeometry(width + 2, 4, depth + 2);
    const baseMat = new THREE.MeshStandardMaterial({
      color: 0x222244,
      metalness: 0.3,
      roughness: 0.6,
    });
    const base = new THREE.Mesh(baseGeo, baseMat);
    base.position.y = 2;
    base.castShadow = true;
    group.add(base);

    // ── Rooftop HVAC unit ──
    if (width > 15) {
      const hvacW = width * 0.2;
      const hvacH = 4;
      const hvacD = depth * 0.2;
      const hvacGeo = new THREE.BoxGeometry(hvacW, hvacH, hvacD);
      const hvacMat = new THREE.MeshStandardMaterial({ color: 0x2a2a40, metalness: 0.4, roughness: 0.6 });
      const hvac = new THREE.Mesh(hvacGeo, hvacMat);
      hvac.position.set(width * 0.2, height + hvacH / 2, depth * 0.15);
      hvac.castShadow = true;
      group.add(hvac);
    }

    // ── Antenna for tall buildings ──
    if (height > 120) {
      const antennaGeo = new THREE.CylinderGeometry(0.3, 0.3, 20, 6);
      const antennaMat = new THREE.MeshStandardMaterial({ color: 0x3a3a5a, metalness: 0.5, roughness: 0.5 });
      const antenna = new THREE.Mesh(antennaGeo, antennaMat);
      antenna.position.set(0, height + 10, 0);
      antenna.castShadow = true;
      group.add(antenna);

      // Blinking light on antenna
      const lightGeo = new THREE.SphereGeometry(1, 8, 8);
      const lightMat = new THREE.MeshBasicMaterial({ color: state === 'critical' ? 0xff2222 : 0xff4444 });
      const light = new THREE.Mesh(lightGeo, lightMat);
      light.position.set(0, height + 20.5, 0);
      light.userData.blink = true;
      light.userData.blinkSpeed = 2 + Math.random();
      group.add(light);
    }

    // ── Neon sign (Sprite with canvas texture) ──
    createNeonSign(group, entity.name || '', width, height, neonColor);

    // ── PointLight at building base ──
    const pointLight = new THREE.PointLight(neonColor, 0.5, 60);
    pointLight.position.set(0, 3, depth / 2 + 3);
    group.add(pointLight);

    // ── Outline / edge glow ──
    const edgesGeo = new THREE.EdgesGeometry(bodyGeo);
    const edgesMat = new THREE.LineBasicMaterial({ color: color, transparent: true, opacity: 0.6 });
    const edges = new THREE.LineSegments(edgesGeo, edgesMat);
    edges.position.y = height / 2;
    group.add(edges);

    group.position.set(posX, 0, posZ);
    return group;
  }

  function createWindows(parent, w, h, d, state, neonColor) {
    // Determine window lit percentage per state
    let litChance, windowColor;
    switch (state) {
      case 'healthy':
        litChance = 0.8;
        windowColor = 0xfbbf24;
        break;
      case 'running':
        litChance = 0.6;
        windowColor = 0x60a5fa;
        break;
      case 'warning':
        litChance = 0.4;
        windowColor = 0xf97316;
        break;
      case 'critical':
        litChance = 0.15;
        windowColor = 0xef4444;
        break;
      case 'stopped':
        litChance = 0.03;
        windowColor = 0x334455;
        break;
      case 'idle':
        litChance = 0.25;
        windowColor = 0x94a3b8;
        break;
      default:
        litChance = 0.2;
        windowColor = 0x6b7280;
    }

    const winW = 2.0;
    const winH = 2.5;
    const gapX = 4;
    const gapY = 5;
    const startY = 6;

    const litMat = new THREE.MeshBasicMaterial({ color: windowColor, transparent: true, opacity: 0.9 });
    const darkMat = new THREE.MeshBasicMaterial({ color: 0x0a0a1e, transparent: true, opacity: 0.5 });

    // Front and back faces
    for (let face = 0; face < 4; face++) {
      const isXFace = face < 2;
      const faceW = isXFace ? w : d;
      const faceD = isXFace ? d : w;
      const cols = Math.max(1, Math.floor((faceW - 2) / gapX));
      const rows = Math.max(1, Math.floor((h - startY - 3) / gapY));

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const isLit = Math.random() < litChance;
          const winGeo = new THREE.PlaneGeometry(winW, winH);
          const win = new THREE.Mesh(winGeo, isLit ? litMat : darkMat);

          const wx = -faceW / 2 + 2 + c * gapX + gapX / 2;
          const wy = startY + r * gapY + gapY / 2;

          if (face === 0) {       // front (+z)
            win.position.set(wx, wy, faceD / 2 + 0.05);
          } else if (face === 1) { // back (-z)
            win.position.set(wx, wy, -faceD / 2 - 0.05);
            win.rotation.y = Math.PI;
          } else if (face === 2) { // right (+x)
            const wz = -faceD / 2 + 2 + c * gapX + gapX / 2;
            win.position.set(faceW / 2 + 0.05, wy, wz);
            win.rotation.y = Math.PI / 2;
          } else {                 // left (-x)
            const wz = -faceD / 2 + 2 + c * gapX + gapX / 2;
            win.position.set(-faceW / 2 - 0.05, wy, wz);
            win.rotation.y = -Math.PI / 2;
          }

          parent.add(win);
        }
      }
    }
  }

  function createNeonSign(parent, name, w, h, neonColor) {
    const displayName = name.slice(0, 12);
    if (!displayName) return;

    // Create a canvas texture for the sign
    const signCanvas = document.createElement('canvas');
    const cW = 256;
    const cH = 64;
    signCanvas.width = cW;
    signCanvas.height = cH;
    const sCtx = signCanvas.getContext('2d');

    // Background
    sCtx.fillStyle = '#0f0f2a';
    sCtx.fillRect(0, 0, cW, cH);

    // Border
    const neonHex = '#' + new THREE.Color(neonColor).getHexString();
    sCtx.strokeStyle = neonHex;
    sCtx.lineWidth = 3;
    sCtx.shadowColor = neonHex;
    sCtx.shadowBlur = 10;
    sCtx.strokeRect(4, 4, cW - 8, cH - 8);

    // Text
    sCtx.fillStyle = neonHex;
    sCtx.shadowColor = neonHex;
    sCtx.shadowBlur = 15;
    sCtx.font = "bold 28px 'Courier New', monospace";
    sCtx.textAlign = 'center';
    sCtx.textBaseline = 'middle';
    sCtx.fillText(displayName, cW / 2, cH / 2);

    const texture = new THREE.CanvasTexture(signCanvas);
    const signW = Math.max(w, displayName.length * 3);
    const signH = signW * (cH / cW);
    const signGeo = new THREE.PlaneGeometry(signW, signH);
    const signMat = new THREE.MeshBasicMaterial({
      map: texture,
      transparent: true,
      side: THREE.DoubleSide,
    });
    const sign = new THREE.Mesh(signGeo, signMat);
    sign.position.set(0, h + (h > 120 ? 25 : 6), 0);
    sign.userData.neonSign = true;
    parent.add(sign);
  }

  // ── District Wireframes ────────────────────────────────────────────

  function createDistrict(entity, cx, cz, size) {
    const state = entity.state || 'unknown';
    const color = STATE_COLORS[state] || STATE_COLORS.unknown;

    // Wireframe boundary on the ground
    const borderGeo = new THREE.EdgesGeometry(new THREE.BoxGeometry(size, 1, size));
    const borderMat = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.6 });
    const border = new THREE.LineSegments(borderGeo, borderMat);
    border.position.set(cx, 0.5, cz);

    // Label sprite
    const labelSprite = makeTextSprite(entity.name || '', '#' + new THREE.Color(color).getHexString());
    labelSprite.position.set(cx, 8, cz - size / 2 + 5);
    labelSprite.scale.set(30, 15, 1);

    const group = new THREE.Group();
    group.userData = { entityId: entity.id, entityType: 'cluster' };
    group.add(border);
    group.add(labelSprite);
    return group;
  }

  function makeTextSprite(text, color) {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 128;
    const ctx = canvas.getContext('2d');

    ctx.fillStyle = 'rgba(15, 15, 42, 0.8)';
    ctx.fillRect(0, 0, 512, 128);

    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.shadowColor = color;
    ctx.shadowBlur = 8;
    ctx.strokeRect(4, 4, 504, 120);

    ctx.fillStyle = color;
    ctx.shadowColor = color;
    ctx.shadowBlur = 12;
    ctx.font = "bold 40px 'Courier New', monospace";
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text.slice(0, 20), 256, 64);

    const texture = new THREE.CanvasTexture(canvas);
    const mat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    return new THREE.Sprite(mat);
  }

  // ── Traffic Particles ──────────────────────────────────────────────

  function setupTraffic() {
    trafficMeshes = [];
    const roadPositions = [
      { axis: 'x', pos: 0,  lane: 5  },
      { axis: 'x', pos: 0,  lane: -5 },
      { axis: 'z', pos: 0,  lane: 5  },
      { axis: 'z', pos: 0,  lane: -5 },
      { axis: 'x', pos: -200, lane: 4 },
      { axis: 'x', pos: 200, lane: -4 },
      { axis: 'z', pos: -200, lane: 4 },
      { axis: 'z', pos: 200, lane: -4 },
    ];

    const carColors = [0xff00ff, 0x00ffff, 0xffff00, 0xff4488, 0x44ff88];

    for (let i = 0; i < 30; i++) {
      const rp = roadPositions[i % roadPositions.length];
      const color = carColors[i % carColors.length];
      const carGeo = new THREE.BoxGeometry(3, 1.5, 2);
      const carMat = new THREE.MeshBasicMaterial({ color });
      const car = new THREE.Mesh(carGeo, carMat);

      const startOffset = (Math.random() - 0.5) * 600;
      const direction = Math.random() > 0.5 ? 1 : -1;
      const speed = 20 + Math.random() * 40;

      car.userData = {
        axis: rp.axis,
        roadPos: rp.pos,
        lane: rp.lane,
        offset: startOffset,
        speed: speed * direction,
      };

      updateTrafficPosition(car);
      particleGroup.add(car);
      trafficMeshes.push(car);
    }
  }

  function updateTrafficPosition(car) {
    const d = car.userData;
    if (d.axis === 'x') {
      car.position.set(d.offset, 1, d.roadPos + d.lane);
    } else {
      car.position.set(d.roadPos + d.lane, 1, d.offset);
    }
  }

  // ── Layout Computation ─────────────────────────────────────────────

  function computeLayout(entityList) {
    layout = {};
    if (!entityList || !entityList.length) return layout;

    const byId = {};
    entityList.forEach(e => byId[e.id] = e);
    const roots = entityList.filter(e => !e.parent);

    if (!roots.length) return layout;

    // District spacing
    const districtSpacing = 180;
    const startX = -(roots.length - 1) * districtSpacing / 2;

    roots.forEach((root, di) => {
      const dx = startX + di * districtSpacing;
      layout[root.id] = { x: dx, z: 0 };

      const children = (root.children || []).map(id => byId[id]).filter(Boolean);
      if (!children.length) return;

      const blockSpacing = 80;
      const startZ = -(children.length - 1) * blockSpacing / 2;

      children.forEach((child, bi) => {
        const cz = startZ + bi * blockSpacing;
        layout[child.id] = { x: dx, z: cz };

        const grandchildren = (child.children || []).map(id => byId[id]).filter(Boolean);
        if (!grandchildren.length) return;

        const bSpacing = 50;
        const bStart = -(grandchildren.length - 1) * bSpacing / 2;

        grandchildren.forEach((gc, gi) => {
          const gx = dx + bStart + gi * bSpacing;
          layout[gc.id] = { x: gx, z: cz };
        });
      });
    });

    return layout;
  }

  // ── Build Scene from Entities ──────────────────────────────────────

  function buildScene(entityList) {
    // Clear existing
    while (buildingGroup.children.length) buildingGroup.remove(buildingGroup.children[0]);
    while (districtGroup.children.length) districtGroup.remove(districtGroup.children[0]);
    while (particleGroup.children.length > 1) particleGroup.remove(particleGroup.children[1]); // keep rain

    entities = entityList;
    const newLayout = computeLayout(entityList);

    const byId = {};
    entityList.forEach(e => byId[e.id] = e);

    // Create districts (clusters)
    entityList.forEach(e => {
      if (e.type !== 'cluster') return;
      const pos = newLayout[e.id];
      if (!pos) return;
      const childCount = (e.children || []).length || 1;
      const size = 60 + childCount * 30;
      const district = createDistrict(e, pos.x, pos.z, size);
      districtGroup.add(district);
    });

    // Create buildings (services)
    entityList.forEach(e => {
      if (e.type !== 'service') return;
      const pos = newLayout[e.id];
      if (!pos) return;
      const building = createBuilding(e, pos.x, pos.z);
      buildingGroup.add(building);
    });

    // Setup traffic
    setupTraffic();

    return newLayout;
  }

  // ── Animation Loop ─────────────────────────────────────────────────

  function animate() {
    animId = requestAnimationFrame(animate);
    const dt = clock.getDelta();
    const elapsed = clock.getElapsedTime();

    // Update rain
    if (rainPositions) {
      for (let i = 0; i < RAIN_COUNT; i++) {
        rainPositions[i * 3 + 1] -= rainVelocities[i] * dt;
        if (rainPositions[i * 3 + 1] < 0) {
          rainPositions[i * 3]     = (Math.random() - 0.5) * RAIN_AREA;
          rainPositions[i * 3 + 1] = RAIN_HEIGHT;
          rainPositions[i * 3 + 2] = (Math.random() - 0.5) * RAIN_AREA;
        }
      }
      rainPoints.geometry.attributes.position.needsUpdate = true;
    }

    // Update traffic
    for (const car of trafficMeshes) {
      car.userData.offset += car.userData.speed * dt;
      if (car.userData.offset > 350) car.userData.offset = -350;
      if (car.userData.offset < -350) car.userData.offset = 350;
      updateTrafficPosition(car);
    }

    // Blink antenna lights + flicker neon signs
    buildingGroup.traverse(child => {
      if (child.userData.blink) {
        const blink = Math.sin(elapsed * child.userData.blinkSpeed * 3) > 0.3;
        child.visible = blink;
      }
    });

    // Slow orbit of camera
    const camAngle = elapsed * 0.05;
    const camRadius = 350;
    camera.position.x = Math.cos(camAngle) * camRadius;
    camera.position.z = Math.sin(camAngle) * camRadius;
    camera.position.y = 180 + Math.sin(elapsed * 0.1) * 30;
    camera.lookAt(0, 40, 0);

    renderer.render(scene, camera);
  }

  // ── Public API ─────────────────────────────────────────────────────

  return {
    init(canvas) {
      initScene(canvas);
      animate();
    },

    update(entityList) {
      buildScene(entityList);
      layout = computeLayout(entityList);
    },

    resize(w, h) {
      if (!renderer) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    },

    getLayout() {
      return layout;
    },

    getTooltip(entity, x, y) {
      const lines = [
        `${entity.name || '?'} (${entity.type || '?'})`,
        `State: ${entity.state || 'unknown'}`,
      ];
      const m = entity.metrics || {};
      if (m.cpu !== undefined) lines.push(`CPU: ${m.cpu}%`);
      if (m.mem !== undefined) lines.push(`Mem: ${m.mem}%`);
      return lines.join('\n');
    },

    hitTest(entity, x, y) {
      const pos = layout[entity.id];
      if (!pos) return false;
      const w = 30, h = 30;
      return x >= pos.x - w / 2 && x <= pos.x + w / 2 &&
             y >= pos.z - h / 2 && y <= pos.z + h / 2;
    },

    dispose() {
      if (animId) cancelAnimationFrame(animId);
      if (renderer) renderer.dispose();
      scene = null;
      camera = null;
      renderer = null;
    },
  };
})();
