import random

from core.config import CHUNK_SIZE, LOCAL_H, LOCAL_W, TILE_SIZE
from core.noise import ValueNoise
from world.biome import Biome

WALL_TILES = {"water", "rock", "tree", "cactus"}

TRANSITION_WIDTH = 12  # макс. ширина переходной полосы
WATER_DEPTH = 3  # минимум воды у самого края
NOISE_AMPLITUDE = 6  # насколько шум сдвигает границу (±6 тайлов)


class LocalMap:
    def __init__(self, width, height, biome, tiles):
        self.width = width
        self.height = height
        self.biome = biome
        self.tiles = tiles
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

    def walls_near(self, px: float, py: float, radius_px: int = 128) -> list:
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


# --- Утилиты границы ---

_DIR_OFFSET = {"n": 0.0, "s": 500.0, "w": 1000.0, "e": 1500.0}
_DIR_NEIGHBOR = {"n": (0, -1), "s": (0, 1), "w": (-1, 0), "e": (1, 0)}


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
    """Диапазоны (ys, xs) — только клетки в полосе у нужного края."""
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
    """Расстояние до края + шум — граница становится «живой»."""
    d = _distance_to_edge(x, y, w, h, direction)
    off = _DIR_OFFSET[direction]
    n = noise.fbm(x * 0.12 + off, y * 0.12 + off, octaves=4)
    return d + (n - 0.5) * NOISE_AMPLITUDE * 2


# --- Обработчики переходов ---


def _transition_ocean(tiles, w, h, direction, rng, noise):
    max_depth = TRANSITION_WIDTH + NOISE_AMPLITUDE + 2
    ys, xs = _edge_ranges(direction, w, h, max_depth)

    # Вода + песок
    for y in ys:
        for x in xs:
            nd = _noisy_distance(x, y, w, h, direction, noise)
            if nd < WATER_DEPTH:
                tiles[y][x] = "water"
            elif nd < TRANSITION_WIDTH:
                if tiles[y][x] not in ("water", "rock"):
                    tiles[y][x] = "sand"

    # Разбросанные камни на пляже
    for y in ys:
        for x in xs:
            if tiles[y][x] == "sand" and rng.random() < 0.04:
                tiles[y][x] = "rock"


def _transition_scatter(
    tiles, w, h, direction, rng, noise, tile, width_scale, probability, allowed_sources
):
    """Общий случай: разбрасывает tile с шумной шириной."""
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
    """Выбирает стиль перехода под биом-соседа."""
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
            tile="rock",
            width_scale=0.7,
            probability=0.85,
            allowed_sources={"grass", "sand", "snow", "tree"},
        )

    elif neighbor_biome == Biome.DESERT:
        _transition_scatter(
            tiles,
            w,
            h,
            direction,
            rng,
            noise,
            tile="sand",
            width_scale=0.9,
            probability=1.0,
            allowed_sources={"grass", "snow"},
        )

    elif neighbor_biome == Biome.TUNDRA:
        _transition_scatter(
            tiles,
            w,
            h,
            direction,
            rng,
            noise,
            tile="snow",
            width_scale=0.9,
            probability=1.0,
            allowed_sources={"grass", "sand"},
        )

    elif neighbor_biome == Biome.FOREST:
        _transition_scatter(
            tiles,
            w,
            h,
            direction,
            rng,
            noise,
            tile="tree",
            width_scale=0.6,
            probability=0.4,
            allowed_sources={"grass", "sand", "snow"},
        )

    elif neighbor_biome == Biome.PLAINS:
        # Равнины — самый мягкий переход: редкие пятна травы
        _transition_scatter(
            tiles,
            w,
            h,
            direction,
            rng,
            noise,
            tile="grass",
            width_scale=0.4,
            probability=0.25,
            allowed_sources={"sand", "snow", "rock"},
        )


FILLERS = {
    Biome.PLAINS: [("grass", 0.90), ("tree", 0.08), ("rock", 0.02)],
    Biome.FOREST: [("grass", 0.55), ("tree", 0.40), ("rock", 0.05)],
    Biome.DESERT: [("sand", 0.80), ("cactus", 0.15), ("rock", 0.05)],
    Biome.TUNDRA: [("snow", 0.75), ("rock", 0.20), ("tree", 0.05)],
    Biome.MOUNTAIN: [("rock", 0.95), ("snow", 0.05)],
    Biome.OCEAN: [("water", 1.0)],
}


def generate_local_map(biome: Biome, seed: int, neighbors=None) -> LocalMap:
    rng = random.Random(seed)
    noise = ValueNoise(seed + 7777)  # отдельный шум для границ
    w, h = LOCAL_W, LOCAL_H

    weights = FILLERS[biome]
    ids = [t for t, _ in weights]
    probs = [p for _, p in weights]

    tiles = [rng.choices(ids, weights=probs, k=w) for _ in range(h)]

    # Переходы для каждого соседа
    if neighbors and biome != Biome.OCEAN:
        for direction, nbr_biome in neighbors.items():
            if nbr_biome is None or nbr_biome == biome:
                continue
            _apply_transition(tiles, w, h, direction, nbr_biome, rng, noise)

    # Пятачок спавна — обязательно ПОСЛЕ переходов
    cx, cy = w // 2, h // 2
    ground = "sand" if biome == Biome.OCEAN else "grass"
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            tiles[cy + dy][cx + dx] = ground

    return LocalMap(w, h, biome, tiles)
