import random

from world.quest import Quest, QuestObjective, QuestType

KILL_TARGETS = [
    ("goblin", "гоблинов"),
    ("bandit", "разбойников"),
    ("skeleton", "скелетов"),
    ("wolf", "волков"),
    ("bear", "медведей"),
]

FETCH_TARGETS = [
    ("leather", "кожи"),
    ("meat", "мяса"),
    ("bone", "костей"),
    ("iron_ore", "железной руды"),
]

BOSS_TARGETS = [
    ("troll", "тролля"),
    ("bear", "медведя"),
]


def generate_quest(world, npc, seed, level=1):
    rng = random.Random(seed)
    choice = rng.choices(
        [QuestType.KILL, QuestType.CLEAR, QuestType.FETCH, QuestType.BOSS],
        weights=[40, 25, 25, 10],
        k=1,
    )[0]

    if choice == QuestType.CLEAR:
        candidates = [
            p
            for p in world.pois
            if p.poi_type.value == "quest_dungeon" and not p.cleared
        ]
        if not candidates:
            choice = QuestType.KILL
        else:
            poi = rng.choice(candidates)
            obj = QuestObjective(
                description=f"Зачистить {poi.name}",
                target_id=poi.name,
                required=1,
            )
            return Quest(
                quest_id=f"clear_{poi.gx}_{poi.gy}",
                title=f"Зачистка: {poi.name}",
                description=(
                    f"В {poi.name} засели тёмные силы. "
                    f"Зачисти локацию и получи награду."
                ),
                quest_type=QuestType.CLEAR,
                objective=obj,
                reward_gold=80,
                reward_xp=150,
                giver_npc_id=npc.npc_id,
                giver_name=npc.name,
            )

    if choice == QuestType.BOSS:
        boss_id, boss_name = rng.choice(BOSS_TARGETS)
        obj = QuestObjective(
            description=f"Убить {boss_name}",
            target_id=boss_id,
            required=1,
        )
        return Quest(
            quest_id=f"boss_{boss_id}_{rng.randint(0, 999999)}",
            title="Охота на босса",
            description=f"В окрестностях завёлся {boss_name}. Убей его.",
            quest_type=QuestType.BOSS,
            objective=obj,
            reward_gold=120,
            reward_xp=200,
            giver_npc_id=npc.npc_id,
            giver_name=npc.name,
        )

    if choice == QuestType.FETCH:
        item_id, item_name = rng.choice(FETCH_TARGETS)
        count = rng.randint(2, 5)
        obj = QuestObjective(
            description=f"Принести {count} {item_name}",
            target_id=item_id,
            required=count,
        )
        return Quest(
            quest_id=f"fetch_{item_id}_{rng.randint(0, 999999)}",
            title=f"Поставка: {item_name}",
            description=f"Нужно {count} {item_name}. Принеси — отблагодарю.",
            quest_type=QuestType.FETCH,
            objective=obj,
            reward_gold=25 + count * 8,
            reward_xp=40 + count * 12,
            giver_npc_id=npc.npc_id,
            giver_name=npc.name,
            consume_items=True,
        )

    # KILL — по умолчанию
    enemy_id, enemy_name = rng.choice(KILL_TARGETS)
    count = rng.randint(3, 6) + level // 2
    obj = QuestObjective(
        description=f"Убить {count} {enemy_name}",
        target_id=enemy_id,
        required=count,
    )
    return Quest(
        quest_id=f"kill_{enemy_id}_{rng.randint(0, 999999)}",
        title=f"Охота: {enemy_name}",
        description=f"Избавь окрестности от {enemy_name}.",
        quest_type=QuestType.KILL,
        objective=obj,
        reward_gold=30 + count * 5,
        reward_xp=50 + count * 10,
        giver_npc_id=npc.npc_id,
        giver_name=npc.name,
    )


def make_story_quests(world):
    """Сюжетные квесты (3 акта), создаются при старте игры."""
    from world.quest import Quest, QuestObjective, QuestType

    quests = []

    # Акт 1: зачистить 2 квест-данжа
    quests.append(
        Quest(
            quest_id="story_act1",
            title="Акт I: Первые шаги",
            description=("Зачисти два квестовых данжа, чтобы доказать свою силу."),
            quest_type=QuestType.CLEAR,
            objective=QuestObjective(
                description="Зачистить данжи",
                target_id="__any_quest__",  # см. ниже
                required=2,
            ),
            reward_gold=200,
            reward_xp=500,
            giver_name="Судьба",
        )
    )
    return quests
