import pygame as pg

from core.camera import Camera
from core.config import screen
from core.scene_manager import Scene

SEG_SIZE = 16  # 150 × 16 = 2400 px по ширине


class WorldScene(Scene):
    def __init__(self, manager, world, world_pos=(0, 0)):
        self.manager = manager
        self.world = world
        self.gx, self.gy = world_pos

        sw, sh = screen.get_size()
        self.camera = Camera(sw, sh)
        self.map_w_px = world.width * SEG_SIZE
        self.map_h_px = world.height * SEG_SIZE

    def on_enter(self, world_pos=None):
        if world_pos is not None:
            self.gx, self.gy = world_pos
        self._center_camera()

    def _center_camera(self):
        # Камера центрируется на текущем сегменте игрока
        cx = self.gx * SEG_SIZE + SEG_SIZE / 2
        cy = self.gy * SEG_SIZE + SEG_SIZE / 2
        self.camera.x = max(0, min(cx - self.camera.view_w / 2,
                                   self.map_w_px - self.camera.view_w))
        self.camera.y = max(0, min(cy - self.camera.view_h / 2,
                                   self.map_h_px - self.camera.view_h))

    def handle_event(self, event):
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
                from scenes.local_scene import LocalScene
                self.manager.switch(LocalScene(self.manager, seg),
                                    return_pos=(self.gx, self.gy))

    def _can_move(self, dx, dy) -> bool:
        seg = self.world.get(self.gx + dx, self.gy + dy)
        return seg is not None and seg.biome.walkable

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill((15, 15, 25))

        # --- Отрисовка ТОЛЬКО видимых сегментов ---
        tx0 = max(0, int(self.camera.x // SEG_SIZE) - 1)
        ty0 = max(0, int(self.camera.y // SEG_SIZE) - 1)
        tx1 = min(self.world.width,
                  int((self.camera.x + self.camera.view_w) // SEG_SIZE) + 2)
        ty1 = min(self.world.height,
                  int((self.camera.y + self.camera.view_h) // SEG_SIZE) + 2)

        cam_x, cam_y = int(self.camera.x), int(self.camera.y)
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

        # --- Маркер игрока ---
        px = self.gx * SEG_SIZE - cam_x
        py = self.gy * SEG_SIZE - cam_y
        pg.draw.rect(screen, (255, 60, 60),
                     (px, py, SEG_SIZE, SEG_SIZE))