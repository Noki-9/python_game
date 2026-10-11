import pygame as pg

from core.config import clock, screen
from core.scene_manager import SceneManager
from scenes.world_scene import WorldScene
from world.world_map import WorldMap


def main():
    pg.init()
    manager = SceneManager()
    world = WorldMap(seed=1337)
    manager.world = world

    manager.switch(WorldScene(manager, world))

    running = True
    while running:
        dt = clock.tick(60) / 1000
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            else:
                manager.handle_event(event)
        manager.update(dt)
        manager.draw(screen)
        pg.display.flip()

    pg.quit()


if __name__ == "__main__":
    main()