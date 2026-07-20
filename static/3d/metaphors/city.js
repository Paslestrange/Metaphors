// City 3D Metaphor — Dense, Architecturally Varied, State-Colored
class CityMetaphor extends Base3DMetaphor {
    constructor() {
        super();
        this.name = 'city';
        this.buildings = [];
        this.startTime = performance.now() / 1000;
        this.seed = 42;
    }

    // Simple seeded random for reproducible layouts
    _random() {
        this.seed = (this.seed * 16807 + 0) % 2147483647;
        return (this.seed - 1) / 2147483646;
    }

    _randRange(min, max) {
        return min + this._random() * (max - min);
    }

    _randInt(min, max) {
        return Math.floor(this._randRange(min, max + 1));
    }

    _pick(arr) {
        return arr[this._randInt(0, arr.length - 1)];
    }

    getDefaultCameraPosition() {
        return { x: 35, y: 28, z: 65 };
    }

    getDefaultCameraTarget() {
        return { x: 0, y: 6, z: 0 };
    }

    getStateColor(state) {
        const colors = {
            healthy:  0x22c55e,
            running:  0x3b82f6,
            idle:     0x9ca3af,
            warning:  0xf59e0b,
            degraded: 0xf97316,
            critical: 0xef4444,
            stopped:  0x6b7280,
            pending:  0xa78bfa,
            scaling:  0x06b6d4,
            unknown:  0x6b7280
        };
        return colors[state] || colors.unknown;
    }

    getStateColorHex(state) {
        const colors = {
            healthy:  '#22c55e',
            running:  '#3b82f6',
            idle:     '#9ca3af',
            warning:  '#f59e0b',
            degraded: '#f99316',
            critical: '#ef4444',
            stopped:  '#6b7280',
            pending:  '#a78bfa',
            scaling:  '#06b6d4',
            unknown:  '#6b7280'
        };
        return colors[state] || colors.unknown;
    }

    // Generate a window texture — brighter, more visible windows
    _makeWindowTexture(stateColor, stateColorInt, width, height, style) {
        var canvas = document.createElement('canvas');
        canvas.width = 128;
        canvas.height = 256;
        var ctx = canvas.getContext('2d');

        // Wall color — dark but with state color tint
        var r = (stateColorInt >> 16) & 0xff;
        var g = (stateColorInt >> 8) & 0xff;
        var b = stateColorInt & 0xff;
        // Tint wall with 15% state color
        var wallR = Math.floor(20 + r * 0.15);
        var wallG = Math.floor(20 + g * 0.15);
        var wallB = Math.floor(25 + b * 0.15);
        ctx.fillStyle = 'rgb(' + wallR + ',' + wallG + ',' + wallB + ')';
        ctx.fillRect(0, 0, 128, 256);

        // Window grid
        var windowRows, windowCols, windowW, windowH, gapX, gapY;

        if (style === 'grid') {
            windowRows = this._randInt(8, 16);
            windowCols = this._randInt(4, 8);
            windowW = Math.floor(110 / windowCols);
            windowH = Math.floor(220 / windowRows);
            gapX = Math.floor((128 - windowCols * windowW) / (windowCols + 1));
            gapY = Math.floor((256 - windowRows * windowH) / (windowRows + 1));

            for (var row = 0; row < windowRows; row++) {
                for (var col = 0; col < windowCols; col++) {
                    var lit = this._random() < 0.7;
                    if (lit) {
                        ctx.fillStyle = stateColor;
                        ctx.globalAlpha = 0.5 + this._random() * 0.5;
                    } else {
                        ctx.fillStyle = '#080810';
                        ctx.globalAlpha = 0.9;
                    }
                    var wx = gapX + col * (windowW + gapX);
                    var wy = gapY + row * (windowH + gapY);
                    ctx.fillRect(wx, wy, windowW - 1, windowH - 1);
                }
            }
        } else if (style === 'stripes') {
            var numBands = this._randInt(5, 10);
            var bandH = Math.floor(220 / numBands);
            for (var band = 0; band < numBands; band++) {
                var by = 15 + band * (bandH + 5);
                ctx.fillStyle = stateColor;
                ctx.globalAlpha = 0.35 + this._random() * 0.35;
                ctx.fillRect(6, by, 116, bandH - 3);
                // Divisions
                ctx.fillStyle = 'rgb(' + wallR + ',' + wallG + ',' + wallB + ')';
                ctx.globalAlpha = 1.0;
                var divs = this._randInt(3, 6);
                for (var d = 0; d < divs; d++) {
                    var dx = 6 + Math.floor((d + 1) * 116 / (divs + 1));
                    ctx.fillRect(dx - 1, by, 2, bandH - 3);
                }
            }
        } else if (style === 'scattered') {
            for (var i = 0; i < 80; i++) {
                var wx2 = this._randInt(2, 122);
                var wy2 = this._randInt(2, 250);
                var ww = this._randInt(5, 14);
                var wh = this._randInt(4, 12);
                var lit2 = this._random() < 0.6;
                ctx.fillStyle = lit2 ? stateColor : '#080810';
                ctx.globalAlpha = lit2 ? (0.5 + this._random() * 0.5) : 0.9;
                ctx.fillRect(wx2, wy2, ww, wh);
            }
        } else {
            // 'modern' — large glass panels
            var panelRows = this._randInt(4, 8);
            var panelH = Math.floor(230 / panelRows);
            for (var p = 0; p < panelRows; p++) {
                var py = 12 + p * (panelH + 4);
                ctx.fillStyle = stateColor;
                ctx.globalAlpha = 0.35;
                ctx.fillRect(4, py, 120, panelH - 2);
                // Reflection highlight
                ctx.fillStyle = '#ffffff';
                ctx.globalAlpha = 0.08;
                ctx.fillRect(4, py, 50, panelH - 2);
            }
        }

        ctx.globalAlpha = 1.0;
        return new THREE.CanvasTexture(canvas);
    }

    // Generate rooftop texture
    _makeRooftopTexture() {
        var canvas = document.createElement('canvas');
        canvas.width = 64;
        canvas.height = 64;
        var ctx = canvas.getContext('2d');
        ctx.fillStyle = '#141420';
        ctx.fillRect(0, 0, 64, 64);
        for (var i = 0; i < this._randInt(1, 4); i++) {
            ctx.fillStyle = '#2a2a3a';
            var rx = this._randInt(4, 48);
            var ry = this._randInt(4, 48);
            ctx.fillRect(rx, ry, this._randInt(6, 14), this._randInt(6, 14));
        }
        return new THREE.CanvasTexture(canvas);
    }

    // Create a building with architectural variety
    _createBuilding(x, z, cellSize, state, entity, index) {
        var group = new THREE.Group();
        var stateColor = this.getStateColor(state);
        var stateColorHex = this.getStateColorHex(state);

        // Building dimensions
        var maxW = cellSize * 0.85;
        var maxD = cellSize * 0.85;
        var bWidth = this._randRange(maxW * 0.5, maxW * 0.95);
        var bDepth = this._randRange(maxD * 0.5, maxD * 0.95);

        // MUCH more height variation — real city has skyscrapers
        var bHeight;
        var heightRoll = this._random();
        if (heightRoll < 0.1) {
            // Skyscraper (10%)
            bHeight = this._randRange(45, 80);
        } else if (heightRoll < 0.3) {
            // Tall (20%)
            bHeight = this._randRange(25, 45);
        } else if (heightRoll < 0.6) {
            // Medium (30%)
            bHeight = this._randRange(12, 25);
        } else if (heightRoll < 0.85) {
            // Short (25%)
            bHeight = this._randRange(5, 12);
        } else {
            // Low (15%)
            bHeight = this._randRange(3, 6);
        }

        // State modifies height
        if (state === 'critical') bHeight = Math.min(bHeight, 8);
        else if (state === 'warning') bHeight = Math.min(bHeight, 15);
        else if (state === 'healthy' || state === 'running') bHeight *= 1.2;

        // Choose architectural style
        var style = this._randInt(0, 4);
        var windowStyle = this._pick(['grid', 'stripes', 'scattered', 'modern']);

        // Window texture for walls
        var windowTex = this._makeWindowTexture(stateColorHex, stateColor, bWidth, bHeight, windowStyle);
        windowTex.wrapS = THREE.RepeatWrapping;
        windowTex.wrapT = THREE.RepeatWrapping;

        var rooftopTex = this._makeRooftopTexture();

        if (style === 0) {
            // Simple box tower
            var geo = new THREE.BoxGeometry(bWidth, bHeight, bDepth);
            var materials = [
                new THREE.MeshStandardMaterial({ map: windowTex, roughness: 0.7, metalness: 0.3, emissive: stateColor, emissiveIntensity: 0.12 }),
                new THREE.MeshStandardMaterial({ map: windowTex, roughness: 0.7, metalness: 0.3, emissive: stateColor, emissiveIntensity: 0.12 }),
                new THREE.MeshStandardMaterial({ map: rooftopTex, roughness: 0.9, metalness: 0.1 }),
                new THREE.MeshStandardMaterial({ color: 0x111118, roughness: 0.9 }),
                new THREE.MeshStandardMaterial({ map: windowTex, roughness: 0.7, metalness: 0.3, emissive: stateColor, emissiveIntensity: 0.12 }),
                new THREE.MeshStandardMaterial({ map: windowTex, roughness: 0.7, metalness: 0.3, emissive: stateColor, emissiveIntensity: 0.12 }),
            ];
            var mesh = new THREE.Mesh(geo, materials);
            mesh.position.y = bHeight / 2;
            group.add(mesh);

        } else if (style === 1) {
            // Stepped / tiered tower
            var tiers = this._randInt(2, 4);
            var currentH = 0;
            var currentW = bWidth;
            var currentD = bDepth;
            for (var t = 0; t < tiers; t++) {
                var tierH = bHeight / tiers * this._randRange(0.6, 1.4);
                var geo = new THREE.BoxGeometry(currentW, tierH, currentD);
                var mat = new THREE.MeshStandardMaterial({
                    map: windowTex,
                    roughness: 0.6,
                    metalness: 0.4,
                    emissive: stateColor,
                    emissiveIntensity: 0.08 + t * 0.04
                });
                var mesh = new THREE.Mesh(geo, mat);
                mesh.position.y = currentH + tierH / 2;
                group.add(mesh);
                currentH += tierH;
                currentW *= this._randRange(0.55, 0.75);
                currentD *= this._randRange(0.55, 0.75);
            }
            bHeight = currentH;

        } else if (style === 2) {
            // Cylinder tower
            var segments = this._randInt(8, 16);
            var geo = new THREE.CylinderGeometry(bWidth / 2, bWidth / 2, bHeight, segments);
            var mat = new THREE.MeshStandardMaterial({
                map: windowTex,
                roughness: 0.6,
                metalness: 0.4,
                emissive: stateColor,
                emissiveIntensity: 0.12
            });
            var mesh = new THREE.Mesh(geo, mat);
            mesh.position.y = bHeight / 2;
            group.add(mesh);

            // Cone top
            var coneGeo = new THREE.ConeGeometry(bWidth / 2 + 0.5, 3, segments);
            var coneMat = new THREE.MeshStandardMaterial({
                color: 0x2a2a3a,
                roughness: 0.8,
                metalness: 0.3
            });
            var cone = new THREE.Mesh(coneGeo, coneMat);
            cone.position.y = bHeight + 1.5;
            group.add(cone);
            bHeight += 3;

        } else if (style === 3) {
            // L-shaped building (two boxes)
            var halfW = bWidth * 0.5;
            var halfD = bDepth * 0.5;
            var mat = new THREE.MeshStandardMaterial({
                map: windowTex,
                roughness: 0.7,
                metalness: 0.3,
                emissive: stateColor,
                emissiveIntensity: 0.1
            });

            var geo1 = new THREE.BoxGeometry(bWidth, bHeight, halfD);
            var mesh1 = new THREE.Mesh(geo1, mat);
            mesh1.position.set(0, bHeight / 2, -halfD / 2);
            group.add(mesh1);

            var h2 = bHeight * this._randRange(0.5, 0.8);
            var geo2 = new THREE.BoxGeometry(halfW, h2, bDepth);
            var mesh2 = new THREE.Mesh(geo2, mat);
            mesh2.position.set(bWidth / 2 - halfW / 2, h2 / 2, 0);
            group.add(mesh2);

        } else {
            // Wide low building (warehouse/datacenter style)
            bHeight = this._randRange(3, 8);
            bWidth *= 1.3;
            bDepth *= 1.3;
            var geo = new THREE.BoxGeometry(bWidth, bHeight, bDepth);
            var mat = new THREE.MeshStandardMaterial({
                map: windowTex,
                roughness: 0.8,
                metalness: 0.2,
                emissive: stateColor,
                emissiveIntensity: 0.1
            });
            var mesh = new THREE.Mesh(geo, mat);
            mesh.position.y = bHeight / 2;
            group.add(mesh);
        }

        // Rooftop details — antennas, AC units
        if (bHeight > 12 && this._random() < 0.6) {
            var antennaH = this._randRange(2, 6);
            var antennaGeo = new THREE.CylinderGeometry(0.1, 0.15, antennaH, 6);
            var antennaMat = new THREE.MeshStandardMaterial({ color: 0x888888, metalness: 0.8, roughness: 0.3 });
            var antenna = new THREE.Mesh(antennaGeo, antennaMat);
            antenna.position.set(this._randRange(-bWidth * 0.2, bWidth * 0.2), bHeight + antennaH / 2, this._randRange(-bDepth * 0.2, bDepth * 0.2));
            group.add(antenna);

            // Blinking light on top
            var lightGeo = new THREE.SphereGeometry(0.3, 8, 8);
            var lightMat = new THREE.MeshBasicMaterial({ color: 0xff0000 });
            var light = new THREE.Mesh(lightGeo, lightMat);
            light.position.set(antenna.position.x, bHeight + antennaH + 0.3, antenna.position.z);
            group.add(light);
        }

        // AC units on rooftop
        if (this._random() < 0.5) {
            var numAC = this._randInt(1, 3);
            for (var a = 0; a < numAC; a++) {
                var acGeo = new THREE.BoxGeometry(1.2, 0.8, 1.2);
                var acMat = new THREE.MeshStandardMaterial({ color: 0x555566, roughness: 0.6, metalness: 0.5 });
                var ac = new THREE.Mesh(acGeo, acMat);
                ac.position.set(
                    this._randRange(-bWidth * 0.3, bWidth * 0.3),
                    bHeight + 0.4,
                    this._randRange(-bDepth * 0.3, bDepth * 0.3)
                );
                group.add(ac);
            }
        }

        // State-colored base/foundation glow strip
        var baseGeo = new THREE.BoxGeometry(bWidth + 0.6, 0.5, bDepth + 0.6);
        var baseMat = new THREE.MeshStandardMaterial({
            color: stateColor,
            emissive: stateColor,
            emissiveIntensity: 0.8,
            roughness: 0.3,
            metalness: 0.5
        });
        var base = new THREE.Mesh(baseGeo, baseMat);
        base.position.y = 0.25;
        group.add(base);

        group.position.set(x, 0, z);

        // Store metadata for animation
        group.userData = {
            entity: entity,
            state: state,
            stateColor: stateColor,
            height: bHeight,
            baseY: 0,
            index: index
        };

        return group;
    }

    buildScene(entities) {
        if (!this.scene) return;
        this.seed = 42;

        // Clear existing buildings
        this.buildings.forEach(function(b) {
            if (b.group) this.scene.remove(b.group);
        }.bind(this));
        this.buildings = [];

        // === GROUND — city footprint
        var gridSize = 100;
        var groundGeo = new THREE.PlaneGeometry(gridSize, gridSize);
        var groundMat = new THREE.MeshStandardMaterial({
            color: 0x0d0d22,
            roughness: 0.8
        });
        var ground = new THREE.Mesh(groundGeo, groundMat);
        ground.rotation.x = -Math.PI / 2;
        ground.position.y = 0;
        this.scene.add(ground);
        this.objects.set('ground', ground);

        // Grid lines on ground
        var gridHelper = new THREE.GridHelper(gridSize, 25, 0x1a1a3e, 0x111128);
        gridHelper.position.y = 0.01;
        this.scene.add(gridHelper);
        this.objects.set('gridHelper', gridHelper);

        // === SKY / ATMOSPHERE ===
        this.scene.background = new THREE.Color(0x06061a);
        this.scene.fog = new THREE.FogExp2(0x0a0820, 0.003);

        // Sky dome
        var skyGeo = new THREE.SphereGeometry(300, 32, 32);
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

        // Stars
        var starGeo = new THREE.BufferGeometry();
        var starCount = 2000;
        var starPos = new Float32Array(starCount * 3);
        var starSizes = new Float32Array(starCount);
        for (var s = 0; s < starCount; s++) {
            var theta = Math.random() * Math.PI * 2;
            var phi = Math.random() * Math.PI * 0.4;
            var r = 200 + Math.random() * 80;
            starPos[s*3]   = r * Math.sin(phi) * Math.cos(theta);
            starPos[s*3+1] = r * Math.cos(phi);
            starPos[s*3+2] = r * Math.sin(phi) * Math.sin(theta);
            starSizes[s] = Math.random() < 0.05 ? Math.random()*1.5+1.5 : Math.random()*0.8+0.3;
        }
        starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
        starGeo.setAttribute('size', new THREE.BufferAttribute(starSizes, 1));
        this.objects.set('stars', new THREE.Points(starGeo, new THREE.PointsMaterial({
            size: 1.2, sizeAttenuation: true, transparent: true, opacity: 1.0,
            color: 0xeeeeff, blending: THREE.AdditiveBlending, depthWrite: false
        })));
        this.scene.add(this.objects.get('stars'));

        // Rain
        var rainGeo = new THREE.BufferGeometry();
        var rainCount = 5000;
        var rainPos = new Float32Array(rainCount * 3);
        for (var rr = 0; rr < rainCount; rr++) {
            rainPos[rr*3]   = (Math.random()-0.5) * 150;
            rainPos[rr*3+1] = Math.random() * 100;
            rainPos[rr*3+2] = (Math.random()-0.5) * 150;
        }
        rainGeo.setAttribute('position', new THREE.BufferAttribute(rainPos, 3));
        this.objects.set('rainGeo', rainGeo);
        this.objects.set('rainCount', rainCount);
        this.objects.set('rain', new THREE.Points(rainGeo, new THREE.PointsMaterial({
            color: 0x99aadd, size: 0.5, sizeAttenuation: true, transparent: true, opacity: 0.6,
            blending: THREE.AdditiveBlending, depthWrite: false
        })));
        this.scene.add(this.objects.get('rain'));

        // Lighting — brighter to see buildings
        var ambientLight = new THREE.AmbientLight(0x333355, 0.8);
        this.scene.add(ambientLight);
        this.objects.set('ambientLight', ambientLight);

        var dirLight = new THREE.DirectionalLight(0x5555aa, 0.6);
        dirLight.position.set(50, 100, 50);
        this.scene.add(dirLight);
        this.objects.set('dirLight', dirLight);

        // Stronger accent point lights for neon feel
        var accentColors = [0xff00ff, 0x00ffff, 0xff6600];
        for (var al = 0; al < 5; al++) {
            var pl = new THREE.PointLight(accentColors[al % 3], 0.5, 80);
            pl.position.set(this._randRange(-40, 40), 20, this._randRange(-40, 40));
            this.scene.add(pl);
        }

        // === BUILD CITY FROM ENTITIES ===
        var byId = {};
        entities.forEach(function(e) { byId[e.id] = e; });
        var serviceEntities = entities.filter(function(e) {
            return e.type === 'service' || (e.children && e.children.length === 0);
        });

        // Target: 60+ buildings for density
        var minBuildings = 60;
        var fillerCount = Math.max(0, minBuildings - serviceEntities.length);
        var totalBuildings = serviceEntities.length + fillerCount;

        // Layout: tighter packing
        var cellSize = gridSize / Math.ceil(Math.sqrt(totalBuildings));
        cellSize = Math.max(cellSize, 2.5);
        cellSize = Math.min(cellSize, 8);

        var gridCols = Math.floor(gridSize / cellSize);
        var gridRows = Math.floor(gridSize / cellSize);
        var startX = -(gridCols * cellSize) / 2 + cellSize / 2;
        var startZ = -(gridRows * cellSize) / 2 + cellSize / 2;

        var buildingIndex = 0;
        var occupiedCells = {};

        // Place real service buildings first
        var row = 0, col = 0;
        serviceEntities.forEach(function(entity, idx) {
            var metrics = entity.metrics || {};
            var state = entity.state || 'unknown';

            // Find next available cell
            while (occupiedCells[row + ',' + col] && col < gridCols) {
                col++;
                if (col >= gridCols) { col = 0; row++; }
            }
            if (row >= gridRows) return;

            var x = startX + col * cellSize + (Math.random() - 0.5) * cellSize * 0.15;
            var z = startZ + row * cellSize + (Math.random() - 0.5) * cellSize * 0.15;
            occupiedCells[row + ',' + col] = true;

            var building = this._createBuilding(x, z, cellSize, state, entity, buildingIndex);
            this.scene.add(building);
            this.buildings.push({ group: building, entity: entity, index: buildingIndex });
            this.objects.set(entity.id, building);
            buildingIndex++;

            col++;
            if (col >= gridCols) { col = 0; row++; }
        }.bind(this));

        // Place filler/background buildings for density
        for (var f = 0; f < fillerCount; f++) {
            while (occupiedCells[row + ',' + col] && col < gridCols) {
                col++;
                if (col >= gridCols) { col = 0; row++; }
            }
            if (row >= gridRows) break;

            var x2 = startX + col * cellSize + (Math.random() - 0.5) * cellSize * 0.15;
            var z2 = startZ + row * cellSize + (Math.random() - 0.5) * cellSize * 0.15;
            occupiedCells[row + ',' + col] = true;

            // Filler buildings — random state
            var fillerStates = ['idle', 'idle', 'idle', 'healthy', 'running', 'stopped'];
            var fillerState = this._pick(fillerStates);
            var fillerEntity = {
                id: 'filler_' + f,
                state: fillerState,
                metrics: { cpu: this._randRange(10, 60), mem: this._randRange(10, 60) },
                name: 'building_' + f
            };

            var filler = this._createBuilding(x2, z2, cellSize, fillerState, fillerEntity, buildingIndex);
            this.scene.add(filler);
            this.buildings.push({ group: filler, entity: fillerEntity, index: buildingIndex });
            buildingIndex++;

            col++;
            if (col >= gridCols) { col = 0; row++; }
        }

        // === ROADS — between building rows every 3 rows ===
        var roadMat = new THREE.MeshStandardMaterial({ color: 0x111128, roughness: 0.9 });
        for (var rz = 0; rz < gridRows; rz += 3) {
            var roadGeo = new THREE.PlaneGeometry(gridSize, 1.2);
            var road = new THREE.Mesh(roadGeo, roadMat);
            road.rotation.x = -Math.PI / 2;
            road.position.set(0, 0.02, startZ + rz * cellSize - cellSize * 0.1);
            this.scene.add(road);

            // Road lane markings
            var markMat = new THREE.MeshBasicMaterial({ color: 0x444466 });
            for (var m = 0; m < 12; m++) {
                var markGeo = new THREE.PlaneGeometry(1.5, 0.15);
                var mark = new THREE.Mesh(markGeo, markMat);
                mark.rotation.x = -Math.PI / 2;
                mark.position.set(startX + m * cellSize * 1.3, 0.03, startZ + rz * cellSize - cellSize * 0.1);
                this.scene.add(mark);
            }
        }
    }

    update(deltaTime, entities) {
        var now = performance.now() / 1000 - this.startTime;

        // Animate rain
        var rain = this.objects.get('rain');
        if (rain) {
            var positions = rain.geometry.attributes.position.array;
            var count = this.objects.get('rainCount') || 5000;
            for (var i = 0; i < count; i++) {
                positions[i * 3 + 1] -= 1.5;
                if (positions[i * 3 + 1] < 0) {
                    positions[i * 3 + 1] = 100;
                }
            }
            rain.geometry.attributes.position.needsUpdate = true;
        }

        // Animate buildings — pulse critical/warning, glow base
        this.buildings.forEach(function(b) {
            if (!b.group) return;
            var state = b.entity.state;
            var group = b.group;

            group.traverse(function(child) {
                if (child.isMesh && child.material && child.material.emissiveIntensity !== undefined) {
                    if (state === 'critical') {
                        child.material.emissiveIntensity = 0.3 + 0.5 * Math.sin(now * 4 + b.index * 0.7);
                    } else if (state === 'warning') {
                        child.material.emissiveIntensity = 0.2 + 0.3 * Math.sin(now * 2.5 + b.index * 0.5);
                    } else if (state === 'healthy' || state === 'running') {
                        child.material.emissiveIntensity = 0.1 + 0.06 * Math.sin(now * 0.8 + b.index * 0.3);
                    }
                }
            });
        });
    }
}

window.CityMetaphor = CityMetaphor;
