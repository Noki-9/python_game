import pygame as pg

from core.camera import Camera
from core.config import screen
from core.scene_manager import Scene

from scenes.local_scene import LocalScene

SEG_SIZE = 16
CAM_PAN_SPEED = 600     # px/s — скорость панорамы в spawn-режиме


class WorldScene(Scene):
    def __init__(self, manager, world, world_pos=None, mode="spawn"):
        self.manager = manager
        self.world = world
        self.mode = mode                                # "spawn" | "play"
        self.gx, self.gy = world_pos if world_pos else (0, 0)

        sw, sh = screen.get_size()
        self.camera = Camera(sw, sh)
        self.map_w_px = world.width * SEG_SIZE
        self.map_h_px = world.height * SEG_SIZE

        self.hover_seg = None                           # (gx, gy) под курсором
        self.hover_valid = False

    def on_enter(self, world_pos=None, mode=None):
        if mode is not None:
            self.mode = mode
        if world_pos is not None:
            self.gx, self.gy = world_pos
        elif self.mode == "spawn":
            # при первом запуске ставим камеру на ближайший проходимый
            self.gx, self.gy = self._find_start_near_center()
        self._center_camera()

    def _find_start_near_center(self):
        """Ищет ближайший проходимый сегмент к центру карты (спираль)."""
        cx, cy = self.world.width // 2, self.world.height // 2
        max_r = max(self.world.width, self.world.height)
        for r in range(max_r):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if max(abs(dx), abs(dy)) != r:      # только кольцо радиуса r
                        continue
                    seg = self.world.get(cx + dx, cy + dy)
                    if seg and seg.biome.walkable:
                        return cx + dx, cy + dy
        return cx, cy

    def _center_camera(self):
        cx = self.gx * SEG_SIZE + SEG_SIZE / 2
        cy = self.gy * SEG_SIZE + SEG_SIZE / 2
        self.camera.x = max(0, min(cx - self.camera.view_w / 2,
                                   self.map_w_px - self.camera.view_w))
        self.camera.y = max(0, min(cy - self.camera.view_h / 2,
                                   self.map_h_px - self.camera.view_h))

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
        if event.key == pg.K_w: dy = -1
        if event.key == pg.K_s: dy = 1
        if event.key == pg.K_a: dx = -1
        if event.key == pg.K_d: dx = 1

        if (dx or dy) and self._can_move(dx, dy):
            self.gx += dx
            self.gy += dy
            self._center_camera()

        if event.key == pg.K_RETURN:
            seg = self.world.get(self.gx, self.gy)
            if seg and seg.biome.walkable:
                self.manager.switch(LocalScene(self.manager, seg),
                                    return_pos=(self.gx, self.gy))

    def _try_pick_segment(self, screen_pos):
        """Превращает экранную точку в сегмент. Только проходимые."""
        gx, gy = self._screen_to_segment(screen_pos)
        if gx is None:
            return
        self.gx, self.gy = gx, gy
        self.mode = "play"                              # всё — выбор сделан
        self._center_camera()

        seg = self.world.get(self.gx, self.gy)
        self.manager.switch(LocalScene(self.manager, seg), return_pos=(self.gx, self.gy))

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

    # ---------------- Update ----------------
    def update(self, dt):
        if self.mode != "spawn":
            return

        # панорама камеры: держим WASD
        keys = pg.key.get_pressed()
        pan_x = pan_y = 0
        if keys[pg.K_w]: pan_y -= 1
        if keys[pg.K_s]: pan_y += 1
        if keys[pg.K_a]: pan_x -= 1
        if keys[pg.K_d]: pan_x += 1

        if pan_x or pan_y:
            self.camera.x = max(0, min(
                self.camera.x + pan_x * CAM_PAN_SPEED * dt,
                self.map_w_px - self.camera.view_w))
            self.camera.y = max(0, min(
                self.camera.y + pan_y * CAM_PAN_SPEED * dt,
                self.map_h_px - self.camera.view_h))

        # обновляем подсветку под курсором
        gx, gy = self._screen_to_segment(pg.mouse.get_pos())
        if gx is None:
            self.hover_seg = None
            self.hover_valid = False
        else:
            self.hover_seg = (gx, gy)
            self.hover_valid = True

    # ---------------- Draw ----------------
    def draw(self, screen):
        screen.fill((15, 15, 25))
        self._draw_segments(screen)

        if self.mode == "spawn":
            self._draw_hover(screen)
        else:
            self._draw_player(screen)

        self._draw_hint(screen)

    def _draw_segments(self, screen):
        cam_x, cam_y = int(self.camera.x), int(self.camera.y)
        tx0 = max(0, int(self.camera.x // SEG_SIZE) - 1)
        ty0 = max(0, int(self.camera.y // SEG_SIZE) - 1)
        tx1 = min(self.world.width,
                  int((self.camera.x + self.camera.view_w) // SEG_SIZE) + 2)
        ty1 = min(self.world.height,
                  int((self.camera.y + self.camera.view_h) // SEG_SIZE) + 2)

        for gy in range(ty0, ty1):
            for gx in range(tx0, tx1):
                seg = self.world.segments.get((gx, gy))
                if seg is None:
                    continue
                sx = gx * SEG_SIZE - cam_x
                sy = gy * SEG_SIZE - cam_y
                pg.draw.rect(screen, seg.biome.color,
                             (sx, sy, SEG_SIZE - 1, SEG_SIZE - 1))
                if seg.explored:
                    pg.draw.rect(screen, (255, 255, 0),
                                 (sx, sy, SEG_SIZE - 1, SEG_SIZE - 1), 1)

    def _draw_hover(self, screen):
        if self.hover_seg is None:
            return
        hx, hy = self.hover_seg
        sx = hx * SEG_SIZE - int(self.camera.x)
        sy = hy * SEG_SIZE - int(self.camera.y)
        color = (255, 255, 255) if self.hover_valid else (200, 60, 60)
        pg.draw.rect(screen, color, (sx, sy, SEG_SIZE, SEG_SIZE), 2)

    def _draw_player(self, screen):
        px = self.gx * SEG_SIZE - int(self.camera.x)
        py = self.gy * SEG_SIZE - int(self.camera.y)
        pg.draw.rect(screen, (255, 60, 60), (px, py, SEG_SIZE, SEG_SIZE))

    def _draw_hint(self, screen):
        font = pg.font.SysFont(None, 22)
        if self.mode == "spawn":
            text = "ЛКМ / Enter — выбрать стартовую точку  |  WASD — панорама"
        else:
            text = "WASD — шаг  |  Enter — войти в локацию"
        surf = font.render(text, True, (230, 230, 230))
        bg = pg.Surface((surf.get_width() + 16, surf.get_height() + 8))
        bg.set_alpha(160)
        bg.fill((0, 0, 0))
        x = 10
        y = screen.get_height() - surf.get_height() - 14
        screen.blit(bg, (x, y))
        screen.blit(surf, (x + 8, y + 4))