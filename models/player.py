import math

import pygame as pg

from models.unit import Unit


def _get_rect(obj) -> pg.Rect:
    if isinstance(obj, pg.Rect):
        return obj
    return obj.Rect


class Player(Unit):
    def __init__(self, x, y, rect_x, rect_y, health, speed, texture):
        super().__init__("player", x, y, rect_x, rect_y, health, speed, texture)

    def update(self, dt, walls=None, map_w_px=None, map_h_px=None):
        super().update(dt)
        walls = walls or []

        keys = pg.key.get_pressed()

        dx, dy = 0, 0
        if keys[pg.K_w]:
            dy -= 1
        if keys[pg.K_s]:
            dy += 1
        if keys[pg.K_a]:
            dx -= 1
        if keys[pg.K_d]:
            dx += 1

        length = math.hypot(dx, dy)
        if length != 0:
            dx /= length
            dy /= length

        dx *= self.speed * dt
        dy *= self.speed * dt

        # --- движение по X ---
        if dx != 0:
            self.x += dx
            if map_w_px is not None:
                self.x = max(0, min(self.x, map_w_px - self.rect_x))
            self.sync_rect()

            for wall in walls:
                w_rect = _get_rect(wall)
                if self.Rect.colliderect(w_rect):
                    if dx > 0:
                        self.x = w_rect.left - self.rect_x
                    else:
                        self.x = w_rect.right
                    self.sync_rect()
                    break

        # --- движение по Y ---
        if dy != 0:
            self.y += dy
            if map_h_px is not None:
                self.y = max(0, min(self.y, map_h_px - self.rect_y))
            self.sync_rect()

            for wall in walls:
                w_rect = _get_rect(wall)
                if self.Rect.colliderect(w_rect):
                    if dy > 0:
                        self.y = w_rect.top - self.rect_y
                    else:
                        self.y = w_rect.bottom
                    self.sync_rect()
                    break
