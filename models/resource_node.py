import pygame as pg

from core.assets import assets
from models.world_object import WorldObject

# kind спрайта -> id предмета в world/loot.py
RESOURCE_ITEMS = {
    "ore": "iron_ore",
    "herb": "herb",
    "log": "wood",
}

RESOURCE_NAMES = {
    "ore": "Руда",
    "herb": "Трава",
    "log": "Дерево",
}


class ResourceNode(WorldObject):
    """Собираемый ресурс на локальной карте."""

    def __init__(self, kind, x, y, variant=0, amount=1):
        super().__init__(kind, x, y, variant=variant, solid=False)
        self.resource_id = RESOURCE_ITEMS.get(kind, "wood")
        self.amount = max(1, int(amount))
        self.depleted = False

    @property
    def display_name(self):
        return RESOURCE_NAMES.get(self.kind, "Ресурс")

    def draw(self, screen, camera, time=0.0):
        sx, sy = camera.apply(self.x, self.y)
        if self.depleted:
            # Истощённая жила/куст — едва заметный след.
            color = (70, 66, 60) if self.kind == "ore" else (60, 90, 50)
            pg.draw.ellipse(screen, color, (sx + 6, sy + 22, 20, 6))
            return
        image = assets.object_frame(self.kind, self.variant)
        if image is not None:
            screen.blit(image, (sx, sy))
            return
        color = (150, 150, 160) if self.kind == "ore" else (80, 160, 80)
        pg.draw.rect(screen, color, (sx + 6, sy + 8, 20, 22))
