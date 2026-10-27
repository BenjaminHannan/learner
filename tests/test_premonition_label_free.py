"""Milestone 1 (design/06 §11): trustworthy label-free inputs and evaluation. CPU, real village shards.

1. Isolation. Changing an earlier answer or feedback (even inserting a fresh name only there) leaves every
   later label-free input identical: D's reader tensors, name tables, entity mentions and eligible cards,
   and the A / C / E prompts; a fixed model under `read_only` predicts the same. Changing the current answer
   changes only its supervised target. The legacy path (whole-line cache + batch-level masking) is shown to
   bind the fresh name.
2. Identity. The preprocessing digest names the rules; caches live under it; a golden visit pins it.
3. Scoring boundaries: an unbound output entity is a wrong prediction, a malformed target or input an error.
4. Checkpoints fail closed; mixed-regime or non-primary reports never produce a verdict.
5. C's candidates: evidence inside A's window but outside C's is eligible now (it was lost before).
"""
from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import random
import shutil
import tempfile
import unittest

import torch

from learnlab import step1
from learnlab.ckpt import save_checkpoint
from learnlab.core import Core, CoreConfig
from learnlab.readonly import read_only
from learnlab.step1 import ANSWER_TAG, FEEDBACK_TAG, QUESTION_TAG
from learnlab.tokenizer import Tokenizer
from premonition import contenders, exp1, identity, lookup, preprocess, slices
from premonition import data as pdata
from premonition.batch import N_ENT, NameTable
from premonition.config import MiniConfig
from premonition.model import PremonitionMini
from premonition.pointer import NameDetector, pointerize_lines
from premonition.preprocess import LABEL_FREE, WITH_LABELS, MalformedInput, MalformedTarget
from premonition.train import (MiniTrainer, checkpoint_config, d_scorer, evaluate_d_checkpoint, judge, label_free,
                               mini_train_config, save_mini_checkpoint)
from tests.test_premonition_contenders import fixture, train_bm25

QUIET = lambda _message: None  # noqa: E731
PROJECT = Path(__file__).resolve().parents[1]
FRESH = "Zyxqo"                 # a name no village has: it appears only in the planted label
FRESH_FEEDBACK = "Qwyxa"
SEEN = {"templates": set(), "styles": set(), "rule_families": set()}

# Golden identity (design/06 §11.1). Changing a preprocessing rule must change the spec, hence the digest,
# hence every cache path; and the output of GOLDEN_LINES under the v2 tokenizer is pinned to that digest.
# If this test fails after an intended rule change: bump preprocess.VERSION and update both pins.
PINNED_DIGEST = {LABEL_FREE: "9add8e2fded136434c37f8b97641f83528b920c640693ff89011bd452b36e3c7",
                 WITH_LABELS: "bdf907371b40740e50dbd054ca1617904ed327d72e5b548da08885019e51f40b"}
PINNED_OUTPUT = "262ee80798bd3a16eda1fe47c45891c8929d4c6db2725f6c38ddb5241c737d37"   # preprocess v1, tokenizer v2
GOLDEN_LINES = (
    "[world] Kelo walked to the mill.",
    f"[question] Where is Kelo? [answer] the mill [feedback] Right, {FRESH} agrees.",
    "[question] Who walked to the barn? [answer] Rami [feedback] Right.",
    "[world] Rami walked to the barn.",
    "[question] Who is at the barn? [answer] Rami [feedback] Right.",
)
GOLDEN_FIT = "where is who walked to the mill barn right agrees at kelo rami"


def golden_detector() -> NameDetector:
    return NameDetector.fit([GOLDEN_FIT.replace("kelo ", "").replace(" rami", "")], vocabulary=())


def v2_tokenizer() -> Tokenizer:
    path = PROJECT / identity.V2_TOKENIZER["path"]
    if not path.is_file():
        raise unittest.SkipTest(f"{path} is not in this checkout")
    return Tokenizer.load(path)


def prepared_fingerprint(visit: preprocess.PreparedVisit) -> str:
    payload = {"tokens": visit.tokens, "starts": visit.starts, "table": visit.table.spellings,
               "questions": {k: [q.span, q.target, q.unbound] for k, q in sorted(visit.questions.items())},
               "label_only": visit.label_only_names}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


# ----------------------------------------------------------------- shard surgery


def question_lines(split_dir: Path) -> list[step1.Question]:
    return [q for text, meta in step1.shard_files(split_dir) for q in step1.read_questions(text, meta, "validation")]


def rewrite_label(split_dir: Path, qid: str, answer: str, feedback: str) -> None:
    """Rewrite one question line's answer and feedback in place (and its record's answer, which must match)."""
    for text, meta in step1.shard_files(split_dir):
        questions = {q.id: q for q in step1.read_questions(text, meta, "validation")}
        if qid not in questions:
            continue
        q = questions[qid]
        lines = text.read_text(encoding="utf-8").split("\n")
        asked, _, _ = step1.parse_question_line(lines[q.line])
        lines[q.line] = f"{QUESTION_TAG} {asked} {ANSWER_TAG} {answer} {FEEDBACK_TAG} {feedback}"
        text.write_text("\n".join(lines), encoding="utf-8")
        rows = [json.loads(line) for line in meta.read_text(encoding="utf-8").splitlines() if line.strip()]
        for row in rows:
            if row.get("id") == qid:
                row["answer"] = answer
        meta.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        return
    raise KeyError(qid)


class PreprocessRulesTest(unittest.TestCase):
    """The shared rules on a hand-made visit: labels leave before names are bound."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tokenizer = Tokenizer.train(["\n".join(GOLDEN_LINES)], vocab_size=300)
        cls.detector = golden_detector()

    def test_visible_lines(self) -> None:
        line = GOLDEN_LINES[1]
        self.assertEqual(preprocess.visible_line(line), "[question] Where is Kelo? [answer]")
        self.assertEqual(preprocess.visible_line(line, WITH_LABELS), line)
        self.assertEqual(preprocess.visible_line(GOLDEN_LINES[0]), GOLDEN_LINES[0])
        with self.assertRaises(MalformedInput):
            preprocess.visible_line("[question] Where is Kelo?")                  # no [answer] tag
        with self.assertRaises(MalformedInput):
            preprocess.visible_line("[world] odd [feedback] text")               # a label outside a question
        with self.assertRaises(ValueError):
            preprocess.visible_line(line, "labels-please")
        self.assertEqual(lookup.shown(line, False), preprocess.visible_line(line))  # C and E share the rule

    def test_names_are_bound_from_visible_text_only(self) -> None:
        free = preprocess.prepare_visit(GOLDEN_LINES, self.tokenizer, self.detector)
        self.assertEqual(free.table.spellings, {0: "Kelo", 1: "Rami"})
        self.assertEqual(free.label_only_names, (FRESH,))
        # The legacy whole-line binding takes the fresh name from the feedback and shifts Rami to ENT2.
        _, legacy = pointerize_lines(list(GOLDEN_LINES), self.tokenizer, self.detector)
        self.assertEqual(legacy.spellings, {0: "Kelo", 1: FRESH, 2: "Rami"})
        base = self.tokenizer.vocab_size
        second, third = free.questions[2], free.questions[4]
        # "Who walked to the barn?" is asked before Rami is ever visible: the target cannot bind him.
        self.assertEqual(second.unbound, ("Rami",))
        self.assertNotIn(base + 1, second.target)
        self.assertEqual(preprocess.target_text(second.target, free.table, self.tokenizer).lower(), "rami")
        # After "[world] Rami walked ..." the same answer is ENT1.
        self.assertEqual(third.unbound, ())
        self.assertIn(base + 1, third.target)
        self.assertEqual(preprocess.target_text(third.target, free.table, self.tokenizer), "Rami")
        # Spans end at "[answer]", a newline follows, and nothing of any answer or feedback is in the stream.
        answer_id = self.tokenizer.token_to_id(ANSWER_TAG)
        tokens = free.tokens
        for k, q in free.questions.items():
            self.assertEqual(tokens[q.span[1] - 1], answer_id)
            self.assertEqual(tokens[q.span[1]:q.span[1] + 1], self.tokenizer.encode("\n"))
        preprocess.audit_stream(tokens, self.tokenizer, LABEL_FREE)
        with_labels = preprocess.prepare_visit(GOLDEN_LINES, self.tokenizer, self.detector, regime=WITH_LABELS)
        with self.assertRaises(MalformedInput):
            preprocess.audit_stream(with_labels.tokens, self.tokenizer, LABEL_FREE)

    def test_changing_any_label_changes_only_its_target(self) -> None:
        base = preprocess.prepare_visit(GOLDEN_LINES, self.tokenizer, self.detector)
        for k in (1, 2, 4):
            lines = list(GOLDEN_LINES)
            asked, _, _ = step1.parse_question_line(lines[k])
            lines[k] = f"{QUESTION_TAG} {asked} {ANSWER_TAG} {FRESH} ran off [feedback] No, {FRESH_FEEDBACK} did."
            other = preprocess.prepare_visit(lines, self.tokenizer, self.detector)
            self.assertEqual(other.tokens, base.tokens, k)
            self.assertEqual(other.table, base.table, k)
            for j, q in base.questions.items():
                mine = other.questions[j]
                self.assertEqual((mine.span, mine.bound), (q.span, q.bound))
                if j == k:
                    self.assertNotEqual(mine.target, q.target)
                    self.assertIn(FRESH, mine.unbound)                      # flagged, never bound
                else:
                    self.assertEqual((mine.target, mine.unbound), (q.target, q.unbound))

    def test_scoring_boundaries(self) -> None:
        table = NameTable({0: "Kelo"})
        base = self.tokenizer.vocab_size
        newline = self.tokenizer.encode("\n")
        text, unbound = preprocess.prediction_text([base + 5, *newline], table, self.tokenizer)
        self.assertEqual((text, unbound), ("<ent5>", True))
        self.assertFalse(step1.exact_match(text, "Rami"))
        self.assertEqual(preprocess.prediction_text([base, *newline], table, self.tokenizer), ("Kelo", False))
        self.assertEqual(preprocess.prediction_text([base + 99], table, self.tokenizer), ("", False))
        with self.assertRaises(MalformedTarget):
            preprocess.target_text([base + 5, *newline], table, self.tokenizer)
        with self.assertRaises(MalformedTarget):
            preprocess.target_text(newline, table, self.tokenizer)
        self.assertTrue(issubclass(MalformedTarget, ValueError) and not issubclass(MalformedTarget, MalformedInput))

    def test_input_audit(self) -> None:
        tok = self.tokenizer
        good = tok.encode("[question] Where is Kelo? [answer]\n[question] Who? [answer]")
        preprocess.audit_ids(good, tok, LABEL_FREE)
        with self.assertRaises(MalformedInput):
            preprocess.audit_ids(tok.encode("[question] Where is Kelo? [answer] the mill\n[question] Who? [answer]"),
                                 tok, LABEL_FREE)
        with self.assertRaises(MalformedInput):
            preprocess.audit_ids(tok.encode("[world] Kelo. [feedback] Right.\n[question] Who? [answer]"),
                                 tok, LABEL_FREE)
        preprocess.audit_ids(tok.encode("[question] Q [answer] the mill [feedback] ok\n[question] Who? [answer]"),
                             tok, WITH_LABELS)                               # with labels: not audited

    def test_identity_and_golden_pin(self) -> None:
        self.assertNotEqual(preprocess.digest(LABEL_FREE), preprocess.digest(WITH_LABELS))
        self.assertEqual(preprocess.identity_problems(preprocess.identity(LABEL_FREE)), [])
        self.assertTrue(preprocess.identity_problems(None))
        stale = {**preprocess.identity(LABEL_FREE), "digest": "0" * 64}
        self.assertIn("not today's", preprocess.identity_problems(stale)[0])
        self.assertTrue(preprocess.identity_problems({**preprocess.identity(LABEL_FREE), "version": 0}))
        for regime, pinned in PINNED_DIGEST.items():
            self.assertEqual(preprocess.digest(regime), pinned, f"{regime}: bump preprocess.VERSION and re-pin")
        visit = preprocess.prepare_visit(GOLDEN_LINES, v2_tokenizer(), golden_detector())
        self.assertEqual(prepared_fingerprint(visit), PINNED_OUTPUT,
                         "label-free output changed: bump preprocess.VERSION and re-pin both values")


class VillageIsolationTest(unittest.TestCase):
    """The adversarial isolation checks on real village shards (40 train + 24 held-out visits)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root, cls.budget, cls.data, cls.questions = fixture()
        cls.tokenizer = cls.data.tokenizer
        cls.detector = pdata.name_detector(cls.budget, cls.data.rel, log=QUIET)
        cls.bm25 = train_bm25(cls.data)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dirs = {}
        by_visit: dict[tuple[str, int], list[step1.Question]] = {}
        for q in cls.questions:
            by_visit.setdefault((q.shard, q.visit), []).append(q)
        # The visit with the most questions; perturb its FIRST question (earlier label) and its LAST one
        # (the current answer of the last question).
        cls.visit_questions = max(by_visit.values(), key=len)
        cls.early, cls.last = cls.visit_questions[0], cls.visit_questions[-1]
        source = cls.data.split_dir("validation")
        for name, target in (("original", None), ("early", cls.early), ("last", cls.last)):
            folder = Path(cls.tmp.name) / name
            shutil.copytree(source, folder)
            if target is not None:
                rewrite_label(folder, target.id, f"{FRESH} took the barn",
                              f"No! {FRESH_FEEDBACK} says {FRESH} took it.")
            cls.dirs[name] = folder
        cls.caches = {name: pdata.build_cache(folder, cls.tokenizer, cls.detector, split="validation",
                                              regime=LABEL_FREE) for name, folder in cls.dirs.items()}
        cls.legacy = {name: pdata.build_cache(folder, cls.tokenizer, cls.detector, split="validation")
                      for name, folder in cls.dirs.items()}
        cls.qs = {name: {q.id: q for q in question_lines(folder)} for name, folder in cls.dirs.items()}

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def visit_index(self, cache: pdata.VisitCache) -> int:
        position = cache.question_ids.index(self.early.id)
        return next(v for v in range(len(cache)) if position in cache.questions_of(v))

    def batch(self, name: str, legacy: bool = False):
        cache = (self.legacy if legacy else self.caches)[name]
        batch = pdata.collate(cache, [self.visit_index(cache)])
        return label_free(batch) if legacy else batch

    def test_the_perturbation_is_real(self) -> None:
        self.assertGreaterEqual(len(self.visit_questions), 3)
        self.assertIn(FRESH, self.qs["early"][self.early.id].raw_line)
        self.assertNotIn(FRESH, "\n".join(line for _, line in self.early.context))
        self.assertEqual(self.qs["early"][self.early.id].answer, f"{FRESH} took the barn")

    def test_d_inputs_are_identical_and_only_the_target_moves(self) -> None:
        original = self.batch("original")
        for name, moved in (("early", self.early), ("last", self.last)):
            other = self.batch(name)
            for field in ("tokens", "line_of", "card_end", "lengths", "lm_mask", "line_is_question", "line_start",
                          "line_ents", "q_visit", "q_line", "q_span", "gold_lines", "depth"):
                self.assertTrue(torch.equal(getattr(other, field), getattr(original, field)), (name, field))
            self.assertEqual(other.names, original.names, name)
            self.assertNotIn(FRESH, other.names[0].spellings.values())
            for q, qid in enumerate(original.question_ids):
                same = torch.equal(other.answer[q], original.answer[q])
                self.assertEqual(same, qid != moved.id, (name, qid))
            cache = self.caches[name]
            flagged = {qid for qid, bad in zip(cache.question_ids, cache.target_unbound.tolist()) if bad}
            self.assertEqual(flagged, {moved.id}, name)                     # the fresh target name is flagged
        # The legacy path binds the fresh name from the label and puts it in the name table.
        legacy = self.batch("early", legacy=True)
        self.assertIn(FRESH, legacy.names[0].spellings.values())
        self.assertNotIn(FRESH, self.batch("original", legacy=True).names[0].spellings.values())

    def test_a_fixed_d_predicts_the_same_under_read_only(self) -> None:
        torch.manual_seed(0)
        model = PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=self.tokenizer.vocab_size)).eval()
        stops = sorted(step1.stop_ids(self.tokenizer)[0])
        outputs = {}
        with read_only(model):
            for name in ("original", "early", "last"):
                batch = self.batch(name)
                answers = model.answer(batch, stop=stops)
                texts = judge(answers, batch, tokenizer=self.tokenizer, stop=stops)[1]
                outputs[name] = (answers.tokens, answers.loops, answers.first_top, texts)
        for name in ("early", "last"):
            for mine, theirs in zip(outputs[name][:3], outputs["original"][:3]):
                self.assertTrue(torch.equal(mine, theirs), name)
            self.assertEqual(outputs[name][3], outputs["original"][3], name)

    def test_core_prompts_and_predictions_are_identical(self) -> None:
        free = lookup.LineIds(self.tokenizer, regime=LABEL_FREE)
        labelled = lookup.LineIds(self.tokenizer, regime=WITH_LABELS)
        torch.manual_seed(0)
        core = Core(CoreConfig(self.tokenizer.vocab_size, 768, 32, 2, 2)).eval()
        pointer_core = Core(CoreConfig(self.tokenizer.vocab_size + N_ENT, 768, 32, 2, 2)).eval()
        stops, _ = step1.stop_ids(self.tokenizer)
        pad = self.tokenizer.token_to_id("<pad>")
        leaked = 0
        for name in ("early", "last"):
            later = [q for q in self.visit_questions if q.line >= self.early.line]
            for q in later:
                mine, theirs = self.qs[name][q.id], self.qs["original"][q.id]
                a = lookup.plain_input(mine, free)[0]
                self.assertEqual(a, lookup.plain_input(theirs, free)[0], q.id)
                c, c0 = lookup.lookup_input(mine, free, self.bm25), lookup.lookup_input(theirs, free, self.bm25)
                self.assertEqual((c.ids, c.recall.lines), (c0.ids, c0.recall.lines), q.id)
                e = contenders.pointer_input(mine, self.tokenizer, self.detector, regime=LABEL_FREE)
                e0 = contenders.pointer_input(theirs, self.tokenizer, self.detector, regime=LABEL_FREE)
                self.assertEqual((e.ids, e.table), (e0.ids, e0.table), q.id)
                self.assertNotIn(FRESH, e.table.spellings.values())
                for ids in (a, c.ids, e.ids):
                    preprocess.audit_ids(ids, self.tokenizer, LABEL_FREE)
                with read_only(core), read_only(pointer_core):
                    got = step1.greedy_decode(core, [a, c.ids], max_new=6, stop=stops, batch_size=2, pad_id=pad)
                    ref = step1.greedy_decode(core, [lookup.plain_input(theirs, free)[0], c0.ids], max_new=6,
                                              stop=stops, batch_size=2, pad_id=pad)
                    self.assertEqual(got, ref, q.id)
                    self.assertEqual(
                        step1.greedy_decode(pointer_core, [e.ids], max_new=6, stop=stops, batch_size=1, pad_id=pad),
                        step1.greedy_decode(pointer_core, [e0.ids], max_new=6, stop=stops, batch_size=1, pad_id=pad))
                # With labels (the diagnostic regime) the rewritten answer IS visible to later questions.
                if q.line > self.early.line and name == "early":
                    leaked += lookup.plain_input(mine, labelled)[0] != lookup.plain_input(theirs, labelled)[0]
        self.assertGreater(leaked, 0)

    def test_label_free_tags_are_identical_across_the_perturbation(self) -> None:
        tags = {}
        for name in ("original", "early"):
            questions = [self.qs[name][q.id] for q in self.visit_questions]
            items, tags[name] = slices.tag_questions(self.tokenizer, questions, seen=SEEN, source="validation")
            for item in items:
                preprocess.audit_ids(item.prompt, self.tokenizer, LABEL_FREE)
        for qid, tag in tags["original"].items():
            mine = tags["early"][qid]
            self.assertEqual((mine.near, mine.far, mine.evidence_kept, mine.slices() if qid != self.early.id else 0),
                             (tag.near, tag.far, tag.evidence_kept, tag.slices() if qid != self.early.id else 0))

    def test_new_cache_equals_legacy_masking_where_legacy_was_right(self) -> None:
        """On unperturbed shards no name is written only in a label, so the v2 cache must reproduce the
        legacy cache after `train.label_free` exactly: the new path changes nothing it did not have to."""
        new, old = self.caches["original"], self.legacy["original"]
        self.assertEqual(new.info["stats"].get("label_only_names", 0), 0)
        visits = list(range(len(new)))
        a, b = pdata.collate(new, visits), label_free(pdata.collate(old, visits))
        for field in ("tokens", "line_of", "card_end", "lm_mask", "line_start", "line_ents", "q_span", "answer",
                      "gold_lines"):
            self.assertTrue(torch.equal(getattr(a, field), getattr(b, field)), field)
        self.assertEqual(a.names, b.names)
        answer_id, feedback_id = (self.tokenizer.token_to_id(t) for t in (ANSWER_TAG, FEEDBACK_TAG))
        self.assertNotIn(feedback_id, new.tokens.tolist())
        self.assertTrue(bool((new.answer_end == new.q_span[:, 1] + 1).all()))
        for row in range(a.size[0]):
            preprocess.audit_stream(a.tokens[row, :int(a.lengths[row])].tolist(), self.tokenizer, LABEL_FREE)
        self.assertFalse(bool(a.lm_mask[a.tokens == answer_id].any()))

    def test_cache_identity_paths_and_files(self) -> None:
        old = pdata.cache_relative("d", "validation", self.tokenizer, self.detector)
        new = pdata.cache_relative("d", "validation", self.tokenizer, self.detector, LABEL_FREE)
        self.assertEqual(old, f"d/premonition-v1-{self.tokenizer.digest[:12]}-{self.detector.digest[:12]}/"
                              "validation.pt")                                   # the old identity is kept
        self.assertIn(preprocess.digest(LABEL_FREE)[:12], new)
        self.assertNotEqual(Path(old).parent, Path(new).parent)
        with tempfile.TemporaryDirectory() as folder:
            for cache, name in ((self.caches["original"], "v2.pt"), (self.legacy["original"], "v1.pt")):
                path = Path(folder) / name
                path.write_bytes(cache.to_bytes())
                again = pdata.VisitCache.load(path)
                self.assertEqual(again.regime, cache.regime)
                self.assertTrue(torch.equal(again.tokens, cache.tokens))
            self.assertIsNone(pdata.VisitCache.load(Path(folder) / "v1.pt").target_unbound)
            stale = replace(self.caches["original"], info={**self.caches["original"].info,
                                                           "preprocess": {**preprocess.identity(LABEL_FREE),
                                                                          "digest": "f" * 64}})
            (Path(folder) / "stale.pt").write_bytes(stale.to_bytes())
            with self.assertRaisesRegex(ValueError, "not today's"):
                pdata.VisitCache.load(Path(folder) / "stale.pt")

    def test_d_scorer_needs_the_label_free_cache(self) -> None:
        with self.assertRaisesRegex(ValueError, "label-free visit cache"):
            d_scorer(self.legacy["original"])
        d_scorer(self.caches["original"])
        d_scorer(self.legacy["original"], regime=WITH_LABELS)
        with self.assertRaises(ValueError):
            d_scorer(self.caches["original"], regime=WITH_LABELS)

    def test_judge_scores_unbound_entities_wrong_and_malformed_targets_raise(self) -> None:
        batch = self.batch("original")
        torch.manual_seed(0)
        model = PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=self.tokenizer.vocab_size)).eval()
        stops = sorted(step1.stop_ids(self.tokenizer)[0])
        answers = model.answer(batch, stop=stops)
        base = self.tokenizer.vocab_size
        unused = next(e for e in range(N_ENT) if e not in batch.names[0].spellings)
        answers.tokens[:, 0] = base + unused                                   # an entity nobody was bound to
        correct, texts = judge(answers, batch, tokenizer=self.tokenizer, stop=stops)
        self.assertFalse(any(correct))
        self.assertTrue(all(text.startswith(f"<ent{unused}>") for text in texts))
        broken = replace(batch, answer=batch.answer.clone())
        broken.answer[0, 0] = base + unused
        with self.assertRaises(MalformedTarget):
            judge(answers, broken, tokenizer=self.tokenizer, stop=stops)


class CandidateWindowTest(unittest.TestCase):
    """design/06 §11.5: every non-question line before C's own window start is eligible."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root, cls.budget, cls.data, cls.questions = fixture()
        cls.tokenizer = cls.data.tokenizer
        cls.bm25 = train_bm25(cls.data)

    def planted(self, max_len: int):
        """A question whose evidence sits in A's window but, once C's recall block is placed, not in C's.

        Lines 0-3 mention the query words (BM25 recalls them, so C's block is long), the rest is filler. The
        evidence replaces the filler line just after A's window start; it is shorter than the filler, so A's
        window only grows, and it still lies before C's legacy window start.
        """
        q = self.questions[0]
        facts = [f"[world] Zyzzq kept a red pear in box {i}." for i in range(4)]
        filler = "[world] The old well is quiet today and the meadow is calm and green."
        context = facts + [filler] * 60
        raw = "[question] Where did Zyzzq hide the pear? [answer] the pond [feedback] Right."

        def make(lines):
            return replace(q, context=tuple(enumerate(lines)), line=len(lines), raw_line=raw,
                           question="Where did Zyzzq hide the pear?", answer="the pond", knowable=True, earlier=(),
                           evidence=(evidence,) if evidence is not None else ())

        evidence = None
        lines = lookup.LineIds(self.tokenizer, regime=LABEL_FREE)
        before = lookup.lookup_input(make(context), lines, self.bm25, max_len=max_len,
                                     candidates_rule=preprocess.LEGACY_LOOKUP_CANDIDATES)
        evidence = before.a_start + 1
        self.assertLess(evidence + 1, before.window.start, "the fixture needs a gap of at least two lines")
        context[evidence] = "[world] Zyzzq hid the pear at the pond."
        return make(context), evidence

    def test_evidence_in_a_s_window_but_not_c_s_is_eligible(self) -> None:
        question, evidence = self.planted(300)
        lines = lookup.LineIds(self.tokenizer, regime=LABEL_FREE)
        legacy = lookup.lookup_input(question, lines, self.bm25, max_len=300,
                                     candidates_rule=preprocess.LEGACY_LOOKUP_CANDIDATES)
        self.assertLess(legacy.a_start, evidence)                  # A sees the evidence ...
        self.assertGreater(legacy.window.start, evidence)          # ... C's window does not ...
        self.assertNotIn(evidence, legacy.recall.lines)            # ... and the legacy rule never recalls it
        self.assertIn(evidence, legacy.gap_lines)
        entry = lookup.lookup_input(question, lines, self.bm25, max_len=300)
        self.assertIn(evidence, entry.recall.lines)                 # now eligible, and BM25 finds it
        self.assertEqual(entry.gap_lines, ())
        self.assertGreaterEqual(entry.rounds, 2)
        self.assertEqual(entry.boundary, entry.window.start)
        self.assertTrue(all(n < entry.window.start for n in entry.recall.lines))    # no overlap
        self.assertTrue(all(n < question.line for n in entry.recall.lines))         # no future line
        self.assertLessEqual(len(entry.ids), 300)                                   # no overflow
        self.assertEqual(entry.ids[-1], self.tokenizer.token_to_id(ANSWER_TAG))
        self.assertIn(evidence, entry.evidence_before)

    def test_no_gap_and_no_overflow_on_real_questions(self) -> None:
        lines = lookup.LineIds(self.tokenizer, regime=LABEL_FREE)
        rounds = []
        for max_len in (slices.CUT_MAX_LEN, 300):
            for q in self.questions:
                entry = lookup.lookup_input(q, lines, self.bm25, max_len=max_len)
                self.assertEqual(entry.gap_lines, ())
                self.assertLessEqual(len(entry.ids), max_len)
                eligible = {n for n, line in q.context if n < entry.window.start and not line.startswith(QUESTION_TAG)}
                self.assertLessEqual(set(entry.recall.lines), eligible)
                self.assertEqual(entry.recall.candidates, len(eligible))
                rounds.append(entry.rounds)
        self.assertGreater(max(rounds), 1)                          # the widening loop really runs


class CheckpointIdentityTest(unittest.TestCase):
    """Checkpoints fail closed; reports carry their identity; verdicts refuse what they must."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root, cls.budget, cls.data, cls.questions = fixture()
        cls.v2 = v2_tokenizer()
        cls.v1_path = PROJECT / "data/tokenizer/premonition-tok-v1-fallback.json"

    def a_config(self, tok: Tokenizer, **changes) -> dict:
        d_model, layers, heads = contenders.contender("A").shape
        config = {"contender": "A", "inputs": "plain", "tokenizer": {"sha256": tok.digest},
                  "core": {"vocab_size": tok.vocab_size, "context": 768, "d_model": d_model, "n_layers": layers,
                           "n_heads": heads, "mlp_ratio": 4},
                  "preprocess": preprocess.identity(WITH_LABELS)}
        config.update(changes)
        return config

    def test_v2_tokenizer_is_verified_through_the_api(self) -> None:
        info = identity.verify_v2_tokenizer(PROJECT)
        self.assertEqual(info["vocab_size"], 7068)
        self.assertTrue(info["sha256"].startswith("2c9d06aed330"))
        self.assertEqual(identity.tokenizer_status(self.v2), "v2")
        if self.v1_path.is_file():
            self.assertEqual(identity.tokenizer_status(Tokenizer.load(self.v1_path)), "retired")
        self.assertEqual(identity.tokenizer_status(self.data.tokenizer), "other")

    def test_admission_rules(self) -> None:
        v2 = self.v2
        good = exp1.core_checks(self.a_config(v2), v2, "A")
        self.assertEqual(good, [])
        self.assertEqual(identity.admit(good, v2, regime=LABEL_FREE, purpose="primary"), [])
        with self.assertRaises(identity.CheckpointIncompatible):          # with-labels is never primary
            identity.admit(good, v2, regime=WITH_LABELS, purpose="primary")
        self.assertTrue(identity.admit(good, v2, regime=WITH_LABELS, purpose="diagnostic"))
        missing = exp1.core_checks(self.a_config(v2, preprocess=None), v2, "A")
        self.assertEqual([identity.problem_kind(p) for p in missing], ["preprocess"])
        with self.assertRaises(identity.CheckpointIncompatible):
            identity.admit(missing, v2, regime=LABEL_FREE, purpose="primary")
        legacy = identity.admit(missing, v2, regime=LABEL_FREE, purpose="legacy")
        self.assertTrue(any("legacy/unknown" in p for p in legacy))
        wrong_vocab = exp1.core_checks(self.a_config(v2, core={**self.a_config(v2)["core"], "vocab_size": 6372}),
                                       v2, "A")
        with self.assertRaisesRegex(identity.CheckpointIncompatible, "vocab"):
            identity.admit(wrong_vocab, v2, regime=LABEL_FREE, purpose="legacy")
        no_digest = exp1.core_checks(self.a_config(v2, tokenizer={}), v2, "A")
        with self.assertRaisesRegex(identity.CheckpointIncompatible, "tokenizer"):
            identity.admit(no_digest, v2, regime=LABEL_FREE, purpose="legacy")
        other = exp1.core_checks(self.a_config(self.data.tokenizer), v2, "A")
        with self.assertRaisesRegex(identity.CheckpointIncompatible, "differs"):
            identity.admit(other, v2, regime=LABEL_FREE, purpose="diagnostic")
        stale = exp1.core_checks(self.a_config(v2, preprocess={**preprocess.identity(WITH_LABELS),
                                                               "digest": "0" * 64}), v2, "A")
        with self.assertRaises(identity.CheckpointIncompatible):
            identity.admit(stale, v2, regime=LABEL_FREE, purpose="primary")
        e_as_plain = exp1.core_checks(self.a_config(v2, contender="E", inputs="pointer"), v2, "A")
        self.assertIn("inputs", [identity.problem_kind(p) for p in e_as_plain])
        with self.assertRaisesRegex(identity.CheckpointIncompatible, "never a v2 contender"):
            identity.admit(good, v2, regime=LABEL_FREE, purpose="fixture")
        if self.v1_path.is_file():
            v1 = Tokenizer.load(self.v1_path)
            retired = exp1.core_checks(self.a_config(v1), v1, "A")
            self.assertEqual(retired, [])                                     # the checkpoint is self-consistent,
            with self.assertRaisesRegex(identity.CheckpointIncompatible, "retired"):   # but v1 is retired
                identity.admit(retired, v1, regime=LABEL_FREE, purpose="primary")
            self.assertTrue(identity.admit(retired, v1, regime=LABEL_FREE, purpose="legacy"))

    def test_d_checkpoints_must_record_label_free_visits(self) -> None:
        from premonition.train import d_checks
        tok = self.data.tokenizer
        torch.manual_seed(0)
        model = PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=tok.vocab_size))
        base = {"contender": "D", "tokenizer": {"sha256": tok.digest}, "mini": asdict(model.config),
                "detector": {"sha256": "abc"}, "preprocess": preprocess.identity(LABEL_FREE)}
        found = d_checks(base, tok, model, "abc")
        self.assertEqual([identity.problem_kind(p) for p in found], ["shape"])     # tiny vs the full preset
        found = d_checks({**base, "preprocess": preprocess.identity(WITH_LABELS)}, tok, model, "abc")
        self.assertTrue(any("D reads label-free" in p for p in found))
        found = d_checks({**base, "detector": {}}, tok, model, "abc")
        self.assertTrue(any("name detector" in p for p in found))

    def test_scoring_refuses_before_it_starts(self) -> None:
        budget, data = self.budget, self.data
        torch.manual_seed(0)
        config = contenders.core_config("A", data.tokenizer.vocab_size, size="tiny")
        model = Core(config)
        base = {"contender": "A", "inputs": "plain", "core": asdict(config), "tokenizer": data.tokenizer_info,
                "data": {"dir": data.rel, "tag": data.tag}}
        save_checkpoint(budget, "artifacts/m01-no-preprocess.ckpt", model=model, config=base)
        save_checkpoint(budget, "artifacts/m01-ok.ckpt", model=model,
                        config={**base, "preprocess": preprocess.identity(WITH_LABELS)})
        other = Tokenizer.train(["[world] something else entirely.\n"], vocab_size=280)
        other.save(self.root / "artifacts" / "m01-other-tokenizer.json")
        options = dict(replay=False, max_new=2, directories=["validation"], log=QUIET)
        with self.assertRaisesRegex(identity.CheckpointIncompatible, "not the v2 contender"):
            exp1.evaluate_checkpoint(self.root, "artifacts/m01-ok.ckpt", **options)          # primary by default
        with self.assertRaisesRegex(identity.CheckpointIncompatible, "legacy/unknown"):
            exp1.evaluate_checkpoint(self.root, "artifacts/m01-no-preprocess.ckpt", purpose="fixture", **options)
        with self.assertRaisesRegex(identity.CheckpointIncompatible, "differs"):   # the old override bypass
            exp1.evaluate_checkpoint(self.root, "artifacts/m01-ok.ckpt", purpose="fixture",
                                     tokenizer_path="artifacts/m01-other-tokenizer.json", **options)
        with self.assertRaisesRegex(identity.CheckpointIncompatible, "differs"):
            contenders.evaluate_contender(self.root, "artifacts/m01-ok.ckpt", purpose="fixture",
                                          tokenizer_path="artifacts/m01-other-tokenizer.json", **options)
        report = exp1.evaluate_checkpoint(self.root, "artifacts/m01-ok.ckpt", purpose="fixture", **options)
        ident = report["identity"]
        self.assertEqual((report["regime"], ident["regime"], ident["purpose"], ident["primary"]),
                         (LABEL_FREE, LABEL_FREE, "fixture", False))
        self.assertEqual(ident["preprocess"], preprocess.identity(LABEL_FREE))
        self.assertEqual(ident["checkpoint"]["train_preprocess"], preprocess.identity(WITH_LABELS))
        self.assertEqual(ident["tokenizer"]["status"], "other")
        self.assertIsNotNone(ident["checkpoint"]["manifest_sha256"])
        self.assertIn("regime label-free", exp1.format_report(report))

    def test_real_v1_checkpoint_is_refused_for_a_primary_report(self) -> None:
        checkpoint = PROJECT / "artifacts/premonition-step1-4M-1789770088141917828-23843.ckpt"
        data_rel = "data/village/stream/cache/large-seed0-f78a540c1e8a"
        if not (checkpoint / "manifest.json").is_file() or not (PROJECT / data_rel / "train/COMPLETE.json").is_file():
            raise unittest.SkipTest("the step-1 v1 checkpoint or the large build is not in this checkout")
        with self.assertRaisesRegex(identity.CheckpointIncompatible, "retired"):
            exp1.evaluate_checkpoint(PROJECT, checkpoint, data_rel=data_rel, log=QUIET)

    def test_d_evaluation_records_identity_and_refuses_mismatches(self) -> None:
        tok = self.data.tokenizer
        detector = pdata.name_detector(self.budget, self.data.rel, log=QUIET)
        torch.manual_seed(0)
        model = PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=tok.vocab_size))
        trainer = MiniTrainer(model, mini_train_config(), "cpu", flop_budget=1.0)
        common = dict(contender="D", tokenizer={"path": self.data.tokenizer_info["path"], "sha256": tok.digest},
                      detector=detector.digest, data={"dir": self.data.rel, "tag": self.data.tag})
        save_mini_checkpoint(self.budget, "artifacts/m01-d.ckpt", trainer,
                             checkpoint_config(trainer, **common, preprocess_identity=preprocess.identity(LABEL_FREE)))
        save_mini_checkpoint(self.budget, "artifacts/m01-d-legacy.ckpt", trainer, checkpoint_config(trainer, **common))
        options = dict(replay=False, directories=["validation"], log=QUIET)
        with self.assertRaisesRegex(identity.CheckpointIncompatible, "legacy/unknown"):
            evaluate_d_checkpoint(self.budget, "artifacts/m01-d-legacy.ckpt", purpose="fixture", **options)
        with self.assertRaises(identity.CheckpointIncompatible):
            evaluate_d_checkpoint(self.budget, "artifacts/m01-d.ckpt", **options)            # primary needs v2
        report = evaluate_d_checkpoint(self.budget, "artifacts/m01-d.ckpt", purpose="fixture", **options)
        self.assertEqual(report["identity"]["regime"], LABEL_FREE)
        self.assertEqual(report["directories"]["validation"]["retrieval"]["preprocess"], preprocess.identity(LABEL_FREE))
        self.assertEqual(report["directories"]["validation"]["retrieval"]["predictions_with_unbound_entity"], 0)
        legacy = evaluate_d_checkpoint(self.budget, "artifacts/m01-d-legacy.ckpt", purpose="legacy", **options)
        self.assertFalse(legacy["identity"]["primary"])
        self.assertTrue((self.root / pdata.cache_relative(self.data.rel, "validation", tok, detector,
                                                          LABEL_FREE)).is_file())

    # ------------------------------------------------------------- verdict guards

    def report(self, contender: str, regime, purpose: str = "primary", primary: bool = True, digest=None) -> dict:
        ids = [f"q{i}" for i in range(20)]
        rows = [{"id": qid, "correct": bool(i % 2), "decision": True, "slices": ["overall", "near"]}
                for i, qid in enumerate(ids)]
        out = {"contender": contender, "wipe": None, "split": "validation", "items": {"validation": rows},
               "tokenizer": {"sha256": "t"}, "data": {"tag": "d"}}
        if regime is not None:
            pre = preprocess.identity(regime)
            if digest:
                pre = {**pre, "digest": digest}
            out["regime"] = regime
            out["identity"] = {"regime": regime, "purpose": purpose, "primary": primary, "preprocess": pre,
                               "problems": [] if primary else ["tokenizer: not v2"]}
        return out

    def test_verdicts_refuse_mixed_unknown_and_non_primary_reports(self) -> None:
        ok = [self.report("A", LABEL_FREE), self.report("D", LABEL_FREE)]
        decision = exp1.verdict(ok)
        self.assertEqual(decision["verdict"], "INSUFFICIENT")
        self.assertFalse(decision["full_verdict"])
        self.assertIn("NOT a full §9/§10 verdict", decision["scope"])
        cases = {
            "mixed input regimes": [self.report("A", LABEL_FREE), self.report("D", WITH_LABELS, "diagnostic", False)],
            "legacy/unknown": [self.report("A", LABEL_FREE), self.report("D", None)],
            "never enter a verdict": [self.report("A", WITH_LABELS, "diagnostic", False),
                                      self.report("D", WITH_LABELS, "diagnostic", False)],
            "gold-evidence reports": [self.report("A", preprocess.GOLD_EVIDENCE, "diagnostic", False)],
            "not a primary report": [self.report("A", LABEL_FREE), self.report("D", LABEL_FREE, "legacy", False)],
            "not today's": [self.report("A", LABEL_FREE), self.report("D", LABEL_FREE, digest="0" * 64)],
            "fixture reports cannot share": [self.report("A", LABEL_FREE, "fixture", False),
                                             self.report("D", LABEL_FREE)],
        }
        for reason, reports in cases.items():
            with self.assertRaisesRegex(exp1.VerdictRefused, reason, msg=reason):
                exp1.verdict(reports, allow_fixture=reason.startswith("fixture"))
        with self.assertRaisesRegex(exp1.VerdictRefused, "not a primary"):
            exp1.verdict([self.report("A", LABEL_FREE, "fixture", False), self.report("D", LABEL_FREE, "fixture",
                                                                                         False)])
        mechanics = exp1.verdict([self.report("A", LABEL_FREE, "fixture", False),
                                  self.report("D", LABEL_FREE, "fixture", False)], allow_fixture=True)
        self.assertTrue(mechanics["fixture"])
        self.assertEqual(identity.report_regime({"contender": "A"}), preprocess.LEGACY)


if __name__ == "__main__":
    unittest.main()
