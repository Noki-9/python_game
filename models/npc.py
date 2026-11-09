import math

import pygame as pg

from core.assets import assets
from models.unit import Unit


class NPC(Unit):
    def __init__(
        self, npc_id, name, role, x, y, rect_x, rect_y, color, visual_scale=1.0
    ):
        super().__init__(
            "npc",
            x,
            y,
            rect_x,
            rect_y,
            100,
            0,
            color,
            sprite_group="npcs",
            sprite_key=role,
            visual_scale=visual_scale,
        )
        self.npc_id = npc_id
        self.name = name
        self.role = role
        self.dialogue_root = role
        self.inventory = []  # для торговцев
        self.home_x = x
        self.home_y = y
        self.role_title = ""
        self._phase = (hash(npc_id) % 100) / 100.0

    def update(self, dt, player=None):
        if player is not None:
            dist = math.hypot(
                player.x - self.x, player.y - self.y
            )
            if dist < 150:
                self.face_towards(
                    player.x + player.rect_x / 2, player.y + player.rect_y / 2
                )
        self.moving = False
        self.update_animation(dt)

    def draw(self, screen, camera, font):
        sx, sy = camera.apply(self.x, self.y)
        if not self.draw_sprite(screen, camera):
            pg.draw.rect(screen, self.texture, (sx, sy, self.rect_x, self.rect_y))
            pg.draw.rect(screen, (20, 20, 20), (sx, sy, self.rect_x, self.rect_y), 1)

        top = sy + self.rect_y - int(32 * self.visual_scale)
        label = font.render(self.name, True, (255, 255, 200))
        screen.blit(
            label,
            (sx + self.rect_x // 2 - label.get_width() // 2, top - 15),
        )

        if self.role == "questgiver":
            t = pg.time.get_ticks() / 1000.0 + self._phase * 6.28
            bob = int(math.sin(t * 3) * 2)
            mx = sx + self.rect_x // 2
            my = top - 30 + bob
            pg.draw.circle(screen, (250, 210, 70), (mx, my), 7)
            pg.draw.circle(screen, (80, 60, 20), (mx, my), 7, 1)
            mark = font.render("!", True, (60, 40, 10))
            screen.blit(mark, (mx - mark.get_width() // 2, my - mark.get_height() // 2))
        elif self.role in ("merchant", "blacksmith"):
            icon = assets.item_icon(_GOLD)
            if icon is not None:
                icon = assets.scaled(icon, 14, 14)
                screen.blit(icon, (sx + self.rect_x // 2 - 7, top - 30))


class _GoldStub:
    item_id = "gold"
    item_type = None


_GOLD = _GoldStub()
