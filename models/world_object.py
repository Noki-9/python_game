import pygame as pg

from core.assets import assets
from core.config import TILE_SIZE

OBJECT_COLORS = {
    "tree": (50, 120, 60),
    "cactus": (70, 140, 80),
}


class WorldObject:
    """Статичный объект мира (дерево, кактус) — как NPC, но без AI."""

    def __init__(self, kind, x, y, variant=0, solid=False):
        self.kind = kind
        self.x = x
        self.y = y
        self.variant = variant
        self.solid = solid
        self.tx = int(x // TILE_SIZE)
        self.ty = int(y // TILE_SIZE)
        self.rect_x = TILE_SIZE
        self.rect_y = TILE_SIZE

    @property
    def bottom(self):
        return self.y + self.rect_y

    def draw(self, screen, camera, time=0.0):
        sx, sy = camera.apply(self.x, self.y)
        image = assets.object_frame(self.kind, self.variant)
        if image is not None:
            screen.blit(image, (sx, sy))
            return
        pg.draw.rect(
            screen,
            OBJECT_COLORS.get(self.kind, (255, 0, 255)),
            (sx, sy, self.rect_x, self.rect_y),
        )
