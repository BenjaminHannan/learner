"""Made-up syllable names, split whole by `learnlab.splits` (axis "name").

People have two syllables ("Kelo"), villages three ("Zobaki"), so the two
pools never share a name. The final syllable of a person's name never ends
in "e" (that avoids "bake", "love", "give" ...), and a short blocklist plus
the village vocabulary remove the remaining English words. Usage within a
village is Zipf-bursty: `zipf_weights` gives rank r the weight 1 / (r + 1) ** s.
"""
from __future__ import annotations

from functools import lru_cache
import random

from learnlab.splits import SplitView
from learnlab.toy import SYLLABLES as TOY_SYLLABLES

from . import vocab

SYLLABLES: tuple[str, ...] = TOY_SYLLABLES + ("ne", "ta", "vi", "sa", "ku", "mo", "li", "re")
_VILLAGE_ENDS = ("ki", "ra", "lo", "mu", "no", "ta", "vi", "sa")
_BLOCKED = frozenset({"visa", "vita", "lira", "silo", "veto", "keto", "moto", "tapa", "raku", "pare", "sake", "tuba"})
ZIPF_EXPONENT = 1.2


def _vocab_words() -> frozenset[str]:
    words: set[str] = set()
    for group in (vocab.PLACES, vocab.OBJECTS, tuple(vocab.PLURAL.values()), vocab.CATEGORIES, vocab.MATERIALS,
                  vocab.COLOURS, vocab.CONTAINERS, vocab.TIMES, vocab.DIRECTIONS, vocab.NUMBER_WORDS, vocab.STYLES):
        words.update(group)
    return frozenset(words)


@lru_cache(maxsize=None)
def people_names() -> tuple[str, ...]:
    """Every candidate person name (two syllables, capitalised), sorted."""
    banned = _BLOCKED | _vocab_words()
    names = {a + b for a in SYLLABLES for b in SYLLABLES if a != b and not b.endswith("e")}
    return tuple(sorted(n.capitalize() for n in names if n not in banned))


@lru_cache(maxsize=None)
def village_names() -> tuple[str, ...]:
    """Every candidate village name (three syllables, capitalised), sorted."""
    banned = _vocab_words()
    names = {a + b + c for a in SYLLABLES for b in SYLLABLES for c in _VILLAGE_ENDS if len({a, b, c}) == 3}
    return tuple(sorted(n.capitalize() for n in names if n not in banned))


def all_names() -> tuple[str, ...]:
    """People and village names together: the "name" vocabulary for `splits.audit_examples`."""
    return people_names() + village_names()


def draw_people(view: SplitView, rng: random.Random, k: int) -> list[str]:
    """`k` distinct person names of the view's split, recorded; list order is the Zipf rank."""
    return view.draw("name", people_names(), rng, k=k)


def draw_village(view: SplitView, rng: random.Random, taken: frozenset = frozenset()) -> str:
    """A village name of the view's split that no village in `taken` already has."""
    return view.draw("name", [n for n in village_names() if n not in taken], rng)[0]


def zipf_weights(count: int, exponent: float = ZIPF_EXPONENT) -> list[float]:
    return [1.0 / (rank + 1) ** exponent for rank in range(count)]


__all__ = ["SYLLABLES", "ZIPF_EXPONENT", "all_names", "draw_people", "draw_village", "people_names",
           "village_names", "zipf_weights"]
