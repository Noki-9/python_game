import math
import random

import pygame as pg

from models.unit import Unit


def _get_rect(obj) -> pg.Rect:
    if isinstance(obj, pg.Rect):
        return obj
    return obj.Rect


class Player(Unit):
    def __init__(self, x, y, rect_x, rect_y, health, speed, texture, state=None):
        super().__init__("player", x, y, rect_x, rect_y, health, speed, texture)
        self.state = state
        self.attack_timer = 0.0

    def take_damage(self, amount):
        if self.state is None:
            self.health -= amount
            return self.health <= 0
        return self.state.take_damage(amount)

    def is_alive(self):
        if self.state is None:
            return self.health > 0
        return self.state.hp > 0

    def try_attack(self, targets):
        """Возвращает (killed, target, is_crit) или None."""
        if self.state is None or self.attack_timer > 0:
            return None

        cx = self.x + self.rect_x / 2
        cy = self.y + self.rect_y / 2
        attack_range = self.state.attack_range

        target = None
        target_dist = None
        for t in targets:
            if not t.is_alive():
                continue
            tx = t.x + t.rect_x / 2
            ty = t.y + t.rect_y / 2
            d = math.hypot(tx - cx, ty - cy)
            if d <= attack_range and (target_dist is None or d < target_dist):
                target = t
                target_dist = d

        if target is None:
            return None

        damage = self.state.attack_damage
        is_crit = random.random() < self.state.crit_chance
        if is_crit:
            damage = int(damage * self.state.crit_multiplier)

        self.attack_timer = self.state.attack_cooldown
        killed = target.take_damage(damage)
        return killed, target, is_crit

    def update(self, dt, walls=None, map_w_px=None, map_h_px=None):
        super().update(dt)
        if self.attack_timer > 0:
            self.attack_timer = max(0.0, self.attack_timer - dt)

        walls = walls or []
        keys = pg.key.get_pressed()

        dx = dy = 0
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
