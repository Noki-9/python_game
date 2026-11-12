import random

from core.classes import CLASSES
from core.skills import ALL_SKILLS
from core.status_effects import StatusEffectSet
from models.item import EQUIP_SLOTS, Item, ItemType
from world.factions import FACTIONS
from world.quest import QuestLog


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
        # Отношение фракций: Корона / Вольные / Культ.
        self.factions = {faction_id: 0 for faction_id in FACTIONS}

        self.inventory: list[Item] = []
        self.equipment: dict[ItemType, Item | None] = {
            slot: None for slot in EQUIP_SLOTS
        }

        self.unlocked_skills: set[str] = set()
        self.skill_points = 0

        self.quest_log = QuestLog()
        self.waypoint = None

        # --- Мир и перемещение ---
        self.visited_villages: set[tuple[int, int]] = set()
        self.last_village: tuple[int, int] | None = None
        self.status = StatusEffectSet()
        self.stealth = False
        self.last_blocked = False

        # --- Мана и умения ---
        self.max_mana = self.class_def.max_mana
        self.mana_regen = self.class_def.mana_regen
        self.mana = float(self.max_mana)
        self.ability_cooldowns: dict[str, float] = {}

        from world.item_generator import starting_equipment

        for item in starting_equipment(class_id):
            self.inventory.append(item)
            self.equip(item)

        self.hp = self.max_hp

    # ---------- Derived ----------
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

    @property
    def mana_ratio(self):
        return self.mana / self.max_mana if self.max_mana else 0.0

    # ---------- Выносливость ----------
    def can_move(self, cost=1):
        return self.stamina >= cost

    def spend(self, cost=1):
        if not self.can_move(cost):
            return False
        self.stamina -= cost
        return True

    def restore(self):
        self.stamina = self.max_stamina

    @property
    def travel_penalty(self):
        """Тяжёлая броня/щит увеличивают стоимость шага по миру."""
        penalty = 0
        armor = self.equipment.get(ItemType.ARMOR)
        shield = self.equipment.get(ItemType.SHIELD)
        if armor is not None:
            penalty += 1
        if shield is not None:
            penalty += 1
        # Выносливость компенсирует вес.
        if self.total_endurance >= 10:
            penalty -= 1
        return max(0, penalty)

    def rest(self, full=False):
        """Отдых восстанавливает силы, а при full — ещё HP и ману."""
        self.stamina = self.max_stamina
        if full:
            self.hp = self.max_hp
            self.mana = float(self.max_mana)
        self.status.clear()

    def remember_village(self, gx, gy):
        self.visited_villages.add((int(gx), int(gy)))
        self.last_village = (int(gx), int(gy))

    # ---------- Фракции ----------
    def faction_standing(self, faction_id) -> int:
        return int(self.factions.get(faction_id, 0))

    def adjust_faction(self, faction_id, delta):
        if faction_id not in self.factions:
            return
        self.factions[faction_id] = max(
            -100, min(100, self.factions[faction_id] + int(delta))
        )

    def reputation_with(self, faction_id) -> int:
        """Общая репутация плюс отношение конкретной фракции."""
        return self.reputation + self.faction_standing(faction_id)

    # ---------- HP / Мана ----------
    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def take_damage(self, amount):
        reduced = max(1, amount - self.defense)
        self.last_blocked = False
        if self.class_id == "warrior":
            shield = self.equipment.get(ItemType.SHIELD)
            if shield is not None and random.random() < 0.25:
                reduced = max(1, reduced // 4)
                self.last_blocked = True
        self.hp = max(0, self.hp - reduced)
        return self.hp <= 0

    def tick_status(self, dt):
        """Тик статус-эффектов игрока. Возвращает True, если игрок погиб."""
        damage = self.status.tick(dt)
        if damage > 0:
            self.hp = max(0, self.hp - damage)
        return self.hp <= 0

    def regen_mana(self, dt):
        self.mana = min(float(self.max_mana), self.mana + self.mana_regen * dt)

    # ---------- Умения ----------
    def try_spend_ability(self, ability) -> bool:
        if self.ability_cooldowns.get(ability.ability_id, 0.0) > 0:
            return False
        if self.mana < ability.mana_cost:
            return False
        self.mana -= ability.mana_cost
        self.ability_cooldowns[ability.ability_id] = ability.cooldown
        return True

    def tick_ability_cooldowns(self, dt):
        for k in list(self.ability_cooldowns.keys()):
            if self.ability_cooldowns[k] > 0:
                self.ability_cooldowns[k] = max(0.0, self.ability_cooldowns[k] - dt)

    def get_cooldown_ratio(self, ability) -> float:
        """1.0 = готово, 0.0 = только что использовано."""
        cd = self.ability_cooldowns.get(ability.ability_id, 0.0)
        if cd <= 0:
            return 1.0
        return 1.0 - cd / ability.cooldown

    # ---------- Прогресс ----------
    def add_gold(self, amount):
        self.gold += max(0, amount)

    def add_xp(self, amount):
        self.xp += max(0, amount)
        leveled = 0
        while self.level < 30 and self.xp >= self.xp_to_next:
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

    # ---------- Навыки ----------
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

    # ---------- Инвентарь ----------
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

    # ---------- Квесты ----------
    def grant_quest_reward(self, quest):
        self.add_gold(quest.reward_gold)
        self.add_xp(quest.reward_xp)
        if quest.consume_items:
            quest.consume_required_items(self.inventory)
