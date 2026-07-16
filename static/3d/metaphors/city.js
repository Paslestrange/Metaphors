// City 3D Metaphor — Full visual overhaul with procedural textures
class CityMetaphor extends Base3DMetaphor {
    constructor() {
        super();
        this.name = 'city';
        this.buildings = [];
        this.startTime = performance.now() / 1000;
        this.textures = {};
    }

    getDefaultCameraPosition() {
        return { x: 0, y: 25, z: 60 };
    }

    getDefaultCameraTarget() {
        return { x: 0, y: 8, z: 0 };
    }

    buildScene(entities) {
        if (!this.scene) return;

        // Generate procedural textures
        this.createTextures();

        // Ground plane with pavement texture
        const groundGeo = new THREE.PlaneGeometry(300, 300);
        const groundMat = new THREE.MeshStandardMaterial({ 
            map: this.textures.pavement,
            roughness: 0.9,
            metalness: 0.1
        });
        const ground = new THREE.Mesh(groundGeo, groundMat);
        ground.rotation.x = -Math.PI / 2;
        ground.position.y = 0;
        this.scene.add(ground);
        this.objects.set('ground', ground);

        // Skybox - dark night sky
        this.scene.background = new THREE.Color(0x0a0a1a);

        // Lighting - cyberpunk city ambience
        const ambientLight = new THREE.AmbientLight(0x334455, 0.6);
        this.scene.add(ambientLight);
        this.objects.set('ambientLight', ambientLight);

        const moonLight = new THREE.DirectionalLight(0x8888cc, 0.4);
        moonLight.position.set(50, 100, 50);
        this.scene.add(moonLight);
        this.objects.set('moonLight', moonLight);

        // Neon accent lights
        const neonLight1 = new THREE.PointLight(0xff00ff, 0.8, 80);
        neonLight1.position.set(-20, 15, 10);
        this.scene.add(neonLight1);
        this.objects.set('neonLight1', neonLight1);

        const neonLight2 = new THREE.PointLight(0x00ffff, 0.6, 80);
        neonLight2.position.set(20, 12, 5);
        this.scene.add(neonLight2);
        this.objects.set('neonLight2', neonLight2);

        // Build roads
        this.buildRoads();

        // Build buildings from entities
        this.buildBuildings(entities);

        // Add atmospheric fog
        this.scene.fog = new THREE.Fog(0x0a0a1a, 50, 200);
    }

    createTextures() {
        // Procedural window texture
        this.textures.window = this.createWindowTexture();
        this.textures.road = this.createRoadTexture();
        this.textures.pavement = this.createPavementTexture();
    }

    createWindowTexture() {
        const canvas = document.createElement('canvas');
        canvas.width = 128;
        canvas.height = 128;
        const ctx = canvas.getContext('2d');

        // Dark building wall
        ctx.fillStyle = '#1a1a3e';
        ctx.fillRect(0, 0, 128, 128);

        // Window grid
        const winW = 8;
        const winH = 10;
        const gapX = 12;
        const gapY = 14;

        for (let y = 5; y < 120; y += gapY) {
            for (let x = 5; x < 120; x += gapX) {
                // Random lit/unlit windows
                const lit = Math.random() > 0.4;
                if (lit) {
                    // Warm yellow/orange window glow
                    const brightness = 0.5 + Math.random() * 0.5;
                    ctx.fillStyle = `rgba(251, 191, 36, ${brightness})`;
                } else {
                    // Dark unlit window
                    ctx.fillStyle = '#0a0a18';
                }
                ctx.fillRect(x, y, winW, winH);

                // Window frame
                ctx.strokeStyle = '#2a2a4e';
                ctx.lineWidth = 0.5;
                ctx.strokeRect(x, y, winW, winH);
            }
        }

        const texture = new THREE.CanvasTexture(canvas);
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
        return texture;
    }

    createRoadTexture() {
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');

        // Dark asphalt
        ctx.fillStyle = '#1a1a2e';
        ctx.fillRect(0, 0, 256, 64);

        // Center dashed line (yellow)
        ctx.fillStyle = '#fbbf24';
        for (let x = 0; x < 256; x += 40) {
            ctx.fillRect(x, 30, 20, 2);
        }

        // Edge lines (white)
        ctx.fillStyle = '#cccccc';
        ctx.fillRect(0, 5, 256, 1);
        ctx.fillRect(0, 60, 256, 1);

        // Subtle noise for asphalt texture
        for (let i = 0; i < 500; i++) {
            const x = Math.random() * 256;
            const y = Math.random() * 64;
            const brightness = Math.random() * 20;
            ctx.fillStyle = `rgba(${brightness}, ${brightness}, ${brightness}, 0.1)`;
            ctx.fillRect(x, y, 1, 1);
        }

        const texture = new THREE.CanvasTexture(canvas);
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
        return texture;
    }

    createPavementTexture() {
        const canvas = document.createElement('canvas');
        canvas.width = 128;
        canvas.height = 128;
        const ctx = canvas.getContext('2d');

        // Base pavement color
        ctx.fillStyle = '#0d0d22';
        ctx.fillRect(0, 0, 128, 128);

        // Concrete block pattern
        ctx.strokeStyle = '#1a1a30';
        ctx.lineWidth = 1;

        for (let y = 0; y < 128; y += 16) {
            for (let x = 0; x < 128; x += 16) {
                ctx.strokeRect(x, y, 16, 16);
            }
        }

        // Subtle noise for texture
        for (let i = 0; i < 300; i++) {
            const x = Math.random() * 128;
            const y = Math.random() * 128;
            const brightness = Math.random() * 15;
            ctx.fillStyle = `rgba(${brightness}, ${brightness}, ${brightness}, 0.15)`;
            ctx.fillRect(x, y, 1, 1);
        }

        const texture = new THREE.CanvasTexture(canvas);
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
        texture.repeat.set(10, 10);
        return texture;
    }

    buildRoads() {
        // Main road in front of buildings
        const roadGeo = new THREE.PlaneGeometry(120, 12);
        const roadMat = new THREE.MeshStandardMaterial({
            map: this.textures.road,
            roughness: 0.85
        });
        const road = new THREE.Mesh(roadGeo, roadMat);
        road.rotation.x = -Math.PI / 2;
        road.position.set(0, 0.01, 15);
        this.scene.add(road);
        this.objects.set('mainRoad', road);

        // Cross streets
        for (let i = -2; i <= 2; i++) {
            const crossGeo = new THREE.PlaneGeometry(8, 60);
            const crossMat = new THREE.MeshStandardMaterial({
                map: this.textures.road,
                roughness: 0.85
            });
            const cross = new THREE.Mesh(crossGeo, crossMat);
            cross.rotation.x = -Math.PI / 2;
            cross.position.set(i * 30, 0.01, 0);
            this.scene.add(cross);
            this.objects.set(`crossRoad_${i}`, cross);
        }
    }

    buildBuildings(entities) {
        const roots = entities.filter(e => !e.parent);
        let xOffset = -50;

        const byId = {};
        entities.forEach(e => byId[e.id] = e);

        roots.forEach((root, i) => {
            const children = (root.children || []).map(id => byId[id]).filter(Boolean);

            children.forEach((child, ci) => {
                const grandchildren = (child.children || []).map(id => byId[id]).filter(Boolean);
                const blockX = xOffset + ci * 25;

                grandchildren.forEach((gc, gi) => {
                    const metrics = gc.metrics || {};
                    const cpu = Math.max(0, Math.min(100, metrics.cpu || 50));
                    const mem = Math.max(0, Math.min(100, metrics.mem || 50));

                    const height = 5 + (cpu / 100) * 25;
                    const width = 3 + (mem / 100) * 3;
                    const depth = width;

                    const stateColor = this.getStateColor(gc.state);
                    const stateEmissive = this.getEmissiveColor(gc.state);

                    // Building geometry with window texture on sides
                    const buildGeo = new THREE.BoxGeometry(width, height, depth);
                    
                    // Materials: [right, left, top, bottom, front, back]
                    const materials = [
                        new THREE.MeshStandardMaterial({ 
                            map: this.textures.window,
                            emissive: stateEmissive,
                            emissiveIntensity: 0.2,
                            roughness: 0.7,
                            metalness: 0.3
                        }),
                        new THREE.MeshStandardMaterial({ 
                            map: this.textures.window,
                            emissive: stateEmissive,
                            emissiveIntensity: 0.2,
                            roughness: 0.7,
                            metalness: 0.3
                        }),
                        new THREE.MeshStandardMaterial({ 
                            color: 0x2a2a4a,
                            roughness: 0.9,
                            metalness: 0.1
                        }),
                        new THREE.MeshStandardMaterial({ 
                            color: 0x0a0a18,
                            roughness: 0.9
                        }),
                        new THREE.MeshStandardMaterial({ 
                            map: this.textures.window,
                            emissive: stateEmissive,
                            emissiveIntensity: 0.3,
                            roughness: 0.6,
                            metalness: 0.3
                        }),
                        new THREE.MeshStandardMaterial({ 
                            map: this.textures.window,
                            emissive: stateEmissive,
                            emissiveIntensity: 0.3,
                            roughness: 0.6,
                            metalness: 0.3
                        })
                    ];

                    const building = new THREE.Mesh(buildGeo, materials);
                    
                    const bx = blockX + gi * 6;
                    const bz = 0;
                    building.position.set(bx, height / 2, bz);
                    
                    this.scene.add(building);
                    this.objects.set(gc.id, building);
                    this.buildings.push({ 
                        mesh: building, 
                        entity: gc, 
                        baseY: height / 2,
                        materials: materials
                    });

                    // Add neon sign above building
                    this.addNeonSign(gc, bx, height, bz);
                });
            });
            xOffset += 30;
        });
    }

    addNeonSign(entity, x, height, z) {
        const name = entity.name || entity.id;
        const shortName = name.substring(0, 8);
        
        // Create text sprite
        const canvas = document.createElement('canvas');
        canvas.width = 128;
        canvas.height = 32;
        const ctx = canvas.getContext('2d');

        // Dark background plate
        ctx.fillStyle = '#0f0f2a';
        ctx.fillRect(0, 0, 128, 32);

        // Neon border
        const stateColor = this.getStateColor(entity.state);
        const r = (stateColor >> 16) & 255;
        const g = (stateColor >> 8) & 255;
        const b = stateColor & 255;
        
        ctx.strokeStyle = `rgb(${r}, ${g}, ${b})`;
        ctx.lineWidth = 2;
        ctx.strokeRect(2, 2, 124, 28);

        // Text with glow
        ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
        ctx.font = 'bold 16px monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(shortName, 64, 16);

        const texture = new THREE.CanvasTexture(canvas);
        const spriteMat = new THREE.SpriteMaterial({ 
            map: texture,
            transparent: true
        });
        const sprite = new THREE.Sprite(spriteMat);
        sprite.position.set(x, height + 2, z);
        sprite.scale.set(4, 1, 1);
        
        this.scene.add(sprite);
        this.objects.set(`sign_${entity.id}`, sprite);
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

    getEmissiveColor(state) {
        const colors = {
            healthy: 0x22ff88,
            running: 0x44aaff,
            idle: 0x8899aa,
            warning: 0xffcc00,
            degraded: 0xff8800,
            critical: 0xff2222,
            stopped: 0x555555,
            pending: 0xbb99ff,
            scaling: 0x00ddff,
            unknown: 0x778899
        };
        return colors[state] || colors.unknown;
    }

    update(deltaTime, entities) {
        const now = performance.now() / 1000 - this.startTime;
        
        // Animate buildings based on state
        this.buildings.forEach(b => {
            if (b.entity.state === 'critical') {
                // Strobe effect for critical
                const strobe = 0.3 + 0.5 * Math.abs(Math.sin(now * 8 + b.entity.id.length));
                b.materials.forEach(mat => {
                    if (mat.emissiveIntensity !== undefined) {
                        mat.emissiveIntensity = strobe;
                    }
                });
            } else if (b.entity.state === 'warning') {
                // Pulse for warning
                const pulse = 0.2 + 0.3 * Math.abs(Math.sin(now * 4));
                b.materials.forEach(mat => {
                    if (mat.emissiveIntensity !== undefined) {
                        mat.emissiveIntensity = pulse;
                    }
                });
            } else if (b.entity.state === 'healthy') {
                // Subtle flicker for healthy
                const flicker = 0.15 + 0.1 * Math.sin(now * 2 + b.entity.id.length);
                b.materials.forEach(mat => {
                    if (mat.emissiveIntensity !== undefined) {
                        mat.emissiveIntensity = flicker;
                    }
                });
            }
        });

        // Animate neon lights
        const neonLight1 = this.objects.get('neonLight1');
        const neonLight2 = this.objects.get('neonLight2');
        if (neonLight1) {
            neonLight1.intensity = 0.6 + 0.3 * Math.sin(now * 1.5);
        }
        if (neonLight2) {
            neonLight2.intensity = 0.5 + 0.2 * Math.sin(now * 2 + 1);
        }
    }
}

window.CityMetaphor = CityMetaphor;
