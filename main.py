import pygame as pg

from core.config import clock, screen
from core.scene_manager import SceneManager
from scenes.menu_scene import MenuScene


def main():
    pg.init()
    manager = SceneManager()
    manager.switch(MenuScene(manager))

    while manager.running:
        dt = clock.tick(60) / 1000
        for event in pg.event.get():
            if event.type == pg.QUIT:
                manager.running = False
            else:
                manager.handle_event(event)
        manager.update(dt)
        manager.draw(screen)
        pg.display.flip()

    pg.quit()


if __name__ == "__main__":
    main()
