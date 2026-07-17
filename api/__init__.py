"""Metaphors REST API package.

Provides a FastAPI router with all /api/* routes.
Usage in server.py:
    from api import create_api_router
    app.include_router(create_api_router(registry, ...))
"""

from fastapi import APIRouter
from typing import Callable, Optional, List

from api.routes import create_routes


def create_api_router(
    registry,
    get_active_metaphor: Callable[[], str],
    set_active_metaphor: Optional[Callable[[str], None]] = None,
    known_client_metaphors: Optional[List[str]] = None,
) -> APIRouter:
    """Build an APIRouter bound to the metaphor registry and active state.

    Args:
        registry: MetaphorRegistry with registered renderers.
        get_active_metaphor: Callable returning the current active metaphor name.
        set_active_metaphor: Optional callable to change the active metaphor.
        known_client_metaphors: List of metaphor names only rendered client-side.
    """
    router = APIRouter(prefix="/api", tags=["metaphors"])
    known_client = known_client_metaphors or ["forest", "space", "city3d", "garden"]

    create_routes(router, registry, get_active_metaphor, known_client)

    return router


__all__ = ["create_api_router"]
