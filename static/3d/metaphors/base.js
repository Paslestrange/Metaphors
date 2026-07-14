// Base 3D Metaphor class
class Base3DMetaphor {
    constructor() {
        this.scene = null;
        this.camera = null;
        this.objects = new Map(); // entity.id -> THREE.Object3D
    }

    // Initialize scene with camera position and lighting
    init(scene, camera) {
        this.scene = scene;
        this.camera = camera;
    }

    // Build 3D scene from entities
    buildScene(entities) {
        console.warn('buildScene not implemented for', this.name);
    }

    // Update animations and dynamic elements
    update(deltaTime, entities) {
        // Override in subclasses
    }

    // Clean up all geometries and materials
    dispose() {
        if (this.scene) {
            this.objects.forEach(obj => {
                this.disposeObject(obj);
            });
            this.objects.clear();
        }
    }

    disposeObject(obj) {
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) {
            if (Array.isArray(obj.material)) {
                obj.material.forEach(m => m.dispose());
            } else {
                obj.material.dispose();
            }
        }
        if (obj.children) {
            obj.children.forEach(child => this.disposeObject(child));
        }
    }

    // Get default camera position for this metaphor
    getDefaultCameraPosition() {
        return { x: 0, y: 50, z: 100 };
    }

    // Get default camera look-at target
    getDefaultCameraTarget() {
        return { x: 0, y: 0, z: 0 };
    }
}

// Make available globally
window.Base3DMetaphor = Base3DMetaphor;
