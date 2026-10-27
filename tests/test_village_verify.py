"""Independent verification (red team) of the village world, oracle, scheduler and stream.

`Reference` is a second interpreter written from the spec, not from oracle.py
(the Reference never uses it). It reads only what a learner reads: every record
that is not silent, in order. Places it cannot see yet are union-find
variables ("wherever Toli is"), so co-location facts ("Toli picked up the
basket", "Rami gave the cup to Toli") pay off as soon as one side is named,
even later. Stated rules are applied by the reference itself, and it relies
on the narration contract: a firing the learner could not derive is narrated.
Its answers must equal the oracle's on every question, "not told" included.
"""
from __future__ import annotations

import random
import re
import unittest
from collections import Counter, defaultdict
from typing import Any, Mapping, Optional
from unittest import mock

from learnlab.splits import SplitManifest, SplitRegistry
from learnlab.village import names, scheduler, stream, vocab
from learnlab.village.oracle import check_plan, parse_plan, surface  # for the tests only, never the Reference
from learnlab.village.world import make_rule
from tests.test_village_world import Scene, small_world

NOT_TOLD, NOBODY, NOTHING = "not told", "nobody", "nothing"
TIMES = tuple(vocab.TIMES)
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}
GONE = "gone"
RULE_FORMS = {  # the canonical rule statements (Q8), as agreed in the contract
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
RULE_SUBJECTS = {
    "q.rule_material": ("material", {"R1": ("material",)}),
    "q.rule_category": ("category", {"R1": ("category",)}),
    "q.rule_person": ("person", {"R2": ("person", "leader"), "R6": ("person",), "R7": ("person",)}),
    "q.rule_place": ("place", {"R3": ("place", "place2"), "R7": ("place",), "R8": ("place",)}),
    "q.rule_container": ("container", {"R5": ("container",), "R6": ("container",)}),
}


class Places:
    """Union-find over fixed places, each maybe still unknown ("where Toli stood then")."""

    def __init__(self) -> None:
        self.parent: list[int] = []
        self.value: list[Optional[str]] = []

    def new(self, place: Optional[str] = None) -> int:
        self.parent.append(len(self.parent))
        self.value.append(place)
        return len(self.parent) - 1

    def find(self, n: int) -> int:
        while self.parent[n] != n:
            self.parent[n] = self.parent[self.parent[n]]
            n = self.parent[n]
        return n

    def get(self, n: int) -> Optional[str]:
        return self.value[self.find(n)]

    def union(self, a: int, b: int) -> None:
        a, b = self.find(a), self.find(b)
        if a == b:
            return
        va, vb = self.value[a], self.value[b]
        if va is not None and vb is not None and va != vb:
            raise AssertionError(f"reference contradiction: one place is both {va} and {vb}")
        self.parent[b] = a
        self.value[a] = va if va is not None else vb

    def same(self, a: int, b: int) -> bool:
        return self.find(a) == self.find(b) or (self.get(a) is not None and self.get(a) == self.get(b))


class Reference:
    """What a careful learner can know from the stream of one village (all its visits, fed in order)."""

    def __init__(self, people: list[str]) -> None:
        self.uf = Places()
        self.pv = {p: self.uf.new() for p in people}     # person -> their place since their last move
        self.ent: dict[str, Mapping[str, Any]] = {}
        self.colour: dict[str, Optional[str]] = {}
        # item -> ("place", node) | ("person", name) | ("container", cid) | ("gone",) | ("reach", name, node)
        # ("reach", p, n): held by p, or lying loose at node n (where p stood when they used it).
        self.loc: dict[str, tuple] = {}
        self.owner: dict[str, str] = {}
        self.material: dict[str, str] = {}
        self.category: dict[str, str] = {}
        self.is_open: dict[str, bool] = {}
        self.complete: set[str] = set()
        self.rules: dict[int, tuple[str, str, dict]] = {}   # rule index -> (family, bank, slots)
        self.dirs: set[tuple[str, str, str]] = set()       # (a, d, b): a is d of b
        self.nexts: set[frozenset] = set()
        self.cause: dict[str, Optional[str]] = {}
        self.seen: set[str] = set()
        self.time: Optional[int] = None
        self.day = 0
        # History, one entry per action: the direct locations and people's place nodes after it, and what
        # moved in it: ("person", p), ("item", i) (and whatever is inside it) or ("trade", p, kind).
        self.locs: list[dict[str, tuple]] = []
        self.pvs: list[dict[str, int]] = []
        self.causes: list[list[tuple]] = []
        self._causes: list[tuple] = []
        self.retro: dict[str, tuple[int, tuple]] = {}      # item -> (action index, where it was until then)
        self.swaps: dict[str, list[int]] = defaultdict(list)
        self.born: dict[str, int] = {}
        self.period: dict[tuple[int, int], int] = {}        # (day, time) -> first snapshot of that period
        self._pending = False
        self._period_pending: Optional[tuple[int, int]] = None
        self._last_bank: Optional[str] = None

    # ------------------------------------------------------------ reading

    def feed(self, visit: Mapping[str, Any]) -> list[tuple[dict, str]]:
        """Read one visit; (question record, reference answer) for every question in it."""
        for eid, entity in visit["entities"].items():
            if eid not in self.ent:
                self.ent[eid] = entity
                self.colour[eid] = entity.get("colour")
        out = []
        for record in visit["records"]:
            if record.get("silent"):
                continue
            kind, inner = record["kind"], record.get("inner")
            if kind == "teacher" and isinstance(inner, Mapping):
                record, kind = inner, inner["kind"]
            elif kind == "teacher":
                continue
            if kind == "question":
                self.flush()
                out.append((record, self.answer(record)))
            elif kind == "rule":
                self.flush()
                self.rules[record["meta"]["rule_index"]] = (record["family"], record["bank"], dict(record["slots"]))
            else:
                self.event(record)
        self.flush()
        return out

    def flush(self) -> None:
        """Close the current action and keep its state for history questions."""
        if not self._pending:
            return
        self._pending = False
        self.locs.append(dict(self.loc))
        self.pvs.append(dict(self.pv))
        self.causes.append(self._causes)
        self._causes = []
        if self._period_pending is not None:
            self.period[self._period_pending] = len(self.locs) - 1
            self._period_pending = None

    def learn(self, item: str, before: tuple) -> None:
        """The event shows where a never-located item was just before it; nothing unnamed moves a loose
        or boxed item, so it was there all along (a held one, since its holder's last swap)."""
        if item not in self.loc and item not in self.retro:
            self.retro[item] = (len(self.locs), before)

    def event(self, record: Mapping[str, Any]) -> None:
        bank, s = record["bank"], record["slots"]
        consequence = bool((record.get("meta") or {}).get("rule")) or (bank == "ev.time" and self._last_bank == "ev.new_day")
        if not consequence:
            self.flush()
        self._pending = True
        self._last_bank = bank
        for name in ("object", "item", "container"):
            if isinstance(s.get(name), str) and s[name] in self.ent:
                self.seen.add(s[name])
        getattr(self, "_" + bank[3:])(s)

    def at(self, place: str) -> int:
        return self.uf.new(place)

    def moved(self, person: str, place: str, known: bool) -> None:
        """`person` is now at `place`; `known` when the learner knows they really moved (so followers did too)."""
        self._causes.append(("person", person))
        self.pv[person] = self.at(place)
        if not known:
            return
        for family, _, s in list(self.rules.values()):
            if family == "R2" and s["leader"] == person:
                before = self.uf.get(self.pv[s["person"]])
                self.moved(s["person"], place, before is not None and before != place)

    def loose_at(self, item: str, node: int) -> None:
        cur = self.loc.get(item)
        if cur is None:
            return
        if cur[0] == "place":
            self.uf.union(cur[1], node)
        elif cur[0] == "reach":
            self.uf.union(cur[2], node)
        else:
            raise AssertionError(f"reference believed {item} at {cur}, but it was lying loose")

    def reach(self, person: str, box: str) -> None:
        """`person` used `box`: they hold it, or it lies where they stand."""
        cur = self.loc.get(box)
        here = self.pv[person]
        if cur is None:
            self.loc[box] = ("reach", person, here)
        elif cur[0] == "place":
            self.uf.union(cur[1], here)
        elif cur[0] == "person":
            if cur[1] != person:
                raise AssertionError(f"reference believed {box} held by {cur[1]}, but {person} used it")
        elif cur[0] == "reach":
            if cur[1] != person:  # held by neither alone: it lies loose where both stood
                self.uf.union(cur[2], here)
                self.loc[box] = ("place", cur[2])
            elif not self.uf.same(cur[2], here):
                self.loc[box] = ("reach", person, here)

    def _go(self, s): self.moved(s["person"], s["place"], True)

    def _follows(self, s):
        self.uf.union(self.pv[s["leader"]], self.at(s["place"]))
        self.moved(s["person"], s["place"], True)

    def _carry(self, s):
        self._causes.append(("item", s["container"]))
        self.reach(s["person"], s["container"])
        self.loc[s["container"]] = ("person", s["person"])
        self.moved(s["person"], s["place"], True)

    def _pick_up(self, s):
        self.learn(s["object"], ("place", self.pv[s["person"]]))
        self.loose_at(s["object"], self.pv[s["person"]])
        self.loc[s["object"]] = ("person", s["person"])

    def _fail_pick_up(self, s):
        self.learn(s["object"], ("place", self.pv[s["person"]]))
        self.loose_at(s["object"], self.pv[s["person"]])
        self.loc.setdefault(s["object"], ("place", self.pv[s["person"]]))

    def _put_down(self, s):
        node = self.at(s["place"])
        self.uf.union(self.pv[s["person"]], node)
        self.learn(s["object"], ("person", s["person"]))
        self.loc[s["object"]] = ("place", node)
        self.cause[s["object"]] = f"{s['person']} put it there"

    def _give(self, s):
        self.uf.union(self.pv[s["giver"]], self.pv[s["receiver"]])
        self.learn(s["object"], ("person", s["giver"]))
        self.loc[s["object"]] = ("person", s["receiver"])

    def _put_in(self, s):
        self.reach(s["person"], s["container"])
        self.learn(s["object"], ("person", s["person"]))
        self.loc[s["object"]] = ("container", s["container"])
        self.is_open[s["container"]] = True
        for family, _, r in self.rules.values():
            if family == "R5" and r["container"] == s["container"]:
                self.colour[s["object"]] = r["colour"]

    def _take_out(self, s):
        self.reach(s["person"], s["container"])
        self.learn(s["object"], ("container", s["container"]))
        self.loc[s["object"]] = ("person", s["person"])
        self.is_open[s["container"]] = True

    def _open(self, s):
        self.reach(s["person"], s["container"])
        self.is_open[s["container"]] = True

    def _close(self, s):
        self.reach(s["person"], s["container"])
        self.is_open[s["container"]] = False

    def _fail_open(self, s):
        self.reach(s["person"], s["container"])
        self.is_open[s["container"]] = False

    def _fail_put_in(self, s):
        self.reach(s["person"], s["container"])
        self.learn(s["object"], ("person", s["person"]))
        self.is_open[s["container"]] = False
        self.loc[s["object"]] = ("person", s["person"])

    def _swap(self, s):
        a, b = s["person"], s["person_b"]
        self.uf.union(self.pv[a], self.pv[b])
        other = {a: b, b: a}
        self.swaps[a].append(len(self.locs))
        self.swaps[b].append(len(self.locs))
        for item, cur in list(self.loc.items()):
            if cur[0] == "person" and cur[1] in other:
                self.loc[item] = ("person", other[cur[1]])
            elif cur[0] == "reach" and cur[1] in other:
                self.loc[item] = ("reach", other[cur[1]], cur[2])

    def _traded(self, s):
        person = s["person"]
        for family, _, r in self.rules.values():
            if family == "R8" and r["count"] == s["count"] and r["object_kind"] == s["object_kind"]:
                self.uf.union(self.pv[person], self.at(r["place"]))
        self._causes.append(("trade", person, s["object_kind"]))
        for item, cur in list(self.loc.items()):
            if cur == ("person", person) and self.ent[item]["type"] == "object" and self.ent[item]["kind"] == s["object_kind"]:
                self.loc[item] = (GONE,)
        self.loc[s["item"]] = ("person", person)
        self.born[s["item"]] = len(self.locs)

    def _breaks(self, s): pass

    def _moved_by_place(self, s):
        cur = self.loc.get(s["object"])
        if cur and cur[0] == "place" and self.uf.get(cur[1]) == s["place2"]:
            return  # already derived from the stated rule
        self.learn(s["object"], ("place", self.at(s["place"])))
        self.loose_at(s["object"], self.at(s["place"]))
        self._causes.append(("item", s["object"]))
        self.loc[s["object"]] = ("place", self.at(s["place2"]))
        self.cause[s["object"]] = f"it was moved from {self.s(s['place'])} at {TIMES[self.time]}"

    def _returned(self, s):
        self._causes.append(("item", s["object"]))
        self.loc[s["object"]] = ("person", s["person"])
        self.owner[s["object"]] = s["person"]

    def _recoloured(self, s): self.colour[s["object"]] = s["colour"]

    def _new_day(self, s): self.day += 1

    def _time(self, s):
        self.time = TIMES.index(s["time"])
        self._period_pending = (self.day, self.time)
        for family, _, r in sorted(self.rules.values(), key=lambda x: x[0]):
            if r.get("time") != s["time"]:
                continue
            if family == "R3":
                for item, cur in list(self.loc.items()):
                    if (self.ent[item]["type"] == "object" and cur[0] == "place" and self.uf.get(cur[1]) == r["place"]):
                        self._causes.append(("item", item))
                        self.loc[item] = ("place", self.at(r["place2"]))
                        self.cause[item] = f"it was moved from {self.s(r['place'])} at {s['time']}"
            elif family == "R4":
                for item, cur in list(self.loc.items()):
                    if self.ent[item]["type"] == "object" and cur[0] == "place" and item in self.owner:
                        self._causes.append(("item", item))
                        self.loc[item] = ("person", self.owner[item])
            elif family == "R7":
                before = self.uf.get(self.pv[r["person"]])
                self.moved(r["person"], r["place"], before is not None and before != r["place"])

    def _intro_person(self, s): self.uf.union(self.pv[s["person"]], self.at(s["place"]))

    def _intro_object(self, s):
        self.learn(s["object"], ("place", self.at(s["place"])))
        cur = self.loc.get(s["object"])
        if cur is not None and cur[0] in ("place", "reach"):
            self.loose_at(s["object"], self.at(s["place"]))  # the same stay: the cause still holds
            self.loc[s["object"]] = ("place", cur[1] if cur[0] == "place" else cur[2])
        else:
            self.cause[s["object"]] = None
            self.loc[s["object"]] = ("place", self.at(s["place"]))

    def _intro_in(self, s):
        self.learn(s["object"], ("container", s["container"]))
        self.loc[s["object"]] = ("container", s["container"])

    def _intro_holds(self, s):
        self.learn(s["object"], ("person", s["person"]))
        self.loc[s["object"]] = ("person", s["person"])

    def _owner(self, s): self.owner[s["object"]] = s["person"]

    def _material(self, s): self.material[s["object"]] = s["material"]

    def _kind_group(self, s): self.category[s["object_kind"]] = s["category"]

    def _is_open(self, s):
        self.is_open[s["container"]] = True
        self.complete.add(s["container"])  # scene convention: a described container's contents came just before

    def _is_closed(self, s):
        self.is_open[s["container"]] = False
        self.complete.add(s["container"])

    def _layout_dir(self, s): self.dirs.add((s["place"], s["direction"], s["place2"]))

    def _layout_next(self, s): self.nexts.add(frozenset((s["place"], s["place2"])))

    # ------------------------------------------------------------ resolving

    def s(self, eid: str) -> str:
        entity = self.ent[eid]
        return f"the {self.colour[eid]} {entity['kind']}" if entity["type"] == "object" else f"the {entity['kind']}"

    def rnode(self, item: str) -> Any:
        """The node of the item's resolved place, GONE, or None when unknown."""
        cur = self.loc.get(item)
        if cur is None:
            return None
        if cur[0] == "place":
            return cur[1]
        if cur[0] == "person":
            return self.pv[cur[1]]
        if cur[0] == "container":
            return self.rnode(cur[1])
        if cur[0] == GONE:
            return GONE
        return cur[2] if self.uf.same(cur[2], self.pv[cur[1]]) else None

    def value(self, node: Any) -> Any:
        return node if node in (None, GONE) else self.uf.get(node)

    def rplace(self, item: str) -> Any:
        return self.value(self.rnode(item))

    def holders(self, item: str) -> Optional[frozenset]:
        """Who might hold the item (NOBODY = lying at a place); None when anyone might."""
        cur = self.loc.get(item)
        if cur is None or cur[0] == GONE:
            return None
        if cur[0] == "place":
            return frozenset((NOBODY,))
        if cur[0] == "person":
            return frozenset((cur[1],))
        if cur[0] == "reach":
            return frozenset((cur[1], NOBODY))
        return self.holders(cur[1])

    # ------------------------------------------------------------ answers

    def answer(self, q: Mapping[str, Any]) -> str:
        bank = q["bank"]
        if bank in RULE_SUBJECTS:
            return self.rule_question(bank, q["slots"])
        return getattr(self, "q_" + bank[2:])(q["slots"])

    def q_where_object(self, s):
        v = self.rplace(s["object"])
        return self.s(v) if v not in (None, GONE) else NOT_TOLD

    def q_where_person(self, s):
        v = self.uf.get(self.pv[s["person"]])
        return self.s(v) if v else NOT_TOLD

    def q_who_has(self, s):
        h = self.holders(s["object"])
        return next(iter(h)) if h is not None and len(h) == 1 else NOT_TOLD

    def q_in_container(self, s):
        box = s["container"]
        members = [i for i, cur in self.loc.items() if cur == ("container", box)]
        if box in self.complete:
            return listing(self.s(i) for i in members)
        return NOT_TOLD if not members else "PARTIAL"

    def loc_at(self, item: str, k: int) -> Optional[tuple]:
        cur = self.locs[k].get(item)
        if cur is not None:
            return cur
        found = self.retro.get(item)
        if found is None or k >= found[0]:
            return None
        before = found[1]
        if before[0] == "person" and any(k < g <= found[0] for g in self.swaps.get(before[1], ())):
            return None
        return before

    def value_at(self, item: str, k: int) -> Any:
        cur = self.loc_at(item, k)
        if cur is None:
            return None
        if cur[0] == "place":
            return self.uf.get(cur[1])
        if cur[0] == "person":
            return self.uf.get(self.pvs[k][cur[1]])
        if cur[0] == "container":
            return self.value_at(cur[1], k)
        if cur[0] == GONE:
            return GONE
        return self.uf.get(cur[2]) if self.uf.same(cur[2], self.pvs[k][cur[1]]) else None

    def inside(self, item: str, other: str, k: int) -> bool:
        """Might `item` be `other`, or inside it, at action k (containers never nest)?"""
        if item == other:
            return True
        cur = self.loc_at(item, k)
        if cur is None:
            return self.ent[item]["type"] == "object" and self.ent[other]["type"] == "container"
        return cur == ("container", other)

    def with_person(self, item: str, person: str, k: int) -> bool:
        cur = self.loc_at(item, k)
        if cur is None:
            return True
        if cur[0] in ("person", "reach"):
            return cur[1] == person
        return cur[0] == "container" and self.with_person(cur[1], person, k)

    def moved_at(self, item: str, k: int) -> bool:
        """Might action k have changed the item's resolved place (judged from the state before it)?"""
        for cause in self.causes[k]:
            if cause[0] == "item" and self.inside(item, cause[1], k - 1):
                return True
            if cause[0] == "person" and self.with_person(item, cause[1], k - 1):
                return True
            if (cause[0] == "trade" and self.ent[item]["type"] == "object" and self.ent[item]["kind"] == cause[2]
                    and self.with_person(item, cause[1], k - 1)):
                return True
        return False

    def stays(self, item: str) -> list[tuple[int, int, Any]]:
        """The item's history as (first, last action, place or None): within a stay nothing could move it."""
        out: list[list] = []
        for k in range(self.born.get(item, 0), len(self.locs)):
            v = self.value_at(item, k)
            if out and not self.moved_at(item, k):
                stay = out[-1]
                if v is not None and stay[2] is not None and v != stay[2]:
                    raise AssertionError(f"reference: {item} changed place from {stay[2]} to {v} with nothing moving it")
                stay[1], stay[2] = k, stay[2] if v is None else v
            else:
                out.append([k, k, v])
        return [tuple(stay) for stay in out]

    def q_where_before(self, s):
        stays = self.stays(s["object"])
        now = stays[-1][2]
        if now in (None, GONE):
            return NOT_TOLD if now is None else "GONE"
        for _, _, v in reversed(stays[:-1]):
            if v == now:
                continue
            return NOT_TOLD if v is None else (self.s(v) if v != GONE else "WAS GONE")
        return "NO CHANGE"

    def q_where_at_time(self, s):
        t = TIMES.index(s["time"])
        start, stop = self.period.get((self.day, t)), self.period.get((self.day, t + 1))
        if start is None or stop is None:
            return "NO PERIOD"
        values = {v for first, last, v in self.stays(s["object"]) if first < stop and last >= start}
        if None in values:
            return NOT_TOLD
        return self.s(values.pop()) if len(values) == 1 else "CHANGED"

    def _count(self, kind: str, hit) -> str:
        count = 0
        for o in self.seen:
            if self.ent[o]["type"] != "object" or self.ent[o]["kind"] != kind or self.loc.get(o) == (GONE,):
                continue
            found = hit(o)
            if found is None:
                return NOT_TOLD
            count += found
        return vocab.NUMBER_WORDS[count]

    def q_count_at(self, s):
        def hit(o):
            v = self.rplace(o)
            return None if v is None else v == s["place"]
        return self._count(s["object_kind"], hit)

    def q_count_held(self, s):
        def hit(o):
            h = self.holders(o)
            if h is not None and s["person"] not in h:
                return False
            return None if h is None else h == {s["person"]}
        return self._count(s["object_kind"], hit)

    def q_compare_count(self, s):
        a = self.q_count_at({"object_kind": s["object_kind"], "place": s["place"]})
        b = self.q_count_at({"object_kind": s["object_kind"], "place": s["place2"]})
        if NOT_TOLD in (a, b):
            return NOT_TOLD
        a, b = vocab.NUMBER_WORDS.index(a), vocab.NUMBER_WORDS.index(b)
        return "EQUAL" if a == b else self.s(s["place"] if a > b else s["place2"])

    def q_direction(self, s):
        edges = defaultdict(set)
        for a, d, b in self.dirs:
            edges[(b, d)].add(a)
            edges[(a, OPPOSITE[d])].add(b)
        for d in OPPOSITE:
            frontier, seen = [s["place"]], {s["place"]}
            while frontier:
                nxt = [y for x in frontier for y in edges[(x, d)] if y not in seen]
                if s["place2"] in nxt:
                    return d
                seen.update(nxt)
                frontier = nxt
        return NOT_TOLD

    def q_next_to(self, s):
        near = {q for pair in self.nexts if s["place"] in pair for q in pair if q != s["place"]}
        return self.s(near.pop()) if len(near) == 1 else (NOT_TOLD if not near else "MANY")

    def q_what_if(self, s):
        bank, a = s["action"]["bank"], s["action"]["slots"]
        stated = [(family, b, r) for family, b, r in self.rules.values()]
        if bank == "ev.put_down":
            obj, unknown = a["object"], False
            for family, _, r in stated:
                if family != "R1":
                    continue
                known = self.material.get(obj) if "material" in r else self.category.get(self.ent[obj]["kind"])
                if known is None:
                    unknown = True
                elif known == r.get("material", r.get("category")):
                    return f"{self.s(obj)} would break"
            return NOT_TOLD if unknown else "nothing would happen"
        if bank == "ev.put_in":
            obj = a["object"]
            for family, _, r in stated:
                if family == "R5" and r["container"] == a["container"]:
                    return "nothing would happen" if self.colour[obj] == r["colour"] else f"{self.s(obj)} would turn {r['colour']}"
            return "nothing would happen"
        if bank == "ev.open":
            if self.is_open.get(a["container"]):
                return "nothing would happen"
            for family, _, r in stated:
                if family == "R6" and r["container"] == a["container"] and r["person"] != a["person"]:
                    return f"{self.s(a['container'])} would stay shut"
            return f"{self.s(a['container'])} would open"
        if bank == "ev.go":
            followers = [r["person"] for family, _, r in stated if family == "R2" and r["leader"] == a["person"]]
            return f"{followers[0]} would follow" if len(followers) == 1 else ("nothing would happen" if not followers else "MANY")
        return "UNKNOWN ACTION"

    def q_why_at(self, s):
        item = s["object"]
        v = self.rplace(item)
        if v != s["place"]:
            return NOT_TOLD if v is None else "NOT THERE"
        cur = self.loc[item]
        if cur[0] == "person":
            return f"{cur[1]} has it"
        if cur[0] == "container":
            return f"it is in {self.s(cur[1])}"
        return (self.cause.get(item) or NOT_TOLD) if cur[0] == "place" else NOT_TOLD

    def q_plan_get(self, s):
        person, item = s["person"], s["object"]
        me = self.uf.get(self.pv[person])
        steps: list[str] = []

        def go(place: Optional[str]) -> None:
            if place is None:
                raise LookupError
            if place != me:
                steps.append(f"go to {self.s(place)}")

        def held_by(who: str) -> str:
            return self.uf.get(self.pv[who])

        try:
            cur = self.loc.get(item)
            if cur is None or cur[0] in ("reach", GONE):
                raise LookupError
            if cur[0] == "place":
                go(self.uf.get(cur[1]))
                steps.append(f"pick up {self.s(item)}")
            elif cur[0] == "person":
                if cur[1] == person:
                    return "ALREADY HELD"
                go(held_by(cur[1]))
                steps.append(f"ask {cur[1]} for {self.s(item)}")
            else:
                box = cur[1]
                where = self.loc.get(box)
                if where is None or where[0] == "reach":
                    raise LookupError
                if where[0] == "place":
                    go(self.uf.get(where[1]))
                elif where[1] != person:
                    go(held_by(where[1]))
                    steps.append(f"ask {where[1]} for {self.s(box)}")
                if self.is_open.get(box) is not True:
                    steps.append(f"open {self.s(box)}")
                steps.append(f"take {self.s(item)} out of {self.s(box)}")
        except LookupError:
            return NOT_TOLD
        return ", ".join(steps)

    def rule_question(self, bank: str, s: Mapping[str, Any]) -> str:
        slot, fields = RULE_SUBJECTS[bank]
        found = [(b, r) for family, b, r in self.rules.values()
                 if any(r.get(f) == s[slot] for f in fields.get(family, ()))]
        if len(found) != 1:
            return NOT_TOLD if not found else "MANY"
        b, r = found[0]
        values = {}
        for name, value in r.items():
            if name in ("place", "place2", "container"):
                value = self.s(value)
            elif name == "count":
                value = vocab.NUMBER_WORDS[value]
            elif name == "object_kind":
                value = vocab.PLURAL[value]
            elif name == "item":
                value = ("an " if value[:1] in "aeiou" else "a ") + value
            values[name] = value
        return RULE_FORMS[b].format(**values)

    def q_yn_at(self, s):
        v = self.rplace(s["object"])
        if v in (None, GONE):
            return NOT_TOLD
        return "yes" if v == s["place"] else "no"

    def q_yn_has(self, s):
        h = self.holders(s["object"])
        if h is None:
            v, mine = self.rplace(s["object"]), self.uf.get(self.pv[s["person"]])
            return "no" if v not in (None, GONE) and mine is not None and v != mine else NOT_TOLD
        if s["person"] not in h:
            return "no"
        return "yes" if len(h) == 1 else NOT_TOLD

    def q_yn_in(self, s):
        cur = self.loc.get(s["object"])
        if cur is None:
            return "no" if s["container"] in self.complete else NOT_TOLD
        return "yes" if cur == ("container", s["container"]) else "no"


def listing(names) -> str:
    names = sorted(names)
    if not names:
        return NOTHING
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


# ================================================================ the tests
# Everything below may use the generator and the oracle; the Reference above never does.

SPLITS = ("train", "validation", "test")


def disagreements(visits, key=lambda visit: visit["id"]) -> tuple[list, Counter]:
    """Feed visits in order to References (one per `key`: a visit, or a village of a life); every
    (question id, bank, oracle answer, reference answer) that differs."""
    refs: dict[Any, Reference] = {}
    bad, stats = [], Counter()
    for visit in visits:
        ref = refs.setdefault(key(visit), Reference(visit["people"]))
        for q, mine in ref.feed(visit):
            stats["questions"] += 1
            stats["not told"] += q["answer"] == NOT_TOLD
            if mine != q["answer"]:
                bad.append((q["id"], q["bank"], q["answer"], mine))
        stats["visits"] += 1
    return bad, stats


class ReferenceAgreementTests(unittest.TestCase):
    """A second interpreter, written from the spec, gives the oracle's answer to every question."""

    def test_standalone_visits(self):
        bad, stats = disagreements(scheduler.generate_visit(split, seed) for split in SPLITS for seed in range(100))
        self.assertGreaterEqual(stats["visits"], 300)
        self.assertGreaterEqual(stats["questions"], 2000)
        self.assertGreater(stats["not told"], 50)
        self.assertEqual(bad, [])

    def test_lives_with_revisits(self):
        bad, stats = disagreements([v for split in SPLITS for seed in range(6) for v in scheduler.generate_life(split, seed, 5)],
                                   key=lambda v: (v["id"].rsplit("-", 1)[0], v["village"]))
        self.assertGreater(stats["questions"], 500)
        self.assertEqual(bad, [])

    def test_the_references_final_beliefs_are_true(self):
        for split in SPLITS:
            for seed in range(15):
                vis, view = scheduler._standalone(split, seed, None, None, scheduler.VISIBLE_LINES)
                visit = scheduler._package(vis, view, seed)
                ref = Reference(visit["people"])
                ref.feed(visit)
                world = vis.world
                for item in world.items:
                    believed = ref.rplace(item)
                    if believed is not None:
                        truth = world.place_of(item)
                        self.assertEqual(believed, GONE if truth is None else truth, (visit["id"], item))
                for person in world.people:
                    believed = ref.uf.get(ref.pv[person])
                    if believed is not None:
                        self.assertEqual(believed, world.people[person], (visit["id"], person))


class RegressionTests(unittest.TestCase):
    """Hand-built cases for the bugs this review found and fixed."""

    def test_a_follow_of_an_uncertain_follower_is_narrated(self):
        # Tavi follows Rami and Kelo follows Tavi. Where Tavi was is unknown, so Tavi may have been at the
        # barn already, and then Kelo would not move: Kelo's follow cannot be silent.
        w = small_world([make_rule("R2", person="Tavi", leader="Rami"), make_rule("R2", person="Kelo", leader="Tavi")])
        s = Scene(w, intro=[("ev.intro_person", {"person": "Rami", "place": "p0"})])
        s.rule(0)
        s.rule(1)
        silent = []
        for rec in s.w.act("go", person="Rami", place="p1"):
            record = {"kind": "event", **rec, "silent": False}
            record["silent"] = bool(rec["meta"].get("rule")) and s.obs.can_derive(record)
            silent.append((rec["slots"]["person"], record["silent"]))
            s._feed(record)
        s.obs.snapshot(s.w)
        self.assertEqual(silent, [("Rami", False), ("Tavi", True), ("Kelo", False)])
        self.assertEqual(s.ask("q.where_person", person="Kelo").answer, "the barn")

    def test_picking_up_a_thing_places_the_person(self):
        s = Scene(small_world(), intro=[("ev.intro_object", {"object": "o0", "place": "p0"})])
        self.assertEqual(s.ask("q.where_person", person="Nera").answer, NOT_TOLD)
        s.act("pick_up", person="Nera", item="o0")
        got = s.ask("q.where_person", person="Nera")
        self.assertEqual((got.answer, got.depth), ("the mill", 2))

    def test_a_fully_described_box_answers_no_for_other_things(self):
        w = small_world()
        w.items["o1"].loc = ("container", "c0")
        s = Scene(w, intro=[("ev.is_open", {"container": "c0"}), ("ev.intro_in", {"object": "o1", "container": "c0"})])
        s.obs.complete["c0"] = s.obs.is_open["c0"][1]  # the scene's convention: every content is listed next
        self.assertEqual(s.ask("q.yn_in", object="o0", container="c0").answer, "no")
        self.assertEqual(s.ask("q.yn_in", object="o1", container="c0").answer, "yes")

    def test_one_sentence_giving_two_links_is_one_read(self):
        w = small_world()
        w.items["o1"].loc = ("container", "c0")
        w.items["c0"].loc = ("person", "Kelo")
        s = Scene(w, intro=[("ev.intro_in", {"object": "o1", "container": "c0"})])
        s.act("carry", person="Kelo", container="c0", place="p2")  # the box is Kelo's and Kelo is at the well
        got = s.ask("q.where_object", object="o1")
        self.assertEqual((got.answer, got.depth), ("the well", 2))

    def test_a_scheduled_move_does_not_deepen_a_known_place(self):
        w = small_world([make_rule("R7", person="Nera", place="p2", time="noon")])
        s = Scene(w)
        s.rule(0)
        s.act("go", person="Nera", place="p2")
        s.act("time", quiet=True)  # noon: Nera is already at the well, so nothing is said
        got = s.ask("q.where_person", person="Nera")
        self.assertEqual((got.answer, got.depth, got.families), ("the well", 1, []))

    def test_a_recolour_costs_a_step_only_when_the_old_colour_is_used(self):
        s = Scene(small_world(), intro=[("ev.intro_object", {"object": "o1", "place": "p0"})])
        s.w.items["o1"].colour = "white"
        s.say("ev.recoloured", object="o1", colour="white")
        got = s.ask("q.where_object", object="o1")
        self.assertEqual((got.answer, got.depth), ("the mill", 2))  # "the blue cup is at the mill" + the recolour
        s.act("pick_up", person="Kelo", item="o1")
        s.act("go", person="Kelo", place="p1")
        got = s.ask("q.where_object", object="o1")
        self.assertEqual((got.answer, got.depth), ("the barn", 2))  # read by its new colour

    def test_a_thing_with_no_material_never_matches_a_rule(self):
        w = small_world([make_rule("R1", category="clothes")])
        w.items["o0"].material = None  # food has no material; the category rule's missing material is None too
        self.assertIsNone(w.breaks_on_put_down("o0"))

    def test_village_names_are_unique_within_a_life(self):
        for split in SPLITS:
            for seed in range(12):
                cast: dict[str, tuple] = {}
                for visit in scheduler.generate_life(split, seed, 6):
                    people = tuple(sorted(visit["people"]))
                    self.assertEqual(cast.setdefault(visit["village"], people), people, visit["id"])


class ObserverHonestyTests(unittest.TestCase):
    def test_no_false_belief_and_not_told_only_when_the_truth_was_never_given(self):
        # Observer.check(world) runs after every action while generating; any false belief raises.
        bad, stats = disagreements([v for split in SPLITS for seed in range(100, 106)
                                    for v in scheduler.generate_life(split, seed, 4)],
                                   key=lambda v: (v["id"].rsplit("-", 1)[0], v["village"]))
        self.assertEqual(bad, [])  # includes every "not told": the reference cannot answer it either
        self.assertGreater(stats["not told"], 10)


def captured_plans(visits_per_split: int) -> list:
    """(world copy, person, item, canonical plan) for every knowable plan question the scheduler weighs."""
    captured, original = [], scheduler.ask

    def spy(obs, world, bank, slots):
        answer = original(obs, world, bank, slots)
        if bank == "q.plan_get" and answer is not None and answer.knowable:
            captured.append((world.copy(), slots["person"], slots["object"], answer.answer))
        return answer

    with mock.patch.object(scheduler, "ask", spy):
        for split in SPLITS:
            for seed in range(visits_per_split):
                scheduler.generate_visit(split, seed)
    return captured


def must_fail(world, person: str, item: str, text: str) -> list[tuple[str, str]]:
    """Mutations of a working plan that cannot work: a needed go dropped or aimed elsewhere, the order
    rotated, the last step dropped, a needed open dropped."""
    steps = [step.strip() for step in text.split(",")]
    out = [("missing last step", ", ".join(steps[:-1]))]
    goes = [i for i, step in enumerate(steps) if step.startswith("go to ")]
    if goes and world.people[person] != parse_plan(world, steps[goes[0]])[0][1]:
        i = goes[0]
        if not any(rule.get("leader") == person for _, rule in world.rules_of("R2")):  # else a follower comes along
            other = next(p for p in sorted(world.places) if p != parse_plan(world, steps[i])[0][1])
            out.append(("wrong place", ", ".join(steps[:i] + [f"go to {surface(world, other)}"] + steps[i + 1:])))
        out.append(("missing go", ", ".join(steps[:i] + steps[i + 1:])))
        out.append(("wrong order", ", ".join([steps[-1]] + steps[:-1])))
    opens = [i for i, step in enumerate(steps) if step.startswith("open ")]
    if opens and not world.items[parse_plan(world, steps[opens[0]])[0][1]].open:
        out.append(("missing open", ", ".join(steps[:opens[0]] + steps[opens[0] + 1:])))
    return [(name, plan) for name, plan in out if plan]


class PlanTests(unittest.TestCase):
    def test_canonical_plans_pass_and_broken_ones_fail(self):
        plans = captured_plans(25)
        self.assertGreater(len(plans), 500)
        kinds = Counter()
        for world, person, item, text in plans:
            before = repr(world.items[item]), dict(world.people)
            self.assertTrue(check_plan(world, person, item, text), text)
            for name, plan in must_fail(world, person, item, text):
                kinds[name] += 1
                self.assertFalse(check_plan(world, person, item, plan), (name, text, plan))
            self.assertEqual((repr(world.items[item]), dict(world.people)), before)  # the checker changes nothing
        self.assertGreaterEqual(set(kinds), {"missing last step", "wrong place", "missing go", "wrong order", "missing open"})


class HeldOutTests(unittest.TestCase):
    def test_rule_families_depth_and_split_limits(self):
        for split in SPLITS:
            for seed in range(60):
                visit = scheduler.generate_visit(split, seed)
                families = {rule["family"] for rule in visit["rules"]}
                used = set(visit["provenance"].get("rule_family", ()))
                self.assertTrue(all(item.endswith(":" + split) for item in used), used)
                if split == "train":
                    self.assertNotIn("R8:train", used)
                    self.assertNotIn("R8", families)
                for q in scheduler.questions_of(visit):
                    if split == "train":
                        self.assertLessEqual(q["depth"], 3)
                        self.assertLessEqual(q["rule_applications"], 1)
                        self.assertLessEqual(len(set(q["families"])), 1)
                        self.assertNotIn("R8", q["families"])
                    elif split == "validation":
                        self.assertLessEqual(len(set(q["families"])), 1)

    def test_rendered_visits_pass_the_split_audit_and_the_registry_stays_disjoint(self):
        source = stream.default_source()
        registry = stream.default_registry(source)
        for split in SPLITS:
            rendered = [stream.render_visit(scheduler.generate_visit(split, seed), source, registry) for seed in range(40)]
            stream.audit(rendered, registry, source, names.all_names())
        registry.assert_disjoint()

    def test_manifests_round_trip_and_verify(self):
        registry = scheduler.make_registry()
        text = registry.manifest().to_json()
        self.assertEqual(SplitManifest.from_json(text), registry.manifest())
        scheduler.generate_visit("train", 0, registry=registry)  # using the registry never changes the assignment
        registry.verify_manifest(text)
        SplitRegistry.from_manifest(text).verify_manifest(registry.manifest())


class LeakTests(unittest.TestCase):
    def test_no_answer_in_its_input_and_the_simple_classes_are_clean(self):
        source = stream.default_source()
        registry = stream.default_registry(source)

        def sample(split: str, visits: int, offset: int) -> list:
            out = []
            for seed in range(offset, offset + visits):
                examples = stream.to_qa_examples(scheduler.generate_visit(split, seed), source=source, registry=registry)
                by_class: dict[str, list] = defaultdict(list)
                for e in examples:  # one question per class per visit, so the items are independent
                    by_class[e.answer if e.answer in stream.SPECIAL_ANSWERS else stream.answer_class(e)].append(e)
                out.extend(group[seed % len(group)] for group in by_class.values())
            return out

        reports = stream.leak_reports(sample("train", 160, 7000), sample("test", 120, 7000))
        for name, report in reports.items():
            self.assertEqual(report.answer_in_input_rate, 0.0, name)
        for name in ("yes/no", "direction", "count", "rule", "plan", "why"):
            self.assertFalse(reports[name].leaking, (name, reports[name].leaking_detectors))


class TwinTests(unittest.TestCase):
    def test_twins_read_the_same_and_both_answers_are_right(self):
        source = stream.default_source()
        links = 0
        for split in SPLITS:
            for seed in range(8):
                a, b = scheduler.counterfactual_pair(split, seed)
                ra, rb = (stream.render_visit(v, source) for v in (a, b))
                text = {q["id"]: q["question"] for r in (ra, rb) for q in r.questions}
                mine = {q["id"]: answer for v in (a, b) for q, answer in Reference(v["people"]).feed(v)}
                qa = {q["id"]: q for q in scheduler.questions_of(a)}
                for qb in scheduler.questions_of(b):
                    if qb["twin"] is None:
                        continue
                    first = qa[qb["twin"]]
                    links += 1
                    self.assertEqual(text[first["id"]], text[qb["id"]])
                    self.assertNotEqual(first["answer"], qb["answer"])
                    self.assertEqual((mine[first["id"]], mine[qb["id"]]), (first["answer"], qb["answer"]))
        self.assertGreater(links, 20)


if __name__ == "__main__":
    unittest.main()
