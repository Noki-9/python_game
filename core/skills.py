from dataclasses import dataclass, field


@dataclass
class SkillEffect:
    strength: int = 0
    agility: int = 0
    intelligence: int = 0
    endurance: int = 0
    hp: int = 0
    attack: int = 0
    crit: float = 0.0
    defense: int = 0
    move_stamina: int = 0


@dataclass
class SkillNode:
    skill_id: str
    name: str
    description: str
    branch: str
    level_required: int
    cost: int
    requires: list[str] = field(default_factory=list)
    effect: SkillEffect = field(default_factory=SkillEffect)


WARRIOR_SKILLS = [
    SkillNode(
        "w_def1", "Стальная кожа", "+20 HP", "defense", 1, 1, effect=SkillEffect(hp=20)
    ),
    SkillNode(
        "w_def2",
        "Стойкость",
        "+2 Выносливость",
        "defense",
        3,
        1,
        requires=["w_def1"],
        effect=SkillEffect(endurance=2),
    ),
    SkillNode(
        "w_def3",
        "Щит-бастион",
        "+5 Защита",
        "defense",
        5,
        1,
        requires=["w_def2"],
        effect=SkillEffect(defense=5),
    ),
    SkillNode(
        "w_rage1", "Берсерк", "+3 Атака", "rage", 1, 1, effect=SkillEffect(attack=3)
    ),
    SkillNode(
        "w_rage2",
        "Кровожадность",
        "+10% Крит",
        "rage",
        3,
        1,
        requires=["w_rage1"],
        effect=SkillEffect(crit=0.10),
    ),
    SkillNode(
        "w_rage3",
        "Ярость битвы",
        "+5 Атака",
        "rage",
        5,
        1,
        requires=["w_rage2"],
        effect=SkillEffect(attack=5),
    ),
    SkillNode(
        "w_str1",
        "Могучие руки",
        "+2 Сила",
        "strength",
        1,
        1,
        effect=SkillEffect(strength=2),
    ),
    SkillNode(
        "w_str2",
        "Железный хват",
        "+30 HP",
        "strength",
        4,
        1,
        requires=["w_str1"],
        effect=SkillEffect(hp=30),
    ),
]

ROGUE_SKILLS = [
    SkillNode(
        "r_agi1",
        "Кошачья грация",
        "+2 Ловкость",
        "agility",
        1,
        1,
        effect=SkillEffect(agility=2),
    ),
    SkillNode(
        "r_agi2",
        "Увёртливость",
        "+15 HP",
        "agility",
        3,
        1,
        requires=["r_agi1"],
        effect=SkillEffect(hp=15),
    ),
    SkillNode(
        "r_agi3",
        "Тень",
        "+5% Крит",
        "agility",
        5,
        1,
        requires=["r_agi2"],
        effect=SkillEffect(crit=0.05),
    ),
    SkillNode(
        "r_crit1",
        "Смертельный удар",
        "+10% Крит",
        "crit",
        1,
        1,
        effect=SkillEffect(crit=0.10),
    ),
    SkillNode(
        "r_crit2",
        "Кровавый клинок",
        "+3 Атака",
        "crit",
        3,
        1,
        requires=["r_crit1"],
        effect=SkillEffect(attack=3),
    ),
    SkillNode(
        "r_crit3",
        "Мастер клинка",
        "+15% Крит",
        "crit",
        5,
        1,
        requires=["r_crit2"],
        effect=SkillEffect(crit=0.15),
    ),
    SkillNode(
        "r_end1",
        "Выносливый",
        "+3 Выносливость",
        "endurance",
        1,
        1,
        effect=SkillEffect(endurance=3),
    ),
    SkillNode(
        "r_end2",
        "Быстрые ноги",
        "+10 к макс. шагам",
        "endurance",
        4,
        1,
        requires=["r_end1"],
        effect=SkillEffect(move_stamina=10),
    ),
]

MAGE_SKILLS = [
    SkillNode(
        "m_int1",
        "Ученик магии",
        "+2 Интеллект",
        "intelligence",
        1,
        1,
        effect=SkillEffect(intelligence=2),
    ),
    SkillNode(
        "m_int2",
        "Мудрец",
        "+2 Интеллект",
        "intelligence",
        3,
        1,
        requires=["m_int1"],
        effect=SkillEffect(intelligence=2),
    ),
    SkillNode(
        "m_int3",
        "Архимаг",
        "+3 Интеллект",
        "intelligence",
        5,
        1,
        requires=["m_int2"],
        effect=SkillEffect(intelligence=3),
    ),
    SkillNode(
        "m_pow1", "Сила чар", "+4 Атака", "power", 1, 1, effect=SkillEffect(attack=4)
    ),
    SkillNode(
        "m_pow2",
        "Огненный шар",
        "+6 Атака",
        "power",
        3,
        1,
        requires=["m_pow1"],
        effect=SkillEffect(attack=6),
    ),
    SkillNode(
        "m_pow3",
        "Метеор",
        "+8 Атака",
        "power",
        5,
        1,
        requires=["m_pow2"],
        effect=SkillEffect(attack=8),
    ),
    SkillNode(
        "m_def1", "Магический щит", "+30 HP", "shield", 1, 1, effect=SkillEffect(hp=30)
    ),
    SkillNode(
        "m_def2",
        "Барьер",
        "+5 Защита",
        "shield",
        4,
        1,
        requires=["m_def1"],
        effect=SkillEffect(defense=5),
    ),
]

ARCHER_SKILLS = [
    SkillNode(
        "a_agi1",
        "Зоркий глаз",
        "+2 Ловкость",
        "agility",
        1,
        1,
        effect=SkillEffect(agility=2),
    ),
    SkillNode(
        "a_agi2",
        "Быстрая рука",
        "+10% Крит",
        "agility",
        3,
        1,
        requires=["a_agi1"],
        effect=SkillEffect(crit=0.10),
    ),
    SkillNode(
        "a_agi3",
        "Соколиный взор",
        "+3 Ловкость",
        "agility",
        5,
        1,
        requires=["a_agi2"],
        effect=SkillEffect(agility=3),
    ),
    SkillNode(
        "a_pow1",
        "Точный выстрел",
        "+4 Атака",
        "power",
        1,
        1,
        effect=SkillEffect(attack=4),
    ),
    SkillNode(
        "a_pow2",
        "Пронзающая стрела",
        "+6 Атака",
        "power",
        3,
        1,
        requires=["a_pow1"],
        effect=SkillEffect(attack=6),
    ),
    SkillNode(
        "a_pow3",
        "Смертельный залп",
        "+8 Атака",
        "power",
        5,
        1,
        requires=["a_pow2"],
        effect=SkillEffect(attack=8),
    ),
    SkillNode(
        "a_end1",
        "Выносливый стрелок",
        "+2 Выносливость",
        "endurance",
        1,
        1,
        effect=SkillEffect(endurance=2),
    ),
    SkillNode(
        "a_end2",
        "Долгий поход",
        "+8 к макс. шагам",
        "endurance",
        4,
        1,
        requires=["a_end1"],
        effect=SkillEffect(move_stamina=8),
    ),
]


ALL_SKILLS = {
    "warrior": WARRIOR_SKILLS,
    "rogue": ROGUE_SKILLS,
    "mage": MAGE_SKILLS,
    "archer": ARCHER_SKILLS,
}
