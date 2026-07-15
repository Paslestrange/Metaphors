// Main 3D Controller - Manages scene, camera, metaphor switching
(function() {
    'use strict';

    // Three.js core
    let scene, camera, renderer;
    let clock;
    let isInitialized = false;

    // Metaphor state
    let currentMetaphor = localStorage.getItem('metaphor_3d') || 'city';
    let availableMetaphors = [];
    let metaphorInstances = {};
    let activeMetaphorInstance = null;
    let isTransitioning = false;

    // Camera animation
    let cameraAnimating = false;
    let cameraStartPos = new THREE.Vector3();
    let cameraTargetPos = new THREE.Vector3();
    let cameraStartLookAt = new THREE.Vector3();
    let cameraTargetLookAt = new THREE.Vector3();
    let cameraAnimProgress = 0;
    const CAMERA_ANIM_DURATION = 0.8; // seconds

    // Entity data
    let entities = [];

    // ============================================================
    // Initialization
    // ============================================================
    function init() {
        const canvas = document.getElementById('canvas3d');
        
        // Scene
        scene = new THREE.Scene();
        
        // Camera
        camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.set(0, 50, 100);

        // Renderer
        renderer = new THREE.WebGLRenderer({ 
            canvas: canvas, 
            antialias: true,
            alpha: false
        });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.shadowMap.enabled = true;

        // Clock for deltaTime
        clock = new THREE.Clock();

        // Handle resize
        window.addEventListener('resize', onResize);

        // Initialize metaphor instances
        initMetaphorInstances();

        // Fetch metaphors from API
        fetchMetaphors().then(() => {
            // Load initial metaphor
            loadMetaphor(currentMetaphor);
            isInitialized = true;
            
            // Hide loading
            document.getElementById('loading').style.display = 'none';
            
            // Start animation loop
            animate();

            // Connect to WebSocket for live data
            connectWebSocket();
        });

        // Keyboard shortcuts
        setupKeyboardShortcuts();
    }

    function initMetaphorInstances() {
        if (window.CityMetaphor) metaphorInstances.city = new window.CityMetaphor();
        if (window.SpaceMetaphor) metaphorInstances.space = new window.SpaceMetaphor();
        if (window.GardenMetaphor) metaphorInstances.garden = new window.GardenMetaphor();
    }

    // ============================================================
    // Metaphor Loading & Switching
    // ============================================================
    async function fetchMetaphors() {
        try {
            const res = await fetch('/api/metaphors');
            const data = await res.json();
            availableMetaphors = data.metaphors || [];
            
            // Restore saved or use default
            const saved = localStorage.getItem('metaphor_3d');
            if (saved && availableMetaphors.some(m => m.id === saved)) {
                currentMetaphor = saved;
            } else {
                currentMetaphor = data.default || data.active || 'city';
            }
            
            buildToolbar();
        } catch (e) {
            console.error('Failed to fetch metaphors:', e);
            availableMetaphors = [
                { id: 'city', name: 'City', description: 'Infrastructure as a 3D cityscape' },
                { id: 'solar', name: 'Solar', description: 'Systems as orbiting celestial bodies' },
                { id: 'forest', name: 'Forest', description: 'Services as a 3D forest ecosystem' },
                { id: 'traffic_light', name: 'Traffic Light', description: 'Urban intersection with signal colors' },
                { id: 'space', name: 'Space Station', description: 'Orbital station in deep space' },
                { id: 'garden', name: 'Garden', description: 'Infrastructure as a living garden' }
            ];
            buildToolbar();
        }
    }

    function loadMetaphor(metaphorId) {
        if (!metaphorInstances[metaphorId]) {
            console.error('Unknown metaphor:', metaphorId);
            return;
        }

        // Dispose previous
        if (activeMetaphorInstance) {
            activeMetaphorInstance.dispose();
        }

        // Clear scene
        while (scene.children.length > 0) {
            scene.remove(scene.children[0]);
        }

        // Load new metaphor
        activeMetaphorInstance = metaphorInstances[metaphorId];
        activeMetaphorInstance.init(scene, camera);
        activeMetaphorInstance.buildScene(entities);

        // Set camera to default position
        const defaultPos = activeMetaphorInstance.getDefaultCameraPosition();
        const defaultTarget = activeMetaphorInstance.getDefaultCameraTarget();
        camera.position.set(defaultPos.x, defaultPos.y, defaultPos.z);
        camera.lookAt(defaultTarget.x, defaultTarget.y, defaultTarget.z);
    }

    function switchMetaphor(newMetaphor) {
        if (newMetaphor === currentMetaphor || isTransitioning) return;
        if (!metaphorInstances[newMetaphor]) return;

        isTransitioning = true;
        const overlay = document.getElementById('fade-overlay');

        // Fade out
        overlay.classList.add('active');

        // Start camera transition
        const oldPos = activeMetaphorInstance ? activeMetaphorInstance.getDefaultCameraPosition() : { x: 0, y: 50, z: 100 };
        const newMetaphorInst = metaphorInstances[newMetaphor];
        const newDefaultPos = newMetaphorInst.getDefaultCameraPosition();
        const newDefaultTarget = newMetaphorInst.getDefaultCameraTarget();

        cameraStartPos.copy(camera.position);
        cameraTargetPos.set(newDefaultPos.x, newDefaultPos.y, newDefaultPos.z);
        
        // Get current look-at (approximate from camera direction)
        cameraStartLookAt.set(0, 0, 0);
        cameraTargetLookAt.set(newDefaultTarget.x, newDefaultTarget.y, newDefaultTarget.z);
        
        cameraAnimProgress = 0;
        cameraAnimating = true;

        setTimeout(() => {
            // Switch metaphor
            currentMetaphor = newMetaphor;
            localStorage.setItem('metaphor_3d', newMetaphor);
            loadMetaphor(newMetaphor);

            // Update toolbar
            updateToolbarDescription();
            const select = document.getElementById('metaphor-select');
            if (select) select.value = newMetaphor;

            // Fade in
            setTimeout(() => {
                overlay.classList.remove('active');
                isTransitioning = false;
            }, 50);
        }, 300);
    }

    // ============================================================
    // Animation Loop
    // ============================================================
    function animate() {
        requestAnimationFrame(animate);

        const deltaTime = clock.getDelta();

        // Camera animation
        if (cameraAnimating) {
            cameraAnimProgress += deltaTime / CAMERA_ANIM_DURATION;
            
            if (cameraAnimProgress >= 1) {
                cameraAnimProgress = 1;
                cameraAnimating = false;
            }

            // Smooth easing
            const t = easeInOutCubic(cameraAnimProgress);
            
            camera.position.lerpVectors(cameraStartPos, cameraTargetPos, t);
            
            const lookAt = new THREE.Vector3().lerpVectors(cameraStartLookAt, cameraTargetLookAt, t);
            camera.lookAt(lookAt);
        }

        // Update active metaphor
        if (activeMetaphorInstance) {
            activeMetaphorInstance.update(deltaTime, entities);
        }

        // Render
        renderer.render(scene, camera);
    }

    function easeInOutCubic(t) {
        return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    // ============================================================
    // UI & Controls
    // ============================================================
    function buildToolbar() {
        const toolbar = document.getElementById('toolbar');
        const metaphorOptions = availableMetaphors.map((m, i) =>
            `<option value="${m.id}" ${m.id === currentMetaphor ? 'selected' : ''}>${i + 1}. ${m.name}</option>`
        ).join('');

        const currentMeta = availableMetaphors.find(m => m.id === currentMetaphor);
        const desc = currentMeta ? currentMeta.description : '';

        const toolbarInfo = toolbar.querySelector('.toolbar-info');
        if (toolbarInfo) {
            document.getElementById('metaphor-desc').textContent = desc;
            const select = document.getElementById('metaphor-select');
            select.innerHTML = metaphorOptions;
            select.addEventListener('change', (e) => {
                switchMetaphor(e.target.value);
            });
        }
    }

    function updateToolbarDescription() {
        const meta = availableMetaphors.find(m => m.id === currentMetaphor);
        const descEl = document.getElementById('metaphor-desc');
        if (descEl && meta) {
            descEl.textContent = meta.description;
        }
    }

    function setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Number keys 1-9 switch metaphors
            const num = parseInt(e.key);
            if (num >= 1 && num <= 9 && num <= availableMetaphors.length) {
                const targetMetaphor = availableMetaphors[num - 1].id;
                switchMetaphor(targetMetaphor);
            }
        });
    }

    function onResize() {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    }

    // ============================================================
    // Public API for entity updates (WebSocket)
    // ============================================================
    window.updateEntities = function(newEntities) {
        entities = newEntities;
        
        // Rebuild scene with new data
        if (activeMetaphorInstance && !isTransitioning) {
            activeMetaphorInstance.dispose();
            while (scene.children.length > 0) {
                scene.remove(scene.children[0]);
            }
            activeMetaphorInstance.buildScene(entities);
        }
    };

    // ============================================================
    // WebSocket connection for live entity data
    // ============================================================
    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/entities`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('3D WebSocket connected');
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.entities && Array.isArray(data.entities)) {
                    // Convert entity tree to flat list with children references
                    const flatEntities = flattenEntities(data.entities);
                    window.updateEntities(flatEntities);
                }
            } catch (e) {
                console.error('Failed to parse WebSocket message:', e);
            }
        };

        ws.onerror = (e) => {
            console.error('WebSocket error:', e);
        };

        ws.onclose = () => {
            console.log('WebSocket closed, reconnecting in 3s...');
            setTimeout(connectWebSocket, 3000);
        };
    }

    // Flatten nested entity structure for 3D renderers
    function flattenEntities(entityTree) {
        const flat = [];
        function traverse(entity, parentId) {
            const flatEntity = {
                id: entity.id,
                name: entity.name || entity.id,
                type: entity.type || 'service',
                state: entity.state || 'unknown',
                metrics: entity.metrics || {},
                parent: parentId,
                children: (entity.children || []).map(c => c.id || c)
            };
            flat.push(flatEntity);
            if (entity.children && Array.isArray(entity.children)) {
                entity.children.forEach(child => {
                    if (typeof child === 'object' && child.id) {
                        traverse(child, entity.id);
                    }
                });
            }
        }
        if (Array.isArray(entityTree)) {
            entityTree.forEach(e => traverse(e, null));
        } else {
            traverse(entityTree, null);
        }
        return flat;
    }

    // Start initialization when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
