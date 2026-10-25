import pygame as pg

from ui.overlay import UIOverlay
from world.dialogue import DIALOGUES
from world.quest_gen import generate_quest


class DialogueUI(UIOverlay):
    def __init__(self, screen_size, player_state, npc, world=None):
        super().__init__(screen_size, player_state)
        self.npc = npc
        self.world = world
        self.dialogues = DIALOGUES.get(npc.role, {})
        self.current_node = "root"
        self.option_rects = []
        self.message = ""
        self.message_timer = 0.0

    def _get_node(self):
        return self.dialogues.get(self.current_node)

    def handle_event(self, event):
        if event.type == pg.KEYDOWN:
            if pg.K_1 <= event.key <= pg.K_9:
                idx = event.key - pg.K_1
                self._select_option(idx)
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.option_rects):
                if rect.collidepoint(event.pos):
                    self._select_option(i)
                    return

    def _select_option(self, idx):
        node = self._get_node()
        if node is None or idx >= len(node.options):
            return
        option = node.options[idx]

        if option.action == "close":
            self.manager.pop_ui()

        elif option.action == "next":
            if option.next_node and option.next_node in self.dialogues:
                self.current_node = option.next_node

        elif option.action == "trade":
            if not self.npc.inventory:
                self._flash("У меня нет товаров")
                return
            from ui.trade_ui import TradeUI

            self.manager.push_ui(TradeUI(self.width, self.height, self.state, self.npc))

        elif option.action == "heal":
            if self.state.gold < option.cost:
                self._flash("Недостаточно золота")
                return
            if self.state.hp >= self.state.max_hp:
                self._flash("Ты и так здоров")
                return
            self.state.gold -= option.cost
            self.state.heal(option.heal_amount)
            self._flash(f"Подлечено! +{option.heal_amount} HP")

        elif option.action == "get_quest":
            self._give_quest()

    def _give_quest(self):
        if self.world is None:
            self._flash("Квесты недоступны")
            return

        if self.state.quest_log.has_active_from(self.npc.npc_id):
            self._flash("Сначала выполни текущее задание")
            return

        seed = (
            hash((self.npc.npc_id, self.state.level, len(self.state.quest_log.quests)))
            & 0xFFFFFFFF
        )
        quest = generate_quest(self.world, self.npc, seed, self.state.level)
        if self.state.quest_log.add(quest):
            self._flash(f"Новый квест: {quest.title}")
        else:
            self._flash("У меня больше нет заданий")

    def _flash(self, text):
        self.message = text
        self.message_timer = 2.5

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt

    def draw(self, screen):
        super().draw(screen)

        title = self.font_big.render(
            f"{self.npc.name} — {self.npc.role_title}",
            True,
            self.npc.texture,
        )
        screen.blit(title, ((self.width - title.get_width()) // 2, 60))

        node = self._get_node()
        if node is None:
            return

        y = 120
        for line in node.text.split("\n"):
            surf = self.font_med.render(line, True, (240, 240, 240))
            screen.blit(surf, ((self.width - surf.get_width()) // 2, y))
            y += 28

        y = 260
        self.option_rects = []
        for i, option in enumerate(node.options):
            label = f"{i + 1}. {option.label}"
            surf = self.font_med.render(label, True, (220, 220, 240))
            rect = pg.Rect((self.width - 500) // 2, y, 500, 34)
            pg.draw.rect(screen, (40, 50, 70), rect)
            pg.draw.rect(screen, (100, 120, 160), rect, 1)
            screen.blit(surf, (rect.x + 14, rect.y + 8))
            self.option_rects.append(rect)
            y += 42

        if self.message_timer > 0:
            surf = self.font_med.render(self.message, True, (255, 230, 120))
            screen.blit(surf, ((self.width - surf.get_width()) // 2, y + 20))

        hint = self.font_small.render(
            "ЛКМ или 1-9 — выбрать, Esc — закрыть", True, (150, 150, 150)
        )
        screen.blit(hint, ((self.width - hint.get_width()) // 2, self.height - 60))
