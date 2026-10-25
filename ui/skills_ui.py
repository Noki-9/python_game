import pygame as pg

from core.skills import ALL_SKILLS
from ui.overlay import UIOverlay

NODE_SIZE = 60
NODE_GAP = 24


class SkillsUI(UIOverlay):
    def __init__(self, screen_size, player_state):
        super().__init__(screen_size, player_state)
        self.hovered_node = None
        self.hovered_rect = None

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            self._try_unlock(event.pos)

    def _positions(self):
        skills = ALL_SKILLS.get(self.state.class_id, [])
        branches = {}
        for node in skills:
            branches.setdefault(node.branch, []).append(node)

        positions = []
        branch_keys = sorted(branches.keys())
        col_w = NODE_SIZE + NODE_GAP * 2
        total_w = len(branch_keys) * col_w
        x_start = (self.width - total_w) // 2

        for bi, branch in enumerate(branch_keys):
            bx = x_start + bi * col_w
            for ni, node in enumerate(branches[branch]):
                ny = 170 + ni * (NODE_SIZE + NODE_GAP)
                positions.append((node, pg.Rect(bx, ny, NODE_SIZE, NODE_SIZE)))
        return positions

    def _try_unlock(self, pos):
        for node, rect in self._positions():
            if rect.collidepoint(pos):
                self.state.unlock_skill(node)
                return

    def draw(self, screen):
        super().draw(screen)

        title = self.font_big.render("Дерево навыков", True, (255, 255, 255))
        screen.blit(title, ((self.width - title.get_width()) // 2, 60))

        info = (
            f"Класс: {self.state.class_def.name}   "
            f"Уровень: {self.state.level}   "
            f"Очки навыков: {self.state.skill_points}"
        )
        surf = self.font_med.render(info, True, (220, 220, 220))
        screen.blit(surf, ((self.width - surf.get_width()) // 2, 100))

        self.hovered_node = None
        self.hovered_rect = None

        for node, rect in self._positions():
            self._draw_node(screen, node, rect)
            if rect.collidepoint(pg.mouse.get_pos()):
                self.hovered_node = node
                self.hovered_rect = rect

        if self.hovered_node:
            self._draw_tooltip(screen, self.hovered_node)

    def _draw_node(self, screen, node, rect):
        unlocked = node.skill_id in self.state.unlocked_skills
        can = self.state.can_unlock_skill(node)

        if unlocked:
            color, border = (60, 180, 60), (120, 240, 120)
        elif can:
            color, border = (60, 100, 160), (120, 180, 240)
        else:
            color, border = (55, 55, 65), (100, 100, 110)

        pg.draw.rect(screen, color, rect)
        pg.draw.rect(screen, border, rect, 2)

        name_surf = self.font_small.render(node.name, True, (240, 240, 240))
        screen.blit(name_surf, (rect.centerx - name_surf.get_width() // 2, rect.y - 20))

        lvl_surf = self.font_small.render(
            f"Ур.{node.level_required}", True, (200, 200, 200)
        )
        screen.blit(lvl_surf, (rect.x + 4, rect.y + 4))

    def _draw_tooltip(self, screen, node):
        unlocked = node.skill_id in self.state.unlocked_skills
        can = self.state.can_unlock_skill(node)

        lines = [node.name, node.description, ""]
        if unlocked:
            lines.append("✔ Изучено")
        elif can:
            lines.append(f"Нажмите ЛКМ — изучить ({node.cost} очк.)")
        else:
            reqs = ""
            if node.requires:
                reqs = "Требует: " + ", ".join(node.requires)
            lines.append(f"Ур. {node.level_required}, {node.cost} очк. {reqs}")

        surf_list = [self.font_small.render(l, True, (240, 240, 240)) for l in lines]
        max_w = max(s.get_width() for s in surf_list)
        h = sum(s.get_height() + 2 for s in surf_list) + 12

        mx, my = pg.mouse.get_pos()
        bg = pg.Rect(mx + 16, my + 16, max_w + 16, h)
        if bg.right > self.width:
            bg.right = mx - 8
        if bg.bottom > self.height:
            bg.bottom = my - 8
        pg.draw.rect(screen, (20, 20, 30), bg)
        pg.draw.rect(screen, (200, 200, 200), bg, 2)
        y = bg.y + 6
        for s in surf_list:
            screen.blit(s, (bg.x + 8, y))
            y += s.get_height() + 2
