from dataclasses import dataclass


@dataclass
class ClassDef:
    class_id: str
    name: str
    description: str
    base_hp: int
    base_strength: int
    base_agility: int
    base_intelligence: int
    base_endurance: int
    base_attack_damage: int
    attack_range: int
    attack_cooldown: float
    color: tuple
    max_mana: int
    mana_regen: float


CLASSES = {
    "warrior": ClassDef(
        "warrior",
        "Воин",
        "Тяжёлый боец ближнего боя. Много HP и урона.",
        base_hp=130,
        base_strength=8,
        base_agility=4,
        base_intelligence=3,
        base_endurance=7,
        base_attack_damage=14,
        attack_range=48,
        attack_cooldown=0.5,
        color=(200, 60, 60),
        max_mana=60,
        mana_regen=4.0,
    ),
    "rogue": ClassDef(
        "rogue",
        "Разбойник",
        "Быстрый боец с высоким шансом крита.",
        base_hp=90,
        base_strength=5,
        base_agility=8,
        base_intelligence=5,
        base_endurance=5,
        base_attack_damage=10,
        attack_range=48,
        attack_cooldown=0.35,
        color=(160, 80, 200),
        max_mana=80,
        mana_regen=5.0,
    ),
    "mage": ClassDef(
        "mage",
        "Маг",
        "Дальний бой. Магия и урон по площади.",
        base_hp=70,
        base_strength=3,
        base_agility=4,
        base_intelligence=9,
        base_endurance=4,
        base_attack_damage=8,
        attack_range=250,
        attack_cooldown=0.9,
        color=(80, 120, 240),
        max_mana=150,
        mana_regen=10.0,
    ),
    "archer": ClassDef(
        "archer",
        "Лучник",
        "Дальний бой. Точные выстрелы и криты.",
        base_hp=85,
        base_strength=4,
        base_agility=9,
        base_intelligence=5,
        base_endurance=5,
        base_attack_damage=11,
        attack_range=300,
        attack_cooldown=0.7,
        color=(80, 200, 100),
        max_mana=100,
        mana_regen=6.0,
    ),
}
