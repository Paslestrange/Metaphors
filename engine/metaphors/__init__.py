"""Metaphor renderer plugin system."""
from engine.metaphors.base import MetaphorRenderer, MetaphorRegistry
from engine.metaphors.city import CityRenderer
from engine.metaphors.space import SpaceStationRenderer

__all__ = ["MetaphorRenderer", "MetaphorRegistry", "CityRenderer", "SpaceStationRenderer"]
