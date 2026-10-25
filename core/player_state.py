class PlayerState:
    """Состояние игрока, общее для всех сцен."""

    def __init__(
        self, gx: int = 0, gy: int = 0, stamina: int = 30, max_stamina: int = 30
    ):
        self.gx = gx
        self.gy = gy
        self.stamina = stamina
        self.max_stamina = max_stamina

    def can_move(self, cost: int = 1) -> bool:
        return self.stamina >= cost

    def spend(self, cost: int = 1) -> bool:
        if not self.can_move(cost):
            return False
        self.stamina -= cost
        return True

    def restore(self):
        self.stamina = self.max_stamina

    @property
    def stamina_ratio(self) -> float:
        return self.stamina / self.max_stamina if self.max_stamina else 0.0
