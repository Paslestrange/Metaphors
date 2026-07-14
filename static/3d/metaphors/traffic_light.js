// Traffic Light 3D Metaphor
class TrafficLightMetaphor extends Base3DMetaphor {
    constructor() {
        super();
        this.name = 'traffic_light';
        this.lights = [];
        this.startTime = performance.now() / 1000;
    }

    getDefaultCameraPosition() {
        return { x: 30, y: 20, z: 50 };
    }

    getDefaultCameraTarget() {
        return { x: 0, y: 8, z: 0 };
    }

    buildScene(entities) {
        if (!this.scene) return;
        this.scene.background = new THREE.Color(0x1e1e1e);

        // Lighting
        const ambientLight = new THREE.AmbientLight(0x333333, 0.4);
        this.scene.add(ambientLight);
        this.objects.set('ambientLight', ambientLight);

        // Ground - road
        const groundGeo = new THREE.PlaneGeometry(200, 200);
        const groundMat = new THREE.MeshStandardMaterial({ color: 0x2a2a2a, roughness: 0.9 });
        const ground = new THREE.Mesh(groundGeo, groundMat);
        ground.rotation.x = -Math.PI / 2;
        this.scene.add(ground);
        this.objects.set('ground', ground);

        const byId = {};
        entities.forEach(e => byId[e.id] = e);
        const roots = entities.filter(e => !e.parent);
        let xOff = -30;

        roots.forEach((root, ri) => {
            const children = (root.children || []).map(id => byId[id]).filter(Boolean);
            children.forEach((child, ci) => {
                const tx = xOff + ci * 15;
                const tz = ri * 20;
                
                // Traffic pole
                const poleGeo = new THREE.CylinderGeometry(0.3, 0.3, 10, 8);
                const poleMat = new THREE.MeshStandardMaterial({ color: 0x444444 });
                const pole = new THREE.Mesh(poleGeo, poleMat);
                pole.position.set(tx, 5, tz);
                this.scene.add(pole);
                this.objects.set(child.id + '_pole', pole);

                // Traffic light housing
                const housingGeo = new THREE.BoxGeometry(2, 6, 2);
                const housingMat = new THREE.MeshStandardMaterial({ color: 0x111111 });
                const housing = new THREE.Mesh(housingGeo, housingMat);
                housing.position.set(tx, 12, tz);
                this.scene.add(housing);
                this.objects.set(child.id + '_housing', housing);

                // Grandchildren as lights
                const grandchildren = (child.children || []).map(id => byId[id]).filter(Boolean);
                grandchildren.forEach((gc, gi) => {
                    const stateColor = this.getStateColor(gc.state);
                    const lightGeo = new THREE.SphereGeometry(0.7, 16, 16);
                    const lightMat = new THREE.MeshBasicMaterial({ color: stateColor });
                    const light = new THREE.Mesh(lightGeo, lightMat);
                    
                    const ly = 10 + gi * 2;
                    light.position.set(tx + 1.2, ly, tz);
                    this.scene.add(light);
                    this.objects.set(gc.id, light);
                    this.lights.push({ mesh: light, entity: gc, baseColor: stateColor });
                });
            });
            xOff += 30;
        });
    }

    getStateColor(state) {
        const colors = {
            healthy: 0x22c55e, running: 0x22c55e, idle: 0xeab308,
            warning: 0xeab308, degraded: 0xf97316, critical: 0xef4444,
            stopped: 0x6b7280, pending: 0xa78bfa, scaling: 0x06b6d4, unknown: 0x4b5563
        };
        return colors[state] || colors.unknown;
    }

    update(deltaTime, entities) {
        const now = performance.now() / 1000 - this.startTime;
        this.lights.forEach(l => {
            if (l.entity.state === 'critical') {
                const blink = Math.sin(now * 6) > 0 ? 1 : 0.2;
                l.mesh.material.opacity = blink;
                l.mesh.material.transparent = true;
            } else if (l.entity.state === 'warning') {
                const pulse = 0.5 + 0.5 * Math.sin(now * 3);
                l.mesh.material.opacity = pulse;
                l.mesh.material.transparent = true;
            } else {
                l.mesh.material.opacity = 1;
                l.mesh.material.transparent = false;
            }
        });
    }
}

window.TrafficLightMetaphor = TrafficLightMetaphor;
