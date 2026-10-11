# world/biome.py
from enum import Enum


class Biome(Enum):
    OCEAN    = "ocean"
    TUNDRA   = "tundra"
    DESERT   = "desert"
    PLAINS   = "plains"
    FOREST   = "forest"
    MOUNTAIN = "mountain"

    @property
    def color(self):
        return {
            "ocean":    (40, 80, 160),
            "tundra":   (200, 220, 230),
            "desert":   (230, 200, 120),
            "plains":   (140, 200, 100),
            "forest":   (60, 130, 60),
            "mountain": (120, 110, 100),
        }[self.value]

    @property
    def walkable(self):
        # по океану/горам ходить нельзя (или можно — на ваш вкус)
        return self not in (Biome.OCEAN, Biome.MOUNTAIN)