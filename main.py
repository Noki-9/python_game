import pygame as pg
from core.config import screen, clock
from models.player import Player


# pygame setup
pg.init()
scr_size = screen.get_size()

player = Player(scr_size[0] // 2, scr_size[1] // 2, 50, 100, 100, 200, 'blue')

running = True
while running:
    dt = clock.tick(60) / 1000
    # poll for events
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False

    # fill the screen with a color to wipe away anything from last frame
    screen.fill("purple")

    player.update(dt)
    player.draw(screen)

    # flip() the display to put your work on screen
    pg.display.flip()

    clock.tick(60)  # limits FPS to 60

pg.quit()