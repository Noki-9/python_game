import pygame as pg

from core.camera import Camera
from core.config import TILE_SIZE, screen
from core.scene_manager import Scene
from models.player import Player

COLORS = {
    "grass": (100, 180, 90),
    "sand": (230, 210, 140),
    "snow": (230, 240, 250),
    "water": (60, 100, 200),
    "rock": (110, 100, 90),
    "tree": (50, 120, 60),
    "cactus": (70, 140, 80),
}


class LocalScene(Scene):
    def __init__(self, manager, segment):
        self.manager = manager
        self.segment = segment
        self.map = None
        self.player = None
        self.return_pos = None

    def _get_neighbors(self):
        """Биомы четырёх соседей текущего сегмента."""
        world = getattr(self.manager, "world", None)
        if world is None:
            return None
        gx, gy = self.segment.gx, self.segment.gy
        result = {}
        for name, (dx, dy) in (
            ("n", (0, -1)),
            ("s", (0, 1)),
            ("w", (-1, 0)),
            ("e", (1, 0)),
        ):
            seg = world.get(gx + dx, gy + dy)
            result[name] = seg.biome if seg else None
        return result

    def on_enter(self, return_pos=None, entry_from=None):
        self.return_pos = return_pos
        neighbors = self._get_neighbors()
        self.map = self.segment.get_local_map(neighbors=neighbors)

        cx = (self.map.width // 2) * TILE_SIZE
        cy = (self.map.height // 2) * TILE_SIZE
        self.player = Player(cx, cy, TILE_SIZE - 8, TILE_SIZE - 8, 100, 300, "blue")

        sw, sh = screen.get_size()
        self.camera = Camera(sw, sh)
        self.map_w_px = self.map.width * TILE_SIZE
        self.map_h_px = self.map.height * TILE_SIZE

    def handle_event(self, event):
        if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
            from scenes.world_scene import WorldScene

            self.manager.switch(
                WorldScene(self.manager, self.manager.world),
                world_pos=self.return_pos,
                mode="play",
            )

    def update(self, dt):
        nearby = self.map.walls_near(
            self.player.x + self.player.rect_x / 2,
            self.player.y + self.player.rect_y / 2,
            radius_px=96,
        )
        self.player.update(
            dt, walls=nearby, map_w_px=self.map_w_px, map_h_px=self.map_h_px
        )
        self.camera.follow(self.player, self.map_w_px, self.map_h_px)

    def draw(self, screen):
        screen.fill((20, 20, 20))
        tx0, ty0, tx1, ty1 = self.camera.visible_tile_range(TILE_SIZE)
        tx1 = min(tx1, self.map.width)
        ty1 = min(ty1, self.map.height)

        tiles = self.map.tiles
        for ty in range(ty0, ty1):
            row = tiles[ty]
            sy = ty * TILE_SIZE - int(self.camera.y)
            for tx in range(tx0, tx1):
                sx = tx * TILE_SIZE - int(self.camera.x)
                pg.draw.rect(screen, COLORS[row[tx]], (sx, sy, TILE_SIZE, TILE_SIZE))

        px, py = self.camera.apply(self.player.x, self.player.y)
        pg.draw.rect(
            screen,
            self.player.texture,
            (px, py, self.player.rect_x, self.player.rect_y),
        )
