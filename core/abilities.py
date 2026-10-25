from dataclasses import dataclass


@dataclass
class AbilityDef:
    ability_id: str
    name: str
    description: str
    key: str  # "Q" / "F" / "R"
    mana_cost: int
    cooldown: float
    damage_mult: float = 0.0
    range: int = 0
    aoe_radius: int = 0
    projectile_speed: int = 0
    projectile_count: int = 1
    projectile_spread: float = 0.0  # градусы
    heal: int = 0
    color: tuple = (255, 200, 100)

    @property
    def is_projectile(self):
        return self.projectile_speed > 0

    @property
    def is_aoe_at_cursor(self):
        return self.aoe_radius > 0 and self.range > 0 and not self.is_projectile

    @property
    def is_aoe_self(self):
        return self.aoe_radius > 0 and self.range == 0

    @property
    def is_single_target(self):
        return self.aoe_radius == 0 and not self.is_projectile


WARRIOR_ABILITIES = [
    AbilityDef(
        ability_id="w_q",
        name="Мощный удар",
        description="Удар по всем врагам вблизи",
        key="Q",
        mana_cost=10,
        cooldown=4.0,
        damage_mult=1.8,
        aoe_radius=70,
        color=(220, 120, 60),
    ),
    AbilityDef(
        ability_id="w_f",
        name="Боевой клич",
        description="Урон вокруг + лечит 15 HP",
        key="F",
        mana_cost=15,
        cooldown=6.0,
        damage_mult=1.2,
        aoe_radius=120,
        heal=15,
        color=(240, 200, 80),
    ),
    AbilityDef(
        ability_id="w_r",
        name="Вихрь",
        description="Сильный удар по всем вокруг",
        key="R",
        mana_cost=25,
        cooldown=10.0,
        damage_mult=2.5,
        aoe_radius=100,
        color=(255, 80, 80),
    ),
]

ROGUE_ABILITIES = [
    AbilityDef(
        ability_id="r_q",
        name="Смертельный удар",
        description="Удар по ближайшему x3.5",
        key="Q",
        mana_cost=10,
        cooldown=4.0,
        damage_mult=3.5,
        range=80,
        color=(180, 80, 220),
    ),
    AbilityDef(
        ability_id="r_f",
        name="Удар в спину",
        description="Точный удар по ближайшему",
        key="F",
        mana_cost=15,
        cooldown=5.0,
        damage_mult=2.5,
        range=80,
        color=(120, 180, 240),
    ),
    AbilityDef(
        ability_id="r_r",
        name="Веер клинков",
        description="Урон по всем врагам вокруг",
        key="R",
        mana_cost=20,
        cooldown=8.0,
        damage_mult=2.0,
        aoe_radius=90,
        color=(200, 140, 255),
    ),
]

MAGE_ABILITIES = [
    AbilityDef(
        ability_id="m_q",
        name="Огненный шар",
        description="Огненный снаряд, взрывается",
        key="Q",
        mana_cost=15,
        cooldown=2.0,
        damage_mult=2.0,
        range=350,
        projectile_speed=500,
        aoe_radius=40,
        color=(255, 120, 60),
    ),
    AbilityDef(
        ability_id="m_f",
        name="Ледяная новая",
        description="Урон всем вокруг",
        key="F",
        mana_cost=25,
        cooldown=6.0,
        damage_mult=1.5,
        aoe_radius=120,
        color=(120, 200, 255),
    ),
    AbilityDef(
        ability_id="m_r",
        name="Метеор",
        description="AoE в точке курсора",
        key="R",
        mana_cost=50,
        cooldown=15.0,
        damage_mult=3.0,
        range=400,
        aoe_radius=120,
        color=(255, 200, 100),
    ),
]

ARCHER_ABILITIES = [
    AbilityDef(
        ability_id="a_q",
        name="Тройной выстрел",
        description="Три стрелы веером",
        key="Q",
        mana_cost=12,
        cooldown=3.0,
        damage_mult=1.0,
        range=350,
        projectile_speed=700,
        projectile_count=3,
        projectile_spread=30.0,
        color=(100, 220, 120),
    ),
    AbilityDef(
        ability_id="a_f",
        name="Пронзающая стрела",
        description="Мощная стрела",
        key="F",
        mana_cost=18,
        cooldown=6.0,
        damage_mult=2.5,
        range=400,
        projectile_speed=900,
        color=(160, 240, 100),
    ),
    AbilityDef(
        ability_id="a_r",
        name="Дождь стрел",
        description="AoE в точке курсора",
        key="R",
        mana_cost=30,
        cooldown=12.0,
        damage_mult=2.0,
        range=400,
        aoe_radius=110,
        color=(120, 255, 180),
    ),
]


ABILITIES_BY_CLASS = {
    "warrior": WARRIOR_ABILITIES,
    "rogue": ROGUE_ABILITIES,
    "mage": MAGE_ABILITIES,
    "archer": ARCHER_ABILITIES,
}


def get_abilities_for_class(class_id):
    return ABILITIES_BY_CLASS.get(class_id, [])


def get_ability_for_key(class_id, key):
    for a in ABILITIES_BY_CLASS.get(class_id, []):
        if a.key == key:
            return a
    return None
