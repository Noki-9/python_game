class Scene:
    def on_enter(self): ...
    def on_exit(self): ...
    def handle_event(self, event): ...
    def update(self, dt): ...
    def draw(self, screen): ...


class SceneManager:
    def __init__(self):
        self.scene = None

    def switch(self, scene, **kwargs):
        if self.scene:
            self.scene.on_exit()
        self.scene = scene
        self.scene.on_enter(**kwargs)

    def handle_event(self, e): self.scene.handle_event(e)
    def update(self, dt):       self.scene.update(dt)
    def draw(self, screen):     self.scene.draw(screen)