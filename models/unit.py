import pygame as pg


class Unit:
    def __init__(self, type: str, x: int, y: int, rect_x: int, rect_y: int,
                 health: int, speed: int, texture: str):
        self.type = type
        self.health = health
        self.x = x
        self.y = y
        self.rect_x = rect_x
        self.rect_y = rect_y
        # Rect создаётся сразу — это "хитбокс" юнита
        self.Rect = pg.Rect(x, y, rect_x, rect_y)
        self.speed = speed
        self.texture = texture

    def sync_rect(self):
        """Переносит x, y в Rect. Вызывать после любого изменения позиции."""
        self.Rect.topleft = (int(self.x), int(self.y))

    def check_collision(self, other) -> bool:
        """other — Unit или pygame.Rect."""
        other_rect = other.Rect if isinstance(other, Unit) else other
        return self.Rect.colliderect(other_rect)

    def check_collision_many(self, others: list) -> list:
        """Возвращает список объектов, с которыми есть пересечение."""
        return [o for o in others if self.check_collision(o)]

    def draw(self, screen):
        pg.draw.rect(screen, self.texture, self.Rect)

    def update(self, dt):
        pass