// City 3D Metaphor
class CityMetaphor extends Base3DMetaphor {
    constructor() {
        super();
        this.name = 'city';
        this.buildings = [];
        this.startTime = performance.now() / 1000;
    }

    getDefaultCameraPosition() {
        return { x: 0, y: 40, z: 80 };
    }

    getDefaultCameraTarget() {
        return { x: 0, y: 10, z: 0 };
    }

    buildScene(entities) {
        if (!this.scene) return;

        // Ground plane
        const groundGeo = new THREE.PlaneGeometry(200, 200);
        const groundMat = new THREE.MeshStandardMaterial({ 
            color: 0x0d0d22,
            roughness: 0.8
        });
        const ground = new THREE.Mesh(groundGeo, groundMat);
        ground.rotation.x = -Math.PI / 2;
        ground.position.y = 0;
        this.scene.add(ground);
        this.objects.set('ground', ground);

        // Skybox / ambient
        this.scene.background = new THREE.Color(0x0a0a1a);

        // Lighting - cyberpunk city
        const ambientLight = new THREE.AmbientLight(0x222244, 0.5);
        this.scene.add(ambientLight);
        this.objects.set('ambientLight', ambientLight);

        const dirLight = new THREE.DirectionalLight(0x4444ff, 0.3);
        dirLight.position.set(50, 100, 50);
        this.scene.add(dirLight);
        this.objects.set('dirLight', dirLight);

        // Build buildings from entities
        const roots = entities.filter(e => !e.parent);
        let xOffset = -50;

        roots.forEach((root, i) => {
            const byId = {};
            entities.forEach(e => byId[e.id] = e);
            const children = (root.children || []).map(id => byId[id]).filter(Boolean);

            children.forEach((child, ci) => {
                const grandchildren = (child.children || []).map(id => byId[id]).filter(Boolean);
                const blockX = xOffset + ci * 25;

                grandchildren.forEach((gc, gi) => {
                    const metrics = gc.metrics || {};
                    const cpu = Math.max(0, Math.min(100, metrics.cpu || 50));
                    const mem = Math.max(0, Math.min(100, metrics.mem || 50));

                    const height = 5 + (cpu / 100) * 30;
                    const width = 3 + (mem / 100) * 4;
                    const depth = width;

                    const stateColor = this.getStateColor(gc.state);
                    const buildGeo = new THREE.BoxGeometry(width, height, depth);
                    const buildMat = new THREE.MeshStandardMaterial({ 
                        color: 0x1a1a3e,
                        emissive: stateColor,
                        emissiveIntensity: 0.3,
                        roughness: 0.7,
                        metalness: 0.3
                    });
                    const building = new THREE.Mesh(buildGeo, buildMat);
                    
                    const bx = blockX + gi * 6;
                    const bz = 0;
                    building.position.set(bx, height / 2, bz);
                    
                    this.scene.add(building);
                    this.objects.set(gc.id, building);
                    this.buildings.push({ mesh: building, entity: gc, baseY: height / 2 });
                });
            });
            xOffset += 30;
        });
    }

    getStateColor(state) {
        const colors = {
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
        return colors[state] || colors.unknown;
    }

    update(deltaTime, entities) {
        const now = performance.now() / 1000 - this.startTime;
        
        // Animate critical buildings (pulse)
        this.buildings.forEach(b => {
            if (b.entity.state === 'critical') {
                const pulse = 0.3 + 0.3 * Math.sin(now * 4 + b.entity.id.length);
                b.mesh.material.emissiveIntensity = pulse;
            } else if (b.entity.state === 'warning') {
                const pulse = 0.2 + 0.2 * Math.sin(now * 2);
                b.mesh.material.emissiveIntensity = pulse;
            }
        });
    }
}

window.CityMetaphor = CityMetaphor;
