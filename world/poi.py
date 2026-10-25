from dataclasses import dataclass
from enum import Enum

from world.location_type import LocationType


class POIType(Enum):
    STARTING_VILLAGE = "starting_village"
    VILLAGE = "village"
    QUEST_DUNGEON = "quest_dungeon"
    MAIN_ANTAGONIST = "main_antagonist"
    WILD_POINT = "wild_point"


@dataclass
class POI:
    poi_type: POIType
    gx: int
    gy: int
    name: str
    cleared: bool = False
    discovered: bool = False

    @property
    def location_type(self) -> LocationType:
        return {
            POIType.STARTING_VILLAGE: LocationType.STARTING_VILLAGE,
            POIType.VILLAGE: LocationType.VILLAGE,
            POIType.QUEST_DUNGEON: LocationType.QUEST,
            POIType.MAIN_ANTAGONIST: LocationType.MAIN_QUEST,
            POIType.WILD_POINT: LocationType.WILD,
        }[self.poi_type]

    @property
    def icon_color(self):
        return {
            POIType.STARTING_VILLAGE: (110, 220, 110),
            POIType.VILLAGE: (230, 200, 90),
            POIType.QUEST_DUNGEON: (220, 90, 90),
            POIType.MAIN_ANTAGONIST: (200, 70, 200),
            POIType.WILD_POINT: (170, 170, 170),
        }[self.poi_type]
