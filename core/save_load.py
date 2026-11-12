"""Сохранение и загрузка прогресса (ТЗ 13).

Используется стандартный sqlite3: одна таблица со слотами, внутри — JSON.
Мир детерминирован от seed, поэтому сохраняются только изменяемые флаги
(explored / cleared / poi.cleared) и состояние игрока.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from core.player_state import PlayerState
from models.item import Item, ItemType, Rarity
from world.quest import Quest, QuestObjective, QuestStatus, QuestType

DEFAULT_DB = Path("saves") / "save.db"


def _ensure_db(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS saves ("
        "slot TEXT PRIMARY KEY, data TEXT NOT NULL, updated TEXT NOT NULL)"
    )
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Предметы
# ---------------------------------------------------------------------------
def _item_to_dict(item: Item) -> dict:
    return {
        "item_id": item.item_id,
        "name": item.name,
        "item_type": item.item_type.value,
        "rarity": item.rarity.name,
        "value": item.value,
        "count": item.count,
        "bonus_strength": item.bonus_strength,
        "bonus_agility": item.bonus_agility,
        "bonus_intelligence": item.bonus_intelligence,
        "bonus_endurance": item.bonus_endurance,
        "bonus_hp": item.bonus_hp,
        "bonus_attack": item.bonus_attack,
        "bonus_crit": item.bonus_crit,
        "bonus_defense": item.bonus_defense,
        "heal_amount": item.heal_amount,
        "icon_color": list(item.icon_color),
    }


def _item_from_dict(data: dict) -> Item:
    return Item(
        item_id=data["item_id"],
        name=data["name"],
        item_type=ItemType(data["item_type"]),
        rarity=Rarity[data.get("rarity", "COMMON")],
        value=data.get("value", 0),
        count=data.get("count", 1),
        bonus_strength=data.get("bonus_strength", 0),
        bonus_agility=data.get("bonus_agility", 0),
        bonus_intelligence=data.get("bonus_intelligence", 0),
        bonus_endurance=data.get("bonus_endurance", 0),
        bonus_hp=data.get("bonus_hp", 0),
        bonus_attack=data.get("bonus_attack", 0),
        bonus_crit=data.get("bonus_crit", 0.0),
        bonus_defense=data.get("bonus_defense", 0),
        heal_amount=data.get("heal_amount", 0),
        icon_color=tuple(data.get("icon_color", (200, 200, 200))),
    )


# ---------------------------------------------------------------------------
# Квесты
# ---------------------------------------------------------------------------
def _quest_to_dict(quest: Quest) -> dict:
    obj = quest.objective
    return {
        "quest_id": quest.quest_id,
        "title": quest.title,
        "description": quest.description,
        "quest_type": quest.quest_type.value,
        "objective": {
            "description": obj.description,
            "target_id": obj.target_id,
            "required": obj.required,
            "current": obj.current,
        },
        "reward_gold": quest.reward_gold,
        "reward_xp": quest.reward_xp,
        "status": quest.status.value,
        "giver_npc_id": quest.giver_npc_id,
        "giver_name": quest.giver_name,
        "consume_items": quest.consume_items,
        "target_gx": quest.target_gx,
        "target_gy": quest.target_gy,
        "giver_gx": quest.giver_gx,
        "giver_gy": quest.giver_gy,
    }


def _quest_from_dict(data: dict) -> Quest:
    obj = data["objective"]
    return Quest(
        quest_id=data["quest_id"],
        title=data["title"],
        description=data["description"],
        quest_type=QuestType(data["quest_type"]),
        objective=QuestObjective(
            description=obj["description"],
            target_id=obj["target_id"],
            required=obj["required"],
            current=obj.get("current", 0),
        ),
        reward_gold=data.get("reward_gold", 0),
        reward_xp=data.get("reward_xp", 0),
        status=QuestStatus(data.get("status", "active")),
        giver_npc_id=data.get("giver_npc_id"),
        giver_name=data.get("giver_name"),
        consume_items=data.get("consume_items", False),
        target_gx=data.get("target_gx"),
        target_gy=data.get("target_gy"),
        giver_gx=data.get("giver_gx"),
        giver_gy=data.get("giver_gy"),
    )


# ---------------------------------------------------------------------------
# Состояние игрока
# ---------------------------------------------------------------------------
def _state_to_dict(state: PlayerState) -> dict:
    return {
        "gx": state.gx,
        "gy": state.gy,
        "class_id": state.class_id,
        "level": state.level,
        "xp": state.xp,
        "xp_to_next": state.xp_to_next,
        "gold": state.gold,
        "reputation": state.reputation,
        "factions": dict(state.factions),
        "hp": state.hp,
        "mana": state.mana,
        "stamina": state.stamina,
        "max_stamina": state.max_stamina,
        "base_strength": state.base_strength,
        "base_agility": state.base_agility,
        "base_intelligence": state.base_intelligence,
        "base_endurance": state.base_endurance,
        "stat_points": state.stat_points,
        "skill_points": state.skill_points,
        "unlocked_skills": sorted(state.unlocked_skills),
        "inventory": [_item_to_dict(i) for i in state.inventory],
        "equipment": {
            slot.value: (_item_to_dict(item) if item is not None else None)
            for slot, item in state.equipment.items()
        },
        "quests": [_quest_to_dict(q) for q in state.quest_log.quests],
        "waypoint": list(state.waypoint) if state.waypoint else None,
        "visited_villages": [list(v) for v in sorted(state.visited_villages)],
        "last_village": list(state.last_village) if state.last_village else None,
    }


def _state_from_dict(data: dict) -> PlayerState:
    state = PlayerState(
        gx=data.get("gx", 0),
        gy=data.get("gy", 0),
        class_id=data.get("class_id", "warrior"),
    )
    state.level = data.get("level", 1)
    state.xp = data.get("xp", 0)
    state.xp_to_next = data.get("xp_to_next", 100)
    state.gold = data.get("gold", 0)
    state.reputation = data.get("reputation", 0)
    state.factions.update(data.get("factions", {}))
    state.max_stamina = data.get("max_stamina", state.max_stamina)
    state.stamina = data.get("stamina", state.max_stamina)
    state.base_strength = data.get("base_strength", state.base_strength)
    state.base_agility = data.get("base_agility", state.base_agility)
    state.base_intelligence = data.get("base_intelligence", state.base_intelligence)
    state.base_endurance = data.get("base_endurance", state.base_endurance)
    state.stat_points = data.get("stat_points", 0)
    state.skill_points = data.get("skill_points", 0)
    state.unlocked_skills = set(data.get("unlocked_skills", []))
    state.hp = data.get("hp", state.max_hp)
    state.mana = float(data.get("mana", state.max_mana))

    state.inventory = [_item_from_dict(d) for d in data.get("inventory", [])]
    state.equipment = {slot: None for slot in state.equipment}
    for slot_name, item_data in data.get("equipment", {}).items():
        try:
            slot = ItemType(slot_name)
        except ValueError:
            continue
        state.equipment[slot] = (
            _item_from_dict(item_data) if item_data is not None else None
        )

    state.quest_log.quests = [
        _quest_from_dict(d) for d in data.get("quests", [])
    ]
    waypoint = data.get("waypoint")
    state.waypoint = tuple(waypoint) if waypoint else None
    state.visited_villages = {
        tuple(v) for v in data.get("visited_villages", [])
    }
    last = data.get("last_village")
    state.last_village = tuple(last) if last else None
    return state


# ---------------------------------------------------------------------------
# Мир
# ---------------------------------------------------------------------------
def _world_to_dict(world) -> dict:
    explored = []
    cleared = []
    poi_cleared = []
    poi_destroyed = []
    village_states = []
    opened_props = []
    depleted_resources = []
    for (gx, gy), seg in world.segments.items():
        if seg.explored:
            explored.append([gx, gy])
        if seg.cleared:
            cleared.append([gx, gy])
        if seg.poi is not None and seg.poi.cleared:
            poi_cleared.append([gx, gy])
        if seg.poi is not None and seg.poi.destroyed:
            poi_destroyed.append([gx, gy])
        if getattr(seg, "village_state", "peaceful") != "peaceful":
            village_states.append([gx, gy, seg.village_state])
        if seg.opened_props:
            opened_props.append(
                [gx, gy, [[kind, tx, ty] for kind, tx, ty in seg.opened_props]]
            )
        if getattr(seg, "depleted_resources", None):
            depleted_resources.append(
                [gx, gy, [[tx, ty] for tx, ty in seg.depleted_resources]]
            )
    return {
        "seed": world.seed,
        "width": world.width,
        "height": world.height,
        "start_gx": world.start_gx,
        "start_gy": world.start_gy,
        "explored": explored,
        "cleared": cleared,
        "poi_cleared": poi_cleared,
        "poi_destroyed": poi_destroyed,
        "village_states": village_states,
        "opened_props": opened_props,
        "depleted_resources": depleted_resources,
    }


def _restore_world(data: dict):
    from world.world_map import WorldMap

    world = WorldMap(
        width=data.get("width", 150),
        height=data.get("height", 120),
        seed=data.get("seed", 42),
    )
    world.start_gx = data.get("start_gx", world.start_gx)
    world.start_gy = data.get("start_gy", world.start_gy)
    for gx, gy in data.get("explored", []):
        seg = world.get(gx, gy)
        if seg:
            seg.explored = True
    for gx, gy in data.get("cleared", []):
        seg = world.get(gx, gy)
        if seg:
            seg.cleared = True
    for gx, gy in data.get("poi_cleared", []):
        seg = world.get(gx, gy)
        if seg and seg.poi:
            seg.poi.cleared = True
    for gx, gy in data.get("poi_destroyed", []):
        seg = world.get(gx, gy)
        if seg:
            seg.village_state = "destroyed"
            if seg.poi:
                seg.poi.destroyed = True
    for gx, gy, village_state in data.get("village_states", []):
        seg = world.get(gx, gy)
        if seg:
            seg.village_state = village_state
    for gx, gy, props in data.get("opened_props", []):
        seg = world.get(gx, gy)
        if seg:
            seg.opened_props = {(kind, tx, ty) for kind, tx, ty in props}
    for gx, gy, cells in data.get("depleted_resources", []):
        seg = world.get(gx, gy)
        if seg:
            seg.depleted_resources = {(tx, ty) for tx, ty in cells}
    return world


# ---------------------------------------------------------------------------
# Публичный API
# ---------------------------------------------------------------------------
def save_game(world, state, slot="auto", path=DEFAULT_DB):
    payload = {
        "version": 1,
        "world": _world_to_dict(world),
        "player": _state_to_dict(state),
    }
    conn = _ensure_db(path)
    try:
        conn.execute(
            "INSERT INTO saves(slot, data, updated) VALUES(?, ?, ?) "
            "ON CONFLICT(slot) DO UPDATE SET data=excluded.data, "
            "updated=excluded.updated",
            (
                slot,
                json.dumps(payload, ensure_ascii=False),
                datetime.now().isoformat(timespec="microseconds"),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return True


def has_save(slot="auto", path=DEFAULT_DB):
    path = Path(path)
    if not path.exists():
        return False
    conn = _ensure_db(path)
    try:
        row = conn.execute(
            "SELECT 1 FROM saves WHERE slot=?", (slot,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def latest_slot(path=DEFAULT_DB):
    """Возвращает слот с самой свежей записью (auto/manual) или None."""
    path = Path(path)
    if not path.exists():
        return None
    conn = _ensure_db(path)
    try:
        row = conn.execute(
            "SELECT slot FROM saves ORDER BY updated DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def load_game(slot="auto", path=DEFAULT_DB):
    path = Path(path)
    if not path.exists():
        return None
    conn = _ensure_db(path)
    try:
        row = conn.execute(
            "SELECT data FROM saves WHERE slot=?", (slot,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    payload = json.loads(row[0])
    world = _restore_world(payload["world"])
    state = _state_from_dict(payload["player"])
    return world, state
