import random

from core.config import WORLD_H, WORLD_W
from core.noise import ValueNoise
from world.biome import Biome
from world.poi import POI, POIType
from world.segment import Segment

VILLAGE_NAMES = [
    "Ravenhold",
    "Thornwick",
    "Greystone",
    "Mirefall",
    "Hollowbrook",
    "Aldergrove",
    "Duskwallow",
    "Fernhollow",
]
QUEST_NAMES = [
    "Sunken Crypt",
    "Ashen Sanctum",
    "The Silent Ruin",
    "Whispering Catacombs",
    "Frostbound Halls",
    "The Blighted Well",
]
MAIN_QUEST_NAMES = ["The Fractured Spire"]
WILD_NAMES = [
    "Wilderness",
    "Old Grove",
    "Broken Stones",
    "Hunter's Trail",
    "Elder Meadow",
]


class WorldMap:
    def __init__(self, width=WORLD_W, height=WORLD_H, seed=42):
        self.width = width
        self.height = height
        self.seed = seed
        self.elevation = ValueNoise(seed)
        self.temperature = ValueNoise(seed + 1)
        self.moisture = ValueNoise(seed + 2)
        self.segments = {}
        self.pois = []
        self.start_gx = width // 2
        self.start_gy = height // 2
        self._generate()
        self._place_pois()

    def _generate(self):
        for gy in range(self.height):
            for gx in range(self.width):
                biome = self._pick_biome(gx, gy)
                seg_seed = hash((self.seed, gx, gy)) & 0xFFFFFFFF
                self.segments[(gx, gy)] = Segment(gx, gy, biome, seg_seed)

    def _pick_biome(self, gx, gy):
        elev = self.elevation.fbm(gx * 0.06, gy * 0.06, octaves=4)
        temp = self.temperature.fbm(gx * 0.04, gy * 0.04, octaves=3)
        moist = self.moisture.fbm(gx * 0.08, gy * 0.08, octaves=3)

        if elev < 0.35:
            return Biome.OCEAN
        if elev > 0.75:
            return Biome.MOUNTAIN
        if temp < 0.30:
            return Biome.TUNDRA
        if temp > 0.65 and moist < 0.35:
            return Biome.DESERT
        if moist > 0.60:
            return Biome.FOREST
        return Biome.PLAINS

    def _place_pois(self):
        rng = random.Random(self.seed + 9001)
        walkable = [
            (gx, gy) for (gx, gy), seg in self.segments.items() if seg.biome.walkable
        ]
        if not walkable:
            return

        used = set()

        def place(poi_type, name_pool, min_dist, max_tries=800):
            for _ in range(max_tries):
                gx, gy = rng.choice(walkable)
                if (gx, gy) in used:
                    continue
                too_close = False
                for ux, uy in used:
                    if abs(ux - gx) + abs(uy - gy) < min_dist:
                        too_close = True
                        break
                if too_close:
                    continue

                name = rng.choice(name_pool)
                poi = POI(poi_type, gx, gy, name)
                seg = self.segments[(gx, gy)]
                seg.location_type = poi.location_type
                seg.poi = poi
                used.add((gx, gy))
                self.pois.append(poi)
                return poi
            return None

        # Стартовая деревня — ближайший проходимый сегмент к центру
        cx, cy = self.width // 2, self.height // 2
        best = None
        best_d2 = None
        for gx, gy in walkable:
            d2 = (gx - cx) ** 2 + (gy - cy) ** 2
            if best_d2 is None or d2 < best_d2:
                best_d2 = d2
                best = (gx, gy)

        if best is not None:
            gx, gy = best
            start_poi = POI(POIType.STARTING_VILLAGE, gx, gy, "Ravenhold")
            seg = self.segments[(gx, gy)]
            seg.location_type = start_poi.location_type
            seg.poi = start_poi
            self.pois.append(start_poi)
            used.add((gx, gy))
            self.start_gx, self.start_gy = gx, gy

        # 6 деревень
        for _ in range(6):
            place(POIType.VILLAGE, VILLAGE_NAMES, 12)

        # 3 квестовых данжа
        for _ in range(3):
            place(POIType.QUEST_DUNGEON, QUEST_NAMES, 15)

        # 1 главный антагонист
        place(POIType.MAIN_ANTAGONIST, MAIN_QUEST_NAMES, 25)

        # 10 диких точек
        for _ in range(10):
            place(POIType.WILD_POINT, WILD_NAMES, 5)

    def get(self, gx, gy):
        return self.segments.get((gx, gy))

    def poi_at(self, gx, gy):
        seg = self.segments.get((gx, gy))
        return seg.poi if seg else None
