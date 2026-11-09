import pygame as pg

from core.assets import assets
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
        gold_icon = assets.named_icon("gold")
        if gold_icon is not None:
            gold_icon = assets.scaled(gold_icon, 24, 24)
            total_w = gold_icon.get_width() + 6 + gold_surf.get_width()
            gx = (self.width - total_w) // 2
            screen.blit(gold_icon, (gx, 94))
            screen.blit(gold_surf, (gx + gold_icon.get_width() + 6, 95))
        else:
            screen.blit(gold_surf, ((self.width - gold_surf.get_width()) // 2, 95))

        # Сетка
        x0, y0 = self._grid_origin()
        grid_w = GRID_COLS * (CELL_SIZE + 4) - 4
        grid_h = GRID_ROWS * (CELL_SIZE + 4) - 4
        assets.draw_panel(
            screen,
            pg.Rect(x0 - 14, y0 - 14, grid_w + 28, grid_h + 28),
            alpha=225,
        )
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
            icon = assets.item_icon(item)
            if icon is not None:
                icon = assets.scaled(icon, CELL_SIZE - 14, CELL_SIZE - 14)
                screen.blit(
                    icon, icon.get_rect(center=(cx + CELL_SIZE // 2, cy + CELL_SIZE // 2))
                )
            else:
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
        gap = 8
        slot_w = min(
            180,
            max(110, (self.width - 40 - gap * max(0, len(slots) - 1)) // max(1, len(slots))),
        )
        total_w = len(slots) * (slot_w + gap) - gap
        x_start = (self.width - total_w) // 2

        for i, slot in enumerate(slots):
            sx = x_start + i * (slot_w + gap)
            rect = pg.Rect(sx, y, slot_w, 44)
            pg.draw.rect(screen, (50, 50, 65), rect)
            pg.draw.rect(screen, (110, 110, 130), rect, 2)

            label = EQUIP_SLOT_NAMES.get(slot, slot.value)
            item = self.state.equipment.get(slot)
            color = item.rarity.color if item else (150, 150, 150)
            text_x = sx + 8
            if item is not None:
                icon = assets.item_icon(item)
                if icon is not None:
                    icon = assets.scaled(icon, 28, 28)
                    screen.blit(icon, (sx + 6, y + 8))
                    text_x = sx + 38
            name = item.name if item else "—"
            text = f"{label}: {name}"
            max_text_w = rect.right - text_x - 6
            if self.font_small.size(text)[0] > max_text_w:
                while name and self.font_small.size(f"{label}: {name}…")[0] > max_text_w:
                    name = name[:-1]
                text = f"{label}: {name}…"
            surf = self.font_small.render(text, True, color)
            screen.blit(surf, (text_x, y + 13))

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
