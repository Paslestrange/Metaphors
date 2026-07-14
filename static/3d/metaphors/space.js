// Space Station 3D Metaphor
class SpaceMetaphor extends Base3DMetaphor {
    constructor() {
        super();
        this.name = 'space';
        this.modules = [];
        this.stars = [];
        this.startTime = performance.now() / 1000;
    }

    getDefaultCameraPosition() {
        return { x: 20, y: 20, z: 60 };
    }

    getDefaultCameraTarget() {
        return { x: 0, y: 0, z: 0 };
    }

    buildScene(entities) {
        if (!this.scene) return;
        this.scene.background = new THREE.Color(0x000011);

        // Lighting
        const ambientLight = new THREE.AmbientLight(0x222233, 0.3);
        this.scene.add(ambientLight);
        this.objects.set('ambientLight', ambientLight);

        const sunLight = new THREE.DirectionalLight(0xffffff, 0.8);
        sunLight.position.set(50, 30, 50);
        this.scene.add(sunLight);
        this.objects.set('sunLight', sunLight);

        // Starfield
        const starGeo = new THREE.BufferGeometry();
        const starPositions = [];
        for (let i = 0; i < 500; i++) {
            starPositions.push(
                (Math.random() - 0.5) * 300,
                (Math.random() - 0.5) * 300,
                (Math.random() - 0.5) * 300
            );
        }
        starGeo.setAttribute('position', new THREE.Float32BufferAttribute(starPositions, 3));
        const starMat = new THREE.PointsMaterial({ color: 0xffffff, size: 0.5 });
        const stars = new THREE.Points(starGeo, starMat);
        this.scene.add(stars);
        this.objects.set('stars', stars);

        // Station modules from entities
        const byId = {};
        entities.forEach(e => byId[e.id] = e);
        const roots = entities.filter(e => !e.parent);
        let xOff = -20;

        roots.forEach((root, ri) => {
            const children = (root.children || []).map(id => byId[id]).filter(Boolean);
            children.forEach((child, ci) => {
                const stateColor = this.getStateColor(child.state);
                const mem = (child.metrics?.mem || 50) / 100;
                const modSize = 2 + mem * 3;
                
                // Module (node)
                const modGeo = new THREE.BoxGeometry(modSize, modSize, modSize * 2);
                const modMat = new THREE.MeshStandardMaterial({ 
                    color: 0x333344,
                    emissive: stateColor,
                    emissiveIntensity: 0.2,
                    metalness: 0.8,
                    roughness: 0.3
                });
                const mod = new THREE.Mesh(modGeo, modMat);
                const mx = xOff + ci * 12;
                const mz = ri * 15;
                mod.position.set(mx, 0, mz);
                this.scene.add(mod);
                this.objects.set(child.id, mod);
                this.modules.push({ mesh: mod, entity: child });

                // Connector panels (grandchildren)
                const grandchildren = (child.children || []).map(id => byId[id]).filter(Boolean);
                grandchildren.forEach((gc, gi) => {
                    const gcColor = this.getStateColor(gc.state);
                    const panelGeo = new THREE.BoxGeometry(1.5, 0.2, 3);
                    const panelMat = new THREE.MeshStandardMaterial({ 
                        color: 0x2244aa,
                        emissive: gcColor,
                        emissiveIntensity: 0.3,
                        metalness: 0.9,
                        roughness: 0.2
                    });
                    const panel = new THREE.Mesh(panelGeo, panelMat);
                    const px = mx + (gi % 2 === 0 ? -modSize - 1.5 : modSize + 1.5);
                    const py = Math.floor(gi / 2) * 2 - 1;
                    panel.position.set(px, py, mz);
                    this.scene.add(panel);
                    this.objects.set(gc.id, panel);
                });
            });
            xOff += 25;
        });
    }

    getStateColor(state) {
        const colors = {
            healthy: 0x4ade80, running: 0x60a5fa, idle: 0x94a3b8,
            warning: 0xfbbf24, degraded: 0xf97316, critical: 0xef4444,
            stopped: 0x374151, pending: 0xa78bfa, scaling: 0x06b6d4, unknown: 0x6b7280
        };
        return colors[state] || colors.unknown;
    }

    update(deltaTime, entities) {
        const now = performance.now() / 1000 - this.startTime;
        
        // Slowly rotate station
        this.modules.forEach(m => {
            m.mesh.rotation.y += deltaTime * 0.1;
        });

        // Pulse critical modules
        this.modules.forEach(m => {
            if (m.entity.state === 'critical') {
                m.mesh.material.emissiveIntensity = 0.3 + 0.3 * Math.sin(now * 4);
            }
        });
    }
}

window.SpaceMetaphor = SpaceMetaphor;
