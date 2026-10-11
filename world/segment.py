from world.biome import Biome


class Segment:
    def __init__(self, gx: int, gy: int, biome: Biome, seed: int):
        self.gx = gx                # координаты в глобальной сетке
        self.gy = gy
        self.biome = biome
        self.seed = seed            # уникальный сид для локальной карты
        self.local_map = None       # ленивая генерация
        self.explored = False

    def get_local_map(self):
        if self.local_map is None:
            from world.local_map import generate_local_map
            self.local_map = generate_local_map(self.biome, self.seed)
            self.explored = True
        return self.local_map