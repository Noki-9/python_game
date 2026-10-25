import pygame as pg

from core.camera import Camera
from core.config import screen
from core.scene_manager import Scene
from world.biome import Biome

SEG_SIZE = 16
CAM_PAN_SPEED = 600

# Стоимость шага по биому НАЗНАЧЕНИЯ
BIOME_MOVE_COST = {
    Biome.PLAINS: 1,
    Biome.FOREST: 2,
    Biome.DESERT: 3,
    Biome.TUNDRA: 3,
}
DEFAULT_MOVE_COST = 1


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

        sw, sh = screen.get_size()
        self.camera = Camera(sw, sh)
        self.map_w_px = world.width * SEG_SIZE
        self.map_h_px = world.height * SEG_SIZE

        self.hover_seg = None
        self.hover_valid = False
        self._ensure_prerender()

    # ---- Позиция как свойства → синхронизируется с state ----
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
                    # Проходимый рядом с непроходимым — размываем СВОЮ сторону
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
                    continue  # сосед размоет себя сам
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

    # ---------------- Жизненный цикл ----------------
    def on_enter(self, world_pos=None, mode=None):
        if mode is not None:
            self.mode = mode
        if world_pos is not None:
            self.gx, self.gy = world_pos
        elif self.mode == "spawn":
            self.gx, self.gy = self._find_start_near_center()
            self.state.restore()  # старт — полные силы
        self._center_camera()

    def _find_start_near_center(self):
        cx, cy = self.world.width // 2, self.world.height // 2
        for r in range(max(self.world.width, self.world.height)):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if max(abs(dx), abs(dy)) != r:
                        continue
                    seg = self.world.get(cx + dx, cy + dy)
                    if seg and seg.biome.walkable:
                        return cx + dx, cy + dy
        return cx, cy

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

        # Enter работает всегда — даже при нулевой выносливости
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
            return  # не хватает выносливости
        self.gx += dx
        self.gy += dy
        self._center_camera()

    def _try_pick_segment(self, screen_pos):
        gx, gy = self._screen_to_segment(screen_pos)
        if gx is None:
            return
        self.gx, self.gy = gx, gy
        self.state.restore()  # точка старта — всегда с силами
        self.mode = "play"
        self._center_camera()

    def _screen_to_segment(self, screen_pos):
        sx, sy = screen_pos
        wx = sx + self.camera.x
        wy = sy + self.camera.y
        gx = int(wx // SEG_SIZE)
        gy = int(wy // SEG_SIZE)
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
        if self.mode != "spawn":
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

        screen.blit(
            self.world._prerender,
            (0, 0),
            (cam_x, cam_y, self.camera.view_w, self.camera.view_h),
        )

        # Разведанные — обводка
        tx0 = max(0, int(cam_x // SEG_SIZE) - 1)
        ty0 = max(0, int(cam_y // SEG_SIZE) - 1)
        tx1 = min(self.world.width, int((cam_x + self.camera.view_w) // SEG_SIZE) + 2)
        ty1 = min(self.world.height, int((cam_y + self.camera.view_h) // SEG_SIZE) + 2)
        for gy in range(ty0, ty1):
            for gx in range(tx0, tx1):
                seg = self.world.segments.get((gx, gy))
                if seg and seg.explored:
                    pg.draw.rect(
                        screen,
                        (255, 255, 0),
                        (
                            gx * SEG_SIZE - cam_x,
                            gy * SEG_SIZE - cam_y,
                            SEG_SIZE - 1,
                            SEG_SIZE - 1,
                        ),
                        1,
                    )

        if self.mode == "spawn":
            self._draw_hover(screen, cam_x, cam_y)
        else:
            self._draw_player(screen, cam_x, cam_y)

        self._draw_stamina(screen)
        self._draw_hint(screen)

    def _draw_hover(self, screen, cam_x, cam_y):
        if self.hover_seg is None:
            return
        hx, hy = self.hover_seg
        sx = hx * SEG_SIZE - cam_x
        sy = hy * SEG_SIZE - cam_y
        color = (255, 255, 255) if self.hover_valid else (200, 60, 60)
        pg.draw.rect(screen, color, (sx, sy, SEG_SIZE, SEG_SIZE), 2)

    def _draw_player(self, screen, cam_x, cam_y):
        px = self.gx * SEG_SIZE - cam_x
        py = self.gy * SEG_SIZE - cam_y
        # Если сил нет — маркер тускнеет
        color = (255, 60, 60) if self.state.stamina > 0 else (120, 40, 40)
        pg.draw.rect(screen, color, (px, py, SEG_SIZE, SEG_SIZE))

    def _draw_stamina(self, screen):
        s = self.state
        bar_w, bar_h = 220, 22
        x, y = 12, 12

        pg.draw.rect(screen, (20, 20, 20), (x, y, bar_w, bar_h))
        fill_w = int((bar_w - 4) * s.stamina_ratio)
        color = (220, 200, 60) if s.stamina_ratio > 0.3 else (220, 60, 60)
        if fill_w > 0:
            pg.draw.rect(screen, color, (x + 2, y + 2, fill_w, bar_h - 4))
        pg.draw.rect(screen, (240, 240, 240), (x, y, bar_w, bar_h), 2)

        font = pg.font.SysFont(None, 18)
        text = f"Выносливость: {s.stamina}/{s.max_stamina}"
        surf = font.render(text, True, (255, 255, 255))
        screen.blit(surf, (x + bar_w + 8, y + 3))

    def _draw_hint(self, screen):
        font = pg.font.SysFont(None, 22)
        if self.mode == "spawn":
            text = "ЛКМ / Enter — выбрать старт  |  WASD — панорама"
        elif self.state.stamina > 0:
            text = "WASD — шаг  |  Enter — войти в локацию"
        else:
            text = "Нет сил идти — Enter, чтобы отдохнуть в локации"

        surf = font.render(text, True, (230, 230, 230))
        bg = pg.Surface((surf.get_width() + 16, surf.get_height() + 8))
        bg.set_alpha(160)
        bg.fill((0, 0, 0))
        x = 10
        y = screen.get_height() - surf.get_height() - 14
        screen.blit(bg, (x, y))
        screen.blit(surf, (x + 8, y + 4))
