"""Visits and lives: what the learner reads, generated deterministically from (split, seed).

A visit is: the start of a day, a scene introduction (on a first visit; some
facts deliberately left out so that "not told" questions exist), layout
sentences, rule statements or teacher demonstrations, then days of plausible
events (rules fire, narrated or SILENT when the observer could derive them),
teacher acts and questions. Every step is kept in a script of intents, so a
counterfactual twin replays the same script with one move changed.

Split rules (the shared contract): rule families R1-R7 everywhere, R8 only in
validation and test villages, R9-style questions (two or more different rule
families in one derivation) only in test. Train questions have depth <= 3 and
at most one rule application; validation and test go up to depth 6.

The rule_family axis is a partition, so a family used by several splits is
recorded per split: item "R1:train" belongs to train, "R8:validation" to
validation, and so on (`rule_family_assignment`). Build a registry with
`make_registry()`, or hand `world_families()` to `render.village_registry`.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import random
from typing import Any, Iterator, Mapping, Optional

from learnlab.splits import SPLITS, FamilyManifest, SplitManifest, SplitRegistry, SplitView, assign_ranked, hash_canary

from . import names, vocab
from .oracle import NOBODY, NOT_TOLD, NOTHING, QTYPES, Answer, Observer, ask, surface
from .world import ALL_FAMILIES, TIMES, World, generate_world

RULE_VERSION = "village-rules-v2"
FAMILY_SPLITS: dict[str, tuple[str, ...]] = {
    **{family: SPLITS for family in ALL_FAMILIES if family != "R8"},
    "R8": ("validation", "test"),
    "R9": ("test",),
}
MAX_DEPTH = {"train": 3, "validation": 6, "test": 6}
DEPTH_TARGET = {
    "train": {1: 0.25, 2: 0.4, 3: 0.35},
    "validation": {1: 0.1, 2: 0.15, 3: 0.2, 4: 0.25, 5: 0.15, 6: 0.15},
    "test": {1: 0.1, 2: 0.15, 3: 0.2, 4: 0.25, 5: 0.15, 6: 0.15},
}
VISIBLE_LINES = 40
# A count answer 1-4 is kept this often once chosen (bigger ones are rarely possible, so they are kept more),
# which spreads them evenly; counts above four are not asked.
COUNT_KEEP = {1: 0.45, 2: 0.4, 3: 0.65, 4: 1.0}
# People hold few things, so a held count of one or two is possible far more often: those are kept less.
HELD_COUNT_KEEP = {1: 0.235, 2: 0.23, 3: 0.65, 4: 1.0}
# Busy places are named often and also hold most things, so "the most-mentioned place" would be a good blind
# guess at a place answer. A place answer is chosen with weight (1 + times named in the window) ** -this.
MENTION_DAMPING = 1.0
PLACE_BANKS = frozenset(("q.where_object", "q.where_person", "q.where_before", "q.where_at_time", "q.next_to"))
UNTOLD_PICK = 0.5  # a type chosen for balance is asked with a "not told" answer this often, when it has one
# Answers open to most questions of their type get a smaller share, so none of them is a good blind guess.
COMMON_ANSWERS = frozenset((NOBODY, NOTHING))
COMMON_WEIGHT = 0.25
DEMO_FAMILIES = ("R1", "R2")


def _seed(*parts: object) -> int:
    return int.from_bytes(hashlib.sha256("|".join(map(str, ("village-v0",) + parts)).encode()).digest()[:8], "big")


# ---------------------------------------------------------------- splits


def family_item(family: str, split: str) -> str:
    return f"{family}:{split}"


def rule_family_assignment() -> dict[str, str]:
    return {family_item(f, s): s for f, splits in FAMILY_SPLITS.items() for s in splits}


def world_families() -> dict[str, tuple[str, dict[str, str]]]:
    """The world's fixed families in `render.village_registry`'s format."""
    return {"rule_family": (RULE_VERSION, rule_family_assignment())}


def style_assignment() -> dict[str, str]:
    """Teacher styles 6/2/2, ranked exactly as `learnlab.patterns.assign_splits` ranks them."""
    return assign_ranked("teacher_style", vocab.STYLES, salt=vocab.MANIFEST_VERSION, fractions=vocab.SPLIT_FRACTIONS)


def make_registry() -> SplitRegistry:
    """Names hashed (pattern-bank salt and fractions); teacher styles and rule families fixed."""
    manifest = SplitManifest(
        salt=vocab.MANIFEST_VERSION,
        fractions=tuple(vocab.SPLIT_FRACTIONS),
        families=(FamilyManifest("teacher_style", vocab.MANIFEST_VERSION, tuple(style_assignment().items())),
                  FamilyManifest("rule_family", RULE_VERSION, tuple(rule_family_assignment().items()))),
        canary=hash_canary(vocab.MANIFEST_VERSION, vocab.SPLIT_FRACTIONS),
    )
    return SplitRegistry.from_manifest(manifest)


_REGISTRY: Optional[SplitRegistry] = None


def default_registry() -> SplitRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = make_registry()
    return _REGISTRY


def allowed_families(split: str) -> list[str]:
    return [f for f in ALL_FAMILIES if split in FAMILY_SPLITS[f]]


def question_allowed(split: str, answer: Answer) -> bool:
    """The split's depth and rule-family limits for one question."""
    if answer.depth > MAX_DEPTH[split]:
        return False
    if split == "train":
        return answer.rule_applications <= 1
    if split == "validation":
        return len(answer.families) <= 1
    return True


# ---------------------------------------------------------------- villages


class Village:
    """One village's persistent world, observer and cast, drawn through `view`."""

    def __init__(self, split: str, seed: Any, view: SplitView, number: int = 0, taken: frozenset = frozenset()) -> None:
        rng = random.Random(_seed("village", split, seed, number))
        self.split = split
        self.name = names.draw_village(view, rng, taken)  # unique in its life: the name is the village's id
        self.people = names.draw_people(view, rng, rng.randint(5, 12))  # list order = Zipf rank
        self.weights = names.zipf_weights(len(self.people))
        self.style = view.draw("teacher_style", vocab.STYLES, rng)[0]
        self.world: World = generate_world(rng, self.people, allowed_families(split), link_rules=split == "test")
        self.observer = Observer(self.world)
        self.modes = {}
        for index, rule in enumerate(self.world.rules):
            roll = rng.random()
            demo = rule.family in DEMO_FAMILIES and roll < 0.3
            self.modes[index] = "demo" if demo else ("shown" if roll > 0.8 and rule.family != "R8" else "state")
        self.visits = 0
        self.asked: list[tuple[str, dict[str, Any], int, int]] = []  # bank, slots, visit number, line
        self.visit_ids: dict[int, str] = {}  # visit number (in the life) -> visit id
        self.use(view)

    def use(self, view: SplitView) -> None:
        """Record everything this village uses in a visit's view."""
        for name in [self.name] + self.people:
            view.use("name", name)
        view.use("teacher_style", self.style)
        for rule in self.world.rules:
            view.use("rule_family", family_item(rule.family, self.split))


# ---------------------------------------------------------------- one visit


class _Visit:
    """Executes script steps on a village and collects the visit's records."""

    def __init__(self, village: Village, visit_id: str, visit_no: int, visible_lines: int) -> None:
        self.v, self.world, self.obs = village, village.world, village.observer
        self.id, self.no, self.visible_lines = visit_id, visit_no, visible_lines
        self.records: list[dict[str, Any]] = []
        self.entities = {eid: self.world.entity(eid) for eid in list(self.world.places) + list(self.world.items)}
        self.script: list[dict[str, Any]] = []
        self.spans: list[tuple[int, int]] = []  # record lines each script step produced
        self.questions: dict[str, dict[str, Any]] = {}
        self.intro_end = 0  # record lines of the scene introduction (first visits only)

    # ------------------------------------------------ records

    def _emit(self, record: dict[str, Any]) -> dict[str, Any]:
        record["line"] = len(self.records)
        inner = record.get("inner")
        if isinstance(inner, dict):
            inner["line"] = record["line"]
        self.records.append(record)
        self.obs.observe(record, (self.no, record["line"]))
        return record

    def _event(self, bank: str, slots: Mapping[str, Any], meta: Optional[Mapping] = None, silent: bool = False) -> dict:
        return {"kind": "event", "bank": bank, "slots": dict(slots), "day": self.world.day, "time": self.world.now,
                "village": self.v.name, "silent": silent, "meta": dict(meta or {})}

    def _teacher(self, bank: str, inner: Optional[dict] = None, remember: bool = False) -> dict:
        return {"kind": "teacher", "bank": bank, "style": self.v.style, "slots": {}, "inner": inner,
                "remember": remember, "day": self.world.day, "time": self.world.now, "village": self.v.name}

    def _rule(self, index: int) -> dict:
        rule = self.world.rules[index]
        return {"kind": "rule", "bank": rule.bank, "family": rule.family, "slots": rule.slots,
                "day": self.world.day, "time": self.world.now, "village": self.v.name, "meta": {"rule_index": index}}

    # ------------------------------------------------ steps

    def run(self, step: dict[str, Any]) -> bool:
        """Execute one step; False (and nothing emitted) when it is not possible now."""
        start = len(self.records)
        done = getattr(self, "_do_" + step["op"])(step)
        if done:
            self.script.append(step)
            self.spans.append((start, len(self.records)))
        return done

    def _do_act(self, step: dict[str, Any]) -> bool:
        before = set(self.world.items)
        out = self.world.act(step["action"], **step.get("args", {}))
        if out is None:
            return False
        for eid in set(self.world.items) - before:
            self.entities[eid] = self.world.entity(eid)
        for rec in out:
            event = self._event(rec["bank"], rec["slots"], rec["meta"])
            fired = bool(rec["meta"].get("rule"))
            if step.get("demo"):
                self._emit(self._teacher("t.demo_step", event))
                continue
            event["silent"] = fired and bool(step.get("quiet")) and self.obs.can_derive(event)
            self._emit(event)
        self.obs.snapshot(self.world)
        return True

    def _do_say(self, step: dict[str, Any]) -> bool:
        self._emit(self._event(step["bank"], step["slots"], step.get("meta")))
        self.obs.snapshot(self.world)
        return True

    def _do_teach(self, step: dict[str, Any]) -> bool:
        if not all(f in self.world.items or f in self.world.people or f in self.world.places or f in vocab.CATEGORY
                   for f in step["fact"][1:]):
            return False
        fact = fact_record(self.world, step["fact"])
        if fact is None:
            return False
        inner = self._event(*fact)
        self._emit(self._teacher(step["bank"], inner, remember=step["bank"] == "t.remember"))
        self.obs.snapshot(self.world)
        return True

    def _do_change(self, step: dict[str, Any]) -> bool:
        out = self.world.act("set_owner", item=step["object"], person=step["owner"])  # refers() guards ids
        if out is None:
            return False
        self._emit(self._teacher("t.change", self._event(out[0]["bank"], out[0]["slots"])))
        self.obs.snapshot(self.world)
        return True

    def _do_rule(self, step: dict[str, Any]) -> bool:
        record = self._rule(step["index"])
        if step["how"] == "state":
            self._emit(record)
        else:
            self._emit(self._teacher("t." + step["how"], record))
        return True

    def _do_ask(self, step: dict[str, Any]) -> bool:
        action = step["slots"].get("action")
        if not self.world.refers(step["slots"]) or (action and not self.world.refers(action["slots"])):
            return False
        answer = ask(self.obs, self.world, step["bank"], step["slots"])
        if answer is None or not question_allowed(self.v.split, answer):
            return False
        record = self._question(step, answer)
        if step.get("wrapper"):
            self._emit(self._teacher(step["wrapper"], record))
        else:
            self._emit(record)
        self.questions[step["key"]] = record
        self.v.asked.append((step["bank"], step["slots"], self.no, record["line"]))
        return True

    def _question(self, step: dict[str, Any], answer: Answer) -> dict[str, Any]:
        line = len(self.records)
        refs = sorted(answer.deriv.evidence)
        local = sorted({l for v, l in refs if v == self.no})
        prior = [[self.v.visit_ids[v], l] for v, l in refs if v != self.no]
        long_range = bool(prior) or any(l < line - self.visible_lines for l in local)
        base = QTYPES[step["bank"]]
        return {
            "kind": "question", "bank": step["bank"], "qtype": "Q10" if not answer.knowable else base, "base_qtype": base,
            "slots": step["slots"], "answer": answer.answer, "depth": answer.depth, "evidence": local,
            "rule_applications": answer.rule_applications, "families": answer.families, "knowable": answer.knowable,
            "twin": None, "id": f"{self.id}:{step['key']}", "range": "long_range" if long_range else "visible",
            "long_range": long_range, "prior_evidence": prior, "surface": self._surfaces(step["slots"]),
            "day": self.world.day, "time": self.world.now, "village": self.v.name,
        }

    def _surfaces(self, slots: Mapping[str, Any]) -> dict[str, str]:
        out = {}
        for name, value in slots.items():
            if isinstance(value, str) and (value in self.world.items or value in self.world.places):
                out[name] = surface(self.world, value)
        return out


def fact_record(world: World, fact: tuple) -> Optional[tuple[str, dict[str, Any]]]:
    """(bank, slots) of a true present-tense state sentence about `fact`, or None if it has none now."""
    kind = fact[0]
    if kind == "loc":
        loc = world.items[fact[1]].loc
        if loc[0] == "place":
            return "ev.intro_object", {"object": fact[1], "place": loc[1]}
        if loc[0] == "person":
            return "ev.intro_holds", {"person": loc[1], "object": fact[1]}
        if loc[0] == "container":
            return "ev.intro_in", {"object": fact[1], "container": loc[1]}
        return None
    if kind == "person":
        return "ev.intro_person", {"person": fact[1], "place": world.people[fact[1]]}
    if kind == "owner":
        owner = world.items[fact[1]].owner
        return ("ev.owner", {"person": owner, "object": fact[1]}) if owner else None
    if kind == "material":
        it = world.items[fact[1]]
        return ("ev.material", {"object": fact[1], "material": it.material}) if it.type == "object" and it.material else None
    if kind == "kind":
        return "ev.kind_group", {"object_kind": fact[1], "category": vocab.CATEGORY[fact[1]]}
    if kind == "open":
        return ("ev.is_open" if world.items[fact[1]].open else "ev.is_closed"), {"container": fact[1]}
    if kind == "dir":
        direction = world.direction(fact[2], fact[1])
        return ("ev.layout_dir", {"place": fact[1], "direction": direction, "place2": fact[2]}) if direction else None
    if kind == "next":
        return "ev.layout_next", {"place": fact[1], "place2": fact[2]}
    raise ValueError(f"unknown fact {fact!r}")


# ---------------------------------------------------------------- policy


def _say(fact: Optional[tuple[str, dict]], meta: Optional[dict] = None) -> Optional[dict[str, Any]]:
    return None if fact is None else {"op": "say", "bank": fact[0], "slots": fact[1], "meta": meta or {}}


def _intro_steps(v: Village, rng: random.Random) -> list[dict[str, Any]]:
    """Scene introduction: some facts deliberately left out, so "not told" questions exist."""
    w, steps = v.world, []
    people = list(v.people)
    rng.shuffle(people)
    steps += [_say(fact_record(w, ("person", p))) for p in people if rng.random() < 0.8]
    described: set[str] = set()
    for box in w.containers():
        if rng.random() < 0.15:
            continue
        steps.append(_say(fact_record(w, ("loc", box))))
        for item in w.contents(box):  # all of them: the reader takes an open/closed line after a listing as complete
            steps.append(_say(fact_record(w, ("loc", item))))
            described.add(item)
        steps.append(_say(fact_record(w, ("open", box)), {"complete": True}))
    loose = [o for o in w.objects() if o not in described and w.items[o].loc[0] != "container"]
    rng.shuffle(loose)
    steps += [_say(fact_record(w, ("loc", o))) for o in loose if rng.random() < 0.8]
    for o in w.objects():
        if w.items[o].owner and rng.random() < 0.5:
            steps.append(_say(fact_record(w, ("owner", o))))
        if rng.random() < 0.4:
            steps.append(_say(fact_record(w, ("material", o))))
    for kind in sorted({w.items[o].kind for o in w.objects()}):
        if kind not in v.observer.category and rng.random() < 0.6:
            steps.append(_say(fact_record(w, ("kind", kind))))
    pids = list(w.places)
    lines = [(a, b) for a in pids for b in pids if a < b and w.direction(a, b)]
    rng.shuffle(lines)
    for a, b in lines[: len(pids)]:
        steps.append(_say(fact_record(w, ("dir", a, b) if rng.random() < 0.5 else ("dir", b, a))))
    near = [(a, b) for a in pids for b in w.neighbours(a) if a < b]
    rng.shuffle(near)
    steps += [_say(fact_record(w, ("next", a, b) if rng.random() < 0.5 else ("next", b, a))) for a, b in near[:3]]
    return [step for step in steps if step is not None]


def _demo_steps(v: Village, index: int, rng: random.Random) -> Optional[list[dict[str, Any]]]:
    """A worked example of rule `index` (R1: someone puts a matching object down; R2: the leader goes)."""
    w, rule = v.world, v.world.rules[index]
    if rule.family == "R1":
        held = [o for o in w.objects() if w.items[o].loc[0] == "person" and w.breaks_on_put_down(o) == index]
        if not held:
            return None
        o = rng.choice(held)
        act = {"op": "act", "action": "put_down", "args": {"person": w.items[o].loc[1], "item": o}, "demo": True}
    elif rule.family == "R2":
        leader = rule.get("leader")
        places = [p for p in w.places if p != w.people[leader]]
        act = {"op": "act", "action": "go", "args": {"person": leader, "place": rng.choice(places)}, "demo": True}
    else:
        return None
    return [{"op": "rule", "index": index, "how": "demo_intro"}, act, {"op": "rule", "index": index, "how": "demo_outro"}]


def _propose(v: Village, rng: random.Random, person: str) -> list[tuple[float, str, dict[str, Any]]]:
    """Weighted possible actions for one person (weights shared among the options of each kind)."""
    w = v.world
    place = w.people[person]
    held = w.held(person)
    here = [i for i, it in w.items.items() if it.loc == ("place", place)]
    others = [q for q in v.people if q != person and w.people[q] == place]
    boxes = [c for c in w.containers() if w.reachable(person, c)]
    deep = v.split != "train" or rng.random() < 0.5
    follower = any(r.get("person") == person for _, r in w.rules_of("R2")) or any(
        r.get("person") == person for _, r in w.rules_of("R7"))
    groups: list[tuple[float, list[tuple[str, dict[str, Any]]]]] = [
        (3.0, [("go", {"person": person, "place": p}) for p in w.places if p != place]),
        (3.0, [("pick_up", {"person": person, "item": i}) for i in here if not w.items[i].broken]),
        (0.3, [("pick_up", {"person": person, "item": i}) for i in here if w.items[i].broken]),
        (2.0 + 2.0 * (len(held) >= 3), [("put_down", {"person": person, "item": i}) for i in held]),
        (1.5, [("give", {"giver": person, "receiver": q, "item": i}) for i in held for q in others]),
        (2.5 if deep else 1.5, [("put_in", {"person": person, "item": o, "container": c})
                                for o in held if w.items[o].type == "object" for c in boxes]),
        (1.5, [("take_out", {"person": person, "item": o, "container": c}) for c in boxes for o in w.contents(c)]),
        (1.0, [("open", {"person": person, "container": c}) for c in boxes if not w.items[c].open]),
        (0.8, [("close", {"person": person, "container": c}) for c in boxes if w.items[c].open]),
        ((6.0 if follower and deep else 2.0), [("carry", {"person": person, "container": c, "place": p})
                                              for c in boxes for p in w.places if p != place]),
        (0.4, [("swap", {"person": person, "person_b": q}) for q in others]),
        (6.0, [("trade", {"person": person})] if w.trade_rule(person) else []),
    ]
    return [(weight / len(options), action, args) for weight, options in groups if options for action, args in options]


def _random_action(vis: _Visit, rng: random.Random, quiet: float) -> bool:
    v = vis.v
    for _ in range(8):
        person = rng.choices(v.people, weights=v.weights)[0]
        options = _propose(v, rng, person)
        if not options:
            continue
        _, action, args = rng.choices(options, weights=[o[0] for o in options])[0]
        if vis.run({"op": "act", "action": action, "args": args, "quiet": rng.random() < quiet}):
            return True
    return False


def _errand(vis: _Visit, rng: random.Random, quiet: float) -> None:
    """R8 villages: someone gathers exactly `count` objects of the rule's kind, goes to its place and trades."""
    from .oracle import parse_plan, true_plan

    w = vis.world
    found = w.rules_of("R8")
    if not found:
        return
    _, rule = rng.choice(found)
    person = rng.choice(vis.v.people)
    kind, count = rule.get("object_kind"), rule.get("count")
    mine = lambda: [i for i in w.held(person) if w.items[i].type == "object" and w.items[i].kind == kind]
    for extra in mine()[count:]:
        vis.run({"op": "act", "action": "put_down", "args": {"person": person, "item": extra}})
    for target in [o for o in w.objects() if w.items[o].kind == kind and w.items[o].loc[0] != "gone"]:
        if len(mine()) >= count:
            break
        plan = true_plan(w, person, target)
        for step in (parse_plan(w, plan) or []) if plan else []:
            verb, args = step[0], step[1:]
            if verb == "go":
                act = ("go", {"person": person, "place": args[0]})
            elif verb == "pick_up":
                act = ("pick_up", {"person": person, "item": args[0]})
            elif verb == "open":
                act = ("open", {"person": person, "container": args[0]})
            elif verb == "take_out":
                act = ("take_out", {"person": person, "item": args[0], "container": args[1]})
            else:
                act = ("give", {"giver": args[0], "receiver": person, "item": args[1]})
            if not (verb == "go" and w.people[person] == args[0]):
                vis.run({"op": "act", "action": act[0], "args": act[1], "quiet": rng.random() < quiet})
    if len(mine()) == count:
        if w.people[person] != rule.get("place"):
            vis.run({"op": "act", "action": "go", "args": {"person": person, "place": rule.get("place")}})
        vis.run({"op": "act", "action": "trade", "args": {"person": person}})


def _deepen(vis: _Visit, rng: random.Random, quiet: float) -> None:
    """Build a long chain on purpose: an object in a container held by the tail of a follower chain,
    whose head then moves (silent follows); without R2, a loaded container changes hands by a swap."""
    w = vis.world
    leaders = {r.get("person"): r.get("leader") for _, r in w.rules_of("R2")}
    people = list(vis.v.people)
    carrier = max(leaders, key=lambda p: (_chain_length(leaders, p), rng.random())) if leaders else rng.choice(people)

    def act(action: str, quiet_step: bool = False, **args: Any) -> bool:
        return vis.run({"op": "act", "action": action, "args": args, "quiet": quiet_step})

    boxes = [c for c in w.held(carrier) if w.items[c].type == "container"]
    if not boxes:
        loose = [c for c in w.containers() if w.items[c].loc[0] == "place"]
        if not loose:
            return
        box = rng.choice(loose)
        if w.people[carrier] != w.items[box].loc[1]:
            act("go", person=carrier, place=w.items[box].loc[1])
        if not act("pick_up", person=carrier, item=box):
            return
    else:
        box = boxes[0]
    things = [o for o in w.held(carrier) if w.items[o].type == "object"]
    if not things:
        here = [o for o in w.objects() if w.items[o].loc == ("place", w.people[carrier]) and not w.items[o].broken]
        if here and act("pick_up", person=carrier, item=here[0]):
            things = [here[0]]
    if things:
        act("open", person=carrier, container=box)
        act("put_in", rng.random() < quiet, person=carrier, item=things[0], container=box)
    if not leaders:  # hand the loaded container over by a swap: one more inference step
        others = [p for p in people if p != carrier and w.people[p] == w.people[carrier] and w.held(p)]
        if others:
            act("swap", person=carrier, person_b=others[0])
        return
    head = carrier
    while head in leaders:
        head = leaders[head]
    act("go", True, person=head, place=rng.choice([p for p in w.places if p != w.people[head]]))


def _chain_length(leaders: Mapping[str, str], person: str) -> int:
    length = 0
    while person in leaders:
        person, length = leaders[person], length + 1
    return length


def _teach_step(vis: _Visit, rng: random.Random) -> Optional[dict[str, Any]]:
    """A teacher fact, mostly one the learner has not been told."""
    w, obs = vis.world, vis.obs
    unknown = [("loc", i) for i in w.items if i not in obs.loc and w.items[i].loc[0] != "gone"]
    unknown += [("person", p) for p in vis.v.people if p not in obs.ploc]
    unknown += [("owner", o) for o in w.objects() if w.items[o].owner and o not in obs.owner]
    unknown += [("material", o) for o in w.objects() if o not in obs.material and w.items[o].material]
    unknown += [("kind", k) for k in sorted({w.items[o].kind for o in w.objects()}) if k not in obs.category]
    anything = [("loc", i) for i in w.items if w.items[i].loc[0] != "gone"] + [("person", p) for p in vis.v.people]
    pool = unknown if unknown and rng.random() < 0.7 else anything
    return {"op": "teach", "bank": "t.remember" if rng.random() < 0.3 else "t.state", "fact": rng.choice(pool)}


# ---------------------------------------------------------------- questions


def _candidates(vis: _Visit, rng: random.Random) -> list[tuple[str, dict[str, Any]]]:
    w, obs, v = vis.world, vis.obs, vis.v
    items = [i for i in w.items if w.items[i].loc[0] != "gone"]
    objects = [o for o in items if w.items[o].type == "object"]
    seen = [i for i in items if i in obs.seen] or items
    seen_objects = [o for o in objects if o in obs.seen] or objects
    pids = list(w.places)

    def item() -> str:
        return rng.choice(seen if rng.random() < 0.85 else items)

    def obj() -> str:
        return rng.choice(seen_objects if rng.random() < 0.85 else objects)

    # Slots that could make an answer "yes" come from what the learner knows, never from the true state:
    # a "not told" question must not name the true place or holder.
    def believed(i: str) -> Optional[str]:
        found = obs.place(i)
        return found[0] if found is not None else None

    def holder(i: str) -> Optional[str]:
        found = obs.resolve(i, stop_at_person=True)
        return found[0][1] if found is not None and found[0][0] == "person" else None

    out: list[tuple[str, dict[str, Any]]] = []
    for _ in range(2):
        i, o, p = item(), obj(), rng.choice(v.people)
        out += [("q.where_object", {"object": i}), ("q.who_has", {"object": item()}),
                ("q.where_before", {"object": item()}), ("q.where_before", {"object": item()}),
                ("q.why_at", {"object": i, "place": w.place_of(i)}),
                ("q.plan_get", {"person": p, "object": o}),
                ("q.yn_at", {"object": i, "place": rng.choice(pids)}), ("q.yn_has", {"person": p, "object": i})]
    placed = [i for i in seen if believed(i)]
    for i in rng.sample(placed, min(2, len(placed))):  # questions whose answer can be "yes"
        out.append(("q.yn_at", {"object": i, "place": believed(i)}))
    held = [i for i in seen if holder(i)]
    for i in rng.sample(held, min(2, len(held))):
        out.append(("q.yn_has", {"person": holder(i), "object": i}))
    deep = sorted((found[1].steps, i) for i in seen if (found := obs.place(i)) is not None and found[0] is not None)
    for _, i in deep[-3:]:  # the items the observer knows most indirectly make the deepest questions
        p = rng.choice(v.people)
        out += [("q.where_object", {"object": i}), ("q.where_before", {"object": i}), ("q.who_has", {"object": i}),
                ("q.yn_at", {"object": i, "place": rng.choice(pids)}), ("q.plan_get", {"person": p, "object": i})]
    # Every seen thing and every person: the answer is then spread over all places, not the busiest ones.
    out += [("q.where_object", {"object": i}) for i in seen] + [("q.where_person", {"person": p}) for p in v.people]
    out += [("q.why_at", {"object": i, "place": w.place_of(i)}) for i in rng.sample(placed, min(4, len(placed)))]
    boxes = w.containers()
    out += [("q.in_container", {"container": c}) for c in boxes]
    out += [("q.who_has", {"object": i}) for i in rng.sample(held, min(2, len(held)))]
    out.append(("q.yn_in", {"object": obj(), "container": rng.choice(boxes)}))
    boxed = [(o, obs.loc[o][0][1]) for o in seen_objects if o in obs.loc and obs.loc[o][0][0] == "container"]
    for o, box in rng.sample(boxed, min(2, len(boxed))):
        out.append(("q.yn_in", {"object": o, "container": box}))
    if w.time > 0:
        earlier = rng.choice(TIMES[: w.time])
        out += [("q.where_at_time", {"object": i, "time": earlier}) for i in rng.sample(seen, min(6, len(seen)))]
    kinds = sorted({w.items[o].kind for o in objects})
    for kind in rng.sample(kinds, min(3, len(kinds))):
        mine = [o for o in objects if w.items[o].kind == kind]
        at = sorted({b for o in mine if (b := believed(o))}) or pids
        holders = sorted({h for o in mine if (h := holder(o))}) or v.people
        for place in (rng.choice(at), rng.choice(pids)):
            out.append(("q.count_at", {"object_kind": kind, "place": place}))
        for person in (rng.choice(holders), rng.choice(v.people)):
            out.append(("q.count_held", {"object_kind": kind, "person": person}))
        out.append(("q.compare_count", {"object_kind": kind, "place": rng.choice(at), "place2": rng.choice(pids)}))
    lines = [(a, b) for a in pids for b in pids if a != b and w.direction(a, b)]
    if lines:
        a, b = rng.choice(lines)
        out.append(("q.direction", {"place": a, "place2": b}))
    single = [p for p in pids if len(w.neighbours(p)) == 1]
    if single:
        out.append(("q.next_to", {"place": rng.choice(single)}))
    p, o = rng.choice(v.people), obj()
    placed = [q for q in v.people if q in obs.ploc]  # a put-down names the place: only one the learner knows
    actions = [
        {"bank": "ev.put_in", "slots": {"person": p, "object": o, "container": rng.choice(boxes)}},
        {"bank": "ev.open", "slots": {"person": p, "container": rng.choice(boxes)}},
    ]
    if placed:
        q = rng.choice(placed)
        actions.append({"bank": "ev.put_down", "slots": {"person": q, "object": o, "place": w.people[q]}})
    for rule in w.rules:  # hypotheticals aimed at each rule
        params = rule.slots
        person = rng.choice(v.people)
        if rule.family == "R1" and placed:
            person = rng.choice(placed)
            actions.append({"bank": "ev.put_down", "slots": {"person": person, "object": obj(), "place": w.people[person]}})
        elif rule.family == "R5":
            actions.append({"bank": "ev.put_in", "slots": {"person": person, "object": obj(), "container": params["container"]}})
        elif rule.family == "R6":  # the permitted person too, so an opening does not always fail
            actions.append({"bank": "ev.open", "slots": {"person": person, "container": params["container"]}})
        elif rule.family == "R2":  # anyone too, so a going does not always bring a follower
            actions.append({"bank": "ev.go", "slots": {"person": params["leader"], "place": rng.choice(pids)}})
            actions.append({"bank": "ev.go", "slots": {"person": person, "place": rng.choice(pids)}})
    for action in actions:
        out.append(("q.what_if", {"action": {"kind": "event", **action}}))
    for rule in w.rules:  # R1 has no part the question leaves out (q.rule_material would name its whole answer)
        params = rule.slots
        for slot, bank in (("person", "q.rule_person"), ("leader", "q.rule_person"), ("place", "q.rule_place"),
                           ("place2", "q.rule_place"), ("container", "q.rule_container")):
            if slot in params:
                out.append((bank, {slot if slot != "leader" else "person": params[slot]} if slot != "place2"
                            else {"place": params[slot]}))
    return out


def _choose_question(vis: _Visit, rng: random.Random, used: dict[str, int]) -> Optional[tuple[str, dict[str, Any]]]:
    """A question: its type (balanced, or by the split's depth target), then its answer, spread evenly over the
    answers that type could have now, so that the type or the wording never makes one answer a good guess."""
    # Nothing whose answer can be copied from the visible window: not the same question again, nor a rule shown.
    line = len(vis.records)
    recent = [q for q in vis.questions.values() if q["line"] >= line - vis.visible_lines]
    asked = {(q["bank"], repr(q["slots"])) for q in recent}
    shown = {q["answer"] for q in recent if q["base_qtype"] == "Q8"}
    scored = []
    for bank, slots in _candidates(vis, rng):
        if (bank, repr(slots)) in asked:
            continue
        answer = ask(vis.obs, vis.world, bank, slots)
        if answer is not None and question_allowed(vis.v.split, answer) and answer.answer not in shown:
            scored.append((bank, slots, answer))
    if not scored:
        return None
    known = [c for c in scored if c[2].knowable]
    held_out = [c for c in known if len(c[2].families) >= 2 or "R8" in c[2].families]
    target = None
    if held_out and rng.random() < 0.4:  # the held-out families are rare: ask them whenever they arise
        pool = known = held_out
    elif not known or rng.random() < 0.5:  # balance the question types; each type is "not told" equally often
        fewest = min(used.get(_kind(c), 0) for c in scored)
        kind = rng.choice(sorted({_kind(c) for c in scored if used.get(_kind(c), 0) == fewest}))
        untold = [c for c in scored if _kind(c) == kind and not c[2].knowable]
        pool = [c for c in known if _kind(c) == kind]
        if untold and (not pool or rng.random() < UNTOLD_PICK):
            pool = known = untold
    else:  # steer toward the split's depth distribution
        target = rng.choices(list(DEPTH_TARGET[vis.v.split]), weights=list(DEPTH_TARGET[vis.v.split].values()))[0]
        best = min(abs(c[2].depth - target) for c in known)
        pool = [c for c in known if abs(c[2].depth - target) == best]
    fewest = min(used.get(_kind(c), 0) for c in pool)
    kind = rng.choice(sorted({_kind(c) for c in pool if used.get(_kind(c), 0) == fewest}))
    same = [c for c in known if _kind(c) == kind]
    answers = sorted({c[2].answer for c in same})
    weights = [_weight(a) for a in answers]
    if kind in PLACE_BANKS:
        named = _named_places(vis)
        weights = [w * (1 + named[a]) ** -MENTION_DAMPING for w, a in zip(weights, answers)]
    if not any(weights):
        return None
    answer = rng.choices(answers, weights=weights)[0]
    count = vocab.NUMBER_WORDS.index(answer) if answer in vocab.NUMBER_WORDS else 0
    keep = HELD_COUNT_KEEP if kind == "q.count_held" else COUNT_KEEP
    if count and rng.random() >= keep.get(count, 0.0):
        return None
    group = [c for c in same if c[2].answer == answer]
    if target is not None:
        best = min(abs(c[2].depth - target) for c in group)
        group = [c for c in group if abs(c[2].depth - target) == best]
    bank, slots, _ = rng.choice(group)
    used[kind] = used.get(kind, 0) + 1
    return bank, slots


def _named_places(vis: _Visit) -> Counter:
    """How often each place's surface is named by the records in the visible window (nested ones too)."""
    named: Counter = Counter()

    def walk(value: Any) -> None:
        if isinstance(value, str):
            if value in vis.world.places:
                named[surface(vis.world, value)] += 1
        elif isinstance(value, Mapping):
            for inner in value.values():
                walk(inner)
        elif isinstance(value, (list, tuple)):
            for inner in value:
                walk(inner)

    for record in vis.records[-vis.visible_lines:]:
        walk(record.get("slots"))
        walk(record.get("inner"))
    return named


def _kind(candidate: tuple) -> str:
    """The unit whose answers are balanced: the bank, and for a what-if the kind of action too."""
    bank, slots = candidate[0], candidate[1]
    return f"{bank}:{slots['action']['bank']}" if bank == "q.what_if" else bank


def _weight(answer: str) -> float:
    """How often an answer is chosen among those a question type could have now: common ones less, and
    larger counts more, since they are rarely possible (a world has few things of one kind in one place)."""
    if answer in COMMON_ANSWERS:
        return COMMON_WEIGHT
    if answer.startswith("it is in "):  # four containers answer every "why" about a boxed thing
        return COMMON_WEIGHT
    if answer in vocab.NUMBER_WORDS:
        n = vocab.NUMBER_WORDS.index(answer)
        return 8.0 ** (n - 1) if 0 < n <= max(COUNT_KEEP) else float(n == 0)
    return 1.0


def _ask(vis: _Visit, rng: random.Random, used: dict[str, int]) -> None:
    line = len(vis.records)  # a quiz asks again only what has left the visible window
    later = [(b, s) for b, s, no, at in vis.v.asked if no != vis.no or at < line - vis.visible_lines]
    if later and rng.random() < 0.15:
        bank, slots = rng.choice(later)
        wrapper = "t.quiz_later"
    else:
        chosen = _choose_question(vis, rng, used)
        if chosen is None:
            return
        bank, slots = chosen
        wrapper = "t.ask" if rng.random() < 0.3 else None
    vis.run({"op": "ask", "bank": bank, "slots": slots, "wrapper": wrapper, "key": f"q{len(vis.questions)}"})


# ---------------------------------------------------------------- visits


def _run_visit(v: Village, visit_id: str, visit_no: int, rng: random.Random, days: Optional[int],
               visible_lines: int) -> _Visit:
    vis = _Visit(v, visit_id, visit_no, visible_lines)
    v.visit_ids[visit_no] = visit_id
    quiet = 0.5 if v.split == "train" else 0.8
    if v.visits == 0:  # the scene comes before the morning, so "where was it this morning" covers it
        vis.run({"op": "say", "bank": "ev.new_day", "slots": {}})
        for step in _intro_steps(v, rng):
            vis.run(step)
        vis.intro_end = len(vis.records)
        vis.run({"op": "say", "bank": "ev.time", "slots": {"time": v.world.now}})
        for index, mode in v.modes.items():
            demo = _demo_steps(v, index, rng) if mode == "demo" else None
            if mode == "shown":
                continue
            for step in demo or [{"op": "rule", "index": index, "how": "state"}]:
                vis.run(step)
    else:
        vis.run({"op": "act", "action": "time", "quiet": rng.random() < quiet})
        for index, mode in v.modes.items():
            if mode != "shown" and rng.random() < 0.3:
                vis.run({"op": "rule", "index": index, "how": "state"})
    used: dict[str, int] = {}
    for day in range(days or rng.randint(1, 2)):
        for period in range(len(TIMES)):
            if day or period:
                vis.run({"op": "act", "action": "time", "quiet": rng.random() < quiet})
            # Errands come before the everyday actions, so a question about them is not about the last place named.
            if v.world.rules_of("R8") and rng.random() < 0.3:
                _errand(vis, rng, quiet)
            if rng.random() < (0.15 if v.split == "train" else 0.35):
                _deepen(vis, rng, quiet)
            for _ in range(rng.randint(3, 7)):
                _random_action(vis, rng, quiet)
            if rng.random() < 0.3:
                step = _teach_step(vis, rng)
                if step:
                    vis.run(step)
            if rng.random() < 0.05:
                o = rng.choice(v.world.objects())
                vis.run({"op": "change", "object": o, "owner": rng.choice(v.people)})
            for _ in range(rng.randint(0, 2)):
                _ask(vis, rng, used)
    for _ in range(rng.randint(2, 4)):
        _ask(vis, rng, used)
    v.visits += 1
    return vis


def _package(vis: _Visit, view: SplitView, seed: Any) -> dict[str, Any]:
    split = vis.v.split
    if any(len(q["families"]) >= 2 for q in _all_questions(vis.records)):
        view.use("rule_family", family_item("R9", split))
    w = vis.world
    return {
        "id": vis.id, "split": split, "seed": seed, "village": vis.v.name, "style": vis.v.style,
        "people": list(vis.v.people), "entities": vis.entities, "records": vis.records,
        "rules": [{"family": r.family, "bank": r.bank, "slots": r.slots, "mode": vis.v.modes[i]} for i, r in enumerate(w.rules)],
        "provenance": {axis: list(items) for axis, items in view.provenance().items()},
        "render_seed": vis.id,
    }


def _all_questions(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for record in records:
        if record["kind"] == "question":
            out.append(record)
        elif record["kind"] == "teacher" and isinstance(record.get("inner"), dict) and record["inner"]["kind"] == "question":
            out.append(record["inner"])
    return out


def questions_of(visit: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every QuestionRecord of a visit, including those a teacher record wraps."""
    return _all_questions(visit["records"])


def _standalone(split: str, seed: int, registry: Optional[SplitRegistry], days: Optional[int],
                visible_lines: int, script: Optional[list[dict[str, Any]]] = None,
                visit_id: Optional[str] = None) -> tuple[_Visit, SplitView]:
    registry = registry if registry is not None else default_registry()
    view = registry.view(split)
    village = Village(split, seed, view)
    visit_id = visit_id or f"{split}-{seed}"
    if script is None:
        vis = _run_visit(village, visit_id, 0, random.Random(_seed("visit", split, seed)), days, visible_lines)
    else:
        vis = _Visit(village, visit_id, 0, visible_lines)
        village.visit_ids[0] = visit_id
        for step in script:
            vis.run(step)
    return vis, view


def generate_visit(split: str, seed: int, *, registry: Optional[SplitRegistry] = None, days: Optional[int] = None,
                   visible_lines: int = VISIBLE_LINES) -> dict[str, Any]:
    """One standalone visit (a first visit to a fresh village), deterministic given (split, seed)."""
    vis, view = _standalone(split, seed, registry, days, visible_lines)
    return _package(vis, view, seed)


def counterfactual_pair(split: str, seed: int, *, registry: Optional[SplitRegistry] = None,
                        days: Optional[int] = None, visible_lines: int = VISIBLE_LINES,
                        attempts: int = 12) -> tuple[dict[str, Any], dict[str, Any]]:
    """A visit and its sibling that differs by one move (a go or carry to another place).

    Questions asked with the same wording (same bank, slots and surfaces) that
    both can answer but answer differently are linked through "twin" ids; the
    sibling with the most links is returned (the visit's other questions keep
    twin None).
    """
    first, view = _standalone(split, seed, registry, days, visible_lines)
    script = first.script
    places = sorted(first.world.places)
    movable = [k for k, st in enumerate(script)
               if st["op"] == "act" and st["action"] in ("go", "carry") and not st.get("demo")]
    # First the moves a question's answer was read from: changing one of those changes an answer.
    evidence = {line for q in first.questions.values() for line in q["evidence"]}
    read = [k for k in movable if any(line in evidence for line in range(*first.spans[k]))]
    best: Optional[tuple[int, _Visit, SplitView]] = None
    for k in (list(reversed(read)) + [k for k in reversed(movable) if k not in read])[:attempts]:
        step = script[k]
        others = [p for p in places if p != step["args"]["place"]]
        alt = others[_seed("cf", split, seed, k) % len(others)]
        altered = script[:k] + [{**step, "args": {**step["args"], "place": alt}}] + script[k + 1:]
        twin, twin_view = _standalone(split, seed, registry, days, visible_lines, altered, f"{split}-{seed}-cf")
        links = _twin_links(first, twin)
        if best is None or len(links) > best[0]:
            best = (len(links), twin, twin_view)
        if len(links) >= 3:
            break
    if best is None:
        twin, twin_view = _standalone(split, seed, registry, days, visible_lines, list(script), f"{split}-{seed}-cf")
    else:
        twin, twin_view = best[1], best[2]
    for key in _twin_links(first, twin):
        a, b = first.questions[key], twin.questions[key]
        a["twin"], b["twin"] = b["id"], a["id"]
    return _package(first, view, seed), _package(twin, twin_view, seed)


def _twin_links(first: _Visit, twin: _Visit) -> list[str]:
    links = []
    for key, a in first.questions.items():
        b = twin.questions.get(key)
        if (b is not None and a["bank"] == b["bank"] and a["slots"] == b["slots"] and a["surface"] == b["surface"]
                and a["knowable"] and b["knowable"] and a["answer"] != b["answer"]):
            links.append(key)
    return links


def generate_life(split: str, seed: int, visits: int, *, registry: Optional[SplitRegistry] = None,
                  days: Optional[int] = None, revisit: float = 0.35,
                  visible_lines: int = VISIBLE_LINES) -> Iterator[dict[str, Any]]:
    """A life: `visits` visits, to new villages and (with probability `revisit`) back to earlier ones.

    A village's world, observer and cast persist between its visits; between
    visits nothing happens except the night passing, which the next visit
    narrates first. Evidence from an earlier visit is listed in
    "prior_evidence" as [visit id, line] and makes the question long-range.
    """
    registry = registry if registry is not None else default_registry()
    rng = random.Random(_seed("life", split, seed))
    villages: list[Village] = []
    last: Optional[Village] = None
    for k in range(visits):
        view = registry.view(split)
        choices = [v for v in villages if v is not last]
        if choices and len(villages) >= 2 and rng.random() < revisit:
            village = rng.choice(choices)
            village.use(view)
        else:
            village = Village(split, f"life{seed}", view, number=len(villages),
                              taken=frozenset(v.name for v in villages))
            villages.append(village)
        visit_id = f"{split}-life{seed}-v{k:04d}"
        vis = _run_visit(village, visit_id, k, random.Random(_seed("life-visit", split, seed, k)), days, visible_lines)
        last = village
        yield _package(vis, view, seed)


__all__ = [
    "DEPTH_TARGET", "FAMILY_SPLITS", "MAX_DEPTH", "RULE_VERSION", "VISIBLE_LINES", "Village", "allowed_families",
    "counterfactual_pair", "default_registry", "fact_record", "family_item", "generate_life", "generate_visit",
    "make_registry", "question_allowed", "questions_of", "rule_family_assignment", "style_assignment",
    "world_families",
]
