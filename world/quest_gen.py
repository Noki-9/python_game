import random

from world.biome import Biome
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


ENEMY_BIOMES = {
    "goblin": {Biome.FOREST, Biome.TUNDRA, Biome.PLAINS},
    "bandit": {Biome.FOREST, Biome.DESERT, Biome.PLAINS},
    "skeleton": {Biome.DESERT, Biome.TUNDRA, Biome.MOUNTAIN},
    "wolf": {Biome.FOREST},
    "bear": {Biome.FOREST},
    "troll": {Biome.MOUNTAIN},
}


def _find_nearest_segment(world, biomes, from_gx, from_gy):
    """Ближайший проходимый сегмент нужного биома."""
    best = None
    best_d = float("inf")
    for (gx, gy), seg in world.segments.items():
        if seg.biome not in biomes:
            continue
        if not seg.biome.walkable:
            continue
        d = (gx - from_gx) ** 2 + (gy - from_gy) ** 2
        if d < best_d:
            best_d = d
            best = (gx, gy)
    return best


def generate_quest(world, npc, seed, level=1, player_gx=0, player_gy=0):
    rng = random.Random(seed)
    choice = rng.choices(
        [
            QuestType.KILL,
            QuestType.CLEAR,
            QuestType.FETCH,
            QuestType.BOSS,
            QuestType.FREE,
            QuestType.EXPLORE,
            QuestType.ESCORT,
        ],
        weights=[34, 20, 20, 8, 8, 6, 4],
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
                target_gx=poi.gx,
                target_gy=poi.gy,
            )

    if choice == QuestType.BOSS:
        boss_id, boss_name = rng.choice(BOSS_TARGETS)
        obj = QuestObjective(
            description=f"Убить {boss_name}",
            target_id=boss_id,
            required=1,
        )
        biomes = ENEMY_BIOMES.get(boss_id, {Biome.FOREST})
        target = _find_nearest_segment(world, biomes, player_gx, player_gy)
        tgx, tgy = target if target else (None, None)
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
            target_gx=tgx,
            target_gy=tgy,
        )

    if choice in (QuestType.FREE, QuestType.EXPLORE):
        candidates = [
            p
            for p in world.pois
            if p.poi_type.value == "quest_dungeon" and not p.cleared
        ]
        if not candidates:
            choice = QuestType.KILL
        else:
            poi = rng.choice(candidates)
            if choice == QuestType.FREE:
                title = f"Освобождение: {poi.name}"
                desc = (
                    f"В {poi.name} удерживают пленника. "
                    f"Проберись внутрь и освободи его."
                )
                qid = f"free_{poi.gx}_{poi.gy}"
                gold, xp = 100, 180
            else:
                title = f"Руины: {poi.name}"
                desc = (
                    f"В {poi.name} спрятан древний артефакт. "
                    f"Найди его в глубине локации."
                )
                qid = f"explore_{poi.gx}_{poi.gy}"
                gold, xp = 90, 160
            return Quest(
                quest_id=qid,
                title=title,
                description=desc,
                quest_type=choice,
                objective=QuestObjective(
                    description=desc,
                    target_id=poi.name,
                    required=1,
                ),
                reward_gold=gold,
                reward_xp=xp,
                giver_npc_id=npc.npc_id,
                giver_name=npc.name,
                target_gx=poi.gx,
                target_gy=poi.gy,
            )

    if choice == QuestType.ESCORT:
        candidates = [
            p
            for p in world.pois
            if p.poi_type.value in ("village", "starting_village")
            and (p.gx, p.gy) != (player_gx, player_gy)
            and not p.cleared
        ]
        if not candidates:
            choice = QuestType.KILL
        else:
            dest = min(
                candidates,
                key=lambda p: (p.gx - player_gx) ** 2
                + (p.gy - player_gy) ** 2,
            )
            return Quest(
                quest_id=f"escort_{dest.gx}_{dest.gy}",
                title=f"Сопровождение: {dest.name}",
                description=(
                    f"Проводи путника до {dest.name}. "
                    f"Дойди до поселения вместе с ним."
                ),
                quest_type=QuestType.ESCORT,
                objective=QuestObjective(
                    description=f"Довести путника до {dest.name}",
                    target_id=dest.name,
                    required=1,
                ),
                reward_gold=70,
                reward_xp=140,
                giver_npc_id=npc.npc_id,
                giver_name=npc.name,
                target_gx=dest.gx,
                target_gy=dest.gy,
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
            target_gx=None,
            target_gy=None,
        )

    # KILL — по умолчанию
    enemy_id, enemy_name = rng.choice(KILL_TARGETS)
    count = rng.randint(3, 6) + level // 2
    obj = QuestObjective(
        description=f"Убить {count} {enemy_name}",
        target_id=enemy_id,
        required=count,
    )
    biomes = ENEMY_BIOMES.get(enemy_id, {Biome.PLAINS, Biome.FOREST})
    target = _find_nearest_segment(world, biomes, player_gx, player_gy)
    tgx, tgy = target if target else (None, None)
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
        target_gx=tgx,
        target_gy=tgy,
    )


def make_story_quests(world):
    quests = []
    quests.append(
        Quest(
            quest_id="story_act1",
            title="Акт I: Первые шаги",
            description=("Зачисти два квестовых данжа, чтобы доказать свою силу."),
            quest_type=QuestType.CLEAR,
            objective=QuestObjective(
                description="Зачистить данжи",
                target_id="__any_quest__",
                required=2,
            ),
            reward_gold=200,
            reward_xp=500,
            giver_name="Судьба",
        )
    )
    return quests
