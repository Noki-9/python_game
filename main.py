import pygame as pg
from core.config import screen, clock
from models.player import Player
from models.walls import Wall


pg.init()
scr_w, scr_h = screen.get_size()

player = Player(scr_w // 2, scr_h // 2, 50, 100, 100, 200, 'blue')
walls = [
    Wall(100, 100, 50, 50, 100, "gray"),
    Wall(400, 300, 200, 30, 100, "gray"),
    Wall(800, 500, 30, 200, 100, "gray"),
]

running = True
while running:
    dt = clock.tick(60) / 1000   # ОДИН раз за кадр!

    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False

    screen.fill("purple")

    # Игрок двигается с учётом стен
    player.update(dt, walls)
    player.draw(screen)

    for wall in walls:
        wall.draw(screen)

    pg.display.flip()

pg.quit()