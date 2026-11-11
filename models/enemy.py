import math
import random

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
        visual_scale=1.0,
    ):
        super().__init__(
            "enemy",
            x,
            y,
            rect_x,
            rect_y,
            health,
            speed,
            color,
            sprite_group="enemies",
            sprite_key=enemy_id,
            visual_scale=visual_scale,
        )
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
        self.ai_state = "idle"  # idle | patrol | chase | attack | flee
        self.home_x = x
        self.home_y = y
        self.patrol_x = x
        self.patrol_y = y
        self.patrol_timer = random.uniform(1.0, 4.0)
        # Эффект, который враг накладывает при попадании (яд и т.п.)
        self.hit_effect = None

    # --- Жизнь ---
    def is_alive(self) -> bool:
        return self.health > 0

    def take_damage(self, amount, effect=None, effect_chance=1.0,
                    effect_duration=None, effect_power=None) -> bool:
        self.health -= amount
        self.alert_timer = 5.0
        if effect and random.random() < effect_chance:
            self.apply_status(effect, effect_duration, effect_power)
        self.trigger_hurt()
        return self.health <= 0

    def drop_loot(self, rng):
        return roll_loot(self.enemy_id, rng)

    # --- Поведение ---
    def update(self, dt, player, walls):
        if not self.is_alive():
            return

        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.alert_timer = max(0.0, self.alert_timer - dt)
        speed = self.speed * self.status.speed_multiplier()

        px = player.x + player.rect_x / 2
        py = player.y + player.rect_y / 2
        cx = self.x + self.rect_x / 2
        cy = self.y + self.rect_y / 2
        dx, dy = px - cx, py - cy
        dist = math.hypot(dx, dy)

        # Решение (скрытность игрока уменьшает радиус обнаружения)
        player_state = getattr(player, "state", None)
        stealthed = bool(getattr(player_state, "stealth", False))
        aggro_range = self.aggro_radius * (0.35 if stealthed else 1.0)
        if dist < aggro_range or self.alert_timer > 0:
            if self.health < self.max_health * 0.2 and self.enemy_id != "troll":
                self.ai_state = "flee"
            elif dist < self.attack_range:
                self.ai_state = "attack"
            else:
                self.ai_state = "chase"
        else:
            self.ai_state = "patrol"

        # Движение
        mvx = mvy = 0.0
        if self.ai_state == "chase" and dist > 0:
            mvx = dx / dist * speed * dt
            mvy = dy / dist * speed * dt
        elif self.ai_state == "flee" and dist > 0:
            mvx = -dx / dist * speed * dt
            mvy = -dy / dist * speed * dt
        elif self.ai_state == "patrol":
            self.patrol_timer -= dt
            home_dist = math.hypot(self.home_x - self.x, self.home_y - self.y)
            if home_dist > 260:
                # Слишком далеко ушли — возвращаемся.
                self.patrol_x, self.patrol_y = self.home_x, self.home_y
            elif self.patrol_timer <= 0:
                angle = random.uniform(0, math.tau)
                radius = random.uniform(24, 110)
                self.patrol_x = self.home_x + math.cos(angle) * radius
                self.patrol_y = self.home_y + math.sin(angle) * radius
                self.patrol_timer = random.uniform(2.5, 6.0)

            tdx, tdy = self.patrol_x - self.x, self.patrol_y - self.y
            td = math.hypot(tdx, tdy)
            if td > 8:
                mvx = tdx / td * speed * 0.45 * dt
                mvy = tdy / td * speed * 0.45 * dt

        self.moving = bool(mvx or mvy)
        if self.moving:
            self.face_delta(mvx, mvy)
        if self.ai_state in ("attack", "chase"):
            self.face_towards(px, py)

        if mvx or mvy:
            self._try_move(mvx, mvy, walls)

        # Атака
        if self.ai_state == "attack" and self.attack_timer <= 0:
            player.take_damage(self.damage)
            if self.hit_effect:
                target_state = getattr(player, "state", None)
                if target_state is not None:
                    target_state.status.apply(self.hit_effect)
            self.attack_timer = self.attack_cooldown
            self.trigger_attack(0.25)

        self.update_animation(dt)

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
        if not self.draw_sprite(screen, camera):
            pg.draw.rect(screen, self.texture, (sx, sy, self.rect_x, self.rect_y))
            pg.draw.rect(
                screen, (20, 20, 20), (sx, sy, self.rect_x, self.rect_y), 1
            )
        sprite_h = int(32 * self.visual_scale)
        bar_y = sy + self.rect_y - sprite_h + 1
        if self.health < self.max_health:
            ratio = max(0.0, self.health / self.max_health)
            pg.draw.rect(screen, (60, 60, 60), (sx, bar_y, self.rect_x, 4))
            pg.draw.rect(
                screen, (220, 60, 60), (sx, bar_y, int(self.rect_x * ratio), 4)
            )

        effect_color = self.status.strongest_color()
        if effect_color is not None:
            pg.draw.circle(
                screen, effect_color, (sx + self.rect_x - 4, bar_y - 4), 3
            )
