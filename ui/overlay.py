# ui/overlay.py
import pygame as pg


class UIOverlay:
    def __init__(self, screen_size, player_state):
        self.width, self.height = screen_size
        self.state = player_state
        self.manager = None  # ставится SceneManager.push_ui
        self.font_small = pg.font.SysFont(None, 18)
        self.font_med = pg.font.SysFont(None, 22)
        self.font_big = pg.font.SysFont(None, 28)

    def handle_event(self, event):
        pass

    def update(self, dt):
        """По умолчанию ничего не делает — наследники переопределяют."""

    def draw(self, screen):
        overlay = pg.Surface((self.width, self.height))
        overlay.set_alpha(190)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        hint = self.font_small.render("Esc — закрыть", True, (180, 180, 180))
        screen.blit(hint, (self.width - hint.get_width() - 20, self.height - 30))
