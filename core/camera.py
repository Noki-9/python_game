

class Camera:
    def __init__(self, view_w: int, view_h: int):
        self.x = 0
        self.y = 0
        self.view_w = view_w
        self.view_h = view_h

    def follow(self, target, map_w_px: int, map_h_px: int):
        """Центрирует камеру на цели, не выходя за границы карты."""
        self.x = target.x + target.rect_x / 2 - self.view_w / 2
        self.y = target.y + target.rect_y / 2 - self.view_h / 2

        # не выходить за края
        self.x = max(0, min(self.x, map_w_px - self.view_w))
        self.y = max(0, min(self.y, map_h_px - self.view_h))

        # если карта меньше экрана — прижимаем к 0
        if map_w_px < self.view_w: self.x = (map_w_px - self.view_w) / 2
        if map_h_px < self.view_h: self.y = (map_h_px - self.view_h) / 2

    def apply(self, x: float, y: float) -> tuple[int, int]:
        """Мировые координаты → экранные."""
        return int(x - self.x), int(y - self.y)

    def visible_tile_range(self, tile_size: int) -> tuple[int, int, int, int]:
        """Возвращает (tx0, ty0, tx1, ty1) — диапазон видимых тайлов."""
        tx0 = max(0, int(self.x // tile_size) - 1)
        ty0 = max(0, int(self.y // tile_size) - 1)
        tx1 = int((self.x + self.view_w) // tile_size) + 1
        ty1 = int((self.y + self.view_h) // tile_size) + 1
        return tx0, ty0, tx1, ty1