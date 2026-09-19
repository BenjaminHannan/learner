"""Village renderer, stream and shards, on hand-made records (independent of the world code)."""
import json
from pathlib import Path
import random
import shutil
import tempfile
import unittest

from learnlab.leaks import answer_in_input_rate
from learnlab.splits import SPLITS, SplitLeak
from learnlab.toy import all_names
from learnlab.village import vocab
from learnlab.village.render import BANK_SLOTS, FALLBACK, PatternSource, Renderer, TEACHER_BANKS, check_slots, village_registry
from learnlab.village.shards import write_shards
from learnlab.village.stream import audit, render_visit, split_vocab, to_qa_examples

NAMES = [name.capitalize() for name in all_names()]
FAMILY_SPLIT = {**{f"R{i}": "train" for i in range(1, 8)}, "R8": "validation", "R9": "test"}
SPEC = "tests.test_village_stream"


def fake_families():
    return {"rule_family": ("fake-rules-v1", FAMILY_SPLIT)}


def fake_names():
    return NAMES


def fake_visit(split, index, *, seed=0, registry=None):
    """A small deterministic visit following the world -> renderer contract."""
    rng = random.Random(f"{seed}|{split}|{index}")
    view = registry.view(split)
    people = view.draw("name", NAMES, rng, k=3)
    style = view.draw("teacher_style", vocab.STYLES, rng)[0]
    family = view.draw("rule_family", FAMILY_SPLIT, rng)[0]
    places = rng.sample(["mill", "well", "barn", "pond", "market"], 3)
    kinds = rng.sample(["cup", "lamp", "axe", "key", "apple"], 3)
    colours = rng.sample(["red", "blue", "green", "white"], 3)
    entities = {f"p{i}": {"type": "place", "kind": kind} for i, kind in enumerate(places)}
    entities.update({f"o{i}": {"type": "object", "kind": kind, "colour": colour, "material": "wood"}
                     for i, (kind, colour) in enumerate(zip(kinds, colours))})
    entities["c0"] = {"type": "container", "kind": "chest"}
    a, b, c = people
    records = []

    def add(record):
        record["line"] = len(records)
        records.append(record)
        return record["line"]

    def ev(bank, **slots):
        return {"kind": "event", "bank": bank, "slots": slots}

    def q(bank, qtype, answer, evidence, number, **slots):
        return {"kind": "question", "bank": bank, "qtype": qtype, "slots": slots, "answer": answer, "depth": len(evidence),
                "evidence": evidence, "rule_applications": 0, "families": [], "knowable": True,
                "twin": f"{split}-{index ^ 1}-q{number}", "id": f"{split}-{index}-q{number}"}

    for person, place in zip(people, ("p0", "p1", "p2")):
        add(ev("ev.intro_person", person=person, place=place))
    seen = add(ev("ev.intro_object", object="o0", place="p0"))
    add(ev("ev.layout_dir", place="p0", direction="north", place2="p1"))
    add({**ev("ev.time", time="noon"), "silent": rng.random() < 0.5})
    gone = add(ev("ev.go", person=a, place="p1"))
    put = add(ev("ev.put_in", person=b, object="o1", container="c0"))
    add({**ev("ev.recoloured", object="o1", colour="yellow"), "silent": True})
    add({"kind": "rule", "bank": "rule.R2", "family": family, "slots": {"person": c, "leader": a}})
    told = add({"kind": "teacher", "bank": "t.state", "style": style, "slots": {}, "remember": False,
                "inner": ev("ev.intro_in", object="o1", container="c0")})
    records[told]["inner"]["line"] = told
    for _ in range(rng.randrange(0, 12)):
        add(ev("ev.go", person=rng.choice(people), place=rng.choice(["p0", "p1", "p2"])))
    add(q("q.where_object", "Q1", f"the {places[0]}", [seen], 0, object="o0"))
    add({"kind": "teacher", "bank": "t.ask", "style": style, "slots": {}, "remember": False,
         "inner": q("q.in_container", "Q3", f"the yellow {kinds[1]}", [put, told], 1, container="c0")})
    add(q("q.compare_count", "Q13", f"the {places[0]}", [seen], 2, object_kind=kinds[0], place="p0", place2="p1"))
    add(q("q.what_if", "Q7", "it breaks", [], 3, action=ev("ev.put_down", person=c, object="o2", place="p2")))
    add({"kind": "teacher", "bank": "t.quiz_later", "style": style, "slots": {}, "remember": False,
         "inner": q("q.where_person", "Q1", f"the {places[1]}", [gone], 4, person=a)})
    add(ev("ev.traded", person=b, count=2, object_kind=kinds[2], item="axe"))
    add(ev("ev.new_day"))
    for record in records:
        if record["kind"] == "teacher":
            record["inner"].setdefault("line", record["line"])
        record.setdefault("day", 0)
        record.setdefault("time", "morning")
        record.setdefault("village", f"v{index}")
        record.setdefault("silent", False)
        record.setdefault("meta", {})
    return {"id": f"{split}-{index:05d}", "split": split, "seed": seed * 100003 + index, "style": style,
            "village": f"v{index}", "entities": entities, "records": records, "provenance": view.provenance()}


def setup():
    source = PatternSource.fallback()
    return source, village_registry(source, fake_families())


class RenderTests(unittest.TestCase):
    def test_fallback_patterns_have_exact_placeholders_and_pass_the_bank_checks(self):
        source = PatternSource.fallback()
        for pid, text in source.text.items():
            check_slots(source.bank[pid], text)
        self.assertEqual(set(FALLBACK) | set(TEACHER_BANKS), set(BANK_SLOTS))
        try:
            from learnlab import patterns
        except ImportError:
            return
        for pid, text in source.text.items():
            bank = source.bank[pid]
            if bank in patterns.BANKS:
                self.assertEqual(sorted(patterns.BANKS[bank].placeholders), sorted(BANK_SLOTS[bank]), bank)
                self.assertEqual(patterns.check_pattern(bank, text), [], (bank, text))
        with self.assertRaises(ValueError):
            check_slots("ev.go", "{person} went to {place} and {place}.")

    def test_surface_forms_and_current_colour(self):
        source, registry = setup()
        entities = {"p": {"type": "place", "kind": "mill"}, "o": {"type": "object", "kind": "cup", "colour": "red"},
                    "c": {"type": "container", "kind": "chest"}}
        renderer = Renderer(source, {"id": "v", "entities": entities, "style": "terse"}, registry.view("train"))
        self.assertEqual(renderer.surface("object", "o"), "the red cup")
        self.assertEqual(renderer.surface("place2", "p"), "the mill")
        self.assertEqual(renderer.surface("container", "c"), "the chest")
        self.assertEqual(renderer.surface("object_kind", "loaf"), "loaves")
        self.assertEqual(renderer.surface("item", "axe"), "an axe")
        self.assertEqual(renderer.surface("item", "lamp"), "a lamp")
        self.assertEqual(renderer.surface("count", 2), "two")
        recolour = {"kind": "event", "bank": "ev.recoloured", "slots": {"object": "o", "colour": "green"}, "line": 0}
        self.assertIn("the red cup", renderer.line(recolour).text.lower())
        line = renderer.line({"kind": "event", "bank": "ev.pick_up", "slots": {"person": "Kelo", "object": "o"}, "line": 1})
        self.assertIn("the green cup", line.text)
        self.assertNotIn("red", line.text)
        self.assertNotRegex(line.text, r"[{}]")
        self.assertTrue(line.text.startswith("[world] ") and line.text[8].isupper())
        demo = {"kind": "teacher", "bank": "t.demo_step", "style": "terse", "slots": {}, "line": 2,
                "inner": {**recolour, "slots": {"object": "o", "colour": "blue"}, "line": 2}}
        self.assertIn("the green cup", renderer.line(demo).text.lower())
        question = {"kind": "question", "bank": "q.who_has", "qtype": "Q2", "slots": {"object": "o"}, "answer": "Kelo",
                    "id": "q", "line": 3, "surface": {"object": "the blue cup"}}
        self.assertIn("the blue cup", renderer.line(question).text)
        with self.assertRaises(ValueError):  # the oracle and the renderer disagree about the surface
            renderer.line({**question, "surface": {"object": "the red cup"}})
        with self.assertRaises(ValueError):  # two objects that would both be "the red cup"
            Renderer(source, {"id": "v", "entities": {**entities, "o2": dict(entities["o"])}}, registry.view("train"))

    def test_nested_sentences_and_clauses(self):
        source, registry = setup()
        visit = fake_visit("train", 3, registry=registry)
        lines = render_visit(visit, source, registry).lines
        what_if = next(line for line in lines if "it breaks" in line)
        self.assertRegex(what_if, r"^\[question\] [A-Z][^\[]*\? \[answer\] it breaks \[feedback\] \S")
        self.assertNotRegex(what_if.split(" [answer]")[0], r"\.\s")  # the action clause lost its full stop
        teacher = next(line for line in lines if line.startswith("[teacher]"))
        self.assertTrue(teacher.endswith("."), teacher)


class SplitTests(unittest.TestCase):
    def test_patterns_styles_and_names_stay_in_their_split_and_the_audit_passes(self):
        source, registry = setup()
        style_split = source.style_split
        self.assertEqual(sorted(list(style_split.values()).count(s) for s in SPLITS), [2, 2, 6])
        for split in SPLITS:
            rendered = [render_visit(fake_visit(split, i, registry=registry), source, registry) for i in range(40)]
            for visit in rendered:
                for templates in visit.line_templates:
                    self.assertTrue(all(source.split[pid] == split for pid in templates), templates)
                self.assertTrue(all(style_split[s] == split for s in visit.provenance["teacher_style"]))
                self.assertTrue(all(source.split[p] == split for p in visit.provenance["template"]))
            report = audit(rendered, registry, source, NAMES)
            self.assertEqual(report["by_split"][split], 40)
        registry.assert_disjoint()

    def test_foreign_style_or_pattern_is_refused_and_caught_by_the_audit(self):
        source, registry = setup()
        visit = fake_visit("train", 0, registry=registry)
        foreign = next(s for s, split in source.style_split.items() if split == "test")
        visit["records"].append({"kind": "teacher", "bank": "t.right", "style": foreign, "slots": {}, "inner": None,
                                 "line": len(visit["records"])})
        with self.assertRaises(SplitLeak):
            render_visit(visit, source, registry)
        good = render_visit(fake_visit("train", 1, registry=registry), source, registry)
        test_pattern = next(pid for pid in source.ids("ev.go", "test"))
        leaked = source.text[test_pattern].format(person=good.provenance["name"][0], place="the mill")
        record = {**good.audit_record(), "text": good.audit_record()["text"] + "\n" + leaked}
        with self.assertRaises(SplitLeak):
            from learnlab.splits import audit_examples
            audit_examples([record], registry, text_of=lambda r: r["text"], vocab=split_vocab(source, NAMES))

    def test_twins_share_question_wording(self):
        source, registry = setup()
        first = fake_visit("validation", 4, registry=registry)
        twin = fake_visit("validation", 5, registry=registry)
        twin["entities"], twin["style"] = first["entities"], first["style"]
        twin["provenance"] = first["provenance"]
        asked = [r for r in first["records"] if r["kind"] == "question"][0]
        twin["records"] = [r for r in first["records"] if r["kind"] != "question"][:3] + [
            {**asked, "id": asked["twin"], "twin": asked["id"], "answer": "the pond", "line": 3}]
        one = render_visit(first, source, registry).questions[0]
        two = render_visit(twin, source, registry).questions[0]
        self.assertEqual(one["question"], two["question"])
        self.assertNotEqual(one["answer"], two["answer"])


class StreamTests(unittest.TestCase):
    def test_silent_records_emit_nothing(self):
        source, registry = setup()
        visit = fake_visit("train", 2, registry=registry)
        rendered = render_visit(visit, source, registry)
        self.assertEqual(len(rendered.lines), sum(not r["silent"] for r in visit["records"]))
        self.assertFalse(any("yellow" in line and "turn" in line for line in rendered.lines))
        visit["records"] = [{**r, "silent": True} for r in visit["records"] if r["kind"] == "event"]
        self.assertEqual(render_visit(visit, source, registry).lines, [])

    def test_metadata_line_numbers_point_at_the_right_lines(self):
        source, registry = setup()
        for index in range(20):
            visit = fake_visit("test", index, registry=registry)
            rendered = render_visit(visit, source, registry)
            by_line = {r["line"]: r for r in visit["records"]}
            for q in rendered.questions:
                line = rendered.lines[q["text_line"]]
                self.assertTrue(line.startswith(f"[question] {q['question']} [answer] {q['answer']} [feedback] "), line)
                for evidence, text_line in zip(q["evidence"], q["evidence_text_lines"]):
                    record = by_line[evidence]
                    record = record.get("inner") or record
                    for name, value in record["slots"].items():
                        expected = value if name in ("person", "leader") else visit["entities"][value]["kind"]
                        self.assertIn(expected, rendered.lines[text_line])
                self.assertTrue(q["visible"])
                self.assertLessEqual(sum(len(l) + 1 for l in rendered.lines[q["context_start"]:q["text_line"]]), 2048)

    def test_qa_examples_never_contain_the_answer_in_the_question(self):
        source, registry = setup()
        examples = []
        for split in SPLITS:
            for index in range(30):
                rendered = render_visit(fake_visit(split, index, registry=registry), source, registry)
                qa = to_qa_examples(rendered)
                self.assertEqual(len(qa), len(rendered.questions) - 1)  # the Q13 choice question is left out
                self.assertEqual(len(to_qa_examples(rendered, include_choice=True)), len(rendered.questions))
                for example, q in zip(qa, [q for q in rendered.questions if q["qtype"] != "Q13"]):
                    self.assertEqual(example.context.split("\n"), rendered.lines[q["context_start"]:q["text_line"]])
                    expected = {"template", "style", "rule_family", "qtype", "bank"} | ({"action"} if q.get("action") else set())
                    self.assertEqual(set(example.meta), expected)
                examples += qa
        self.assertEqual(answer_in_input_rate(examples), 0.0)
        self.assertFalse(any(e.answer.lower() in e.question.lower() for e in examples))

    def test_bank_file_is_used_and_gaps_are_filled(self):
        from learnlab import patterns
        source = PatternSource.fallback()
        accepted = [{"id": f"x{pid}", "bank": source.bank[pid], "text": source.text[pid], "writer": "t",
                     **({"style": source.style[pid]} if pid in source.style else {})}
                    for pid in source.text if source.bank[pid] in patterns.BANKS
                    and source.bank[pid] not in ("ev.go", "ev.intro_in")]
        manifest, banks = patterns.assign_splits(accepted)
        folder = Path(tempfile.mkdtemp())
        try:
            path = folder / "bank-v1.json"
            path.write_text(json.dumps({"version": patterns.MANIFEST_VERSION, "manifest_digest": manifest.digest(),
                                        "manifest": manifest.payload(), "banks": banks}))
            loaded = PatternSource.load(path)
        finally:
            shutil.rmtree(folder)
        self.assertTrue(all(pid.startswith("x") for pid in loaded.ids("ev.pick_up", "train")))
        self.assertTrue(all(pid.startswith("fb-") for split in SPLITS for pid in loaded.ids("ev.go", split)))
        self.assertTrue(all(pid.startswith("fb-") for pid in loaded.ids("ev.intro_in", "test")))
        self.assertIn("+fill:", loaded.version)
        registry = village_registry(loaded, fake_families())
        rendered = render_visit(fake_visit("validation", 0, registry=registry), loaded, registry)
        audit([rendered], registry, loaded, NAMES)


class WorldIntegrationTests(unittest.TestCase):
    def test_world_visits_render_audit_and_keep_answers_out_of_questions(self):
        try:
            from learnlab.village import names
            from learnlab.village.scheduler import counterfactual_pair, generate_visit
        except ImportError as error:
            self.skipTest(f"world code not importable: {error}")
        from learnlab.village.stream import default_registry
        source = PatternSource.load()
        registry = default_registry(source)
        examples = []
        for split in SPLITS:
            rendered = [render_visit(generate_visit(split, seed, registry=registry), source, registry) for seed in range(8)]
            audit(rendered, registry, source, names.all_names())
            for visit in rendered:
                for q in visit.questions:
                    self.assertTrue(visit.lines[q["text_line"]].startswith(f"[question] {q['question']} [answer] "))
                    self.assertNotIn(None, q["evidence_text_lines"])
                examples += to_qa_examples(visit)
        self.assertEqual(answer_in_input_rate(examples), 0.0)
        first, twin = counterfactual_pair("test", 0, registry=registry)
        by_id = {q["id"]: q for q in render_visit(twin, source, registry).questions}
        pairs = [(q, by_id[q["twin"]]) for q in render_visit(first, source, registry).questions if q["twin"]]
        self.assertTrue(pairs)
        for q, other in pairs:
            self.assertEqual(q["question"], other["question"])
            self.assertNotEqual(q["answer"], other["answer"])


class ShardTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root)

    def _write(self, name, workers, **extra):
        options = dict(seed=3, visits_per_shard=4, generator=f"{SPEC}:fake_visit", families=f"{SPEC}:fake_families",
                       names=f"{SPEC}:fake_names", audit_every=5, verbose=False)
        options.update(extra)
        return write_shards("train", 10, self.root / name, workers, **options)

    @staticmethod
    def _files(folder):
        return {p.name: p.read_bytes() for p in sorted((folder / "train").iterdir())}

    def test_shards_are_deterministic_resumable_and_line_numbers_hold(self):
        report = self._write("a", 1)
        self.assertEqual((report["shards_written"], report["visits"]), (3, 10))
        self.assertTrue(report["tokens_estimated"] and report["chars_per_second"] > 0)
        self._write("b", 2)
        first = self._files(self.root / "a")
        self.assertEqual(first, self._files(self.root / "b"))
        self.assertEqual(sorted(first), ["manifest.json"] + [f"shard-0000{k}.{e}" for k in range(3) for e in ("jsonl", "txt")])

        (self.root / "a" / "train" / "shard-00001.txt").unlink()
        (self.root / "a" / "train" / "shard-00002.jsonl.tmp-1").write_text("partial")
        resumed = self._write("a", 1)
        self.assertEqual((resumed["shards_written"], resumed["shards_skipped"]), (1, 2))
        (self.root / "a" / "train" / "shard-00002.jsonl.tmp-1").unlink()
        self.assertEqual(self._files(self.root / "a"), first)
        with self.assertRaises(ValueError):
            self._write("a", 1, seed=4)

        text = (self.root / "a" / "train" / "shard-00001.txt").read_text().split("\n")
        rows = [json.loads(line) for line in (self.root / "a" / "train" / "shard-00001.jsonl").read_text().splitlines()]
        visits = [r for r in rows if r["kind"] == "visit"]
        self.assertEqual([v["index"] for v in visits], [4, 5, 6, 7])
        for visit in visits:
            self.assertEqual(text[visit["first_line"] + visit["lines"]], "")
        for q in (r for r in rows if r["kind"] == "question"):
            self.assertTrue(text[q["text_line"]].startswith(f"[question] {q['question']} [answer] {q['answer']}"))
            self.assertTrue(all(text[t] and not text[t].startswith("[question]") for t in q["evidence_text_lines"]))


if __name__ == "__main__":
    unittest.main()


class LeakClassTests(unittest.TestCase):
    def test_hypotheticals_are_classed_by_action_and_tested_without_the_named_thing(self):
        from learnlab.leaks import QAExample
        from learnlab.village.stream import answer_class, effect_only

        opened = QAExample("", "What happens if Juba opened the sack?", "the sack would stay shut",
                           {"bank": "q.what_if", "action": "ev.open"})
        went = QAExample("", "What happens if Danu headed off to the square?", "Kuli would follow",
                         {"bank": "q.what_if", "action": "ev.go"})
        self.assertEqual(answer_class(opened), "what if: ev.open")
        self.assertEqual(answer_class(went), "what if: ev.go")
        self.assertEqual(answer_class(QAExample("", "Who has it?", "Kelo", {"bank": "q.who_has"})), "person")
        self.assertEqual(effect_only(opened).answer, "it would stay shut")
        self.assertEqual(effect_only(went).answer, "Kuli would follow")  # the follower is not named in the question
        nothing = QAExample("", "What happens if Juba opened the sack?", "nothing would happen", opened.meta)
        self.assertEqual(effect_only(nothing).answer, "nothing would happen")
