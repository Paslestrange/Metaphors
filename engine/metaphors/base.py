"""Base classes for metaphor renderer plugin system."""
from abc import ABC, abstractmethod
from typing import Any


class MetaphorRenderer(ABC):
    """Abstract base class for metaphor renderers.
    
    Each metaphor (city, forest, etc.) implements this interface
    to provide custom rendering logic for entities.
    """
    
    @abstractmethod
    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        """Render entities to the given canvas context.
        
        Args:
            entities: List of entity dicts from the entity model
            ctx: Canvas rendering context (CanvasRenderingContext2D or similar)
            w: Canvas width in pixels
            h: Canvas height in pixels
        """
        pass
    
    @abstractmethod
    def get_tooltip(self, entity: dict[str, Any], x: int, y: int) -> str | None:
        """Get tooltip text for an entity at the given coordinates.
        
        Args:
            entity: Entity dict
            x: Mouse x coordinate
            y: Mouse y coordinate
            
        Returns:
            Tooltip string or None if no tooltip
        """
        pass
    
    @abstractmethod
    def hit_test(self, entity: dict[str, Any], x: int, y: int) -> bool:
        """Test if coordinates hit this entity's rendered area.
        
        Args:
            entity: Entity dict
            x: Mouse x coordinate
            y: Mouse y coordinate
            
        Returns:
            True if (x, y) is within this entity's bounds
        """
        pass


class MetaphorRegistry:
    """Registry for metaphor renderers.
    
    Allows dynamic registration and lookup of metaphor implementations.
    """
    
    def __init__(self):
        self._renderers: dict[str, MetaphorRenderer] = {}
    
    def register(self, name: str, renderer: MetaphorRenderer) -> None:
        """Register a metaphor renderer by name.
        
        Args:
            name: Unique identifier for this metaphor (e.g., 'city', 'forest')
            renderer: MetaphorRenderer instance
        """
        self._renderers[name] = renderer
    
    def get(self, name: str) -> MetaphorRenderer | None:
        """Get a registered metaphor renderer by name.
        
        Args:
            name: Metaphor identifier
            
        Returns:
            MetaphorRenderer instance or None if not found
        """
        return self._renderers.get(name)
    
    def list(self) -> list[str]:
        """List all registered metaphor names.
        
        Returns:
            List of metaphor name strings
        """
        return list(self._renderers.keys())
