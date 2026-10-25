import math

_DIRECTION_NAMES = [
    "восток",
    "юго-восток",
    "юг",
    "юго-запад",
    "запад",
    "северо-запад",
    "север",
    "северо-восток",
]


def direction_name(dx: float, dy: float) -> str:
    if dx == 0 and dy == 0:
        return "здесь"
    angle = math.atan2(dy, dx)
    idx = int(round(angle / (math.pi / 4))) % 8
    return _DIRECTION_NAMES[idx]
