import math

import pygame as pg

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
from ui.character_ui import CharacterUI
from ui.inventory_ui import InventoryUI
from ui.quest_log_ui import QuestLogUI
from ui.skills_ui import SkillsUI
from world.biome import Biome

SEG_SIZE = 16
CAM_PAN_SPEED = 600

BIOME_MOVE_COST = {
    Biome.PLAINS: 1,
    Biome.FOREST: 2,
    Biome.DESERT: 3,
    Biome.TUNDRA: 3,
}
DEFAULT_MOVE_COST = 1

MINIMAP_W = 180
MINIMAP_H = 144


def _mix(a, b, t):
    return (
        int(a[0] * (1 - t) + b[0] * t),
        int(a[1] * (1 - t) + b[1] * t),
        int(a[2] * (1 - t) + b[2] * t),
    )


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

        # Кэши
        self._fog_surface = None
        self._minimap_surf = None
        self._minimap_dirty = True
        self._minimap_full = None

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

    # ---------------- Пре-рендер ----------------
    def _ensure_prerender(self):
        if getattr(self.world, "_prerender", None) is None:
            self._prerender_map()

    def _prerender_map(self):
        surf = pg.Surface((self.map_w_px, self.map_h_px))
        surf.fill((15, 15, 25))
        for (gx, gy), seg in self.world.segments.items():
            pg.draw.rect(
                surf,
                seg.biome.color,
                (gx * SEG_SIZE, gy * SEG_SIZE, SEG_SIZE, SEG_SIZE),
            )

        for (gx, gy), seg in self.world.segments.items():
            for direction, (dx, dy) in (
                ("N", (0, -1)),
                ("S", (0, 1)),
                ("W", (-1, 0)),
                ("E", (1, 0)),
            ):
                nbr = self.world.segments.get((gx + dx, gy + dy))
                if nbr is None or nbr.biome == seg.biome:
                    continue
                seg_walk = seg.biome.walkable
                nbr_walk = nbr.biome.walkable
                if seg_walk and not nbr_walk:
                    self._draw_edge_dither(
                        surf,
                        gx,
                        gy,
                        direction,
                        seg.biome.color,
                        nbr.biome.color,
                        max_thickness=6,
                    )
                elif not seg_walk and nbr_walk:
                    continue
                else:
                    self._draw_edge_dither(
                        surf, gx, gy, direction, seg.biome.color, nbr.biome.color
                    )
        self.world._prerender = surf

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

    # ---------------- Туман войны ----------------
    def _segment_visibility(self, gx, gy) -> float:
        """0.0 = чёрный, 1.0 = полностью виден."""
        seg = self.world.get(gx, gy)
        if seg is None:
            return 0.0

        dx = gx - self.gx
        dy = gy - self.gy
        d2 = dx * dx + dy * dy

        if d2 <= VISION_NEAR_SQ:
            return 1.0

        if d2 >= VISION_FAR_SQ:
            return MEMORY_VISIBILITY if seg.explored else 0.0

        d = math.sqrt(d2)
        t = (d - VISION_NEAR) / (VISION_FAR - VISION_NEAR)
        t = t * t * (3.0 - 2.0 * t)  # smoothstep
        current = 1.0 - t

        if seg.explored:
            return MEMORY_VISIBILITY + current * (1.0 - MEMORY_VISIBILITY)
        return current

    def _reveal_around_player(self):
        """Размечает FAR-радиус как explored; при новых — флаг для мини-карты."""
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

    # ---------------- Жизненный цикл ----------------
    def on_enter(self, world_pos=None, mode=None):
        if mode is not None:
            self.mode = mode
        if world_pos is not None:
            self.gx, self.gy = world_pos
        elif self.mode == "spawn":
            self.gx = self.world.start_gx
            self.gy = self.world.start_gy
        else:
            self.gx = self.world.start_gx
            self.gy = self.world.start_gy
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

    # ---------------- Ввод ----------------
    def handle_event(self, event):
        if event.type == pg.KEYDOWN:
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
        if event.type != pg.KEYDOWN:
            return
        dx = dy = 0
        if event.key == pg.K_w:
            dy = -1
        if event.key == pg.K_s:
            dy = 1
        if event.key == pg.K_a:
            dx = -1
        if event.key == pg.K_d:
            dx = 1
        if dx or dy:
            self._try_step(dx, dy)
        if event.key == pg.K_RETURN:
            seg = self.world.get(self.gx, self.gy)
            if seg and seg.biome.walkable:
                from scenes.local_scene import LocalScene

                self.manager.switch(
                    LocalScene(self.manager, seg), return_pos=(self.gx, self.gy)
                )

    def _try_step(self, dx, dy):
        if not self._can_move(dx, dy):
            return
        cost = self._move_cost(dx, dy)
        if not self.state.spend(cost):
            return
        self.gx += dx
        self.gy += dy
        self._reveal_around_player()
        self._center_camera()

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
        seg = self.world.get(gx, gy)
        if seg is None or not seg.biome.walkable:
            return None, None
        return gx, gy

    def _can_move(self, dx, dy):
        seg = self.world.get(self.gx + dx, self.gy + dy)
        return seg is not None and seg.biome.walkable

    def _move_cost(self, dx, dy):
        seg = self.world.get(self.gx + dx, self.gy + dy)
        if seg is None:
            return 999
        return BIOME_MOVE_COST.get(seg.biome, DEFAULT_MOVE_COST)

    # ---------------- Update ----------------
    def update(self, dt):
        if self.mode == "play":
            self._reveal_around_player()
            return

        keys = pg.key.get_pressed()
        pan_x = pan_y = 0
        if keys[pg.K_w]:
            pan_y -= 1
        if keys[pg.K_s]:
            pan_y += 1
        if keys[pg.K_a]:
            pan_x -= 1
        if keys[pg.K_d]:
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

    # ---------------- Draw ----------------
    def draw(self, screen):
        screen.fill((15, 15, 25))
        cam_x, cam_y = int(self.camera.x), int(self.camera.y)

        # 1. Террейн (пре-рендер)
        screen.blit(
            self.world._prerender,
            (0, 0),
            (cam_x, cam_y, self.camera.view_w, self.camera.view_h),
        )

        # 2. POI — до тумана, чтобы он их тоже затемнял
        self._draw_pois(screen, cam_x, cam_y)

        # 3. Туман (градиент поверх террейна и POI)
        self._draw_fog(screen, cam_x, cam_y)

        # 4. Игрок / hover — над туманом
        if self.mode == "spawn":
            self._draw_hover(screen, cam_x, cam_y)
        else:
            self._draw_player(screen, cam_x, cam_y)

        # 5. HUD + мини-карта
        self._draw_hud(screen)
        self._draw_minimap(screen)
        self._draw_hint(screen)

    def _draw_pois(self, screen, cam_x, cam_y):
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
            color = (100, 100, 100) if poi.cleared else poi.icon_color
            center = (sx + SEG_SIZE // 2, sy + SEG_SIZE // 2)
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
                self._fog_surface.fill(
                    (0, 0, 0, alpha),
                    (sx, sy, SEG_SIZE, SEG_SIZE),
                )

        screen.blit(self._fog_surface, (0, 0))

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
        pg.draw.rect(screen, color, (px, py, SEG_SIZE, SEG_SIZE))
        pg.draw.rect(screen, (255, 255, 255), (px, py, SEG_SIZE, SEG_SIZE), 1)

    def _draw_hud(self, screen):
        s = self.state
        bar_w, bar_h = 220, 18
        x, y = 12, 12
        self._bar(screen, x, y, bar_w, bar_h, s.hp_ratio, (220, 60, 60))
        t = self._font_small.render(f"HP {s.hp}/{s.max_hp}", True, (255, 255, 255))
        screen.blit(t, (x + bar_w + 8, y + 2))
        y += bar_h + 4
        color = (220, 200, 60) if s.stamina_ratio > 0.3 else (220, 60, 60)
        self._bar(screen, x, y, bar_w, bar_h - 4, s.stamina_ratio, color)
        t = self._font_small.render(
            f"Силы {s.stamina}/{s.max_stamina}", True, (255, 255, 255)
        )
        screen.blit(t, (x + bar_w + 8, y))
        y += bar_h
        xp_r = s.xp / s.xp_to_next if s.xp_to_next else 0
        self._bar(screen, x, y, bar_w, bar_h - 4, xp_r, (90, 180, 230))
        t = self._font_small.render(
            f"Ур. {s.level}  {s.xp}/{s.xp_to_next}", True, (255, 255, 255)
        )
        screen.blit(t, (x + bar_w + 8, y))
        y += bar_h
        t = self._font_small.render(f"Золото: {s.gold}", True, (240, 220, 100))
        screen.blit(t, (x, y))
        y += 18
        active = len(s.quest_log.active())
        if active:
            t = self._font_small.render(f"Квесты: {active}  [J]", True, (200, 220, 250))
            screen.blit(t, (x, y))

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
                        base.set_at((gx, gy), seg.biome.color)
            self._minimap_surf = base
            self._minimap_dirty = False
            self._minimap_full = show_full

        scaled = pg.transform.scale(self._minimap_surf, (MINIMAP_W, MINIMAP_H))
        mm_x = self.camera.view_w - MINIMAP_W - 10
        mm_y = 10
        screen.blit(scaled, (mm_x, mm_y))
        pg.draw.rect(screen, (150, 150, 170), (mm_x, mm_y, MINIMAP_W, MINIMAP_H), 2)

        # POI
        for poi in self.world.pois:
            if not self._is_poi_visible(poi):
                continue
            px = mm_x + int(poi.gx * MINIMAP_W / self.world.width)
            py = mm_y + int(poi.gy * MINIMAP_H / self.world.height)
            color = (100, 100, 100) if poi.cleared else poi.icon_color
            pg.draw.circle(screen, color, (px, py), 3)
            pg.draw.circle(screen, (20, 20, 20), (px, py), 3, 1)

        # Игрок
        px = mm_x + int(self.gx * MINIMAP_W / self.world.width)
        py = mm_y + int(self.gy * MINIMAP_H / self.world.height)
        pg.draw.circle(screen, (255, 60, 60), (px, py), 4)
        pg.draw.circle(screen, (255, 255, 255), (px, py), 4, 1)

    def _draw_hint(self, screen):
        if self.mode == "spawn":
            text = "ЛКМ / Enter — выбрать старт | WASD — панорама | I C K J"
        elif self.state.stamina > 0:
            text = "WASD — шаг | Enter — войти | I C K J — панели"
        else:
            text = "Нет сил идти — Enter для отдыха | I C K J"
        surf = self._font_hint.render(text, True, (230, 230, 230))
        bg = pg.Surface((surf.get_width() + 16, surf.get_height() + 8))
        bg.set_alpha(160)
        bg.fill((0, 0, 0))
        x = 10
        y = screen.get_height() - surf.get_height() - 14
        screen.blit(bg, (x, y))
        screen.blit(surf, (x + 8, y + 4))
