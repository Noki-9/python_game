import pygame as pg
from core.config import clock, screen
from models.unit import Unit


class Player(Unit):
    def __init__(self, x, y, rect_x, rect_y, health, speed, texture):
        super().__init__(x, y, rect_x, rect_y, health, speed, texture)

        

    def update(self, dt):
        super().update()

        scr_x, scr_y = screen.get_size()

        self.keys = pg.key.get_pressed()
        if self.keys[pg.K_w] and self.y > 0:
            self.y -= self.speed * dt
        
        if self.keys[pg.K_s] and self.y < scr_y - self.rect_y:
            self.y += self.speed * dt

        if self.keys[pg.K_a] and self.x > 0:
            self.x -= self.speed * dt

        if self.keys[pg.K_d] and self.x < scr_x - self.rect_x:
            self.x += self.speed * dt