from world.biome import Biome


class Segment:
    def __init__(self, gx: int, gy: int, biome: Biome, seed: int):
        self.gx = gx
        self.gy = gy
        self.biome = biome
        self.seed = seed
        self.local_map = None
        self.explored = False

    def get_local_map(self, neighbors=None):
        if self.local_map is None:
            from world.local_map import generate_local_map
            self.local_map = generate_local_map(self.biome, self.seed, neighbors)
            self.explored = True
        return self.local_map