class PlayerState:
    """Состояние игрока, общее для всех сцен."""

    def __init__(
        self, gx: int = 0, gy: int = 0, stamina: int = 30, max_stamina: int = 30
    ):
        self.gx = gx
        self.gy = gy
        self.stamina = stamina
        self.max_stamina = max_stamina

        # --- Бой ---
        self.hp = 100
        self.max_hp = 100
        self.attack_damage = 12
        self.attack_range = 48
        self.attack_cooldown = 0.45

        # --- Прогресс ---
        self.level = 1
        self.xp = 0
        self.xp_to_next = 100
        self.gold = 0
        self.inventory = {}

    # --- Выносливость ---
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

    # --- HP ---
    @property
    def hp_ratio(self) -> float:
        return self.hp / self.max_hp if self.max_hp else 0.0

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def take_damage(self, amount):
        self.hp = max(0, self.hp - amount)
        return self.hp <= 0

    # --- Прогресс ---
    def add_gold(self, amount: int):
        self.gold += max(0, amount)

    def add_xp(self, amount: int):
        self.xp += max(0, amount)
        leveled = False
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(self.xp_to_next * 1.5)
            self.max_hp += 15
            self.hp = self.max_hp
            self.attack_damage += 2
            leveled = True
        return leveled

    def add_item(self, item_id: str, count: int = 1):
        self.inventory[item_id] = self.inventory.get(item_id, 0) + count
