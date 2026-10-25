import pygame as pg

from ui.overlay import UIOverlay
from world.quest import QuestStatus


class QuestLogUI(UIOverlay):
    def __init__(self, screen_size, player_state):
        super().__init__(screen_size, player_state)
        self.scroll = 0
        self.tab = "active"  # active | completed

    def handle_event(self, event):
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_TAB:
                self.tab = "completed" if self.tab == "active" else "active"
                self.scroll = 0
        elif event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 4:
                self.scroll = max(0, self.scroll - 1)
            elif event.button == 5:
                self.scroll += 1
        elif event.type == pg.MOUSEMOTION:
            pass

    def draw(self, screen):
        super().draw(screen)

        title = self.font_big.render("Журнал квестов", True, (255, 255, 255))
        screen.blit(title, ((self.width - title.get_width()) // 2, 40))

        # Табы
        tab_y = 90
        active_count = len(self.state.quest_log.active())
        done_count = len(self.state.quest_log.completed())

        tabs = [
            ("active", f"Активные ({active_count})"),
            ("completed", f"Выполнено ({done_count})"),
        ]
        x = self.width // 2 - 220
        for key, label in tabs:
            surf = self.font_med.render(
                label, True, (240, 220, 100) if self.tab == key else (140, 140, 140)
            )
            rect = pg.Rect(x, tab_y, 220, 30)
            if self.tab == key:
                pg.draw.rect(screen, (60, 60, 80), rect)
            screen.blit(surf, (x + 8, tab_y + 4))
            x += 240

        if self.tab == "active":
            quests = self.state.quest_log.active()
        else:
            quests = self.state.quest_log.completed()

        if not quests:
            msg = "Нет квестов" if self.tab == "active" else "Нет выполненных"
            surf = self.font_med.render(msg, True, (150, 150, 150))
            screen.blit(surf, ((self.width - surf.get_width()) // 2, 200))
            self._draw_hint(screen)
            return

        y = 150
        row_h = 100
        visible = self.height - y - 60
        max_visible = max(1, visible // row_h)
        start = min(self.scroll, max(0, len(quests) - max_visible))

        for i, q in enumerate(quests[start : start + max_visible]):
            self._draw_quest(screen, q, 60, y, self.width - 120, row_h - 10)
            y += row_h

        self._draw_hint(screen)

    def _draw_quest(self, screen, quest, x, y, w, h):
        rect = pg.Rect(x, y, w, h)
        bg = (35, 40, 55) if quest.status == QuestStatus.ACTIVE else (30, 50, 35)
        pg.draw.rect(screen, bg, rect)

        border = (
            (200, 180, 100) if quest.status == QuestStatus.ACTIVE else (100, 200, 120)
        )
        pg.draw.rect(screen, border, rect, 2)

        # Заголовок
        title = self.font_med.render(quest.title, True, border)
        screen.blit(title, (x + 12, y + 8))

        # Описание
        desc = self.font_small.render(quest.description, True, (220, 220, 220))
        screen.blit(desc, (x + 12, y + 34))

        # Цель с прогрессом
        obj = quest.objective
        obj_color = (120, 240, 120) if obj.done else (240, 220, 100)
        obj_surf = self.font_small.render(
            f"Цель: {obj.description}  [{obj.progress_str}]", True, obj_color
        )
        screen.blit(obj_surf, (x + 12, y + 56))

        # Награда
        reward = self.font_small.render(
            f"Награда: {quest.reward_gold} золота, {quest.reward_xp} XP",
            True,
            (240, 210, 120),
        )
        screen.blit(reward, (x + 12, y + 74))

        # Выдал
        if quest.giver_name:
            giver = self.font_small.render(
                f"Квестодатель: {quest.giver_name}", True, (150, 150, 180)
            )
            screen.blit(giver, (x + w - giver.get_width() - 12, y + 8))

    def _draw_hint(self, screen):
        hint = self.font_small.render(
            "Tab — переключить вкладку | Колесо — прокрутка | Esc — закрыть",
            True,
            (150, 150, 150),
        )
        screen.blit(hint, ((self.width - hint.get_width()) // 2, self.height - 30))
