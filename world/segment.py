from world.location_type import LocationType


class Segment:
    def __init__(self, gx, gy, biome, seed, location_type=None, poi=None):
        self.gx = gx
        self.gy = gy
        self.biome = biome
        self.seed = seed
        self.local_map = None
        self.explored = False
        self.cleared = False
        self.location_type = location_type or LocationType.WILD
        self.poi = poi

    def get_local_map(self, neighbors=None, player_state=None):
        if self.local_map is None:
            from world.local_map import generate_local_map

            self.local_map = generate_local_map(
                self.biome,
                self.seed,
                neighbors=neighbors,
                location_type=self.location_type,
                player_state=player_state,
            )
        return self.local_map

    def reset_if_unfinished(self):
        """Квест-локация без выполнения цели сбрасывается при выходе."""
        if self.location_type.is_quest and not self.cleared:
            self.local_map = None
