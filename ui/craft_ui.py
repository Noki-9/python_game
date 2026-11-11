import random

import pygame as pg

from core.assets import assets
from ui.overlay import UIOverlay
from world.crafting import RECIPES, can_craft, craft, material_count

ROW_H = 56


class CraftUI(UIOverlay):
    def __init__(self, screen_size, player_state, recipes=None, title="Кузнец — крафт"):
        super().__init__(screen_size, player_state)
        self.recipes = list(recipes if recipes is not None else RECIPES)
        self.title = title
        self.rng = random.Random()
        self.row_rects = []
        self.message = ""
        self.message_timer = 0.0

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            for rect, recipe in self.row_rects:
                if rect.collidepoint(event.pos):
                    self._craft(recipe)
                    return

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt

    def _craft(self, recipe):
        if not can_craft(self.state, recipe):
            self.message = "Не хватает материалов или золота"
            self.message_timer = 2.0
            return
        item = craft(self.state, recipe, self.rng)
        if item is None:
            self.message = "Не удалось создать предмет"
        else:
            self.message = f"Создано: {item.name}"
        self.message_timer = 2.4

    def _materials_text(self, recipe):
        parts = []
        for item_id, need in recipe.materials.items():
            have = material_count(self.state.inventory, item_id)
            name = item_id
            from world.loot import ITEMS_REGISTRY

            template = ITEMS_REGISTRY.get(item_id)
            if template is not None:
                name = template.name
            parts.append(f"{name} {have}/{need}")
        if recipe.gold:
            parts.append(f"золото {self.state.gold}/{recipe.gold}")
        return "  ".join(parts)

    def draw(self, screen):
        super().draw(screen)
        title = self.font_big.render(self.title, True, (255, 255, 255))
        screen.blit(title, ((self.width - title.get_width()) // 2, 40))

        x = (self.width - 760) // 2
        y = 100
        self.row_rects = []
        for recipe in self.recipes:
            rect = pg.Rect(x, y, 760, ROW_H - 6)
            ok = can_craft(self.state, recipe)
            pg.draw.rect(screen, (44, 52, 66) if ok else (34, 34, 42), rect)
            pg.draw.rect(screen, (110, 180, 140) if ok else (80, 80, 90), rect, 1)

            name = self.font_med.render(recipe.name, True, (235, 235, 240))
            screen.blit(name, (rect.x + 12, rect.y + 6))
            mats = self.font_small.render(
                self._materials_text(recipe),
                True,
                (190, 200, 170) if ok else (160, 120, 120),
            )
            screen.blit(mats, (rect.x + 12, rect.y + 30))

            price = self.font_small.render(
                f"{recipe.gold} зол.", True, (240, 220, 100)
            )
            screen.blit(price, (rect.right - price.get_width() - 12, rect.y + 16))
            self.row_rects.append((rect, recipe))
            y += ROW_H

        if self.message_timer > 0:
            surf = self.font_med.render(self.message, True, (255, 230, 120))
            screen.blit(surf, ((self.width - surf.get_width()) // 2, y + 10))

        hint = self.font_small.render(
            "ЛКМ по рецепту — создать | Esc — закрыть", True, (150, 150, 150)
        )
        screen.blit(hint, ((self.width - hint.get_width()) // 2, self.height - 40))
