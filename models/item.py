from dataclasses import dataclass
from enum import Enum


class ItemType(Enum):
    WEAPON = "weapon"
    SHIELD = "shield"
    HELMET = "helmet"
    ARMOR = "armor"
    GLOVES = "gloves"
    BOOTS = "boots"
    AMULET = "amulet"
    RING = "ring"
    CONSUMABLE = "consumable"
    RESOURCE = "resource"


EQUIP_SLOTS = frozenset(
    {
        ItemType.WEAPON,
        ItemType.SHIELD,
        ItemType.HELMET,
        ItemType.ARMOR,
        ItemType.GLOVES,
        ItemType.BOOTS,
        ItemType.AMULET,
        ItemType.RING,
    }
)

EQUIP_SLOT_NAMES = {
    ItemType.WEAPON: "Оружие",
    ItemType.SHIELD: "Щит",
    ItemType.HELMET: "Шлем",
    ItemType.ARMOR: "Броня",
    ItemType.GLOVES: "Перчатки",
    ItemType.BOOTS: "Сапоги",
    ItemType.AMULET: "Амулет",
    ItemType.RING: "Кольцо",
}


class Rarity(Enum):
    COMMON = ("common", "Обычный", (180, 180, 180), 0)
    UNCOMMON = ("uncommon", "Необычный", (100, 220, 100), 1)
    RARE = ("rare", "Редкий", (100, 150, 240), 2)
    EPIC = ("epic", "Эпический", (200, 100, 240), 3)
    LEGENDARY = ("legendary", "Легендарный", (240, 180, 60), 4)

    @property
    def display_name(self):
        return self.value[1]

    @property
    def color(self):
        return self.value[2]

    @property
    def affix_count(self):
        return self.value[3]


@dataclass
class Item:
    item_id: str
    name: str
    item_type: ItemType
    rarity: Rarity = Rarity.COMMON
    value: int = 0
    count: int = 1

    bonus_strength: int = 0
    bonus_agility: int = 0
    bonus_intelligence: int = 0
    bonus_endurance: int = 0
    bonus_hp: int = 0
    bonus_attack: int = 0
    bonus_crit: float = 0.0
    bonus_defense: int = 0

    heal_amount: int = 0

    icon_color: tuple = (200, 200, 200)

    @property
    def is_equipment(self):
        return self.item_type in EQUIP_SLOTS

    @property
    def is_stackable(self):
        return self.item_type in (ItemType.RESOURCE, ItemType.CONSUMABLE)

    def describe_bonuses(self):
        lines = []
        if self.bonus_strength:
            lines.append(f"+{self.bonus_strength} Сила")
        if self.bonus_agility:
            lines.append(f"+{self.bonus_agility} Ловкость")
        if self.bonus_intelligence:
            lines.append(f"+{self.bonus_intelligence} Интеллект")
        if self.bonus_endurance:
            lines.append(f"+{self.bonus_endurance} Выносливость")
        if self.bonus_hp:
            lines.append(f"+{self.bonus_hp} HP")
        if self.bonus_attack:
            lines.append(f"+{self.bonus_attack} Атака")
        if self.bonus_crit:
            lines.append(f"+{self.bonus_crit * 100:.1f}% Крит")
        if self.bonus_defense:
            lines.append(f"+{self.bonus_defense} Защита")
        if self.heal_amount:
            lines.append(f"Лечит {self.heal_amount} HP")
        return lines

    def copy(self):
        from dataclasses import replace

        return replace(self)
