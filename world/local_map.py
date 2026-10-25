import random

from core.config import CHUNK_SIZE, LOCAL_H, LOCAL_W, TILE_SIZE
from core.noise import ValueNoise
from world.biome import Biome
from world.location_type import LocationType

WALL_TILES = {"water", "rock", "tree", "cactus", "house_wall"}

TRANSITION_WIDTH = 12
WATER_DEPTH = 3
NOISE_AMPLITUDE = 6


class LocalMap:
    def __init__(self, width, height, biome, tiles, spawn_tile):
        self.width = width
        self.height = height
        self.biome = biome
        self.tiles = tiles
        self.spawn_tile = spawn_tile
        self.walls_by_chunk = {}
        self._build_walls_index()

    def _build_walls_index(self):
        import pygame as pg

        for ty in range(self.height):
            row = self.tiles[ty]
            for tx in range(self.width):
                if row[tx] in WALL_TILES:
                    chunk = (tx // CHUNK_SIZE, ty // CHUNK_SIZE)
                    rect = pg.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    self.walls_by_chunk.setdefault(chunk, []).append(rect)

    def is_walkable(self, tx, ty):
        if not (0 <= tx < self.width and 0 <= ty < self.height):
            return False
        return self.tiles[ty][tx] not in WALL_TILES

    def walls_near(self, px, py, radius_px=128):
        cx0 = int((px - radius_px) // (CHUNK_SIZE * TILE_SIZE))
        cy0 = int((py - radius_px) // (CHUNK_SIZE * TILE_SIZE))
        cx1 = int((px + radius_px) // (CHUNK_SIZE * TILE_SIZE))
        cy1 = int((py + radius_px) // (CHUNK_SIZE * TILE_SIZE))
        result = []
        for cy in range(cy0, cy1 + 1):
            for cx in range(cx0, cx1 + 1):
                chunk = self.walls_by_chunk.get((cx, cy))
                if chunk:
                    result.extend(chunk)
        return result


# ---------- Переходы биомов ----------

_DIR_OFFSET = {"n": 0.0, "s": 500.0, "w": 1000.0, "e": 1500.0}


def _distance_to_edge(x, y, w, h, direction):
    if direction == "n":
        return y
    if direction == "s":
        return h - 1 - y
    if direction == "w":
        return x
    if direction == "e":
        return w - 1 - x
    return 999


def _edge_ranges(direction, w, h, max_depth):
    max_depth = int(max_depth) + 2
    if direction == "n":
        return range(min(h, max_depth)), range(w)
    if direction == "s":
        return range(max(0, h - max_depth), h), range(w)
    if direction == "w":
        return range(h), range(min(w, max_depth))
    if direction == "e":
        return range(h), range(max(0, w - max_depth), w)
    return range(0), range(0)


def _noisy_distance(x, y, w, h, direction, noise):
    d = _distance_to_edge(x, y, w, h, direction)
    off = _DIR_OFFSET[direction]
    n = noise.fbm(x * 0.12 + off, y * 0.12 + off, octaves=4)
    return d + (n - 0.5) * NOISE_AMPLITUDE * 2


def _transition_ocean(tiles, w, h, direction, rng, noise):
    max_depth = TRANSITION_WIDTH + NOISE_AMPLITUDE + 2
    ys, xs = _edge_ranges(direction, w, h, max_depth)
    for y in ys:
        for x in xs:
            nd = _noisy_distance(x, y, w, h, direction, noise)
            if nd < WATER_DEPTH:
                tiles[y][x] = "water"
            elif nd < TRANSITION_WIDTH:
                if tiles[y][x] not in ("water", "rock"):
                    tiles[y][x] = "sand"
    for y in ys:
        for x in xs:
            if tiles[y][x] == "sand" and rng.random() < 0.04:
                tiles[y][x] = "rock"


def _transition_scatter(
    tiles, w, h, direction, rng, noise, tile, width_scale, probability, allowed_sources
):
    max_depth = (TRANSITION_WIDTH * width_scale) + NOISE_AMPLITUDE + 2
    ys, xs = _edge_ranges(direction, w, h, max_depth)
    limit = TRANSITION_WIDTH * width_scale
    for y in ys:
        for x in xs:
            nd = _noisy_distance(x, y, w, h, direction, noise)
            if nd < limit:
                if tiles[y][x] in allowed_sources and rng.random() < probability:
                    tiles[y][x] = tile


def _apply_transition(tiles, w, h, direction, neighbor_biome, rng, noise):
    if neighbor_biome == Biome.OCEAN:
        _transition_ocean(tiles, w, h, direction, rng, noise)
    elif neighbor_biome == Biome.MOUNTAIN:
        _transition_scatter(
            tiles,
            w,
            h,
            direction,
            rng,
            noise,
            "rock",
            0.7,
            0.85,
            {"grass", "sand", "snow", "tree"},
        )
    elif neighbor_biome == Biome.DESERT:
        _transition_scatter(
            tiles, w, h, direction, rng, noise, "sand", 0.9, 1.0, {"grass", "snow"}
        )
    elif neighbor_biome == Biome.TUNDRA:
        _transition_scatter(
            tiles, w, h, direction, rng, noise, "snow", 0.9, 1.0, {"grass", "sand"}
        )
    elif neighbor_biome == Biome.FOREST:
        _transition_scatter(
            tiles,
            w,
            h,
            direction,
            rng,
            noise,
            "tree",
            0.6,
            0.4,
            {"grass", "sand", "snow"},
        )
    elif neighbor_biome == Biome.PLAINS:
        _transition_scatter(
            tiles,
            w,
            h,
            direction,
            rng,
            noise,
            "grass",
            0.4,
            0.25,
            {"sand", "snow", "rock"},
        )


FILLERS = {
    Biome.PLAINS: [("grass", 0.90), ("tree", 0.08), ("rock", 0.02)],
    Biome.FOREST: [("grass", 0.55), ("tree", 0.40), ("rock", 0.05)],
    Biome.DESERT: [("sand", 0.80), ("cactus", 0.15), ("rock", 0.05)],
    Biome.TUNDRA: [("snow", 0.75), ("rock", 0.20), ("tree", 0.05)],
    Biome.MOUNTAIN: [("rock", 0.95), ("snow", 0.05)],
    Biome.OCEAN: [("water", 1.0)],
}


# ---------- Генерация локаций по типу ----------


def _apply_village(tiles, w, h, rng):
    cx, cy = w // 2, h // 2
    plaza_r = 12

    # Площадь
    for dy in range(-plaza_r, plaza_r + 1):
        for dx in range(-plaza_r, plaza_r + 1):
            x, y = cx + dx, cy + dy
            if 0 <= x < w and 0 <= y < h:
                tiles[y][x] = "grass"

    # Дороги-крест
    for i in range(-45, 46):
        x = cx + i
        if 0 <= x < w:
            tiles[cy][x] = "road"
        y = cy + i
        if 0 <= y < h:
            tiles[y][cx] = "road"

    # Дома — в квадрантах (не пересекают площадь и дороги)
    houses = []
    attempts = 0
    while len(houses) < 7 and attempts < 120:
        attempts += 1
        hw = rng.randint(5, 8)
        hh = rng.randint(4, 6)
        hx = rng.randint(3, w - hw - 3)
        hy = rng.randint(3, h - hh - 3)

        # Не пересекается с площадью
        if (
            hx <= cx + plaza_r + 2
            and hx + hw >= cx - plaza_r - 2
            and hy <= cy + plaza_r + 2
            and hy + hh >= cy - plaza_r - 2
        ):
            continue

        # Не пересекает дороги
        if hx <= cx <= hx + hw:
            continue
        if hy <= cy <= hy + hh:
            continue

        # Не пересекается с другим домом (мин. зазор 2 тайла)
        overlap = False
        for ox, oy, ow, oh in houses:
            if not (
                hx + hw + 2 < ox
                or ox + ow + 2 < hx
                or hy + hh + 2 < oy
                or oy + oh + 2 < hy
            ):
                overlap = True
                break
        if overlap:
            continue

        # Строим
        for dy in range(hh):
            for dx in range(hw):
                if dy in (0, hh - 1) or dx in (0, hw - 1):
                    tiles[hy + dy][hx + dx] = "house_wall"
                else:
                    tiles[hy + dy][hx + dx] = "house_floor"
        door_x = hx + hw // 2
        tiles[hy + hh - 1][door_x] = "door"
        houses.append((hx, hy, hw, hh))


def _apply_quest_site(tiles, w, h, rng):
    cx, cy = w // 2, h // 2
    radius = 20
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            x, y = cx + dx, cy + dy
            if not (0 <= x < w and 0 <= y < h):
                continue
            d2 = dx * dx + dy * dy
            if d2 < 100 or d2 < radius * radius and rng.random() < 0.4:
                tiles[y][x] = "stone"


def _find_spawn_near(tiles, cx, cy, w, h, ground, max_r=60):
    for r in range(max_r):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                x, y = cx + dx, cy + dy
                if 0 <= x < w and 0 <= y < h:
                    if tiles[y][x] not in WALL_TILES:
                        return (x, y)
    # Крайний случай — расчищаем центр
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            x, y = cx + dx, cy + dy
            if 0 <= x < w and 0 <= y < h:
                tiles[y][x] = ground
    return (cx, cy)


def generate_local_map(
    biome, seed, neighbors=None, location_type=LocationType.WILD, player_state=None
):
    rng = random.Random(seed + 7919)
    noise = ValueNoise(seed + 7777)
    w, h = LOCAL_W, LOCAL_H

    weights = FILLERS[biome]
    ids = [t for t, _ in weights]
    probs = [p for _, p in weights]

    tiles = [rng.choices(ids, weights=probs, k=w) for _ in range(h)]

    # Переходы биомов
    if neighbors and biome != Biome.OCEAN:
        for direction, nbr_biome in neighbors.items():
            if nbr_biome is None or nbr_biome == biome:
                continue
            _apply_transition(tiles, w, h, direction, nbr_biome, rng, noise)

    cx, cy = w // 2, h // 2
    ground = "sand" if biome == Biome.OCEAN else "grass"

    # Тип локации
    if location_type.is_settlement:
        _apply_village(tiles, w, h, rng)
        spawn_tx, spawn_ty = cx, cy
    elif location_type.is_quest:
        _apply_quest_site(tiles, w, h, rng)
        spawn_tx, spawn_ty = cx, cy + 15
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                x, y = spawn_tx + dx, spawn_ty + dy
                if 0 <= x < w and 0 <= y < h:
                    tiles[y][x] = "stone"
    else:
        spawn_tx, spawn_ty = _find_spawn_near(tiles, cx, cy, w, h, ground)

    return LocalMap(w, h, biome, tiles, (spawn_tx, spawn_ty))
