"""Step 1 pipeline on a tiny fake village: data, tokenizer, stream, read-only QA eval, gate (CPU)."""
from __future__ import annotations

import json
from pathlib import Path
import random
import tempfile
import time
import unittest
from unittest import mock

import torch
from torch import nn

from learnlab import step1
from learnlab.core import Core, CoreConfig
from learnlab.readonly import ReadOnlyViolation
from learnlab.tokenizer import Tokenizer
from learnlab.train import TrainConfig, Trainer
from memorylab.storage import Budget

NAMES = {"train": ["Kelo", "Rami", "Tosa", "Vemi", "Nuba", "Sali"],
         "validation": ["Zarv", "Quil", "Brex", "Doma"],
         "test": ["Jopo", "Wexa", "Yurn", "Fiko"]}
TEMPLATES = {"train": ["{p} walked to the {l}.", "{p} went over to the {l}."],
             "validation": ["{p} strolled to the {l}."],
             "test": ["{p} wandered to the {l}."]}
STYLES = {"train": "plain", "validation": "cheerful", "test": "terse"}
FAMILIES = {"train": "R1", "validation": "R8", "test": "R9"}
PLACES = ["mill", "barn", "well", "market", "pond"]
HELDOUT_MARKERS = ("Zarv", "Quil", "Brex", "Doma", "Jopo", "Wexa", "Yurn", "Fiko",
                   "strolled", "wandered", "cheerful", "terse")


def fake_write_shards(split, n_visits, out_dir, workers, *, seed=0):
    """The real shard layout: out_dir/<split>/shard-<k>.txt + .jsonl (visit rows, then question rows)."""
    rng = random.Random(f"{seed}:{split}")
    out = Path(out_dir) / split
    out.mkdir(parents=True, exist_ok=True)
    per_shard = max(1, (n_visits + 1) // 2)
    for shard, first in enumerate(range(0, n_visits, per_shard)):
        lines, rows = [], []
        for visit in range(first, min(n_visits, first + per_shard)):
            base, text, questions = len(lines), [], []
            people = rng.sample(NAMES[split], 3)
            where = {}
            for _ in range(5):
                person, place = rng.choice(people[:2]), rng.choice(PLACES)
                template = rng.randrange(len(TEMPLATES[split]))
                text.append("[world] " + TEMPLATES[split][template].format(p=person, l=place))
                where[person] = (place, len(text) - 1, template)
            style = STYLES[split]
            text.append(f"[teacher] ({style}) Remember where everyone went.")
            asked = sorted(where)[0]
            place, evidence, template = where[asked]
            common = {"kind": "question", "visit": f"{split}-{visit}", "split": split, "bank": "q.fake",
                      "style": style, "families": [FAMILIES[split]], "template": f"{split}:q",
                      "templates": [f"{split}:q"], "evidence_templates": [f"{split}:{template}"],
                      "evidence": [rng.randrange(1000)], "depth": 1}
            text.append(f"[question] Where is {asked}? [answer] the {place} [feedback] Right.")
            questions.append({**common, "id": f"{split}-{visit}-a", "qtype": "Q1", "visible": True,
                              "long_range": False, "evidence_text_lines": [base + evidence],
                              "text_line": base + len(text) - 1, "answer": f"the {place}",
                              "twin": f"{split}-{visit ^ 1}-a", "knowable": True})
            text.append(f"[question] Who went to the {place}? [answer] {asked} [feedback] Yes.")
            questions.append({**common, "id": f"{split}-{visit}-b", "qtype": "Q2", "visible": True,
                              "long_range": False, "evidence_text_lines": [base + evidence],
                              "text_line": base + len(text) - 1, "answer": asked, "twin": None,
                              "knowable": True})
            text.append(f"[question] Where is {people[2]}? [answer] not told [feedback] Right.")
            questions.append({**common, "id": f"{split}-{visit}-c", "qtype": "Q10", "visible": False,
                              "long_range": True, "evidence_text_lines": [None],
                              "text_line": base + len(text) - 1, "answer": "not told", "twin": None,
                              "knowable": False})
            provenance = {"name": sorted(people), "teacher_style": [style],
                          "rule_family": [FAMILIES[split]],
                          "template": [f"{split}:q"] + [f"{split}:{t}" for t in range(len(TEMPLATES[split]))]}
            rows.append({"kind": "visit", "id": f"{split}-{visit}", "split": split, "index": visit,
                         "first_line": base, "lines": len(text), "provenance": provenance})
            rows.extend(questions)
            lines.extend(text + [""])
        (out / f"shard-{shard:05d}.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        (out / f"shard-{shard:05d}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"split": split, "visits": n_visits}


fake_write_shards.version = "fake-1"


class Workspace:
    """A temporary project root with its own Budget."""

    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.budget = Budget(self.root, hard=10_000_000_000, steady=8_000_000_000)

    def close(self) -> None:
        self.tmp.cleanup()

    def data(self, **overrides):
        settings = dict(visits="tiny", seed=0, workers=1, writer=fake_write_shards,
                        vocab_size=400, log=lambda _message: None)
        settings.update(overrides)
        return step1.build_data(self.budget, **settings)


def tiny_tokenizer() -> Tokenizer:
    text = "\n".join(f"[world] {p} walked to the {l}." for p in NAMES["train"] for l in PLACES)
    return Tokenizer.train([text, "[question] where is kelo? [answer] the mill [feedback] right."],
                           vocab_size=320)


class ShardContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        fake_write_shards("train", 6, self.dir, 1)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_questions_join_records_and_lines(self) -> None:
        pairs = step1.shard_files(self.dir)
        self.assertEqual([t.name for t, _ in pairs], ["shard-00000.txt", "shard-00001.txt"])
        questions = step1.read_questions(*pairs[0], "train")
        self.assertEqual(len(questions), 9)
        first = questions[0]
        self.assertEqual(first.id, "train-0-a")
        self.assertTrue(first.visible)
        self.assertEqual(first.prompt_line, f"[question] {first.question} [answer]")
        self.assertNotIn(first.answer, first.prompt_line)
        self.assertEqual(len(first.context), 6)      # five world lines and the teacher line
        self.assertEqual(first.context[first.evidence[0] - first.context[0][0]][0], first.evidence[0])
        self.assertEqual(questions[1].context[-1][1], first.raw_line)
        self.assertFalse(questions[2].visible)
        self.assertEqual(step1.parse_question_line("[question] Who? [answer] Rami [feedback] Yes."),
                         ("Who?", "Rami", "Yes."))

    def test_contract_violations_are_loud(self) -> None:
        text, meta = step1.shard_files(self.dir)[0]
        records = step1.read_records(meta)
        records[0]["answer"] = "the moon"
        meta.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        with self.assertRaises(step1.ShardFormatError):
            step1.read_questions(text, meta, "train")
        meta.write_text("".join(json.dumps(r) + "\n" for r in records[1:]), encoding="utf-8")
        with self.assertRaises(step1.ShardFormatError):
            step1.read_questions(text, meta, "train")
        records[0]["answer"] = records[1]["answer"] = None
        meta.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        with self.assertRaises(step1.ShardFormatError):   # split mismatch
            step1.read_questions(text, meta, "test")
        self.assertEqual(len(step1.read_questions(text, meta, "train")), len(records))
        records[2]["text_line"] += 1
        meta.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        with self.assertRaises(step1.ShardFormatError):   # text_line points elsewhere
            step1.read_questions(text, meta, "train")

    def test_rule_family_ids(self) -> None:
        self.assertEqual(step1.family_ids(["R1:train"]), ("R1",))
        self.assertEqual(step1.family_ids(["R3", "R5:test"]), ("R3", "R5", "R9"))
        self.assertEqual(step1.family_ids(["R3", "R3"]), ("R3",))
        self.assertEqual(step1.family_ids(["R1:train", "R2:train"], derivation=False), ("R1", "R2"))

    def test_sampling_keeps_twins_together(self) -> None:
        questions = [q for t, m in step1.shard_files(self.dir) for q in step1.read_questions(t, m, "train")]
        visible = [q for q in questions if q.visible]
        sample = step1.sample_questions(visible, 5, seed=3)
        self.assertLessEqual(len(sample), 5)
        everyone, chosen = {q.id for q in visible}, {q.id for q in sample}
        paired = [q for q in sample if q.twin in everyone]
        self.assertTrue(paired)
        for q in paired:
            self.assertIn(q.twin, chosen)    # a twin is never sampled without its partner
        self.assertEqual(sample, step1.sample_questions(visible, 5, seed=3))


class DataPipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.work = Workspace()

    def tearDown(self) -> None:
        self.work.close()

    def test_builds_splits_tokenizer_and_tokens_once(self) -> None:
        calls = []

        def counting(split, n, out_dir, workers, seed=0):
            calls.append(split)
            return fake_write_shards(split, n, out_dir, workers, seed=seed)

        counting.version = "fake-1"
        data = self.work.data(writer=counting)
        self.assertEqual(calls, ["train", "validation", "test"])
        for split in step1.SPLITS:
            self.assertTrue((data.split_dir(split) / "COMPLETE.json").is_file())
        train = data.splits["train"]
        self.assertEqual(train["templates"], ["train:0", "train:1", "train:q"])
        self.assertEqual((train["styles"], train["rule_families"]), (["plain"], ["R1"]))
        self.assertEqual(train["names"], len(NAMES["train"]))
        tokenizer_file = self.work.root / step1.TOKENIZER_PATH
        manifest = json.loads((self.work.root / step1.TOKENIZER_MANIFEST).read_text())
        self.assertEqual(manifest["village_splits"], ["train"])
        self.assertEqual(manifest["sha256"], Tokenizer.load(tokenizer_file).digest)
        self.assertEqual(data.tokenizer.digest, manifest["sha256"])
        self.assertTrue(data.rel.startswith(step1.STREAM_ROOT))

        # The token files decode back to the train visits with <eos> after each one.
        tokenizer, eos = data.tokenizer, data.tokenizer.token_to_id("<eos>")
        stream = step1.stream_for(data, chunk=10_000, seed=0)
        tokens = torch.cat([step1.load_tokens(p) for p in stream.probe + stream.files]).tolist()
        visits = [v for t, _ in step1.shard_files(data.split_dir("train")) for v in step1.read_visits(t)]
        expected = []
        for visit in visits:
            expected.extend(step1.encode_visit(tokenizer, [line for _, line in visit], eos))
        self.assertEqual(sorted(tokens), sorted(expected))
        self.assertEqual(tokens.count(eos), len(visits))
        self.assertEqual(stream.probe_tokens, data.tokens["probe_tokens"])
        self.assertGreater(data.tokens["probe_tokens"], 0)
        self.assertEqual(tokenizer.decode(expected[: expected.index(eos)]),
                         tokenizer.normalize("\n".join(l for _, l in visits[0]) + "\n"))

        again = self.work.data(writer=counting)
        self.assertEqual(calls, ["train", "validation", "test"])   # cached: nothing regenerated
        self.assertEqual(again.tokenizer.digest, data.tokenizer.digest)

    def test_tokenizer_never_sees_heldout_text(self) -> None:
        seen_texts: list[str] = []
        real_train = Tokenizer.train

        def spy(texts, *args, **kwargs):
            texts = list(texts)
            seen_texts.extend(texts)
            return real_train(texts, *args, **kwargs)

        with mock.patch.object(Tokenizer, "train", side_effect=spy):
            self.work.data()
        self.assertTrue(seen_texts)
        corpus = "\n".join(seen_texts)
        self.assertIn("Kelo", corpus)
        for marker in HELDOUT_MARKERS:
            self.assertNotIn(marker, corpus)
        held = next(p for p in (self.work.root / step1.STREAM_ROOT).rglob("shard-*.txt")
                    if "validation" in p.parts)
        with self.assertRaises(ValueError):
            step1.tokenizer_corpus([("validation", held)])

    def test_fallback_patterns_get_a_provisional_tokenizer(self) -> None:
        def fallback_writer(split, n, out_dir, workers, *, seed=0):
            return fake_write_shards(split, n, out_dir, workers, seed=seed)

        fallback_writer.patterns = "village-fallback-v1"
        messages = []
        data = self.work.data(writer=fallback_writer, log=messages.append)
        self.assertTrue(data.tokenizer_info["provisional"])
        self.assertEqual(data.tokenizer_info["path"], step1.PROVISIONAL_TOKENIZER_PATH)
        self.assertFalse((self.work.root / step1.TOKENIZER_PATH).exists())
        manifest = json.loads((self.work.root / step1.PROVISIONAL_TOKENIZER_MANIFEST).read_text())
        self.assertEqual(manifest["village_patterns"], "village-fallback-v1")

        def real_writer(split, n, out_dir, workers, *, seed=0):
            return fake_write_shards(split, n, out_dir, workers, seed=seed)

        real_writer.patterns = "village-patterns-v1:abc"
        data = self.work.data(writer=real_writer)
        self.assertFalse(data.tokenizer_info["provisional"])
        self.assertTrue((self.work.root / step1.TOKENIZER_PATH).is_file())
        real_writer.patterns = "village-patterns-v2:def"
        messages.clear()
        data = self.work.data(writer=real_writer, log=messages.append)
        self.assertTrue(data.tokenizer_info["patterns_mismatch"])
        self.assertTrue(any("WARNING" in m for m in messages))

    def test_parallel_encoding_matches_serial(self) -> None:
        serial = self.work.data()
        other = Workspace()
        self.addCleanup(other.close)
        (other.root / "data" / "tokenizer").mkdir(parents=True)
        for name in (step1.TOKENIZER_PATH, step1.TOKENIZER_MANIFEST):
            (other.root / name).write_bytes((self.work.root / name).read_bytes())
        parallel = other.data(workers=2)
        self.assertEqual(parallel.tokenizer.digest, serial.tokenizer.digest)
        for entry in serial.tokens["files"] + serial.tokens["probe_files"]:
            self.assertEqual((parallel.token_dir / entry["file"]).read_bytes(),
                             (serial.token_dir / entry["file"]).read_bytes())

    def test_spawn_safe_main_hides_the_script_path(self) -> None:
        import sys
        import types

        fake = types.ModuleType("__main__")
        fake.__file__ = "/somewhere/run.py"
        fake.__spec__ = None
        with mock.patch.dict(sys.modules, {"__main__": fake}):
            with step1.spawn_safe_main():
                self.assertFalse(hasattr(fake, "__file__"))
            self.assertEqual(fake.__file__, "/somewhere/run.py")

    def test_stream_probe_once_then_cycles(self) -> None:
        folder = self.work.root / "tok"
        folder.mkdir()
        paths = {}
        for name, values in {"probe": [1, 2], "a": [3, 4, 5], "b": [6, 7, 8, 9]}.items():
            paths[name] = folder / f"{name}.tok"
            paths[name].write_bytes(step1.array("H", values).tobytes())
        stream = step1.TokenStream([paths["a"], paths["b"]], [paths["probe"]], chunk=2, seed=1)
        got = []
        while len(got) < 2 + 7 * 3:
            got.extend(next(stream).tolist())
        self.assertEqual(got[:9], [1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertNotIn(1, got[9:])
        self.assertEqual(sorted(got[9:16]), [3, 4, 5, 6, 7, 8, 9])
        self.assertGreaterEqual(stream.epoch, 2)
        self.assertAlmostEqual(stream.epochs(2 + 14), 2.0)
        self.assertGreaterEqual(stream.stall_seconds, 0.0)


class NameTokenizationTest(unittest.TestCase):
    """Seen and fresh village names tokenize alike; a tokenizer that does not split names is refused and kept."""

    def setUp(self) -> None:
        try:
            from learnlab.village.names import SYLLABLES, people_names, village_names
            registry = step1._oracle_registry()
        except ImportError as error:
            self.skipTest(f"village simulator not available: {error}")
        self.syllables = SYLLABLES
        split = {name: registry.split_of("name", name) for name in people_names() + village_names()}
        # Village names ending in "ki", "mu" or "no" are not made of name syllables, so they are left out.
        whole = [n for n in village_names() if all(n[i:i + 2].lower() in SYLLABLES for i in range(0, len(n), 2))]
        self.people = {s: [n for n in people_names() if split[n] == s] for s in step1.SPLITS}
        self.villages = {s: [n for n in whole if split[n] == s] for s in step1.SPLITS}
        # Only train names reach a tokenizer's corpus, as in build_tokenizer.
        self.corpus = [f"[world] {name} walked to the mill." for name in self.people["train"]] * 2

    def fit(self, syllables=()) -> Tokenizer:
        return Tokenizer.train(self.corpus, vocab_size=2000, syllables=syllables)

    def test_seen_and_fresh_names_of_equal_syllables_tokenize_alike(self) -> None:
        tokenizer = self.fit(self.syllables)
        for pool, syllables in ((self.people, 2), (self.villages, 3)):
            for form, extra in (("{}", 0), ("[answer] {} [feedback]", 4)):  # line start; mid-line: 2 tags, 2 spaces
                counts = {split: {len(tokenizer.encode(form.format(n))) for n in pool[split]} for split in step1.SPLITS}
                self.assertEqual(counts, {split: {syllables + extra} for split in step1.SPLITS}, form)
        plain = self.fit()      # the bug: seen names became whole words, fresh ones did not
        self.assertEqual(len(plain.encode(" " + self.people["train"][0])), 1)
        self.assertGreater(len(plain.encode(" " + self.people["validation"][0])), 1)

    def test_audit_warns_only_when_splits_tokenize_names_differently(self) -> None:
        bad = step1.name_token_audit(self.fit())
        self.assertTrue(bad["single_token_mismatch"])
        self.assertEqual(bad["splits"]["train"]["single_token"], len(self.people["train"]))
        self.assertEqual([bad["splits"][s]["single_token"] for s in step1.HELDOUT], [0, 0])
        self.assertGreater(bad["max_mean_gap"], step1.NAME_PIECE_GAP)
        self.assertIn("tokenize differently", bad["warning"])
        good = step1.name_token_audit(self.fit(self.syllables))
        self.assertIsNone(good["warning"])
        self.assertFalse(good["single_token_mismatch"])
        self.assertLessEqual(good["max_mean_gap"], step1.NAME_PIECE_GAP)
        # The warning reaches the report's warnings list.
        data = mock.Mock(tokenizer_info={}, oracle={})
        sets = mock.Mock(signature_source={})
        scored = {"heldout": [], "heldin": [], "pairs": []}
        self.assertEqual(step1.run_warnings(data, sets, scored, {"epochs": 1.0}, bad), [bad["warning"]])
        self.assertEqual(step1.run_warnings(data, sets, scored, {"epochs": 1.0}, good), [])

    def test_a_saved_tokenizer_without_name_syllables_is_refused_and_left_untouched(self) -> None:
        self.assertEqual(step1.next_version("data/tokenizer/premonition-tok-v1-fallback.manifest.json"),
                         "data/tokenizer/premonition-tok-v2-fallback.manifest.json")
        self.assertEqual(step1.next_version("tok.json"), "tok-v2.json")
        work = Workspace()
        self.addCleanup(work.close)
        old_path = "data/tokenizer/premonition-tok-v1-fallback.json"
        old_manifest = "data/tokenizer/premonition-tok-v1-fallback.manifest.json"
        old = tiny_tokenizer()
        self.assertEqual(old.syllables, ())
        (work.root / "data" / "tokenizer").mkdir(parents=True)
        (work.root / old_path).write_text(old.to_json(), encoding="utf-8")
        (work.root / old_manifest).write_text(json.dumps({"sha256": old.digest, "village_splits": ["train"]}))
        before = {p: (work.root / p).read_bytes() for p in (old_path, old_manifest)}
        fake_write_shards("train", 6, work.root / "shards", 1)
        messages = []

        def build():
            return step1.build_tokenizer(work.budget, work.root / "shards" / "train", path=old_path,
                                         manifest_path=old_manifest, vocab_size=400, log=messages.append)

        tokenizer, info = build()
        self.assertEqual((info["path"], info["built"], info["skipped"]),
                         (step1.PROVISIONAL_TOKENIZER_PATH, True, [old_path]))
        self.assertEqual(tokenizer.syllables, tuple(sorted(self.syllables)))
        self.assertEqual(Tokenizer.load(work.root / step1.PROVISIONAL_TOKENIZER_PATH).digest, tokenizer.digest)
        manifest = json.loads((work.root / step1.PROVISIONAL_TOKENIZER_MANIFEST).read_text())
        self.assertEqual(manifest["sha256"], tokenizer.digest)
        self.assertTrue(any("WARNING" in m and old_path in m and "no name syllables" in m for m in messages))
        again, info = build()          # the refit is loaded next time; the old file is still refused
        self.assertEqual((again.digest, info["built"], info["skipped"]), (tokenizer.digest, False, [old_path]))
        for path, content in before.items():
            self.assertEqual((work.root / path).read_bytes(), content)

        # build_data's defaults go straight to v2 even with the v1 files on disk (and never touch them).
        def fallback_writer(split, n, out_dir, workers, *, seed=0):
            return fake_write_shards(split, n, out_dir, workers, seed=seed)

        fallback_writer.patterns = "village-fallback-v1"
        other = Workspace()
        self.addCleanup(other.close)
        (other.root / "data" / "tokenizer").mkdir(parents=True)
        for path, content in before.items():
            (other.root / path).write_bytes(content)
        data = other.data(writer=fallback_writer)
        self.assertEqual((data.tokenizer_info["path"], data.tokenizer_info["built"]),
                         (step1.PROVISIONAL_TOKENIZER_PATH, True))
        self.assertEqual(set(data.tokenizer.syllables), set(self.syllables))
        for path, content in before.items():
            self.assertEqual((other.root / path).read_bytes(), content)


class RealVillageTest(unittest.TestCase):
    """Integration with the real simulator (skipped until learnlab.village is importable)."""

    def setUp(self) -> None:
        try:
            from learnlab.village.render import PatternSource, village_registry
            from learnlab.village.scheduler import world_families
        except ImportError as error:
            self.skipTest(f"village simulator not available: {error}")
        self.registry = village_registry(PatternSource.load(), world_families())

    def test_pair_visits_are_linked_twins(self) -> None:
        from learnlab.village.stream import render_visit

        first = step1.pair_visit("validation", 4, seed=0, registry=self.registry)
        second = step1.pair_visit("validation", 5, seed=0, registry=self.registry)
        self.assertNotEqual(first["id"], second["id"])
        a, b = render_visit(first, registry=self.registry), render_visit(second, registry=self.registry)
        ids_b = {q["id"] for q in b.questions}
        twins = [q for q in a.questions if q["twin"]]
        for q in twins:
            self.assertIn(q["twin"], ids_b)
        self.assertEqual(step1.pair_visit("validation", 4, seed=0, registry=self.registry)["id"], first["id"])

    def test_real_shards_through_the_reader(self) -> None:
        from learnlab.village.shards import write_shards

        with tempfile.TemporaryDirectory() as folder:
            write_shards("train", 6, folder, 1, seed=0, verbose=False)
            summary = step1.summarize_split(Path(folder) / "train", "train")
            self.assertEqual(summary["visits"], 6)
            self.assertGreater(summary["questions"], 0)
            self.assertLessEqual(set(summary["rule_families"]), {f"R{i}" for i in range(1, 8)})
            text, meta = step1.shard_files(Path(folder) / "train")[0]
            for q in step1.read_questions(text, meta, "train"):
                self.assertTrue(q.raw_line.startswith("[question]"))
                self.assertLess(max([q.line - 1] + [e for e in q.evidence if e >= 0]), q.line)


class RealVillageOracleTest(unittest.TestCase):
    """The oracle index replays real village visits (skipped until learnlab.village is importable)."""

    def setUp(self) -> None:
        try:
            from learnlab.village.shards import write_shards
        except ImportError as error:
            self.skipTest(f"village simulator not available: {error}")
        self.write_shards = write_shards
        self.work = Workspace()
        self.addCleanup(self.work.close)

    def build(self, name: str, split: str, visits: int, **extra):
        self.write_shards(split, visits, self.work.root / "d" / name, 1, seed=0, verbose=False, **extra)
        return step1.build_oracle(self.work.budget, "d", name, split, workers=1, log=lambda _m: None)

    def test_index_covers_every_question_and_plans_are_acted_out(self) -> None:
        summary = self.build("validation", "validation", 4)
        signatures, plans, shards = step1.load_oracle(self.work.root / "d" / "validation")
        questions = [q for t, m in step1.shard_files(self.work.root / "d" / "validation")
                     for q in step1.read_questions(t, m, "validation", signatures)]
        self.assertEqual(summary["questions_indexed"], len(questions))
        self.assertEqual(set(signatures), {q.id for q in questions})
        self.assertEqual(shards, ["shard-00000"])
        plan_questions = [q for q in questions if q.qtype == "Q12"]
        self.assertTrue(plan_questions)
        self.assertEqual({q.id for q in plan_questions}, set(plans))
        from learnlab.village.oracle import surface

        for q in plan_questions:
            world, person, _ = plans[q.id]
            self.assertTrue(step1.plan_works(plans[q.id], q.answer.lower()), q.answer)   # model output is lowercase
            here = surface(world, world.people[person])
            self.assertTrue(step1.plan_works(plans[q.id], f"go to {here}, {q.answer}"))  # another working plan
            self.assertFalse(step1.plan_works(plans[q.id], "not told"))
            self.assertFalse(step1.plan_works(plans[q.id], q.answer + ", open the moon"))
        # Signatures come from (bank, slots), so every repeat is caught however it is worded.
        by_sig: dict[tuple[int, str], list] = {}
        for q in questions:
            by_sig.setdefault((q.visit, q.signature), []).append(q)
            self.assertTrue(q.signature.startswith(q.bank + "|"))
        self.assertTrue(any(len(group) > 1 for group in by_sig.values()))
        again = step1.build_oracle(self.work.budget, "d", "validation", "validation", workers=1,
                                   log=lambda _m: None)
        self.assertEqual(again["questions_indexed"], summary["questions_indexed"])     # cached

    def test_pair_sets_replay_both_siblings(self) -> None:
        self.build("validation-pairs", "validation", 4, generator=step1.PAIR_GENERATOR)
        signatures, _, _ = step1.load_oracle(self.work.root / "d" / "validation-pairs")
        self.assertTrue(any(qid.split(":")[0].endswith("-cf") for qid in signatures))

    def test_a_record_the_simulator_did_not_write_is_refused(self) -> None:
        self.write_shards("test", 2, self.work.root / "d" / "test", 1, seed=0, verbose=False)
        meta = next((self.work.root / "d" / "test").rglob("*.jsonl"))
        rows = [json.loads(line) for line in meta.read_text().splitlines()]
        question = next(row for row in rows if row["kind"] == "question")
        question["answer"] = "the moon"
        meta.write_text("".join(json.dumps(row) + "\n" for row in rows))
        with self.assertRaises(step1.ShardFormatError):
            step1.build_oracle(self.work.budget, "d", "test", "test", workers=1, log=lambda _m: None)

    def test_not_told_keeps_its_asked_type_in_leak_metadata(self) -> None:
        q = step1.Question(id="x", split="test", shard="s", visit=0, line=3, raw_line="[question] q [answer] a",
                           question="q", answer="not told", context=(), qtype="Q10", depth=0, visible=True,
                           knowable=False, twin=None, templates=(), style=None, rule_families=(),
                           evidence=(), bank="q.who_has")
        self.assertEqual(step1.base_qtype(q), "Q2")


def repeat_shard(folder: Path) -> tuple[Path, Path]:
    """One visit asking where Kelo is four times, worded three ways, with the answer changing once."""
    lines = ["[world] Kelo walked to the mill.",
             "[question] Where is Kelo? [answer] the mill [feedback] Right.",
             "[question] Tell me again: where is Kelo? [answer] the mill [feedback] Right.",
             "[world] Kelo walked to the barn.",
             "[question] Kelo is where? [answer] the barn [feedback] Right.",
             "[question] Where is Kelo? [answer] the barn [feedback] Right."]
    rows = [{"kind": "visit", "id": "v", "split": "test", "provenance": {}}]
    for key, line in zip("abcd", (1, 2, 4, 5)):
        answer = step1.parse_question_line(lines[line])[1]
        rows.append({"kind": "question", "id": f"v:{key}", "split": "test", "qtype": "Q1", "visible": True,
                     "answer": answer, "text_line": line, "evidence_text_lines": [0 if line < 3 else 3],
                     "bank": "q.where_person"})
    (folder / "shard-00000.txt").write_text("\n".join(lines) + "\n\n")
    (folder / "shard-00000.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    return folder / "shard-00000.txt", folder / "shard-00000.jsonl"


class RepeatDetectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.text, self.meta = repeat_shard(Path(self.tmp.name))
        self.tokenizer = tiny_tokenizer()
        self.seen = {"templates": set(), "styles": set(), "rule_families": set()}

    def flags(self, signatures=None, max_len=400):
        questions = step1.read_questions(self.text, self.meta, "test", signatures)
        items = step1.build_items(self.tokenizer, questions, max_len=max_len, seen=self.seen)
        return ([item.repeat_in_context for item in items], [item.changed_since_asked for item in items])

    def test_oracle_signatures_find_every_repeat(self) -> None:
        same = {f"v:{key}": "q.where_person|kelo" for key in "abcd"}
        repeats, changed = self.flags(same)
        self.assertEqual(repeats, [False, True, False, True])    # b repeats a; d repeats c
        self.assertEqual(changed, [False, False, True, False])   # c was asked before, answer since changed

    def test_wording_alone_misses_reworded_repeats(self) -> None:
        repeats, changed = self.flags()
        self.assertEqual(repeats, [False, False, False, False])  # b is worded differently; d's twin answer changed
        self.assertEqual(changed, [False, False, False, True])

    def test_a_repeat_cut_out_of_the_input_no_longer_counts(self) -> None:
        same = {f"v:{key}": "q.where_person|kelo" for key in "abcd"}
        questions = step1.read_questions(self.text, self.meta, "test", same)
        tail = len(self.tokenizer.encode(questions[1].prompt_line))
        short = step1.build_items(self.tokenizer, questions[1:2], max_len=tail + 2, seen=self.seen)[0]
        self.assertTrue(short.truncated)
        self.assertFalse(short.repeat_in_context)

    def test_repeats_leave_the_gate_and_the_pair_test(self) -> None:
        results = fake_results(10, 10)
        for i, r in enumerate(results):
            r["twin"] = f"pair-{i // 2}"
        results[0]["repeat_in_context"] = True
        kept = step1.gated(results)
        self.assertEqual(len(kept), 9)
        examples = {r["id"]: step1.QAExample("Kelo went to the mill.", "Where?", "the mill") for r in results}
        self.assertEqual(step1.pair_summary(kept, examples)["n"], 4)    # the pair with a repeat is gone
        self.assertEqual(step1.gate_metrics(kept, {"hits": 0, "n": 0}, {}, 2, 0.0)["heldout_visible"]["n"], 9)


class TokenizerDesignTest(unittest.TestCase):
    def test_seen_and_fresh_names_split_alike(self) -> None:
        """design/04 part 2: names split into syllable pieces, so a fresh name looks like a seen one."""
        from learnlab.village.names import SYLLABLES
        text = " ".join(f"[world] {name} went to the mill." for name in ["Bada", "Kelo", "Rami"] * 50)
        tokenizer = Tokenizer.train([text], vocab_size=600, syllables=SYLLABLES)
        for name in ("Bada", "Kelo", "Baho", "Kemi"):
            pieces = [tokenizer.id_to_token(i) for i in tokenizer.encode(" " + name)]
            self.assertEqual(pieces, [" ", name.lower()[:2], name.lower()[2:]], name)
        self.assertEqual(tokenizer.decode(tokenizer.encode("Kelo met Baho.")), "kelo met baho.")
        self.assertEqual(Tokenizer.from_json(tokenizer.to_json()).encode(" Kemi"), tokenizer.encode(" Kemi"))

class LookupModel(nn.Module):
    """Next token = table[current token]; logits are one-hot scaled."""

    def __init__(self, table: list[int], context: int = 64) -> None:
        super().__init__()
        self.register_buffer("table", torch.tensor(table))
        self.weight = nn.Parameter(torch.zeros(1))
        self.config = CoreConfig(vocab_size=len(table), context=context, d_model=4, n_layers=1,
                                 n_heads=1)

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        return nn.functional.one_hot(self.table[tokens], len(self.table)).float() * 10 + self.weight


class DecodingTest(unittest.TestCase):
    def test_decoding_stops_at_stop_tokens_and_max_new(self) -> None:
        # 5 -> 6 -> 7 -> 2 (stop); 9 -> 9 forever; 3 -> 4 -> 1 (stop)
        table = list(range(12))
        table[5], table[6], table[7], table[9], table[3], table[4] = 6, 7, 2, 9, 4, 1
        model = LookupModel(table)
        prompts = [[8, 5], [9], [1, 1, 1, 3], [5]]
        out = step1.greedy_decode(model, prompts, max_new=4, stop={1, 2}, batch_size=3)
        self.assertEqual(out, [[6, 7, 2], [9, 9, 9, 9], [4, 1], [6, 7, 2]])
        single = [step1.greedy_decode(model, [p], max_new=4, stop={1, 2})[0] for p in prompts]
        self.assertEqual(single, out)
        with self.assertRaises(ValueError):
            step1.greedy_decode(model, [[1] * 62], max_new=4, stop={1})   # beyond the context

    def test_right_padded_batches_match_single_prompts_on_a_real_core(self) -> None:
        torch.manual_seed(0)
        model = Core(CoreConfig(vocab_size=50, context=32, d_model=32, n_layers=2, n_heads=2)).eval()
        prompts = [[3, 4, 5], [7] * 11, [9, 8], [1, 2, 3, 4, 5, 6]]
        with torch.no_grad():
            batched = step1.greedy_decode(model, prompts, max_new=6, stop={0}, batch_size=4)
            singles = [step1.greedy_decode(model, [p], max_new=6, stop={0})[0] for p in prompts]
            uncached = step1.greedy_decode(model, prompts, max_new=6, stop={0}, batch_size=4,
                                           use_cache=False)
            stopping = step1.greedy_decode(model, prompts, max_new=6, stop={batched[1][1]},
                                           batch_size=3)
            stopping_ref = step1.greedy_decode(model, prompts, max_new=6, stop={batched[1][1]},
                                               batch_size=3, use_cache=False)
            tokens = torch.randint(0, 50, (3, 10))
            positions = torch.tensor([2, 9, 5])
            expected = model(tokens)[torch.arange(3), positions]
            self.assertTrue(torch.allclose(step1.last_logits(model, tokens, positions), expected,
                                           atol=1e-5))
        self.assertEqual(batched, singles)
        self.assertEqual(batched, uncached)             # the key/value cache changes nothing
        self.assertEqual(stopping, stopping_ref)
        self.assertEqual(stopping[1][-1], batched[1][1])   # stopped on (and kept) its stop token
        self.assertLessEqual(len(stopping[1]), 2)

    def test_answer_text_cuts_at_special_or_newline(self) -> None:
        tokenizer = tiny_tokenizer()
        stops, newline = step1.stop_ids(tokenizer)
        feedback = tokenizer.token_to_id("[feedback]")
        self.assertIn(feedback, stops)
        self.assertIn(tokenizer.encode("\n")[0], newline)
        ids = tokenizer.encode(" the mill ") + [feedback] + tokenizer.encode(" right.")
        self.assertEqual(step1.answer_text(tokenizer, ids, stops, newline), "the mill")
        ids = tokenizer.encode(" kelo\n[world] x")
        self.assertEqual(step1.answer_text(tokenizer, ids, stops, newline), "kelo")

    def test_exact_match_after_normalisation(self) -> None:
        self.assertTrue(step1.exact_match(" The Mill. ", "the mill"))
        self.assertTrue(step1.exact_match("red cup, blue key", "Red cup blue key"))
        self.assertFalse(step1.exact_match("mill", "the mill"))
        self.assertFalse(step1.exact_match("the mill yes", "the mill"))
        self.assertFalse(step1.exact_match("", "..."))


class EvaluationInputTest(unittest.TestCase):
    def setUp(self) -> None:
        self.work = Workspace()
        self.data = self.work.data()

    def tearDown(self) -> None:
        self.work.close()

    def test_inputs_end_at_answer_and_match_training_tokens(self) -> None:
        tokenizer = self.data.tokenizer
        answer = tokenizer.token_to_id("[answer]")
        eos = tokenizer.token_to_id("<eos>")
        questions = step1._questions(self.data, "validation")
        seen = {"templates": set(), "styles": set(), "rule_families": set()}
        items = step1.build_items(tokenizer, questions, max_len=200, seen=seen)
        visits = {}
        for text, _ in step1.shard_files(self.data.split_dir("validation")):
            for index, visit in enumerate(step1.read_visits(text)):
                visits[(text.stem, index)] = visit
        for item in items:
            self.assertEqual(item.prompt[-1], answer)
            self.assertTrue(tokenizer.decode(item.prompt).endswith("[answer]"))
            self.assertFalse(item.truncated)
            self.assertEqual(item.prompt[0], eos)
            visit = visits[(item.question.shard, item.question.visit)]
            full = step1.encode_visit(tokenizer, [line for _, line in visit], eos)
            self.assertEqual(full[: len(item.prompt) - 1], item.prompt[1:])   # a prefix of training text
            self.assertEqual(item.template, "unseen")
        # A short budget keeps whole lines from the end and drops the separator.
        short = step1.build_items(tokenizer, questions[:1], max_len=40, seen=seen)[0]
        self.assertTrue(short.truncated)
        self.assertNotEqual(short.prompt[0], eos)
        kept = short.context_text.split("\n")
        self.assertEqual(kept, [line for _, line in questions[0].context[-len(kept):]])
        with self.assertRaises(AssertionError):
            bad = step1.EvalItem(**{**short.__dict__, "prompt": short.prompt + [5]})
            step1.score_items(Core(CoreConfig(tokenizer.vocab_size, 64, 16, 1, 1)), tokenizer, [bad],
                              max_new=4, batch_size=2)

    def test_every_input_is_audited(self) -> None:
        sets = step1.build_eval_sets(self.data, seq_len=128, max_new=8, heldout_limit=40,
                                     heldin_limit=20, probe_limit=10, subset=10, seed=0, lm_rows_limit=2)
        audit = step1.audit_inputs(self.data.tokenizer, sets)
        self.assertEqual(audit["heldout"]["inputs"], len(sets.heldout))
        self.assertEqual(audit["signatures"]["validation"], "text")   # the fake village has no oracle
        bad = sets.heldout[0]
        answer = self.data.tokenizer.encode(" " + bad.question.answer)
        sets.heldout[0] = step1.EvalItem(**{**bad.__dict__, "prompt": bad.prompt[:-1] + answer + bad.prompt[-1:]})
        with self.assertRaises(AssertionError):
            step1.audit_inputs(self.data.tokenizer, sets)

    def test_eval_sets_shrink_to_fit_the_time_budget(self) -> None:
        sets = step1.build_eval_sets(self.data, seq_len=128, max_new=8, heldout_limit=40,
                                     heldin_limit=20, probe_limit=10, subset=10, seed=0, lm_rows_limit=2)
        before = sets.counts()
        everyone = {item.question.id for item in sets.heldout}
        roomy = step1.fit_eval_sets(sets, 1e-6, seconds=60, points=6, seed=0)
        self.assertFalse(roomy["shrunk"])
        self.assertEqual(sets.counts(), before)
        tight = step1.fit_eval_sets(sets, 0.1, seconds=10, points=6, seed=0)   # 3 s for the final eval
        self.assertTrue(tight["shrunk"])
        final = len(sets.heldout) + len(sets.heldout_long_range) + len(sets.heldin) + len(sets.probe)
        self.assertLessEqual(final * 0.1, 3.0 + 1e-9)
        self.assertLess(len(sets.heldout), before["heldout"])
        kept = {item.question.id for item in sets.heldout}
        for item in sets.heldout:
            if item.question.twin in everyone:
                self.assertIn(item.question.twin, kept)     # twins are kept or dropped together

    def test_evaluation_is_read_only(self) -> None:
        tokenizer = self.data.tokenizer
        questions = step1._questions(self.data, "test")
        items = step1.build_items(tokenizer, questions, max_len=100,
                                  seen={"templates": set(), "styles": set(), "rule_families": set()})
        torch.manual_seed(0)
        model = Core(CoreConfig(tokenizer.vocab_size, 128, 32, 2, 2))
        trainer = Trainer(model, TrainConfig(batch=2, seq_len=128), "cpu")
        before = {k: v.clone() for k, v in model.state_dict().items()}
        results = trainer.evaluate(lambda m: step1.score_items(m, tokenizer, items, max_new=8,
                                                               batch_size=4))
        self.assertEqual(len(results), len(items))
        for key, value in model.state_dict().items():
            self.assertTrue(torch.equal(value, before[key]), key)

        def cheating(m):
            with torch.no_grad():
                m.embed.weight.add_(1.0)

        with self.assertRaises(ReadOnlyViolation):
            trainer.evaluate(cheating)


def fake_results(n, correct, **fields):
    base = {"split": "test", "qtype": "Q1", "depth": 1, "visible": True, "knowable": True,
            "rule_families": ["R9"], "heldout_family": True, "template": "unseen", "style": "terse",
            "style_status": "unseen", "name_answer": False, "truncated": False,
            "evidence_kept": True, "repeat_in_context": False, "twin": None, "answer": "the mill",
            "prediction": "the mill"}
    base.update(fields)
    return [{**base, "id": f"r{i}", "correct": i < correct} for i in range(n)]


class CombineLeakReportsTest(unittest.TestCase):
    def report(self, status, n, leaking=()):
        return {"status": status, "n": n,
                "detectors": {name: {"leaking": name in leaking, "accuracy": 0.3, "null": 0.1}
                              for name in ("majority", "target_line")}}

    def test_any_leaking_class_leaks_and_is_named(self) -> None:
        combined = step1.combine_leak_reports({"place": self.report("clean", 900),
                                               "person": self.report("leaking", 300, ["target_line"])})
        self.assertEqual(combined["status"], "leaking")
        self.assertEqual(combined["leaking_detectors"], ["person/target_line"])

    def test_clean_needs_testable_classes_to_cover_most_items(self) -> None:
        clean = {"place": self.report("clean", 950), "what if: ev.go": self.report("insufficient", 50)}
        self.assertEqual(step1.combine_leak_reports(clean)["status"], "clean")
        thin = {"place": self.report("clean", 500), "what if: ev.go": self.report("insufficient", 500)}
        self.assertEqual(step1.combine_leak_reports(thin)["status"], "insufficient")
        self.assertEqual(step1.combine_leak_reports({})["status"], "insufficient")


class GateTest(unittest.TestCase):
    def metrics(self, hits=1900, n=2000, pairs=(800, 1000, 0.1), leak="clean", points=5, stall=0.01):
        cell = {"hits": hits, "n": n}
        return {"heldout_visible": cell, "unseen_templates": cell, "unseen_styles": cell,
                "heldout_rule_families": cell,
                "pairs": {"hits": pairs[0], "n": pairs[1], "chance": pairs[2]},
                "leak_status": leak, "forgetting_points": points, "world_stall_fraction": stall}

    def test_pass(self) -> None:
        gate = step1.step1_gate(self.metrics())
        self.assertEqual(gate["status"], "PASS", gate["reasons"])
        self.assertEqual(gate["reasons"], [])

    def test_fail(self) -> None:
        self.assertEqual(step1.step1_gate(self.metrics(hits=1500))["status"], "FAIL")
        self.assertEqual(step1.step1_gate(self.metrics(leak="leaking"))["status"], "FAIL")
        self.assertEqual(step1.step1_gate(self.metrics(stall=0.2))["status"], "FAIL")
        gate = step1.step1_gate(self.metrics(pairs=(12, 1000, 0.01)))
        self.assertEqual(gate["status"], "FAIL")
        self.assertTrue(any("counterfactual_pairs" in reason for reason in gate["reasons"]))

    def test_insufficient(self) -> None:
        for metrics in (self.metrics(hits=19, n=20), self.metrics(hits=1810, n=2000),
                        self.metrics(leak="insufficient"), self.metrics(points=1),
                        self.metrics(stall=None), self.metrics(pairs=(40, 50, 0.1))):
            gate = step1.step1_gate(metrics)
            self.assertEqual(gate["status"], "INSUFFICIENT", gate["reasons"])
        # A fail anywhere outranks insufficient elsewhere.
        self.assertEqual(step1.step1_gate(self.metrics(hits=10, n=20, leak="leaking"))["status"], "FAIL")

    def test_never_passes_below_the_minimum_n(self) -> None:
        """Even a perfect score is INSUFFICIENT below policy.MIN_ITEMS, on every counted criterion."""
        limit = step1.MIN_ITEMS
        for key in ("heldout_visible", "unseen_templates", "unseen_styles", "heldout_rule_families"):
            metrics = self.metrics()
            metrics[key] = {"hits": limit - 1, "n": limit - 1}
            gate = step1.step1_gate(metrics)
            self.assertEqual(gate["status"], "INSUFFICIENT", key)
            entry = next(c for c in gate["criteria"] if c["criterion"] == key)
            self.assertEqual(entry["status"], "INSUFFICIENT")
            metrics[key] = {"hits": limit, "n": limit}
            self.assertEqual(step1.step1_gate(metrics)["status"], "PASS", key)
        metrics = self.metrics(pairs=(limit - 1, limit - 1, 0.01))
        self.assertEqual(step1.step1_gate(metrics)["status"], "INSUFFICIENT")
        metrics = self.metrics()
        metrics["pairs"]["chance"] = None
        self.assertEqual(step1.step1_gate(metrics)["status"], "INSUFFICIENT")
        missing = self.metrics()
        del missing["unseen_templates"], missing["world_stall_fraction"]
        self.assertEqual(step1.step1_gate(missing)["status"], "INSUFFICIENT")
        # 94/100 has a lower one-sided 99% bound below 0.9: not enough evidence either way.
        self.assertEqual(step1.step1_gate(self.metrics(hits=94, n=100))["status"], "INSUFFICIENT")

    def test_summaries_pairs_and_name_gap(self) -> None:
        results = fake_results(10, 7)
        summary = step1.summarize(results)
        self.assertEqual(summary["overall"]["hits"], 7)
        self.assertEqual(set(summary["by_template"]), {"unseen"})
        low, high = summary["overall"]["wilson95"]
        self.assertLess(low, 0.7)
        self.assertGreater(high, 0.7)
        for i, r in enumerate(results):
            r["twin"] = f"pair-{i // 2}"
        examples = {r["id"]: step1.QAExample("Kelo went to the mill.", "Where?", "the mill")
                    for r in results}
        pairs = step1.pair_summary(results, examples)
        self.assertEqual((pairs["n"], pairs["hits"]), (5, 3))
        self.assertEqual(pairs["chance"], 1.0)   # one candidate: guessing is always right
        gap = step1.name_gap(fake_results(40, 30, name_answer=True), fake_results(40, 10, name_answer=True))
        self.assertTrue(gap["measurable"])
        self.assertAlmostEqual(gap["gap"], 0.5)
        self.assertFalse(step1.name_gap(fake_results(5, 5, name_answer=True), [])["measurable"])


class EndToEndTest(unittest.TestCase):
    def test_twenty_second_cpu_smoke(self) -> None:
        work = Workspace()
        self.addCleanup(work.close)
        logs = []
        started = time.perf_counter()
        report = step1.run_step1(
            work.budget, size="tiny", device="cpu", seconds=20, visits="tiny", seed=0, workers=1,
            seq_len=128, batch=8, eval_limit=40, max_new=8, writer=fake_write_shards,
            log=logs.append)
        elapsed = time.perf_counter() - started
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["model"], "premonition")
        self.assertLess(report["elapsed_seconds"], 20 + 5)
        self.assertGreater(report["train"]["steps"], 0)
        self.assertGreaterEqual(len(report["evaluations"]), 2)
        for key in ("heldout_visible", "heldout_repeats", "heldout_long_range", "train_heldin", "probe",
                    "generalisation_gap", "counterfactual_pairs", "name_gap", "plan_grading"):
            self.assertIn(key, report["final"])
        self.assertEqual(report["input_audit"]["heldout"]["inputs"], report["eval_sets"]["heldout"])
        self.assertIsNone(report["name_token_audit"]["warning"])     # the fitted tokenizer splits names
        self.assertIsNone(report["final"]["plan_grading"]["checker"])     # no oracle for the fake village
        held = report["final"]["heldout_visible"]
        self.assertEqual(set(held["by_split"]), {"validation", "test"})
        for axis in ("by_qtype", "by_depth", "by_rule_family", "by_knowable", "by_template",
                     "by_style", "by_style_status"):
            self.assertIn(axis, held)
        self.assertEqual(set(held["by_template"]), {"unseen"})
        self.assertEqual(set(held["by_rule_family"]), {"R8", "R9"})
        self.assertIn(report["gate"]["status"], ("PASS", "FAIL", "INSUFFICIENT"))
        self.assertEqual(report["gate"]["status"], "INSUFFICIENT")   # far too few items to pass
        self.assertIn("status", report["leaks"])
        self.assertIsNotNone(report["world"]["stall_fraction"])
        self.assertGreater(report["world"]["epochs"], 0)
        self.assertTrue(report["artifact"].startswith("artifacts/premonition-step1-tiny-"))
        self.assertTrue((work.root / report["checkpoint"] / "manifest.json").is_file())
        saved = json.loads((work.root / report["artifact"]).read_text())
        self.assertEqual(saved["gate"]["status"], report["gate"]["status"])
        text = step1.format_summary(report)
        self.assertIn("GATE:", text)
        print(f"\n[step1 smoke] {elapsed:.1f}s wall; train {report['train']['steps']} steps "
              f"{report['train']['tokens_per_s']:,.0f} tok/s loss {report['train']['final_loss']:.3f}; "
              f"held-out {held['overall']['hits']}/{held['overall']['n']}; "
              f"held-in {report['final']['train_heldin']['overall']['hits']}/"
              f"{report['final']['train_heldin']['overall']['n']}; gate {report['gate']['status']}")


if __name__ == "__main__":
    unittest.main()
