import random

import pygame as pg

from core.classes import CLASSES
from core.config import screen
from core.player_state import PlayerState
from core.save_load import has_save, load_game
from core.scene_manager import Scene
from world.world_map import WorldMap

TITLE = "Wanderers of the Fractured Realm"


class MenuScene(Scene):
    """Главное меню: новая игра, загрузка, выход (ТЗ 12.2 / 13)."""

    def __init__(self, manager):
        self.manager = manager
        self.mode = "main"  # main | class
        self.options = ["Новая игра", "Продолжить", "Выход"]
        self.class_ids = list(CLASSES.keys())
        self.selected = 0
        self.message = ""
        self.message_timer = 0.0
        self._font_title = pg.font.SysFont(None, 54)
        self._font_med = pg.font.SysFont(None, 30)
        self._font_small = pg.font.SysFont(None, 20)
        self._option_rects = []

    # ------------------------------------------------------------------
    def _flash(self, text):
        self.message = text
        self.message_timer = 2.5

    def handle_event(self, event):
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                if self.mode == "class":
                    self.mode = "main"
                    self.selected = 0
                else:
                    self.manager.running = False
                return
            if self.mode == "main":
                if event.key in (pg.K_w, pg.K_UP):
                    self.selected = (self.selected - 1) % len(self.options)
                elif event.key in (pg.K_s, pg.K_DOWN):
                    self.selected = (self.selected + 1) % len(self.options)
                elif event.key == pg.K_RETURN:
                    self._choose_main(self.selected)
            else:
                if event.key in (pg.K_a, pg.K_LEFT):
                    self.selected = (self.selected - 1) % len(self.class_ids)
                elif event.key in (pg.K_d, pg.K_RIGHT):
                    self.selected = (self.selected + 1) % len(self.class_ids)
                elif event.key == pg.K_RETURN:
                    self._start_new_game(self.class_ids[self.selected])
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            for idx, rect in enumerate(self._option_rects):
                if rect.collidepoint(event.pos):
                    if self.mode == "main":
                        self._choose_main(idx)
                    else:
                        self._start_new_game(self.class_ids[idx])
                    return

    def _choose_main(self, idx):
        if idx == 0:
            self.mode = "class"
            self.selected = 0
        elif idx == 1:
            self._continue()
        else:
            self.manager.running = False

    def _continue(self):
        if not has_save("auto"):
            self._flash("Сохранение не найдено")
            return
        loaded = load_game("auto")
        if loaded is None:
            self._flash("Не удалось загрузить сохранение")
            return
        world, state = loaded
        self.manager.world = world
        self.manager.player_state = state
        from scenes.world_scene import WorldScene

        self.manager.switch(
            WorldScene(self.manager, world, world_pos=(state.gx, state.gy), mode="play")
        )

    def _start_new_game(self, class_id):
        world = WorldMap(seed=random.randint(1000, 9999))
        state = PlayerState(class_id=class_id)
        self.manager.world = world
        self.manager.player_state = state
        from scenes.world_scene import WorldScene

        self.manager.switch(WorldScene(self.manager, world, mode="spawn"))

    # ------------------------------------------------------------------
    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt

    def draw(self, screen):
        screen.fill((14, 16, 26))
        # Простой градиент.
        for y in range(0, screen.get_height(), 4):
            t = y / max(1, screen.get_height())
            color = (int(14 + 22 * t), int(16 + 26 * t), int(26 + 38 * t))
            pg.draw.rect(screen, color, (0, y, screen.get_width(), 4))

        title = self._font_title.render(TITLE, True, (235, 225, 180))
        screen.blit(title, ((screen.get_width() - title.get_width()) // 2, 90))

        if self.mode == "main":
            self._draw_main(screen)
        else:
            self._draw_class_select(screen)

        if self.message_timer > 0:
            surf = self._font_med.render(self.message, True, (255, 210, 120))
            screen.blit(
                surf, ((screen.get_width() - surf.get_width()) // 2, screen.get_height() - 90)
            )

    def _draw_main(self, screen):
        self._option_rects = []
        y = 260
        for idx, label in enumerate(self.options):
            active = idx == self.selected
            rect = pg.Rect((screen.get_width() - 420) // 2, y, 420, 48)
            pg.draw.rect(screen, (48, 58, 78) if active else (28, 32, 44), rect)
            pg.draw.rect(
                screen,
                (220, 200, 120) if active else (80, 84, 100),
                rect,
                2 if active else 1,
            )
            surf = self._font_med.render(label, True, (240, 240, 240))
            screen.blit(surf, surf.get_rect(center=rect.center))
            self._option_rects.append(rect)
            y += 62

        hint = self._font_small.render(
            "W/S — выбор | Enter / ЛКМ — подтвердить | Esc — выход",
            True,
            (150, 150, 165),
        )
        screen.blit(
            hint,
            ((screen.get_width() - hint.get_width()) // 2, screen.get_height() - 50),
        )

    def _draw_class_select(self, screen):
        self._option_rects = []
        y = 210
        for idx, class_id in enumerate(self.class_ids):
            defn = CLASSES[class_id]
            active = idx == self.selected
            rect = pg.Rect((screen.get_width() - 720) // 2, y, 720, 82)
            pg.draw.rect(screen, (44, 54, 72) if active else (26, 30, 40), rect)
            pg.draw.rect(
                screen, defn.color if active else (76, 80, 96), rect, 2 if active else 1
            )
            name = self._font_med.render(defn.name, True, defn.color)
            screen.blit(name, (rect.x + 18, rect.y + 12))
            desc = self._font_small.render(defn.description, True, (220, 220, 220))
            screen.blit(desc, (rect.x + 18, rect.y + 48))
            if active:
                marker = self._font_small.render("►", True, (240, 220, 120))
                screen.blit(marker, (rect.right - 34, rect.y + 28))
            self._option_rects.append(rect)
            y += 96

        hint = self._font_small.render(
            "A/D или ЛКМ — выбрать класс | Enter — начать | Esc — назад",
            True,
            (150, 150, 165),
        )
        screen.blit(
            hint,
            ((screen.get_width() - hint.get_width()) // 2, screen.get_height() - 50),
        )
