"""Фракции мира и отношение к ним игрока (ТЗ 8, 10).

Фракция деревни определяется её seed, поэтому она стабильна между
заходами и сохранениями. Отношение фракции влияет на цены и доступность
заданий, а враждебность жителей — на поведение стражи.
"""

FACTIONS = {
    "crown": "Корона",
    "free": "Вольные",
    "cult": "Культ",
}

FACTION_IDS = tuple(FACTIONS)


def faction_for_seed(seed: int) -> str:
    """Детерминированная фракция деревни по seed мира."""
    return FACTION_IDS[int(seed) % len(FACTION_IDS)]


def faction_name(faction_id) -> str:
    return FACTIONS.get(faction_id, "Неизвестные")


def standing_title(value: int) -> str:
    if value >= 50:
        return "Союзник"
    if value >= 15:
        return "Друг"
    if value > -15:
        return "Нейтрал"
    if value > -40:
        return "Подозрительный"
    return "Враг"
