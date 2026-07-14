// Garden 3D Metaphor - Trees, flowers, terrain, sun, fireflies
class GardenMetaphor extends Base3DMetaphor {
    constructor() {
        super();
        this.name = 'garden';
        this.trees = [];
        this.flowers = [];
        this.fireflies = null;
        this.fireflyPositions = null;
        this.waterPlane = null;
        this.sunMesh = null;
        this.sunLight = null;
        this.startTime = performance.now() / 1000;
        this.timeOfDay = 0.45; // Start at ~10:48 AM (0.45 * 24h)
    }

    getDefaultCameraPosition() {
        return { x: 0, y: 35, z: 75 };
    }

    getDefaultCameraTarget() {
        return { x: 0, y: 8, z: 0 };
    }

    // ============================================================
    // Scene Building
    // ============================================================
    buildScene(entities) {
        if (!this.scene) return;

        // Sky gradient background
        this._buildSky();

        // Sun
        this._buildSun();

        // Lighting
        this._buildLighting();

        // Terrain with noise displacement
        this._buildTerrain();

        // Water with ripples
        this._buildWater();

        // Garden beds, plants, flowers
        this._buildGarden(entities);

        // Fireflies
        this._buildFireflies();
    }

    // ============================================================
    // Sky Gradient
    // ============================================================
    _buildSky() {
        // Use a large sphere with shader material for sky gradient
        const skyGeo = new THREE.SphereGeometry(400, 32, 16);
        const skyMat = new THREE.ShaderMaterial({
            uniforms: {
                topColor: { value: new THREE.Color(0x87ceeb) },
                bottomColor: { value: new THREE.Color(0xb0e0e6) },
                offset: { value: 10 },
                exponent: { value: 0.6 }
            },
            vertexShader: `
                varying vec3 vWorldPosition;
                void main() {
                    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
                    vWorldPosition = worldPosition.xyz;
                    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                }
            `,
            fragmentShader: `
                uniform vec3 topColor;
                uniform vec3 bottomColor;
                uniform float offset;
                uniform float exponent;
                varying vec3 vWorldPosition;
                void main() {
                    float h = normalize(vWorldPosition + offset).y;
                    gl_FragColor = vec4(mix(bottomColor, topColor, max(pow(max(h, 0.0), exponent), 0.0)), 1.0);
                }
            `,
            side: THREE.BackSide
        });
        const sky = new THREE.Mesh(skyGeo, skyMat);
        this.scene.add(sky);
        this.objects.set('sky', sky);
        this.skyMaterial = skyMat;
    }

    // ============================================================
    // Sun
    // ============================================================
    _buildSun() {
        const sunGeo = new THREE.SphereGeometry(6, 16, 16);
        const sunMat = new THREE.MeshBasicMaterial({ color: 0xffd700 });
        this.sunMesh = new THREE.Mesh(sunGeo, sunMat);
        this.sunMesh.position.set(0, 80, -100);
        this.scene.add(this.sunMesh);
        this.objects.set('sun', this.sunMesh);

        // Sun glow (larger transparent sphere)
        const glowGeo = new THREE.SphereGeometry(10, 16, 16);
        const glowMat = new THREE.MeshBasicMaterial({
            color: 0xfff3b0,
            transparent: true,
            opacity: 0.3
        });
        const glow = new THREE.Mesh(glowGeo, glowMat);
        this.sunMesh.add(glow);
    }

    // ============================================================
    // Lighting
    // ============================================================
    _buildLighting() {
        // Ambient
        const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
        this.scene.add(ambientLight);
        this.objects.set('ambientLight', ambientLight);

        // Sun directional light
        this.sunLight = new THREE.DirectionalLight(0xffeecc, 1.0);
        this.sunLight.position.set(0, 80, -50);
        this.sunLight.castShadow = true;
        this.sunLight.shadow.mapSize.width = 2048;
        this.sunLight.shadow.mapSize.height = 2048;
        this.sunLight.shadow.camera.near = 0.5;
        this.sunLight.shadow.camera.far = 300;
        this.sunLight.shadow.camera.left = -100;
        this.sunLight.shadow.camera.right = 100;
        this.sunLight.shadow.camera.top = 100;
        this.sunLight.shadow.camera.bottom = -100;
        this.scene.add(this.sunLight);
        this.objects.set('sunLight', this.sunLight);

        // Hemisphere light for natural sky/ground colors
        const hemiLight = new THREE.HemisphereLight(0x87ceeb, 0x228b22, 0.3);
        this.scene.add(hemiLight);
        this.objects.set('hemiLight', hemiLight);
    }

    // ============================================================
    // Terrain with noise displacement
    // ============================================================
    _buildTerrain() {
        const size = 200;
        const segments = 100;
        const terrainGeo = new THREE.PlaneGeometry(size, size, segments, segments);

        // Apply noise displacement for natural ground
        const posAttr = terrainGeo.attributes.position;
        for (let i = 0; i < posAttr.count; i++) {
            const x = posAttr.getX(i);
            const y = posAttr.getY(i);
            // Simple multi-octave noise
            const noise = this._noise(x * 0.05, y * 0.05) * 3.0
                        + this._noise(x * 0.1, y * 0.1) * 1.5
                        + this._noise(x * 0.2, y * 0.2) * 0.5;
            posAttr.setZ(i, noise);
        }
        terrainGeo.computeVertexNormals();

        const terrainMat = new THREE.MeshStandardMaterial({
            color: 0x228b22, // forest green
            roughness: 1.0,
            flatShading: false
        });
        const terrain = new THREE.Mesh(terrainGeo, terrainMat);
        terrain.rotation.x = -Math.PI / 2;
        terrain.position.y = 0;
        terrain.receiveShadow = true;
        this.scene.add(terrain);
        this.objects.set('terrain', terrain);
        this.terrain = terrain;

        // Soil paths between garden beds
        this._buildSoilPaths();
    }

    _buildSoilPaths() {
        const pathMat = new THREE.MeshStandardMaterial({
            color: 0x6b4c3b, // sandy dirt brown
            roughness: 1.0
        });

        // Main path down the middle
        const mainPathGeo = new THREE.PlaneGeometry(4, 80);
        const mainPath = new THREE.Mesh(mainPathGeo, pathMat);
        mainPath.rotation.x = -Math.PI / 2;
        mainPath.position.y = 0.05;
        this.scene.add(mainPath);
        this.objects.set('mainPath', mainPath);

        // Cross paths
        for (let z = -30; z <= 30; z += 20) {
            const crossGeo = new THREE.PlaneGeometry(60, 3);
            const crossPath = new THREE.Mesh(crossGeo, pathMat);
            crossPath.rotation.x = -Math.PI / 2;
            crossPath.position.set(0, 0.05, z);
            this.scene.add(crossPath);
            this.objects.set('crossPath_' + z, crossPath);
        }
    }

    // ============================================================
    // Water
    // ============================================================
    _buildWater() {
        const waterGeo = new THREE.PlaneGeometry(30, 10, 40, 20);
        const waterMat = new THREE.MeshStandardMaterial({
            color: 0x4488ff,
            transparent: true,
            opacity: 0.7,
            roughness: 0.2,
            metalness: 0.3
        });
        this.waterPlane = new THREE.Mesh(waterGeo, waterMat);
        this.waterPlane.rotation.x = -Math.PI / 2;
        this.waterPlane.position.set(0, 0.1, 40);
        this.scene.add(this.waterPlane);
        this.objects.set('water', this.waterPlane);

        // Store original Y positions for ripple animation
        const posAttr = this.waterPlane.geometry.attributes.position;
        this.waterOrigY = new Float32Array(posAttr.count);
        for (let i = 0; i < posAttr.count; i++) {
            this.waterOrigY[i] = posAttr.getZ(i);
        }
    }

    // ============================================================
    // Garden Beds, Trees, Flowers
    // ============================================================
    _buildGarden(entities) {
        // Garden bed borders (wooden fence)
        this._buildFence(-25, -20, 20, 25);
        this._buildFence(5, -20, 20, 25);
        this._buildFence(-25, 10, 20, 15);
        this._buildFence(5, 10, 20, 15);

        // Build plants from entities
        const roots = entities.filter(e => !e.parent);
        const byId = {};
        entities.forEach(e => byId[e.id] = e);

        let bedIndex = 0;
        const bedPositions = [
            { x: -15, z: -10 }, { x: 15, z: -10 },
            { x: -15, z: 17 }, { x: 15, z: 17 }
        ];

        roots.forEach((root, ri) => {
            const children = (root.children || []).map(id => byId[id]).filter(Boolean);
            const bed = bedPositions[bedIndex % bedPositions.length];
            bedIndex++;

            children.forEach((child, ci) => {
                const grandchildren = (child.children || []).map(id => byId[id]).filter(Boolean);

                grandchildren.forEach((gc, gi) => {
                    const metrics = gc.metrics || {};
                    const cpu = Math.max(0, Math.min(100, metrics.cpu || 50));
                    const stateColor = this.getStateColor(gc.state);

                    // Plant position within bed
                    const px = bed.x + (gi % 4) * 5 - 7.5;
                    const pz = bed.z + Math.floor(gi / 4) * 5 - 5;

                    // Alternate between trees and flowers
                    if (gi % 3 === 0) {
                        this._buildTree(px, pz, cpu, stateColor, gc);
                    } else if (gi % 3 === 1) {
                        this._buildFlower(px, pz, cpu, stateColor, gc);
                    } else {
                        this._buildBush(px, pz, cpu, stateColor, gc);
                    }
                });
            });
        });
    }

    _buildTree(x, z, cpu, color, entity) {
        const group = new THREE.Group();

        // Trunk: CylinderGeometry
        const trunkHeight = 4 + (cpu / 100) * 8; // Height based on CPU
        const trunkGeo = new THREE.CylinderGeometry(0.4, 0.7, trunkHeight, 8);
        const trunkMat = new THREE.MeshStandardMaterial({
            color: 0x4a3020,
            roughness: 0.9
        });
        const trunk = new THREE.Mesh(trunkGeo, trunkMat);
        trunk.position.y = trunkHeight / 2;
        trunk.castShadow = true;
        group.add(trunk);

        // Canopy: SphereGeometry, color by health
        const canopySize = 2.5 + (cpu / 100) * 2;
        const canopyGeo = new THREE.SphereGeometry(canopySize, 12, 8);
        const canopyMat = new THREE.MeshStandardMaterial({
            color: color,
            emissive: color,
            emissiveIntensity: 0.1,
            roughness: 0.8
        });
        const canopy = new THREE.Mesh(canopyGeo, canopyMat);
        canopy.position.y = trunkHeight + canopySize * 0.6;
        canopy.castShadow = true;
        group.add(canopy);

        group.position.set(x, 0, z);
        this.scene.add(group);
        this.objects.set(entity.id, group);
        this.trees.push({
            group: group,
            canopy: canopy,
            entity: entity,
            baseHeight: trunkHeight,
            baseSize: canopySize
        });
    }

    _buildFlower(x, z, cpu, color, entity) {
        const group = new THREE.Group();

        // Stem: thin cylinder
        const stemHeight = 1.5 + (cpu / 100) * 3;
        const stemGeo = new THREE.CylinderGeometry(0.1, 0.15, stemHeight, 6);
        const stemMat = new THREE.MeshStandardMaterial({
            color: 0x228b22,
            roughness: 0.8
        });
        const stem = new THREE.Mesh(stemGeo, stemMat);
        stem.position.y = stemHeight / 2;
        group.add(stem);

        // Petals: sphere at top (color by state)
        const petalSize = 0.5 + (cpu / 100) * 0.5;
        const petalGeo = new THREE.SphereGeometry(petalSize, 8, 8);
        const petalMat = new THREE.MeshStandardMaterial({
            color: color,
            emissive: color,
            emissiveIntensity: 0.2,
            roughness: 0.5
        });
        const petals = new THREE.Mesh(petalGeo, petalMat);
        petals.position.y = stemHeight + petalSize * 0.5;
        group.add(petals);

        // Leaves on stem
        const leafGeo = new THREE.SphereGeometry(0.3, 6, 4);
        leafGeo.scale(1, 0.3, 2);
        const leafMat = new THREE.MeshStandardMaterial({ color: 0x32cd32 });

        const leaf1 = new THREE.Mesh(leafGeo, leafMat);
        leaf1.position.set(0.3, stemHeight * 0.4, 0);
        leaf1.rotation.z = -0.5;
        group.add(leaf1);

        const leaf2 = new THREE.Mesh(leafGeo.clone(), leafMat);
        leaf2.position.set(-0.3, stemHeight * 0.6, 0);
        leaf2.rotation.z = 0.5;
        group.add(leaf2);

        group.position.set(x, 0, z);
        this.scene.add(group);
        this.objects.set(entity.id, group);
        this.flowers.push({
            group: group,
            petals: petals,
            entity: entity,
            baseHeight: stemHeight,
            baseSize: petalSize
        });
    }

    _buildBush(x, z, cpu, color, entity) {
        const group = new THREE.Group();

        const bushSize = 1.5 + (cpu / 100) * 2;

        // Multiple overlapping spheres for bush shape
        for (let i = 0; i < 3; i++) {
            const size = bushSize * (0.7 + Math.random() * 0.3);
            const bushGeo = new THREE.SphereGeometry(size, 8, 8);
            const bushMat = new THREE.MeshStandardMaterial({
                color: color,
                emissive: color,
                emissiveIntensity: 0.08,
                roughness: 0.9
            });
            const sphere = new THREE.Mesh(bushGeo, bushMat);
            sphere.position.set(
                (Math.random() - 0.5) * bushSize,
                size * 0.8,
                (Math.random() - 0.5) * bushSize
            );
            sphere.castShadow = true;
            group.add(sphere);
        }

        group.position.set(x, 0, z);
        this.scene.add(group);
        this.objects.set(entity.id, group);
    }

    // ============================================================
    // Fence
    // ============================================================
    _buildFence(x, z, w, h) {
        const postMat = new THREE.MeshStandardMaterial({ color: 0x8B6914, roughness: 0.9 });
        const railMat = new THREE.MeshStandardMaterial({ color: 0xA0824A, roughness: 0.8 });

        const posts = [];
        const spacing = 4;

        // Build fence around perimeter
        for (let px = x; px <= x + w; px += spacing) {
            posts.push([px, z]);
            posts.push([px, z + h]);
        }
        for (let pz = z + spacing; pz < z + h; pz += spacing) {
            posts.push([x, pz]);
            posts.push([x + w, pz]);
        }

        posts.forEach(([px, pz], i) => {
            const postGeo = new THREE.CylinderGeometry(0.15, 0.2, 2, 6);
            const post = new THREE.Mesh(postGeo, postMat);
            post.position.set(px, 1, pz);
            this.scene.add(post);
            this.objects.set('fence_post_' + i, post);
        });

        // Horizontal rails
        const railPositions = [0.6, 1.4];
        railPositions.forEach(ry => {
            // Top/bottom rails
            const hRail1Geo = new THREE.BoxGeometry(w, 0.1, 0.1);
            const hRail1 = new THREE.Mesh(hRail1Geo, railMat);
            hRail1.position.set(x + w / 2, ry, z);
            this.scene.add(hRail1);
            this.objects.set('rail_h1_' + ry, hRail1);

            const hRail2 = new THREE.Mesh(hRail1Geo.clone(), railMat);
            hRail2.position.set(x + w / 2, ry, z + h);
            this.scene.add(hRail2);
            this.objects.set('rail_h2_' + ry, hRail2);

            const vRail1Geo = new THREE.BoxGeometry(0.1, 0.1, h);
            const vRail1 = new THREE.Mesh(vRail1Geo, railMat);
            vRail1.position.set(x, ry, z + h / 2);
            this.scene.add(vRail1);
            this.objects.set('rail_v1_' + ry, vRail1);

            const vRail2 = new THREE.Mesh(vRail1Geo.clone(), railMat);
            vRail2.position.set(x + w, ry, z + h / 2);
            this.scene.add(vRail2);
            this.objects.set('rail_v2_' + ry, vRail2);
        });
    }

    // ============================================================
    // Fireflies (200 Points with glow)
    // ============================================================
    _buildFireflies() {
        const count = 200;
        const positions = new Float32Array(count * 3);
        const sizes = new Float32Array(count);

        for (let i = 0; i < count; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 120;
            positions[i * 3 + 1] = 1 + Math.random() * 15;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 120;
            sizes[i] = 0.5 + Math.random() * 1.5;
        }

        const geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geo.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

        const mat = new THREE.ShaderMaterial({
            uniforms: {
                time: { value: 0 },
                color: { value: new THREE.Color(0xffd700) },
                opacity: { value: 0.8 }
            },
            vertexShader: `
                attribute float size;
                uniform float time;
                varying float vAlpha;
                void main() {
                    vec3 pos = position;
                    // Animate position
                    pos.x += sin(time * 0.5 + position.z * 0.1) * 2.0;
                    pos.y += sin(time * 0.7 + position.x * 0.1) * 1.0;
                    pos.z += cos(time * 0.3 + position.y * 0.1) * 2.0;
                    
                    // Pulse alpha
                    vAlpha = 0.3 + 0.7 * abs(sin(time * 2.0 + position.x * 0.5));
                    
                    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
                    gl_PointSize = size * (300.0 / -mvPosition.z);
                    gl_Position = projectionMatrix * mvPosition;
                }
            `,
            fragmentShader: `
                uniform vec3 color;
                uniform float opacity;
                varying float vAlpha;
                void main() {
                    // Circular glow
                    vec2 center = gl_PointCoord - vec2(0.5);
                    float dist = length(center);
                    if (dist > 0.5) discard;
                    
                    float glow = 1.0 - dist * 2.0;
                    glow = pow(glow, 2.0);
                    
                    gl_FragColor = vec4(color, glow * vAlpha * opacity);
                }
            `,
            transparent: true,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });

        this.fireflies = new THREE.Points(geo, mat);
        this.fireflyPositions = positions;
        this.scene.add(this.fireflies);
        this.objects.set('fireflies', this.fireflies);
    }

    // ============================================================
    // Noise function for terrain
    // ============================================================
    _noise(x, y) {
        // Simple value noise with hash
        const ix = Math.floor(x);
        const iy = Math.floor(y);
        const fx = x - ix;
        const fy = y - iy;

        const sx = fx * fx * (3 - 2 * fx);
        const sy = fy * fy * (3 - 2 * fy);

        const n00 = this._hash(ix, iy);
        const n10 = this._hash(ix + 1, iy);
        const n01 = this._hash(ix, iy + 1);
        const n11 = this._hash(ix + 1, iy + 1);

        const nx0 = n00 + (n10 - n00) * sx;
        const nx1 = n01 + (n11 - n01) * sx;

        return nx0 + (nx1 - nx0) * sy;
    }

    _hash(x, y) {
        let n = x * 127 + y * 311;
        n = (n << 13) ^ n;
        return ((n * (n * n * 15731 + 789221) + 1376312589) & 0x7fffffff) / 2147483647.0 * 2 - 1;
    }

    // ============================================================
    // State color mapping
    // ============================================================
    getStateColor(state) {
        const colors = {
            healthy: 0x4ade80,  // bright green
            running: 0x22c55e,  // vibrant green
            idle: 0x86efac,     // pale green
            warning: 0xfbbf24,  // yellowing
            degraded: 0xeab308, // sickly yellow
            critical: 0x92400e, // brown/dying
            stopped: 0x78350f,  // dead brown
            pending: 0xa3e635,  // sprouting lime
            scaling: 0x34d399,  // growing green
            unknown: 0x6b7280   // grey
        };
        return colors[state] || colors.unknown;
    }

    // ============================================================
    // Update / Animation
    // ============================================================
    update(deltaTime, entities) {
        const now = performance.now() / 1000 - this.startTime;

        // Time of day (1 full cycle = 60 seconds for demo)
        this.timeOfDay = (now / 60) % 1.0;
        this._updateSunPosition(now);
        this._updateSkyColors();

        // Water ripple animation
        this._animateWater(now);

        // Firefly animation (brighter at night)
        this._animateFireflies(now);

        // Animate trees (subtle sway)
        this.trees.forEach(t => {
            const sway = Math.sin(now * 0.5 + t.entity.id.length) * 0.02;
            t.group.rotation.z = sway;
        });

        // Animate flowers (gentle bobbing)
        this.flowers.forEach(f => {
            const bob = Math.sin(now * 1.5 + f.entity.id.length) * 0.1;
            f.petals.position.y = f.baseHeight + f.baseSize * 0.5 + bob;
        });
    }

    _updateSunPosition(now) {
        // Sun arcs across sky: 0.25 = dawn, 0.5 = noon, 0.75 = dusk
        const tod = this.timeOfDay;
        let sunAngle;
        if (tod < 0.25 || tod > 0.833) {
            // Night - sun below horizon
            this.sunMesh.position.set(-200, -50, -100);
            this.sunLight.position.set(0, -10, 0);
            this.sunLight.intensity = 0.1;
        } else {
            // Day - sun arcs
            const t = (tod - 0.25) / 0.583;
            sunAngle = Math.PI * t;
            const x = -100 + 200 * t;
            const y = Math.sin(sunAngle) * 80;
            const z = -100;
            this.sunMesh.position.set(x, y, z);
            this.sunLight.position.copy(this.sunMesh.position);
            this.sunLight.intensity = 0.5 + Math.sin(sunAngle) * 0.5;

            // Sun color changes with time
            if (tod < 0.35 || tod > 0.75) {
                this.sunMesh.material.color.setHex(0xff6600); // orange at dawn/dusk
                this.sunLight.color.setHex(0xff8844);
            } else {
                this.sunMesh.material.color.setHex(0xffd700); // gold at noon
                this.sunLight.color.setHex(0xffeecc);
            }
        }
    }

    _updateSkyColors() {
        if (!this.skyMaterial) return;
        const tod = this.timeOfDay;

        let topColor, bottomColor;
        if (tod < 0.25) {
            // Night
            topColor = new THREE.Color(0x1a0a2e);
            bottomColor = new THREE.Color(0x2d1b4e);
        } else if (tod < 0.35) {
            // Dawn
            const t = (tod - 0.25) / 0.1;
            topColor = new THREE.Color(0x1a0a2e).lerp(new THREE.Color(0xff7e5f), t);
            bottomColor = new THREE.Color(0x2d1b4e).lerp(new THREE.Color(0xfeb47b), t);
        } else if (tod < 0.45) {
            // Morning
            const t = (tod - 0.35) / 0.1;
            topColor = new THREE.Color(0xff7e5f).lerp(new THREE.Color(0x87ceeb), t);
            bottomColor = new THREE.Color(0xfeb47b).lerp(new THREE.Color(0xb0e0e6), t);
        } else if (tod < 0.75) {
            // Day
            topColor = new THREE.Color(0x87ceeb);
            bottomColor = new THREE.Color(0xb0e0e6);
        } else if (tod < 0.833) {
            // Sunset
            const t = (tod - 0.75) / 0.083;
            topColor = new THREE.Color(0x87ceeb).lerp(new THREE.Color(0xff7e5f), t);
            bottomColor = new THREE.Color(0xb0e0e6).lerp(new THREE.Color(0xfeb47b), t);
        } else {
            // Dusk to night
            const t = (tod - 0.833) / 0.167;
            topColor = new THREE.Color(0xff7e5f).lerp(new THREE.Color(0x1a0a2e), t);
            bottomColor = new THREE.Color(0xfeb47b).lerp(new THREE.Color(0x2d1b4e), t);
        }

        this.skyMaterial.uniforms.topColor.value.copy(topColor);
        this.skyMaterial.uniforms.bottomColor.value.copy(bottomColor);
    }

    _animateWater(now) {
        if (!this.waterPlane) return;
        const posAttr = this.waterPlane.geometry.attributes.position;
        for (let i = 0; i < posAttr.count; i++) {
            const x = posAttr.getX(i);
            const y = posAttr.getY(i);
            const ripple = Math.sin(x * 0.5 + now * 2) * 0.1
                         + Math.cos(y * 0.3 + now * 1.5) * 0.08;
            posAttr.setZ(i, this.waterOrigY[i] + ripple);
        }
        posAttr.needsUpdate = true;
    }

    _animateFireflies(now) {
        if (!this.fireflies) return;

        // Fireflies brighter at night
        const tod = this.timeOfDay;
        const nightFactor = (tod < 0.3 || tod > 0.8) ? 1.0 : 0.2;
        this.fireflies.material.uniforms.time.value = now;
        this.fireflies.material.uniforms.opacity.value = nightFactor * 0.8;
    }
}

window.GardenMetaphor = GardenMetaphor;
