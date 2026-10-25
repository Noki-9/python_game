from enum import Enum


class LocationType(Enum):
    WILD = "wild"
    VILLAGE = "village"
    STARTING_VILLAGE = "starting_village"
    QUEST = "quest"
    MAIN_QUEST = "main_quest"

    @property
    def display_name(self):
        return {
            "wild": "Дикая местность",
            "village": "Деревня",
            "starting_village": "Стартовая деревня",
            "quest": "Квестовая локация",
            "main_quest": "Сюжетная локация",
        }[self.value]

    @property
    def is_settlement(self):
        return self in (LocationType.VILLAGE, LocationType.STARTING_VILLAGE)

    @property
    def is_quest(self):
        return self in (LocationType.QUEST, LocationType.MAIN_QUEST)
