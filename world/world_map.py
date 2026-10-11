from core.config import WORLD_H, WORLD_W
from core.noise import ValueNoise
from world.biome import Biome
from world.segment import Segment


class WorldMap:
    def __init__(self, width: int = WORLD_W, height: int = WORLD_H, seed: int = 42):
        self.width = width
        self.height = height
        self.seed = seed
        self.elevation = ValueNoise(seed)
        self.temperature = ValueNoise(seed + 1)
        self.moisture = ValueNoise(seed + 2)
        self.segments = {}
        self._generate()

    def _generate(self):
        # 18 000 итераций — терпимо. Если станет медленно —
        # генерируйте сегменты лениво, по мере приближения игрока.
        for gy in range(self.height):
            for gx in range(self.width):
                biome = self._pick_biome(gx, gy)
                seg_seed = hash((self.seed, gx, gy)) & 0xFFFFFFFF
                self.segments[(gx, gy)] = Segment(gx, gy, biome, seg_seed)

    def _pick_biome(self, gx: int, gy: int) -> Biome:
        # частоты подобраны под размер карты 150×120
        elev = self.elevation.fbm(gx * 0.06, gy * 0.06, octaves=4)
        temp = self.temperature.fbm(gx * 0.04, gy * 0.04, octaves=3)
        moist = self.moisture.fbm(gx * 0.08, gy * 0.08, octaves=3)

        if elev < 0.35:  return Biome.OCEAN
        if elev > 0.75:  return Biome.MOUNTAIN
        if temp < 0.30:  return Biome.TUNDRA
        if temp > 0.65 and moist < 0.35: return Biome.DESERT
        if moist > 0.60: return Biome.FOREST
        return Biome.PLAINS

    def get(self, gx: int, gy: int) -> Segment | None:
        return self.segments.get((gx, gy))