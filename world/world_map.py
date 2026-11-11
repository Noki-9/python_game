import heapq
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

DIRS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


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
        self.rivers: set[tuple[int, int]] = set()
        self.lakes: set[tuple[int, int]] = set()
        self.crossings: set[tuple[int, int]] = set()
        self.roads: set[tuple[int, int]] = set()
        self.start_gx = width // 2
        self.start_gy = height // 2
        self._generate()
        self._generate_hydrography()
        self._place_pois()
        self._build_roads()

    # ------------------------------------------------------------------
    # Биомы
    # ------------------------------------------------------------------
    def _generate(self):
        for gy in range(self.height):
            for gx in range(self.width):
                biome = self._pick_biome(gx, gy)
                seg_seed = hash((self.seed, gx, gy)) & 0xFFFFFFFF
                self.segments[(gx, gy)] = Segment(gx, gy, biome, seg_seed)

    def _elev(self, gx, gy):
        return self.elevation.fbm(gx * 0.06, gy * 0.06, octaves=4)

    def _pick_biome(self, gx, gy):
        elev = self._elev(gx, gy)
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

    # ------------------------------------------------------------------
    # Реки и озёра (ТЗ 3.2)
    # ------------------------------------------------------------------
    def _generate_hydrography(self):
        rng = random.Random(self.seed + 4242)
        self._generate_lakes(rng)
        self._generate_rivers(rng)
        self._place_fords(rng)

    def _generate_lakes(self, rng):
        candidates = [
            (gx, gy)
            for (gx, gy), seg in self.segments.items()
            if seg.biome not in (Biome.OCEAN, Biome.MOUNTAIN)
            and 0.36 <= self._elev(gx, gy) <= 0.47
        ]
        rng.shuffle(candidates)
        made = 0
        for gx, gy in candidates:
            if made >= 6:
                break
            if (gx, gy) in self.lakes:
                continue
            level = self._elev(gx, gy) + 0.045
            cells = self._flood_lake(gx, gy, level, limit=16)
            if len(cells) < 3:
                continue
            for cx, cy in cells:
                seg = self.segments[(cx, cy)]
                if seg.biome == Biome.OCEAN:
                    continue
                seg.lake = True
                self.lakes.add((cx, cy))
            made += 1

    def _flood_lake(self, gx, gy, level, limit):
        seen = set()
        queue = [(gx, gy)]
        while queue and len(seen) < limit:
            cx, cy = queue.pop()
            if (cx, cy) in seen:
                continue
            seg = self.segments.get((cx, cy))
            if seg is None or seg.biome in (Biome.OCEAN, Biome.MOUNTAIN):
                continue
            if self._elev(cx, cy) > level:
                continue
            seen.add((cx, cy))
            for dx, dy in DIRS4:
                queue.append((cx + dx, cy + dy))
        return list(seen)

    def _generate_rivers(self, rng):
        sources = [
            (gx, gy)
            for (gx, gy), seg in self.segments.items()
            if seg.biome == Biome.MOUNTAIN and self._elev(gx, gy) > 0.76
        ]
        rng.shuffle(sources)
        for source in sources[:9]:
            self._trace_river(source, rng)

    def _trace_river(self, source, rng):
        current = source
        visited = set()
        for _step in range(500):
            if current in visited:
                break
            visited.add(current)
            seg = self.segments.get(current)
            if seg is None:
                break
            if seg.biome == Biome.OCEAN or seg.lake:
                break
            seg.river = True
            self.rivers.add(current)

            cx, cy = current
            current_elev = self._elev(cx, cy)
            options = []
            for dx, dy in DIRS4 + ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                nx, ny = cx + dx, cy + dy
                nseg = self.segments.get((nx, ny))
                if nseg is None:
                    continue
                if (nx, ny) in self.rivers:
                    continue
                options.append((self._elev(nx, ny), (nx, ny)))
            if not options:
                break
            options.sort(key=lambda item: item[0])
            next_elev, next_cell = options[0]
            next_seg = self.segments[next_cell]
            # Дошли до океана/озера — русло завершено.
            if next_seg.biome == Biome.OCEAN or next_seg.lake:
                break
            # Локальный минимум — река заканчивается.
            if next_elev > current_elev + 0.012:
                break
            current = next_cell

    def _place_fords(self, rng):
        """Броды: редкие проходимые клетки на реках."""
        river_cells = sorted(self.rivers)
        rng.shuffle(river_cells)
        for gx, gy in river_cells:
            if rng.random() > 0.16:
                continue
            # Не ставим броды вплотную друг к другу.
            if any(
                abs(gx - ox) + abs(gy - oy) <= 2
                for ox, oy in self.crossings
            ):
                continue
            seg = self.segments[(gx, gy)]
            seg.crossing = True
            self.crossings.add((gx, gy))

    # ------------------------------------------------------------------
    # Дороги (ТЗ 3.2)
    # ------------------------------------------------------------------
    def _build_roads(self):
        hubs = [p for p in self.pois if p.poi_type != POIType.WILD_POINT]
        if not hubs:
            return
        start = next(
            (p for p in hubs if p.poi_type == POIType.STARTING_VILLAGE), hubs[0]
        )
        connected = {(start.gx, start.gy)}

        # Каждый POI соединяем с ближайшим уже подключённым узлом.
        pending = [
            (p.gx, p.gy) for p in hubs if (p.gx, p.gy) not in connected
        ]
        while pending:
            best = None
            best_pair = None
            for target in pending:
                for src in connected:
                    d = abs(target[0] - src[0]) + abs(target[1] - src[1])
                    if best is None or d < best:
                        best = d
                        best_pair = (src, target)
            if best_pair is None:
                break
            src, target = best_pair
            path = self._find_path(src, target)
            if path:
                self._mark_road(path)
                connected.add(target)
            pending.remove(target)

    def _step_cost(self, gx, gy):
        seg = self.segments[(gx, gy)]
        if seg.lake:
            return None
        if seg.river:
            return 2 if seg.crossing else 7
        if not seg.biome.walkable:
            return None
        base = {
            Biome.PLAINS: 1,
            Biome.FOREST: 3,
            Biome.DESERT: 4,
            Biome.TUNDRA: 4,
        }.get(seg.biome, 2)
        if seg.road:
            return 1
        return base

    def _find_path(self, start, goal):
        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))
        if start == goal:
            return [start]
        open_heap = [(0, 0, start)]
        came_from = {}
        g_score = {start: 0}
        counter = 0
        while open_heap:
            _f, _c, current = heapq.heappop(open_heap)
            if current == goal:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                return path
            cx, cy = current
            for dx, dy in DIRS4:
                nxt = (cx + dx, cy + dy)
                if nxt not in self.segments:
                    continue
                cost = self._step_cost(*nxt)
                if cost is None:
                    continue
                tentative = g_score[current] + cost
                if tentative < g_score.get(nxt, 1 << 30):
                    came_from[nxt] = current
                    g_score[nxt] = tentative
                    h = abs(nxt[0] - goal[0]) + abs(nxt[1] - goal[1])
                    counter += 1
                    heapq.heappush(open_heap, (tentative + h, counter, nxt))
        return None

    def _mark_road(self, path):
        for gx, gy in path:
            seg = self.segments[(gx, gy)]
            if seg.lake:
                continue
            if seg.river:
                seg.crossing = True
                seg.bridge = True
                self.crossings.add((gx, gy))
            elif seg.biome.walkable:
                seg.road = True
                self.roads.add((gx, gy))

    # ------------------------------------------------------------------
    # POI
    # ------------------------------------------------------------------
    def _place_pois(self):
        rng = random.Random(self.seed + 9001)
        walkable = [
            (gx, gy)
            for (gx, gy), seg in self.segments.items()
            if self.is_passable(gx, gy)
        ]
        if not walkable:
            return

        used = set()

        def place(poi_type, name_pool, min_dist, max_tries=1200):
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

    # ------------------------------------------------------------------
    def get(self, gx, gy):
        return self.segments.get((gx, gy))

    def poi_at(self, gx, gy):
        seg = self.segments.get((gx, gy))
        return seg.poi if seg else None

    def is_passable(self, gx, gy):
        """Можно ли войти в сегмент с учётом рек, озёр и бродов."""
        seg = self.get(gx, gy)
        if seg is None:
            return False
        if seg.lake:
            return False
        if seg.river:
            return seg.crossing
        return seg.biome.walkable
