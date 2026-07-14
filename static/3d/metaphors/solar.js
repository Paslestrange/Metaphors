// Solar System 3D Metaphor
class SolarMetaphor extends Base3DMetaphor {
    constructor() {
        super();
        this.name = 'solar';
        this.planets = [];
        this.orbits = [];
        this.startTime = performance.now() / 1000;
    }

    getDefaultCameraPosition() {
        return { x: 0, y: 60, z: 100 };
    }

    getDefaultCameraTarget() {
        return { x: 0, y: 0, z: 0 };
    }

    buildScene(entities) {
        if (!this.scene) return;

        // Space background
        this.scene.background = new THREE.Color(0x0a0a1a);

        // Lighting - sun-like
        const ambientLight = new THREE.AmbientLight(0x333333, 0.3);
        this.scene.add(ambientLight);
        this.objects.set('ambientLight', ambientLight);

        const sunLight = new THREE.PointLight(0xfbbf24, 1, 200);
        sunLight.position.set(0, 0, 0);
        this.scene.add(sunLight);
        this.objects.set('sunLight', sunLight);

        // Sun (center)
        const sunGeo = new THREE.SphereGeometry(5, 32, 32);
        const sunMat = new THREE.MeshBasicMaterial({ 
            color: 0xfbbf24,
            emissive: 0xfbbf24
        });
        const sun = new THREE.Mesh(sunGeo, sunMat);
        this.scene.add(sun);
        this.objects.set('sun', sun);

        // Planets from entities
        const roots = entities.filter(e => !e.parent);
        const byId = {};
        entities.forEach(e => byId[e.id] = e);

        roots.forEach((root, i) => {
            const orbitRadius = 20 + i * 15;
            
            // Orbit ring
            const orbitGeo = new THREE.RingGeometry(orbitRadius - 0.1, orbitRadius + 0.1, 64);
            const orbitMat = new THREE.MeshBasicMaterial({ 
                color: 0x1f2937,
                side: THREE.DoubleSide,
                transparent: true,
                opacity: 0.3
            });
            const orbit = new THREE.Mesh(orbitGeo, orbitMat);
            orbit.rotation.x = Math.PI / 2;
            this.scene.add(orbit);
            this.orbits.push(orbit);

            const children = (root.children || []).map(id => byId[id]).filter(Boolean);
            children.forEach((child, ci) => {
                const angle = (ci / Math.max(children.length, 1)) * Math.PI * 2;
                const px = Math.cos(angle) * orbitRadius;
                const pz = Math.sin(angle) * orbitRadius;

                const stateColor = this.getStateColor(child.state);
                const size = 2 + ((child.metrics?.mem || 50) / 100) * 2;
                
                const planetGeo = new THREE.SphereGeometry(size, 16, 16);
                const planetMat = new THREE.MeshStandardMaterial({ 
                    color: stateColor,
                    emissive: stateColor,
                    emissiveIntensity: 0.4,
                    roughness: 0.6,
                    metalness: 0.4
                });
                const planet = new THREE.Mesh(planetGeo, planetMat);
                planet.position.set(px, 0, pz);
                
                this.scene.add(planet);
                this.objects.set(child.id, planet);
                this.planets.push({ 
                    mesh: planet, 
                    entity: child, 
                    orbitRadius, 
                    angle,
                    speed: 0.2 + Math.random() * 0.3
                });

                // Moons (grandchildren)
                const grandchildren = (child.children || []).map(id => byId[id]).filter(Boolean);
                grandchildren.forEach((gc, gi) => {
                    const moonAngle = (gi / Math.max(grandchildren.length, 1)) * Math.PI * 2;
                    const moonRadius = size + 3;
                    const mx = px + Math.cos(moonAngle) * moonRadius;
                    const mz = pz + Math.sin(moonAngle) * moonRadius;

                    const gcColor = this.getStateColor(gc.state);
                    const moonGeo = new THREE.SphereGeometry(0.8, 8, 8);
                    const moonMat = new THREE.MeshStandardMaterial({ 
                        color: gcColor,
                        emissive: gcColor,
                        emissiveIntensity: 0.3
                    });
                    const moon = new THREE.Mesh(moonGeo, moonMat);
                    moon.position.set(mx, 0, mz);
                    
                    this.scene.add(moon);
                    this.objects.set(gc.id, moon);
                });
            });
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
        
        // Rotate planets around sun
        this.planets.forEach(p => {
            p.angle += p.speed * deltaTime;
            const px = Math.cos(p.angle) * p.orbitRadius;
            const pz = Math.sin(p.angle) * p.orbitRadius;
            p.mesh.position.set(px, 0, pz);
            
            // Rotate planet on its axis
            p.mesh.rotation.y += deltaTime * 0.5;
        });
    }
}

window.SolarMetaphor = SolarMetaphor;
