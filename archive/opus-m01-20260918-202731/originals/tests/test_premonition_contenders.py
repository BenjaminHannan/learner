"""Experiment 1's Core contenders: C's plain lookup, E's pointerized inputs, FLOP-budgeted training and
evaluation of A, B12, B28, C and E (design/06 §4, §5, §7 test 9, §8 step 7, §9). CPU, tiny models.

The shared fixture is a real-village step-1 build (40 train and 24 held-out visits, a small syllable-splitting
tokenizer), so visits are longer than A's 736-token cut and far questions exist.
"""
from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path
import random
import tempfile
import unittest

import torch
from torch import nn

from learnlab import step1
from learnlab.core import Core, CoreConfig
from learnlab.leaks import normalize
from learnlab.step1 import ANSWER_TAG, FEEDBACK_TAG, QUESTION_TAG
from learnlab.train import TrainConfig, Trainer
from memorylab.storage import Budget
from premonition import contenders, exp1, flops, lookup, slices
from premonition import data as pdata
from premonition.batch import N_ENT, NameTable
from premonition.pointer import Binder, detokenise, pointerize, restored

QUIET = lambda _message: None  # noqa: E731


def village_writer(split, visits, out_dir, workers, *, seed=0):
    """The real village, small shards, no counterfactual pairs and no oracle index (fast)."""
    try:
        from learnlab.village.shards import write_shards
    except ImportError as error:
        raise unittest.SkipTest(f"village simulator not available: {error}")
    return write_shards(split, visits, out_dir, 1, seed=seed, visits_per_shard=16, verbose=False)


village_writer.version = "contenders-test-1"

_FIXTURE: dict = {}


def fixture():
    """(workspace root, budget, StepData, validation questions), built once for the whole module."""
    if not _FIXTURE:
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        budget = Budget(root, hard=10_000_000_000, steady=8_000_000_000)
        data = step1.build_data(budget, visits=40, seed=0, workers=1, writer=village_writer, vocab_size=1200,
                                log=QUIET)
        questions = [q for text, meta in step1.shard_files(data.split_dir("validation"))
                     for q in step1.read_questions(text, meta, "validation")]
        _FIXTURE.update(tmp=tmp, root=root, budget=budget, data=data, questions=questions)
    return _FIXTURE["root"], _FIXTURE["budget"], _FIXTURE["data"], _FIXTURE["questions"]


def tearDownModule() -> None:
    if _FIXTURE:
        _FIXTURE["tmp"].cleanup()
        _FIXTURE.clear()


def train_bm25(data):
    return lookup.fit_bm25(lookup.split_lines(data.split_dir("train")))


class Bm25Test(unittest.TestCase):
    def test_terms_and_query(self) -> None:
        self.assertEqual(lookup.terms("[world] The red cup is in Kelo's box."),
                         ("the", "red", "cup", "is", "in", "kelo", "s", "box"))
        self.assertEqual(lookup.query_terms("Where is the red cup?"), ("red", "cup"))
        # A name is kept even when it spells a stopword; a sentence-initial capital is not a name.
        self.assertEqual(lookup.query_terms("Quiz time! Where did Will go?"), ("quiz", "time", "will", "go"))
        self.assertEqual(lookup.label_free("[question] Where is Kelo? [answer] the mill [feedback] Right."),
                         "[question] Where is Kelo?")
        self.assertEqual(lookup.label_free("[world] Kelo is here."), "[world] Kelo is here.")

    def test_scores_ties_and_budget(self) -> None:
        bm25 = lookup.fit_bm25(["[world] kelo went to the mill.", "[world] rami went to the barn.",
                                "[world] the mill is old.", "[question] where? [answer] x"])
        self.assertEqual(bm25.lines, 3)
        self.assertAlmostEqual(bm25.idf("kelo"), math.log(1 + (3 - 1 + 0.5) / 1.5))
        self.assertAlmostEqual(bm25.idf("unseen"), math.log(1 + 3.5 / 0.5))
        again = lookup.Bm25.from_dict(json.loads(json.dumps(bm25.to_dict())))
        self.assertEqual(again.digest, bm25.digest)
        with self.assertRaises(ValueError):
            lookup.Bm25.from_dict({**bm25.to_dict(), "lines": 4})
        candidates = [(0, "[world] Kelo went to the mill."), (1, "[world] Rami went to the barn."),
                      (2, "[world] Kelo went to the pond."), (3, "[world] Sali went to the barn.")]
        found = lookup.recall(bm25, "Where did Kelo go?", candidates, lambda text: 10)
        self.assertEqual(found.ranked, (2, 0))           # equal scores: the newer line first
        self.assertEqual(found.lines, (0, 2))            # then chronological
        none = lookup.recall(bm25, "What is blue?", candidates, lambda text: 10)
        self.assertEqual(none.lines, ())                 # nothing scores above zero
        crowded = [(i, f"[world] Kelo went to spot {i}.") for i in range(20)]
        top = lookup.recall(bm25, "Where is Kelo?", crowded, lambda text: 10)
        self.assertEqual(len(top.lines), lookup.TOP_K)
        self.assertEqual(top.ranked, tuple(range(19, 11, -1)))
        tight = lookup.recall(bm25, "Where is Kelo?", crowded, lambda text: 50)
        self.assertEqual(tight.ranked, (19, 18, 17))     # 3 x 50 <= 192 < 4 x 50: the fourth ends it
        self.assertEqual(tight.tokens, 150)
        self.assertEqual(tight.top, top.ranked)

    def test_recall_report(self) -> None:
        def entry(evidence, ranked):
            found = lookup.Recall(lines=tuple(sorted(ranked)), ranked=tuple(ranked), top=tuple(ranked), tokens=0,
                                  candidates=10)
            return lookup.LookupInput(ids=[], recall=found, a_start=50, window=None, masked=0,
                                      evidence_before=tuple(evidence))

        report = lookup.recall_report([entry([3, 7], [7, 1]), entry([4], [4]), entry([], [2])])
        self.assertEqual(report["targets"], 3)
        self.assertAlmostEqual(report["recall_at_8"], 2 / 3)
        self.assertEqual(report["with_targets"], 2)
        self.assertAlmostEqual(report["all_gold_recalled"], 0.5)


class LookupInputTest(unittest.TestCase):
    """design/06 §7 test 9 on real village visits."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root, cls.budget, cls.data, cls.questions = fixture()
        cls.tokenizer = cls.data.tokenizer
        cls.bm25 = train_bm25(cls.data)
        cls.ids = {name: cls.tokenizer.token_to_id(name)
                   for name in ("<eos>", "<bos>", "<pad>", ANSWER_TAG, FEEDBACK_TAG, QUESTION_TAG)}

    def test_bos_is_free_and_visits_exceed_a_s_cut(self) -> None:
        for text, _ in step1.shard_files(self.data.split_dir("train")):
            self.assertNotIn(lookup.SEPARATOR, text.read_text(encoding="utf-8"))
        seen = {"templates": set(), "styles": set(), "rule_families": set()}
        items = slices.canonical_items(self.tokenizer, self.questions, seen=seen)
        self.assertGreater(sum(item.evidence_kept is False for item in items), 10)    # far questions exist

    def test_a_s_window_is_build_items(self) -> None:
        seen = {"templates": set(), "styles": set(), "rule_families": set()}
        items = step1.build_items(self.tokenizer, self.questions, max_len=slices.CUT_MAX_LEN, seen=seen)
        lines = lookup.LineIds(self.tokenizer, labels=True)
        for item in items:
            ids, window = lookup.plain_input(item.question, lines)
            self.assertEqual(ids, item.prompt)
            self.assertEqual(window.start, slices.window_start(item))
            entry = lookup.lookup_input(item.question, lines, self.bm25)
            self.assertEqual(entry.a_start, slices.window_start(item))

    def check_inputs(self, max_len: int, labels: bool) -> int:
        lines = lookup.LineIds(self.tokenizer, labels=labels)
        recalled = 0
        for q in self.questions:
            entry = lookup.lookup_input(q, lines, self.bm25, max_len=max_len)
            ids = entry.ids
            # Prompt shape: <eos>, recalled lines, <bos>, window, the question up to [answer].
            self.assertLessEqual(len(ids), max_len)
            self.assertLessEqual(len(ids), slices.SEQ_LEN)
            self.assertEqual(ids[-1], self.ids[ANSWER_TAG])
            tail = self.tokenizer.encode(q.prompt_line)
            self.assertEqual(ids[-len(tail):], tail)
            self.assertEqual(ids[0], self.ids["<eos>"])
            self.assertEqual(ids.count(self.ids["<bos>"]), 1)
            block = 1 + sum(len(lines(dict(q.context)[n])) for n in entry.recall.lines)
            self.assertEqual(ids[block], self.ids["<bos>"])
            self.assertEqual(entry.masked, block + 1 + int(entry.window.prefix))
            # BM25 never recalls the window or anything later, nor a question line.
            context = dict(q.context)
            for number in entry.recall.lines:
                self.assertLess(number, entry.a_start)
                self.assertIn(number, context)
                self.assertFalse(context[number].startswith(QUESTION_TAG))
            self.assertLessEqual(entry.a_start, entry.window.start)        # C's window is inside A's
            self.assertEqual(list(entry.recall.lines), sorted(entry.recall.lines))
            self.assertLessEqual(len(entry.recall.lines), lookup.TOP_K)
            self.assertLessEqual(entry.recall.tokens, lookup.RECALL_TOKENS)
            if not labels:
                self.assertEqual(ids.count(self.ids[ANSWER_TAG]), 1)       # only the question's own [answer]
                self.assertNotIn(self.ids[FEEDBACK_TAG], ids)
            recalled += bool(entry.recall.lines)
        return recalled

    def test_prompts_fit_end_with_answer_and_never_recall_the_window(self) -> None:
        self.assertGreater(self.check_inputs(slices.CUT_MAX_LEN, labels=True), 10)
        self.assertGreater(self.check_inputs(slices.CUT_MAX_LEN, labels=False), 10)
        self.assertGreater(self.check_inputs(240, labels=True), 50)       # a short window: many candidates

    def test_a_planted_perfect_match_in_the_window_or_later_is_never_recalled(self) -> None:
        lines = lookup.LineIds(self.tokenizer)
        q = next(q for q in self.questions
                 if lookup.lookup_input(q, lines, self.bm25).a_start > q.context[0][0] + 5)
        question = replace(q, raw_line="[question] Where is Zyzzq? [answer] x [feedback] y", question="Where is Zyzzq?")
        a_start = lookup.lookup_input(question, lines, self.bm25).a_start
        bait = "[world] Zyzzq."          # shorter than any line it replaces, so A's window only grows
        planted = tuple((n, bait if n >= a_start else line) for n, line in q.context)
        entry = lookup.lookup_input(replace(question, context=planted), lines, self.bm25)
        self.assertLessEqual(entry.a_start, a_start)
        self.assertEqual(entry.recall.lines, ())
        early = next(n for n, line in q.context if n < entry.a_start and not line.startswith(QUESTION_TAG))
        planted = tuple((n, bait if n == early else line) for n, line in planted)
        entry = lookup.lookup_input(replace(question, context=planted), lines, self.bm25)
        self.assertEqual(entry.recall.lines, (early,))

    def test_question_rows_are_exact_masked_and_aligned(self) -> None:
        text, meta = step1.shard_files(self.data.split_dir("train"))[0]
        rows = lookup.shard_rows(text, meta, self.tokenizer, self.bm25, seed="t")
        questions = {q.id: q for q in step1.read_questions(text, meta, "train")}
        self.assertEqual(rows.tokens.shape, (len(questions), slices.SEQ_LEN))
        self.assertGreater(rows.stats["with_recall"], 0)
        eos, bos, pad, answer = (self.ids[k] for k in ("<eos>", "<bos>", "<pad>", ANSWER_TAG))
        for ids, mask in zip(rows.tokens.tolist(), rows.mask.tolist()):
            self.assertEqual(ids[0], eos)
            self.assertFalse(mask[0])
            cut = ids.index(bos)
            self.assertFalse(any(mask[: cut + 1]))                      # recalled block and <bos> are never targets
            first = mask.index(True)
            self.assertIn(first - cut, (1, 2))                          # the window starts right after (<eos>)
            if first - cut == 2:
                self.assertEqual(ids[cut + 1], eos)
            where = ids.index(answer, first)
            self.assertTrue(all(mask[first:where + 2]))                 # window, question and the answer's start
            self.assertTrue(all(not m for i, m in zip(ids, mask) if i == pad))
        # Trainer._next_batch: every input row is one stream row, and its last target is the next row's <eos>.
        stream = lookup.LookupStream(self.data, self.bm25, seed=1)
        trainer = Trainer(Core(CoreConfig(self.tokenizer.vocab_size, slices.SEQ_LEN, 32, 2, 2)),
                          TrainConfig(batch=3, seq_len=slices.SEQ_LEN))
        mirror = lookup.LookupStream(self.data, self.bm25, seed=1)
        for _ in range(3):
            inputs, targets, target_mask = trainer._next_batch(stream)
            for row in range(3):
                tokens, mask = next(mirror)
                self.assertEqual(inputs[row].tolist(), tokens.tolist())
                self.assertEqual(targets[row, :-1].tolist(), tokens[1:].tolist())
                self.assertEqual(target_mask[row, :-1].tolist(), mask[1:].tolist())
                self.assertEqual(int(targets[row, -1]), eos)
                self.assertFalse(bool(target_mask[row, -1]))
        summary = stream.summary()
        self.assertEqual(summary["plain_rows"] + summary["question_rows"], 10)   # 9 rows + the carried one
        self.assertLessEqual(abs(summary["plain_rows"] - summary["question_rows"]), 1)

    def test_spawned_workers_build_the_same_stream(self) -> None:
        pooled = lookup.LookupStream(self.data, self.bm25, seed=2, workers=1)
        try:
            rows = [next(pooled) for _ in range(12)]
        finally:
            pooled.close()
        local = lookup.LookupStream(self.data, self.bm25, seed=2)
        for tokens, mask in rows:
            again = next(local)
            self.assertTrue(torch.equal(tokens, again[0]))
            self.assertTrue(torch.equal(mask, again[1]))

    def test_worker_rows_match_in_process_rows(self) -> None:
        text, meta = step1.shard_files(self.data.split_dir("train"))[1]
        lookup._init_rows(self.tokenizer.to_json(), self.bm25.to_dict())
        tokens, mask, stats, count = lookup._rows_task((str(text), str(meta), "s", slices.SEQ_LEN,
                                                        slices.CUT_MAX_LEN))
        rows = lookup.shard_rows(text, meta, self.tokenizer, self.bm25, seed="s")
        rebuilt = torch.frombuffer(bytearray(tokens), dtype=torch.int16).long().reshape(count, -1)
        self.assertTrue(torch.equal(rebuilt, rows.tokens))
        self.assertEqual(bytes(rows.mask.reshape(-1).tolist()), mask)
        self.assertEqual(stats, dict(rows.stats))


class PointerInputTest(unittest.TestCase):
    """E: names round-trip exactly and the answer never reaches the input or the name table."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root, cls.budget, cls.data, cls.questions = fixture()
        cls.tokenizer = cls.data.tokenizer
        cls.detector = pdata.name_detector(cls.budget, cls.data.rel, log=QUIET)

    def test_names_round_trip_and_answers_never_leak(self) -> None:
        tokenizer, detector = self.tokenizer, self.detector
        base, answer_id = tokenizer.vocab_size, tokenizer.token_to_id(ANSWER_TAG)
        cache: dict = {}
        named = 0
        for labels in (False, True):
            for q in self.questions:
                entry = contenders.pointer_input(q, tokenizer, detector, labels=labels, cache=cache)
                ids = entry.ids
                self.assertLessEqual(len(ids), slices.CUT_MAX_LEN)
                self.assertEqual(ids[-1], answer_id)
                self.assertTrue(all(0 <= i < base + N_ENT for i in ids))
                if not labels:
                    self.assertEqual(ids.count(answer_id), 1)
                    self.assertNotIn(tokenizer.token_to_id(FEEDBACK_TAG), ids)
                # The table holds exactly the names of what the input is built from: the answer is never bound.
                shown = [lookup.shown(line, labels) for _, line in q.context] + [q.prompt_line]
                self.assertEqual(list(entry.table.spellings.values()), detector.names("\n".join(shown)))
                self.assertEqual(sorted(entry.table.spellings), list(range(len(entry.table.spellings))))
                # The input decodes to the visible text with every name spelled exactly.
                kept = [lookup.shown(line, labels) + "\n" for n, line in q.context if n >= entry.window.start]
                text = ("<eos>" if entry.window.prefix else "") + "".join(kept) + q.prompt_line
                self.assertEqual(detokenise(ids, entry.table, tokenizer), restored(text, tokenizer, detector))
                if not labels:
                    continue
                # A name answer decodes from its entity id to the exact spelling.
                binder = Binder()
                for e in sorted(entry.table.spellings):
                    binder.bind(entry.table.spellings[e])
                answer = pointerize(" " + q.answer + "\n", tokenizer, detector, binder=binder)[0]
                if len(binder.table.spellings) != len(entry.table.spellings):
                    continue                                     # the answer names someone the input never did
                prediction = contenders.entity_answer(answer, entry.table, tokenizer)
                self.assertTrue(step1.exact_match(prediction, q.answer), (prediction, q.answer))
                for name in detector.names(q.answer):
                    named += 1
                    self.assertIn(name, prediction)              # exact capitalised spelling, not lowercased
        self.assertGreater(named, 10)

    def test_unbound_entities_never_match(self) -> None:
        table = NameTable({0: "Kelo"})
        base = self.tokenizer.vocab_size
        newline = self.tokenizer.encode("\n")
        self.assertEqual(contenders.entity_answer([base, *newline], table, self.tokenizer), "Kelo")
        self.assertEqual(contenders.entity_answer([base + 5, *newline], table, self.tokenizer), "<ent5>")

    def test_pointer_stream_renumbers_each_visit(self) -> None:
        cache = pdata.load_or_build(self.budget, self.data.rel, "train", self.tokenizer, self.detector, split="train",
                                    log=QUIET)
        base, eos = self.tokenizer.vocab_size, self.tokenizer.token_to_id("<eos>")
        first = [next(contenders.PointerStream(cache, eos, seed=s)) for s in (0, 1)]
        stream = contenders.PointerStream(cache, eos, seed=0)
        visits = [next(stream) for _ in range(len(cache))]
        self.assertEqual(stream.summary()["epochs"], 1.0)
        self.assertTrue(torch.equal(visits[0], first[0]))
        lengths = sorted(v.numel() - 1 for v in visits)
        self.assertEqual(lengths, sorted(cache.lengths.tolist()))
        for v in visits:
            self.assertEqual(int(v[-1]), eos)
            self.assertTrue(bool((v < base + N_ENT).all()))
        orders = {tuple(dict.fromkeys(int(i) - base for i in v if i >= base)) for v in visits}
        self.assertGreater(len(orders), 1)          # not all identity: entity order is shuffled per visit
        self.assertNotEqual({tuple(int(i) - base for i in v if i >= base)[:1] for v in visits}, {(0,)})

    def test_pointer_scorer_copies_the_exact_spelling(self) -> None:
        tokenizer = self.tokenizer
        base, newline = tokenizer.vocab_size, tokenizer.encode("\n")[0]

        class FirstEntity(nn.Module):
            """Says ENT0 after the prompt, then a newline."""

            def __init__(self) -> None:
                super().__init__()
                self.weight = nn.Parameter(torch.zeros(1))

            def forward(self, tokens: torch.Tensor) -> torch.Tensor:
                logits = torch.zeros(*tokens.shape, base + N_ENT)
                logits[..., base] = 1.0
                logits[..., newline] += 2.0 * (tokens == base).float()
                return logits

        seen = {"templates": set(), "styles": set(), "rule_families": set()}
        items = slices.canonical_items(tokenizer, self.questions[:40], seen=seen)
        scorer = contenders.ContenderScorer("pointer", detector=self.detector)
        rows = exp1.score_read_only(FirstEntity(), tokenizer, items, max_new=4, scorer=scorer)
        self.assertEqual(len(rows), len(items))
        plain = step1.score_items(Core(CoreConfig(base, 768, 32, 2, 2)), tokenizer, items[:2], max_new=2,
                                  batch_size=2)
        self.assertEqual(set(rows[0]), set(plain[0]))        # the same result keys as step 1's scorer
        for item, row in zip(items, rows):
            table = contenders.pointer_input(item.question, tokenizer, self.detector).table
            self.assertEqual(row["prediction"], table.spellings[0])
        self.assertEqual(scorer.calls[-1]["predictions_with_entity"], len(items))
        self.assertEqual(scorer.calls[-1]["predictions_with_unbound_entity"], 0)


class BudgetTest(unittest.TestCase):
    def test_step_flops_are_counted_and_linear(self) -> None:
        config = CoreConfig(300, 64, 32, 2, 2)
        torch.manual_seed(0)
        state = torch.get_rng_state()
        one = contenders.step_flops(config, 1, 64)
        self.assertTrue(torch.equal(torch.get_rng_state(), state))       # measuring never touches the RNG
        self.assertEqual(contenders.step_flops(config, 3, 64), 3 * one)
        self.assertEqual(flops.measure_core(Core(config), torch.zeros(3, 65, dtype=torch.long)), 3 * one)
        hand = flops.core_flops_per_token(config, 64)
        self.assertLess(abs(one / 64 / hand - 1), 0.10)

    def test_plans(self) -> None:
        plan = contenders.plan_budget(1000, 10, flops_budget=10_300)
        self.assertEqual((plan.steps, plan.flops, plan.tokens), (10, 10_000, 100))
        self.assertLess(abs(plan.error(plan.steps)), 0.05)
        self.assertEqual(contenders.plan_budget(1000, 10, flops_budget=1030).steps, 1)
        with self.assertRaises(contenders.BudgetError):
            contenders.plan_budget(1000, 10, flops_budget=600)             # 1 step is +67%, 0 steps is -100%
        with self.assertRaises(ValueError):
            contenders.plan_budget(1000, 10)
        self.assertEqual(contenders.plan_budget(1000, 10, tokens_budget=96).steps, 10)

    def test_real_contender_shapes(self) -> None:
        counts = {name: Core(contenders.core_config(name, 6372)).num_parameters() for name in ("A", "E", "B12")}
        self.assertEqual(counts["A"], 4_987_392)                  # design/06 §0 (v1 vocabulary)
        self.assertEqual(counts["E"], 4_991_488)
        self.assertAlmostEqual(counts["B12"] / 1e6, 13.4, delta=0.05)
        b28 = contenders.core_config("B28", 6372)
        self.assertEqual((b28.d_model, b28.n_layers, b28.n_heads), (512, 8, 8))
        self.assertEqual(contenders.core_config("C", 7068), contenders.core_config("A", 7068))
        self.assertEqual(contenders.core_config("E", 7068).vocab_size, 7068 + N_ENT)
        with self.assertRaises(ValueError):
            contenders.core_config("D", 7068)


class MiniRunTest(unittest.TestCase):
    """Every contender trains to a FLOP budget on tiny data and its checkpoint scores through exp1."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root, cls.budget, cls.data, cls.questions = fixture()
        cls.reports = {}
        cls.evals = {}
        per_step = None
        for name in ("A", "B12", "B28", "C", "E"):
            config = contenders.core_config(name, cls.data.tokenizer.vocab_size, size="tiny")
            per_step = contenders.step_flops(config, 2, slices.SEQ_LEN)
            cls.reports[name] = contenders.train_contender(
                cls.budget, cls.data, name, flops_budget=6.2 * per_step, batch=2, size="tiny", log_every=2, log=QUIET)
            cls.evals[name] = contenders.evaluate_contender(
                cls.root, cls.reports[name]["checkpoint"], replay=False, max_new=8, batch_size=64,
                heldin=12 if name == "E" else 0, log=QUIET)

    def test_budget_stop_lands_within_tolerance(self) -> None:
        for name, report in self.reports.items():
            info = report["flops"]
            self.assertEqual(report["status"], "completed", name)
            self.assertEqual(report["train"]["steps"], 6)
            self.assertTrue(info["within_tolerance"])
            self.assertLessEqual(abs(info["achieved"] / info["target"] - 1), 0.05)
            self.assertEqual(info["achieved"], 6 * info["per_step"])
            self.assertEqual(report["train"]["tokens"], 6 * 2 * slices.SEQ_LEN)
            self.assertTrue(report["history"] and "flops" in report["history"][-1])
            saved = json.loads((self.root / report["artifact"]).read_text(encoding="utf-8"))
            self.assertEqual(saved["flops"]["achieved"], info["achieved"])
            budget = contenders.budget_from_report(self.root / report["artifact"])
            self.assertEqual(budget["flops"], info["achieved"])
        c = self.reports["C"]["stream"]
        self.assertEqual(c["kind"], "lookup")
        self.assertGreaterEqual(c["question_rows"], 6)
        self.assertEqual(self.reports["E"]["config"]["core"]["vocab_size"], self.data.tokenizer.vocab_size + N_ENT)

    def test_token_budget_and_step1_reports(self) -> None:
        report = contenders.train_contender(self.budget, self.data, "A", tokens_budget=3 * 2 * slices.SEQ_LEN,
                                            batch=2, size="tiny", save=False, log=QUIET)
        self.assertEqual(report["train"]["steps"], 3)
        self.assertEqual(report["flops"]["budget_kind"], "tokens")
        config = contenders.core_config("A", self.data.tokenizer.vocab_size, size="tiny")
        step1_report = {"command": "step1", "artifact": "x.json",
                        "config": {"core": {"vocab_size": config.vocab_size, "context": 768, "d_model": 32,
                                            "n_layers": 2, "n_heads": 2, "mlp_ratio": 4},
                                   "train": {"batch": 4, "seq_len": 768}, "tokenizer": {"sha256": "abc"}},
                        "train": {"steps": 7, "tokens": 7 * 4 * 768}}
        budget = contenders.budget_from_report(step1_report)
        self.assertEqual(budget["flops"], 7 * contenders.step_flops(config, 4, 768))
        self.assertEqual(budget["tokens"], 7 * 4 * 768)

    def test_every_checkpoint_scores_through_exp1(self) -> None:
        count = len(self.questions)
        for name, report in self.evals.items():
            self.assertEqual(report["contender"], name)
            items = report["items"]["validation"]
            self.assertEqual([r["id"] for r in items], [q.id for q in self.questions])
            self.assertEqual(report["directories"]["validation"]["summary"]["items"], count)
            self.assertEqual(report["inputs"]["labels"], False)
            json.dumps(report)
            self.assertIn("overall: ", exp1.format_report(report))
            inputs = report["inputs"]["per_directory"]["validation"]
            self.assertLessEqual(inputs["max_tokens"], slices.CUT_MAX_LEN)
        recall = self.evals["C"]["inputs"]["per_directory"]["validation"]["recall"]
        self.assertGreater(recall["targets"], 0)
        self.assertIsNotNone(recall["recall_at_8"])
        self.assertIn(exp1.HELDIN_SOURCE, self.evals["E"]["directories"])
        verdict = exp1.verdict(list(self.evals.values()))
        self.assertEqual(verdict["contenders"], ["A", "B12", "B28", "C", "E"])
        self.assertEqual(verdict["verdict"], "INSUFFICIENT")                  # no D, and too few items

    def test_contender_override_must_share_inputs(self) -> None:
        with self.assertRaises(ValueError):
            contenders.evaluate_contender(self.root, self.reports["E"]["checkpoint"], contender_name="A",
                                          replay=False, log=QUIET)
        report = contenders.evaluate_contender(self.root, self.reports["A"]["checkpoint"], contender_name="B28",
                                               directories=["validation"], replay=False, max_new=4, log=QUIET)
        self.assertEqual(report["contender"], "B28")

    def test_with_labels_matches_exp1_for_plain_contenders(self) -> None:
        ours = contenders.evaluate_contender(self.root, self.reports["A"]["checkpoint"], replay=False, max_new=8,
                                             labels=True, log=QUIET)
        theirs = exp1.evaluate_checkpoint(self.root, self.reports["A"]["checkpoint"], replay=False, max_new=8,
                                          log=QUIET)
        self.assertEqual(ours["items"], theirs["items"])


if __name__ == "__main__":
    unittest.main()
