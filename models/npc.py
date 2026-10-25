from models.unit import Unit


class NPC(Unit):
    def __init__(self, npc_id, name, role, x, y, rect_x, rect_y, color):
        super().__init__("npc", x, y, rect_x, rect_y, 100, 0, color)
        self.npc_id = npc_id
        self.name = name
        self.role = role
        self.dialogue_root = role
        self.inventory = []  # для торговцев
        self.home_x = x
        self.home_y = y
        self.role_title = ""

    def draw(self, screen, camera, font):
        sx, sy = camera.apply(self.x, self.y)
        import pygame as pg

        pg.draw.rect(screen, self.texture, (sx, sy, self.rect_x, self.rect_y))
        pg.draw.rect(screen, (20, 20, 20), (sx, sy, self.rect_x, self.rect_y), 1)
        label = font.render(self.name, True, (255, 255, 200))
        screen.blit(label, (sx + self.rect_x // 2 - label.get_width() // 2, sy - 14))
