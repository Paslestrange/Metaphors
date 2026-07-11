from __future__ import annotations
from abc import ABC, abstractmethod
from engine.entities import Entity

class DataSource(ABC):
    """Abstract base for all data sources."""

    name: str = "base"

    @abstractmethod
    def fetch(self) -> list[Entity]:
        """Return current snapshot of all entities."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this data source can connect."""
        ...
