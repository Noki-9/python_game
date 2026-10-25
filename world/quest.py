from dataclasses import dataclass
from enum import Enum


class QuestType(Enum):
    KILL = "kill"
    CLEAR = "clear"
    FETCH = "fetch"
    BOSS = "boss"
    STORY = "story"


class QuestStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QuestObjective:
    description: str
    target_id: str
    required: int
    current: int = 0

    @property
    def done(self):
        return self.current >= self.required

    @property
    def progress_str(self):
        return f"{min(self.current, self.required)}/{self.required}"


@dataclass
class Quest:
    quest_id: str
    title: str
    description: str
    quest_type: QuestType
    objective: QuestObjective
    reward_gold: int
    reward_xp: int
    status: QuestStatus = QuestStatus.ACTIVE
    giver_npc_id: str | None = None
    giver_name: str | None = None
    consume_items: bool = False
    target_gx: int | None = None
    target_gy: int | None = None

    def on_kill(self, enemy_id) -> bool:
        if self.status != QuestStatus.ACTIVE:
            return False
        if self.quest_type in (QuestType.KILL, QuestType.BOSS):
            if enemy_id == self.objective.target_id:
                self.objective.current += 1
                return self._try_complete()
        return False

    def sync_inventory(self, inventory) -> bool:
        if self.status != QuestStatus.ACTIVE:
            return False
        if self.quest_type != QuestType.FETCH:
            return False
        total = 0
        for item in inventory:
            if item.item_id == self.objective.target_id:
                total += item.count
        self.objective.current = min(total, self.objective.required)
        return self._try_complete()

    def on_location_cleared(self, location_name) -> bool:
        if self.status != QuestStatus.ACTIVE:
            return False
        if self.quest_type != QuestType.CLEAR:
            return False
        if location_name == self.objective.target_id:
            self.objective.current = self.objective.required
            return self._try_complete()
        return False

    def _try_complete(self) -> bool:
        if self.objective.done and self.status == QuestStatus.ACTIVE:
            self.status = QuestStatus.COMPLETED
            return True
        return False

    def consume_required_items(self, inventory):
        if not self.consume_items:
            return
        if self.quest_type != QuestType.FETCH:
            return
        remaining = self.objective.required
        to_remove = []
        for item in inventory:
            if item.item_id != self.objective.target_id:
                continue
            if remaining <= 0:
                break
            take = min(item.count, remaining)
            item.count -= take
            remaining -= take
            if item.count <= 0:
                to_remove.append(item)
        for it in to_remove:
            if it in inventory:
                inventory.remove(it)


class QuestLog:
    def __init__(self):
        self.quests: list[Quest] = []

    def add(self, quest) -> bool:
        for q in self.quests:
            if q.quest_id == quest.quest_id:
                return False
        self.quests.append(quest)
        return True

    def active(self):
        return [q for q in self.quests if q.status == QuestStatus.ACTIVE]

    def completed(self):
        return [q for q in self.quests if q.status == QuestStatus.COMPLETED]

    def has_active_from(self, npc_id) -> bool:
        return any(
            q.giver_npc_id == npc_id and q.status == QuestStatus.ACTIVE
            for q in self.quests
        )

    def notify_kill(self, enemy_id) -> list:
        return [q for q in self.quests if q.on_kill(enemy_id)]

    def notify_inventory(self, inventory) -> list:
        return [q for q in self.quests if q.sync_inventory(inventory)]

    def notify_location_cleared(self, name) -> list:
        return [q for q in self.quests if q.on_location_cleared(name)]
