import pygame as pg

from ui.overlay import UIOverlay

STAT_NAMES = {
    "strength": "Сила",
    "agility": "Ловкость",
    "intelligence": "Интеллект",
    "endurance": "Выносливость",
}


class CharacterUI(UIOverlay):
    def __init__(self, screen_size, player_state):
        super().__init__(screen_size, player_state)

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            self._try_add_stat(event.pos)

    def _stat_buttons(self):
        buttons = []
        y = 400
        for stat_key in STAT_NAMES:
            rect = pg.Rect(self.width // 2 + 180, y - 4, 36, 28)
            buttons.append((stat_key, rect))
            y += 36
        return buttons

    def _try_add_stat(self, pos):
        if self.state.stat_points <= 0:
            return
        for stat_key, rect in self._stat_buttons():
            if rect.collidepoint(pos):
                self.state.spend_stat_point(stat_key)
                return

    def draw(self, screen):
        super().draw(screen)
        s = self.state

        title = self.font_big.render("Персонаж", True, (255, 255, 255))
        screen.blit(title, ((self.width - title.get_width()) // 2, 60))

        x = self.width // 2 - 300
        y = 110
        info = [
            f"Класс: {s.class_def.name}",
            f"Уровень: {s.level}  ({s.xp}/{s.xp_to_next} XP)",
            f"HP: {s.hp}/{s.max_hp}",
            f"Атака: {s.attack_damage}",
            f"Крит: {s.crit_chance * 100:.1f}%  x{s.crit_multiplier:.2f}",
            f"Защита: {s.defense}",
            f"Радиус атаки: {s.attack_range}",
            f"Золото: {s.gold}",
            "",
            f"Очки характеристик: {s.stat_points}",
            f"Очки навыков: {s.skill_points}",
        ]
        for line in info:
            surf = self.font_med.render(line, True, (230, 230, 230))
            screen.blit(surf, (x, y))
            y += 24

        # Статы с кнопками
        y = 400
        stat_values = {
            "strength": s.total_strength,
            "agility": s.total_agility,
            "intelligence": s.total_intelligence,
            "endurance": s.total_endurance,
        }
        for stat_key, label in STAT_NAMES.items():
            line = f"{label}: {stat_values[stat_key]}"
            surf = self.font_med.render(line, True, (230, 230, 230))
            screen.blit(surf, (x, y))
            y += 36

        if s.stat_points > 0:
            for stat_key, rect in self._stat_buttons():
                pg.draw.rect(screen, (60, 120, 60), rect)
                pg.draw.rect(screen, (120, 220, 120), rect, 2)
                plus = self.font_med.render("+", True, (255, 255, 255))
                screen.blit(plus, (rect.x + 13, rect.y + 4))
