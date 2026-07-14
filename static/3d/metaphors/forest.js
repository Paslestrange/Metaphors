// Forest 3D Metaphor
class ForestMetaphor extends Base3DMetaphor {
    constructor() {
        super();
        this.name = 'forest';
        this.trees = [];
        this.fireflies = [];
        this.startTime = performance.now() / 1000;
    }

    getDefaultCameraPosition() {
        return { x: 30, y: 30, z: 70 };
    }

    getDefaultCameraTarget() {
        return { x: 0, y: 10, z: 0 };
    }

    buildScene(entities) {
        if (!this.scene) return;

        // Forest background - dark green/blue
        this.scene.background = new THREE.Color(0x0a1a0a);
        this.scene.fog = new THREE.FogExp2(0x0a1a0a, 0.008);

        // Lighting
        const ambientLight = new THREE.AmbientLight(0x224422, 0.4);
        this.scene.add(ambientLight);
        this.objects.set('ambientLight', ambientLight);

        const sunLight = new THREE.DirectionalLight(0xffdd88, 0.6);
        sunLight.position.set(50, 80, 30);
        this.scene.add(sunLight);
        this.objects.set('sunLight', sunLight);

        // Ground
        const groundGeo = new THREE.PlaneGeometry(200, 200);
        const groundMat = new THREE.MeshStandardMaterial({ 
            color: 0x1a3a1a,
            roughness: 1.0
        });
        const ground = new THREE.Mesh(groundGeo, groundMat);
        ground.rotation.x = -Math.PI / 2;
        ground.position.y = 0;
        this.scene.add(ground);
        this.objects.set('ground', ground);

        // Build trees from entities
        const roots = entities.filter(e => !e.parent);
        const byId = {};
        entities.forEach(e => byId[e.id] = e);
        let xOff = -40;

        roots.forEach((root, ri) => {
            const children = (root.children || []).map(id => byId[id]).filter(Boolean);
            
            children.forEach((child, ci) => {
                const tx = xOff + ci * 12;
                const tz = ri * 15;
                const stateColor = this.getStateColor(child.state);
                
                // Tree trunk (cluster)
                const trunkGeo = new THREE.CylinderGeometry(1, 1.5, 12, 8);
                const trunkMat = new THREE.MeshStandardMaterial({ 
                    color: 0x4a3020,
                    roughness: 0.9
                });
                const trunk = new THREE.Mesh(trunkGeo, trunkMat);
                trunk.position.set(tx, 6, tz);
                this.scene.add(trunk);
                this.objects.set(child.id + '_trunk', trunk);

                // Canopy (node)
                const canopyGeo = new THREE.SphereGeometry(6, 12, 8);
                const canopyMat = new THREE.MeshStandardMaterial({ 
                    color: stateColor,
                    emissive: stateColor,
                    emissiveIntensity: 0.15,
                    roughness: 0.8
                });
                const canopy = new THREE.Mesh(canopyGeo, canopyMat);
                canopy.position.set(tx, 15, tz);
                this.scene.add(canopy);
                this.objects.set(child.id, canopy);
                this.trees.push({ mesh: canopy, entity: child, baseY: 15 });

                // Leaves (grandchildren)
                const grandchildren = (child.children || []).map(id => byId[id]).filter(Boolean);
                grandchildren.forEach((gc, gi) => {
                    const leafAngle = (gi / Math.max(grandchildren.length, 1)) * Math.PI * 2;
                    const leafDist = 4 + gi * 1.5;
                    const lx = tx + Math.cos(leafAngle) * leafDist;
                    const lz = tz + Math.sin(leafAngle) * leafDist;
                    const ly = 12 + Math.random() * 6;

                    const gcColor = this.getStateColor(gc.state);
                    const leafGeo = new THREE.SphereGeometry(1.5, 6, 6);
                    const leafMat = new THREE.MeshStandardMaterial({ 
                        color: gcColor,
                        emissive: gcColor,
                        emissiveIntensity: 0.1
                    });
                    const leaf = new THREE.Mesh(leafGeo, leafMat);
                    leaf.position.set(lx, ly, lz);
                    this.scene.add(leaf);
                    this.objects.set(gc.id, leaf);
                });
            });
            xOff += 25;
        });

        // Fireflies
        for (let i = 0; i < 30; i++) {
            const ffGeo = new THREE.SphereGeometry(0.2, 4, 4);
            const ffMat = new THREE.MeshBasicMaterial({ color: 0xaaffaa });
            const ff = new THREE.Mesh(ffGeo, ffMat);
            ff.position.set(
                (Math.random() - 0.5) * 100,
                2 + Math.random() * 20,
                (Math.random() - 0.5) * 100
            );
            this.scene.add(ff);
            this.fireflies.push({ 
                mesh: ff, 
                baseX: ff.position.x, 
                baseY: ff.position.y, 
                baseZ: ff.position.z,
                phase: Math.random() * Math.PI * 2,
                speed: 0.5 + Math.random() * 1.5
            });
        }
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
        
        // Animate fireflies
        this.fireflies.forEach(ff => {
            ff.mesh.position.x = ff.baseX + Math.sin(now * ff.speed + ff.phase) * 3;
            ff.mesh.position.y = ff.baseY + Math.sin(now * ff.speed * 1.3 + ff.phase) * 2;
            ff.mesh.position.z = ff.baseZ + Math.cos(now * ff.speed * 0.7 + ff.phase) * 3;
            ff.mesh.material.opacity = 0.3 + 0.7 * Math.abs(Math.sin(now * ff.speed * 2 + ff.phase));
            ff.mesh.material.transparent = true;
        });

        // Sway trees
        this.trees.forEach(t => {
            t.mesh.position.y = t.baseY + Math.sin(now * 0.5 + t.entity.id.length) * 0.3;
        });
    }
}

window.ForestMetaphor = ForestMetaphor;
