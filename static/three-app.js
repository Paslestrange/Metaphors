// static/three-app.js - Three.js WebGL renderer for city metaphor
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

class CityRenderer3D {
    constructor(container) {
        this.container = container;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.buildings = new Map(); // entity.id -> mesh
        this.labels = new Map(); // entity.id -> label sprite
        this.entities = [];
        this.pointLights = [];
        this.clock = new THREE.Clock();
        this.animating = false;
        this.rainParticles = null;
        this.starField = null;
        this.moon = null;
        this.moonLight = null;

        // Hover / raycasting
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.hoveredMesh = null;
        this._lastRaycastTs = 0;
        this._raycastInterval = 100; // ms debounce
        this._onMouseMove = null;
        this._onMouseLeave = null;

        // State colors
        this.COLORS = {
            healthy: 0x4ade80,
            running: 0x60a5fa,
            idle: 0x94a3b8,
            warning: 0xfbbf24,
            degraded: 0xf97316,
            critical: 0xef4444,
            stopped: 0x374151,
            pending: 0xa78bfa,
            scaling: 0x06b6d4,
            unknown: 0x6b7280
        };
        
        this.WALL_COLOR = 0x1a1a3e;
        this.GROUND_COLOR = 0x0d0d22;
        this.ROAD_COLOR = 0x111128;
    }
    
    init() {
        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x050510);
        this.scene.fog = new THREE.FogExp2(0x0a0820, 0.006);
        
        // Camera - 45 degree angle looking down
        const aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(60, aspect, 0.1, 1000);
        this.camera.position.set(80, 80, 80);
        this.camera.lookAt(0, 0, 0);
        
        // Renderer with antialiasing
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.container.appendChild(this.renderer.domElement);
        
        // Lights
        this.setupLights();
        
        // Atmosphere
        this.createStarField();
        this.createRain();
        this.createMoon();
        this.createCityHaze();
        
        // Ground
        this.createGround();
        
        // Controls
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.maxPolarAngle = Math.PI / 2.2;
        this.controls.minDistance = 20;
        this.controls.maxDistance = 300;
        
        // Events
        window.addEventListener('resize', () => this.resize());

        // Hover interaction
        this._setupHover();

        // Start animation
        this.animating = true;
        this.animate();
        
        return this;
    }
    
    // ----------------------------------------------------------------
    // HOVER / RAYCASTING
    // ----------------------------------------------------------------

    _setupHover() {
        const canvas = this.renderer.domElement;

        this._onMouseMove = (event) => {
            const now = performance.now();
            if (now - this._lastRaycastTs < this._raycastInterval) return;
            this._lastRaycastTs = now;

            const rect = canvas.getBoundingClientRect();
            this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

            this.raycaster.setFromCamera(this.mouse, this.camera);

            const meshes = Array.from(this.buildings.values());
            const intersects = this.raycaster.intersectObjects(meshes, false);

            if (intersects.length > 0) {
                const hitMesh = intersects[0].object;
                if (hitMesh !== this.hoveredMesh) {
                    this._unhover();
                    this._hover(hitMesh);
                }
                canvas.style.cursor = 'pointer';
            } else {
                this._unhover();
                canvas.style.cursor = 'default';
            }
        };

        this._onMouseLeave = () => {
            this._unhover();
            canvas.style.cursor = 'default';
        };

        canvas.addEventListener('mousemove', this._onMouseMove);
        canvas.addEventListener('mouseleave', this._onMouseLeave);

        // Click handler — populate entity detail panel
        this._onClick = (event) => {
            if (this._wasDragged) { this._wasDragged = false; return; }
            const rect = canvas.getBoundingClientRect();
            this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
            this.raycaster.setFromCamera(this.mouse, this.camera);
            const meshes = Array.from(this.buildings.values());
            const intersects = this.raycaster.intersectObjects(meshes, false);
            if (intersects.length > 0) {
                const entity = intersects[0].object.userData.entity;
                if (entity && typeof window.showDetailPanel === 'function') {
                    window.showDetailPanel(entity);
                }
            } else if (typeof window.hideDetailPanel === 'function') {
                window.hideDetailPanel();
            }
        };

        this._wasDragged = false;
        this._onMouseDown = (e) => { this._mouseDownX = e.clientX; this._mouseDownY = e.clientY; };
        this._onMouseUp = (e) => {
            if (Math.hypot(e.clientX - this._mouseDownX, e.clientY - this._mouseDownY) > 4) {
                this._wasDragged = true;
            }
        };

        canvas.addEventListener('click', this._onClick);
        canvas.addEventListener('mousedown', this._onMouseDown);
        canvas.addEventListener('mouseup', this._onMouseUp);
    }

    _hover(mesh) {
        this.hoveredMesh = mesh;
        mesh.userData._origEmissiveIntensity = mesh.material.emissiveIntensity;
        mesh.material.emissiveIntensity = (mesh.userData._origEmissiveIntensity || 0.2) * 1.5;
    }

    _unhover() {
        if (!this.hoveredMesh) return;
        const mesh = this.hoveredMesh;
        const orig = mesh.userData._origEmissiveIntensity;
        if (orig !== undefined) {
            mesh.material.emissiveIntensity = orig;
            delete mesh.userData._origEmissiveIntensity;
        }
        this.hoveredMesh = null;
    }

    setupLights() {
        // Ambient light
        const ambient = new THREE.AmbientLight(0x404040, 0.5);
        this.scene.add(ambient);
        
        // Directional light (moon) — cool blue-white
        const dirLight = new THREE.DirectionalLight(0xb4c6e7, 0.6);
        dirLight.position.set(-60, 120, -40);
        dirLight.castShadow = true;
        dirLight.shadow.camera.left = -150;
        dirLight.shadow.camera.right = 150;
        dirLight.shadow.camera.top = 150;
        dirLight.shadow.camera.bottom = -150;
        dirLight.shadow.camera.near = 0.1;
        dirLight.shadow.camera.far = 300;
        dirLight.shadow.mapSize.width = 2048;
        dirLight.shadow.mapSize.height = 2048;
        this.scene.add(dirLight);
        this.moonLight = dirLight;
        
        // Hemisphere light for ambient variation
        const hemiLight = new THREE.HemisphereLight(0x1a1a3e, 0x0d0d22, 0.3);
        this.scene.add(hemiLight);
    }
    
    createGround() {
        // Ground plane
        const groundGeo = new THREE.PlaneGeometry(500, 500);
        const groundMat = new THREE.MeshStandardMaterial({
            color: this.GROUND_COLOR,
            roughness: 0.9,
            metalness: 0.1
        });
        const ground = new THREE.Mesh(groundGeo, groundMat);
        ground.rotation.x = -Math.PI / 2;
        ground.receiveShadow = true;
        this.scene.add(ground);
        
        // Roads
        this.createRoads();
    }
    
    createRoads() {
        // Road material: dark asphalt with slight reflectivity
        const roadMat = new THREE.MeshStandardMaterial({
            color: this.ROAD_COLOR,
            roughness: 0.4,
            metalness: 0.6,
            emissive: 0x050510,
            emissiveIntensity: 0.3
        });

        // Roads connect district boundaries — spacing matches blockSpacing (25)
        // in computeLayout so roads run between building clusters
        const roadWidth = 5;
        const spacing = 25;
        const halfExtent = 150; // roads span ±150 units
        const roadPositions = [];

        for (let pos = -halfExtent; pos <= halfExtent; pos += spacing) {
            roadPositions.push(pos);
        }

        // Horizontal roads (along X axis)
        roadPositions.forEach(z => {
            const road = new THREE.Mesh(
                new THREE.PlaneGeometry(halfExtent * 2, roadWidth),
                roadMat
            );
            road.rotation.x = -Math.PI / 2;
            road.position.set(0, 0.1, z);
            road.receiveShadow = true;
            this.scene.add(road);
        });

        // Vertical roads (along Z axis)
        roadPositions.forEach(x => {
            const road = new THREE.Mesh(
                new THREE.PlaneGeometry(roadWidth, halfExtent * 2),
                roadMat
            );
            road.rotation.x = -Math.PI / 2;
            road.position.set(x, 0.1, 0);
            road.receiveShadow = true;
            this.scene.add(road);
        });

        // Lane markings — dashed white lines down center of each road
        this.createLaneMarkings(roadPositions, halfExtent);

        // Crosswalks at intersections
        this.createCrosswalks(roadPositions, roadWidth);

        // Streetlights along roads
        this.createStreetlights(roadPositions, halfExtent);
    }

    createLaneMarkings(roadPositions, halfExtent) {
        const dashLength = 3;
        const gapLength = 3;
        const lineColor = 0xffffff;
        const lineMat = new THREE.LineDashedMaterial({
            color: lineColor,
            dashSize: dashLength,
            gapSize: gapLength,
            linewidth: 1
        });

        // Center dashed line for horizontal roads
        roadPositions.forEach(z => {
            const points = [
                new THREE.Vector3(-halfExtent, 0.15, z),
                new THREE.Vector3(halfExtent, 0.15, z)
            ];
            const geometry = new THREE.BufferGeometry().setFromPoints(points);
            const line = new THREE.Line(geometry, lineMat);
            line.computeLineDistances();
            this.scene.add(line);
        });

        // Center dashed line for vertical roads
        roadPositions.forEach(x => {
            const points = [
                new THREE.Vector3(x, 0.15, -halfExtent),
                new THREE.Vector3(x, 0.15, halfExtent)
            ];
            const geometry = new THREE.BufferGeometry().setFromPoints(points);
            const line = new THREE.Line(geometry, lineMat);
            line.computeLineDistances();
            this.scene.add(line);
        });
    }

    createCrosswalks(roadPositions, roadWidth) {
        const stripeMat = new THREE.MeshBasicMaterial({
            color: 0xcccccc,
            transparent: true,
            opacity: 0.7
        });
        const stripeWidth = 0.4;
        const stripeGap = 0.8;
        const crosswalkLength = roadWidth;
        const numStripes = Math.floor(crosswalkLength / (stripeWidth + stripeGap));

        // At each intersection, add crosswalk stripes on all 4 approaches
        roadPositions.forEach(roadZ => {
            roadPositions.forEach(roadX => {
                // Crosswalk on horizontal road (east and west approaches)
                for (let side = -1; side <= 1; side += 2) {
                    for (let s = 0; s < numStripes; s++) {
                        const stripe = new THREE.Mesh(
                            new THREE.PlaneGeometry(stripeWidth, 0.6),
                            stripeMat
                        );
                        stripe.rotation.x = -Math.PI / 2;
                        stripe.position.set(
                            roadX + side * (roadWidth * 0.7 + s * (stripeWidth + stripeGap)),
                            0.12,
                            roadZ
                        );
                        this.scene.add(stripe);
                    }
                }
                // Crosswalk on vertical road (north and south approaches)
                for (let side = -1; side <= 1; side += 2) {
                    for (let s = 0; s < numStripes; s++) {
                        const stripe = new THREE.Mesh(
                            new THREE.PlaneGeometry(0.6, stripeWidth),
                            stripeMat
                        );
                        stripe.rotation.x = -Math.PI / 2;
                        stripe.position.set(
                            roadX,
                            0.12,
                            roadZ + side * (roadWidth * 0.7 + s * (stripeWidth + stripeGap))
                        );
                        this.scene.add(stripe);
                    }
                }
            });
        });
    }

    createStreetlights(roadPositions, halfExtent) {
        const poleMat = new THREE.MeshStandardMaterial({
            color: 0x333355,
            metalness: 0.8,
            roughness: 0.3
        });
        const lampMat = new THREE.MeshBasicMaterial({
            color: 0xffcc66,
            transparent: true,
            opacity: 0.9
        });
        const lightColor = 0xffaa44; // warm yellow
        const lightIntensity = 0.3;
        const lightDistance = 15;

        // Place streetlights every other road segment to limit PointLight count
        const lightSpacing = 50; // every 50 units along each road
        const poleHeight = 4;
        const poleRadius = 0.1;
        let lightCount = 0;
        const maxLights = 30; // limit for performance

        roadPositions.forEach(pos => {
            // Along horizontal roads
            for (let x = -halfExtent + 10; x <= halfExtent - 10; x += lightSpacing) {
                if (lightCount >= maxLights) break;
                for (let side = -1; side <= 1; side += 2) {
                    if (lightCount >= maxLights) break;
                    // Pole
                    const poleGeo = new THREE.CylinderGeometry(poleRadius, poleRadius, poleHeight, 6);
                    const pole = new THREE.Mesh(poleGeo, poleMat);
                    pole.position.set(x, poleHeight / 2, pos + side * 3.5);
                    pole.castShadow = true;
                    this.scene.add(pole);

                    // Lamp head
                    const lampGeo = new THREE.SphereGeometry(0.2, 6, 6);
                    const lamp = new THREE.Mesh(lampGeo, lampMat);
                    lamp.position.set(x, poleHeight + 0.1, pos + side * 3.5);
                    this.scene.add(lamp);

                    // Point light (only some lamps to limit count)
                    if (lightCount < maxLights) {
                        const light = new THREE.PointLight(lightColor, lightIntensity, lightDistance);
                        light.position.set(x, poleHeight, pos + side * 3.5);
                        this.scene.add(light);
                        lightCount++;
                    }
                }
            }
        });
    }
    
    computeLayout(entities) {
        const layout = {};
        const byId = {};
        entities.forEach(e => { byId[e.id] = e; });
        
        const roots = entities.filter(e => !e.parent);
        if (!roots.length) return layout;
        
        // Scale pixel-space coordinates to fit 3D camera view
        // Camera at (80,80,80) sees ~160 units, so use a 150x120 world
        // CENTER layout around origin so camera can see everything
        const WORLD_W = 150;
        const WORLD_D = 120;
        const CENTER_X = -WORLD_W / 2;  // Offset to center around x=0
        const CENTER_Z = -WORLD_D / 2;  // Offset to center around z=0
        
        // RECURSIVE LAYOUT: Handle entities at ANY depth in the hierarchy
        // This ensures ALL 25+ entities are positioned and visible
        function layoutRecursive(parentEntity, parentX, parentZ, parentW, parentD, depth) {
            const children = (parentEntity.children || [])
                .map(id => byId[id])
                .filter(Boolean);
            
            if (!children.length) return;
            
            // Arrange children in a grid within parent bounds
            const cols = Math.ceil(Math.sqrt(children.length));
            const rows = Math.ceil(children.length / cols);
            const cellW = parentW / cols;
            const cellD = parentD / rows;
            
            children.forEach((child, idx) => {
                const col = idx % cols;
                const row = Math.floor(idx / cols);
                
                const cx = parentX + col * cellW;
                const cz = parentZ + row * cellD;
                
                // ALL entities become VISIBLE 3D buildings
                // Type based on entity.type, not depth
                const entityType = child.type;
                const metrics = child.metrics || {};
                const cpu = Math.max(0, Math.min(100, metrics.cpu || metrics.cpu_pct || 50));
                
                let buildingType, bw, bh, bd;
                
                if (entityType === 'cluster') {
                    buildingType = 'cluster';
                    bw = cellW - 2;
                    bh = 0.5;
                    bd = cellD - 2;
                } else if (entityType === 'node' || entityType === 'namespace') {
                    buildingType = 'node';
                    bw = Math.max(5, cellW - 3);
                    bh = Math.max(2, cellD * 0.3);
                    bd = Math.max(5, cellD - 3);
                } else if (entityType === 'service' || entityType === 'agent' || entityType === 'session' || entityType === 'queue' || entityType === 'database' || entityType === 'custom') {
                    buildingType = 'service';
                    bw = Math.max(3, Math.min(8, cellW * 0.6));
                    bh = Math.max(5, Math.min(25, 5 + (cpu / 100) * 20));
                    bd = Math.max(3, Math.min(8, cellD * 0.6));
                } else if (entityType === 'container' || entityType === 'process') {
                    // STILL VISIBLE as small buildings (not dots)
                    buildingType = 'container';
                    bw = Math.max(1.5, Math.min(3, cellW * 0.5));
                    bh = Math.max(2, Math.min(8, 2 + (cpu / 100) * 6));
                    bd = Math.max(1.5, Math.min(3, cellD * 0.5));
                } else {
                    // Unknown type: still render as visible building
                    buildingType = 'service';
                    bw = Math.max(3, Math.min(6, cellW * 0.5));
                    bh = Math.max(4, Math.min(15, 4 + (cpu / 100) * 11));
                    bd = Math.max(3, Math.min(6, cellD * 0.5));
                }
                
                layout[child.id] = {
                    type: buildingType,
                    x: cx + (cellW - bw) / 2,
                    y: bh / 2,
                    z: cz + (cellD - bd) / 2,
                    w: bw,
                    h: bh,
                    d: bd
                };
                
                // Recurse into children (handles ANY depth)
                layoutRecursive(child, cx, cz, cellW, cellD, depth + 1);
            });
        }
        
        // Start layout from roots
        const districtWidth = WORLD_W / Math.max(roots.length, 1);
        
        roots.forEach((root, di) => {
            const dx = CENTER_X + di * districtWidth;
            const dz = CENTER_Z;
            
            layoutRecursive(root, dx, dz, districtWidth, WORLD_D, 0);
        });
        
        return layout;
    }
    
    createBuilding(entity, layout) {
        const pos = layout[entity.id];
        if (!pos) return null;
        
        const state = entity.state || 'unknown';
        const color = this.COLORS[state] || this.COLORS.unknown;
        const type = pos.type || entity.type || 'service';
        
        let geometry, material, mesh;
        
        if (type === 'cluster') {
            // Cluster = wireframe boundary on ground
            geometry = new THREE.BoxGeometry(pos.w, pos.h, pos.d);
            const edges = new THREE.EdgesGeometry(geometry);
            material = new THREE.LineBasicMaterial({
                color: color,
                linewidth: 2,
                transparent: true,
                opacity: 0.6
            });
            mesh = new THREE.LineSegments(edges, material);
            mesh.position.set(pos.x + pos.w / 2, pos.y, pos.z + pos.d / 2);
            mesh.userData = { entity: entity };
            this.scene.add(mesh);
            return mesh;
            
        } else if (type === 'node') {
            // Node = ground section with different shade
            geometry = new THREE.BoxGeometry(pos.w, pos.h, pos.d);
            material = new THREE.MeshStandardMaterial({
                color: this.mixColor(this.GROUND_COLOR, color, 0.3),
                roughness: 0.9,
                metalness: 0.1,
                transparent: true,
                opacity: 0.7
            });
            mesh = new THREE.Mesh(geometry, material);
            mesh.position.set(pos.x + pos.w / 2, pos.y, pos.z + pos.d / 2);
            mesh.receiveShadow = true;
            mesh.userData = { entity: entity };
            this.scene.add(mesh);
            return mesh;
            
        } else if (type === 'service') {
            // Service = building with windows
            geometry = new THREE.BoxGeometry(pos.w, pos.h, pos.d);
            
            // Generate window texture based on state for emissive map
            const windowData = this.createWindowTexture(pos, state);
            
            // Wall color: dark but slightly tinted by state
            const wallTint = this.mixColor(this.WALL_COLOR, color, 0.15);
            material = new THREE.MeshStandardMaterial({
                color: wallTint,
                roughness: 0.7,
                metalness: 0.3,
                emissiveMap: windowData.texture,
                emissive: new THREE.Color(windowData.litColor),
                emissiveIntensity: state === 'stopped' ? 0.05 : 0.35
            });
            mesh = new THREE.Mesh(geometry, material);
            mesh.position.set(pos.x + pos.w / 2, pos.y, pos.z + pos.d / 2);
            mesh.castShadow = true;
            mesh.receiveShadow = true;
            mesh.userData = { entity: entity, windowData: windowData };
            this.scene.add(mesh);
            
            // Neon edge outline showing state color
            const edgesGeo = new THREE.EdgesGeometry(geometry);
            const edgesMat = new THREE.LineBasicMaterial({ color: color, linewidth: 1 });
            const edgesMesh = new THREE.LineSegments(edgesGeo, edgesMat);
            mesh.add(edgesMesh);
            mesh.userData.edgesMesh = edgesMesh;
            
            // Add entrance on ground floor
            this.addEntrance(mesh, pos);
            
            // Rooftop details on tall buildings (height > 8)
            if (Math.random() < 0.4 && pos.h > 8) {
                this.addRooftopDetails(mesh, pos);
            }
            
            // Point light for healthy/running
            if ((state === 'healthy' || state === 'running') && this.pointLights.length < 20) {
                const light = new THREE.PointLight(color, 0.5, 30);
                light.position.set(pos.x + pos.w / 2, pos.y + pos.h * 0.7, pos.z + pos.d / 2);
                this.scene.add(light);
                this.pointLights.push({ light, entityId: entity.id });
            }
            
            return mesh;
            
        } else if (type === 'container') {
            // Container = small box at building base
            geometry = new THREE.BoxGeometry(pos.w, pos.h, pos.d);
            material = new THREE.MeshStandardMaterial({
                color: this.mixColor(this.WALL_COLOR, color, 0.4),
                roughness: 0.6,
                metalness: 0.4,
                emissive: color,
                emissiveIntensity: 0.15
            });
            mesh = new THREE.Mesh(geometry, material);
            mesh.position.set(pos.x, pos.y, pos.z);
            mesh.castShadow = true;
            mesh.userData = { entity: entity };
            this.scene.add(mesh);
            return mesh;
            
        } else if (type === 'process') {
            // Process = tiny dot on ground
            geometry = new THREE.SphereGeometry(pos.w / 2, 8, 8);
            material = new THREE.MeshBasicMaterial({
                color: color,
                transparent: true,
                opacity: 0.8
            });
            mesh = new THREE.Mesh(geometry, material);
            mesh.position.set(pos.x, pos.y, pos.z);
            mesh.userData = { entity: entity };
            this.scene.add(mesh);
            return mesh;
        }
        
        return null;
    }
    
    mixColor(color1, color2, ratio) {
        const c1 = new THREE.Color(color1);
        const c2 = new THREE.Color(color2);
        return c1.lerp(c2, ratio).getHex();
    }

    addWindows(building, pos, color) {
        const windowMat = new THREE.MeshBasicMaterial({
            color: color,
            transparent: true,
            opacity: 0.6
        });
        const windowSize = 0.5;
        const spacing = 2;
        const numX = Math.floor(pos.w / spacing);
        const numY = Math.floor(pos.h / spacing);

        for (let i = 0; i < numX; i++) {
            for (let j = 0; j < numY; j++) {
                if (Math.random() > 0.3) {
                    const windowGeo = new THREE.PlaneGeometry(windowSize, windowSize);
                    // Front
                    const w1 = new THREE.Mesh(windowGeo, windowMat);
                    w1.position.set(-pos.w / 2 + spacing / 2 + i * spacing, -pos.h / 2 + spacing / 2 + j * spacing, pos.d / 2 + 0.01);
                    building.add(w1);
                    // Back
                    const w2 = new THREE.Mesh(windowGeo, windowMat);
                    w2.position.set(-pos.w / 2 + spacing / 2 + i * spacing, -pos.h / 2 + spacing / 2 + j * spacing, -pos.d / 2 - 0.01);
                    w2.rotation.y = Math.PI;
                    building.add(w2);
                }
            }
        }
    }

    createWindowTexture(pos, state) {
        const cols = Math.max(2, Math.floor(pos.w * 1.5));
        const rows = Math.max(3, Math.floor(pos.h * 1.5));
        const cellW = 16;
        const cellH = 16;
        const canvas = document.createElement('canvas');
        canvas.width = cols * cellW;
        canvas.height = rows * cellH;
        const ctx = canvas.getContext('2d');

        let litColor, darkColor;
        switch (state) {
            case 'healthy':
            case 'running':
                litColor = '#fbbf24'; darkColor = '#2a1a00'; break;
            case 'warning':
            case 'degraded':
                litColor = '#f97316'; darkColor = '#2a1000'; break;
            case 'critical':
                litColor = '#ef4444'; darkColor = '#2a0000'; break;
            case 'stopped':
                litColor = '#111118'; darkColor = '#0a0a10'; break;
            default:
                litColor = '#6b7280'; darkColor = '#111118';
        }

        ctx.fillStyle = '#1a1a3e';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const padding = 3;
        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++) {
                const lit = Math.random() > 0.3;
                ctx.fillStyle = lit ? litColor : darkColor;
                ctx.fillRect(
                    c * cellW + padding,
                    r * cellH + padding,
                    cellW - padding * 2,
                    cellH - padding * 2
                );
            }
        }

        const texture = new THREE.CanvasTexture(canvas);
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
        texture.magFilter = THREE.NearestFilter;
        return { texture, litColor, state };
    }

    addEntrance(building, pos) {
        const awningW = pos.w * 1.15;
        const awningH = Math.max(0.4, pos.h * 0.12);
        const awningD = pos.d * 0.25;
        const awningGeo = new THREE.BoxGeometry(awningW, awningH, awningD);
        const awningMat = new THREE.MeshStandardMaterial({
            color: 0x2a2a5a,
            roughness: 0.5,
            metalness: 0.4,
            emissive: 0x3a3a6a,
            emissiveIntensity: 0.2
        });
        const awning = new THREE.Mesh(awningGeo, awningMat);
        awning.position.set(0, -pos.h / 2 + awningH / 2, pos.d / 2 + awningD / 2);
        awning.castShadow = true;
        building.add(awning);
    }

    addRooftopDetails(building, pos) {
        // HVAC unit on top
        const hvacW = pos.w * 0.25;
        const hvacH = 0.6;
        const hvacD = pos.d * 0.25;
        const hvacGeo = new THREE.BoxGeometry(hvacW, hvacH, hvacD);
        const hvacMat = new THREE.MeshStandardMaterial({
            color: 0x2a2a4a,
            roughness: 0.6,
            metalness: 0.4
        });
        const hvac = new THREE.Mesh(hvacGeo, hvacMat);
        hvac.position.set(pos.w * 0.2, pos.h / 2 + hvacH / 2, pos.d * 0.15);
        hvac.castShadow = true;
        building.add(hvac);

        // Antenna for taller buildings (h > 8)
        if (pos.h > 8) {
            const antennaGeo = new THREE.CylinderGeometry(0.04, 0.04, 2.0, 6);
            const antennaMat = new THREE.MeshStandardMaterial({
                color: 0x3a3a5a,
                metalness: 0.6,
                roughness: 0.4
            });
            const antenna = new THREE.Mesh(antennaGeo, antennaMat);
            antenna.position.set(-pos.w * 0.2, pos.h / 2 + 1.0, -pos.d * 0.2);
            antenna.castShadow = true;
            building.add(antenna);

            // Red blinking light on antenna tip
            const blinkGeo = new THREE.SphereGeometry(0.08, 8, 8);
            const blinkMat = new THREE.MeshBasicMaterial({ color: 0xff0000 });
            const blink = new THREE.Mesh(blinkGeo, blinkMat);
            blink.position.set(-pos.w * 0.2, pos.h / 2 + 2.0, -pos.d * 0.2);
            building.add(blink);
            building.userData.antennaLight = blink;
        }
    }

    createStarField() {
        // 2000 stars in upper hemisphere — bright and visible
        const starGeo = new THREE.BufferGeometry();
        const starCount = 2000;
        const starPositions = new Float32Array(starCount * 3);
        const starSizes = new Float32Array(starCount);
        const starColors = new Float32Array(starCount * 3);
        
        for (let i = 0; i < starCount; i++) {
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.random() * Math.PI * 0.45;
            const radius = 300 + Math.random() * 100;
            
            starPositions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
            starPositions[i * 3 + 1] = radius * Math.cos(phi);
            starPositions[i * 3 + 2] = radius * Math.sin(phi) * Math.sin(theta);
            starSizes[i] = Math.random() * 3 + 1.5;
            
            // Slight color variation: blue-white to warm-white
            const warmth = Math.random();
            starColors[i * 3] = 0.8 + warmth * 0.2;
            starColors[i * 3 + 1] = 0.85 + warmth * 0.15;
            starColors[i * 3 + 2] = 1.0;
        }
        
        starGeo.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
        starGeo.setAttribute('size', new THREE.BufferAttribute(starSizes, 1));
        starGeo.setAttribute('color', new THREE.BufferAttribute(starColors, 3));
        
        const starMat = new THREE.PointsMaterial({
            size: 3.0,
            sizeAttenuation: true,
            transparent: true,
            opacity: 1.0,
            vertexColors: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });
        
        this.starField = new THREE.Points(starGeo, starMat);
        this.scene.add(this.starField);
    }
    
    createRain() {
        // 4000 rain particles — dense downpour visible against dark sky
        const rainGeo = new THREE.BufferGeometry();
        const rainCount = 4000;
        const rainPositions = new Float32Array(rainCount * 3);
        
        for (let i = 0; i < rainCount; i++) {
            rainPositions[i * 3] = (Math.random() - 0.5) * 250;
            rainPositions[i * 3 + 1] = Math.random() * 120;
            rainPositions[i * 3 + 2] = (Math.random() - 0.5) * 250;
        }
        
        rainGeo.setAttribute('position', new THREE.BufferAttribute(rainPositions, 3));
        
        const rainMat = new THREE.PointsMaterial({
            color: 0x8899cc,
            size: 1.2,
            sizeAttenuation: true,
            transparent: true,
            opacity: 0.85,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });
        
        this.rainParticles = new THREE.Points(rainGeo, rainMat);
        this.rainCount = rainCount;
        this.scene.add(this.rainParticles);
    }
    
    createMoon() {
        // Moon sphere with emissive glow — large and clearly visible
        const moonGeo = new THREE.SphereGeometry(12, 32, 32);
        const moonMat = new THREE.MeshBasicMaterial({
            color: 0xffeedd,
        });
        
        this.moon = new THREE.Mesh(moonGeo, moonMat);
        this.moon.position.set(-60, 120, -40);
        this.scene.add(this.moon);
        
        // Moon glow halo
        const glowGeo = new THREE.SphereGeometry(18, 32, 32);
        const glowMat = new THREE.MeshBasicMaterial({
            color: 0xccbbaa,
            transparent: true,
            opacity: 0.25,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });
        const glow = new THREE.Mesh(glowGeo, glowMat);
        glow.position.copy(this.moon.position);
        this.moonGlow = glow;
        this.scene.add(glow);
    }
    
    createCityHaze() {
        // Large transparent planes at horizon with gradient (orange/purple) — visible city light pollution haze
        const hazeGeo = new THREE.PlaneGeometry(600, 120);
        
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');
        
        const gradient = ctx.createLinearGradient(0, 0, 0, 64);
        gradient.addColorStop(0, 'rgba(255, 140, 50, 0.5)');
        gradient.addColorStop(0.5, 'rgba(200, 100, 150, 0.4)');
        gradient.addColorStop(1, 'rgba(100, 50, 150, 0.2)');
        
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 256, 64);
        
        const hazeTexture = new THREE.CanvasTexture(canvas);
        const hazeMat = new THREE.MeshBasicMaterial({
            map: hazeTexture,
            transparent: true,
            opacity: 0.7,
            side: THREE.DoubleSide,
            depthWrite: false,
            blending: THREE.AdditiveBlending
        });
        
        // Front haze
        const haze = new THREE.Mesh(hazeGeo, hazeMat);
        haze.position.set(0, 5, -150);
        this.scene.add(haze);
        
        // Back haze (opposite side)
        const haze2 = new THREE.Mesh(hazeGeo, hazeMat);
        haze2.position.set(0, 5, 150);
        haze2.rotation.y = Math.PI;
        this.scene.add(haze2);
        
        // Side hazes
        const haze3 = new THREE.Mesh(hazeGeo, hazeMat);
        haze3.position.set(-150, 5, 0);
        haze3.rotation.y = Math.PI / 2;
        this.scene.add(haze3);
        
        const haze4 = new THREE.Mesh(hazeGeo, hazeMat);
        haze4.position.set(150, 5, 0);
        haze4.rotation.y = -Math.PI / 2;
        this.scene.add(haze4);
    }
    
    updateEntities(entities) {
        const W = this.container.clientWidth || 1200;
        const H = this.container.clientHeight || 800;
        const layout = this.computeLayout(entities);
        const currentIds = new Set(entities.map(e => e.id));
        
        // Remove buildings + labels that no longer exist
        for (const [id, mesh] of this.buildings) {
            if (!currentIds.has(id)) {
                // If this was the hovered mesh, clear hover state
                if (this.hoveredMesh === mesh) this._unhover();
                this.scene.remove(mesh);
                mesh.geometry.dispose();
                mesh.material.dispose();
                this.buildings.delete(id);

                // Remove label if exists
                const label = this.labels.get(id);
                if (label) {
                    this.scene.remove(label);
                    label.material.map.dispose();
                    label.material.dispose();
                    this.labels.delete(id);
                }
                
                // Remove point light if exists
                const lightIdx = this.pointLights.findIndex(l => l.entityId === id);
                if (lightIdx >= 0) {
                    this.scene.remove(this.pointLights[lightIdx].light);
                    this.pointLights.splice(lightIdx, 1);
                }
            }
        }
        
        // Add or update buildings
        entities.forEach(entity => {
            if (this.buildings.has(entity.id)) {
                // Update existing
                const mesh = this.buildings.get(entity.id);
                this.updateBuildingState(mesh, entity);
            } else {
                // Create new
                const mesh = this.createBuilding(entity, layout);
                if (mesh) {
                    this.buildings.set(entity.id, mesh);
                }
            }
        });
        
        this.entities = entities;
    }

    updateBuildingState(mesh, entity) {
        const state = entity.state || 'unknown';
        const color = this.COLORS[state] || this.COLORS.unknown;
        mesh.userData.entity = entity;

        // Regenerate window texture if state changed
        const prevData = mesh.userData.windowData;
        if (!prevData || prevData.state !== state) {
            const pos = {
                w: mesh.geometry.parameters.width,
                h: mesh.geometry.parameters.height,
                d: mesh.geometry.parameters.depth
            };
            const newWindowData = this.createWindowTexture(pos, state);
            if (prevData && prevData.texture) prevData.texture.dispose();
            mesh.material.emissiveMap = newWindowData.texture;
            mesh.material.emissive.set(newWindowData.litColor);
            mesh.material.emissiveIntensity = state === 'stopped' ? 0.05 : 0.6;
            mesh.material.needsUpdate = true;
            mesh.userData.windowData = newWindowData;
        }

        // Update edge color
        if (mesh.userData.edgesMesh) {
            mesh.userData.edgesMesh.material.color.setHex(color);
        }
    }

    animate() {
        if (!this.animating) return;
        
        requestAnimationFrame(() => this.animate());
        
        const delta = this.clock.getDelta();
        const elapsed = this.clock.getElapsedTime();
        
        this.controls.update();
        
        // Animate rain particles
        if (this.rainParticles) {
            const positions = this.rainParticles.geometry.attributes.position.array;
            const count = this.rainCount || 4000;
            for (let i = 0; i < count; i++) {
                positions[i * 3 + 1] -= 1.5;
                if (positions[i * 3 + 1] < 0) {
                    positions[i * 3 + 1] = 120;
                }
            }
            this.rainParticles.geometry.attributes.position.needsUpdate = true;
        }
        
        // Animate buildings per state
        this.buildings.forEach((mesh, id) => {
            if (mesh === this.hoveredMesh) return;

            const entity = mesh.userData.entity;
            const state = entity.state || 'unknown';

            if (state === 'warning' || state === 'degraded') {
                const pulse = 0.3 + 0.4 * Math.abs(Math.sin(elapsed * 2));
                mesh.material.emissiveIntensity = pulse;
            } else if (state === 'critical') {
                const strobe = Math.sin(elapsed * 8) > 0 ? 0.9 : 0.15;
                mesh.material.emissiveIntensity = strobe;
            } else if (state === 'stopped') {
                mesh.material.emissiveIntensity = 0.05;
            } else if (state === 'scaling') {
                const scale = 1 + 0.1 * Math.sin(elapsed * 2);
                mesh.scale.y = scale;
            } else if (state === 'pending') {
                const flicker = Math.random() > 0.5 ? 0.2 : 0.1;
                mesh.material.emissiveIntensity = flicker;
            } else {
                mesh.material.emissiveIntensity = 0.6;
            }

            if (mesh.userData.antennaLight) {
                const blink = Math.sin(elapsed * 3) > 0.5;
                mesh.userData.antennaLight.visible = blink;
            }
        });
        
        this.renderer.render(this.scene, this.camera);
    }
    
    resize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }
    
    dispose() {
        this.animating = false;

        // Remove hover listeners
        if (this._onMouseMove && this.renderer && this.renderer.domElement) {
            this.renderer.domElement.removeEventListener('mousemove', this._onMouseMove);
            this.renderer.domElement.removeEventListener('mouseleave', this._onMouseLeave);
        }
        this._onMouseMove = null;
        this._onMouseLeave = null;
        this.hoveredMesh = null;
        
        // Remove all buildings
        this.buildings.forEach((mesh) => {
            this.scene.remove(mesh);
            mesh.geometry.dispose();
            mesh.material.dispose();
        });
        this.buildings.clear();

        // Remove all labels
        this.labels.forEach((sprite) => {
            this.scene.remove(sprite);
            sprite.material.map.dispose();
            sprite.material.dispose();
        });
        this.labels.clear();
        
        // Remove point lights
        this.pointLights.forEach(({ light }) => {
            this.scene.remove(light);
        });
        this.pointLights = [];
        
        // Remove atmosphere
        if (this.starField) {
            this.scene.remove(this.starField);
            this.starField.geometry.dispose();
            this.starField.material.dispose();
        }
        if (this.rainParticles) {
            this.scene.remove(this.rainParticles);
            this.rainParticles.geometry.dispose();
            this.rainParticles.material.dispose();
        }
        if (this.moon) {
            this.scene.remove(this.moon);
            this.moon.geometry.dispose();
            this.moon.material.dispose();
        }
        if (this.moonGlow) {
            this.scene.remove(this.moonGlow);
            this.moonGlow.geometry.dispose();
            this.moonGlow.material.dispose();
        }
        
        // Remove renderer
        if (this.renderer.domElement.parentNode) {
            this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
        }
        this.renderer.dispose();
    }
}

// Export for use in main.js
window.CityRenderer3D = CityRenderer3D;
