import random

from models.item import Item, ItemType, Rarity

WEAPON_TEMPLATES = {
    "sword_iron": ("Железный меч", ItemType.WEAPON, 10, (180, 180, 180)),
    "dagger_iron": ("Железный кинжал", ItemType.WEAPON, 6, (180, 180, 180)),
    "staff_oak": ("Дубовый посох", ItemType.WEAPON, 8, (140, 100, 60)),
    "bow_wood": ("Деревянный лук", ItemType.WEAPON, 9, (140, 100, 60)),
    "axe_iron": ("Железный топор", ItemType.WEAPON, 12, (180, 180, 180)),
}

ARMOR_TEMPLATES = {
    "helmet_leather": ("Кожаный шлем", ItemType.HELMET, 5, (160, 110, 70)),
    "helmet_iron": ("Железный шлем", ItemType.HELMET, 12, (180, 180, 180)),
    "armor_leather": ("Кожаная броня", ItemType.ARMOR, 10, (160, 110, 70)),
    "armor_chain": ("Кольчуга", ItemType.ARMOR, 20, (160, 160, 160)),
    "gloves_leather": ("Кожаные перчатки", ItemType.GLOVES, 4, (160, 110, 70)),
    "boots_leather": ("Кожаные сапоги", ItemType.BOOTS, 4, (160, 110, 70)),
    "shield_wood": ("Деревянный щит", ItemType.SHIELD, 7, (140, 100, 60)),
    "shield_iron": ("Железный щит", ItemType.SHIELD, 14, (180, 180, 180)),
    "amulet_jade": ("Нефритовый амулет", ItemType.AMULET, 15, (100, 200, 150)),
    "ring_silver": ("Серебряное кольцо", ItemType.RING, 12, (200, 200, 220)),
}

ALL_TEMPLATES = {**WEAPON_TEMPLATES, **ARMOR_TEMPLATES}


PREFIXES = {
    Rarity.UNCOMMON: ["Крепкий", "Лёгкий", "Закалённый"],
    Rarity.RARE: ["Рунный", "Кованый", "Стальной"],
    Rarity.EPIC: ["Древний", "Проклятый", "Пламенный"],
    Rarity.LEGENDARY: ["Божественный", "Драконий", "Вечный"],
}


AFFIXES = [
    ("bonus_strength", 2, 4, "Сила"),
    ("bonus_agility", 2, 4, "Ловкость"),
    ("bonus_intelligence", 2, 4, "Интеллект"),
    ("bonus_endurance", 2, 4, "Выносливость"),
    ("bonus_hp", 10, 30, "HP"),
    ("bonus_attack", 2, 6, "Атака"),
    ("bonus_crit", 0.03, 0.08, "Крит"),
    ("bonus_defense", 2, 5, "Защита"),
]


def _roll_rarity(rng):
    r = rng.random()
    if r < 0.55:
        return Rarity.COMMON
    if r < 0.82:
        return Rarity.UNCOMMON
    if r < 0.94:
        return Rarity.RARE
    if r < 0.99:
        return Rarity.EPIC
    return Rarity.LEGENDARY


def _apply_affixes(item, rarity, rng):
    n = rarity.affix_count
    used = set()
    for _ in range(n):
        available = [a for a in AFFIXES if a[0] not in used]
        if not available:
            break
        field_name, min_v, max_v, _ = rng.choice(available)
        used.add(field_name)
        if field_name == "bonus_crit":
            val = rng.uniform(min_v, max_v)
        else:
            val = rng.randint(min_v, max_v)
        setattr(item, field_name, getattr(item, field_name) + val)
        if field_name != "bonus_crit":
            item.value += int(val * 3)


def _apply_base_bonus(item, rng):
    if item.item_type == ItemType.WEAPON:
        item.bonus_attack = 5 + rng.randint(0, 5)
    elif item.item_type in (ItemType.HELMET, ItemType.ARMOR):
        item.bonus_defense = 3 + rng.randint(0, 3)
        item.bonus_hp = 5 + rng.randint(0, 10)
    elif item.item_type in (ItemType.GLOVES, ItemType.BOOTS):
        item.bonus_agility = 1 + rng.randint(0, 2)
    elif item.item_type == ItemType.SHIELD:
        item.bonus_defense = 5 + rng.randint(0, 3)
    elif item.item_type == ItemType.AMULET:
        item.bonus_intelligence = 2 + rng.randint(0, 2)
    elif item.item_type == ItemType.RING:
        item.bonus_crit = 0.03 + rng.uniform(0, 0.03)


def generate_item(template_id, rarity=None, rng=None):
    rng = rng or random.Random()
    if template_id not in ALL_TEMPLATES:
        return None
    name, item_type, base_value, color = ALL_TEMPLATES[template_id]
    rarity = rarity or _roll_rarity(rng)

    item = Item(
        item_id=f"{template_id}_{rarity.value[0]}_{rng.randint(0, 999999)}",
        name=name,
        item_type=item_type,
        rarity=rarity,
        value=base_value,
        icon_color=color,
    )
    if rarity in PREFIXES:
        prefix = rng.choice(PREFIXES[rarity])
        item.name = f"{prefix} {item.name.lower()}"

    _apply_base_bonus(item, rng)
    _apply_affixes(item, rarity, rng)
    return item


def roll_random_equipment(rng):
    template_id = rng.choice(list(ALL_TEMPLATES.keys()))
    return generate_item(template_id, rng=rng)


def starting_equipment(class_id):
    from models.item import Item, ItemType, Rarity

    starting = {
        "warrior": [
            ("sword_iron", "Железный меч"),
            ("shield_wood", "Деревянный щит"),
            ("armor_leather", "Кожаная броня"),
        ],
        "rogue": [
            ("dagger_iron", "Железный кинжал"),
            ("armor_leather", "Кожаная броня"),
            ("boots_leather", "Кожаные сапоги"),
        ],
        "mage": [("staff_oak", "Дубовый посох"), ("amulet_jade", "Нефритовый амулет")],
        "archer": [
            ("bow_wood", "Деревянный лук"),
            ("gloves_leather", "Кожаные перчатки"),
            ("boots_leather", "Кожаные сапоги"),
        ],
    }
    result = []
    for template_id, name in starting.get(class_id, []):
        if template_id not in ALL_TEMPLATES:
            continue
        _, item_type, base_value, color = ALL_TEMPLATES[template_id]
        item = Item(
            item_id=f"{template_id}_start_{class_id}",
            name=name,
            item_type=item_type,
            rarity=Rarity.COMMON,
            value=base_value,
            icon_color=color,
        )
        # Базовые бонусы
        if item_type == ItemType.WEAPON:
            item.bonus_attack = 5
        elif item_type in (ItemType.HELMET, ItemType.ARMOR):
            item.bonus_defense = 3
            item.bonus_hp = 5
        elif item_type in (ItemType.GLOVES, ItemType.BOOTS):
            item.bonus_agility = 1
        elif item_type == ItemType.SHIELD:
            item.bonus_defense = 5
        elif item_type == ItemType.AMULET:
            item.bonus_intelligence = 2
        result.append(item)
    return result
