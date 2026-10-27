"""A toy fact stream for validating the test bench before the village exists.

Episodes state where four people keep four objects (four distinct places, so
no place is repeated), may add one rule line from the episode's rule family,
then ask where one person keeps one object. Names, narrator templates,
teacher styles and rule families are split by whole family through a
`SplitView`, so every episode carries its split and provenance, and the
registry's frozen manifest can be saved and verified. The answer never
appears in the question.

Rule families (a real `rule_family` axis, ranked across splits):
- direct: the fact is stated once;
- restated: the fact is confirmed later without naming its place;
- moved / corrected / chained: the object later goes to where another
  person's object is, so the answer is that new place;
- swapped: two people's objects exchange places.
Half the questions ask about the fact the rule line changed, half about
another fact, so a line-by-line lookup scores about one half on the families
that change places, while a store that applies each rule scores 1.

Planted flaws (`leak=`) exist so each bench check can be shown to catch them.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import random
from typing import Mapping, Optional

from .leaks import QAExample, words
from .splits import SplitRegistry

SYLLABLES = ("ba", "ke", "lo", "mi", "nu", "ra", "si", "to", "ve", "zo", "da", "fe", "gi", "ho", "ju", "pa")
OBJECTS = ("cup", "key", "coin", "book", "rope", "lamp", "bell", "comb")
PLACES = ("barn", "mill", "shed", "well", "hut", "loft", "yard", "pond")
TEMPLATES = {
    "t00": "{name} keeps the {obj} in the {place}.",
    "t01": "The {obj} of {name} is kept in the {place}.",
    "t02": "{name} puts the {obj} away in the {place}.",
    "t03": "In the {place}, {name} stores the {obj}.",
    "t04": "{name} hides the {obj} inside the {place}.",
    "t05": "The {place} is where {name} leaves the {obj}.",
    "t06": "{name} always carries the {obj} to the {place}.",
    "t07": "You can find the {obj} of {name} in the {place}.",
    "t08": "{name} left the {obj} at the {place}.",
    "t09": "The {obj} belonging to {name} sits in the {place}.",
    "t10": "{name} stashed the {obj} in the {place}.",
    "t11": "At the {place} is the {obj} that {name} owns.",
}
STYLES = {
    "q00": "Where does {name} keep the {obj}?",
    "q01": "In which place is the {obj} of {name}?",
    "q02": "{name} keeps the {obj} where?",
    "q03": "Tell me where the {obj} of {name} is.",
    "q04": "Where can the {obj} belonging to {name} be found?",
    "q05": "Which place holds the {obj} of {name}?",
    "q06": "Where would you look for the {obj} of {name}?",
    "q07": "Name the place with the {obj} of {name}.",
}
# Rule line surface per family ({name}/{obj}: the changed fact, {other}/{other_obj}: its partner).
RULE_FAMILIES: dict[str, Optional[str]] = {
    "direct": None,
    "restated": "{name} still keeps the {obj} there.",
    "moved": "Later, {name} moves the {obj} to where {other} keeps the {other_obj}.",
    "swapped": "{name} and {other} swap the {obj} and the {other_obj}.",
    "corrected": "Correction: the {obj} of {name} is really where the {other_obj} of {other} is.",
    "chained": "{name} then puts the {obj} beside the {other_obj} of {other}.",
}
MOVE_FAMILIES = ("moved", "corrected", "chained")   # the changed fact takes its partner's place
UPDATE_FAMILIES = MOVE_FAMILIES + ("swapped",)       # families whose rule line changes a place
OBJECT_PLACE = dict(zip(OBJECTS, PLACES))           # a world regularity, used only by a planted leak

TOY_FRACTIONS = (0.5, 0.25, 0.25)
TOY_SALT = "learnlab-toy-v1"
FAMILY_VERSIONS = {"template": "templates-v1", "teacher_style": "styles-v1", "rule_family": "rules-v1"}
FACTS = 4
LEAKS = (
    "answer_in_question",   # the answer is appended to the question
    "target_first",         # the answer's line is always first
    "target_second",        # ... always second
    "target_last",          # ... always last
    "skew_barn",            # the answer is "barn"
    "object_place",         # the asked object determines the answer (OBJECT_PLACE)
    "teacher_cue",          # the answer's line starts with "Teacher says:"
)


def all_names() -> list[str]:
    return sorted({a + b for a in SYLLABLES for b in SYLLABLES if a != b})


_NAME_SET = frozenset(all_names())


def make_registry() -> SplitRegistry:
    """The toy's registry: names hashed, templates, styles and rule families frozen by version."""
    registry = SplitRegistry(salt=TOY_SALT, fractions=TOY_FRACTIONS)
    registry.fix_family("template", TEMPLATES, FAMILY_VERSIONS["template"])
    registry.fix_family("teacher_style", STYLES, FAMILY_VERSIONS["teacher_style"])
    registry.fix_family("rule_family", RULE_FAMILIES, FAMILY_VERSIONS["rule_family"])
    return registry


def split_vocab() -> dict[str, object]:
    """Surface forms of every split item, for `splits.audit_examples`.

    `direct` has no rule line, so it has no surface form to scan for.
    """
    return {
        "name": all_names(),
        "template": dict(TEMPLATES),
        "teacher_style": dict(STYLES),
        "rule_family": {family: surface for family, surface in RULE_FAMILIES.items() if surface},
    }


@dataclass(frozen=True)
class Fact:
    name: str
    obj: str
    place: str


@dataclass(frozen=True)
class Episode:
    """One generated episode with its split, provenance and ground truth."""

    episode_id: str
    split: str
    rule_family: str
    facts: tuple[Fact, ...]            # stated facts, in line order
    lines: tuple[str, ...]             # fact lines, then the rule line (if any)
    templates: tuple[str, ...]         # template id of each fact line
    style: str
    question: str
    target: Fact                       # the asked (name, obj) and its current place: the answer
    answer_line: int                   # index of the fact line that states the answer's place
    affected: bool                     # the rule line changed the asked fact's place
    provenance: Mapping[str, tuple[str, ...]] = field(default_factory=dict, compare=False, hash=False)
    leak: Optional[str] = None

    @property
    def item_id(self) -> str:
        return self.episode_id

    @property
    def context(self) -> str:
        return "\n".join(self.lines)

    @property
    def text(self) -> str:
        return f"{self.context}\n{self.question}"

    def example(self) -> QAExample:
        meta = {
            "template": self.templates[self.answer_line],
            "style": self.style,
            "rule_family": self.rule_family,
        }
        return QAExample(self.context, self.question, self.target.place, meta)


@dataclass(frozen=True)
class _Spec:
    """Everything that decides an episode's text, before rendering."""

    names: tuple[str, ...]
    objects: tuple[str, ...]
    places: tuple[str, ...]
    templates: tuple[str, ...]
    style: str
    family: str
    changed: int
    partner: int
    asked: int
    order: tuple[int, ...]
    cue: bool = False
    answer_in_question: bool = False

    def holder(self) -> int:
        """The fact whose stated place answers the question."""
        if self.family in MOVE_FAMILIES and self.asked == self.changed:
            return self.partner
        if self.family == "swapped" and self.asked in (self.changed, self.partner):
            return self.partner if self.asked == self.changed else self.changed
        return self.asked


def _seed(*parts: object) -> int:
    text = "|".join(str(part) for part in (TOY_SALT, *parts))
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")


def _force(places: list[str], index: int, place: str) -> None:
    """Put `place` at `index`, swapping with its current holder so places stay distinct."""
    if place in places:
        other = places.index(place)
        places[other], places[index] = places[index], place
    else:
        places[index] = place


def _plant(spec: _Spec, leak: str) -> _Spec:
    holder = spec.holder()
    places = list(spec.places)
    order = [i for i in spec.order if i != holder]
    if leak == "answer_in_question":
        return replace(spec, answer_in_question=True)
    if leak == "teacher_cue":
        return replace(spec, cue=True)
    if leak in ("target_first", "target_second", "target_last"):
        position = {"target_first": 0, "target_second": 1, "target_last": len(order)}[leak]
        order.insert(position, holder)
        return replace(spec, order=tuple(order))
    if leak == "skew_barn":
        _force(places, holder, "barn")
        return replace(spec, places=tuple(places))
    if leak == "object_place":
        _force(places, holder, OBJECT_PLACE[spec.objects[spec.asked]])
        return replace(spec, places=tuple(places))
    raise ValueError(f"unknown planted leak {leak!r}; choose from {LEAKS}")


def _render(spec: _Spec, episode_id: str, split: str, provenance: Mapping[str, tuple[str, ...]],
            leak: Optional[str]) -> Episode:
    holder = spec.holder()
    facts, lines, templates = [], [], []
    for index in spec.order:
        fact = Fact(spec.names[index], spec.objects[index], spec.places[index])
        line = TEMPLATES[spec.templates[index]].format(name=fact.name, obj=fact.obj, place=fact.place)
        if spec.cue and index == holder:
            line = f"Teacher says: {line}"
        facts.append(fact)
        lines.append(line)
        templates.append(spec.templates[index])
    surface = RULE_FAMILIES[spec.family]
    if surface is not None:
        lines.append(surface.format(
            name=spec.names[spec.changed], obj=spec.objects[spec.changed],
            other=spec.names[spec.partner], other_obj=spec.objects[spec.partner],
        ))
    asked = Fact(spec.names[spec.asked], spec.objects[spec.asked], spec.places[holder])
    question = STYLES[spec.style].format(name=asked.name, obj=asked.obj)
    if spec.answer_in_question:
        question = f"{question} Is it the {asked.place}?"
    return Episode(
        episode_id=episode_id,
        split=split,
        rule_family=spec.family,
        facts=tuple(facts),
        lines=tuple(lines),
        templates=tuple(templates),
        style=spec.style,
        question=question,
        target=asked,
        answer_line=spec.order.index(holder),
        affected=holder != spec.asked,
        provenance=dict(provenance),
        leak=leak,
    )


def _draw(registry: SplitRegistry, split: str, index: int) -> tuple[_Spec, dict[str, tuple[str, ...]]]:
    """Draw one clean episode's items through the split's view (which records them)."""
    rng = random.Random(_seed(split, index))
    view = registry.view(split)
    names = tuple(view.draw("name", all_names(), rng, k=FACTS))
    family = view.draw("rule_family", RULE_FAMILIES, rng)[0]
    objects = tuple(rng.sample(OBJECTS, FACTS))
    places = tuple(rng.sample(PLACES, FACTS))   # without replacement: no frequency cue
    templates = tuple(view.draw("template", TEMPLATES, rng)[0] for _ in range(FACTS))
    style = view.draw("teacher_style", STYLES, rng)[0]
    changed = rng.randrange(FACTS)
    others = [i for i in range(FACTS) if i != changed]
    partner = rng.choice(others)
    asked = changed if rng.random() < 0.5 else rng.choice(others)
    spec = _Spec(names, objects, places, templates, style, family, changed, partner, asked,
                 tuple(range(FACTS)))
    return spec, view.provenance()


def generate_episode(
    registry: SplitRegistry,
    split: str,
    index: int,
    *,
    leak: Optional[str] = None,
    leak_rate: float = 1.0,
) -> Episode:
    """Generate episode `index` of `split`; `leak` plants a flaw on a `leak_rate` share of episodes.

    The planted and clean versions of an episode draw the same items, so a
    planted set differs from its clean control only by the flaw.
    """
    spec, provenance = _draw(registry, split, index)
    planted = None
    if leak is not None:
        if leak not in LEAKS:
            raise ValueError(f"unknown planted leak {leak!r}; choose from {LEAKS}")
        if random.Random(_seed("plant", split, index)).random() < leak_rate:
            spec, planted = _plant(spec, leak), leak
    return _render(spec, f"{split}-{index:05d}", split, provenance, planted)


def episodes(
    registry: SplitRegistry,
    split: str,
    count: int,
    *,
    start: int = 0,
    leak: Optional[str] = None,
    leak_rate: float = 1.0,
) -> list[Episode]:
    return [
        generate_episode(registry, split, start + i, leak=leak, leak_rate=leak_rate)
        for i in range(count)
    ]


def counterfactual_pair(registry: SplitRegistry, split: str, index: int) -> tuple[Episode, Episode]:
    """Two near-identical episodes with opposite answers.

    The twin swaps the answer's place with another fact's place; wording,
    question and every other line stay the same.
    """
    spec, provenance = _draw(registry, split, index)
    holder = spec.holder()
    rng = random.Random(_seed("counterfactual", split, index))
    other = rng.choice([i for i in range(FACTS) if i != holder])
    places = list(spec.places)
    places[holder], places[other] = places[other], places[holder]
    first = _render(spec, f"{split}-{index:05d}", split, provenance, None)
    twin = _render(replace(spec, places=tuple(places)), f"{split}-{index:05d}-cf", split, provenance, None)
    return first, twin


class CardStore:
    """Toy episode store: ordered (name, object) -> place cards, a switch and an optional FIFO budget."""

    def __init__(self, capacity: Optional[int] = None) -> None:
        self.capacity = capacity
        self.cards: dict[tuple[str, str], str] = {}
        self.enabled = True

    def write(self, fact: Fact) -> None:
        key = (fact.name, fact.obj)
        self.cards.pop(key, None)
        self.cards[key] = fact.place
        if self.capacity is not None:
            while len(self.cards) > self.capacity:
                self.cards.pop(next(iter(self.cards)))

    def apply(self, update: "Update") -> None:
        """Apply a rule line: a move takes the partner's place, a swap exchanges two places."""
        source, partner = update.source, update.partner
        if source not in self.cards or partner not in self.cards:
            return
        if update.kind == "swap":
            first, second = self.cards[source], self.cards[partner]
            self.write(Fact(*source, second))
            self.write(Fact(*partner, first))
        else:
            self.write(Fact(*source, self.cards[partner]))

    def read(self, name: str, obj: str) -> Optional[str]:
        return self.cards.get((name, obj)) if self.enabled else None

    def clear(self) -> None:
        self.cards.clear()

    def fingerprint(self) -> str:
        """Ordered cards (FIFO eviction order matters), the switch and the budget."""
        state = (tuple(self.cards.items()), self.enabled, self.capacity)
        return hashlib.sha256(repr(state).encode()).hexdigest()


@dataclass(frozen=True)
class Update:
    kind: str                      # "move" or "swap"
    source: tuple[str, str]        # (name, obj) that moves
    partner: tuple[str, str]       # (name, obj) whose place it takes (or exchanges with)


def _mentions(line: str) -> tuple[list[str], list[str], list[str], list[str]]:
    tokens = words(line)
    names = [t for t in tokens if t in _NAME_SET]
    objs = [t for t in tokens if t in OBJECTS]
    places = [t for t in tokens if t in PLACES]
    return tokens, names, objs, places


def parse_line(line: str) -> Optional[Fact]:
    """Toy 'understanding': a fact line has exactly one name, one known object and one place."""
    _, names, objs, places = _mentions(line)
    if len(objs) == 1 and len(places) == 1 and len(names) == 1:
        return Fact(names[0], objs[0], places[0])
    return None


def parse_update(line: str) -> Optional[Update]:
    """A rule line names two (person, object) pairs and no place; 'swap' exchanges, others move."""
    tokens, names, objs, places = _mentions(line)
    if len(names) != 2 or len(objs) != 2 or places:
        return None
    kind = "swap" if "swap" in tokens else "move"
    return Update(kind, (names[0], objs[0]), (names[1], objs[1]))


def parse_question(question: str) -> Optional[tuple[str, str]]:
    _, names, objs, _ = _mentions(question)
    if len(objs) == 1 and len(names) == 1:
        return names[0], objs[0]
    return None


__all__ = [
    "FACTS",
    "FAMILY_VERSIONS",
    "LEAKS",
    "MOVE_FAMILIES",
    "OBJECTS",
    "OBJECT_PLACE",
    "PLACES",
    "RULE_FAMILIES",
    "STYLES",
    "TEMPLATES",
    "TOY_FRACTIONS",
    "TOY_SALT",
    "UPDATE_FAMILIES",
    "CardStore",
    "Episode",
    "Fact",
    "Update",
    "all_names",
    "counterfactual_pair",
    "episodes",
    "generate_episode",
    "make_registry",
    "parse_line",
    "parse_question",
    "parse_update",
    "split_vocab",
]
