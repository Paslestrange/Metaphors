// static/space3d.js - Three.js 3D Space Station Renderer
(function() {
    'use strict';

    // State colors matching Python backend
    const STATE_COLORS = {
        healthy: 0x4ade80,
        running: 0x60a5fa,
        idle: 0x94a3b8,
        warning: 0xfbbf24,
        degraded: 0xf97316,
        critical: 0xef4444,
        stopped: 0x374151,
        pending: 0xa78bfa,
        scaling: 0x06b6d4,
        unknown: 0x6b7280,
    };

    // Three.js scene objects
    let scene, camera, renderer, clock;
    let stationGroup, modules = [], services = [], containers = [];
    let starField, nebula;
    let hubLight, emergencyLights = [];
    let animationId = null;

    // Entity data cache
    let entities = [];
    let layout = {};

    // Initialize Three.js scene
    function initScene(container) {
        const width = container.clientWidth;
        const height = container.clientHeight;

        // Scene
        scene = new THREE.Scene();
        scene.background = new THREE.Color(0x000011);

        // Camera
        camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
        camera.position.set(0, 50, 150);
        camera.lookAt(0, 0, 0);

        // Renderer
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(width, height);
        renderer.setPixelRatio(window.devicePixelRatio);
        container.appendChild(renderer.domElement);

        // Clock for animations
        clock = new THREE.Clock();

        // Lighting
        const ambientLight = new THREE.AmbientLight(0x404040, 0.3);
        scene.add(ambientLight);

        // Hub central light (warm white)
        hubLight = new THREE.PointLight(0xfff4e6, 2, 200);
        hubLight.position.set(0, 0, 0);
        scene.add(hubLight);

        // Station group
        stationGroup = new THREE.Group();
        scene.add(stationGroup);

        // Create background elements
        createStarField();
        createNebula();

        // Handle resize
        window.addEventListener('resize', () => {
            const w = container.clientWidth;
            const h = container.clientHeight;
            camera.aspect = w / h;
            camera.updateProjectionMatrix();
            renderer.setSize(w, h);
        });
    }

    // Create star field (2000 points in a sphere)
    function createStarField() {
        const starCount = 2000;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(starCount * 3);
        const colors = new Float32Array(starCount * 3);

        for (let i = 0; i < starCount; i++) {
            // Random position in sphere
            const radius = 300 + Math.random() * 200;
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(2 * Math.random() - 1);

            positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
            positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
            positions[i * 3 + 2] = radius * Math.cos(phi);

            // Slight color variation
            const brightness = 0.7 + Math.random() * 0.3;
            colors[i * 3] = brightness;
            colors[i * 3 + 1] = brightness;
            colors[i * 3 + 2] = brightness + Math.random() * 0.1;
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        const material = new THREE.PointsMaterial({
            size: 1.5,
            vertexColors: true,
            transparent: true,
            opacity: 0.8,
        });

        starField = new THREE.Points(geometry, material);
        scene.add(starField);
    }

    // Create nebula (large transparent sphere with gradient)
    function createNebula() {
        const geometry = new THREE.SphereGeometry(250, 32, 32);
        
        // Create gradient texture
        const canvas = document.createElement('canvas');
        canvas.width = 512;
        canvas.height = 512;
        const ctx = canvas.getContext('2d');
        
        const gradient = ctx.createRadialGradient(256, 256, 0, 256, 256, 256);
        gradient.addColorStop(0, 'rgba(30, 20, 60, 0.3)');
        gradient.addColorStop(0.5, 'rgba(20, 10, 40, 0.15)');
        gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
        
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 512, 512);
        
        const texture = new THREE.CanvasTexture(canvas);
        
        const material = new THREE.MeshBasicMaterial({
            map: texture,
            transparent: true,
            opacity: 0.4,
            side: THREE.BackSide,
        });

        nebula = new THREE.Mesh(geometry, material);
        scene.add(nebula);
    }

    // Create central hub (large cylinder, glowing blue)
    function createHub(entity, layoutData) {
        const cpu = (entity.metrics?.cpu || 50) / 100;
        const radius = 8 + cpu * 6;
        const height = 20 + cpu * 10;

        const geometry = new THREE.CylinderGeometry(radius, radius, height, 32);
        const material = new THREE.MeshStandardMaterial({
            color: 0x2a2a3e,
            emissive: 0x4488ff,
            emissiveIntensity: 0.5 + cpu * 0.5,
            metalness: 0.8,
            roughness: 0.3,
        });

        const hub = new THREE.Mesh(geometry, material);
        hub.position.set(0, 0, 0);
        hub.userData = { entity, type: 'hub' };
        
        stationGroup.add(hub);
        modules.push(hub);

        // Glow effect
        const glowGeometry = new THREE.CylinderGeometry(radius * 1.2, radius * 1.2, height * 1.1, 32);
        const glowMaterial = new THREE.MeshBasicMaterial({
            color: 0x4488ff,
            transparent: true,
            opacity: 0.2 + cpu * 0.3,
        });
        const glow = new THREE.Mesh(glowGeometry, glowMaterial);
        hub.add(glow);

        layoutData[entity.id] = { mesh: hub, position: { x: 0, y: 0, z: 0 } };
    }

    // Create module (smaller cylinder connected by corridor)
    function createModule(entity, parentLayout, index, totalModules) {
        const cpu = (entity.metrics?.cpu || 50) / 100;
        const state = entity.state || 'unknown';
        const stateColor = STATE_COLORS[state] || STATE_COLORS.unknown;

        const radius = 5 + cpu * 3;
        const height = 12 + cpu * 6;

        const geometry = new THREE.CylinderGeometry(radius, radius, height, 24);
        const material = new THREE.MeshStandardMaterial({
            color: 0x2a2a3e,
            emissive: stateColor,
            emissiveIntensity: 0.3,
            metalness: 0.7,
            roughness: 0.4,
        });

        const module = new THREE.Mesh(geometry, material);
        module.userData = { entity, type: 'module' };

        // Position radially around hub
        const angle = (index / totalModules) * Math.PI * 2;
        const distance = 40 + Math.random() * 10;
        const x = Math.cos(angle) * distance;
        const z = Math.sin(angle) * distance;
        const y = (Math.random() - 0.5) * 20;

        module.position.set(x, y, z);
        stationGroup.add(module);
        modules.push(module);

        // Create corridor connecting to hub
        createCorridor(parentLayout, { x, y, z });

        // Create solar panels
        createSolarPanels(module, angle);

        // Create docking ports
        createDockingPorts(module, entity);

        // Add emergency light if critical
        if (state === 'critical') {
            const emergencyLight = new THREE.PointLight(0xff1111, 1, 30);
            emergencyLight.position.set(0, 5, 0);
            module.add(emergencyLight);
            emergencyLights.push({ light: emergencyLight, module });
        }

        // LED indicators (life support)
        createLEDs(module, entity);

        parentLayout[entity.id] = { mesh: module, position: { x, y, z }, angle, distance };
    }

    // Create corridor mesh connecting modules
    function createCorridor(from, to) {
        const dx = to.x - from.x;
        const dy = to.y - from.y;
        const dz = to.z - from.z;
        const length = Math.sqrt(dx * dx + dy * dy + dz * dz);

        const geometry = new THREE.CylinderGeometry(0.8, 0.8, length, 8);
        const material = new THREE.MeshStandardMaterial({
            color: 0x1a1a2e,
            emissive: 0x44aaff,
            emissiveIntensity: 0.2,
            metalness: 0.9,
            roughness: 0.2,
        });

        const corridor = new THREE.Mesh(geometry, material);

        // Position at midpoint
        corridor.position.set(
            (from.x + to.x) / 2,
            (from.y + to.y) / 2,
            (from.z + to.z) / 2
        );

        // Rotate to connect the two points
        corridor.lookAt(new THREE.Vector3(to.x, to.y, to.z));
        corridor.rotateX(Math.PI / 2);

        stationGroup.add(corridor);
    }

    // Create solar panels (flat planes with grid pattern)
    function createSolarPanels(module, angle) {
        const panelWidth = 15;
        const panelHeight = 6;
        const offset = 8;

        // Create panel texture with grid
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 128;
        const ctx = canvas.getContext('2d');

        ctx.fillStyle = '#1a3a5c';
        ctx.fillRect(0, 0, 256, 128);

        // Grid pattern
        ctx.strokeStyle = '#2266aa';
        ctx.lineWidth = 2;
        for (let i = 0; i < 8; i++) {
            ctx.beginPath();
            ctx.moveTo(i * 32, 0);
            ctx.lineTo(i * 32, 128);
            ctx.stroke();
        }
        for (let i = 0; i < 4; i++) {
            ctx.beginPath();
            ctx.moveTo(0, i * 32);
            ctx.lineTo(256, i * 32);
            ctx.stroke();
        }

        const texture = new THREE.CanvasTexture(canvas);

        // Two panels, one on each side
        for (let side = -1; side <= 1; side += 2) {
            const geometry = new THREE.PlaneGeometry(panelWidth, panelHeight);
            const material = new THREE.MeshStandardMaterial({
                map: texture,
                metalness: 0.6,
                roughness: 0.4,
            });

            const panel = new THREE.Mesh(geometry, material);
            panel.position.set(side * offset, 0, 0);
            panel.rotation.y = Math.PI / 2;
            panel.rotation.z = angle;

            module.add(panel);
        }
    }

    // Create docking ports (TorusGeometry rings)
    function createDockingPorts(module, entity) {
        const childServices = (entity.children || []).map(id => {
            // Look up entities from the module's userData
            const allEntities = module.userData.allEntities || [];
            return allEntities.find(e => e.id === id);
        }).filter(Boolean);
        childServices.forEach((service, i) => {
            const req = service.metrics?.req_per_sec || 0;
            const available = req < 10;
            const color = available ? 0x00ff88 : 0xff2222;

            const geometry = new THREE.TorusGeometry(3, 0.5, 16, 32);
            const material = new THREE.MeshStandardMaterial({
                color: color,
                emissive: color,
                emissiveIntensity: 0.5,
                metalness: 0.8,
                roughness: 0.2,
            });

            const port = new THREE.Mesh(geometry, material);
            
            // Position around module
            const portAngle = (i / childServices.length) * Math.PI * 2;
            const portRadius = 6;
            port.position.set(
                Math.cos(portAngle) * portRadius,
                0,
                Math.sin(portAngle) * portRadius
            );
            port.rotation.y = portAngle;

            port.userData = { entity: service, type: 'docking_port', available };
            module.add(port);
        });
    }

    // Create service spheres inside modules
    function createService(entity, moduleLayout) {
        const cpu = (entity.metrics?.cpu || 50) / 100;
        const state = entity.state || 'unknown';
        const stateColor = STATE_COLORS[state] || STATE_COLORS.unknown;

        const radius = 2 + cpu * 2;
        const geometry = new THREE.SphereGeometry(radius, 24, 24);
        const material = new THREE.MeshStandardMaterial({
            color: stateColor,
            emissive: stateColor,
            emissiveIntensity: 0.4 + cpu * 0.4,
            metalness: 0.5,
            roughness: 0.5,
        });

        const service = new THREE.Mesh(geometry, material);
        service.userData = { entity, type: 'service' };

        // Position relative to parent module
        const modulePos = moduleLayout.position;
        const offset = 12;
        const angle = Math.random() * Math.PI * 2;
        
        service.position.set(
            modulePos.x + Math.cos(angle) * offset,
            modulePos.y + (Math.random() - 0.5) * 8,
            modulePos.z + Math.sin(angle) * offset
        );

        stationGroup.add(service);
        services.push(service);

        moduleLayout[entity.id] = { mesh: service, position: service.position };
    }

    // Create LED indicators on module surface
    function createLEDs(module, entity) {
        const state = entity.state || 'unknown';
        const ledColors = {
            power: 0x44ff44,
            data: 0x44aaff,
            env: state !== 'critical' && state !== 'stopped' ? 0xffaa44 : 0x333344,
        };

        const ledData = entity.metrics || {};
        const leds = [
            { color: ledColors.power, active: (ledData.cpu || 0) > 10 },
            { color: ledColors.data, active: (ledData.req_per_sec || 0) > 0 },
            { color: ledColors.env, active: state !== 'critical' && state !== 'stopped' },
        ];

        leds.forEach((led, i) => {
            const geometry = new THREE.SphereGeometry(0.3, 8, 8);
            const material = new THREE.MeshBasicMaterial({
                color: led.active ? led.color : 0x333344,
            });

            const ledMesh = new THREE.Mesh(geometry, material);
            
            // Position on module surface
            const angle = (i / leds.length) * Math.PI * 2;
            ledMesh.position.set(
                Math.cos(angle) * 5.5,
                6,
                Math.sin(angle) * 5.5
            );

            module.add(ledMesh);
        });
    }

    // Animation loop
    function animate() {
        animationId = requestAnimationFrame(animate);

        const delta = clock.getDelta();
        const elapsed = clock.getElapsedTime();

        // Rotate star field slowly
        if (starField) {
            starField.rotation.y += delta * 0.02;
        }

        // Pulse hub light
        if (hubLight) {
            hubLight.intensity = 2 + Math.sin(elapsed * 2) * 0.5;
        }

        // Pulse emergency lights
        emergencyLights.forEach(({ light }) => {
            light.intensity = 1 + Math.sin(elapsed * 8) * 0.5;
        });

        // Slowly rotate station
        if (stationGroup) {
            stationGroup.rotation.y += delta * 0.05;
        }

        renderer.render(scene, camera);
    }

    // Update scene with new entity data
    function updateScene(newEntities, newLayout) {
        entities = newEntities;
        layout = newLayout;

        // Clear existing objects
        modules.forEach(m => stationGroup.remove(m));
        services.forEach(s => stationGroup.remove(s));
        modules = [];
        services = [];
        emergencyLights = [];

        // Build new objects
        const roots = entities.filter(e => !e.parent);
        roots.forEach(root => {
            if (root.type === 'cluster') {
                createHub(root, layout);
                
                const children = (root.children || [])
                    .map(id => entities.find(e => e.id === id))
                    .filter(Boolean);
                
                children.forEach((child, i) => {
                    if (child.type === 'node') {
                        createModule(child, layout, i, children.length);
                        
                        const grandchildren = (child.children || [])
                            .map(id => entities.find(e => e.id === id))
                            .filter(Boolean);
                        
                        grandchildren.forEach(gc => {
                            if (gc.type === 'service') {
                                createService(gc, layout[child.id]);
                            }
                        });
                    }
                });
            }
        });
    }

    // Camera controls (mouse orbit)
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };
    let rotationSpeed = 0.005;

    function setupControls() {
        const canvas = renderer.domElement;

        canvas.addEventListener('mousedown', (e) => {
            isDragging = true;
            previousMousePosition = { x: e.clientX, y: e.clientY };
        });

        canvas.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            const deltaX = e.clientX - previousMousePosition.x;
            const deltaY = e.clientY - previousMousePosition.y;

            stationGroup.rotation.y += deltaX * rotationSpeed;
            stationGroup.rotation.x += deltaY * rotationSpeed;

            previousMousePosition = { x: e.clientX, y: e.clientY };
        });

        canvas.addEventListener('mouseup', () => {
            isDragging = false;
        });

        canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            camera.position.z += e.deltaY * 0.1;
            camera.position.z = Math.max(50, Math.min(300, camera.position.z));
        });
    }

    // Cleanup
    function dispose() {
        if (animationId) {
            cancelAnimationFrame(animationId);
        }
        if (renderer) {
            renderer.dispose();
        }
        modules.forEach(m => {
            m.geometry.dispose();
            m.material.dispose();
        });
        services.forEach(s => {
            s.geometry.dispose();
            s.material.dispose();
        });
    }

    // Export API
    window.Space3D = {
        init: function(container) {
            initScene(container);
            setupControls();
            animate();
        },
        update: function(entities, layout) {
            updateScene(entities, layout);
        },
        dispose: dispose,
    };
})();
