"""The true state of one village (design/05-village-v0.md sections 1-3) and its event semantics.

Locations. An item (object or container) is at ("place", pid), with a person
("person", name), inside a container ("container", cid; objects only) or
("gone",) after an R8 trade. People are always at a place. Objects and
containers are both "items": they can be picked up, put down, given and
swapped; only containers take `put_in`, `open`, `close` and `carry`.

Actions (`World.act`) check their preconditions and return the event records
they cause (bank, slots, meta) or None when the action is not possible. A
blocked attempt returns its E10 failure record: opening a container that R6
reserves for someone else (ev.fail_open), putting into a closed container
(ev.fail_put_in), picking up a broken object (ev.fail_pick_up). Rule firings
follow the action that triggers them and carry meta {"rule": family,
"rule_index": i}:
  R1 put_down of a matching object -> ev.breaks (it stays where it fell, broken)
  R2 the leader goes (go, carry, R7, or a follow) -> ev.follows for the follower
  R3 at its time, each object lying loose at `place` -> ev.moved_by_place to `place2`
  R4 at its time, each owned object lying loose at a place ("lost") -> ev.returned (the owner holds it)
  R5 put_in to its container -> ev.recoloured (only if the colour changes)
  R6 open by anyone else -> ev.fail_open
  R7 at its time -> ev.go of its person to its place (then R2 followers)
  R8 `trade` at its place while holding exactly `count` objects of its kind ->
     ev.traded: those objects are gone and a new object of kind `item` is held
Timed rules of one village have distinct times, so their order never matters.
(colour, kind) stays unique among objects for the village's whole life: an
action whose recolour would repeat a label is not possible, and a new object
never reuses a label.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import random
from typing import Any, Iterable, Optional

from . import vocab

TIMES = tuple(vocab.TIMES)
TIMED = ("R3", "R4", "R7")
ALL_FAMILIES = ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8")
Loc = tuple


@dataclass
class Item:
    id: str
    type: str                 # "object" or "container"
    kind: str
    loc: Loc
    colour: Optional[str] = None
    material: Optional[str] = None
    owner: Optional[str] = None
    broken: bool = False
    open: bool = False


@dataclass(frozen=True)
class Rule:
    family: str
    bank: str
    params: tuple[tuple[str, Any], ...]

    def get(self, name: str) -> Any:
        return dict(self.params)[name]

    @property
    def slots(self) -> dict[str, Any]:
        return dict(self.params)

    @property
    def time(self) -> Optional[str]:
        return dict(self.params).get("time")


def make_rule(family: str, **params: Any) -> Rule:
    bank = f"rule.{family}"
    if family == "R1":
        bank = "rule.R1_material" if "material" in params else "rule.R1_category"
    return Rule(family, bank, tuple(sorted(params.items())))


@dataclass
class World:
    size: int
    places: dict[str, dict[str, Any]]      # pid -> {"kind", "cell": (x, y)}; y grows southward
    people: dict[str, str]                 # name -> pid
    items: dict[str, Item]
    rules: list[Rule]
    time: int = 0                          # index into TIMES
    day: int = 1
    labels: set = field(default_factory=set)  # every (kind, colour) an object ever had

    # ------------------------------------------------------------ queries

    def copy(self) -> "World":
        return World(self.size, self.places, dict(self.people), {i: replace(it) for i, it in self.items.items()},
                     list(self.rules), self.time, self.day, set(self.labels))

    @property
    def now(self) -> str:
        return TIMES[self.time]

    def objects(self) -> list[str]:
        return [i for i, it in self.items.items() if it.type == "object"]

    def containers(self) -> list[str]:
        return [i for i, it in self.items.items() if it.type == "container"]

    def place_of(self, entity: str) -> Optional[str]:
        """Resolved place of a person or item (through containers and holders); None if gone."""
        if entity in self.people:
            return self.people[entity]
        loc = self.items[entity].loc
        while loc[0] != "place":
            if loc[0] == "gone":
                return None
            loc = ("place", self.people[loc[1]]) if loc[0] == "person" else self.items[loc[1]].loc
        return loc[1]

    def holder_of(self, item: str) -> Optional[str]:
        """The person holding the item directly or through a container they hold, else None."""
        loc = self.items[item].loc
        while loc[0] == "container":
            loc = self.items[loc[1]].loc
        return loc[1] if loc[0] == "person" else None

    def held(self, person: str) -> list[str]:
        return [i for i, it in self.items.items() if it.loc == ("person", person)]

    def contents(self, container: str) -> list[str]:
        return [i for i, it in self.items.items() if it.loc == ("container", container)]

    def reachable(self, person: str, item: str) -> bool:
        """Held by the person, or lying loose at the person's place."""
        loc = self.items[item].loc
        return loc == ("person", person) or loc == ("place", self.people[person])

    def rules_of(self, family: str) -> list[tuple[int, Rule]]:
        return [(i, r) for i, r in enumerate(self.rules) if r.family == family]

    def breaks_on_put_down(self, item: str) -> Optional[int]:
        """Index of the R1 rule that breaks this object when put down, if any."""
        it = self.items[item]
        if it.type != "object" or it.broken:
            return None
        for index, rule in self.rules_of("R1"):
            params = rule.slots
            if ("material" in params and params["material"] == it.material
                    or "category" in params and params["category"] == vocab.CATEGORY.get(it.kind)):  # None never matches
                return index
        return None

    def recolour_on_put_in(self, item: str, container: str) -> tuple[Optional[int], Optional[str], bool]:
        """(R5 rule index, new colour, allowed) for putting `item` into `container`."""
        for index, rule in self.rules_of("R5"):
            if rule.get("container") == container:
                colour = rule.get("colour")
                it = self.items[item]
                if it.colour == colour:
                    return None, None, True
                return index, colour, (it.kind, colour) not in self.labels
        return None, None, True

    def can_open(self, person: str, container: str) -> tuple[bool, Optional[int]]:
        for index, rule in self.rules_of("R6"):
            if rule.get("container") == container and rule.get("person") != person:
                return False, index
        return True, None

    def entity(self, eid: str) -> dict[str, Any]:
        """One entry of the visit entity table (current colour)."""
        if eid in self.places:
            return {"type": "place", "kind": self.places[eid]["kind"], "cell": list(self.places[eid]["cell"])}
        it = self.items[eid]
        if it.type == "container":
            return {"type": "container", "kind": it.kind}
        return {"type": "object", "kind": it.kind, "colour": it.colour, "material": it.material, "owner": it.owner}

    def direction(self, place: str, place2: str) -> Optional[str]:
        """Direction of `place2` seen from `place`, when they share a row or a column."""
        (x1, y1), (x2, y2) = self.places[place]["cell"], self.places[place2]["cell"]
        if x1 == x2 and y1 != y2:
            return "north" if y2 < y1 else "south"
        if y1 == y2 and x1 != x2:
            return "east" if x2 > x1 else "west"
        return None

    def neighbours(self, place: str) -> list[str]:
        x, y = self.places[place]["cell"]
        return sorted(p for p, info in self.places.items() if abs(info["cell"][0] - x) + abs(info["cell"][1] - y) == 1)

    # ------------------------------------------------------------ actions

    def act(self, action: str, **args: Any) -> Optional[list[dict[str, Any]]]:
        """Apply one action; the records it causes, or None if it is not possible."""
        if not self.refers(args):
            return None
        return getattr(self, "_" + action)(**args)

    def refers(self, slots: dict[str, Any]) -> bool:
        """Every entity slot names an existing entity (an item made by a trade may not exist in a replay)."""
        for name, value in slots.items():
            if name in ("item", "object", "container") and value not in self.items:
                return False
            if name in ("person", "person_b", "giver", "receiver", "leader", "owner") and value not in self.people:
                return False
            if name in ("place", "place2") and value not in self.places:
                return False
        return True

    def _move(self, person: str, place: str, bank: str, slots: dict[str, Any], meta: Optional[dict] = None,
              seen: Optional[set] = None) -> list[dict[str, Any]]:
        self.people[person] = place
        out = [_rec(bank, slots, meta)]
        seen = (seen or set()) | {person}
        for index, rule in self.rules_of("R2"):
            follower = rule.get("person")
            if rule.get("leader") == person and follower not in seen and self.people[follower] != place:
                out += self._move(follower, place, "ev.follows", {"person": follower, "leader": person, "place": place},
                                  _fired("R2", index), seen)
        return out

    def _go(self, person: str, place: str) -> Optional[list]:
        if self.people[person] == place:
            return None
        return self._move(person, place, "ev.go", {"person": person, "place": place})

    def _carry(self, person: str, container: str, place: str) -> Optional[list]:
        it = self.items[container]
        if it.type != "container" or self.people[person] == place or not self.reachable(person, container):
            return None
        it.loc = ("person", person)
        return self._move(person, place, "ev.carry", {"person": person, "container": container, "place": place})

    def _pick_up(self, person: str, item: str) -> Optional[list]:
        it = self.items[item]
        if it.loc != ("place", self.people[person]):
            return None
        if it.broken:
            return [_rec("ev.fail_pick_up", {"person": person, "object": item})]
        it.loc = ("person", person)
        return [_rec("ev.pick_up", {"person": person, "object": item})]

    def _put_down(self, person: str, item: str) -> Optional[list]:
        it = self.items[item]
        if it.loc != ("person", person):
            return None
        rule = self.breaks_on_put_down(item)
        place = self.people[person]
        it.loc = ("place", place)
        out = [_rec("ev.put_down", {"person": person, "object": item, "place": place})]
        if rule is not None:
            it.broken = True
            out.append(_rec("ev.breaks", {"object": item}, _fired("R1", rule)))
        return out

    def _give(self, giver: str, receiver: str, item: str) -> Optional[list]:
        if giver == receiver or self.items[item].loc != ("person", giver) or self.people[giver] != self.people[receiver]:
            return None
        self.items[item].loc = ("person", receiver)
        return [_rec("ev.give", {"giver": giver, "receiver": receiver, "object": item})]

    def _put_in(self, person: str, item: str, container: str) -> Optional[list]:
        it, box = self.items[item], self.items[container]
        if it.type != "object" or box.type != "container" or it.loc != ("person", person) or not self.reachable(person, container):
            return None
        if not box.open:
            return [_rec("ev.fail_put_in", {"person": person, "object": item, "container": container})]
        rule, colour, allowed = self.recolour_on_put_in(item, container)
        if not allowed:
            return None
        it.loc = ("container", container)
        out = [_rec("ev.put_in", {"person": person, "object": item, "container": container})]
        if rule is not None:
            it.colour = colour
            self.labels.add((it.kind, colour))
            out.append(_rec("ev.recoloured", {"object": item, "colour": colour}, _fired("R5", rule)))
        return out

    def _take_out(self, person: str, item: str, container: str) -> Optional[list]:
        box = self.items[container]
        if self.items[item].loc != ("container", container) or not box.open or not self.reachable(person, container):
            return None
        self.items[item].loc = ("person", person)
        return [_rec("ev.take_out", {"person": person, "object": item, "container": container})]

    def _open(self, person: str, container: str) -> Optional[list]:
        box = self.items[container]
        if box.type != "container" or box.open or not self.reachable(person, container):
            return None
        allowed, rule = self.can_open(person, container)
        if not allowed:
            return [_rec("ev.fail_open", {"person": person, "container": container}, _fired("R6", rule))]
        box.open = True
        return [_rec("ev.open", {"person": person, "container": container})]

    def _close(self, person: str, container: str) -> Optional[list]:
        box = self.items[container]
        if box.type != "container" or not box.open or not self.reachable(person, container):
            return None
        box.open = False
        return [_rec("ev.close", {"person": person, "container": container})]

    def _swap(self, person: str, person_b: str) -> Optional[list]:
        if person == person_b or self.people[person] != self.people[person_b]:
            return None
        first, second = self.held(person), self.held(person_b)
        if not first or not second:
            return None
        for item in first:
            self.items[item].loc = ("person", person_b)
        for item in second:
            self.items[item].loc = ("person", person)
        return [_rec("ev.swap", {"person": person, "person_b": person_b})]

    def trade_rule(self, person: str) -> Optional[tuple[int, Rule, list[str]]]:
        for index, rule in self.rules_of("R8"):
            if rule.get("place") != self.people[person]:
                continue
            kind = rule.get("object_kind")
            given = [i for i in self.held(person) if self.items[i].type == "object" and self.items[i].kind == kind]
            if len(given) == rule.get("count"):
                return index, rule, given
        return None

    def _trade(self, person: str, new_id: Optional[str] = None) -> Optional[list]:
        found = self.trade_rule(person)
        if found is None:
            return None
        index, rule, given = found
        kind = rule.get("item")
        free = [c for c in vocab.COLOURS if (kind, c) not in self.labels]
        if not free:
            return None
        for item in given:
            self.items[item].loc = ("gone",)
        new_id = new_id or f"o{len(self.items)}"
        while new_id in self.items:
            new_id += "x"
        colour = free[_stable_index(new_id, len(free))]
        material = vocab.material_for(kind, _stable_index(new_id + "m", 12))
        self.items[new_id] = Item(new_id, "object", kind, ("person", person), colour, material)
        self.labels.add((kind, colour))
        slots = {"person": person, "count": rule.get("count"), "object_kind": rule.get("object_kind"), "item": new_id}
        return [_rec("ev.traded", slots, _fired("R8", index))]

    def _time(self) -> Optional[list]:
        out: list[dict[str, Any]] = []
        if self.time == len(TIMES) - 1:
            self.day += 1
            self.time = 0
            out.append(_rec("ev.new_day", {}))
        else:
            self.time += 1
        out.append(_rec("ev.time", {"time": self.now}))
        for index, rule in enumerate(self.rules):
            if rule.time != self.now:
                continue
            if rule.family == "R3":
                src, dst = rule.get("place"), rule.get("place2")
                for oid in self.objects():
                    if self.items[oid].loc == ("place", src):
                        self.items[oid].loc = ("place", dst)
                        out.append(_rec("ev.moved_by_place", {"object": oid, "place": src, "place2": dst}, _fired("R3", index)))
            elif rule.family == "R4":
                for oid in self.objects():
                    it = self.items[oid]
                    if it.owner is not None and it.loc[0] == "place":
                        it.loc = ("person", it.owner)
                        out.append(_rec("ev.returned", {"object": oid, "person": it.owner}, _fired("R4", index)))
            elif rule.family == "R7":
                person, place = rule.get("person"), rule.get("place")
                if self.people[person] != place:
                    out += self._move(person, place, "ev.go", {"person": person, "place": place}, _fired("R7", index))
        return out

    def _set_owner(self, item: str, person: str) -> Optional[list]:
        """A teacher-announced change (T5): the object now belongs to `person`."""
        it = self.items[item]
        if it.type != "object" or it.owner == person or person not in self.people:
            return None
        it.owner = person
        return [_rec("ev.owner", {"person": person, "object": item})]


def _rec(bank: str, slots: dict[str, Any], meta: Optional[dict] = None) -> dict[str, Any]:
    return {"bank": bank, "slots": dict(slots), "meta": dict(meta or {})}


def _fired(family: str, index: Optional[int]) -> dict[str, Any]:
    return {"rule": family, "rule_index": index}


def _stable_index(text: str, size: int) -> int:
    return sum(ord(ch) * (i + 1) for i, ch in enumerate(text)) % size


# ---------------------------------------------------------------- generation


def generate_world(rng: random.Random, people: list[str], families: Iterable[str], *,
                   rule_count: Optional[int] = None, link_rules: bool = False) -> World:
    """A random village: grid, places, people, objects, containers and 1-3 rules from `families`.

    `link_rules` (test villages) makes R7's person the head of an R2 chain when
    both exist, so one firing triggers the other (an R9 chain).
    """
    size = rng.randint(6, 10)
    cells = rng.sample([(x, y) for x in range(size) for y in range(size)], rng.randint(6, 12))
    kinds = rng.sample(list(vocab.PLACES), len(cells))
    places = {f"p{i}": {"kind": kind, "cell": cell} for i, (kind, cell) in enumerate(zip(kinds, cells))}
    pids = list(places)
    world = World(size, places, {name: rng.choice(pids) for name in people}, {}, [])
    for i, kind in enumerate(rng.sample(list(vocab.CONTAINERS), rng.randint(2, 4))):
        loc = ("person", rng.choice(people)) if rng.random() < 0.2 else ("place", rng.choice(pids))
        world.items[f"c{i}"] = Item(f"c{i}", "container", kind, loc, open=rng.random() < 0.5)
    object_kinds = rng.sample(list(vocab.OBJECTS), rng.randint(3, 6))
    for i in range(rng.randint(8, 20)):
        _add_object(world, rng, f"o{i}", rng.choice(object_kinds), people)
    wanted = list(families) + (["R2"] if "R2" in families else [])  # R2 may appear twice, as a chain
    count = rule_count or rng.randint(1, 3)
    for family in rng.sample(wanted, len(wanted)):
        if len(world.rules) >= count:
            break
        rule = _random_rule(world, rng, family, people)
        if rule is not None:
            world.rules.append(rule)
    follows = {r.get("person"): r.get("leader") for _, r in world.rules_of("R2")}
    if link_rules and follows and world.rules_of("R7"):
        index, rule = world.rules_of("R7")[0]
        head = next(iter(follows.values()))
        while head in follows:
            head = follows[head]
        world.rules[index] = make_rule("R7", person=head, place=rule.get("place"), time=rule.get("time"))
    return world


def _add_object(world: World, rng: random.Random, oid: str, kind: str, people: list[str]) -> bool:
    free = [c for c in vocab.COLOURS if (kind, c) not in world.labels]
    if not free:
        return False
    colour = rng.choice(free)
    roll = rng.random()
    containers = world.containers()
    alike = [world.items[o].loc for o in world.objects() if world.items[o].kind == kind and world.items[o].loc[0] != "gone"]
    if alike and rng.random() < 0.6:  # things of a kind gather (dishes by the well), so counts go past one
        loc = rng.choice(alike)
    elif roll < 0.25 and containers:
        loc = ("container", rng.choice(containers))
    elif roll < 0.45:
        loc = ("person", rng.choice(people))
    else:
        loc = ("place", rng.choice(list(world.places)))
    owner = rng.choice(people) if rng.random() < 0.5 else None
    world.items[oid] = Item(oid, "object", kind, loc, colour, vocab.material_for(kind, rng.randrange(12)), owner)
    world.labels.add((kind, colour))
    return True


def _random_rule(world: World, rng: random.Random, family: str, people: list[str]) -> Optional[Rule]:
    used_times = {r.time for r in world.rules if r.time}
    free_times = [t for t in TIMES if t not in used_times]
    pids = list(world.places)
    if family in TIMED and not free_times:
        return None
    if family == "R1":
        if rng.random() < 0.5:
            present = sorted({world.items[o].material for o in world.objects()} - {None})
            return make_rule("R1", material=rng.choice(present or list(vocab.MATERIALS)))
        kinds = sorted({world.items[o].kind for o in world.objects()})
        return make_rule("R1", category=vocab.CATEGORY[rng.choice(kinds)])
    if family == "R2":
        follows = {r.get("person"): r.get("leader") for _, r in world.rules_of("R2")}
        follower, leader = rng.sample(people, 2)
        if follows and follower not in follows:
            leader = rng.choice(sorted(follows))  # a second R2 extends the chain: someone follows a follower
        chain = leader
        while chain in follows:  # a follower may itself be followed, but never in a cycle
            chain = follows[chain]
            if chain == follower:
                return None
        if follower in follows or follower == leader:
            return None
        return make_rule("R2", person=follower, leader=leader)
    if family == "R3":
        place, place2 = rng.sample(pids, 2)
        return make_rule("R3", place=place, place2=place2, time=rng.choice(free_times))
    if family == "R4":
        return make_rule("R4", time=rng.choice(free_times))
    if family == "R5":
        return make_rule("R5", container=rng.choice(world.containers()), colour=rng.choice(vocab.COLOURS))
    if family == "R6":
        taken = {r.get("container") for _, r in world.rules_of("R6")}
        free = [c for c in world.containers() if c not in taken]
        return make_rule("R6", person=rng.choice(people), container=rng.choice(free)) if free else None
    if family == "R7":
        return make_rule("R7", person=rng.choice(people), place=rng.choice(pids), time=rng.choice(free_times))
    if family == "R8":
        kinds = sorted({world.items[o].kind for o in world.objects()})
        kind = rng.choice(kinds)
        count = rng.randint(2, 3)
        have = sum(1 for o in world.objects() if world.items[o].kind == kind)
        for extra in range(count - have):
            if not _add_object(world, rng, f"o{len(world.items)}", kind, people):
                return None
        item = rng.choice([k for k in vocab.OBJECTS if k not in kinds])
        return make_rule("R8", place=rng.choice(pids), count=count, object_kind=kind, item=item)
    raise ValueError(f"unknown rule family {family!r}")


__all__ = ["ALL_FAMILIES", "Item", "Rule", "TIMED", "TIMES", "World", "generate_world", "make_rule"]
