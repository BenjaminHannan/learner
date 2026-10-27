"""Village v0 world, observer (oracle) and scheduler: rule semantics, honesty, depth, splits, twins."""
import re
import unittest

from learnlab.splits import audit_examples
from learnlab.village import names, vocab
from learnlab.village.oracle import (
    NOT_TOLD, RULE_FORMS, WHAT_IF_FORMS, Observer, ask, check_plan, parse_plan, truth_answer,
)
from learnlab.village.scheduler import (
    MAX_DEPTH, counterfactual_pair, generate_life, generate_visit, make_registry, questions_of,
)
from learnlab.village.world import Item, World, make_rule

SPLITS = ("train", "validation", "test")


def small_world(rules=(), people=("Kelo", "Rami", "Tavi", "Nera")) -> World:
    places = {"p0": {"kind": "mill", "cell": (0, 0)}, "p1": {"kind": "barn", "cell": (0, 2)},
              "p2": {"kind": "well", "cell": (3, 0)}, "p3": {"kind": "market", "cell": (5, 5)}}
    items = {
        "o0": Item("o0", "object", "cup", ("place", "p0"), "red", "glass", "Kelo"),
        "o1": Item("o1", "object", "cup", ("place", "p0"), "blue", "wood", None),
        "o2": Item("o2", "object", "key", ("person", "Rami"), "green", "iron", "Tavi"),
        "c0": Item("c0", "container", "box", ("place", "p1"), open=True),
        "c1": Item("c1", "container", "chest", ("place", "p2"), open=False),
    }
    world = World(8, places, {p: "p0" for p in people}, items, list(rules))
    world.labels = {(it.kind, it.colour) for it in items.values() if it.type == "object"}
    return world


class Scene:
    """Feeds a hand-built world's records to an observer, as the scheduler does."""

    def __init__(self, world: World, intro=()) -> None:
        self.w, self.obs, self.line = world, Observer(world), 0
        self.say("ev.new_day")
        for bank, slots in intro:  # the scene is described before the morning, as the scheduler does
            self.say(bank, **slots)
        self.say("ev.time", time=world.now)

    def _feed(self, record: dict) -> None:
        self.obs.observe(record, (0, self.line))
        self.line += 1

    def say(self, bank: str, meta=None, **slots) -> None:
        self._feed({"kind": "event", "bank": bank, "slots": slots, "meta": meta or {}, "silent": False})
        self.obs.snapshot(self.w)

    def rule(self, index: int) -> None:
        self._feed({"kind": "rule", "bank": self.w.rules[index].bank, "slots": self.w.rules[index].slots,
                    "meta": {"rule_index": index}})

    def act(self, action: str, quiet: bool = False, **args) -> list:
        out = self.w.act(action, **args)
        assert out is not None, (action, args)
        for rec in out:
            record = {"kind": "event", **rec, "silent": False}
            record["silent"] = bool(quiet and rec["meta"].get("rule") and self.obs.can_derive(record))
            self._feed(record)
        self.obs.snapshot(self.w)
        return out

    def ask(self, bank: str, **slots):
        return ask(self.obs, self.w, bank, slots)


def banks(out: list) -> list:
    return [r["bank"] for r in out]


class RuleSemanticsTests(unittest.TestCase):
    def test_r1_material_and_category_break_on_put_down(self):
        w = small_world([make_rule("R1", material="glass")])
        w.items["o0"].loc = w.items["o1"].loc = ("person", "Kelo")
        out = w.act("put_down", person="Kelo", item="o0")
        self.assertEqual(banks(out), ["ev.put_down", "ev.breaks"])
        self.assertEqual(out[1]["meta"], {"rule": "R1", "rule_index": 0})
        self.assertTrue(w.items["o0"].broken)
        self.assertEqual(banks(w.act("put_down", person="Kelo", item="o1")), ["ev.put_down"])
        self.assertEqual(banks(w.act("pick_up", person="Kelo", item="o0")), ["ev.fail_pick_up"])
        self.assertEqual(w.items["o0"].loc, ("place", "p0"))
        w = small_world([make_rule("R1", category="dishes")])
        w.items["o1"].loc = ("person", "Kelo")
        self.assertEqual(banks(w.act("put_down", person="Kelo", item="o1")), ["ev.put_down", "ev.breaks"])

    def test_r2_followers_move_with_their_leader_in_a_chain(self):
        w = small_world([make_rule("R2", person="Tavi", leader="Rami"), make_rule("R2", person="Kelo", leader="Tavi")])
        out = w.act("go", person="Rami", place="p1")
        self.assertEqual(banks(out), ["ev.go", "ev.follows", "ev.follows"])
        self.assertEqual([w.people[p] for p in ("Rami", "Tavi", "Kelo", "Nera")], ["p1", "p1", "p1", "p0"])
        self.assertEqual(w.place_of("o2"), "p1")  # Rami carries the key along

    def test_r3_moves_loose_objects_at_its_time_only(self):
        w = small_world([make_rule("R3", place="p0", place2="p3", time="night")])
        w.time = 1
        self.assertEqual(banks(w.act("time")), ["ev.time"])
        out = w.act("time")
        self.assertEqual(banks(out), ["ev.time", "ev.moved_by_place", "ev.moved_by_place"])
        self.assertEqual((w.place_of("o0"), w.place_of("o1"), w.place_of("o2")), ("p3", "p3", "p0"))
        self.assertEqual(banks(w.act("time")), ["ev.new_day", "ev.time"])
        self.assertEqual((w.day, w.now), (2, "morning"))

    def test_r4_returns_lost_owned_objects(self):
        w = small_world([make_rule("R4", time="noon")])
        w.people["Kelo"] = "p2"
        out = w.act("time")
        self.assertEqual(banks(out), ["ev.time", "ev.returned"])
        self.assertEqual(w.items["o0"].loc, ("person", "Kelo"))
        self.assertEqual(w.items["o1"].loc, ("place", "p0"))   # no owner
        self.assertEqual(w.items["o2"].loc, ("person", "Rami"))  # borrowed, not lost

    def test_r5_recolours_and_never_repeats_a_label(self):
        w = small_world([make_rule("R5", container="c0", colour="yellow")])
        w.people["Kelo"] = "p1"
        w.items["o1"].loc = w.items["o0"].loc = ("person", "Kelo")
        out = w.act("put_in", person="Kelo", item="o1", container="c0")
        self.assertEqual(banks(out), ["ev.put_in", "ev.recoloured"])
        self.assertEqual(w.items["o1"].colour, "yellow")
        self.assertIsNone(w.act("put_in", person="Kelo", item="o0", container="c0"))  # a second yellow cup
        self.assertEqual(w.items["o0"].loc, ("person", "Kelo"))

    def test_r6_permission_makes_other_attempts_fail(self):
        w = small_world([make_rule("R6", person="Rami", container="c1")])
        w.people["Kelo"] = w.people["Rami"] = "p2"
        out = w.act("open", person="Kelo", container="c1")
        self.assertEqual(banks(out), ["ev.fail_open"])
        self.assertFalse(w.items["c1"].open)
        self.assertEqual(banks(w.act("open", person="Rami", container="c1")), ["ev.open"])

    def test_r7_schedule_moves_the_person_and_followers(self):
        w = small_world([make_rule("R7", person="Nera", place="p2", time="noon"), make_rule("R2", person="Tavi", leader="Nera")])
        out = w.act("time")
        self.assertEqual(banks(out), ["ev.time", "ev.go", "ev.follows"])
        self.assertEqual(out[1]["meta"]["rule"], "R7")
        self.assertEqual((w.people["Nera"], w.people["Tavi"]), ("p2", "p2"))

    def test_r8_trades_exactly_count_objects_at_its_place(self):
        w = small_world([make_rule("R8", place="p3", count=2, object_kind="cup", item="lamp")])
        w.items["o0"].loc = w.items["o1"].loc = ("person", "Kelo")
        self.assertIsNone(w.act("trade", person="Kelo"))  # wrong place
        w.people["Kelo"] = "p3"
        out = w.act("trade", person="Kelo")
        self.assertEqual(banks(out), ["ev.traded"])
        new = out[0]["slots"]["item"]
        self.assertEqual((w.items["o0"].loc, w.items["o1"].loc), (("gone",), ("gone",)))
        self.assertEqual((w.items[new].kind, w.items[new].loc), ("lamp", ("person", "Kelo")))
        self.assertIsNone(w.place_of("o0"))
        self.assertIsNone(w.act("trade", person="Kelo"))


class PreconditionTests(unittest.TestCase):
    def test_actions_check_their_preconditions(self):
        w = small_world()
        w.people["Tavi"] = "p1"
        self.assertIsNone(w.act("give", giver="Rami", receiver="Tavi", item="o2"))  # not at the same place
        self.assertIsNone(w.act("pick_up", person="Tavi", item="o0"))              # not where Tavi is
        self.assertIsNone(w.act("go", person="Kelo", place="p0"))                  # already there
        self.assertIsNone(w.act("take_out", person="Tavi", item="o0", container="c0"))
        self.assertEqual(banks(w.act("give", giver="Rami", receiver="Kelo", item="o2")), ["ev.give"])
        self.assertIsNone(w.act("pick_up", person="Kelo", item="o9"))              # no such item

    def test_closed_container_blocks_put_in_and_take_out(self):
        w = small_world()
        w.people["Kelo"] = "p2"
        w.items["o0"].loc = ("person", "Kelo")
        self.assertEqual(banks(w.act("put_in", person="Kelo", item="o0", container="c1")), ["ev.fail_put_in"])
        self.assertEqual(w.items["o0"].loc, ("person", "Kelo"))
        w.items["o1"].loc = ("container", "c1")
        self.assertIsNone(w.act("take_out", person="Kelo", item="o1", container="c1"))

    def test_carry_moves_contents_and_swap_exchanges_holdings(self):
        w = small_world()
        w.people["Kelo"] = "p1"
        w.items["o1"].loc = ("container", "c0")
        self.assertEqual(banks(w.act("carry", person="Kelo", container="c0", place="p3")), ["ev.carry"])
        self.assertEqual((w.place_of("o1"), w.holder_of("o1")), ("p3", "Kelo"))
        w.people["Rami"] = "p3"
        self.assertEqual(banks(w.act("swap", person="Kelo", person_b="Rami")), ["ev.swap"])
        self.assertEqual((w.holder_of("o1"), w.holder_of("o2")), ("Rami", "Kelo"))


class ObserverTests(unittest.TestCase):
    def test_not_told_exactly_until_the_stream_tells(self):
        s = Scene(small_world())
        self.assertEqual(s.ask("q.where_object", object="o0").answer, NOT_TOLD)
        s.say("ev.intro_object", object="o0", place="p0")
        self.assertEqual(s.ask("q.where_object", object="o0").answer, "the mill")
        s.w.items["o1"].loc = ("container", "c0")
        s.say("ev.intro_in", object="o1", container="c0")
        self.assertEqual(s.ask("q.who_has", object="o1").answer, NOT_TOLD)   # where the box is: never told
        self.assertEqual(s.ask("q.yn_in", object="o1", container="c0").answer, "yes")
        s.say("ev.intro_object", object="c0", place="p1")
        self.assertEqual(s.ask("q.who_has", object="o1").answer, "nobody")
        self.assertEqual(s.ask("q.why_at", object="o0", place="p0").answer, NOT_TOLD)  # placed by a description only
        self.assertEqual(s.ask("q.where_person", person="Nera").answer, NOT_TOLD)
        s.act("go", person="Nera", place="p2")
        self.assertEqual(s.ask("q.where_person", person="Nera").answer, "the well")

    def test_a_rule_never_stated_cannot_fire_silently(self):
        s = Scene(small_world([make_rule("R2", person="Tavi", leader="Rami")]))
        out = s.w.act("go", person="Rami", place="p1")
        self.assertFalse(s.obs.can_derive({"kind": "event", **out[1]}))

    def test_depth_on_hand_built_chains_one_to_six(self):
        w = small_world([make_rule("R2", person="Tavi", leader="Rami"), make_rule("R2", person="Kelo", leader="Tavi")])
        w.items["c0"].loc = ("person", "Kelo")
        w.items["o1"].loc = ("container", "c0")
        s = Scene(w)
        for person in ("Rami", "Tavi", "Kelo"):
            s.say("ev.intro_person", person=person, place="p0")
        s.say("ev.intro_in", object="o1", container="c0")
        s.say("ev.intro_holds", person="Kelo", object="c0")
        self.assertEqual(s.ask("q.where_object", object="o1").depth, 3)  # cup -> box -> Kelo -> place
        s.rule(0)
        s.rule(1)
        s.act("go", quiet=True, person="Rami", place="p1")                 # both follows are silent
        cases = [
            ("q.where_person", {"person": "Rami"}, "the barn", 1),
            ("q.where_person", {"person": "Tavi"}, "the barn", 2),
            ("q.where_person", {"person": "Kelo"}, "the barn", 3),
            ("q.where_object", {"object": "o1"}, "the barn", 5),
            ("q.where_before", {"object": "o1"}, "the mill", 6),        # then (3) or now (5), the deeper, + 1
            ("q.plan_get", {"person": "Nera", "object": "o1"},
             "go to the barn, ask Kelo for the box, open the box, take the blue cup out of the box", 6),
        ]
        for bank, slots, answer, depth in cases:
            got = s.ask(bank, **slots)
            self.assertEqual((got.answer, got.depth), (answer, depth), bank)
        got = s.ask("q.where_object", object="o1")
        self.assertEqual((got.rule_applications, got.families), (2, ["R2"]))
        self.assertTrue(check_plan(w, "Nera", "o1", s.ask("q.plan_get", person="Nera", object="o1").answer))

    def test_silent_rules_and_history(self):
        w = small_world([make_rule("R3", place="p0", place2="p3", time="noon"), make_rule("R5", container="c0", colour="yellow")])
        s = Scene(w, intro=[("ev.intro_object", {"object": "o1", "place": "p0"})])
        s.rule(0)
        s.rule(1)
        out = s.act("time", quiet=True)  # noon: the blue cup is moved without a word; the unmentioned red cup aloud
        self.assertEqual([r["slots"]["object"] for r in out[1:]], ["o0", "o1"])
        got = s.ask("q.where_object", object="o1")
        self.assertEqual((got.answer, got.depth, got.families), ("the market", 2, ["R3"]))
        self.assertEqual(s.ask("q.why_at", object="o1", place="p3").answer, "it was moved from the mill at noon")
        self.assertEqual(s.ask("q.where_at_time", object="o1", time="morning").answer, "the mill")
        s.act("time")
        self.assertEqual(s.ask("q.where_at_time", object="o1", time="noon").answer, "the market")
        what_if = {"kind": "event", "bank": "ev.put_in", "slots": {"person": "Kelo", "object": "o1", "container": "c0"}}
        self.assertEqual(s.ask("q.what_if", action=what_if).answer, "the blue cup would turn yellow")

    def test_what_if_needs_the_identity_fact(self):
        w = small_world([make_rule("R1", material="glass")])
        s = Scene(w)
        s.rule(0)
        drop = {"kind": "event", "bank": "ev.put_down", "slots": {"person": "Kelo", "object": "o0", "place": "p0"}}
        self.assertEqual(s.ask("q.what_if", action=drop).answer, NOT_TOLD)
        s.say("ev.material", object="o0", material="glass")
        self.assertEqual(s.ask("q.what_if", action=drop).answer, "the red cup would break")
        wood = {"kind": "event", "bank": "ev.put_down", "slots": {"person": "Kelo", "object": "o1", "place": "p0"}}
        s.say("ev.material", object="o1", material="wood")
        self.assertEqual(s.ask("q.what_if", action=wood).answer, "nothing would happen")
        self.assertEqual(s.ask("q.rule_material", material="glass").answer, "things made of glass break when put down")


class PlanCheckerTests(unittest.TestCase):
    def test_accepts_any_working_plan_and_rejects_the_rest(self):
        w = small_world([make_rule("R6", person="Rami", container="c1")])
        w.people["Nera"] = "p2"
        good = ["go to the mill, pick up the red cup", "go to the barn, go to the mill, pick up the red cup",
                "Go to the mill, then pick up the red cup."]
        bad = ["pick up the red cup", "go to the barn, pick up the red cup", "go to the mill, pick up the red lamp",
               "", "go to the mill, pick up the red cup, fly away"]
        for plan in good:
            self.assertTrue(check_plan(w, "Nera", "o0", plan), plan)
        for plan in bad:
            self.assertFalse(check_plan(w, "Nera", "o0", plan), plan)
        self.assertIsNone(parse_plan(w, "go to the moon"))
        self.assertTrue(check_plan(w, "Nera", "o2", "go to the mill, ask Rami for the green key"))
        self.assertFalse(check_plan(w, "Nera", "o2", "ask Rami for the green key"))  # not at the same place
        w.items["o1"].loc = ("container", "c1")
        plan = "go to the well, open the chest, take the blue cup out of the chest"
        self.assertFalse(check_plan(w, "Nera", "o1", plan))  # only Rami can open the chest
        self.assertTrue(check_plan(w, "Rami", "o1", plan))
        self.assertEqual((w.people["Nera"], w.items["c1"].open), ("p2", False))  # the real state is untouched


def _visits(split, count, **kw):
    return [generate_visit(split, seed, **kw) for seed in range(count)]


_ANSWER_FORMS = [re.escape(x) for x in ("not told", "nobody", "nothing", "yes", "no")] + list(vocab.DIRECTIONS) + list(vocab.NUMBER_WORDS)


def _canonical(answer: str, people) -> bool:
    name = "(?:" + "|".join(map(re.escape, people)) + ")"
    thing = r"the (?:\w+ )?\w+"
    steps = rf"(?:go to {thing}|pick up {thing}|open {thing}|take {thing} out of {thing}|ask {name} for {thing})"
    forms = _ANSWER_FORMS + [name, rf"{thing}(?:(?:, | and ){thing})*", rf"{name} has it", rf"it is in {thing}",
                             rf"{name} put it there", rf"it was moved from {thing} at \w+", rf"{steps}(?:, {steps})*"]
    for form in list(RULE_FORMS.values()) + list(WHAT_IF_FORMS.values()):
        forms.append(re.sub(r"\\\{\w+\\\}", r"[\\w ]+?", re.escape(form)))
    return any(re.fullmatch(form, answer) for form in forms)


class SchedulerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.by_split = {split: _visits(split, 60) for split in SPLITS}

    def test_observer_never_believes_anything_false_over_500_visits(self):
        # Every action ends with Observer.check against the true world, and every known
        # answer is checked against the true state inside `ask`; generation would raise.
        count = 0
        for seed in range(500):
            visit = generate_visit(SPLITS[seed % 3], 1000 + seed)
            count += len(questions_of(visit))
        self.assertGreater(count, 3000)

    def test_split_rules_hold(self):
        for split, visits in self.by_split.items():
            for visit in visits:
                families = {r["family"] for r in visit["rules"]}
                if split == "train":
                    self.assertNotIn("R8", families)
                for q in questions_of(visit):
                    self.assertLessEqual(q["depth"], MAX_DEPTH[split])
                    if split == "train":
                        self.assertLessEqual(q["rule_applications"], 1)
                        self.assertNotIn("R8", q["families"])
                    if split != "test":
                        self.assertLessEqual(len(q["families"]), 1, q)
                self.assertTrue(all(i.endswith(":" + split) for i in visit["provenance"]["rule_family"]))
        deep = [q["depth"] for v in self.by_split["validation"] + self.by_split["test"] for q in questions_of(v)]
        self.assertTrue({4, 5} <= set(deep))

    def test_every_question_type_and_canonical_answers(self):
        seen = set()
        for visits in self.by_split.values():
            for visit in visits:
                for q in questions_of(visit):
                    seen.add(q["qtype"])
                    self.assertTrue(_canonical(q["answer"], visit["people"]), (q["bank"], q["answer"]))
                    self.assertEqual(q["knowable"], q["answer"] != NOT_TOLD)
                    self.assertEqual(q["qtype"] == "Q10", not q["knowable"])
        self.assertEqual(seen, {f"Q{i}" for i in range(1, 14)})

    def test_evidence_silence_and_ranges(self):
        for visits in self.by_split.values():
            for visit in visits:
                records = visit["records"]
                stated = set()
                for record in records:
                    inner = record.get("inner") or {}
                    if record["kind"] == "rule" or inner.get("kind") == "rule":
                        stated.add((record if record["kind"] == "rule" else inner)["meta"]["rule_index"])
                    if record.get("silent"):
                        self.assertIn(record["meta"]["rule_index"], stated, "silent firing of an unstated rule")
                for q in questions_of(visit):
                    if not q["knowable"]:
                        self.assertEqual((q["depth"], q["evidence"], q["families"]), (0, [], []))
                        continue
                    self.assertTrue(q["evidence"] or q["prior_evidence"])
                    for line in q["evidence"]:
                        self.assertLess(line, q["line"])
                        self.assertFalse(records[line].get("silent"))
                    visible = all(line >= q["line"] - 40 for line in q["evidence"]) and not q["prior_evidence"]
                    self.assertEqual(q["range"], "visible" if visible else "long_range")

    def test_answers_match_the_true_state_when_asked(self):
        from learnlab.village import scheduler
        checked = []
        original = scheduler._Visit._question

        def question(vis, step, answer):
            truth = truth_answer(vis.world, step["bank"], step["slots"])
            if answer.knowable and truth is not None:
                checked.append(answer.answer == truth)
            return original(vis, step, answer)

        scheduler._Visit._question = question
        try:
            for split in SPLITS:
                for seed in range(20):
                    generate_visit(split, 500 + seed)
        finally:
            scheduler._Visit._question = original
        self.assertGreater(len(checked), 150)
        self.assertTrue(all(checked))

    def test_provenance_passes_the_split_audit(self):
        registry = make_registry()
        visits = [generate_visit(split, seed, registry=registry) for split in SPLITS for seed in range(20)]

        def text_of(visit):
            people = {v for r in visit["records"] for k, v in (r.get("slots") or {}).items()
                      if k in ("person", "person_b", "giver", "receiver", "leader")}
            return ". ".join(sorted(people) + [visit["village"]])

        report = audit_examples(visits, registry, text_of=text_of, vocab={"name": names.all_names()})
        self.assertEqual(report["examples"], 60)
        registry.assert_disjoint()
        for visit in visits:
            self.assertEqual(set(visit["provenance"]), {"name", "teacher_style", "rule_family"})
        self.assertEqual(set(names.people_names()) & set(names.village_names()), set())

    def test_twins_differ_in_answer_only(self):
        linked = 0
        for seed in range(8):
            first, twin = counterfactual_pair("test", seed)
            others = {q["id"]: q for q in questions_of(twin)}
            for q in questions_of(first):
                if not q["twin"]:
                    continue
                t = others[q["twin"]]
                linked += 1
                self.assertEqual((t["bank"], t["slots"], t["surface"], t["twin"]), (q["bank"], q["slots"], q["surface"], q["id"]))
                self.assertNotEqual(t["answer"], q["answer"])
                self.assertTrue(q["knowable"] and t["knowable"])
        self.assertGreaterEqual(linked, 5)

    def test_determinism_and_lives(self):
        self.assertEqual(generate_visit("validation", 11), generate_visit("validation", 11))
        self.assertNotEqual(generate_visit("validation", 11)["records"], generate_visit("validation", 12)["records"])
        life = list(generate_life("train", 4, 16))
        self.assertEqual(life, list(generate_life("train", 4, 16)))
        villages = [v["village"] for v in life]
        self.assertLess(len(set(villages)), len(villages))  # villages come back
        ids = {v["id"] for v in life}
        prior = [p for v in life for q in questions_of(v) for p in q["prior_evidence"]]
        self.assertTrue(prior and all(visit_id in ids for visit_id, _ in prior))
        first = last = 0  # Zipf-bursty cast: the top-ranked person acts far more than the last
        for visit in life:
            actors = [r["slots"].get("person") for r in visit["records"] if r["kind"] == "event"]
            first += actors.count(visit["people"][0])
            last += actors.count(visit["people"][-1])
        self.assertGreater(first, 2 * last)


if __name__ == "__main__":
    unittest.main()
