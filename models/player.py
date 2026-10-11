import math
import pygame as pg
from core.config import screen
from models.unit import Unit


class Player(Unit):
    def __init__(self, x, y, rect_x, rect_y, health, speed, texture):
        super().__init__("player", x, y, rect_x, rect_y, health, speed, texture)

    def update(self, dt, walls=None):
        super().update(dt)
        walls = walls or []

        scr_w, scr_h = screen.get_size()
        keys = pg.key.get_pressed()

        # --- 1. Считываем направление в виде вектора (-1, 0, 1) ---
        dx, dy = 0, 0
        if keys[pg.K_w]: dy -= 1
        if keys[pg.K_s]: dy += 1
        if keys[pg.K_a]: dx -= 1
        if keys[pg.K_d]: dx += 1

        # --- 2. Нормализация: длина вектора = 1 ---
        length = math.hypot(dx, dy)
        if length != 0:
            dx /= length
            dy /= length

        # --- 3. Умножаем на скорость и dt ---
        dx *= self.speed * dt
        dy *= self.speed * dt

        # --- 4. Движение по X с коллизиями ---
        if dx != 0:
            self.x += dx
            self.x = max(0, min(self.x, scr_w - self.rect_x))
            self.sync_rect()

            for wall in walls:
                if self.check_collision(wall):
                    if dx > 0:
                        self.x = wall.Rect.left - self.rect_x
                    else:
                        self.x = wall.Rect.right
                    self.sync_rect()
                    break

        # --- 5. Движение по Y с коллизиями ---
        if dy != 0:
            self.y += dy
            self.y = max(0, min(self.y, scr_h - self.rect_y))
            self.sync_rect()

            for wall in walls:
                if self.check_collision(wall):
                    if dy > 0:
                        self.y = wall.Rect.top - self.rect_y
                    else:
                        self.y = wall.Rect.bottom
                    self.sync_rect()
                    break