import pygame as pg


class Scene:
    def on_enter(self, **kwargs): ...
    def on_exit(self): ...
    def handle_event(self, event): ...
    def update(self, dt): ...
    def draw(self, screen): ...


class SceneManager:
    def __init__(self):
        self.scene = None
        self.ui_overlays = []

    def switch(self, scene, **kwargs):
        if self.scene:
            self.scene.on_exit()
        self.scene = scene
        self.ui_overlays = []
        self.scene.on_enter(**kwargs)

    def push_ui(self, ui):
        self.ui_overlays.append(ui)

    def pop_ui(self):
        if self.ui_overlays:
            self.ui_overlays.pop()

    def handle_event(self, event):
        if self.ui_overlays:
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                self.pop_ui()
                return
            self.ui_overlays[-1].handle_event(event)
            return
        if self.scene:
            self.scene.handle_event(event)

    def update(self, dt):
        if self.scene:
            self.scene.update(dt)

    def draw(self, screen):
        if self.scene:
            self.scene.draw(screen)
        for ui in self.ui_overlays:
            ui.draw(screen)
