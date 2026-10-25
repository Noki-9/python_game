import pygame as pg

from models.item import EQUIP_SLOT_NAMES
from ui.overlay import UIOverlay

CELL_SIZE = 56
GRID_COLS = 8
GRID_ROWS = 6


class InventoryUI(UIOverlay):
    def __init__(self, screen_size, player_state):
        super().__init__(screen_size, player_state)
        self.hovered_item = None

    def handle_event(self, event):
        if event.type == pg.MOUSEMOTION:
            self.hovered_item = self._item_at(event.pos)
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            item = self._item_at(event.pos)
            if item and item.is_equipment:
                self.state.equip(item)

    def _grid_origin(self):
        x0 = (self.width - GRID_COLS * (CELL_SIZE + 4)) // 2
        y0 = 140
        return x0, y0

    def _item_at(self, pos):
        x0, y0 = self._grid_origin()
        mx, my = pos
        for i, item in enumerate(self.state.inventory):
            row = i // GRID_COLS
            col = i % GRID_COLS
            cell_x = x0 + col * (CELL_SIZE + 4)
            cell_y = y0 + row * (CELL_SIZE + 4)
            if cell_x <= mx < cell_x + CELL_SIZE and cell_y <= my < cell_y + CELL_SIZE:
                return item
        return None

    def draw(self, screen):
        super().draw(screen)

        title = self.font_big.render("Инвентарь", True, (255, 255, 255))
        screen.blit(title, ((self.width - title.get_width()) // 2, 60))

        gold_surf = self.font_med.render(
            f"Золото: {self.state.gold}", True, (240, 220, 100)
        )
        screen.blit(gold_surf, ((self.width - gold_surf.get_width()) // 2, 95))

        # Сетка
        x0, y0 = self._grid_origin()
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                cx = x0 + col * (CELL_SIZE + 4)
                cy = y0 + row * (CELL_SIZE + 4)
                pg.draw.rect(screen, (40, 40, 55), (cx, cy, CELL_SIZE, CELL_SIZE))
                pg.draw.rect(screen, (80, 80, 100), (cx, cy, CELL_SIZE, CELL_SIZE), 2)

        # Предметы
        for i, item in enumerate(self.state.inventory):
            if i >= GRID_COLS * GRID_ROWS:
                break
            row = i // GRID_COLS
            col = i % GRID_COLS
            cx = x0 + col * (CELL_SIZE + 4)
            cy = y0 + row * (CELL_SIZE + 4)

            color = item.icon_color
            pg.draw.rect(
                screen, color, (cx + 8, cy + 8, CELL_SIZE - 16, CELL_SIZE - 16)
            )
            pg.draw.rect(
                screen,
                item.rarity.color,
                (cx + 2, cy + 2, CELL_SIZE - 4, CELL_SIZE - 4),
                2,
            )

            if item.count > 1:
                cnt = self.font_small.render(str(item.count), True, (255, 255, 255))
                screen.blit(cnt, (cx + CELL_SIZE - 20, cy + CELL_SIZE - 18))

        # Экипировка — внизу
        self._draw_equipment(screen)

        # Тултип
        if self.hovered_item:
            self._draw_tooltip(screen, self.hovered_item)

    def _draw_equipment(self, screen):
        y = 140 + GRID_ROWS * (CELL_SIZE + 4) + 20
        title = self.font_med.render("Экипировка", True, (220, 220, 220))
        screen.blit(title, ((self.width - title.get_width()) // 2, y))
        y += 30

        slots = [s for s in self.state.equipment.keys()]
        slot_w = 180
        gap = 8
        total_w = len(slots) * (slot_w + gap) - gap
        x_start = (self.width - total_w) // 2

        for i, slot in enumerate(slots):
            sx = x_start + i * (slot_w + gap)
            rect = pg.Rect(sx, y, slot_w, 44)
            pg.draw.rect(screen, (50, 50, 65), rect)
            pg.draw.rect(screen, (110, 110, 130), rect, 2)

            label = EQUIP_SLOT_NAMES.get(slot, slot.value)
            item = self.state.equipment.get(slot)
            text = f"{label}: {item.name if item else '—'}"
            color = item.rarity.color if item else (150, 150, 150)
            surf = self.font_small.render(text, True, color)
            screen.blit(surf, (sx + 8, y + 13))

    def _draw_tooltip(self, screen, item):
        lines = [f"{item.rarity.display_name} {item.name}"]
        lines.extend(item.describe_bonuses())
        if item.value:
            lines.append(f"Ценность: {item.value}")

        surf_list = [
            (
                line,
                self.font_small.render(
                    line, True, item.rarity.color if i == 0 else (230, 230, 230)
                ),
            )
            for i, line in enumerate(lines)
        ]
        max_w = max(s.get_width() for _, s in surf_list)
        h = sum(s.get_height() + 2 for _, s in surf_list) + 12

        mx, my = pg.mouse.get_pos()
        bg = pg.Rect(mx + 16, my + 16, max_w + 16, h)
        if bg.right > self.width:
            bg.right = mx - 8
        if bg.bottom > self.height:
            bg.bottom = my - 8

        pg.draw.rect(screen, (20, 20, 30), bg)
        pg.draw.rect(screen, item.rarity.color, bg, 2)
        y = bg.y + 6
        for _, s in surf_list:
            screen.blit(s, (bg.x + 8, y))
            y += s.get_height() + 2
