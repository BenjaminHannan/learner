"""Village vocabulary: re-exported from `learnlab.patterns`, with a small fallback of the same names.

Each name is taken from `learnlab.patterns` when that module defines it, so a
partly written patterns module still supplies what it has.
"""
from __future__ import annotations

from typing import Any

_FALLBACK: dict[str, Any] = {
    "PLACES": ("barn", "mill", "well", "market", "bakery", "bridge", "pond", "orchard", "field", "garden",
               "forest", "river", "hill", "farm", "shop", "school"),
    "PLURAL": {"cup": "cups", "plate": "plates", "bowl": "bowls", "key": "keys", "rope": "ropes", "lamp": "lamps",
               "hat": "hats", "scarf": "scarves", "coat": "coats", "ball": "balls", "doll": "dolls", "kite": "kites",
               "apple": "apples", "loaf": "loaves", "pear": "pears"},
    "CATEGORY": {"cup": "dishes", "plate": "dishes", "bowl": "dishes", "key": "tools", "rope": "tools", "lamp": "tools",
                 "hat": "clothes", "scarf": "clothes", "coat": "clothes", "ball": "toys", "doll": "toys", "kite": "toys",
                 "apple": "food", "loaf": "food", "pear": "food"},
    "CATEGORIES": ("dishes", "tools", "clothes", "toys", "food"),
    "MATERIALS": ("glass", "wood", "iron", "cloth", "clay", "stone"),
    "COLOURS": ("red", "blue", "green", "yellow", "white", "black", "brown", "grey"),
    "CONTAINERS": ("box", "basket", "chest", "sack"),
    "TIMES": ("morning", "noon", "evening", "night"),
    "DIRECTIONS": ("north", "south", "east", "west"),
    "NUMBER_WORDS": ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"),
    "STYLES": ("plain", "cheerful", "terse", "storyteller", "formal", "questioning", "childlike",
               "grandparent", "bossy", "poetic"),
    "BANKS": {},
    "MANIFEST_VERSION": "village-patterns-v1",
    "SPLIT_FRACTIONS": (0.6, 0.2, 0.2),
}

try:
    from learnlab import patterns as _patterns
except ImportError:  # patterns.py not written yet
    _patterns = None

_values = {name: getattr(_patterns, name, default) for name, default in _FALLBACK.items()}
_values["OBJECTS"] = tuple(getattr(_patterns, "OBJECTS", None) or _values["CATEGORY"])

PLACES: tuple[str, ...] = tuple(_values["PLACES"])
OBJECTS: tuple[str, ...] = _values["OBJECTS"]
PLURAL: dict[str, str] = dict(_values["PLURAL"])
CATEGORY: dict[str, str] = dict(_values["CATEGORY"])
CATEGORIES: tuple[str, ...] = tuple(_values["CATEGORIES"])
MATERIALS: tuple[str, ...] = tuple(_values["MATERIALS"])
COLOURS: tuple[str, ...] = tuple(_values["COLOURS"])
CONTAINERS: tuple[str, ...] = tuple(_values["CONTAINERS"])
TIMES: tuple[str, ...] = tuple(_values["TIMES"])
DIRECTIONS: tuple[str, ...] = tuple(_values["DIRECTIONS"])
NUMBER_WORDS: tuple[str, ...] = tuple(_values["NUMBER_WORDS"])
STYLES: tuple[str, ...] = tuple(_values["STYLES"])
BANKS = _values["BANKS"]
MANIFEST_VERSION: str = _values["MANIFEST_VERSION"]
SPLIT_FRACTIONS: tuple[float, float, float] = tuple(_values["SPLIT_FRACTIONS"])  # type: ignore[assignment]

__all__ = [
    "BANKS", "CATEGORIES", "CATEGORY", "COLOURS", "CONTAINERS", "DIRECTIONS", "MANIFEST_VERSION", "MATERIALS",
    "NUMBER_WORDS", "OBJECTS", "PLACES", "PLURAL", "SPLIT_FRACTIONS", "STYLES", "TIMES",
]


# Materials an object of each kind can plausibly be made of; food (and balloons, ropes) has none, so no
# material sentence or material rule ever names it.
_M = {"glass", "wood", "iron", "cloth", "clay", "stone"}
KIND_MATERIALS: dict[str, tuple[str, ...]] = {
    "cup": ("glass", "clay", "wood", "iron"), "plate": ("clay", "wood", "glass"), "bowl": ("wood", "clay", "glass", "stone"),
    "spoon": ("wood", "iron"), "fork": ("iron", "wood"), "jug": ("clay", "glass"), "mug": ("clay", "glass", "wood"),
    "pot": ("clay", "iron"), "pan": ("iron",), "kettle": ("iron",), "teapot": ("clay", "iron"), "ladle": ("wood", "iron"),
    "key": ("iron",), "hammer": ("iron", "wood", "stone"), "brush": ("wood",), "shovel": ("iron", "wood"),
    "rake": ("wood", "iron"), "broom": ("wood",), "lamp": ("glass", "iron", "clay"), "bucket": ("wood", "iron"),
    "ladder": ("wood", "iron"), "needle": ("iron",), "axe": ("iron", "stone"),
    "ball": ("cloth",), "doll": ("cloth", "wood", "clay"), "kite": ("cloth",), "drum": ("wood",),
    "whistle": ("wood", "iron", "clay"), "puppet": ("cloth", "wood"), "rattle": ("wood", "clay"), "flute": ("wood",),
    "hoop": ("wood", "iron"), "bell": ("iron", "glass", "clay"), "sled": ("wood",),
    **{kind: ("cloth",) for kind in ("hat", "scarf", "coat", "boot", "glove", "sock", "shirt", "cloak", "apron",
                                      "belt", "mitten", "shawl")},
}
assert all(set(v) <= _M for v in KIND_MATERIALS.values())


def material_for(kind: str, index: int) -> "str | None":
    """The material of an object of `kind` picked by `index`, or None when the kind has no material."""
    options = KIND_MATERIALS.get(kind, ())
    return options[index % len(options)] if options else None
