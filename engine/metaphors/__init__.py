"""Metaphor renderer plugin system."""
from engine.metaphors.base import MetaphorRenderer, MetaphorRegistry
from engine.metaphors.city import CityRenderer
from engine.metaphors.space import SpaceStationRenderer
from engine.metaphors.garden import GardenRenderer
from engine.metaphors.construction import ConstructionRenderer
from engine.metaphors.factory import FactoryRenderer
from engine.metaphors.kitchen import KitchenRenderer
from engine.metaphors.orchestra import OrchestraRenderer
from engine.metaphors.ship import ShipRenderer
from engine.metaphors.solar import SolarRenderer

__all__ = ["MetaphorRenderer", "MetaphorRegistry", "CityRenderer", "SpaceStationRenderer", "GardenRenderer", "ConstructionRenderer", "FactoryRenderer", "KitchenRenderer", "OrchestraRenderer", "ShipRenderer", "SolarRenderer"]
