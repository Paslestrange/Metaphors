"""API route handlers for Metaphors.

Contains FastAPI route functions for the /api/* endpoints.
These are bound to a router by create_api_router() in api/__init__.py.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse


def create_routes(router: APIRouter, registry, get_active_metaphor, known_client_metaphors):
    """Bind route handlers to the given router.

    Args:
        router: FastAPI APIRouter to attach routes to.
        registry: MetaphorRegistry with registered renderers.
        get_active_metaphor: Callable returning the current active metaphor name.
        known_client_metaphors: List of metaphor names only rendered client-side.
    """

    descriptions = {
        "city": "Infrastructure as a cityscape",
        "city3d": "Infrastructure as a 3D cyberpunk city",
        "forest": "Services as a living forest ecosystem",
        "traffic_light": "Infrastructure as traffic signals at an intersection",
        "space": "Systems as a space station with orbiting modules",
        "garden": "Infrastructure as a garden with plants, terrain, and lighting",
    }

    @router.get("/metaphors")
    async def list_metaphors():
        """List all available metaphor renderers."""
        names = registry.list()
        metaphor_info = []
        for name in names:
            metaphor_info.append({
                "id": name,
                "name": name.capitalize(),
                "description": descriptions.get(name, f"The {name} metaphor"),
            })
        # Include client-side-only metaphors
        for name in known_client_metaphors:
            if name not in names:
                metaphor_info.append({
                    "id": name,
                    "name": name.capitalize(),
                    "description": descriptions.get(name, f"The {name} metaphor"),
                })
        return {
            "metaphors": metaphor_info,
            "active": get_active_metaphor(),
            "default": get_active_metaphor(),
        }

    @router.get("/metaphors/{name}")
    async def get_metaphor(name: str):
        """Get configuration for a specific metaphor."""
        renderer = registry.get(name)
        if renderer is None:
            return JSONResponse(
                status_code=404,
                content={"error": f"Metaphor '{name}' not found"},
            )
        if hasattr(renderer, "config"):
            return renderer.config()
        return {"name": name}
