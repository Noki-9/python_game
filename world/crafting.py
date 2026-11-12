"""Крафт у кузнеца (ТЗ 6)."""

from dataclasses import dataclass, field

from models.item import Rarity
from world.item_generator import generate_item


@dataclass
class Recipe:
    recipe_id: str
    name: str
    template_id: str
    materials: dict[str, int] = field(default_factory=dict)
    gold: int = 0


RECIPES = [
    Recipe("r_sword", "Железный меч", "sword_iron", {"iron_ore": 2, "wood": 1}, 10),
    Recipe("r_shield", "Железный щит", "shield_iron", {"iron_ore": 2, "wood": 2}, 12),
    Recipe("r_helmet", "Железный шлем", "helmet_iron", {"iron_ore": 2}, 10),
    Recipe("r_armor", "Кольчуга", "armor_chain", {"iron_ore": 3, "leather": 1}, 25),
    Recipe("r_gloves", "Кожаные перчатки", "gloves_leather", {"leather": 2}, 5),
    Recipe("r_boots", "Кожаные сапоги", "boots_leather", {"leather": 2}, 5),
    Recipe("r_axe", "Железный топор", "axe_iron", {"iron_ore": 3, "wood": 2}, 15),
    Recipe("r_shield_wood", "Деревянный щит", "shield_wood", {"wood": 3}, 8),
    Recipe("r_axe_stone", "Каменный топор", "axe_iron", {"stone": 4, "wood": 2}, 4),
]

# У костра можно сделать только простое снаряжение из дерева/кожи.
CAMP_RECIPES = [
    r
    for r in RECIPES
    if "iron_ore" not in r.materials
]


def material_count(inventory, item_id):
    return sum(it.count for it in inventory if it.item_id == item_id)


def can_craft(state, recipe):
    if state.gold < recipe.gold:
        return False
    return all(
        material_count(state.inventory, item_id) >= need
        for item_id, need in recipe.materials.items()
    )


def consume_materials(state, recipe):
    for item_id, need in recipe.materials.items():
        remaining = need
        for it in list(state.inventory):
            if it.item_id != item_id or remaining <= 0:
                continue
            take = min(it.count, remaining)
            it.count -= take
            remaining -= take
            if it.count <= 0:
                state.inventory.remove(it)
    state.gold -= recipe.gold


def craft(state, recipe, rng):
    if not can_craft(state, recipe):
        return None
    consume_materials(state, recipe)
    item = generate_item(recipe.template_id, Rarity.COMMON, rng)
    if item is not None:
        item.name = recipe.name
        state.add_item(item)
    return item
