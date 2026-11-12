import math

import pygame as pg

from core.assets import assets
from ui.overlay import UIOverlay

ROW_H = 44
MAX_VISIBLE = 10


class FastTravelUI(UIOverlay):
    """Быстрое перемещение между посещёнными деревнями (ТЗ 3.3)."""

    def __init__(self, screen_size, player_state, scene):
        super().__init__(screen_size, player_state)
        self.scene = scene
        self.scroll = 0
        self.row_rects = []
        self.message = ""

    def _destinations(self):
        result = []
        for gx, gy in sorted(self.state.visited_villages):
            poi = self.scene.world.poi_at(gx, gy)
            name = poi.name if poi else "Деревня"
            destroyed = bool(poi is not None and poi.destroyed)
            dist = math.hypot(gx - self.state.gx, gy - self.state.gy)
            cost = max(10, int(dist * 1.5))
            result.append((gx, gy, name, cost, destroyed))
        return result

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 4:
                self.scroll = max(0, self.scroll - 1)
            elif event.button == 5:
                total = len(self._destinations())
                self.scroll = min(max(0, total - MAX_VISIBLE), self.scroll + 1)
            elif event.button == 1:
                for rect, (gx, gy, _name, _cost, destroyed) in self.row_rects:
                    if rect.collidepoint(event.pos):
                        if destroyed:
                            self.message = "Деревня разрушена"
                            return
                        before = (self.state.gx, self.state.gy)
                        self.scene.fast_travel_to(gx, gy)
                        if (self.state.gx, self.state.gy) != before:
                            self.manager.pop_ui()
                        return

    def draw(self, screen):
        super().draw(screen)
        title = self.font_big.render("Быстрое перемещение", True, (255, 255, 255))
        screen.blit(title, ((self.width - title.get_width()) // 2, 50))

        gold = self.font_med.render(
            f"Золото: {self.state.gold}", True, (240, 220, 100)
        )
        screen.blit(gold, ((self.width - gold.get_width()) // 2, 88))

        dests = self._destinations()
        if not dests:
            msg = self.font_med.render("Нет открытых деревень", True, (160, 160, 160))
            screen.blit(msg, ((self.width - msg.get_width()) // 2, 200))
            return

        x = (self.width - 620) // 2
        y = 130
        self.row_rects = []
        visible = dests[self.scroll : self.scroll + MAX_VISIBLE]
        for gx, gy, name, cost, destroyed in visible:
            rect = pg.Rect(x, y, 620, ROW_H - 4)
            here = (gx, gy) == (self.state.gx, self.state.gy)
            affordable = self.state.gold >= cost and not here and not destroyed
            bg = (45, 55, 70) if affordable else (36, 36, 44)
            pg.draw.rect(screen, bg, rect)
            border = (110, 180, 140) if affordable else (80, 80, 90)
            pg.draw.rect(screen, border, rect, 1)

            icon = assets.world_icon("village")
            if icon is not None:
                icon = assets.scaled(icon, 24, 24)
                if destroyed:
                    icon = icon.copy()
                    icon.fill(
                        (150, 80, 80, 255), special_flags=pg.BLEND_RGBA_MULT
                    )
                screen.blit(icon, icon.get_rect(center=(rect.x + 22, rect.centery)))

            ns = self.font_med.render(name, True, (235, 235, 240))
            screen.blit(ns, (rect.x + 44, rect.y + 10))

            if here:
                label = "Вы здесь"
                color = (150, 150, 150)
            elif destroyed:
                label = "Разрушена"
                color = (200, 100, 100)
            else:
                label = f"{cost} зол."
                color = (230, 210, 110) if affordable else (180, 100, 100)
            cs = self.font_med.render(label, True, color)
            screen.blit(cs, (rect.right - cs.get_width() - 12, rect.y + 10))
            self.row_rects.append((rect, (gx, gy, name, cost, destroyed)))
            y += ROW_H

        hint = self.font_small.render(
            "ЛКМ — переместиться | Колесо — прокрутка | Esc — закрыть",
            True,
            (150, 150, 150),
        )
        screen.blit(hint, ((self.width - hint.get_width()) // 2, self.height - 40))
