"""The observer: what the stream has told, and the canonical answers it supports.

The observer reads narrated records (events, state descriptions, teacher
facts, stated rules) and, for a SILENT rule firing, derives the effect itself
from the stated rule; `can_derive` says whether it could, and the scheduler
narrates every firing it could not. It never reads hidden state, and
`check(world)` asserts that every belief it holds is true.

CANONICAL ANSWERS (the only strings an answer can be):
  place            "the mill"                 person        "Kelo"
  object           "the red cup" (current colour)   container  "the chest"
  lists            "the blue key and the red cup", "a, b and c" (sorted by surface)
  empty            "nothing" (container)       no holder    "nobody"
  number           "zero" .. "twenty"          direction    "north" | "south" | "east" | "west"
  yes/no           "yes" | "no"                unknown      "not told"
  rules (Q8)       see RULE_FORMS              hypotheticals (Q7)  see WHAT_IF_FORMS
  causes (Q11)     "Kelo put it there" | "it was moved from the well at night" |
                   "Kelo has it" | "it is in the chest"
  plans (Q12)      actions joined by ", ": "go to the mill", "pick up the red cup", "open the chest",
                   "take the red cup out of the chest", "ask Kelo for the red cup"

QUESTION SEMANTICS:
  where_object     resolved place (through containers and holders)
  who_has          the person holding it directly or via a container they hold, else "nobody"
  in_container     full contents, known only if the container was described in a scene
                   introduction (whose convention is to list all contents next) and every
                   change since was seen; partial knowledge is not asked
  count_at/held    objects of the kind at the resolved place / held (incl. inside held containers)
  compare_count    the place with more (equal counts are not asked)
  where_before     the resolved place before the most recent change of resolved place
  where_at_time    the resolved place during that time of day today (asked only for an
                   earlier time today when the place did not change during it)
  direction        direction of place2 seen from place ("the barn is north of the mill")
  next_to          the single grid neighbour
  what_if          effect of stated rules on a hypothetical action ("nothing would happen" =
                   no rule effect); asked only when every rule of the family is stated
  why_at           the immediate cause; "not told" when only a scene description placed it
  plan_get         shortest plan from the observer's knowledge; any plan that `check_plan`
                   accepts is correct

DEPTH = steps of the observer's shortest derivation: reading a fact = 1 (two
links one sentence gives, "Kelo carried the box to the mill", are one read);
each hop object -> container -> holder -> place = +1; each silent rule
application = +1 (a silent R2 follow is one such application; a silent R7 move
counts the time fact read plus the application = 2); recognising an object by
a colour it had before = +1 per recolour since, when a fact used names it so;
answering a rule question or a hypothetical = +1 on its premises;
where_at_time = the belief then + 1; where_before = the deeper of the belief
then and now, + 1; compare_count = +1 on the counts; counts take the deepest
object they need; plan_get = location derivation + 1; "not told" = 0.
`rule_applications` counts rule uses in the derivation and `families` lists them;
a question is R9-style when it uses two or more DIFFERENT families.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable, Mapping, Optional

from . import vocab
from .world import TIMES, World

NOT_TOLD = "not told"
NOBODY = "nobody"
NOTHING = "nothing"
YES, NO = "yes", "no"
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}
RULE_FORMS = {
    "rule.R1_material": "things made of {material} break when put down",
    "rule.R1_category": "{category} break when put down",
    "rule.R2": "{person} follows {leader}",
    "rule.R3": "things left at {place} go to {place2} every {time}",
    "rule.R4": "lost things go back to their owners every {time}",
    "rule.R5": "things put in {container} turn {colour}",
    "rule.R6": "only {person} can open {container}",
    "rule.R7": "{person} goes to {place} every {time}",
    "rule.R8": "{count} {object_kind} can be traded for {item} at {place}",
}
WHAT_IF_FORMS = {
    "R1": "{object} would break", "R5": "{object} would turn {colour}", "R6": "{container} would stay shut",
    "open": "{container} would open", "R2": "{person} would follow", "none": "nothing would happen",
}
QTYPES = {
    "q.where_object": "Q1", "q.where_person": "Q1", "q.who_has": "Q2", "q.in_container": "Q3",
    "q.where_before": "Q4", "q.where_at_time": "Q4", "q.count_at": "Q5", "q.count_held": "Q5",
    "q.direction": "Q6", "q.next_to": "Q6", "q.what_if": "Q7", "q.rule_material": "Q8", "q.rule_category": "Q8",
    "q.rule_person": "Q8", "q.rule_place": "Q8", "q.rule_container": "Q8", "q.yn_at": "Q9", "q.yn_has": "Q9",
    "q.yn_in": "Q9", "q.why_at": "Q11", "q.plan_get": "Q12", "q.compare_count": "Q13",
}
Ref = tuple  # (visit number, line)
# Banks that say nothing about where anyone or anything is.
UNPLACED = frozenset(("ev.material", "ev.owner", "ev.kind_group", "ev.breaks", "ev.recoloured", "ev.is_open",
                      "ev.is_closed", "ev.time", "ev.new_day", "ev.layout_dir", "ev.layout_next"))
REACH = ("ev.put_in", "ev.take_out", "ev.open", "ev.close", "ev.fail_open", "ev.fail_put_in")


@dataclass(frozen=True)
class Deriv:
    """How the observer knows one thing: steps, the lines it read, the rules it applied (in order)."""

    steps: int
    evidence: frozenset = frozenset()
    rules: tuple[str, ...] = ()


def read(ref: Ref) -> Deriv:
    return Deriv(1, frozenset((ref,)))


def join(*parts: Optional[Deriv], add: int = 0, refs: Iterable[Ref] = (), family: Optional[str] = None) -> Deriv:
    steps, evidence, rules = add, set(refs), []
    for part in parts:
        if part is not None:
            steps += part.steps
            evidence |= part.evidence
            rules += part.rules
    return Deriv(steps, frozenset(evidence), tuple(rules) + ((family,) if family else ()))


@dataclass(frozen=True)
class Answer:
    answer: str
    deriv: Deriv

    @property
    def knowable(self) -> bool:
        return self.answer != NOT_TOLD

    @property
    def depth(self) -> int:
        return self.deriv.steps if self.knowable else 0

    @property
    def families(self) -> list[str]:
        return sorted(set(self.deriv.rules))

    @property
    def rule_applications(self) -> int:
        return len(self.deriv.rules)


def _not_told() -> Answer:
    return Answer(NOT_TOLD, Deriv(0))


# ---------------------------------------------------------------- surfaces


def surface(world: World, eid: str) -> str:
    """Canonical surface of a place, container or object (current colour)."""
    if eid in world.places:
        return f"the {world.places[eid]['kind']}"
    it = world.items[eid]
    return f"the {it.colour} {it.kind}" if it.type == "object" else f"the {it.kind}"


def a_kind(kind: str) -> str:
    return ("an " if kind[:1] in "aeiou" else "a ") + kind


def listing(names: Iterable[str]) -> str:
    names = sorted(names)
    if not names:
        return NOTHING
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def rule_text(world: World, index: int) -> str:
    """The canonical statement of one rule (Q8 answers)."""
    rule = world.rules[index]
    values = {}
    for name, value in rule.params:
        if name in ("place", "place2", "container"):
            value = surface(world, value)
        elif name == "count":
            value = vocab.NUMBER_WORDS[value]
        elif name == "object_kind":
            value = vocab.PLURAL[value]
        elif name == "item":
            value = a_kind(value)
        values[name] = value
    return RULE_FORMS[rule.bank].format(**values)


# ---------------------------------------------------------------- observer


class Observer:
    """Beliefs from the stream only. Reads `world` for rule contents and visible surfaces (kind, colour, type)."""

    def __init__(self, world: World) -> None:
        self.world = world
        self.loc: dict[str, tuple[tuple, Deriv]] = {}       # item -> (location, how known)
        self.ploc: dict[str, tuple[str, Deriv]] = {}        # person -> (place, how known)
        self.owner: dict[str, tuple[str, Deriv]] = {}
        self.material: dict[str, tuple[str, Deriv]] = {}
        self.is_open: dict[str, tuple[bool, Deriv]] = {}
        self.complete: dict[str, Deriv] = {}                # containers whose full contents are known
        self.broken: dict[str, Deriv] = {}
        self.category: dict[str, tuple[str, Deriv]] = {}
        self.rules: dict[int, Deriv] = {}                   # stated rules
        self.dirs: list[tuple[str, str, str, Deriv]] = []   # (a, direction, b): a is direction of b
        self.nexts: dict[tuple[str, str], Deriv] = {}       # (a, b): "a is next to b"
        self.cause: dict[str, tuple[Optional[str], Deriv]] = {}
        self.ident: dict[str, list[tuple[Ref, Deriv]]] = {}  # recolours: where, and how the learner knows
        self.named: dict[str, set] = {}                      # narrated lines naming an item (by its colour then)
        self.seen: set[str] = set()
        self.time: Optional[int] = None
        self.day: Optional[int] = None
        self.tick = 0
        self.time_ref: Optional[Ref] = None
        self.history: dict[str, list[tuple[int, Optional[str], Optional[str], Optional[Deriv]]]] = {}
        self.periods: dict[tuple[int, int], int] = {}       # (day, time) -> tick it began
        self.mentioned: set[str] = set()                    # items a narrated event placed somewhere
        self.linked: set[str] = set()                       # tied to an unknown place the observer cannot resolve
        self.moved_known: dict[str, bool] = {}              # person -> their last move is known to be a real move
        self._moves: dict[str, str] = {}                    # moves in the current action: person -> place
        self._time_read = False

    # -------------------------------------------------------- reading

    def rule_known(self, index: Optional[int]) -> bool:
        return index is not None and index in self.rules

    def can_derive(self, record: Mapping[str, Any]) -> bool:
        """Could the observer infer this rule-firing record without being told?"""
        meta = record.get("meta") or {}
        family, index = meta.get("rule"), meta.get("rule_index")
        if family is None or not self.rule_known(index):
            return False
        s = record["slots"]
        if family == "R1":
            return self._identity_match(s["object"], index) is not None
        if family == "R2":  # only if the leader surely moved: had they been there already, nobody would follow
            leader = self.ploc.get(s["leader"])
            return leader is not None and leader[0] == s["place"] and self.moved_known.get(s["leader"], False)
        if family == "R3":
            return self._loc(s["object"]) == ("place", s["place"])
        if family == "R4":
            known = self.owner.get(s["object"])
            loc = self._loc(s["object"])
            return known is not None and known[0] == s["person"] and loc is not None and loc[0] == "place"
        if family == "R5":
            return self._loc(s["object"]) == ("container", self.world.rules[index].get("container"))
        if family == "R7":
            return self.time is not None
        return False  # R6 and R8 are always narrated

    def _identity_match(self, obj: str, index: int) -> Optional[Deriv]:
        """How the observer knows the object matches R1 rule `index`, if it does."""
        rule = self.world.rules[index].slots
        if "material" in rule:
            known = self.material.get(obj)
            return known[1] if known and known[0] == rule["material"] else None
        known = self.category.get(self.world.items[obj].kind)
        return known[1] if known and known[0] == rule["category"] else None

    def _loc(self, item: str) -> Optional[tuple]:
        known = self.loc.get(item)
        return known[0] if known else None

    def _rule_refs(self, index: int) -> frozenset:
        return self.rules[index].evidence

    def observe(self, record: Mapping[str, Any], ref: Ref) -> None:
        """Take in one record: read it if narrated, derive it if silent."""
        kind = record.get("kind", "event")
        if kind == "rule":
            self.rules[record["meta"]["rule_index"]] = read(ref)
            return
        if kind == "teacher":
            inner = record.get("inner")
            if isinstance(inner, Mapping) and inner.get("kind") in ("event", "rule"):
                self.observe(inner, ref)
            return
        if kind != "event":
            return
        for name, value in record["slots"].items():
            if isinstance(value, str) and (value in self.world.items or value in self.world.people):
                if not record.get("silent"):
                    self.seen.add(value)
                    self.named.setdefault(value, set()).add(ref)
                    if record["bank"] not in UNPLACED and value in self.world.items:
                        self.mentioned.add(value)
        if record.get("silent"):
            self._derive(record, ref)
        else:
            self._read(record, ref)

    def _derive(self, record: Mapping[str, Any], ref: Ref) -> None:
        if not self.can_derive(record):
            raise AssertionError(f"silent record the observer cannot derive: {record}")
        s = record["slots"]
        index = record["meta"]["rule_index"]
        family = record["meta"]["rule"]
        refs = self._rule_refs(index)
        if family == "R1":
            self.broken[s["object"]] = join(self._identity_match(s["object"], index), add=1, refs=refs, family="R1")
        elif family == "R2":
            self._move(s["person"], s["place"], join(self.ploc[s["leader"]][1], add=1, refs=refs, family="R2"))
        elif family == "R3":
            deriv = join(self.loc[s["object"]][1], add=1, refs=refs | {self.time_ref}, family="R3")
            self.loc[s["object"]] = (("place", s["place2"]), deriv)
            self.cause[s["object"]] = (self._moved_cause(s["place"]), deriv)
        elif family == "R4":
            deriv = join(self.loc[s["object"]][1], self.owner[s["object"]][1], add=1, refs=refs | {self.time_ref}, family="R4")
            self.loc[s["object"]] = (("person", s["person"]), deriv)
        elif family == "R5":
            self.ident.setdefault(s["object"], []).append((ref, join(add=1, refs=refs | self.loc[s["object"]][1].evidence, family="R5")))
        elif family == "R7":
            self._move(s["person"], s["place"], Deriv(2, refs | {self.time_ref}, ("R7",)))

    def identify(self, item: str, deriv: Deriv) -> Deriv:
        """`deriv` plus each recolour after the earliest line it uses that names the item by an older colour."""
        used = [ref for ref in deriv.evidence if ref in self.named.get(item, ())]
        if not used:
            return deriv
        first = min(used)
        return join(deriv, *(how for at, how in self.ident.get(item, ()) if at > first))

    def _move(self, person: str, place: str, deriv: Deriv, known: Optional[bool] = None) -> None:
        """A move record; unless narrated, it is known to be a real move only if the old place was known."""
        before = self.ploc.get(person)
        self.moved_known[person] = known if known is not None else (before is not None and before[0] != place)
        self.ploc[person] = (place, deriv)
        self._moves[person] = place

    def _meet(self, person: str, known: Optional[tuple[str, Deriv]], d: Deriv) -> None:
        """The event puts `person` where a known place is (a thing lying there, or someone they met)."""
        if known is not None and person not in self.ploc:
            self.ploc[person] = (known[0], join(known[1], d))

    def _loose_place(self, item: str) -> Optional[tuple[str, Deriv]]:
        known = self.loc.get(item)
        return (known[0][1], known[1]) if known is not None and known[0][0] == "place" else None

    def _moved_cause(self, place: str) -> str:
        return f"it was moved from {surface(self.world, place)} at {TIMES[self.time]}"

    def _read(self, record: Mapping[str, Any], ref: Ref) -> None:
        bank, s, d = record["bank"], record["slots"], read(ref)
        # Co-location: who acts on a thing stands where it lies; who gives or swaps stands with the other.
        # A tie between two unknowns is not followed up later; `linked` marks both instead.
        if bank in ("ev.pick_up", "ev.fail_pick_up"):
            self._meet(s["person"], self._loose_place(s["object"]), d)
            if bank == "ev.fail_pick_up" and s["object"] not in self.loc and s["person"] not in self.ploc:
                self.linked.update((s["person"], s["object"]))
        elif bank in REACH:
            box = self.loc.get(s["container"])
            self._meet(s["person"], self._loose_place(s["container"]), d)
            if box is None:  # held by the person or lying where they stand
                self.linked.update((s["person"], s["container"]))
        elif bank in ("ev.give", "ev.swap"):
            a, b = (s["giver"], s["receiver"]) if bank == "ev.give" else (s["person"], s["person_b"])
            self._meet(a, self.ploc.get(b), d)
            self._meet(b, self.ploc.get(a), d)
            if a not in self.ploc:
                self.linked.update((a, b))
        elif bank == "ev.traded":
            index = record["meta"].get("rule_index")
            if self.rule_known(index):
                self._meet(s["person"], (self.world.rules[index].get("place"), self.rules[index]), d)
            else:
                self.linked.add(s["person"])
        elif bank == "ev.follows":
            self._meet(s["leader"], (s["place"], Deriv(0)), d)
        if bank in ("ev.go", "ev.follows"):
            self._move(s["person"], s["place"], d, True)
        elif bank == "ev.intro_person":
            self.ploc[s["person"]] = (s["place"], d)
        elif bank in ("ev.pick_up", "ev.take_out", "ev.intro_holds", "ev.fail_put_in"):
            self.loc[s["object"]] = (("person", s["person"]), d)
            if bank == "ev.take_out":
                self.is_open[s["container"]] = (True, d)
            if bank == "ev.fail_put_in":
                self.is_open[s["container"]] = (False, d)
        elif bank == "ev.put_down":
            self.loc[s["object"]] = (("place", s["place"]), d)
            self.cause[s["object"]] = (f"{s['person']} put it there", d)
            self.ploc[s["person"]] = (s["place"], d)
        elif bank == "ev.give":
            self.loc[s["object"]] = (("person", s["receiver"]), d)
        elif bank in ("ev.put_in", "ev.intro_in"):
            self.loc[s["object"]] = (("container", s["container"]), d)
            if bank == "ev.put_in":
                self.is_open[s["container"]] = (True, d)
        elif bank in ("ev.open", "ev.close", "ev.is_open", "ev.is_closed", "ev.fail_open"):
            self.is_open[s["container"]] = (bank in ("ev.open", "ev.is_open"), d)
            if (record.get("meta") or {}).get("complete"):
                self.complete[s["container"]] = d
        elif bank == "ev.carry":
            self.loc[s["container"]] = (("person", s["person"]), d)
            self._move(s["person"], s["place"], d, True)
        elif bank == "ev.swap":
            first = [i for i, (loc, _) in self.loc.items() if loc == ("person", s["person"])]
            second = [i for i, (loc, _) in self.loc.items() if loc == ("person", s["person_b"])]
            for items, other in ((first, s["person_b"]), (second, s["person"])):
                for item in items:
                    self.loc[item] = (("person", other), join(self.loc[item][1], add=1, refs=(ref,)))
        elif bank == "ev.time":
            self.time = TIMES.index(s["time"])
            self.time_ref = ref
            self._time_read = True
            if self.day is not None:
                self.periods[(self.day, self.time)] = self.tick + 1  # the state after this action
        elif bank == "ev.new_day":
            self.day = (self.day or 0) + 1
        elif bank == "ev.breaks":
            self.broken[s["object"]] = d
        elif bank == "ev.moved_by_place":
            self.loc[s["object"]] = (("place", s["place2"]), d)
            self.cause[s["object"]] = (self._moved_cause(s["place"]), d)
        elif bank == "ev.returned":
            self.loc[s["object"]] = (("person", s["person"]), d)
            self.owner.setdefault(s["object"], (s["person"], d))
        elif bank == "ev.recoloured":
            self.ident.setdefault(s["object"], []).append((ref, d))
        elif bank == "ev.traded":
            kind = s["object_kind"]
            for item, (loc, known) in list(self.loc.items()):
                it = self.world.items[item]
                if loc == ("person", s["person"]) and it.type == "object" and it.kind == kind:
                    self.loc[item] = (("gone",), join(known, add=1, refs=(ref,), family="R8"))
            self.loc[s["item"]] = (("person", s["person"]), d)
        elif bank == "ev.intro_object":
            if self._loc(s["object"]) != ("place", s["place"]):  # a restatement keeps the cause already seen
                self.cause[s["object"]] = (None, d)
            self.loc[s["object"]] = (("place", s["place"]), d)
        elif bank == "ev.owner":
            self.owner[s["object"]] = (s["person"], d)
        elif bank == "ev.material":
            self.material[s["object"]] = (s["material"], d)
        elif bank == "ev.kind_group":
            self.category[s["object_kind"]] = (s["category"], d)
        elif bank == "ev.layout_dir":
            self.dirs.append((s["place"], s["direction"], s["place2"], d))
        elif bank == "ev.layout_next":
            self.nexts[(s["place"], s["place2"])] = d
        elif bank == "ev.fail_pick_up":
            if s["object"] not in self.loc and s["person"] in self.ploc:  # it lies where the person stands
                place, known = self.ploc[s["person"]]
                self.loc[s["object"]] = (("place", place), join(known, d))
                self.cause.setdefault(s["object"], (None, d))
        else:
            raise ValueError(f"the observer cannot read bank {bank!r}")

    # -------------------------------------------------------- resolving

    def resolve(self, item: str, stop_at_person: bool = False) -> Optional[tuple[tuple, Deriv]]:
        """The item's resolved location (a place, or a person when `stop_at_person`) and its derivation."""
        known = self.loc.get(item)
        if known is None:
            return None
        loc, deriv = known
        parts = [deriv]
        while loc[0] == "container":
            known = self.loc.get(loc[1])
            if known is None:
                return None
            loc = known[0]
            parts.append(known[1])
        if loc[0] == "person" and not stop_at_person:
            known = self.ploc.get(loc[1])
            if known is None:
                return None
            loc = ("place", known[0])
            parts.append(known[1])
        return loc, chain(*parts)

    def place(self, item: str) -> Optional[tuple[Optional[str], Deriv]]:
        """(pid or None if gone, derivation) for an item, or None if unknown."""
        found = self.resolve(item)
        if found is None:
            return None
        loc, deriv = found
        return (loc[1] if loc[0] == "place" else None), deriv

    def settle(self) -> None:
        """End of an action: stated-rule effects that leave no record, because the person was already there.

        A scheduled person (R7) is at their place once its time is read; a follower (R2)
        is where their leader went if the leader surely moved. Had the follower moved,
        its record would be in this action.
        """
        if self._time_read:
            for index, rule in self.world.rules_of("R7"):
                person = rule.get("person")
                if self.rule_known(index) and rule.time == TIMES[self.time] and person not in self._moves \
                        and self.ploc.get(person, (None,))[0] != rule.get("place"):
                    self.ploc[person] = (rule.get("place"), Deriv(2, self.rules[index].evidence | {self.time_ref}, ("R7",)))
                    self.moved_known[person] = False
        for leader, place in list(self._moves.items()):
            if not self.moved_known.get(leader):
                continue
            for index, rule in self.world.rules_of("R2"):
                follower = rule.get("person")
                if rule.get("leader") == leader and self.rule_known(index) and follower not in self._moves \
                        and self.ploc.get(follower, (None,))[0] != place:
                    self.ploc[follower] = (place, join(self.ploc[leader][1], add=1, refs=self.rules[index].evidence,
                                                       family="R2"))
        self._moves.clear()
        self._time_read = False

    def unresolved(self, item: str, stop_at_person: bool = False) -> Optional[str]:
        """The first entity along the item's location chain whose own location is not known, if any."""
        known = self.loc.get(item)
        while known is not None and known[0][0] == "container":
            item = known[0][1]
            known = self.loc.get(item)
        if known is None:
            return item
        if known[0][0] == "person" and not stop_at_person and known[0][1] not in self.ploc:
            return known[0][1]
        return None

    def snapshot(self, world: World) -> None:
        """After an action: settle rule effects, record the history of every item and check no belief is false."""
        self.settle()
        self.tick += 1
        for item in world.items:
            true = world.place_of(item)
            found = self.place(item)
            obs, deriv = (found if found is not None else (None, None))
            entries = self.history.setdefault(item, [])
            if not entries or entries[-1][1:3] != (true, obs):
                entries.append((self.tick, true, obs, deriv))
        self.check(world)

    def check(self, world: World) -> None:
        """Assert that every belief is true of `world` (no false beliefs in v0)."""
        bad = []
        for item, (loc, _) in self.loc.items():
            if world.items[item].loc != loc:
                bad.append(f"{item} believed at {loc}, truly {world.items[item].loc}")
        for person, (place, _) in self.ploc.items():
            if world.people[person] != place:
                bad.append(f"{person} believed at {place}, truly {world.people[person]}")
        for obj, (person, _) in self.owner.items():
            if world.items[obj].owner != person:
                bad.append(f"{obj} believed owned by {person}")
        for obj, (material, _) in self.material.items():
            if world.items[obj].material != material:
                bad.append(f"{obj} believed made of {material}")
        for box, (state, _) in self.is_open.items():
            if world.items[box].open != state:
                bad.append(f"{box} believed open={state}")
        for obj in self.broken:
            if not world.items[obj].broken:
                bad.append(f"{obj} believed broken")
        for kind, (category, _) in self.category.items():
            if vocab.CATEGORY.get(kind) != category:
                bad.append(f"{kind} believed {category}")
        for box in self.complete:
            believed = {i for i, (loc, _) in self.loc.items() if loc == ("container", box)}
            if believed != set(world.contents(box)):
                bad.append(f"{box} contents believed {sorted(believed)}, truly {sorted(world.contents(box))}")
        if self.time is not None and self.time != world.time:
            bad.append(f"time believed {self.time}, truly {world.time}")
        if bad:
            raise AssertionError("observer holds false beliefs: " + "; ".join(bad))


# ---------------------------------------------------------------- answers


def chain(*parts: Deriv) -> Deriv:
    """`join` along a location chain; consecutive links read from one sentence count as one read."""
    total = join(*parts)
    repeats = sum(1 for a, b in zip(parts, parts[1:])
                  if a.steps == b.steps == 1 and len(a.evidence) == 1 and a.evidence == b.evidence)
    return Deriv(total.steps - repeats, total.evidence, total.rules)


def widest(*parts: Optional[Deriv]) -> Deriv:
    """Several facts needed side by side: the deepest one's steps, all their evidence and rules."""
    parts = tuple(p for p in parts if p is not None)
    return Deriv(max((p.steps for p in parts), default=0), frozenset().union(*(p.evidence for p in parts)),
                 tuple(r for p in parts for r in p.rules))


def _known(answer: str, deriv: Deriv) -> Answer:
    return Answer(answer, deriv)


def _where_object(obs: Observer, world: World, s: Mapping[str, Any]) -> Optional[Answer]:
    if world.place_of(s["object"]) is None:
        return None
    found = obs.place(s["object"])
    return _known(surface(world, found[0]), found[1]) if found else _not_told()


def _where_person(obs: Observer, world: World, s: Mapping[str, Any]) -> Optional[Answer]:
    found = obs.ploc.get(s["person"])
    return _known(surface(world, found[0]), found[1]) if found else _not_told()


def _holder(obs: Observer, item: str) -> Optional[tuple[Optional[str], Deriv]]:
    found = obs.resolve(item, stop_at_person=True)
    if found is None:
        return None
    loc, deriv = found
    return (loc[1] if loc[0] == "person" else None), deriv


def _who_has(obs: Observer, world: World, s: Mapping[str, Any]) -> Optional[Answer]:
    if world.place_of(s["object"]) is None:
        return None
    found = _holder(obs, s["object"])
    if found is None:
        return _not_told()
    return _known(found[0] or NOBODY, found[1])


def _in_container(obs: Observer, world: World, s: Mapping[str, Any]) -> Optional[Answer]:
    box = s["container"]
    members = [i for i, (loc, _) in obs.loc.items() if loc == ("container", box)]
    if box not in obs.complete:
        return None if members else _not_told()
    deriv = widest(obs.complete[box], *(obs.identify(i, obs.loc[i][1]) for i in members))
    return _known(listing(surface(world, i) for i in members), deriv)


def _counted(obs: Observer, world: World, kind: str, where) -> Optional[Answer]:
    """Count objects of `kind` for which where(observer-location) holds; None if not askable."""
    present = [o for o in world.objects() if world.items[o].kind == kind and world.place_of(o) is not None]
    if not present or any(o not in obs.seen for o in present):
        return None  # an object the stream never mentioned: the count is not answerable either way
    # Objects traded away count too: the learner must know they are gone (an R8 inference).
    objects = present + [o for o in world.objects() if world.items[o].kind == kind and o in obs.seen and o not in present]
    derivs, count = [], 0
    for o in objects:
        found = where(o)
        if found is None:
            return _not_told()
        hit, deriv = found
        count += hit
        derivs.append(deriv)
    return _known(vocab.NUMBER_WORDS[count], widest(*derivs))


def _count_at(obs: Observer, world: World, s: Mapping[str, Any]) -> Optional[Answer]:
    def where(o: str):
        found = obs.place(o)
        return None if found is None else (found[0] == s["place"], found[1])
    return _counted(obs, world, s["object_kind"], where)


def _count_held(obs: Observer, world: World, s: Mapping[str, Any]) -> Optional[Answer]:
    def where(o: str):
        found = _holder(obs, o)
        return None if found is None else (found[0] == s["person"], found[1])
    return _counted(obs, world, s["object_kind"], where)


def _compare_count(obs: Observer, world: World, s: Mapping[str, Any]) -> Optional[Answer]:
    first = _count_at(obs, world, {"object_kind": s["object_kind"], "place": s["place"]})
    second = _count_at(obs, world, {"object_kind": s["object_kind"], "place": s["place2"]})
    if first is None or second is None or s["place"] == s["place2"]:
        return None
    a, b = (_true_count(world, s["object_kind"], p) for p in (s["place"], s["place2"]))
    if a == b:
        return None
    if not (first.knowable and second.knowable):
        return _not_told()
    return _known(surface(world, s["place"] if a > b else s["place2"]), join(widest(first.deriv, second.deriv), add=1))


def _true_count(world: World, kind: str, place: str) -> int:
    return sum(1 for o in world.objects() if world.items[o].kind == kind and world.place_of(o) == place)


def _where_before(obs: Observer, world: World, s: Mapping[str, Any]) -> Optional[Answer]:
    entries = obs.history.get(s["object"], [])
    if not entries or entries[-1][1] is None:
        return None
    now = entries[-1]
    before = next((e for e in reversed(entries) if e[1] != now[1]), None)
    if before is None or before[1] is None:
        return None
    if any(e[2] != e[1] for e in entries[entries.index(before):]):  # known from then on, or a stop may be missed
        return _not_told()
    deriv = Deriv(max(before[3].steps, now[3].steps) + 1, before[3].evidence | now[3].evidence, before[3].rules + now[3].rules)
    return _known(surface(world, before[1]), deriv)


def _where_at_time(obs: Observer, world: World, s: Mapping[str, Any]) -> Optional[Answer]:
    t = TIMES.index(s["time"])
    start, stop = obs.periods.get((obs.day, t)), obs.periods.get((obs.day, t + 1))
    entries = obs.history.get(s["object"], [])
    if t >= world.time or start is None or stop is None or not entries:
        return None
    during = [e for e in entries if start < e[0] < stop]
    first = next((e for e in reversed(entries) if e[0] <= start), None)
    active = ([first] if first else []) + during
    if not active or first is None or len({e[1] for e in active}) != 1 or active[-1][1] is None:
        return None
    last = active[-1]
    if any(e[2] != e[1] for e in active):
        return _not_told()
    return _known(surface(world, last[1]), join(last[3], add=1))


def _direction(obs: Observer, world: World, s: Mapping[str, Any]) -> Optional[Answer]:
    truth = world.direction(s["place"], s["place2"])
    if truth is None:
        return None
    hops: dict[str, list[tuple[str, str, int, Deriv]]] = {}
    for a, d, b, deriv in obs.dirs:
        hops.setdefault(b, []).append((a, d, 0, deriv))            # from b, a lies d
        hops.setdefault(a, []).append((b, OPPOSITE[d], 1, deriv))  # from a, b lies opposite (+1 inference)
    best: Optional[Deriv] = None
    frontier = [(s["place"], Deriv(0))]
    seen = {s["place"]: 0}
    while frontier:  # breadth-first over hops that all point the true direction
        nxt = []
        for node, deriv in frontier:
            for target, d, extra, fact in hops.get(node, ()):
                if d != truth:
                    continue
                path = join(deriv, fact, add=extra)
                if target == s["place2"]:
                    best = path if best is None or path.steps < best.steps else best
                elif seen.get(target, 99) > path.steps:
                    seen[target] = path.steps
                    nxt.append((target, path))
        frontier = nxt
    return _known(truth, best) if best is not None else _not_told()


def _next_to(obs: Observer, world: World, s: Mapping[str, Any]) -> Optional[Answer]:
    near = world.neighbours(s["place"])
    if len(near) != 1:
        return None
    other = near[0]
    if (other, s["place"]) in obs.nexts:
        return _known(surface(world, other), obs.nexts[(other, s["place"])])
    if (s["place"], other) in obs.nexts:
        return _known(surface(world, other), join(obs.nexts[(s["place"], other)], add=1))
    return _not_told()


def _all_stated(obs: Observer, world: World, family: str) -> Optional[list[int]]:
    found = [i for i, _ in world.rules_of(family)]
    return found if found and all(obs.rule_known(i) for i in found) else None


def _what_if(obs: Observer, world: World, s: Mapping[str, Any]) -> Optional[Answer]:
    action = s["action"]
    bank, a = action["bank"], action["slots"]
    if bank == "ev.put_down":
        rules = _all_stated(obs, world, "R1")
        obj = a["object"]
        if rules is None or world.items[obj].type != "object" or world.items[obj].broken:
            return None
        refs = frozenset().union(*(obs.rules[i].evidence for i in rules))
        truly = world.breaks_on_put_down(obj)
        if truly is not None:
            known = obs._identity_match(obj, truly)
            if known is None:
                return _not_told()
            return _known(WHAT_IF_FORMS["R1"].format(object=surface(world, obj)),
                          join(obs.identify(obj, known), add=1, refs=refs, family="R1"))
        facts = []
        for i in rules:  # every stated R1 rule must be known not to apply
            rule = world.rules[i].slots
            if "material" in rule:
                known = obs.material.get(obj)
            else:
                known = obs.category.get(world.items[obj].kind)
            if known is None:
                return _not_told()
            facts.append(known[1])
        return _known(WHAT_IF_FORMS["none"], join(obs.identify(obj, widest(*facts)), add=1, refs=refs, family="R1"))
    if bank == "ev.put_in":
        rules = _all_stated(obs, world, "R5")
        obj, box = a["object"], a["container"]
        if rules is None or world.items[obj].type != "object":
            return None
        index, colour, allowed = world.recolour_on_put_in(obj, box)
        if not allowed:
            return None
        refs = frozenset().union(*(obs.rules[i].evidence for i in rules))
        if index is None:
            return _known(WHAT_IF_FORMS["none"], join(add=1, refs=refs, family="R5"))
        return _known(WHAT_IF_FORMS["R5"].format(object=surface(world, obj), colour=colour),
                      join(add=1, refs=refs, family="R5"))
    if bank == "ev.open":  # asked where every R6 rule is known; known open, nothing changes
        rules = _all_stated(obs, world, "R6")
        shut = obs.is_open.get(a["container"])
        if rules is None or shut is None:
            return None
        if shut[0]:
            return _known(WHAT_IF_FORMS["none"], join(shut[1], add=1))
        refs = frozenset().union(*(obs.rules[i].evidence for i in rules))
        allowed, _ = world.can_open(a["person"], a["container"])
        form = WHAT_IF_FORMS["open" if allowed else "R6"]
        return _known(form.format(container=surface(world, a["container"])), join(shut[1], add=1, refs=refs, family="R6"))
    if bank == "ev.go":  # every R2 rule known; the learner must know the goer is elsewhere
        rules = _all_stated(obs, world, "R2")
        leads = [(i, r) for i, r in world.rules_of("R2") if r.get("leader") == a["person"]]
        here = obs.ploc.get(a["person"])
        if rules is None or len(leads) > 1 or here is None or here[0] == a["place"]:
            return None
        refs = frozenset().union(*(obs.rules[i].evidence for i in rules))
        if not leads:
            return _known(WHAT_IF_FORMS["none"], join(here[1], add=1, refs=refs, family="R2"))
        follower = leads[0][1].get("person")
        there = obs.ploc.get(follower)
        if any(r.get("leader") == follower for _, r in world.rules_of("R2")) or there is None or there[0] == a["place"]:
            return None  # a chain moves more people; the learner must know the follower is not there already
        return _known(WHAT_IF_FORMS["R2"].format(person=follower), join(widest(here[1], there[1]), add=1, refs=refs, family="R2"))
    return None


def _why_at(obs: Observer, world: World, s: Mapping[str, Any]) -> Optional[Answer]:
    item, place = s["object"], s["place"]
    found = obs.place(item)
    if world.place_of(item) != place or found is None or found[0] != place:
        return None
    loc, link = obs.loc[item]
    if loc[0] == "person":
        return _known(f"{loc[1]} has it", found[1])
    if loc[0] == "container":
        return _known(f"it is in {surface(world, loc[1])}", found[1])
    cause = obs.cause.get(item, (None, None))[0]
    return _known(cause, found[1]) if cause else _not_told()


class _Unknown(Exception):
    pass


def _build_plan(world: World, person: str, item: str, loc_of, person_at, is_open) -> list[str]:
    """Canonical plan; `_Unknown` when a needed fact is missing. Unasked cases raise ValueError."""
    loc = loc_of(item)
    if loc is None:
        raise _Unknown
    if loc == ("person", person) or loc[0] == "gone":
        raise ValueError("already held or gone")
    steps: list[str] = []

    def go(place: str) -> None:
        if person_at(person) != place:
            steps.append(f"go to {surface(world, place)}")

    def place_of_holder(holder: str) -> str:
        place = person_at(holder)
        if place is None:
            raise _Unknown
        return place

    if loc[0] == "place":
        go(loc[1])
        steps.append(f"pick up {surface(world, item)}")
    elif loc[0] == "person":
        go(place_of_holder(loc[1]))
        steps.append(f"ask {loc[1]} for {surface(world, item)}")
    else:
        box = loc[1]
        where = loc_of(box)
        if where is None:
            raise _Unknown
        if where[0] == "place":
            go(where[1])
        elif where != ("person", person):
            go(place_of_holder(where[1]))
            steps.append(f"ask {where[1]} for {surface(world, box)}")
        if is_open(box) is not True:
            steps.append(f"open {surface(world, box)}")
        steps.append(f"take {surface(world, item)} out of {surface(world, box)}")
    return steps


def true_plan(world: World, person: str, item: str) -> Optional[str]:
    """The canonical plan from the true state, if it works (the checker agrees)."""
    try:
        steps = _build_plan(world, person, item, lambda i: world.items[i].loc, world.people.get,
                            lambda c: world.items[c].open)
    except (ValueError, _Unknown):
        return None
    text = ", ".join(steps)
    return text if check_plan(world, person, item, text) else None


def _plan_get(obs: Observer, world: World, s: Mapping[str, Any]) -> Optional[Answer]:
    person, item = s["person"], s["object"]
    if true_plan(world, person, item) is None:
        return None
    try:
        steps = _build_plan(world, person, item, obs._loc, lambda p: (obs.ploc.get(p) or (None,))[0],
                            lambda c: (obs.is_open.get(c) or (None,))[0])
    except _Unknown:
        return _not_told()
    except ValueError:
        return None
    found = obs.place(item)
    text = ", ".join(steps)
    if found is None or not check_plan(world, person, item, text):
        return None
    return _known(text, join(found[1], add=1))


_RULE_SUBJECTS = {
    "q.rule_material": ("material", {"R1": ("material",)}),
    "q.rule_category": ("category", {"R1": ("category",)}),
    "q.rule_person": ("person", {"R2": ("person", "leader"), "R6": ("person",), "R7": ("person",)}),
    "q.rule_place": ("place", {"R3": ("place", "place2"), "R7": ("place",), "R8": ("place",)}),
    "q.rule_container": ("container", {"R5": ("container",), "R6": ("container",)}),
}


def rules_about(world: World, bank: str, value: Any) -> list[int]:
    slot, fields = _RULE_SUBJECTS[bank]
    return [i for i, r in enumerate(world.rules) if any(r.slots.get(f) == value for f in fields.get(r.family, ()))]


def _rule_question(obs: Observer, world: World, s: Mapping[str, Any], bank: str) -> Optional[Answer]:
    slot = _RULE_SUBJECTS[bank][0]
    found = rules_about(world, bank, s[slot])
    if len(found) != 1 or not obs.rule_known(found[0]):
        return None
    index = found[0]
    return _known(rule_text(world, index), join(obs.rules[index], family=world.rules[index].family))


def _yn_at(obs: Observer, world: World, s: Mapping[str, Any]) -> Optional[Answer]:
    if world.place_of(s["object"]) is None:
        return None
    found = obs.place(s["object"])
    return _known(YES if found[0] == s["place"] else NO, found[1]) if found else _not_told()


def _yn_has(obs: Observer, world: World, s: Mapping[str, Any]) -> Optional[Answer]:
    if world.place_of(s["object"]) is None:
        return None
    found = _holder(obs, s["object"])
    return _known(YES if found[0] == s["person"] else NO, found[1]) if found else _not_told()


def _yn_in(obs: Observer, world: World, s: Mapping[str, Any]) -> Optional[Answer]:
    if world.place_of(s["object"]) is None or world.items[s["object"]].type != "object":
        return None
    known = obs.loc.get(s["object"])
    if known is None and s["container"] in obs.complete:  # every content of it is known, and this is not one
        return _known(NO, obs.complete[s["container"]])
    return _known(YES if known[0] == ("container", s["container"]) else NO, known[1]) if known else _not_told()


_HANDLERS = {
    "q.where_object": _where_object, "q.where_person": _where_person, "q.who_has": _who_has,
    "q.in_container": _in_container, "q.where_before": _where_before, "q.where_at_time": _where_at_time,
    "q.count_at": _count_at, "q.count_held": _count_held, "q.compare_count": _compare_count,
    "q.direction": _direction, "q.next_to": _next_to, "q.what_if": _what_if, "q.why_at": _why_at,
    "q.plan_get": _plan_get, "q.yn_at": _yn_at, "q.yn_has": _yn_has, "q.yn_in": _yn_in,
}
_IDENTIFIED = ("q.where_object", "q.who_has", "q.where_before", "q.where_at_time", "q.why_at", "q.plan_get",
               "q.yn_at", "q.yn_has", "q.yn_in")


def ask(obs: Observer, world: World, bank: str, slots: Mapping[str, Any]) -> Optional[Answer]:
    """The observer's answer to a question, or None when it is not askable.

    Not askable: a false presupposition (why_at elsewhere), an ambiguous
    question (equal counts, two rules about the subject), or one no reader
    could settle either way (a count over objects never mentioned). A known
    answer is checked against the true state before it is returned.
    """
    if bank in _RULE_SUBJECTS:
        answer = _rule_question(obs, world, slots, bank)
    else:
        answer = _HANDLERS[bank](obs, world, slots)
    if answer is None:
        return None
    if not answer.knowable:
        return answer if _surely_untold(obs, world, bank, slots) else None
    if bank in _IDENTIFIED:
        answer = Answer(answer.answer, obs.identify(slots["object"], answer.deriv))
    truth = truth_answer(world, bank, slots)
    if truth is not None and truth != answer.answer:
        raise AssertionError(f"observer answered {answer.answer!r} to {bank} {dict(slots)}, truth is {truth!r}")
    return answer


def _surely_untold(obs: Observer, world: World, bank: str, s: Mapping[str, Any]) -> bool:
    """False when "not told" might be wrong because of an inference the observer does not model.

    History: a thing a narrated event placed can show where it was all along (it lay or sat
    in a box unmentioned). Now: the missing link is tied to another unknown place (two people
    met, a used container is held or lies by its user), and that place may be learned later.
    """
    if bank in ("q.where_before", "q.where_at_time", "q.yn_in"):
        return s["object"] not in obs.mentioned
    if bank in ("q.where_object", "q.yn_at", "q.plan_get", "q.who_has", "q.yn_has"):
        missing = [obs.unresolved(s["object"], bank in ("q.who_has", "q.yn_has"))]
    elif bank == "q.where_person":
        missing = [s["person"]]
    elif bank in ("q.count_at", "q.count_held", "q.compare_count"):
        missing = [obs.unresolved(o, bank == "q.count_held") for o in world.objects()
                   if world.items[o].kind == s["object_kind"] and o in obs.seen]
    else:
        return True
    return not any(m in obs.linked for m in missing if m is not None)


def truth_answer(world: World, bank: str, s: Mapping[str, Any]) -> Optional[str]:
    """The answer from the true current state, for the question types that depend only on it."""
    if bank == "q.where_object":
        return surface(world, world.place_of(s["object"]))
    if bank == "q.where_person":
        return surface(world, world.people[s["person"]])
    if bank == "q.who_has":
        return world.holder_of(s["object"]) or NOBODY
    if bank == "q.in_container":
        return listing(surface(world, i) for i in world.contents(s["container"]))
    if bank == "q.count_at":
        return vocab.NUMBER_WORDS[_true_count(world, s["object_kind"], s["place"])]
    if bank == "q.count_held":
        held = [o for o in world.objects() if world.items[o].kind == s["object_kind"] and world.holder_of(o) == s["person"]
                and world.place_of(o) is not None]
        return vocab.NUMBER_WORDS[len(held)]
    if bank == "q.yn_at":
        return YES if world.place_of(s["object"]) == s["place"] else NO
    if bank == "q.yn_has":
        return YES if world.holder_of(s["object"]) == s["person"] else NO
    if bank == "q.yn_in":
        return YES if world.items[s["object"]].loc == ("container", s["container"]) else NO
    if bank == "q.direction":
        return world.direction(s["place"], s["place2"])
    if bank == "q.plan_get":
        return None  # any working plan is right; `check_plan` guards it instead
    return None


# ---------------------------------------------------------------- plans


def _surfaces(world: World) -> dict[str, str]:
    table = {surface(world, p): p for p in world.places}
    table.update({surface(world, i): i for i in world.items if world.items[i].loc[0] != "gone"})
    return table


def parse_plan(world: World, text: str) -> Optional[list[tuple[str, ...]]]:
    """Parse a plan in the canonical grammar into (verb, ids...) steps; None if any step does not parse."""
    names = _surfaces(world)
    steps = []
    for part in [p.strip() for p in text.strip().rstrip(".").split(",")]:
        part = re.sub(r"^(then|and)\s+", "", part[:1].lower() + part[1:])
        if not part:
            continue
        m = re.fullmatch(r"go to (the .+)", part)
        if m and m.group(1) in names and names[m.group(1)] in world.places:
            steps.append(("go", names[m.group(1)]))
            continue
        m = re.fullmatch(r"pick up (the .+)", part)
        if m and m.group(1) in names and m.group(1) not in world.places:
            steps.append(("pick_up", names[m.group(1)]))
            continue
        m = re.fullmatch(r"open (the .+)", part)
        if m and names.get(m.group(1)) in world.items:
            steps.append(("open", names[m.group(1)]))
            continue
        m = re.fullmatch(r"take (the .+) out of (the .+)", part)
        if m and names.get(m.group(1)) in world.items and names.get(m.group(2)) in world.items:
            steps.append(("take_out", names[m.group(1)], names[m.group(2)]))
            continue
        m = re.fullmatch(r"ask (\S+) for (the .+)", part)
        if m and m.group(1) in world.people and names.get(m.group(2)) in world.items:
            steps.append(("ask", m.group(1), names[m.group(2)]))
            continue
        return None
    return steps


def check_plan(world: World, person: str, item: str, text: str) -> bool:
    """Act the plan out for `person` on a copy of the state; True if they then hold `item`.

    Going where one already is and opening an open container are harmless
    no-ops; every other step must succeed (a blocked attempt fails the plan).
    Rules that react to the steps (R2 followers, R6 permission) apply.
    """
    steps = parse_plan(world, text)
    if steps is None or not steps:
        return False
    sim = world.copy()
    for step in steps:
        verb, args = step[0], step[1:]
        if verb == "go":
            ok = sim.people[person] == args[0] or bool(sim.act("go", person=person, place=args[0]))
        elif verb == "pick_up":
            out = sim.act("pick_up", person=person, item=args[0])
            ok = bool(out) and out[0]["bank"] == "ev.pick_up"
        elif verb == "open":
            if sim.items[args[0]].type != "container":
                return False
            out = None if sim.items[args[0]].open else sim.act("open", person=person, container=args[0])
            ok = sim.items[args[0]].open and (out is None or out[0]["bank"] == "ev.open")
        elif verb == "take_out":
            ok = bool(sim.act("take_out", person=person, item=args[0], container=args[1]))
        else:
            ok = args[0] != person and bool(sim.act("give", giver=args[0], receiver=person, item=args[1]))
        if not ok:
            return False
    return sim.items[item].loc == ("person", person)


__all__ = [
    "Answer", "Deriv", "NOBODY", "NOTHING", "NOT_TOLD", "NO", "Observer", "OPPOSITE", "QTYPES", "RULE_FORMS",
    "WHAT_IF_FORMS", "YES", "a_kind", "ask", "check_plan", "join", "listing", "parse_plan", "read", "rule_text",
    "rules_about", "surface", "true_plan", "truth_answer", "widest",
]
