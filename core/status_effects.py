"""Статус-эффекты боя: горение, яд, заморозка, кровотечение.

Эффекты живут на любом юните (Enemy / Animal / Player) и на PlayerState.
Тик урона выполняется в сцене, чтобы смерть от эффекта корректно выдавала лут.
"""

from __future__ import annotations

EFFECT_DEFS = {
    "burn": {
        "name": "Горение",
        "color": (255, 140, 40),
        "duration": 4.0,
        "dps": 4.0,
        "speed_mult": 1.0,
    },
    "poison": {
        "name": "Яд",
        "color": (120, 200, 80),
        "duration": 6.0,
        "dps": 2.5,
        "speed_mult": 1.0,
    },
    "bleed": {
        "name": "Кровотечение",
        "color": (220, 60, 60),
        "duration": 5.0,
        "dps": 3.0,
        "speed_mult": 1.0,
    },
    "freeze": {
        "name": "Заморозка",
        "color": (120, 200, 255),
        "duration": 2.5,
        "dps": 1.0,
        "speed_mult": 0.45,
    },
}

TICK_INTERVAL = 0.5


class StatusEffectSet:
    """Набор активных эффектов. Урон накапливается и снимается тиками."""

    def __init__(self):
        self.effects: dict[str, dict] = {}

    def apply(self, kind, duration=None, power=None):
        defn = EFFECT_DEFS.get(kind)
        if defn is None:
            return False
        duration = defn["duration"] if duration is None else duration
        dps = defn["dps"] if power is None else power
        current = self.effects.get(kind)
        if current is None:
            self.effects[kind] = {
                "time": float(duration),
                "dps": float(dps),
                "tick": 0.0,
            }
        else:
            current["time"] = max(current["time"], float(duration))
            current["dps"] = max(current["dps"], float(dps))
        return True

    def tick(self, dt):
        """Возвращает суммарный урон за прошедший dt."""
        total = 0.0
        for kind in list(self.effects.keys()):
            eff = self.effects[kind]
            eff["time"] -= dt
            eff["tick"] += dt
            while eff["tick"] >= TICK_INTERVAL:
                eff["tick"] -= TICK_INTERVAL
                total += eff["dps"] * TICK_INTERVAL
            if eff["time"] <= 0:
                del self.effects[kind]
        return total

    def speed_multiplier(self):
        mult = 1.0
        for kind in self.effects:
            mult = min(mult, EFFECT_DEFS[kind]["speed_mult"])
        return mult

    def has(self, kind):
        return kind in self.effects

    def active_kinds(self):
        return list(self.effects.keys())

    def clear(self):
        self.effects.clear()

    def strongest_color(self):
        for kind in self.effects:
            defn = EFFECT_DEFS.get(kind)
            if defn:
                return defn["color"]
        return None
