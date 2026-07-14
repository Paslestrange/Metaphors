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
        this.scene.background = new THREE.Color(0x0a0a1a);
        this.scene.fog = new THREE.FogExp2(0x0a0a1a, 0.0015);
        
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

            // Collect all building meshes (only top-level buildings, not windows/AC)
            const meshes = [];
            this.buildings.forEach((mesh) => meshes.push(mesh));

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
    }

    _hover(mesh) {
        this.hoveredMesh = mesh;
        // Store original emissive intensity so we can restore it
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
        const roadMat = new THREE.MeshStandardMaterial({
            color: this.ROAD_COLOR,
            roughness: 0.8,
            metalness: 0.1
        });
        
        // Grid of roads
        const gridSize = 25;
        const spacing = 20;
        
        for (let i = -gridSize; i <= gridSize; i++) {
            // Horizontal roads
            const hRoad = new THREE.Mesh(
                new THREE.PlaneGeometry(500, 3),
                roadMat
            );
            hRoad.rotation.x = -Math.PI / 2;
            hRoad.position.y = 0.01;
            hRoad.position.z = i * spacing;
            hRoad.receiveShadow = true;
            this.scene.add(hRoad);
            
            // Vertical roads
            const vRoad = new THREE.Mesh(
                new THREE.PlaneGeometry(3, 500),
                roadMat
            );
            vRoad.rotation.x = -Math.PI / 2;
            vRoad.position.y = 0.01;
            vRoad.position.x = i * spacing;
            vRoad.receiveShadow = true;
            this.scene.add(vRoad);
        }
    }
    
    computeLayout(entities) {
        const layout = {};
        const byId = {};
        entities.forEach(e => { byId[e.id] = e; });
        
        const roots = entities.filter(e => !e.parent);
        const blockSize = 15;
        const blockSpacing = 25;
        const cols = Math.ceil(Math.sqrt(roots.length));
        
        roots.forEach((root, i) => {
            const col = i % cols;
            const row = Math.floor(i / cols);
            const baseX = (col - cols / 2) * blockSpacing;
            const baseZ = (row - cols / 2) * blockSpacing;
            
            // Root building (cluster)
            layout[root.id] = {
                x: baseX,
                z: baseZ,
                w: 8,
                h: 12,
                d: 8
            };
            
            // Children (nodes/services)
            const children = (root.children || []).map(id => byId[id]).filter(Boolean);
            children.forEach((child, ci) => {
                const angle = (ci / Math.max(children.length, 1)) * Math.PI * 2;
                const radius = 10;
                const cx = baseX + Math.cos(angle) * radius;
                const cz = baseZ + Math.sin(angle) * radius;
                
                layout[child.id] = {
                    x: cx,
                    z: cz,
                    w: 4,
                    h: 6,
                    d: 4
                };
                
                // Grandchildren
                const grandchildren = (child.children || []).map(id => byId[id]).filter(Boolean);
                grandchildren.forEach((gc, gi) => {
                    const subAngle = angle + ((gi / Math.max(grandchildren.length, 1)) * Math.PI * 0.5);
                    const subRadius = 4;
                    const gx = cx + Math.cos(subAngle) * subRadius;
                    const gz = cz + Math.sin(subAngle) * subRadius;
                    
                    layout[gc.id] = {
                        x: gx,
                        z: gz,
                        w: 2,
                        h: 3,
                        d: 2
                    };
                });
            });
        });
        
        return layout;
    }
    
    createBuilding(entity, layout) {
        const pos = layout[entity.id];
        if (!pos) return null;
        
        const state = entity.state || 'unknown';
        const color = this.COLORS[state] || this.COLORS.unknown;
        
        // Building geometry
        const geometry = new THREE.BoxGeometry(pos.w, pos.h, pos.d);
        const material = new THREE.MeshStandardMaterial({
            color: this.WALL_COLOR,
            roughness: 0.7,
            metalness: 0.3,
            emissive: color,
            emissiveIntensity: 0.2
        });
        
        const building = new THREE.Mesh(geometry, material);
        building.position.set(pos.x, pos.h / 2, pos.z);
        building.castShadow = true;
        building.receiveShadow = true;
        building.userData = { entity: entity };
        
        this.scene.add(building);
        
        // Windows
        this.addWindows(building, pos, color);
        
        // Rooftop details on 30% of buildings
        if (Math.random() < 0.3 && pos.w > 3) {
            this.addRooftopDetails(building, pos);
        }
        
        // Point light for healthy/running
        if ((state === 'healthy' || state === 'running') && this.pointLights.length < 20) {
            const light = new THREE.PointLight(color, 0.5, 15);
            light.position.set(pos.x, pos.h * 0.7, pos.z);
            this.scene.add(light);
            this.pointLights.push({ light, entityId: entity.id });
        }
        
        return building;
    }
    
    addWindows(building, pos, color) {
        const windowMat = new THREE.MeshBasicMaterial({
            color: color,
            transparent: true,
            opacity: 0.6
        });
        
        // Create windows on front/back and left/right faces
        const windowSize = 0.4;
        const spacing = 1.5;
        const numWindowsX = Math.floor(pos.w / spacing);
        const numWindowsY = Math.floor(pos.h / spacing);
        
        for (let i = 0; i < numWindowsX; i++) {
            for (let j = 0; j < numWindowsY; j++) {
                if (Math.random() > 0.3) { // 70% chance of window
                    const windowGeo = new THREE.PlaneGeometry(windowSize, windowSize);
                    
                    // Front face
                    const window1 = new THREE.Mesh(windowGeo, windowMat);
                    window1.position.set(
                        -pos.w / 2 + spacing / 2 + i * spacing,
                        -pos.h / 2 + spacing / 2 + j * spacing,
                        pos.d / 2 + 0.01
                    );
                    building.add(window1);
                    
                    // Back face
                    const window2 = new THREE.Mesh(windowGeo, windowMat);
                    window2.position.set(
                        -pos.w / 2 + spacing / 2 + i * spacing,
                        -pos.h / 2 + spacing / 2 + j * spacing,
                        -pos.d / 2 - 0.01
                    );
                    window2.rotation.y = Math.PI;
                    building.add(window2);
                    
                    // Left face
                    const window3 = new THREE.Mesh(windowGeo, windowMat);
                    window3.position.set(
                        -pos.w / 2 - 0.01,
                        -pos.h / 2 + spacing / 2 + j * spacing,
                        -pos.d / 2 + spacing / 2 + i * spacing
                    );
                    window3.rotation.y = -Math.PI / 2;
                    building.add(window3);
                    
                    // Right face
                    const window4 = new THREE.Mesh(windowGeo, windowMat);
                    window4.position.set(
                        pos.w / 2 + 0.01,
                        -pos.h / 2 + spacing / 2 + j * spacing,
                        -pos.d / 2 + spacing / 2 + i * spacing
                    );
                    window4.rotation.y = Math.PI / 2;
                    building.add(window4);
                }
            }
        }
    }
    
    addRooftopDetails(building, pos) {
        // AC unit
        const acGeo = new THREE.BoxGeometry(pos.w * 0.2, 0.5, pos.d * 0.2);
        const acMat = new THREE.MeshStandardMaterial({ color: 0x2a2a4a });
        const ac = new THREE.Mesh(acGeo, acMat);
        ac.position.set(pos.w * 0.25, pos.h / 2 + 0.25, pos.d * 0.25);
        ac.castShadow = true;
        building.add(ac);
        
        // Antenna
        if (pos.w > 5) {
            const antennaGeo = new THREE.CylinderGeometry(0.05, 0.05, 1.5);
            const antennaMat = new THREE.MeshStandardMaterial({ color: 0x3a3a5a });
            const antenna = new THREE.Mesh(antennaGeo, antennaMat);
            antenna.position.set(-pos.w * 0.2, pos.h / 2 + 0.75, -pos.d * 0.2);
            antenna.castShadow = true;
            building.add(antenna);
        }
    }
    
    updateEntities(entities) {
        const layout = this.computeLayout(entities);
        const currentIds = new Set(entities.map(e => e.id));
        
        // Remove buildings that no longer exist
        for (const [id, mesh] of this.buildings) {
            if (!currentIds.has(id)) {
                // If this was the hovered mesh, clear hover state
                if (this.hoveredMesh === mesh) this._unhover();
                this.scene.remove(mesh);
                mesh.geometry.dispose();
                mesh.material.dispose();
                this.buildings.delete(id);
                
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
        mesh.material.emissive.setHex(color);
        mesh.userData.entity = entity;
    }
    
    animate() {
        if (!this.animating) return;
        
        requestAnimationFrame(() => this.animate());
        
        const delta = this.clock.getDelta();
        const elapsed = this.clock.getElapsedTime();
        
        // Update controls
        this.controls.update();
        
        // Animate buildings
        this.buildings.forEach((mesh, id) => {
            // Skip hover-manipulated meshes for state animations
            if (mesh === this.hoveredMesh) return;

            const entity = mesh.userData.entity;
            const state = entity.state || 'unknown';
            
            // Critical: pulse emissive
            if (state === 'critical') {
                const pulse = 0.2 + 0.3 * Math.abs(Math.sin(elapsed * 4));
                mesh.material.emissiveIntensity = pulse;
            }
            // Scaling: animate height
            else if (state === 'scaling') {
                const scale = 1 + 0.1 * Math.sin(elapsed * 2);
                mesh.scale.y = scale;
            }
            // Pending: flicker windows
            else if (state === 'pending') {
                const flicker = Math.random() > 0.5 ? 0.2 : 0.1;
                mesh.material.emissiveIntensity = flicker;
            }
        });
        
        // Render
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
        
        // Remove point lights
        this.pointLights.forEach(({ light }) => {
            this.scene.remove(light);
        });
        this.pointLights = [];
        
        // Remove renderer
        if (this.renderer.domElement.parentNode) {
            this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
        }
        this.renderer.dispose();
    }
}

// Export for use in main.js
window.CityRenderer3D = CityRenderer3D;
