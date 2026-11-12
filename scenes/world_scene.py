import math

import pygame as pg

from core.assets import assets
from core.camera import Camera
from core.config import (
    MEMORY_VISIBILITY,
    VISION_FAR,
    VISION_FAR_SQ,
    VISION_NEAR,
    VISION_NEAR_SQ,
    screen,
)
from core.scene_manager import Scene
from core.utils import direction_name
from ui.character_ui import CharacterUI
from ui.inventory_ui import InventoryUI
from ui.quest_log_ui import QuestLogUI
from ui.skills_ui import SkillsUI
from world.biome import Biome

SEG_SIZE = 16
CAM_PAN_SPEED = 600
MOVE_REPEAT_DELAY = 0.2

BIOME_MOVE_COST = {
    Biome.PLAINS: 1,
    Biome.FOREST: 2,
    Biome.DESERT: 3,
    Biome.TUNDRA: 3,
}
DEFAULT_MOVE_COST = 1

MINIMAP_W = 180
MINIMAP_H = 144

POI_ICONS = {
    "starting_village": "village_start",
    "village": "village",
    "quest_dungeon": "quest",
    "main_antagonist": "main",
    "wild_point": "wild",
}

# Тайлы для глобальной карты: сегмент рисуется текстурой биома.
# Лес строится из травяной подложки и разбросанных поверх деревьев,
# чтобы деревья не повторялись ровной сеткой.
BIOME_TILE = {
    Biome.OCEAN: "water",
    Biome.TUNDRA: "snow",
    Biome.DESERT: "sand",
    Biome.PLAINS: "grass",
    Biome.FOREST: "grass",
    Biome.MOUNTAIN: "rock",
}
FOREST_TINT = (16, 52, 24)
FOREST_TINT_ALPHA = 78
FOREST_TREE_SIZES = (18, 22, 26)


def _mix(a, b, t):
    return (
        int(a[0] * (1 - t) + b[0] * t),
        int(a[1] * (1 - t) + b[1] * t),
        int(a[2] * (1 - t) + b[2] * t),
    )


def _hash01(gx, gy, salt):
    h = (gx * 73856093) ^ (gy * 19349663) ^ (salt * 2654435761)
    h = (h ^ (h >> 16)) * 0x85EBCA6B & 0xFFFFFFFF
    h = h ^ (h >> 13)
    return (h & 0xFFFFFFFF) / 0xFFFFFFFF


def _edge_noise(gx, gy, direction, i):
    d = {"N": 0, "S": 1, "W": 2, "E": 3}[direction]
    h = (gx * 73856093) ^ (gy * 19349663) ^ (d * 83492791) ^ (i * 2654435761)
    h = (h ^ (h >> 16)) * 0x85EBCA6B & 0xFFFFFFFF
    h = h ^ (h >> 13)
    return (h & 0xFFFFFFFF) / 0xFFFFFFFF


class WorldScene(Scene):
    def __init__(self, manager, world, world_pos=None, mode="spawn"):
        self.manager = manager
        self.state = manager.player_state
        self.world = world
        self.mode = mode

        if world_pos is not None:
            self.gx, self.gy = world_pos
        else:
            self.gx = world.start_gx
            self.gy = world.start_gy

        sw, sh = screen.get_size()
        self.camera = Camera(sw, sh)
        self.map_w_px = world.width * SEG_SIZE
        self.map_h_px = world.height * SEG_SIZE

        self.hover_seg = None
        self.hover_valid = False

        self._font_hint = pg.font.SysFont(None, 22)
        self._font_small = pg.font.SysFont(None, 16)

        self._fog_surface = None
        self._minimap_surf = None
        self._minimap_dirty = True
        self._minimap_full = None
        self.move_cooldown = 0.0
        self.message = ""
        self.message_timer = 0.0

        self._ensure_prerender()

    @property
    def gx(self):
        return self.state.gx

    @gx.setter
    def gx(self, v):
        self.state.gx = v

    @property
    def gy(self):
        return self.state.gy

    @gy.setter
    def gy(self, v):
        self.state.gy = v

    # ================= Пре-рендер =================
    def _ensure_prerender(self):
        if getattr(self.world, "_prerender", None) is None:
            self._prerender_map()

    def _prerender_map(self):
        surf = pg.Surface((self.map_w_px, self.map_h_px))
        surf.fill((15, 15, 25))
        tiles = self._world_tile_frames()
        seed = self.world.seed
        for (gx, gy), seg in self.world.segments.items():
            variants, _color = tiles[seg.biome]
            variant = ((gx * 73856093) ^ (gy * 19349663) ^ seed) & 0x7FFFFFFF
            surf.blit(
                variants[variant % len(variants)],
                (gx * SEG_SIZE, gy * SEG_SIZE),
            )

        self._draw_forest_trees(surf)
        self._draw_biome_borders(surf, tiles)
        self._draw_terrain_features(surf)
        self.world._prerender = surf

    def _world_tile_frames(self):
        """Уменьшенные тайлы биомов для глобальной карты (кэш на мире)."""
        cache = getattr(self.world, "_tile_frames_cache", None)
        if cache is not None:
            return cache
        cache = {}
        for biome, tile_name in BIOME_TILE.items():
            frames = [
                assets.scaled(frame, SEG_SIZE, SEG_SIZE)
                for frame in assets.tile_frames(tile_name)
            ]
            if not frames:
                fallback = pg.Surface((SEG_SIZE, SEG_SIZE))
                fallback.fill(biome.color)
                frames = [fallback]
            if biome == Biome.FOREST:
                frames = [
                    self._tint_frame(f, FOREST_TINT, FOREST_TINT_ALPHA)
                    for f in frames
                ]
                color = self._surface_color(frames[0])
            else:
                color = assets.tile_color(tile_name, biome.color)
            cache[biome] = (tuple(frames), color)
        self.world._tile_frames_cache = cache
        return cache

    @staticmethod
    def _tint_frame(frame, color, alpha):
        tinted = frame.copy()
        overlay = pg.Surface(frame.get_size(), pg.SRCALPHA)
        overlay.fill((*color, alpha))
        tinted.blit(overlay, (0, 0))
        return tinted

    @staticmethod
    def _surface_color(surface):
        w, h = surface.get_size()
        r = g = b = 0
        for y in range(h):
            for x in range(w):
                c = surface.get_at((x, y))
                r += c.r
                g += c.g
                b += c.b
        n = max(1, w * h)
        return (r // n, g // n, b // n)

    def _forest_tree_sprites(self):
        """Вырезанные из тайла деревья с прозрачным фоном (кэш на мире)."""
        cache = getattr(self.world, "_forest_tree_cache", None)
        if cache is not None:
            return cache
        cache = []
        tree_frames = assets.tile_frames("tree")
        grass_frames = assets.tile_frames("grass")
        for index, frame in enumerate(tree_frames):
            base = grass_frames[index % len(grass_frames)] if grass_frames else None
            if base is None or base.get_size() != frame.get_size():
                continue
            sprite = pg.Surface(frame.get_size(), pg.SRCALPHA)
            for y in range(frame.get_height()):
                for x in range(frame.get_width()):
                    color = frame.get_at((x, y))
                    ref = base.get_at((x, y))
                    diff = (
                        abs(color.r - ref.r)
                        + abs(color.g - ref.g)
                        + abs(color.b - ref.b)
                    )
                    if diff > 14:
                        sprite.set_at((x, y), (color.r, color.g, color.b, 255))
            if sprite.get_bounding_rect().width == 0:
                continue
            variants = tuple(
                assets.scaled(sprite, size) for size in FOREST_TREE_SIZES
            )
            cache.append((sprite, variants))
        self.world._forest_tree_cache = cache
        return cache

    def _draw_forest_trees(self, surface):
        trees = self._forest_tree_sprites()
        if not trees:
            return
        cells = [
            (gx, gy)
            for (gx, gy), seg in self.world.segments.items()
            if seg.biome == Biome.FOREST
        ]
        # Сначала северные клетки, затем южные — кроны перекрываются естественно.
        cells.sort(key=lambda cell: (cell[1], cell[0]))
        for gx, gy in cells:
            roll = _hash01(gx, gy, 7)
            if roll < 0.10:
                continue
            if roll < 0.62:
                count = 1
            elif roll < 0.88:
                count = 2
            else:
                count = 3
            cx = gx * SEG_SIZE + SEG_SIZE // 2
            cy = gy * SEG_SIZE + SEG_SIZE // 2
            for i in range(count):
                salt = 11 + i * 17
                spr_index = int(_hash01(gx, gy, salt) * len(trees)) % len(trees)
                _sprite, variants = trees[spr_index]
                variant = int(_hash01(gx, gy, salt + 5) * len(variants)) % len(variants)
                tree = variants[variant]
                tw, th = tree.get_size()
                ox = int((_hash01(gx, gy, salt + 9) - 0.5) * 12)
                oy = int((_hash01(gx, gy, salt + 13) - 0.5) * 12)
                surface.blit(tree, (cx + ox - tw // 2, cy + oy - th // 2))

    def _draw_biome_borders(self, surface, tiles):
        """Переходы между биомами, включая непроходимые океан и горы."""
        for (gx, gy), seg in self.world.segments.items():
            _frames, seg_color = tiles[seg.biome]
            for direction, (dx, dy) in (
                ("N", (0, -1)),
                ("S", (0, 1)),
                ("W", (-1, 0)),
                ("E", (1, 0)),
            ):
                nbr = self.world.segments.get((gx + dx, gy + dy))
                if nbr is None or nbr.biome == seg.biome:
                    continue
                _nbr_frames, nbr_color = tiles[nbr.biome]
                seg_walk = seg.biome.walkable
                nbr_walk = nbr.biome.walkable
                if seg_walk and not nbr_walk:
                    # Плавный берег/предгорье на проходимой стороне.
                    self._draw_edge_dither(
                        surface,
                        gx,
                        gy,
                        direction,
                        seg_color,
                        nbr_color,
                        max_thickness=6,
                    )
                elif not seg_walk and nbr_walk:
                    # Мягкая кромка на непроходимой стороне.
                    fringe = _mix(seg_color, nbr_color, 0.35)
                    self._draw_edge_dither(
                        surface,
                        gx,
                        gy,
                        direction,
                        seg_color,
                        fringe,
                        max_thickness=3,
                    )
                else:
                    self._draw_edge_dither(
                        surface,
                        gx,
                        gy,
                        direction,
                        seg_color,
                        nbr_color,
                        max_thickness=5,
                    )

    def _draw_terrain_features(self, surface):
        """Реки, озёра, броды/мосты и дороги поверх биомов."""
        self._draw_lakes(surface)
        self._draw_rivers(surface)
        self._draw_roads(surface)
        self._draw_crossings(surface)

    def _draw_roads(self, surface):
        roads = self.world.roads
        if not roads:
            return
        half = SEG_SIZE // 2
        color = (178, 156, 112)
        edge = (128, 108, 76)
        edges = set()
        for gx, gy in roads:
            a = (gx * SEG_SIZE + half, gy * SEG_SIZE + half)
            for dx, dy in ((1, 0), (0, 1)):
                nb = (gx + dx, gy + dy)
                if nb not in roads:
                    continue
                b = (nb[0] * SEG_SIZE + half, nb[1] * SEG_SIZE + half)
                edges.add((a, b))
        for a, b in edges:
            pg.draw.line(surface, edge, a, b, 5)
        for a, b in edges:
            pg.draw.line(surface, color, a, b, 3)
        for gx, gy in roads:
            pg.draw.circle(
                surface,
                color,
                (gx * SEG_SIZE + half, gy * SEG_SIZE + half),
                2,
            )

    def _crossing_is_vertical(self, gx, gy):
        """Мост поперёк реки: вертикальный, если река течёт горизонтально."""
        rivers = self.world.rivers
        horizontal = (gx - 1, gy) in rivers or (gx + 1, gy) in rivers
        vertical = (gx, gy - 1) in rivers or (gx, gy + 1) in rivers
        if horizontal and not vertical:
            return True
        return False

    def _draw_crossings(self, surface):
        for gx, gy in self.world.crossings:
            seg = self.world.get(gx, gy)
            if seg is None:
                continue
            sx, sy = gx * SEG_SIZE, gy * SEG_SIZE
            half = SEG_SIZE // 2
            color = (150, 110, 62) if seg.bridge else (206, 196, 150)
            if self._crossing_is_vertical(gx, gy):
                rect = pg.Rect(sx + half - 2, sy + 1, 4, SEG_SIZE - 2)
            else:
                rect = pg.Rect(sx + 1, sy + half - 2, SEG_SIZE - 2, 4)
            pg.draw.rect(
                surface,
                (84, 70, 46) if seg.bridge else (150, 140, 104),
                rect.inflate(2, 2),
            )
            pg.draw.rect(surface, color, rect)

    def _draw_lakes(self, surface):
        """Озёра рисуются слитными округлыми водоёмами, а не квадратами."""
        lakes = self.world.lakes
        if not lakes:
            return
        half = SEG_SIZE // 2
        shore = (36, 82, 142)
        water = (54, 116, 194)
        wave = (104, 168, 226)

        # Береговая кромка.
        for gx, gy in lakes:
            pg.draw.circle(
                surface, shore, (gx * SEG_SIZE + half, gy * SEG_SIZE + half), 10
            )
        for gx, gy in lakes:
            cx, cy = gx * SEG_SIZE + half, gy * SEG_SIZE + half
            for dx, dy in (
                (1, 0), (-1, 0), (0, 1), (0, -1),
                (1, 1), (1, -1), (-1, 1), (-1, -1),
            ):
                if (gx + dx, gy + dy) in lakes:
                    pg.draw.line(
                        surface,
                        shore,
                        (cx, cy),
                        ((gx + dx) * SEG_SIZE + half, (gy + dy) * SEG_SIZE + half),
                        12,
                    )

        # Вода.
        for gx, gy in lakes:
            pg.draw.circle(
                surface, water, (gx * SEG_SIZE + half, gy * SEG_SIZE + half), 8
            )
        for gx, gy in lakes:
            cx, cy = gx * SEG_SIZE + half, gy * SEG_SIZE + half
            for dx, dy in (
                (1, 0), (-1, 0), (0, 1), (0, -1),
                (1, 1), (1, -1), (-1, 1), (-1, -1),
            ):
                if (gx + dx, gy + dy) in lakes:
                    pg.draw.line(
                        surface,
                        water,
                        (cx, cy),
                        ((gx + dx) * SEG_SIZE + half, (gy + dy) * SEG_SIZE + half),
                        10,
                    )

        # Редкие блики.
        for gx, gy in lakes:
            h = ((gx * 73856093) ^ (gy * 19349663)) & 0x7FFFFFFF
            if h % 3:
                continue
            cx = gx * SEG_SIZE + half - 5 + h % 4
            cy = gy * SEG_SIZE + half - 2 + (h >> 7) % 5
            pg.draw.line(surface, wave, (cx, cy), (cx + 5, cy), 1)

    def _draw_rivers(self, surface):
        """Реки рисуются связными руслами по центрам соседних клеток."""
        rivers = self.world.rivers
        if not rivers:
            return
        half = SEG_SIZE // 2
        outline = (34, 78, 148)
        water = (62, 132, 208)
        highlight = (116, 186, 238)

        edges = set()
        for gx, gy in rivers:
            for dx, dy in (
                (1, 0), (0, 1), (1, 1), (1, -1),
            ):
                nb = (gx + dx, gy + dy)
                if nb not in rivers:
                    continue
                if dx and dy:
                    # Внутри блока 2x2 диагональ не нужна — она даёт «крестик».
                    if dy == 1:
                        if (gx + 1, gy) in rivers and (gx, gy + 1) in rivers:
                            continue
                    else:
                        if (gx + 1, gy) in rivers and (gx, gy - 1) in rivers:
                            continue
                a = (gx * SEG_SIZE + half, gy * SEG_SIZE + half)
                b = (nb[0] * SEG_SIZE + half, nb[1] * SEG_SIZE + half)
                if a > b:
                    a, b = b, a
                edges.add((a, b))

        # Заполняем центры блоков 2x2, иначе русло рисуется полым квадратом.
        blocks = set()
        for gx, gy in rivers:
            if (
                (gx + 1, gy) in rivers
                and (gx, gy + 1) in rivers
                and (gx + 1, gy + 1) in rivers
            ):
                blocks.add((gx, gy))

        # Тёмная кромка и русло с округлыми стыками.
        for a, b in edges:
            pg.draw.line(surface, outline, a, b, 6)
        for gx, gy in rivers:
            pg.draw.circle(
                surface, outline, (gx * SEG_SIZE + half, gy * SEG_SIZE + half), 3
            )
        for gx, gy in blocks:
            rect = pg.Rect(
                gx * SEG_SIZE + half, gy * SEG_SIZE + half, SEG_SIZE, SEG_SIZE
            )
            pg.draw.rect(surface, outline, rect.inflate(6, 6))
        for a, b in edges:
            pg.draw.line(surface, water, a, b, 3)
        for gx, gy in rivers:
            pg.draw.circle(
                surface, water, (gx * SEG_SIZE + half, gy * SEG_SIZE + half), 2
            )
        for gx, gy in blocks:
            rect = pg.Rect(
                gx * SEG_SIZE + half, gy * SEG_SIZE + half, SEG_SIZE, SEG_SIZE
            )
            pg.draw.rect(surface, water, rect)

        # Прерывистый блик по течению.
        for a, b in edges:
            h = (a[0] * 73856093) ^ (a[1] * 19349663) ^ (b[0] * 83492791)
            if h % 3:
                continue
            pg.draw.line(surface, highlight, a, b, 1)

    def _draw_edge_dither(
        self, surface, gx, gy, direction, base, nbr_color, max_thickness=5
    ):
        sx, sy = gx * SEG_SIZE, gy * SEG_SIZE
        blend = _mix(base, nbr_color, 0.5)
        n_strips = SEG_SIZE // 2
        for i in range(n_strips):
            n = _edge_noise(gx, gy, direction, i)
            if n < 0.30:
                continue
            thickness = int(1 + (n - 0.30) / 0.70 * max_thickness)
            color = blend if n < 0.60 else nbr_color
            if direction == "N":
                pg.draw.rect(surface, color, (sx + i * 2, sy, 2, thickness))
            elif direction == "S":
                pg.draw.rect(
                    surface,
                    color,
                    (sx + i * 2, sy + SEG_SIZE - thickness, 2, thickness),
                )
            elif direction == "W":
                pg.draw.rect(surface, color, (sx, sy + i * 2, thickness, 2))
            elif direction == "E":
                pg.draw.rect(
                    surface,
                    color,
                    (sx + SEG_SIZE - thickness, sy + i * 2, thickness, 2),
                )

    # ================= Туман =================
    def _segment_visibility(self, gx, gy) -> float:
        seg = self.world.get(gx, gy)
        if seg is None:
            return 0.0
        dx, dy = gx - self.gx, gy - self.gy
        d2 = dx * dx + dy * dy
        if d2 <= VISION_NEAR_SQ:
            return 1.0
        if d2 >= VISION_FAR_SQ:
            return MEMORY_VISIBILITY if seg.explored else 0.0
        d = math.sqrt(d2)
        t = (d - VISION_NEAR) / (VISION_FAR - VISION_NEAR)
        t = t * t * (3.0 - 2.0 * t)
        current = 1.0 - t
        if seg.explored:
            return MEMORY_VISIBILITY + current * (1.0 - MEMORY_VISIBILITY)
        return current

    def _reveal_around_player(self):
        r = VISION_FAR
        r2 = VISION_FAR_SQ
        new_reveal = False
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy > r2:
                    continue
                seg = self.world.get(self.gx + dx, self.gy + dy)
                if seg is not None and not seg.explored:
                    seg.explored = True
                    new_reveal = True
        if new_reveal:
            self._minimap_dirty = True

    # ================= Жизненный цикл =================
    def on_enter(self, world_pos=None, mode=None):
        if mode is not None:
            self.mode = mode
        if world_pos is not None:
            self.gx, self.gy = world_pos
        elif self.mode == "spawn":
            self.gx = self.world.start_gx
            self.gy = self.world.start_gy
        # В play-режиме позиция уже задана в __init__ или приходит из world_pos.
        self.move_cooldown = 0.0
        self._center_camera()
        if self.mode == "play":
            self._reveal_around_player()

    def _center_camera(self):
        cx = self.gx * SEG_SIZE + SEG_SIZE / 2
        cy = self.gy * SEG_SIZE + SEG_SIZE / 2
        self.camera.x = max(
            0, min(cx - self.camera.view_w / 2, self.map_w_px - self.camera.view_w)
        )
        self.camera.y = max(
            0, min(cy - self.camera.view_h / 2, self.map_h_px - self.camera.view_h)
        )

    # ================= Ввод =================
    def handle_event(self, event):
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_F5:
                from core.save_load import save_game

                if save_game(self.world, self.state, slot="manual"):
                    self._flash("Игра сохранена")
                else:
                    self._flash("Ошибка сохранения")
                return
            if event.key == pg.K_i:
                self.manager.push_ui(InventoryUI(screen.get_size(), self.state))
                return
            if event.key == pg.K_c:
                self.manager.push_ui(CharacterUI(screen.get_size(), self.state))
                return
            if event.key == pg.K_k:
                self.manager.push_ui(SkillsUI(screen.get_size(), self.state))
                return
            if event.key == pg.K_j:
                self.manager.push_ui(QuestLogUI(screen.get_size(), self.state))
                return

        if self.mode == "spawn":
            self._handle_spawn_input(event)
        else:
            self._handle_play_input(event)

    def _handle_spawn_input(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            self._try_pick_segment(event.pos)
        elif event.type == pg.KEYDOWN and event.key == pg.K_RETURN:
            self._try_pick_segment(pg.mouse.get_pos())

    def _handle_play_input(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 3:
            self._handle_waypoint_click(event.pos)
            return
        if event.type != pg.KEYDOWN:
            return
        if event.key == pg.K_r:
            self._rest_here()
            return
        if event.key == pg.K_t:
            self._open_fast_travel()
            return
        dx = dy = 0
        if event.key in (pg.K_w, pg.K_UP):
            dy = -1
        if event.key in (pg.K_s, pg.K_DOWN):
            dy = 1
        if event.key in (pg.K_a, pg.K_LEFT):
            dx = -1
        if event.key in (pg.K_d, pg.K_RIGHT):
            dx = 1
        if dx or dy:
            self._try_step(dx, dy)
            self.move_cooldown = MOVE_REPEAT_DELAY
        if event.key == pg.K_RETURN:
            seg = self.world.get(self.gx, self.gy)
            if seg and self.world.is_passable(self.gx, self.gy):
                from scenes.local_scene import LocalScene

                self.manager.switch(
                    LocalScene(self.manager, seg), return_pos=(self.gx, self.gy)
                )

    def _rest_here(self):
        seg = self.world.get(self.gx, self.gy)
        if seg is None or not seg.location_type.is_settlement:
            self._flash("Отдых возможен только в деревне")
            return
        if seg.village_state == "destroyed":
            self._flash("В разрушенной деревне негде отдохнуть")
            return
        self.state.rest(full=True)
        self.state.remember_village(self.gx, self.gy)
        self._flash("Отдых в деревне: силы, HP и мана восстановлены")

    def _open_fast_travel(self):
        if not self.state.visited_villages:
            self._flash("Сначала посетите хотя бы одну деревню")
            return
        from ui.fast_travel_ui import FastTravelUI

        self.manager.push_ui(FastTravelUI(screen.get_size(), self.state, self))

    def fast_travel_to(self, gx, gy):
        if (gx, gy) not in self.state.visited_villages:
            self._flash("Эта деревня ещё не открыта")
            return
        poi = self.world.poi_at(gx, gy)
        if poi is not None and poi.destroyed:
            self._flash("Деревня разрушена — путь туда закрыт")
            return
        if (gx, gy) == (self.gx, self.gy):
            self._flash("Вы уже здесь")
            return
        dist = math.hypot(gx - self.gx, gy - self.gy)
        cost = max(10, int(dist * 1.5))
        if self.state.gold < cost:
            self._flash(f"Нужно {cost} золота для быстрого пути")
            return
        self.state.gold -= cost
        self.gx, self.gy = gx, gy
        self._reveal_around_player()
        self._center_camera()
        self._flash(f"Быстрое перемещение: -{cost} золота")

    def _flash(self, text, duration=2.5):
        self.message = text
        self.message_timer = duration

    def _handle_waypoint_click(self, screen_pos):
        gx, gy = self._screen_to_segment_any(screen_pos)
        if gx is None:
            return
        if self.state.waypoint == (gx, gy):
            self.state.waypoint = None
        else:
            self.state.waypoint = (gx, gy)

    def _screen_to_segment_any(self, screen_pos):
        sx, sy = screen_pos
        gx = int((sx + self.camera.x) // SEG_SIZE)
        gy = int((sy + self.camera.y) // SEG_SIZE)
        if not (0 <= gx < self.world.width and 0 <= gy < self.world.height):
            return None, None
        return gx, gy

    def _try_step(self, dx, dy):
        if not self._can_move(dx, dy):
            return False
        cost = self._move_cost(dx, dy)
        if not self.state.spend(cost):
            return False
        self.gx += dx
        self.gy += dy
        self._reveal_around_player()
        self._center_camera()
        return True

    def _held_direction(self):
        keys = list(pg.key.get_pressed())
        dx = dy = 0
        if keys[pg.KSCAN_W] or keys[pg.KSCAN_UP]:
            dy -= 1
        if keys[pg.KSCAN_S] or keys[pg.KSCAN_DOWN]:
            dy += 1
        if keys[pg.KSCAN_A] or keys[pg.KSCAN_LEFT]:
            dx -= 1
        if keys[pg.KSCAN_D] or keys[pg.KSCAN_RIGHT]:
            dx += 1
        return dx, dy

    def _update_held_move(self, dt):
        """Повторяет шаг, пока клавиша движения удерживается."""
        if self.move_cooldown > 0:
            self.move_cooldown = max(0.0, self.move_cooldown - dt)
        if self.move_cooldown > 0:
            return
        dx, dy = self._held_direction()
        if dx or dy:
            self._try_step(dx, dy)
            self.move_cooldown = MOVE_REPEAT_DELAY

    def _try_pick_segment(self, screen_pos):
        gx, gy = self._screen_to_segment(screen_pos)
        if gx is None:
            return
        self.gx, self.gy = gx, gy
        self.state.restore()
        self.mode = "play"
        self._reveal_around_player()
        self._center_camera()

    def _screen_to_segment(self, screen_pos):
        sx, sy = screen_pos
        gx = int((sx + self.camera.x) // SEG_SIZE)
        gy = int((sy + self.camera.y) // SEG_SIZE)
        if not self.world.is_passable(gx, gy):
            return None, None
        return gx, gy

    def _can_move(self, dx, dy):
        return self.world.is_passable(self.gx + dx, self.gy + dy)

    def _move_cost(self, dx, dy):
        seg = self.world.get(self.gx + dx, self.gy + dy)
        if seg is None:
            return 999
        if seg.road:
            return 1
        if seg.river:
            return 2
        return (
            BIOME_MOVE_COST.get(seg.biome, DEFAULT_MOVE_COST)
            + self.state.travel_penalty
        )

    # ================= Update =================
    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt
        if self.mode == "play":
            self._update_held_move(dt)
            self._reveal_around_player()
            # Камера жёстко привязана к персонажу каждый кадр.
            self._center_camera()
            return

        keys = list(pg.key.get_pressed())
        pan_x = pan_y = 0
        if keys[pg.KSCAN_W] or keys[pg.KSCAN_UP]:
            pan_y -= 1
        if keys[pg.KSCAN_S] or keys[pg.KSCAN_DOWN]:
            pan_y += 1
        if keys[pg.KSCAN_A] or keys[pg.KSCAN_LEFT]:
            pan_x -= 1
        if keys[pg.KSCAN_D] or keys[pg.KSCAN_RIGHT]:
            pan_x += 1

        if pan_x or pan_y:
            self.camera.x = max(
                0,
                min(
                    self.camera.x + pan_x * CAM_PAN_SPEED * dt,
                    self.map_w_px - self.camera.view_w,
                ),
            )
            self.camera.y = max(
                0,
                min(
                    self.camera.y + pan_y * CAM_PAN_SPEED * dt,
                    self.map_h_px - self.camera.view_h,
                ),
            )

        gx, gy = self._screen_to_segment(pg.mouse.get_pos())
        self.hover_seg = (gx, gy) if gx is not None else None
        self.hover_valid = gx is not None

    # ================= Draw =================
    def draw(self, screen):
        screen.fill((15, 15, 25))
        cam_x, cam_y = int(self.camera.x), int(self.camera.y)

        screen.blit(
            self.world._prerender,
            (0, 0),
            (cam_x, cam_y, self.camera.view_w, self.camera.view_h),
        )

        self._draw_pois(screen, cam_x, cam_y)
        self._draw_fog(screen, cam_x, cam_y)

        # Маркеры — над туманом (мета-информация)
        if self.mode == "play":
            self._draw_quest_targets(screen, cam_x, cam_y)
            self._draw_waypoint(screen, cam_x, cam_y)

        if self.mode == "spawn":
            self._draw_hover(screen, cam_x, cam_y)
        else:
            self._draw_player(screen, cam_x, cam_y)

        self._draw_hud(screen)
        self._draw_minimap(screen)
        self._draw_hint(screen)
        self._draw_message(screen)

    def _draw_pois(self, screen, cam_x, cam_y):
        t = pg.time.get_ticks() / 1000.0
        for poi in self.world.pois:
            if not self._is_poi_visible(poi):
                continue
            sx = poi.gx * SEG_SIZE - cam_x
            sy = poi.gy * SEG_SIZE - cam_y
            if (
                sx < -SEG_SIZE
                or sy < -SEG_SIZE
                or sx > self.camera.view_w
                or sy > self.camera.view_h
            ):
                continue
            center = (sx + SEG_SIZE // 2, sy + SEG_SIZE // 2)
            if poi.destroyed:
                color = (150, 70, 70)
            else:
                color = (120, 120, 120) if poi.cleared else poi.icon_color
            pulse = 1.0 + 0.18 * math.sin(t * 2.6 + poi.gx * 0.7)
            pg.draw.circle(screen, color, center, int(10 * pulse), 1)
            icon = assets.world_icon(POI_ICONS.get(poi.poi_type.value, "wild"))
            if icon is not None:
                size = 20 if poi.poi_type.value != "wild_point" else 15
                icon = assets.scaled(icon, size, size)
                if poi.destroyed:
                    icon = icon.copy()
                    icon.fill(
                        (150, 80, 80, 255), special_flags=pg.BLEND_RGBA_MULT
                    )
                screen.blit(icon, icon.get_rect(center=center))
                if poi.cleared and not poi.destroyed:
                    check = assets.world_icon("cleared")
                    if check is not None:
                        check = assets.scaled(check, 9, 9)
                        screen.blit(check, (center[0] + 5, center[1] + 5))
                if poi.destroyed:
                    pg.draw.line(
                        screen,
                        (240, 80, 80),
                        (center[0] - 6, center[1] - 6),
                        (center[0] + 6, center[1] + 6),
                        2,
                    )
                    pg.draw.line(
                        screen,
                        (240, 80, 80),
                        (center[0] + 6, center[1] - 6),
                        (center[0] - 6, center[1] + 6),
                        2,
                    )
            else:
                pg.draw.circle(screen, color, center, 6)
                pg.draw.circle(screen, (20, 20, 20), center, 6, 1)

    def _is_poi_visible(self, poi):
        if self.mode == "spawn":
            return True
        seg = self.world.get(poi.gx, poi.gy)
        return seg is not None and seg.explored

    def _draw_fog(self, screen, cam_x, cam_y):
        if self.mode == "spawn":
            return
        vw, vh = self.camera.view_w, self.camera.view_h
        if self._fog_surface is None or self._fog_surface.get_size() != (vw, vh):
            self._fog_surface = pg.Surface((vw, vh), pg.SRCALPHA)
        self._fog_surface.fill((0, 0, 0, 0))

        tx0 = max(0, int(self.camera.x // SEG_SIZE) - 1)
        ty0 = max(0, int(self.camera.y // SEG_SIZE) - 1)
        tx1 = min(self.world.width, int((self.camera.x + vw) // SEG_SIZE) + 2)
        ty1 = min(self.world.height, int((self.camera.y + vh) // SEG_SIZE) + 2)

        for gy in range(ty0, ty1):
            for gx in range(tx0, tx1):
                vis = self._segment_visibility(gx, gy)
                if vis >= 0.999:
                    continue
                alpha = int((1.0 - vis) * 255)
                if alpha <= 0:
                    continue
                sx = gx * SEG_SIZE - cam_x
                sy = gy * SEG_SIZE - cam_y
                self._fog_surface.fill((0, 0, 0, alpha), (sx, sy, SEG_SIZE, SEG_SIZE))
        screen.blit(self._fog_surface, (0, 0))

    def _draw_quest_targets(self, screen, cam_x, cam_y):
        t = pg.time.get_ticks() / 1000.0
        pulse = 1.0 + 0.3 * math.sin(t * 4)
        for q in self.state.quest_log.active():
            if q.target_gx is None or q.target_gy is None:
                continue
            sx = q.target_gx * SEG_SIZE - cam_x + SEG_SIZE // 2
            sy = q.target_gy * SEG_SIZE - cam_y + SEG_SIZE // 2
            if not (
                -30 < sx < self.camera.view_w + 30
                and -30 < sy < self.camera.view_h + 30
            ):
                continue
            r = int(9 * pulse)
            pg.draw.circle(screen, (255, 200, 100), (sx, sy), r, 2)
            icon = assets.world_icon("quest")
            if icon is not None:
                icon = assets.scaled(icon, 16, 16)
                screen.blit(icon, icon.get_rect(center=(sx, sy)))
            else:
                pg.draw.circle(screen, (255, 200, 100), (sx, sy), 3)

    def _draw_waypoint(self, screen, cam_x, cam_y):
        if self.state.waypoint is None:
            return
        gx, gy = self.state.waypoint
        sx = gx * SEG_SIZE - cam_x + SEG_SIZE // 2
        sy = gy * SEG_SIZE - cam_y + SEG_SIZE // 2
        if not (
            -30 < sx < self.camera.view_w + 30 and -30 < sy < self.camera.view_h + 30
        ):
            return
        icon = assets.world_icon("waypoint")
        if icon is not None:
            bob = int(math.sin(pg.time.get_ticks() / 280.0) * 2)
            icon = assets.scaled(icon, 20, 20)
            screen.blit(icon, icon.get_rect(center=(sx, sy - 8 + bob)))
            pg.draw.circle(screen, (255, 230, 80), (sx, sy), 4, 1)
            return
        # Флажок
        pg.draw.line(screen, (230, 230, 200), (sx, sy - 4), (sx, sy - 16), 2)
        pg.draw.polygon(
            screen, (255, 230, 80), [(sx, sy - 16), (sx + 12, sy - 12), (sx, sy - 8)]
        )
        pg.draw.circle(screen, (255, 230, 80), (sx, sy), 4)
        pg.draw.circle(screen, (30, 30, 30), (sx, sy), 4, 1)

    def _draw_hover(self, screen, cam_x, cam_y):
        if self.hover_seg is None:
            return
        hx, hy = self.hover_seg
        sx = hx * SEG_SIZE - cam_x
        sy = hy * SEG_SIZE - cam_y
        color = (255, 255, 255) if self.hover_valid else (200, 60, 60)
        pg.draw.rect(screen, color, (sx, sy, SEG_SIZE, SEG_SIZE), 2)
        if self.hover_valid:
            poi = self.world.poi_at(hx, hy)
            if poi:
                surf = self._font_small.render(poi.name, True, (255, 255, 200))
                screen.blit(surf, (sx, sy - 18))

    def _draw_player(self, screen, cam_x, cam_y):
        px = self.gx * SEG_SIZE - cam_x
        py = self.gy * SEG_SIZE - cam_y
        color = self.state.class_def.color if self.state.stamina > 0 else (100, 60, 60)
        t = pg.time.get_ticks() / 1000.0
        cx = px + SEG_SIZE // 2
        cy = py + SEG_SIZE // 2
        ring = int(11 + 2 * math.sin(t * 3.0))
        pg.draw.circle(screen, color, (cx, cy), ring, 1)
        icon = assets.world_icon("player")
        if icon is not None:
            icon = assets.scaled(icon, 24, 24)
            icon = icon.copy()
            icon.fill((*color, 255), special_flags=pg.BLEND_RGBA_MULT)
            screen.blit(icon, icon.get_rect(center=(cx, cy)))
            pg.draw.circle(screen, (255, 255, 255), (cx, cy), 2)
        else:
            pg.draw.rect(screen, color, (px, py, SEG_SIZE, SEG_SIZE))
            pg.draw.rect(screen, (255, 255, 255), (px, py, SEG_SIZE, SEG_SIZE), 1)

    def _draw_hud(self, screen):
        s = self.state
        bar_w, bar_h = 220, 18
        x, y = 12, 12
        assets.draw_bar(screen, (x, y, bar_w, bar_h), s.hp_ratio, "bar_hp")
        t = self._font_small.render(f"HP {s.hp}/{s.max_hp}", True, (255, 255, 255))
        screen.blit(t, (x + bar_w + 8, y + 2))
        y += bar_h + 4
        assets.draw_bar(screen, (x, y, bar_w, bar_h - 4), s.stamina_ratio, "bar_stamina")
        t = self._font_small.render(
            f"Силы {s.stamina}/{s.max_stamina}", True, (255, 255, 255)
        )
        screen.blit(t, (x + bar_w + 8, y))
        y += bar_h
        xp_r = s.xp / s.xp_to_next if s.xp_to_next else 0
        assets.draw_bar(screen, (x, y, bar_w, bar_h - 4), xp_r, "bar_xp")
        t = self._font_small.render(
            f"Ур. {s.level}  {s.xp}/{s.xp_to_next}", True, (255, 255, 255)
        )
        screen.blit(t, (x + bar_w + 8, y))
        y += bar_h
        gold_icon = assets.named_icon("gold")
        if gold_icon is not None:
            gold_icon = assets.scaled(gold_icon, 18, 18)
            screen.blit(gold_icon, (x, y - 1))
            t = self._font_small.render(f"Золото: {s.gold}", True, (240, 220, 100))
            screen.blit(t, (x + 22, y))
        else:
            t = self._font_small.render(f"Золото: {s.gold}", True, (240, 220, 100))
            screen.blit(t, (x, y))
        y += 20

        # === Навигация ===
        if self.mode == "play":
            if s.waypoint is not None:
                wgx, wgy = s.waypoint
                dx, dy = wgx - self.gx, wgy - self.gy
                dist = math.hypot(dx, dy)
                if dist == 0:
                    text = "★ Вы на метке  (ПКМ — снять)"
                else:
                    text = f"★ Метка: {direction_name(dx, dy)} ({int(dist)} сегм.)"
                surf = self._font_small.render(text, True, (255, 230, 80))
                screen.blit(surf, (x, y))
                y += 18

            active_with_target = [
                q for q in s.quest_log.active() if q.target_gx is not None
            ]
            if active_with_target:
                nearest = min(
                    active_with_target,
                    key=lambda q: (
                        (q.target_gx - self.gx) ** 2 + (q.target_gy - self.gy) ** 2
                    ),
                )
                dx = nearest.target_gx - self.gx
                dy = nearest.target_gy - self.gy
                dist = math.hypot(dx, dy)
                title = (
                    nearest.title
                    if len(nearest.title) <= 22
                    else (nearest.title[:21] + "…")
                )
                if dist == 0:
                    text = f"⚑ {title}: здесь"
                else:
                    text = f"⚑ {title}: {direction_name(dx, dy)} ({int(dist)})"
                surf = self._font_small.render(text, True, (255, 200, 100))
                screen.blit(surf, (x, y))
                y += 18

            remaining = len(s.quest_log.active()) - len(active_with_target)
            if remaining > 0:
                surf = self._font_small.render(
                    f"Ещё квестов: {remaining}  [J]", True, (180, 180, 180)
                )
                screen.blit(surf, (x, y))

    def _bar(self, screen, x, y, w, h, ratio, color):
        pg.draw.rect(screen, (30, 30, 30), (x, y, w, h))
        fill = int((w - 4) * max(0.0, min(1.0, ratio)))
        if fill > 0:
            pg.draw.rect(screen, color, (x + 2, y + 2, fill, h - 4))
        pg.draw.rect(screen, (200, 200, 200), (x, y, w, h), 1)

    def _draw_minimap(self, screen):
        show_full = self.mode == "spawn"
        if (
            self._minimap_surf is None
            or self._minimap_dirty
            or self._minimap_full != show_full
        ):
            base = pg.Surface((self.world.width, self.world.height))
            base.fill((10, 10, 15))
            for gy in range(self.world.height):
                for gx in range(self.world.width):
                    seg = self.world.get(gx, gy)
                    if seg is None:
                        continue
                    if show_full or seg.explored:
                        if (gx, gy) in self.world.lakes:
                            color = (46, 100, 180)
                        elif (gx, gy) in self.world.rivers:
                            color = (64, 136, 210)
                        elif (gx, gy) in self.world.roads:
                            color = (188, 166, 120)
                        else:
                            color = seg.biome.color
                        base.set_at((gx, gy), color)
            self._minimap_surf = base
            self._minimap_dirty = False
            self._minimap_full = show_full

        scaled = pg.transform.scale(self._minimap_surf, (MINIMAP_W, MINIMAP_H))
        mm_x = self.camera.view_w - MINIMAP_W - 10
        mm_y = 10
        screen.blit(scaled, (mm_x, mm_y))
        pg.draw.rect(screen, (150, 150, 170), (mm_x, mm_y, MINIMAP_W, MINIMAP_H), 2)

        def to_mm(gx, gy):
            return (
                mm_x + int(gx * MINIMAP_W / self.world.width),
                mm_y + int(gy * MINIMAP_H / self.world.height),
            )

        # POI
        for poi in self.world.pois:
            if not self._is_poi_visible(poi):
                continue
            px, py = to_mm(poi.gx, poi.gy)
            icon = assets.world_icon(POI_ICONS.get(poi.poi_type.value, "wild"))
            if icon is not None:
                size = 13 if poi.poi_type.value != "wild_point" else 10
                icon = assets.scaled(icon, size, size)
                pg.draw.circle(screen, (20, 20, 20), (px, py), size // 2 + 1)
                if poi.cleared or poi.destroyed:
                    icon = icon.copy()
                    tint = (150, 80, 80, 255) if poi.destroyed else (120, 120, 120, 255)
                    icon.fill(tint, special_flags=pg.BLEND_RGBA_MULT)
                screen.blit(icon, icon.get_rect(center=(px, py)))
            else:
                if poi.destroyed:
                    color = (150, 70, 70)
                else:
                    color = (100, 100, 100) if poi.cleared else poi.icon_color
                pg.draw.circle(screen, color, (px, py), 3)
                pg.draw.circle(screen, (20, 20, 20), (px, py), 3, 1)

        # Квестовые цели (в play-режиме)
        if self.mode == "play":
            for q in self.state.quest_log.active():
                if q.target_gx is None:
                    continue
                px, py = to_mm(q.target_gx, q.target_gy)
                icon = assets.world_icon("quest")
                if icon is not None:
                    icon = assets.scaled(icon, 11, 11)
                    screen.blit(icon, icon.get_rect(center=(px, py)))
                else:
                    pg.draw.circle(screen, (255, 200, 100), (px, py), 3, 1)

            # Метка
            if self.state.waypoint is not None:
                px, py = to_mm(*self.state.waypoint)
                icon = assets.world_icon("waypoint")
                if icon is not None:
                    icon = assets.scaled(icon, 13, 13)
                    screen.blit(icon, icon.get_rect(center=(px, py)))
                else:
                    pg.draw.circle(screen, (255, 230, 80), (px, py), 4)
                    pg.draw.circle(screen, (30, 30, 30), (px, py), 4, 1)

        # Игрок
        px, py = to_mm(self.gx, self.gy)
        icon = assets.world_icon("player")
        if icon is not None:
            pg.draw.circle(screen, (255, 255, 255), (px, py), 7, 1)
            icon = assets.scaled(icon, 13, 13)
            screen.blit(icon, icon.get_rect(center=(px, py)))
        else:
            pg.draw.circle(screen, (255, 60, 60), (px, py), 4)
            pg.draw.circle(screen, (255, 255, 255), (px, py), 4, 1)

    def _draw_message(self, screen):
        if self.message_timer <= 0 or not self.message:
            return
        surf = self._font_hint.render(self.message, True, (255, 235, 150))
        bg = pg.Surface((surf.get_width() + 20, surf.get_height() + 10))
        bg.set_alpha(190)
        bg.fill((0, 0, 0))
        x = (screen.get_width() - bg.get_width()) // 2
        y = 120
        screen.blit(bg, (x, y))
        screen.blit(surf, (x + 10, y + 5))

    def _draw_hint(self, screen):
        if self.mode == "spawn":
            text = "ЛКМ / Enter — выбрать старт | WASD — панорама | I C K J"
        elif self.state.stamina > 0:
            text = "WASD — шаг | R — отдых | T — быстрый путь | ПКМ — метка | Enter — войти"
        else:
            text = "Нет сил — R в деревне | T — быстрый путь | ПКМ — метка"
        surf = self._font_hint.render(text, True, (230, 230, 230))
        bg = pg.Surface((surf.get_width() + 16, surf.get_height() + 8))
        bg.set_alpha(160)
        bg.fill((0, 0, 0))
        x = 10
        y = screen.get_height() - surf.get_height() - 14
        screen.blit(bg, (x, y))
        screen.blit(surf, (x + 8, y + 4))
