import pygame as pg

from ui.overlay import UIOverlay

COL_W = 420
ROW_H = 42
MAX_VISIBLE = 10


def _buy_price(item, rep):
    return max(1, int(item.value * (1.5 - rep * 0.005)))


def _sell_price(item, rep):
    return max(1, int(item.value * (0.4 + rep * 0.003)))


class TradeUI(UIOverlay):
    def __init__(self, screen_w, screen_h, player_state, npc):
        super().__init__((screen_w, screen_h), player_state)
        self.npc = npc
        self.merchant_items = list(npc.inventory)
        self.selected_merchant = -1
        self.selected_player = -1
        self.message = ""
        self.message_timer = 0.0
        self._scroll_m = 0
        self._scroll_p = 0

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt

    def _flash(self, text):
        self.message = text
        self.message_timer = 2.0

    # --- Раскладка ---
    def _layout(self):
        gap = 40
        total = COL_W * 2 + gap
        x0 = (self.width - total) // 2
        y0 = 180
        left_rect = pg.Rect(x0, y0, COL_W, ROW_H * MAX_VISIBLE)
        right_rect = pg.Rect(x0 + COL_W + gap, y0, COL_W, ROW_H * MAX_VISIBLE)
        return left_rect, right_rect

    # --- Ввод ---
    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN:
            left, right = self._layout()
            if event.button == 4:  # wheel up
                if left.collidepoint(event.pos):
                    self._scroll_m = max(0, self._scroll_m - 1)
                elif right.collidepoint(event.pos):
                    self._scroll_p = max(0, self._scroll_p - 1)
            elif event.button == 5:  # wheel down
                if left.collidepoint(event.pos):
                    self._scroll_m = min(
                        max(0, len(self.merchant_items) - MAX_VISIBLE),
                        self._scroll_m + 1,
                    )
                elif right.collidepoint(event.pos):
                    player_items = self._player_sellable()
                    self._scroll_p = min(
                        max(0, len(player_items) - MAX_VISIBLE), self._scroll_p + 1
                    )
            elif event.button == 1:
                self._handle_left_click(event.pos, left, right)

    def _player_sellable(self):
        return [
            it for it in self.state.inventory if not it.is_equipment or True
        ]  # продавать можно всё

    def _handle_left_click(self, pos, left, right):
        # Покупка
        if left.collidepoint(pos):
            row = (pos[1] - left.y) // ROW_H + self._scroll_m
            if 0 <= row < len(self.merchant_items):
                self._buy(self.merchant_items[row])

        # Продажа
        elif right.collidepoint(pos):
            items = self._player_sellable()
            row = (pos[1] - right.y) // ROW_H + self._scroll_p
            if 0 <= row < len(items):
                self._sell(items[row])

    def _buy(self, item):
        price = _buy_price(item, self.state.reputation)
        if self.state.gold < price:
            self._flash("Недостаточно золота")
            return
        self.state.gold -= price
        self.merchant_items.remove(item)
        self.state.add_item(item)
        self._flash(f"Куплено: {item.name} за {price}")

    def _sell(self, item):
        if item not in self.state.inventory:
            return
        price = _sell_price(item, self.state.reputation)
        self.state.inventory.remove(item)
        self.state.gold += price
        self._flash(f"Продано: {item.name} за {price}")

    # --- Draw ---
    def draw(self, screen):
        super().draw(screen)

        title = self.font_big.render(
            f"Торговля — {self.npc.name}", True, (255, 255, 255)
        )
        screen.blit(title, ((self.width - title.get_width()) // 2, 60))

        gold = self.font_med.render(f"Золото: {self.state.gold}", True, (240, 220, 100))
        screen.blit(gold, ((self.width - gold.get_width()) // 2, 100))

        left, right = self._layout()

        # Заголовки колонок
        lh = self.font_med.render("Товар торговца", True, (200, 200, 220))
        screen.blit(lh, (left.x + 8, left.y - 28))
        rh = self.font_med.render("Твой инвентарь", True, (200, 200, 220))
        screen.blit(rh, (right.x + 8, right.y - 28))

        self._draw_merchant_col(screen, left)
        self._draw_player_col(screen, right)

        if self.message_timer > 0:
            surf = self.font_med.render(self.message, True, (255, 230, 120))
            screen.blit(surf, ((self.width - surf.get_width()) // 2, left.bottom + 24))

        hint = self.font_small.render(
            "ЛКМ по предмету — купить/продать | Колесо — прокрутка | Esc — назад",
            True,
            (150, 150, 150),
        )
        screen.blit(hint, ((self.width - hint.get_width()) // 2, self.height - 60))

    def _draw_merchant_col(self, screen, rect):
        pg.draw.rect(screen, (30, 30, 45), rect)
        pg.draw.rect(screen, (80, 80, 110), rect, 2)

        start = self._scroll_m
        visible = self.merchant_items[start : start + MAX_VISIBLE]

        for i, item in enumerate(visible):
            y = rect.y + i * ROW_H
            self._draw_row(
                screen,
                rect.x + 4,
                y,
                rect.w - 8,
                item,
                _buy_price(item, self.state.reputation),
                "buy",
            )

        if len(self.merchant_items) > MAX_VISIBLE:
            self._draw_scroll_hint(screen, rect, start, len(self.merchant_items), "m")

    def _draw_player_col(self, screen, rect):
        pg.draw.rect(screen, (30, 30, 45), rect)
        pg.draw.rect(screen, (80, 80, 110), rect, 2)

        items = self._player_sellable()
        start = self._scroll_p
        visible = items[start : start + MAX_VISIBLE]

        for i, item in enumerate(visible):
            y = rect.y + i * ROW_H
            self._draw_row(
                screen,
                rect.x + 4,
                y,
                rect.w - 8,
                item,
                _sell_price(item, self.state.reputation),
                "sell",
            )

        if len(items) > MAX_VISIBLE:
            self._draw_scroll_hint(screen, rect, start, len(items), "p")

    def _draw_row(self, screen, x, y, w, item, price, mode):
        row_rect = pg.Rect(x, y + 2, w, ROW_H - 4)
        pg.draw.rect(screen, (45, 45, 65), row_rect)

        # Иконка
        pg.draw.rect(screen, item.icon_color, (x + 6, y + 8, 26, 26))
        pg.draw.rect(screen, item.rarity.color, (x + 4, y + 6, 30, 30), 2)

        # Название
        name = item.name
        if item.count > 1:
            name = f"{name} x{item.count}"
        ns = self.font_small.render(name, True, item.rarity.color)
        screen.blit(ns, (x + 44, y + 12))

        # Цена
        price_color = (200, 220, 120) if mode == "buy" else (220, 200, 120)
        ps = self.font_small.render(f"{price} зол.", True, price_color)
        screen.blit(ps, (x + w - ps.get_width() - 10, y + 12))

    def _draw_scroll_hint(self, screen, rect, start, total, key):
        text = f"{start + 1}-{min(start + MAX_VISIBLE, total)} / {total}"
        surf = self.font_small.render(text, True, (160, 160, 180))
        screen.blit(surf, (rect.right - surf.get_width() - 6, rect.y - 20))
