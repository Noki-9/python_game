import pygame as pg


class Unit:
    def __init__(self, x: int, y: int, rect_x: int, rect_y: int, health: int, speed: int, texture: str):
        # Здоровье юнита
        self.health = health
        # Координаты на карте
        self.x = x
        self.y = y
        # Размеры юнита
        self.rect_x = rect_x
        self.rect_y = rect_y
        # Скорость
        self.speed = speed
        # Модель подгружается из отдельной папки
        self.texture = texture

    def check_collision(self, other: pg.Rect) -> bool:
        return self.Rect.colliderect(other)

    def draw(self, screen):
        pg.draw.rect(screen, self.texture, (self.x, self.y, self.rect_x, self.rect_y))

    def update(self):
        pass