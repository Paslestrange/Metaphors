// static/three-app.js
// Three.js WebGL city renderer for the Metaphors dashboard

class ThreeApp {
    constructor(container) {
        this.container = container;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.buildings = new Map(); // entity.id -> mesh
        this.entities = [];
        this.pointLights = [];
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.hoveredEntity = null;
        this.selectedEntity = null;
        this.clock = new THREE.Clock();
        this.animating = false;

        // Colors matching the 2D renderer
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
        this.scene.fog = new THREE.FogExp2(0x0a0a1a, 0.002);

        // Camera
        const aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(60, aspect, 0.1, 1000);
        this.camera.position.set(50, 50, 50);
        this.camera.lookAt(0, 0, 0);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.container.appendChild(this.renderer.domElement);

        // Lights
        this.setupLights();

        // Ground
        this.createGround();

        // Controls
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.maxPolarAngle = Math.PI / 2.2;
        this.controls.minDistance = 10;
        this.controls.maxDistance = 200;

        // Events
        window.addEventListener('resize', () => this.resize());
        this.renderer.domElement.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.renderer.domElement.addEventListener('click', (e) => this.onClick(e));

        // Start animation
        this.animating = true;
        this.animate();
    }

    setupLights() {
        // Ambient
        const ambient = new THREE.AmbientLight(0x404040, 0.5);
        this.scene.add(ambient);

        // Directional (sun/moon)
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
        dirLight.position.set(50, 100, 50);
        dirLight.castShadow = true;
        dirLight.shadow.camera.left = -100;
        dirLight.shadow.camera.right = 100;
        dirLight.shadow.camera.top = 100;
        dirLight.shadow.camera.bottom = -100;
        dirLight.shadow.mapSize.width = 2048;
        dirLight.shadow.mapSize.height = 2048;
        this.scene.add(dirLight);

        // Hemisphere for subtle color variation
        const hemiLight = new THREE.HemisphereLight(0x1a1a3e, 0x0d0d22, 0.3);
        this.scene.add(hemiLight);
    }

    createGround() {
        const groundGeo = new THREE.PlaneGeometry(400, 400);
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
            roughness: 0.8
        });

        // Grid of roads
        const gridSize = 20;
        const spacing = 20;

        for (let i = -gridSize; i <= gridSize; i++) {
            // Horizontal roads
            const hRoad = new THREE.Mesh(
                new THREE.PlaneGeometry(400, 2),
                roadMat
            );
            hRoad.rotation.x = -Math.PI / 2;
            hRoad.position.y = 0.01;
            hRoad.position.z = i * spacing;
            hRoad.receiveShadow = true;
            this.scene.add(hRoad);

            // Vertical roads
            const vRoad = new THREE.Mesh(
                new THREE.PlaneGeometry(2, 400),
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
        building.userData = { entityId: entity.id, entity: entity };

        this.scene.add(building);

        // Windows (small emissive planes on faces)
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

        // Front and back faces
        const windowSize = 0.3;
        const spacing = 1.5;
        const numWindows = Math.floor(pos.w / spacing);

        for (let i = 0; i < numWindows; i++) {
            for (let j = 0; j < Math.floor(pos.h / spacing); j++) {
                if (Math.random() > 0.3) { // 70% chance of window
                    const windowGeo = new THREE.PlaneGeometry(windowSize, windowSize);
                    const window1 = new THREE.Mesh(windowGeo, windowMat);
                    window1.position.set(
                        -pos.w / 2 + spacing / 2 + i * spacing,
                        -pos.h / 2 + spacing / 2 + j * spacing,
                        pos.d / 2 + 0.01
                    );
                    building.add(window1);

                    const window2 = new THREE.Mesh(windowGeo, windowMat);
                    window2.position.set(
                        -pos.w / 2 + spacing / 2 + i * spacing,
                        -pos.h / 2 + spacing / 2 + j * spacing,
                        -pos.d / 2 - 0.01
                    );
                    window2.rotation.y = Math.PI;
                    building.add(window2);
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
    }

    updateEntities(entities) {
        const layout = this.computeLayout(entities);
        const currentIds = new Set(entities.map(e => e.id));

        // Remove buildings that no longer exist
        for (const [id, mesh] of this.buildings) {
            if (!currentIds.has(id)) {
                this.scene.remove(mesh);
                mesh.geometry.dispose();
                mesh.material.dispose();
                this.buildings.delete(id);
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

    onMouseMove(event) {
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        this.raycaster.setFromCamera(this.mouse, this.camera);
        const intersects = this.raycaster.intersectObjects(Array.from(this.buildings.values()));

        if (intersects.length > 0) {
            const mesh = intersects[0].object;
            this.hoveredEntity = mesh.userData.entity;
            this.renderer.domElement.style.cursor = 'pointer';

            // Dispatch custom event for main.js
            window.dispatchEvent(new CustomEvent('three-hover', { detail: { entity: this.hoveredEntity } }));
        } else {
            this.hoveredEntity = null;
            this.renderer.domElement.style.cursor = 'grab';
            window.dispatchEvent(new CustomEvent('three-hover', { detail: { entity: null } }));
        }
    }

    onClick(event) {
        if (this.hoveredEntity) {
            this.selectedEntity = this.hoveredEntity;
            window.dispatchEvent(new CustomEvent('three-click', { detail: { entity: this.selectedEntity } }));
        } else {
            this.selectedEntity = null;
            window.dispatchEvent(new CustomEvent('three-click', { detail: { entity: null } }));
        }
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

        // Dispose renderer
        this.renderer.dispose();
        this.container.removeChild(this.renderer.domElement);
    }
}

// Export for use in main.js
window.ThreeApp = ThreeApp;
