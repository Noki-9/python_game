import math
import random

from core.config import TILE_SIZE
from models.npc import NPC
from world.dialogue import ROLE_TITLES
from world.item_generator import roll_random_equipment

MALE_NAMES = [
    "Бьорн",
    "Альдрик",
    "Герольд",
    "Томас",
    "Эдвин",
    "Седрик",
    "Озвин",
    "Рурик",
    "Эрик",
    "Гаральд",
]
FEMALE_NAMES = [
    "Мира",
    "Элара",
    "Лиса",
    "Сэра",
    "Хальда",
    "Фрейя",
    "Ингрид",
    "Астрид",
    "Сигрун",
    "Тира",
]

ROLE_COLORS = {
    "merchant": (220, 180, 80),
    "blacksmith": (170, 130, 90),
    "healer": (200, 220, 200),
    "elder": (200, 180, 200),
    "questgiver": (220, 180, 180),
    "guard": (130, 130, 180),
}


def _generate_shop_inventory(rng):
    items = []
    for _ in range(rng.randint(6, 10)):
        item = roll_random_equipment(rng)
        if item:
            items.append(item)
    return items


def _find_npc_pos(rng, local_map, cx_px, cy_px, existing):
    for _ in range(200):
        angle = rng.uniform(0, 2 * math.pi)
        dist = rng.uniform(3, 9) * TILE_SIZE
        px = int(cx_px + math.cos(angle) * dist)
        py = int(cy_px + math.sin(angle) * dist)
        tx = px // TILE_SIZE
        ty = py // TILE_SIZE
        if not (0 <= tx < local_map.width and 0 <= ty < local_map.height):
            continue
        if not local_map.is_walkable(tx, ty):
            continue
        ok = True
        for other in existing:
            if math.hypot(px - other.x, py - other.y) < 56:
                ok = False
                break
        if ok:
            return px, py
    return None


def spawn_npcs(local_map, seed, is_starting=False):
    rng = random.Random(seed + 23)
    npcs = []

    roles = ["merchant", "healer", "elder", "questgiver", "guard"]
    if rng.random() < 0.5:
        roles.append("guard")
    if not is_starting and rng.random() < 0.5:
        roles.append("blacksmith")

    spawn_tx, spawn_ty = local_map.spawn_tile
    cx_px = spawn_tx * TILE_SIZE
    cy_px = spawn_ty * TILE_SIZE

    for role in roles:
        pos = _find_npc_pos(rng, local_map, cx_px, cy_px, npcs)
        if pos is None:
            continue
        px, py = pos
        name = rng.choice(MALE_NAMES + FEMALE_NAMES)
        color = ROLE_COLORS.get(role, (180, 180, 180))

        npc = NPC(
            npc_id=f"{role}_{rng.randint(0, 999999)}",
            name=name,
            role=role,
            x=px,
            y=py,
            rect_x=TILE_SIZE - 8,
            rect_y=TILE_SIZE - 8,
            color=color,
        )
        npc.role_title = ROLE_TITLES.get(role, "")

        if role in ("merchant", "blacksmith"):
            npc.inventory = _generate_shop_inventory(rng)

        npcs.append(npc)

    return npcs
