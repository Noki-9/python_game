from models.item import Item, ItemType

GOLD = "gold"
MEAT = "meat"
LEATHER = "leather"
HERB = "herb"
BONE = "bone"
IRON_ORE = "iron_ore"
WOOD = "wood"


ITEMS_REGISTRY = {
    GOLD: Item(GOLD, "Золото", ItemType.GOLD, value=1, color=(230, 200, 90)),
    MEAT: Item(MEAT, "Мясо", ItemType.RESOURCE, value=5, color=(200, 100, 100)),
    LEATHER: Item(LEATHER, "Кожа", ItemType.RESOURCE, value=8, color=(160, 110, 70)),
    HERB: Item(HERB, "Трава", ItemType.RESOURCE, value=3, color=(100, 200, 100)),
    BONE: Item(BONE, "Кость", ItemType.RESOURCE, value=4, color=(240, 240, 220)),
    IRON_ORE: Item(
        IRON_ORE, "Железная руда", ItemType.RESOURCE, value=12, color=(140, 140, 150)
    ),
    WOOD: Item(WOOD, "Дерево", ItemType.RESOURCE, value=2, color=(130, 90, 60)),
}


LOOT_TABLES = {
    # (item_id, min_count, max_count, probability)
    "goblin": [(GOLD, 5, 15, 0.90), (BONE, 1, 2, 0.40), (LEATHER, 1, 1, 0.30)],
    "bandit": [(GOLD, 10, 25, 0.95), (LEATHER, 1, 2, 0.50), (IRON_ORE, 1, 1, 0.20)],
    "skeleton": [(BONE, 1, 3, 0.90), (GOLD, 3, 10, 0.60)],
    "troll": [(GOLD, 30, 60, 1.00), (IRON_ORE, 2, 4, 0.80), (BONE, 2, 4, 0.70)],
    "deer": [(MEAT, 1, 3, 0.90), (LEATHER, 1, 1, 0.50)],
    "wolf": [(LEATHER, 1, 2, 0.80), (MEAT, 1, 2, 0.60)],
    "boar": [(MEAT, 2, 4, 0.90), (LEATHER, 1, 2, 0.60)],
    "bear": [(LEATHER, 2, 4, 0.90), (MEAT, 2, 5, 0.90)],
    "rabbit": [(MEAT, 1, 1, 0.80)],
    "fox": [(LEATHER, 1, 1, 0.70), (MEAT, 1, 1, 0.40)],
    "sheep": [(MEAT, 1, 2, 0.80), (LEATHER, 1, 1, 0.60)],
    "snake": [(LEATHER, 1, 1, 0.50)],
    "scorpion": [(BONE, 1, 1, 0.40)],
    "lizard": [(MEAT, 1, 1, 0.60)],
    "snow_wolf": [(LEATHER, 1, 2, 0.80), (MEAT, 1, 2, 0.60)],
    "moose": [(MEAT, 2, 4, 0.90), (LEATHER, 2, 3, 0.80)],
    "goat": [(MEAT, 1, 2, 0.70), (LEATHER, 1, 1, 0.50)],
}


def roll_loot(enemy_id: str, rng) -> dict:
    """Возвращает {item_id: count}."""
    table = LOOT_TABLES.get(enemy_id, [])
    result = {}
    for item_id, min_c, max_c, prob in table:
        if rng.random() < prob:
            count = rng.randint(min_c, max_c)
            result[item_id] = result.get(item_id, 0) + count
    return result
