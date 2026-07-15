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
        this.scene.background = new THREE.Color(0x06061a);
        this.scene.fog = new THREE.FogExp2(0x0a0820, 0.0015);

        // === ATMOSPHERE EFFECTS ===

        // Sky dome — deep blue to purple gradient
        var skyGeo = new THREE.SphereGeometry(500, 32, 32);
        var skyCanvas = document.createElement('canvas');
        skyCanvas.width = 2;
        skyCanvas.height = 256;
        var skyCtx = skyCanvas.getContext('2d');
        var skyGrad = skyCtx.createLinearGradient(0, 0, 0, 256);
        skyGrad.addColorStop(0, '#020010');
        skyGrad.addColorStop(0.3, '#0a0830');
        skyGrad.addColorStop(0.6, '#120e40');
        skyGrad.addColorStop(0.8, '#1a1555');
        skyGrad.addColorStop(1, '#0d0a30');
        skyCtx.fillStyle = skyGrad;
        skyCtx.fillRect(0, 0, 2, 256);
        var skyTex = new THREE.CanvasTexture(skyCanvas);
        var skyMat = new THREE.MeshBasicMaterial({ map: skyTex, side: THREE.BackSide, depthWrite: false });
        this.objects.set('skyDome', new THREE.Mesh(skyGeo, skyMat));
        this.scene.add(this.objects.get('skyDome'));

        // Stars — 3000 particles, natural star sizes
        var starGeo = new THREE.BufferGeometry();
        var starCount = 3000;
        var starPos = new Float32Array(starCount * 3);
        var starSizes = new Float32Array(starCount);
        var starColors = new Float32Array(starCount * 3);
        for (var s = 0; s < starCount; s++) {
            var theta = Math.random() * Math.PI * 2;
            var phi = Math.random() * Math.PI * 0.4;
            var r = 350 + Math.random() * 100;
            starPos[s*3]   = r * Math.sin(phi) * Math.cos(theta);
            starPos[s*3+1] = r * Math.cos(phi);
            starPos[s*3+2] = r * Math.sin(phi) * Math.sin(theta);
            // Mix of dim and bright stars
            starSizes[s] = Math.random() < 0.05 ? Math.random()*1.5+1.5 : Math.random()*0.8+0.3;
            var w = Math.random();
            starColors[s*3]   = 0.85 + w*0.15;
            starColors[s*3+1] = 0.9  + w*0.1;
            starColors[s*3+2] = 1.0;
        }
        starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
        starGeo.setAttribute('size', new THREE.BufferAttribute(starSizes, 1));
        starGeo.setAttribute('color', new THREE.BufferAttribute(starColors, 3));
        this.objects.set('stars', new THREE.Points(starGeo, new THREE.PointsMaterial({
            size: 1.5, sizeAttenuation: true, transparent: true, opacity: 1.0,
            vertexColors: true, blending: THREE.AdditiveBlending, depthWrite: false
        })));
        this.scene.add(this.objects.get('stars'));

        // Moon — large sphere with dual glow halo
        var moonPos = new THREE.Vector3(-50, 80, -40);
        var moonMesh = new THREE.Mesh(
            new THREE.SphereGeometry(15, 32, 32),
            new THREE.MeshBasicMaterial({ color: 0xfff8e0 })
        );
        moonMesh.position.copy(moonPos);
        this.scene.add(moonMesh);
        this.objects.set('moon', moonMesh);

        var moonGlow = new THREE.Mesh(
            new THREE.SphereGeometry(25, 32, 32),
            new THREE.MeshBasicMaterial({ color: 0xfff0cc, transparent: true, opacity: 0.4, blending: THREE.AdditiveBlending, depthWrite: false })
        );
        moonGlow.position.copy(moonPos);
        this.scene.add(moonGlow);
        this.objects.set('moonGlow', moonGlow);

        var moonOuter = new THREE.Mesh(
            new THREE.SphereGeometry(40, 32, 32),
            new THREE.MeshBasicMaterial({ color: 0xeeddcc, transparent: true, opacity: 0.15, blending: THREE.AdditiveBlending, depthWrite: false })
        );
        moonOuter.position.copy(moonPos);
        this.scene.add(moonOuter);
        this.objects.set('moonOuterGlow', moonOuter);

        // Rain — 8000 particles, thin streaks
        var rainGeo = new THREE.BufferGeometry();
        var rainCount = 8000;
        var rainPos = new Float32Array(rainCount * 3);
        for (var r = 0; r < rainCount; r++) {
            rainPos[r*3]   = (Math.random()-0.5) * 300;
            rainPos[r*3+1] = Math.random() * 150;
            rainPos[r*3+2] = (Math.random()-0.5) * 300;
        }
        rainGeo.setAttribute('position', new THREE.BufferAttribute(rainPos, 3));
        this.objects.set('rainGeo', rainGeo);
        this.objects.set('rainCount', rainCount);
        this.objects.set('rain', new THREE.Points(rainGeo, new THREE.PointsMaterial({
            color: 0x99aadd, size: 0.6, sizeAttenuation: true, transparent: true, opacity: 0.7,
            blending: THREE.AdditiveBlending, depthWrite: false
        })));
        this.scene.add(this.objects.get('rain'));

        // City haze — 4-sided horizon planes
        var hazeCanvas = document.createElement('canvas');
        hazeCanvas.width = 256;
        hazeCanvas.height = 64;
        var hCtx = hazeCanvas.getContext('2d');
        var hGrad = hCtx.createLinearGradient(0, 0, 0, 64);
        hGrad.addColorStop(0, 'rgba(255,140,50,0.6)');
        hGrad.addColorStop(0.3, 'rgba(255,100,80,0.45)');
        hGrad.addColorStop(0.6, 'rgba(180,80,150,0.35)');
        hGrad.addColorStop(1, 'rgba(80,40,120,0.15)');
        hCtx.fillStyle = hGrad;
        hCtx.fillRect(0, 0, 256, 64);
        var hazeTex = new THREE.CanvasTexture(hazeCanvas);
        var hazeMat = new THREE.MeshBasicMaterial({
            map: hazeTex, transparent: true, opacity: 0.8,
            blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false, side: THREE.DoubleSide
        });
        var hazeGeo2 = new THREE.PlaneGeometry(700, 150);
        var h1 = new THREE.Mesh(hazeGeo2, hazeMat); h1.position.set(0, 8, -180);
        var h2 = new THREE.Mesh(hazeGeo2, hazeMat); h2.position.set(0, 8, 180); h2.rotation.y = Math.PI;
        var h3 = new THREE.Mesh(hazeGeo2, hazeMat); h3.position.set(-180, 8, 0); h3.rotation.y = Math.PI/2;
        var h4 = new THREE.Mesh(hazeGeo2, hazeMat); h4.position.set(180, 8, 0); h4.rotation.y = -Math.PI/2;
        this.scene.add(h1); this.scene.add(h2); this.scene.add(h3); this.scene.add(h4);
        this.objects.set('haze1', h1); this.objects.set('haze2', h2);
        this.objects.set('haze3', h3); this.objects.set('haze4', h4);

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
        
        // Animate rain
        const rain = this.objects.get('rain');
        if (rain) {
            const positions = rain.geometry.attributes.position.array;
            const count = this.objects.get('rainCount') || 8000;
            for (let i = 0; i < count; i++) {
                positions[i * 3 + 1] -= 2.0;
                if (positions[i * 3 + 1] < 0) {
                    positions[i * 3 + 1] = 150;
                }
            }
            rain.geometry.attributes.position.needsUpdate = true;
        }
        
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
