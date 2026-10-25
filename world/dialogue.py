from dataclasses import dataclass, field


@dataclass
class DialogueOption:
    label: str
    action: str  # next | close | trade | heal | quest
    next_node: str = None
    cost: int = 0
    heal_amount: int = 0


@dataclass
class DialogueNode:
    text: str
    options: list[DialogueOption] = field(default_factory=list)


DIALOGUES = {
    "merchant": {
        "root": DialogueNode(
            "Приветствую, путник! Не желаешь взглянуть на мой товар?",
            [
                DialogueOption("Торговать", "trade"),
                DialogueOption("Расскажи о себе", "next", next_node="story"),
                DialogueOption("До свидания", "close"),
            ],
        ),
        "story": DialogueNode(
            "Торгую здесь уже двадцать лет. Видел много странников —\n"
            "немногие возвращаются из дальних земель.",
            [DialogueOption("Понятно", "close")],
        ),
    },
    "blacksmith": {
        "root": DialogueNode(
            "Оружие и броня — моё ремесло. Что тебе нужно?",
            [
                DialogueOption("Торговать", "trade"),
                DialogueOption("До свидания", "close"),
            ],
        ),
    },
    "healer": {
        "root": DialogueNode(
            "Ты выглядишь измотанным. Могу подлечить за скромную плату.",
            [
                DialogueOption(
                    "Подлечить (10 золота, +40 HP)", "heal", cost=10, heal_amount=40
                ),
                DialogueOption(
                    "Подлечить полностью (25 золота)", "heal", cost=25, heal_amount=999
                ),
                DialogueOption("Спасибо, я в порядке", "close"),
            ],
        ),
    },
    "elder": {
        "root": DialogueNode(
            "Древние земли хранят много тайн. Что тебя интересует?",
            [
                DialogueOption("Расскажи о мире", "next", next_node="lore"),
                DialogueOption("Что делать дальше?", "next", next_node="hint"),
                DialogueOption("До свидания", "close"),
            ],
        ),
        "lore": DialogueNode(
            "Этот край расколот на осколки. Древние руины разбросаны повсюду,\n"
            "и тени прошлого всё ещё бродят среди них.",
            [DialogueOption("Понятно", "close")],
        ),
        "hint": DialogueNode(
            "Ищи красные метки на карте — это места, где можно испытать себя\n"
            "и обрести славу. А деревни дадут кров и отдых.",
            [DialogueOption("Спасибо", "close")],
        ),
    },
    "questgiver": {
        "root": DialogueNode(
            "У меня есть дело для тебя, странник. Слушай внимательно.",
            [
                DialogueOption("Что нужно сделать?", "next", next_node="task"),
                DialogueOption("Не сейчас", "close"),
            ],
        ),
        "task": DialogueNode(
            "В округе неспокойно. Найди квестовую локацию (красная метка)\n"
            "и зачисти её — щедро награжу.",
            [DialogueOption("Принято", "close")],
        ),
    },
    "guard": {
        "root": DialogueNode(
            "Проходи, не задерживайся. Здесь тебе ничего не угрожает.",
            [
                DialogueOption("Кто вы?", "next", next_node="info"),
                DialogueOption("Прощай", "close"),
            ],
        ),
        "info": DialogueNode(
            "Мы охраняем эту деревню от диких зверей и разбойников.\n"
            "Веди себя мирно — и не будет проблем.",
            [DialogueOption("Понятно", "close")],
        ),
    },
}


ROLE_TITLES = {
    "merchant": "Торговец",
    "blacksmith": "Кузнец",
    "healer": "Лекарь",
    "elder": "Старейшина",
    "questgiver": "Квестодатель",
    "guard": "Стражник",
}
