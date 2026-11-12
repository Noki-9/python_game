import pygame as pg


def _build_scancode_key_map():
    """Карта «физическая клавиша → US-код клавиши».

    SDL в event.key отдаёт код с учётом текущей раскладки, а scancode
    всегда соответствует физической клавише. Константы pygame KSCAN_*
    как раз описывают физические клавиши.
    """
    mapping = {}
    for name in dir(pg):
        if not name.startswith("KSCAN_"):
            continue
        suffix = name[len("KSCAN_"):]
        key_value = getattr(pg, "K_" + suffix, None)
        if key_value is None and len(suffix) == 1 and suffix.isalpha():
            # Буквенные константы в pygame lowercase: K_w, K_a, ...
            key_value = getattr(pg, "K_" + suffix.lower(), None)
        if key_value is not None:
            mapping[getattr(pg, name)] = key_value
    return mapping


SCANCODE_KEY_MAP = _build_scancode_key_map()


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
        self.running = True
        self.world = None
        self.player_state = None

    def switch(self, scene, **kwargs):
        if self.scene:
            self.scene.on_exit()
        self.scene = scene
        self.ui_overlays = []
        self.scene.on_enter(**kwargs)

    def push_ui(self, ui):
        ui.manager = self
        self.ui_overlays.append(ui)

    def pop_ui(self):
        if self.ui_overlays:
            self.ui_overlays.pop()

    def handle_event(self, event):
        self._normalize_key(event)
        if self.ui_overlays:
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                self.pop_ui()
                return
            self.ui_overlays[-1].handle_event(event)
            return
        if self.scene:
            self.scene.handle_event(event)

    @staticmethod
    def _normalize_key(event):
        """Приводит event.key к физической клавише (US-раскладка).

        SDL отдаёт key с учётом текущей раскладки, поэтому при русской
        раскладке WASD перестают совпадать с K_w/K_a/K_s/K_d. Scancode
        же всегда соответствует физической клавише.
        """
        if event.type not in (pg.KEYDOWN, pg.KEYUP):
            return
        scancode = getattr(event, "scancode", 0) or 0
        if not scancode:
            return
        physical = SCANCODE_KEY_MAP.get(scancode)
        if physical is not None:
            event.key = physical

    def update(self, dt):
        if self.ui_overlays:
            self.ui_overlays[-1].update(dt)
            return
        if self.scene:
            self.scene.update(dt)

    def draw(self, screen):
        if self.scene:
            self.scene.draw(screen)
        for ui in self.ui_overlays:
            ui.draw(screen)
