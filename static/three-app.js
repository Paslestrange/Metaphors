// static/three-app.js
// Three.js 3D city renderer for Metaphors project

class ThreeApp {
    constructor() {
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.buildings = new Map(); // entityId -> mesh
        this.entities = [];
        this.layout = {};
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.hoveredBuilding = null;
        this.selectedBuilding = null;
        this.pointLights = [];
        this.clock = new THREE.Clock();
        this.animating = false;
        
        // State colors matching city renderer
        this.COLORS = {
            healthy: 0x4ade80,
            running: 0x60a5fa,
            warning: 0xfbbf24,
            critical: 0xef4444,
            stopped: 0x374151,
            idle: 0x94a3b8,
            degraded: 0xf97316,
            pending: 0xa78bfa,
            scaling: 0x06b6d4,
            unknown: 0x6b7280,
        };
        
        this.WALL_COLOR = 0x1a1a3e;
        this.GROUND_COLOR = 0x0d0d22;
        this.ROAD_COLOR = 0x111128;
        this.FOG_COLOR = 0x0a0a1a;
    }
    
    init(container) {
        // Scene setup
        this.scene = new THREE.Scene();
        this.scene.fog = new THREE.FogExp2(this.FOG_COLOR, 0.002);
        
        // Camera setup - 45 degree angle looking down
        const aspect = window.innerWidth / window.innerHeight;
        this.camera = new THREE.PerspectiveCamera(60, aspect, 0.1, 1000);
        this.camera.position.set(100, 80, 100);
        this.camera.lookAt(0, 0, 0);
        
        // Renderer setup
        this.renderer = new THREE.WebGLRenderer({ 
            antialias: true,
            alpha: false
        });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.setClearColor(this.FOG_COLOR);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        container.appendChild(this.renderer.domElement);
        
        // Lighting
        this.setupLighting();
        
        // Ground plane
        this.createGround();
        
        // OrbitControls
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.maxPolarAngle = Math.PI / 2.2; // Prevent going underground
        this.controls.minDistance = 20;
        this.controls.maxDistance = 300;
        
        // Event listeners
        window.addEventListener('resize', () => this.resize());
        this.renderer.domElement.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.renderer.domElement.addEventListener('click', (e) => this.onClick(e));
        
        // Start animation loop
        this.animating = true;
        this.animate();
        
        return this;
    }
    
    setupLighting() {
        // Ambient light
        const ambient = new THREE.AmbientLight(0xffffff, 0.3);
        this.scene.add(ambient);
        
        // Directional light (sun/moon)
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
        dirLight.position.set(50, 100, 50);
        dirLight.castShadow = true;
        dirLight.shadow.camera.left = -100;
        dirLight.shadow.camera.right = 100;
        dirLight.shadow.camera.top = 100;
        dirLight.shadow.camera.bottom = -100;
        dirLight.shadow.camera.near = 0.1;
        dirLight.shadow.camera.far = 200;
        dirLight.shadow.mapSize.width = 2048;
        dirLight.shadow.mapSize.height = 2048;
        this.scene.add(dirLight);
        
        // Hemisphere light for ambient sky
        const hemiLight = new THREE.HemisphereLight(0x60a5fa, 0x1a1a3e, 0.2);
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
        
        // Road grid
        this.createRoads();
    }
    
    createRoads() {
        const roadMat = new THREE.MeshStandardMaterial({ 
            color: this.ROAD_COLOR,
            roughness: 0.8,
            metalness: 0.1
        });
        
        // Create grid of roads (simplified - 5x5 blocks)
        const blockSize = 40;
        const roadWidth = 8;
        const gridCount = 5;
        const totalSize = gridCount * blockSize + (gridCount + 1) * roadWidth;
        const offset = -totalSize / 2;
        
        // Horizontal roads
        for (let i = 0; i <= gridCount; i++) {
            const roadGeo = new THREE.PlaneGeometry(totalSize, roadWidth);
            const road = new THREE.Mesh(roadGeo, roadMat);
            road.rotation.x = -Math.PI / 2;
            road.position.set(0, 0.01, offset + i * (blockSize + roadWidth) + roadWidth / 2);
            road.receiveShadow = true;
            this.scene.add(road);
        }
        
        // Vertical roads
        for (let i = 0; i <= gridCount; i++) {
            const roadGeo = new THREE.PlaneGeometry(roadWidth, totalSize);
            const road = new THREE.Mesh(roadGeo, roadMat);
            road.rotation.x = -Math.PI / 2;
            road.position.set(offset + i * (blockSize + roadWidth) + roadWidth / 2, 0.01, 0);
            road.receiveShadow = true;
            this.scene.add(road);
        }
    }
    
    computeLayout(entities, width, height) {
        const layout = {};
        const byId = {};
        entities.forEach(e => byId[e.id] = e);
        
        // Group entities by parent
        const roots = entities.filter(e => !e.parent);
        const childrenOf = {};
        entities.forEach(e => {
            if (e.parent) {
                if (!childrenOf[e.parent]) childrenOf[e.parent] = [];
                childrenOf[e.parent].push(e);
            }
        });
        
        // City block layout
        const padding = 20;
        const blockSize = 40;
        const streetWidth = 15;
        const blockSpacing = blockSize + streetWidth;
        
        let blockIdx = 0;
        const blocksPerRow = Math.ceil(Math.sqrt(roots.length));
        
        roots.forEach((root, i) => {
            const row = Math.floor(blockIdx / blocksPerRow);
            const col = blockIdx % blocksPerRow;
            const blockX = col * blockSpacing + padding;
            const blockZ = row * blockSpacing + padding;
            
            // Root entity (cluster/district)
            const rootSize = 30;
            layout[root.id] = {
                x: blockX + blockSize / 2 - rootSize / 2,
                y: 0,
                z: blockZ + blockSize / 2 - rootSize / 2,
                w: rootSize,
                h: rootSize,
                height: 15
            };
            
            // Children (nodes/services)
            const children = childrenOf[root.id] || [];
            children.forEach((child, ci) => {
                const angle = (ci / Math.max(children.length, 1)) * Math.PI * 2;
                const radius = blockSize * 0.3;
                const childSize = child.type === 'node' ? 12 : 8;
                const childHeight = child.type === 'node' ? 10 : 6;
                
                const cx = blockX + blockSize / 2 + Math.cos(angle) * radius;
                const cz = blockZ + blockSize / 2 + Math.sin(angle) * radius;
                
                layout[child.id] = {
                    x: cx - childSize / 2,
                    y: 0,
                    z: cz - childSize / 2,
                    w: childSize,
                    h: childSize,
                    height: childHeight
                };
                
                // Grandchildren
                const grandchildren = (child.children || []).map(id => byId[id]).filter(Boolean);
                grandchildren.forEach((gc, gi) => {
                    const subAngle = angle + ((gi + 0.5) / Math.max(grandchildren.length, 1)) * Math.PI * 0.5;
                    const subRadius = 8;
                    const gcSize = 5;
                    const gcHeight = 4;
                    
                    const gx = cx + Math.cos(subAngle) * subRadius;
                    const gz = cz + Math.sin(subAngle) * subRadius;
                    
                    layout[gc.id] = {
                        x: gx - gcSize / 2,
                        y: 0,
                        z: gz - gcSize / 2,
                        w: gcSize,
                        h: gcSize,
                        height: gcHeight
                    };
                });
            });
            
            blockIdx++;
        });
        
        return layout;
    }
    
    createBuilding(entity, pos) {
        const state = entity.state || 'unknown';
        const color = this.COLORS[state] || this.COLORS.unknown;
        
        // Building geometry
        const width = pos.w;
        const depth = pos.h;
        const height = pos.height || 10;
        
        const geometry = new THREE.BoxGeometry(width, height, depth);
        const material = new THREE.MeshStandardMaterial({
            color: this.WALL_COLOR,
            roughness: 0.7,
            metalness: 0.3,
            emissive: color,
            emissiveIntensity: 0.2
        });
        
        const building = new THREE.Mesh(geometry, material);
        building.position.set(pos.x + width / 2, height / 2, pos.z + depth / 2);
        building.castShadow = true;
        building.receiveShadow = true;
        building.userData = { entityId: entity.id, entity: entity };
        
        // Windows (emissive planes on faces)
        this.addWindows(building, entity, state);
        
        // Rooftop details (30% of buildings)
        if (Math.random() < 0.3) {
            this.addRooftopDetails(building, width, depth, height);
        }
        
        this.scene.add(building);
        
        // Point light for healthy/running buildings
        if (state === 'healthy' || state === 'running') {
            if (this.pointLights.length < 20) {
                const light = new THREE.PointLight(color, 0.5, 15);
                light.position.copy(building.position);
                light.position.y = height * 0.7;
                this.scene.add(light);
                this.pointLights.push(light);
                building.userData.pointLight = light;
            }
        }
        
        return building;
    }
    
    addWindows(building, entity, state) {
        const width = building.geometry.parameters.width;
        const height = building.geometry.parameters.height;
        const depth = building.geometry.parameters.depth;
        
        // Create window texture
        const canvas = document.createElement('canvas');
        canvas.width = 64;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');
        
        // Window color based on state
        let winColor;
        if (state === 'healthy') winColor = '#fbbf24';
        else if (state === 'running') winColor = '#88bbff';
        else if (state === 'warning') winColor = '#f97316';
        else if (state === 'critical') winColor = '#ff4444';
        else winColor = '#1a1a2e';
        
        ctx.fillStyle = winColor;
        
        // Draw windows in grid
        const winW = 8;
        const winH = 8;
        const gapX = 16;
        const gapY = 16;
        
        for (let y = 8; y < 64; y += gapY) {
            for (let x = 8; x < 64; x += gapX) {
                if (Math.random() > 0.3) { // 70% windows lit
                    ctx.fillRect(x, y, winW, winH);
                }
            }
        }
        
        const texture = new THREE.CanvasTexture(canvas);
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
        texture.repeat.set(width / 10, height / 10);
        
        // Create window planes for each face
        const windowMat = new THREE.MeshBasicMaterial({
            map: texture,
            transparent: true,
            opacity: 0.8
        });
        
        // Front and back
        const fbGeo = new THREE.PlaneGeometry(width, height);
        const front = new THREE.Mesh(fbGeo, windowMat);
        front.position.z = depth / 2 + 0.01;
        building.add(front);
        
        const back = new THREE.Mesh(fbGeo, windowMat);
        back.position.z = -depth / 2 - 0.01;
        back.rotation.y = Math.PI;
        building.add(back);
        
        // Left and right
        const lrGeo = new THREE.PlaneGeometry(depth, height);
        const left = new THREE.Mesh(lrGeo, windowMat);
        left.position.x = -width / 2 - 0.01;
        left.rotation.y = -Math.PI / 2;
        building.add(left);
        
        const right = new THREE.Mesh(lrGeo, windowMat);
        right.position.x = width / 2 + 0.01;
        right.rotation.y = Math.PI / 2;
        building.add(right);
    }
    
    addRooftopDetails(building, width, depth, height) {
        // HVAC unit
        const hvacGeo = new THREE.BoxGeometry(width * 0.15, height * 0.05, depth * 0.15);
        const hvacMat = new THREE.MeshStandardMaterial({ color: 0x2a2a40 });
        const hvac = new THREE.Mesh(hvacGeo, hvacMat);
        hvac.position.set(-width * 0.3, height / 2 + height * 0.025, -depth * 0.3);
        hvac.castShadow = true;
        building.add(hvac);
        
        // Antenna
        if (width > 15) {
            const antennaGeo = new THREE.CylinderGeometry(0.1, 0.1, height * 0.15);
            const antennaMat = new THREE.MeshStandardMaterial({ color: 0x3a3a5a });
            const antenna = new THREE.Mesh(antennaGeo, antennaMat);
            antenna.position.set(0, height / 2 + height * 0.075, 0);
            antenna.castShadow = true;
            building.add(antenna);
        }
    }
    
    updateEntities(entities) {
        this.entities = entities;
        
        // Compute layout
        const width = window.innerWidth;
        const height = window.innerHeight;
        this.layout = this.computeLayout(entities, width, height);
        
        // Track which entities we've seen
        const seen = new Set();
        
        // Update or create buildings
        entities.forEach(entity => {
            seen.add(entity.id);
            const pos = this.layout[entity.id];
            if (!pos) return;
            
            if (this.buildings.has(entity.id)) {
                // Update existing building
                const building = this.buildings.get(entity.id);
                this.updateBuildingState(building, entity);
            } else {
                // Create new building
                const building = this.createBuilding(entity, pos);
                this.buildings.set(entity.id, building);
            }
        });
        
        // Remove buildings for entities that no longer exist
        for (const [entityId, building] of this.buildings) {
            if (!seen.has(entityId)) {
                // Remove point light if exists
                if (building.userData.pointLight) {
                    this.scene.remove(building.userData.pointLight);
                    const lightIdx = this.pointLights.indexOf(building.userData.pointLight);
                    if (lightIdx > -1) this.pointLights.splice(lightIdx, 1);
                }
                
                // Remove building
                this.scene.remove(building);
                building.geometry.dispose();
                building.material.dispose();
                building.traverse((child) => {
                    if (child.geometry) child.geometry.dispose();
                    if (child.material) {
                        if (child.material.map) child.material.map.dispose();
                        child.material.dispose();
                    }
                });
                this.buildings.delete(entityId);
            }
        }
    }
    
    updateBuildingState(building, entity) {
        const state = entity.state || 'unknown';
        const color = this.COLORS[state] || this.COLORS.unknown;
        
        // Update material emissive
        building.material.emissive.setHex(color);
        building.material.emissiveIntensity = state === 'critical' ? 0.5 : 0.2;
        
        // Update point light
        if (building.userData.pointLight) {
            if (state === 'healthy' || state === 'running') {
                building.userData.pointLight.color.setHex(color);
                building.userData.pointLight.visible = true;
            } else {
                building.userData.pointLight.visible = false;
            }
        }
    }
    
    animate() {
        if (!this.animating) return;
        
        requestAnimationFrame(() => this.animate());
        
        const delta = this.clock.getDelta();
        const time = this.clock.getElapsedTime();
        
        // Animate critical buildings (pulsing)
        for (const [entityId, building] of this.buildings) {
            const entity = building.userData.entity;
            if (entity.state === 'critical') {
                const pulse = 0.3 + 0.2 * Math.sin(time * 8);
                building.material.emissiveIntensity = pulse;
            } else if (entity.state === 'pending') {
                // Flicker
                const flicker = 0.1 + 0.1 * Math.sin(time * 12 + entityId.length);
                building.material.emissiveIntensity = flicker;
            }
        }
        
        // Update controls
        this.controls.update();
        
        // Render
        this.renderer.render(this.scene, this.camera);
    }
    
    onMouseMove(event) {
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        
        this.raycaster.setFromCamera(this.mouse, this.camera);
        const intersects = this.raycaster.intersectObjects(Array.from(this.buildings.values()));
        
        // Reset previous hover
        if (this.hoveredBuilding && this.hoveredBuilding !== this.selectedBuilding) {
            this.hoveredBuilding.material.opacity = 1;
        }
        
        if (intersects.length > 0) {
            this.hoveredBuilding = intersects[0].object;
            this.hoveredBuilding.material.opacity = 0.8;
            this.renderer.domElement.style.cursor = 'pointer';
            
            // Dispatch custom event for main.js
            const event = new CustomEvent('building-hover', {
                detail: { entity: this.hoveredBuilding.userData.entity }
            });
            window.dispatchEvent(event);
        } else {
            this.hoveredBuilding = null;
            this.renderer.domElement.style.cursor = 'grab';
            
            const event = new CustomEvent('building-hover', { detail: { entity: null } });
            window.dispatchEvent(event);
        }
    }
    
    onClick(event) {
        if (this.hoveredBuilding) {
            // Reset previous selection
            if (this.selectedBuilding) {
                this.selectedBuilding.scale.set(1, 1, 1);
            }
            
            this.selectedBuilding = this.hoveredBuilding;
            this.selectedBuilding.scale.set(1.05, 1.05, 1.05);
            
            // Dispatch custom event for main.js
            const event = new CustomEvent('building-click', {
                detail: { entity: this.selectedBuilding.userData.entity }
            });
            window.dispatchEvent(event);
        } else {
            // Deselect
            if (this.selectedBuilding) {
                this.selectedBuilding.scale.set(1, 1, 1);
                this.selectedBuilding = null;
                
                const event = new CustomEvent('building-click', { detail: { entity: null } });
                window.dispatchEvent(event);
            }
        }
    }
    
    resize() {
        const width = window.innerWidth;
        const height = window.innerHeight;
        
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        
        this.renderer.setSize(width, height);
    }
    
    dispose() {
        this.animating = false;
        
        // Dispose buildings
        for (const [entityId, building] of this.buildings) {
            if (building.userData.pointLight) {
                this.scene.remove(building.userData.pointLight);
            }
            this.scene.remove(building);
            building.geometry.dispose();
            building.material.dispose();
            building.traverse((child) => {
                if (child.geometry) child.geometry.dispose();
                if (child.material) {
                    if (child.material.map) child.material.map.dispose();
                    child.material.dispose();
                }
            });
        }
        this.buildings.clear();
        
        // Dispose scene
        this.scene.traverse((object) => {
            if (object.geometry) object.geometry.dispose();
            if (object.material) {
                if (object.material.map) object.material.map.dispose();
                object.material.dispose();
            }
        });
        
        // Dispose renderer
        this.renderer.dispose();
        
        // Remove controls
        this.controls.dispose();
    }
}

// Export for use in main.js
window.ThreeApp = ThreeApp;
