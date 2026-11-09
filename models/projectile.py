import math

import pygame as pg

from core.assets import assets

PROJECTILE_VISUALS = {
    "m_q": "fireball",
    "m_r": "meteor",
    "a_q": "arrow",
    "a_f": "arrow",
}


def visual_for_ability(ability_id: str) -> str:
    return PROJECTILE_VISUALS.get(ability_id, "orb")


class Projectile:
    def __init__(
        self,
        x,
        y,
        vx,
        vy,
        damage,
        radius=6,
        color=(255, 200, 100),
        lifetime=1.5,
        aoe_radius=0,
        visual="orb",
    ):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.radius = radius
        self.color = color
        self.lifetime = lifetime
        self.aoe_radius = aoe_radius
        self.visual = visual
        self.alive = True
        self.elapsed = 0.0
        self.angle = math.atan2(vy, vx)

    def update(self, dt, enemies, animals, local_map, tile_size) -> list:
        """Возвращает список убитых целей."""
        killed = []
        if not self.alive:
            return killed

        self.elapsed += dt
        self.lifetime -= dt
        if self.lifetime <= 0:
            killed = self._apply_damage(enemies, animals)
            self.alive = False
            return killed

        self.x += self.vx * dt
        self.y += self.vy * dt

        # Стена
        tx = int(self.x // tile_size)
        ty = int(self.y // tile_size)
        if not local_map.is_walkable(tx, ty):
            killed = self._apply_damage(enemies, animals)
            self.alive = False
            return killed

        # Попадание
        hit = False
        for target_list in (enemies, animals):
            for t in target_list:
                if not t.is_alive():
                    continue
                ex = t.x + t.rect_x / 2
                ey = t.y + t.rect_y / 2
                tr = max(t.rect_x, t.rect_y) / 2
                if math.hypot(ex - self.x, ey - self.y) < self.radius + tr:
                    hit = True
                    break
            if hit:
                break

        if hit:
            killed = self._apply_damage(enemies, animals)
            self.alive = False
        return killed

    def _apply_damage(self, enemies, animals) -> list:
        killed = []
        for target_list in (enemies, animals):
            for t in target_list:
                if not t.is_alive():
                    continue
                ex = t.x + t.rect_x / 2
                ey = t.y + t.rect_y / 2
                tr = max(t.rect_x, t.rect_y) / 2

                if self.aoe_radius > 0:
                    if math.hypot(ex - self.x, ey - self.y) <= self.aoe_radius:
                        if t.take_damage(self.damage):
                            killed.append(t)
                else:
                    if math.hypot(ex - self.x, ey - self.y) < self.radius + tr:
                        if t.take_damage(self.damage):
                            killed.append(t)
                        return killed
        return killed

    def draw(self, screen, camera):
        sx, sy = camera.apply(self.x, self.y)
        frame = assets.projectile_frame(
            self.visual,
            self.elapsed,
            self.color if self.visual == "orb" else None,
        )
        if frame is not None:
            if self.visual == "arrow":
                frame = pg.transform.rotate(frame, -math.degrees(self.angle))
            elif self.visual == "meteor":
                frame = assets.scaled(frame, 36, 36)
            scale = 1.5 if self.aoe_radius > 0 and self.visual == "orb" else 1.0
            if scale != 1.0:
                frame = assets.scaled(frame, int(frame.get_width() * scale), int(frame.get_height() * scale))
            rect = frame.get_rect(center=(sx, sy))
            screen.blit(frame, rect)
            return
        pg.draw.circle(screen, self.color, (sx, sy), self.radius)
        pg.draw.circle(screen, (30, 30, 30), (sx, sy), self.radius, 1)
