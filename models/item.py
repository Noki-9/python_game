from dataclasses import dataclass
from enum import Enum


class ItemType(Enum):
    RESOURCE = "resource"
    GOLD = "gold"
    WEAPON = "weapon"
    ARMOR = "armor"
    POTION = "potion"
    MISC = "misc"


@dataclass
class Item:
    item_id: str
    name: str
    item_type: ItemType
    value: int = 0
    color: tuple = (200, 200, 200)
