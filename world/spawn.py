import math
import random

from core.config import TILE_SIZE
from models.animal import Animal
from models.enemy import Enemy
from world.biome import Biome

ENEMY_DEFS = {
    "goblin": dict(
        hp=20,
        speed=120,
        damage=5,
        attack_range=36,
        attack_cooldown=1.0,
        aggro_radius=180,
        xp=15,
        color=(120, 180, 80),
    ),
    "bandit": dict(
        hp=35,
        speed=130,
        damage=8,
        attack_range=40,
        attack_cooldown=0.9,
        aggro_radius=220,
        xp=25,
        color=(180, 140, 90),
    ),
    "skeleton": dict(
        hp=25,
        speed=100,
        damage=6,
        attack_range=38,
        attack_cooldown=1.1,
        aggro_radius=160,
        xp=20,
        color=(200, 200, 180),
    ),
    "troll": dict(
        hp=120,
        speed=90,
        damage=20,
        attack_range=44,
        attack_cooldown=1.5,
        aggro_radius=250,
        xp=100,
        color=(90, 130, 70),
    ),
}

ANIMAL_DEFS = {
    "deer": dict(
        hp=15,
        speed=140,
        damage=2,
        aggro_radius=200,
        xp=5,
        color=(160, 120, 80),
        passive=True,
    ),
    "wolf": dict(
        hp=30,
        speed=160,
        damage=8,
        aggro_radius=280,
        xp=20,
        color=(130, 130, 140),
        passive=False,
    ),
    "boar": dict(
        hp=25,
        speed=120,
        damage=6,
        aggro_radius=160,
        xp=15,
        color=(130, 90, 60),
        passive=False,
    ),
    "bear": dict(
        hp=80,
        speed=110,
        damage=15,
        aggro_radius=250,
        xp=50,
        color=(90, 70, 50),
        passive=False,
    ),
    "rabbit": dict(
        hp=5,
        speed=180,
        damage=1,
        aggro_radius=180,
        xp=2,
        color=(220, 220, 220),
        passive=True,
    ),
    "fox": dict(
        hp=10,
        speed=160,
        damage=3,
        aggro_radius=200,
        xp=5,
        color=(200, 120, 60),
        passive=True,
    ),
    "sheep": dict(
        hp=10,
        speed=100,
        damage=0,
        aggro_radius=150,
        xp=3,
        color=(240, 240, 230),
        passive=True,
    ),
    "snake": dict(
        hp=8,
        speed=140,
        damage=4,
        aggro_radius=140,
        xp=8,
        color=(120, 180, 90),
        passive=False,
    ),
    "scorpion": dict(
        hp=12,
        speed=130,
        damage=5,
        aggro_radius=140,
        xp=10,
        color=(160, 100, 50),
        passive=False,
    ),
    "lizard": dict(
        hp=6,
        speed=170,
        damage=2,
        aggro_radius=120,
        xp=4,
        color=(140, 180, 90),
        passive=True,
    ),
    "snow_wolf": dict(
        hp=35,
        speed=170,
        damage=9,
        aggro_radius=280,
        xp=22,
        color=(220, 230, 240),
        passive=False,
    ),
    "moose": dict(
        hp=60,
        speed=130,
        damage=10,
        aggro_radius=200,
        xp=30,
        color=(100, 70, 50),
        passive=False,
    ),
    "goat": dict(
        hp=15,
        speed=140,
        damage=3,
        aggro_radius=180,
        xp=6,
        color=(180, 170, 150),
        passive=True,
    ),
}

BIOME_ANIMALS = {
    Biome.FOREST: ["deer", "wolf", "boar", "bear"],
    Biome.DESERT: ["snake", "scorpion", "lizard"],
    Biome.TUNDRA: ["snow_wolf", "moose"],
    Biome.PLAINS: ["rabbit", "fox", "sheep"],
    Biome.MOUNTAIN: ["goat"],
}

BIOME_ENEMIES = {
    Biome.FOREST: ["goblin", "bandit"],
    Biome.DESERT: ["bandit", "skeleton"],
    Biome.TUNDRA: ["goblin", "skeleton"],
    Biome.PLAINS: ["goblin", "bandit"],
    Biome.MOUNTAIN: ["troll", "skeleton"],
}


def _random_free_pos(rng, local_map, avoid_pos=None, min_dist=0):
    for _ in range(300):
        tx = rng.randint(5, local_map.width - 6)
        ty = rng.randint(5, local_map.height - 6)
        if not local_map.is_walkable(tx, ty):
            continue
        px = tx * TILE_SIZE
        py = ty * TILE_SIZE
        if avoid_pos is not None and min_dist > 0:
            if math.hypot(px - avoid_pos[0], py - avoid_pos[1]) < min_dist:
                continue
        return px, py
    return None


def spawn_enemies(local_map, biome, location_type, seed, level=1):
    rng = random.Random(seed + 13)
    enemies = []

    if location_type.is_settlement:
        return enemies

    if location_type.is_quest:
        count = rng.randint(6, 10)
    else:
        count = rng.randint(3, 6)

    pool = BIOME_ENEMIES.get(biome, ["goblin"])
    spawn_tx, spawn_ty = local_map.spawn_tile
    avoid = (spawn_tx * TILE_SIZE, spawn_ty * TILE_SIZE)

    for i in range(count):
        enemy_id = rng.choice(pool)

        # В квесте на горе — босс-тролль
        if location_type.is_quest and i == 0 and biome == Biome.MOUNTAIN:
            enemy_id = "troll"

        defn = ENEMY_DEFS[enemy_id]

        pos = _random_free_pos(rng, local_map, avoid, min_dist=220)
        if pos is None:
            continue
        px, py = pos

        e = Enemy(
            enemy_id,
            px,
            py,
            TILE_SIZE - 8,
            TILE_SIZE - 8,
            health=defn["hp"],
            speed=defn["speed"],
            damage=defn["damage"],
            attack_range=defn["attack_range"],
            attack_cooldown=defn["attack_cooldown"],
            aggro_radius=defn["aggro_radius"],
            xp_reward=defn["xp"],
            color=defn["color"],
            loot_rng_seed=rng.randint(0, 1_000_000),
        )
        enemies.append(e)

    return enemies


def spawn_animals(local_map, biome, location_type, seed):
    rng = random.Random(seed + 17)
    animals = []

    if location_type.is_quest or location_type.is_settlement:
        return animals

    pool = BIOME_ANIMALS.get(biome, [])
    if not pool:
        return animals

    count = rng.randint(5, 10)
    spawn_tx, spawn_ty = local_map.spawn_tile
    avoid = (spawn_tx * TILE_SIZE, spawn_ty * TILE_SIZE)

    for _ in range(count):
        animal_id = rng.choice(pool)
        defn = ANIMAL_DEFS[animal_id]

        pos = _random_free_pos(rng, local_map, avoid, min_dist=120)
        if pos is None:
            continue
        px, py = pos

        a = Animal(
            animal_id,
            px,
            py,
            TILE_SIZE - 8,
            TILE_SIZE - 8,
            health=defn["hp"],
            speed=defn["speed"],
            damage=defn["damage"],
            aggro_radius=defn["aggro_radius"],
            xp_reward=defn["xp"],
            color=defn["color"],
            passive=defn["passive"],
            loot_rng_seed=rng.randint(0, 1_000_000),
        )
        animals.append(a)

    return animals
