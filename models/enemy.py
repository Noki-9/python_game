import math

import pygame as pg

from models.unit import Unit
from world.loot import roll_loot


class Enemy(Unit):
    def __init__(
        self,
        enemy_id,
        x,
        y,
        rect_x,
        rect_y,
        health,
        speed,
        damage,
        attack_range,
        attack_cooldown,
        aggro_radius,
        xp_reward,
        color,
        loot_rng_seed=0,
    ):
        super().__init__("enemy", x, y, rect_x, rect_y, health, speed, color)
        self.enemy_id = enemy_id
        self.max_health = health
        self.damage = damage
        self.attack_range = attack_range
        self.attack_cooldown = attack_cooldown
        self.aggro_radius = aggro_radius
        self.xp_reward = xp_reward
        self.loot_rng_seed = loot_rng_seed

        self.attack_timer = 0.0
        self.alert_timer = 0.0
        self.ai_state = "idle"  # idle | chase | attack | flee
        self.home_x = x
        self.home_y = y

    # --- Жизнь ---
    def is_alive(self) -> bool:
        return self.health > 0

    def take_damage(self, amount) -> bool:
        self.health -= amount
        self.alert_timer = 5.0
        return self.health <= 0

    def drop_loot(self, rng):
        return roll_loot(self.enemy_id, rng)

    # --- Поведение ---
    def update(self, dt, player, walls):
        if not self.is_alive():
            return

        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.alert_timer = max(0.0, self.alert_timer - dt)

        px = player.x + player.rect_x / 2
        py = player.y + player.rect_y / 2
        cx = self.x + self.rect_x / 2
        cy = self.y + self.rect_y / 2
        dx, dy = px - cx, py - cy
        dist = math.hypot(dx, dy)

        # Решение
        if dist < self.aggro_radius or self.alert_timer > 0:
            if self.health < self.max_health * 0.2 and self.enemy_id != "troll":
                self.ai_state = "flee"
            elif dist < self.attack_range:
                self.ai_state = "attack"
            else:
                self.ai_state = "chase"
        else:
            self.ai_state = "idle"

        # Движение
        mvx = mvy = 0.0
        if self.ai_state == "chase" and dist > 0:
            mvx = dx / dist * self.speed * dt
            mvy = dy / dist * self.speed * dt
        elif self.ai_state == "flee" and dist > 0:
            mvx = -dx / dist * self.speed * dt
            mvy = -dy / dist * self.speed * dt
        elif self.ai_state == "idle":
            # Возврат к домашней точке
            hdx, hdy = self.home_x - self.x, self.home_y - self.y
            hd = math.hypot(hdx, hdy)
            if hd > 8:
                mvx = hdx / hd * self.speed * 0.4 * dt
                mvy = hdy / hd * self.speed * 0.4 * dt

        if mvx or mvy:
            self._try_move(mvx, mvy, walls)

        # Атака
        if self.ai_state == "attack" and self.attack_timer <= 0:
            player.take_damage(self.damage)
            self.attack_timer = self.attack_cooldown

    def _try_move(self, dx, dy, walls):
        # По X
        self.x += dx
        self.sync_rect()
        for w in walls:
            if self.Rect.colliderect(w):
                if dx > 0:
                    self.x = w.left - self.rect_x
                else:
                    self.x = w.right
                self.sync_rect()
                break

        # По Y
        self.y += dy
        self.sync_rect()
        for w in walls:
            if self.Rect.colliderect(w):
                if dy > 0:
                    self.y = w.top - self.rect_y
                else:
                    self.y = w.bottom
                self.sync_rect()
                break

    # --- Отрисовка ---
    def draw(self, screen, camera):
        sx, sy = camera.apply(self.x, self.y)
        pg.draw.rect(screen, self.texture, (sx, sy, self.rect_x, self.rect_y))
        pg.draw.rect(screen, (20, 20, 20), (sx, sy, self.rect_x, self.rect_y), 1)
        if self.health < self.max_health:
            ratio = self.health / self.max_health
            pg.draw.rect(screen, (60, 60, 60), (sx, sy - 6, self.rect_x, 4))
            pg.draw.rect(
                screen, (220, 60, 60), (sx, sy - 6, int(self.rect_x * ratio), 4)
            )
