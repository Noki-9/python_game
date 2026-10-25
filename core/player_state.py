from core.classes import CLASSES
from core.skills import ALL_SKILLS
from models.item import Item, ItemType


class PlayerState:
    def __init__(self, gx=0, gy=0, stamina=30, max_stamina=30, class_id="warrior"):
        self.gx = gx
        self.gy = gy
        self.stamina = stamina
        self.max_stamina = max_stamina

        self.class_id = class_id
        self.class_def = CLASSES[class_id]

        self.base_strength = self.class_def.base_strength
        self.base_agility = self.class_def.base_agility
        self.base_intelligence = self.class_def.base_intelligence
        self.base_endurance = self.class_def.base_endurance

        self.stat_points = 0

        self.level = 1
        self.xp = 0
        self.xp_to_next = 100
        self.gold = 0

        self.reputation = 0
        self.active_quests = []

        self.inventory: list[Item] = []
        from models.item import EQUIP_SLOTS

        self.equipment: dict[ItemType, Item | None] = {
            slot: None for slot in EQUIP_SLOTS
        }

        self.unlocked_skills: set[str] = set()
        self.skill_points = 0

        from world.item_generator import starting_equipment

        for item in starting_equipment(class_id):
            self.inventory.append(item)
            self.equip(item)

        self.hp = self.max_hp

    # ... (все остальные методы из предыдущей версии — без изменений) ...

    @property
    def bonus_stats(self):
        s = {
            "strength": 0,
            "agility": 0,
            "intelligence": 0,
            "endurance": 0,
            "hp": 0,
            "attack": 0,
            "crit": 0.0,
            "defense": 0,
            "move_stamina": 0,
        }
        for item in self.equipment.values():
            if item is None:
                continue
            s["strength"] += item.bonus_strength
            s["agility"] += item.bonus_agility
            s["intelligence"] += item.bonus_intelligence
            s["endurance"] += item.bonus_endurance
            s["hp"] += item.bonus_hp
            s["attack"] += item.bonus_attack
            s["crit"] += item.bonus_crit
            s["defense"] += item.bonus_defense
        for skill_id in self.unlocked_skills:
            node = self._find_skill(skill_id)
            if not node:
                continue
            eff = node.effect
            s["strength"] += eff.strength
            s["agility"] += eff.agility
            s["intelligence"] += eff.intelligence
            s["endurance"] += eff.endurance
            s["hp"] += eff.hp
            s["attack"] += eff.attack
            s["crit"] += eff.crit
            s["defense"] += eff.defense
            s["move_stamina"] += eff.move_stamina
        return s

    def _find_skill(self, skill_id):
        for node in ALL_SKILLS.get(self.class_id, []):
            if node.skill_id == skill_id:
                return node
        return None

    @property
    def total_strength(self):
        return self.base_strength + self.bonus_stats["strength"]

    @property
    def total_agility(self):
        return self.base_agility + self.bonus_stats["agility"]

    @property
    def total_intelligence(self):
        return self.base_intelligence + self.bonus_stats["intelligence"]

    @property
    def total_endurance(self):
        return self.base_endurance + self.bonus_stats["endurance"]

    @property
    def max_hp(self):
        return (
            self.class_def.base_hp + self.total_endurance * 5 + self.bonus_stats["hp"]
        )

    @property
    def attack_damage(self):
        return (
            self.class_def.base_attack_damage
            + self.total_strength
            + self.bonus_stats["attack"]
        )

    @property
    def attack_range(self):
        return self.class_def.attack_range

    @property
    def attack_cooldown(self):
        return self.class_def.attack_cooldown

    @property
    def crit_chance(self):
        return 0.05 + self.total_agility * 0.005 + self.bonus_stats["crit"]

    @property
    def crit_multiplier(self):
        return 1.5 + self.total_agility * 0.01

    @property
    def defense(self):
        return self.bonus_stats["defense"]

    @property
    def stamina_ratio(self):
        return self.stamina / self.max_stamina if self.max_stamina else 0.0

    @property
    def hp_ratio(self):
        return self.hp / self.max_hp if self.max_hp else 0.0

    def can_move(self, cost=1):
        return self.stamina >= cost

    def spend(self, cost=1):
        if not self.can_move(cost):
            return False
        self.stamina -= cost
        return True

    def restore(self):
        self.stamina = self.max_stamina

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def take_damage(self, amount):
        reduced = max(1, amount - self.defense)
        self.hp = max(0, self.hp - reduced)
        return self.hp <= 0

    def add_gold(self, amount):
        self.gold += max(0, amount)

    def add_xp(self, amount):
        self.xp += max(0, amount)
        leveled = 0
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(self.xp_to_next * 1.5)
            self.stat_points += 2
            self.skill_points += 1
            self.hp = self.max_hp
            leveled += 1
        return leveled

    def spend_stat_point(self, stat_name):
        if self.stat_points <= 0:
            return False
        if stat_name == "strength":
            self.base_strength += 1
        elif stat_name == "agility":
            self.base_agility += 1
        elif stat_name == "intelligence":
            self.base_intelligence += 1
        elif stat_name == "endurance":
            self.base_endurance += 1
        else:
            return False
        self.stat_points -= 1
        return True

    def can_unlock_skill(self, node):
        if node.skill_id in self.unlocked_skills:
            return False
        if self.skill_points < node.cost:
            return False
        if self.level < node.level_required:
            return False
        for req in node.requires:
            if req not in self.unlocked_skills:
                return False
        return True

    def unlock_skill(self, node):
        if not self.can_unlock_skill(node):
            return False
        self.unlocked_skills.add(node.skill_id)
        self.skill_points -= node.cost
        return True

    def add_item(self, item: Item):
        if item.is_stackable:
            for existing in self.inventory:
                if existing.item_id == item.item_id and existing.is_stackable:
                    existing.count += item.count
                    return
        self.inventory.append(item)

    def equip(self, item: Item):
        if not item.is_equipment:
            return False
        if item not in self.inventory:
            return False
        current = self.equipment.get(item.item_type)
        self.inventory.remove(item)
        if current is not None:
            self.inventory.append(current)
        self.equipment[item.item_type] = item
        return True

    def unequip(self, slot_type):
        item = self.equipment.get(slot_type)
        if item is None:
            return False
        self.equipment[slot_type] = None
        self.inventory.append(item)
        return True
