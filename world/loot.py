from models.item import Item, ItemType, Rarity

ITEMS_REGISTRY = {
    "gold": Item(
        "gold",
        "Золото",
        ItemType.RESOURCE,
        Rarity.COMMON,
        value=1,
        icon_color=(230, 200, 90),
    ),
    "meat": Item(
        "meat",
        "Мясо",
        ItemType.RESOURCE,
        Rarity.COMMON,
        value=5,
        icon_color=(200, 100, 100),
    ),
    "leather": Item(
        "leather",
        "Кожа",
        ItemType.RESOURCE,
        Rarity.COMMON,
        value=8,
        icon_color=(160, 110, 70),
    ),
    "herb": Item(
        "herb",
        "Трава",
        ItemType.RESOURCE,
        Rarity.COMMON,
        value=3,
        icon_color=(100, 200, 100),
    ),
    "bone": Item(
        "bone",
        "Кость",
        ItemType.RESOURCE,
        Rarity.COMMON,
        value=4,
        icon_color=(240, 240, 220),
    ),
    "iron_ore": Item(
        "iron_ore",
        "Железная руда",
        ItemType.RESOURCE,
        Rarity.COMMON,
        value=12,
        icon_color=(140, 140, 150),
    ),
    "wood": Item(
        "wood",
        "Дерево",
        ItemType.RESOURCE,
        Rarity.COMMON,
        value=2,
        icon_color=(130, 90, 60),
    ),
}

GOLD = "gold"


LOOT_TABLES = {
    "goblin": [(GOLD, 5, 15, 0.90), ("bone", 1, 2, 0.40), ("leather", 1, 1, 0.30)],
    "bandit": [(GOLD, 10, 25, 0.95), ("leather", 1, 2, 0.50), ("iron_ore", 1, 1, 0.20)],
    "skeleton": [("bone", 1, 3, 0.90), (GOLD, 3, 10, 0.60)],
    "troll": [(GOLD, 30, 60, 1.00), ("iron_ore", 2, 4, 0.80), ("bone", 2, 4, 0.70)],
    "deer": [("meat", 1, 3, 0.90), ("leather", 1, 1, 0.50)],
    "wolf": [("leather", 1, 2, 0.80), ("meat", 1, 2, 0.60)],
    "boar": [("meat", 2, 4, 0.90), ("leather", 1, 2, 0.60)],
    "bear": [("leather", 2, 4, 0.90), ("meat", 2, 5, 0.90)],
    "rabbit": [("meat", 1, 1, 0.80)],
    "fox": [("leather", 1, 1, 0.70), ("meat", 1, 1, 0.40)],
    "sheep": [("meat", 1, 2, 0.80), ("leather", 1, 1, 0.60)],
    "snake": [("leather", 1, 1, 0.50)],
    "scorpion": [("bone", 1, 1, 0.40)],
    "lizard": [("meat", 1, 1, 0.60)],
    "snow_wolf": [("leather", 1, 2, 0.80), ("meat", 1, 2, 0.60)],
    "moose": [("meat", 2, 4, 0.90), ("leather", 2, 3, 0.80)],
    "goat": [("meat", 1, 2, 0.70), ("leather", 1, 1, 0.50)],
}


def roll_loot(enemy_id, rng):
    table = LOOT_TABLES.get(enemy_id, [])
    result = {}
    for item_id, min_c, max_c, prob in table:
        if rng.random() < prob:
            count = rng.randint(min_c, max_c)
            result[item_id] = result.get(item_id, 0) + count
    return result
