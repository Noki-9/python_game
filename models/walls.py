from models.unit import Unit


class Wall(Unit):
    def __init__(self, x, y, rect_x, rect_y, health, texture):
        super().__init__("wall", x, y, rect_x, rect_y, health, 0, texture)
