import random

from core.config import CHUNK_SIZE, LOCAL_H, LOCAL_W, TILE_SIZE
from world.biome import Biome

WALL_TILES = {"water", "rock", "tree", "cactus"}


class LocalMap:
    def __init__(self, width, height, biome, tiles):
        self.width = width
        self.height = height
        self.biome = biome
        self.tiles = tiles              # tiles[y][x] — строка-идентификатор

        # spatial hash: (cx, cy) -> список pg.Rect стен
        self.walls_by_chunk = {}
        self._build_walls_index()

    def _build_walls_index(self):
        import pygame as pg
        for ty in range(self.height):
            row = self.tiles[ty]
            for tx in range(self.width):
                if row[tx] in WALL_TILES:
                    chunk = (tx // CHUNK_SIZE, ty // CHUNK_SIZE)
                    rect = pg.Rect(tx * TILE_SIZE, ty * TILE_SIZE,
                                   TILE_SIZE, TILE_SIZE)
                    self.walls_by_chunk.setdefault(chunk, []).append(rect)

    def is_walkable(self, tx, ty):
        if not (0 <= tx < self.width and 0 <= ty < self.height):
            return False
        return self.tiles[ty][tx] not in WALL_TILES

    def walls_near(self, px: float, py: float, radius_px: int = 128) -> list:
        """Возвращает стены в радиусе radius_px от точки (px, py)."""
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


# --- Генерация ---
FILLERS = {
    Biome.PLAINS:   [("grass", 0.90), ("tree", 0.08), ("rock", 0.02)],
    Biome.FOREST:   [("grass", 0.55), ("tree", 0.40), ("rock", 0.05)],
    Biome.DESERT:   [("sand",  0.80), ("cactus", 0.15), ("rock", 0.05)],
    Biome.TUNDRA:   [("snow",  0.75), ("rock", 0.20), ("tree", 0.05)],
    Biome.MOUNTAIN: [("rock",  0.95), ("snow", 0.05)],
    Biome.OCEAN:    [("water", 1.0)],
}


def generate_local_map(biome: Biome, seed: int) -> LocalMap:
    rng = random.Random(seed)
    w, h = LOCAL_W, LOCAL_H

    weights = FILLERS[biome]
    ids = [t for t, _ in weights]
    probs = [p for _, p in weights]

    # генерация построчно — быстрее, чем вложенный цикл по одному тайлу
    tiles = [
        rng.choices(ids, weights=probs, k=w)
        for _ in range(h)
    ]

    # "пятачок" вокруг центра — чтобы игрок не заспавнился в дереве
    cx, cy = w // 2, h // 2
    ground = "sand" if biome == Biome.OCEAN else "grass"
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            tiles[cy + dy][cx + dx] = ground

    return LocalMap(w, h, biome, tiles)