"""The Stage 1 run script (scripts/span_stage1.py): the log protocol, the branch from P_s (both arms restore the
parent exactly; SPAN's optimizer state is matched by name), the parent's stop at the end of the gold phase and the
arms' stream position, the heavy-batch selection of the memory pre-flight, and the go-file gate. CPU, tiny."""
from __future__ import annotations

import io
import contextlib
import copy
import itertools
import json
import os
import tempfile
import types
import unittest
from pathlib import Path

import torch

from learnlab import ckpt
from premonition import data as pdata, span_cards
from premonition.model import PremonitionMini
from premonition.train import MiniTrainer, Plan, budget_for_steps, planned_loops
from scripts import span_stage1 as s1
from tests.test_premonition_model import synthetic_batch, tiny_config
from tests.test_premonition_span_cards import span_config

GOLD = Plan("gold", "gold", 0.0)


def parent_of(steps: int = 2):
    """A tiny LINE parent after `steps` gold steps, as run_seed snapshots it."""
    torch.manual_seed(0)
    model = PremonitionMini(tiny_config())
    trainer = MiniTrainer(model, s1.train_config(), "cpu", flop_budget=1.0, seed=0)
    batches = [synthetic_batch(seed=s) for s in range(4)]
    trainer.calibrate(batches[:2])
    trainer.flop_budget = budget_for_steps(trainer, batches, 400)
    for batch in batches[:steps]:
        trainer._train_step(batch, GOLD, planned_loops(batch, "gold", model.config), False)
    parent = {"model": copy.deepcopy(model.state_dict()), "optimizer": copy.deepcopy(trainer.optimizer.state_dict()),
              "trainer": copy.deepcopy(trainer.state_dict()), "rng": ckpt.rng_state(),
              "names": s1.optimizer_names(model, trainer.optimizer), "consumed": steps}
    return trainer, parent, batches


def arm(parent: dict, kind: str, budget: float):
    torch.manual_seed(5)                                   # a different global seed: restore must override it
    if kind == "LINE":
        model = PremonitionMini(tiny_config())
        model.load_state_dict(parent["model"])
        trainer = MiniTrainer(model, s1.train_config(), "cpu", flop_budget=budget, seed=0)
    else:
        model = span_cards.build_model(tiny_config(), span_config())
        source = PremonitionMini(tiny_config())
        source.load_state_dict(parent["model"])
        missing, unexpected = s1.span_stage0.load_from_line(model, source)          # the load run_seed uses
        assert set(missing) == s1.span_stage0.GATE_KEYS and not unexpected
        trainer = span_cards.SpanTrainer(model, s1.train_config(), "cpu", flop_budget=budget, seed=0)
    s1.restore(trainer, parent)
    return trainer


class LogProtocolTest(unittest.TestCase):
    def test_records_round_trip_in_short_lines(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            s1.emit("big", {"x": "y" * 2000, "inf": float("inf")})
            s1.emit("small", {"z": 1})
        lines = out.getvalue().splitlines()
        self.assertTrue(all(len(line) <= 500 for line in lines))
        records = s1.decode(lines)
        self.assertEqual([k for k, _ in records], ["big", "small"])
        self.assertEqual(records[0][1]["x"], "y" * 2000)
        self.assertEqual(records[0][1]["inf"], "inf")                     # strict JSON
        self.assertEqual(s1.decode(lines[1:]), [records[1]])               # an incomplete record is skipped

    def test_bits_round_trip(self) -> None:
        values = [bool(i % 3 == 0) for i in range(1003)]
        self.assertEqual(s1.unbits(s1.bits(values), len(values)), values)


class BranchTest(unittest.TestCase):
    def test_the_line_arm_is_the_parent_continued(self) -> None:
        """Restoring P_s into a fresh trainer and continuing equals continuing the parent's own trainer."""
        trainer, parent, batches = parent_of()
        line = arm(parent, "LINE", trainer.flop_budget)
        self.assertEqual((line.step, line.flops), (trainer.step, trainer.flops))
        self.assertTrue(torch.equal(line.generator.get_state(), trainer.generator.get_state()))
        teacher = Plan("teacher", "teacher", 0.0)
        for batch in batches[2:4]:                                         # teacher steps draw from the generator
            loops = planned_loops(batch, "teacher", trainer.model.config)
            rng = ckpt.rng_state()
            a = trainer._train_step(batch, teacher, loops, False)
            ckpt.set_rng_state(rng)                                        # both steps start from one global state
            b = line._train_step(batch, teacher, loops, False)
            self.assertEqual(float(a["loss"]), float(b["loss"]))
        for (name, p), q in zip(trainer.model.named_parameters(), line.model.parameters()):
            self.assertTrue(torch.equal(p, q), name)

    def test_span_shares_every_update_but_the_gate(self) -> None:
        """One gold step of LINE and of SPAN from P_s on the same batch: SPAN's reader, pool and every shared weight
        get LINE's update (same gradients, same restored Adam moments); only the gate moves differently. (This
        early in warmup a swapped Adam state moves a weight by only ~1e-9, so the mapping itself is checked exactly
        by `test_restored_moments_are_the_parents_by_name`.)"""
        trainer, parent, batches = parent_of()
        line, span = arm(parent, "LINE", trainer.flop_budget), arm(parent, "SPAN", trainer.flop_budget)
        names = s1.optimizer_names(span.model, span.optimizer)
        gate = set(s1.span_stage0.GATE_KEYS)
        self.assertEqual(set(names) - set(s1.optimizer_names(line.model, line.optimizer)), gate)
        self.assertTrue(all(i not in span.optimizer.state_dict()["state"] for i, n in enumerate(names) if n in gate))
        batch = batches[2]
        loops = planned_loops(batch, "gold", line.model.config)
        line._train_step(batch, GOLD, loops, False)
        span._train_step(batch, GOLD, loops, False)
        shared = dict(line.model.named_parameters())
        before = dict(arm(parent, "LINE", 1.0).model.named_parameters())
        moved = 0
        for name, p in span.model.named_parameters():
            if name in gate:
                continue
            torch.testing.assert_close(p, shared[name], rtol=0, atol=1e-6, msg=name)
            moved += int(not torch.equal(p, before[name]))
        self.assertGreater(moved, 10)                                      # the step really updated weights

    @staticmethod
    def moments_by_name(trainer) -> dict:
        state = trainer.optimizer.state_dict()["state"]
        return {name: state[i] for i, name in enumerate(s1.optimizer_names(trainer.model, trainer.optimizer))
                if i in state}

    def test_restored_moments_are_the_parents_by_name(self) -> None:
        """The direct check of the mapping: every shared weight's Adam moments after restore are exactly P_s's for
        that name (a post-step weight comparison cannot see a swap this early: Adam's m/sqrt(v) is about +-1 either
        way). Two same-shaped states swapped is caught; a shape mismatch fails loudly at restore."""
        trainer, parent, _ = parent_of()
        old = {name: parent["optimizer"]["state"][i] for i, name in enumerate(parent["names"])
               if i in parent["optimizer"]["state"]}                       # weights with no gradient yet have none
        self.assertGreater(len(old), 20)
        for kind in ("LINE", "SPAN"):
            got = self.moments_by_name(arm(parent, kind, trainer.flop_budget))
            self.assertEqual(set(got), set(old))
            for name, entry in got.items():
                for key in ("exp_avg", "exp_avg_sq"):
                    self.assertTrue(torch.equal(entry[key], old[name][key]), (kind, name, key))
        shapes = dict(trainer.model.named_parameters())
        a, b = next((x, y) for x, y in itertools.combinations(list(old), 2)
                    if shapes[x].shape == shapes[y].shape and not torch.equal(old[x]["exp_avg"], old[y]["exp_avg"]))
        wrong = copy.deepcopy(parent)
        names = wrong["names"]
        i, j = names.index(a), names.index(b)
        names[i], names[j] = b, a
        got = self.moments_by_name(arm(wrong, "SPAN", trainer.flop_budget))
        self.assertFalse(torch.equal(got[a]["exp_avg"], old[a]["exp_avg"]))
        bad = copy.deepcopy(parent)
        bad["names"] = list(reversed(parent["names"]))
        with self.assertRaises(ValueError):
            arm(bad, "SPAN", trainer.flop_budget)

    def test_calibration_leaves_the_random_state_alone(self) -> None:
        trainer, parent, batches = parent_of()
        line = arm(parent, "LINE", trainer.flop_budget)
        generator, rng = line.generator.get_state(), ckpt.rng_state()
        s1.calibrate_keeping_rng(line, batches[:2])
        self.assertTrue(torch.equal(line.generator.get_state(), generator))
        self.assertTrue(torch.equal(ckpt.rng_state()["torch"], rng["torch"]))


class StreamTest(unittest.TestCase):
    def test_the_parent_trains_the_streams_first_batches_and_the_arms_resume_at_the_next(self) -> None:
        """Through the real `MiniTrainer.train` (head chained in front, as run_seed does): the parent trains exactly
        batches 0 .. step-1 of the stream, in order, then stops at the end of the gold phase; an arm's
        `stream_from(skip=step)` starts at batch `step`, the first one the parent did not train."""
        pool = [synthetic_batch(seed=s) for s in range(40)]
        index = {id(batch): i for i, batch in enumerate(pool)}             # which stream batch this is
        original = pdata.batches
        pdata.batches = lambda *a, **k: iter(pool)
        try:
            torch.manual_seed(0)
            model = PremonitionMini(tiny_config())
            trainer = MiniTrainer(model, s1.train_config(), "cpu", flop_budget=1.0, seed=0)
            stream = pdata.batches(None)
            head = [next(stream) for _ in range(s1.HEAD)]
            trainer.calibrate(head)
            trainer.flop_budget = budget_for_steps(trainer, pool, 120)   # gold phase: about 6 steps
            seen = []
            step = trainer._train_step
            trainer._train_step = lambda batch, *a: (seen.append(index[id(batch)]), step(batch, *a))[1]
            trainer.train(s1.gold_only(trainer, itertools.chain(head, stream)))
            self.assertGreater(trainer.step, s1.HEAD)
            self.assertEqual(seen, list(range(trainer.step)))
            self.assertEqual(trainer.plan().phase, "teacher")
            args = types.SimpleNamespace(max_tokens=0, max_visits=0)
            self.assertEqual(index[id(next(s1.stream_from(None, args, 0, trainer.step)))], trainer.step)
        finally:
            pdata.batches = original

    def test_stream_from_skips_exactly_the_consumed_batches(self) -> None:
        cache = types.SimpleNamespace()
        args = types.SimpleNamespace(max_tokens=10_000, max_visits=8)
        original = pdata.batches
        try:
            pdata.batches = lambda *a, **k: iter(range(100))
            self.assertEqual(next(s1.stream_from(cache, args, 0, 7)), 7)
        finally:
            pdata.batches = original


class GoTest(unittest.TestCase):
    def args(self, path: Path) -> types.SimpleNamespace:
        return types.SimpleNamespace(go_file=str(path), go_url=None, go_poll_seconds=0.01, go_wait_hours=0.0003,
                                     seed=1)

    def test_only_a_matching_go_file_releases(self) -> None:
        expected = {"script_sha256": "s", "train_cache_sha256": "t", "N": 11.1}
        fit = s1.LADDER[0]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "go.json"
            path.write_text(json.dumps({"go": True, "seeds": [1], **expected, "max_tokens": 55000,
                                        "max_visits": 48}))
            self.assertEqual(s1.wait_for_go(self.args(path), expected, fit)["max_tokens"], 55000)
            for wrong in ({"N": 11.2}, {"seeds": [0]}, {"go": None}):          # each with a valid rung
                path.write_text(json.dumps({"go": True, "seeds": [1], **expected, "max_tokens": 55000,
                                            "max_visits": 48, **wrong}))
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                    s1.wait_for_go(self.args(path), expected, fit)
            path.write_text(json.dumps({"go": True, "seeds": [1], **expected, "max_tokens": 10 ** 9,
                                        "max_visits": 48}))                 # off the ladder
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                s1.wait_for_go(self.args(path), expected, fit)
            for odd in ({"go": False, "seeds": None}, {"go": False, "seeds": 1}):   # seventh review: no TypeError
                path.write_text(json.dumps(odd))
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as stop:
                    s1.wait_for_go(self.args(path), expected, fit)
                self.assertIn("deadline", str(stop.exception))
            path.write_text(json.dumps({"go": False, "seeds": [1], "script_sha256": "old"}))   # stale: waited on
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as stop:
                s1.wait_for_go(self.args(path), expected, fit)
            self.assertIn("deadline", str(stop.exception))
            for stop_file in ({"go": False, "seeds": [1], "script_sha256": "s"}, {"go": False}):   # plain stop too
                path.write_text(json.dumps(stop_file))
                with self.assertRaises(SystemExit) as stop:
                    s1.wait_for_go(self.args(path), expected, fit)
                self.assertIn("says stop", str(stop.exception))


class PreflightTest(unittest.TestCase):
    def test_heaviest_batches_include_the_largest_by_each_measure(self) -> None:
        class Cache:
            lengths = torch.tensor([50, 400, 380, 90, 60, 300, 20, 410])
            line_counts = torch.tensor([5, 9, 40, 9, 9, 9, 2, 9])

            def questions_of(self, v):
                return list(range([1, 1, 1, 30, 1, 1, 1, 1][v]))

            def __len__(self):
                return 8
        cache = Cache()
        groups = s1.heaviest(cache, 800, 2, 0)
        self.assertLessEqual(len(groups), 9)
        all_groups = pdata.length_batches(cache.lengths.tolist(), 800, rng=__import__("random").Random(0),
                                          max_visits=2)
        padded = max(all_groups, key=lambda g: len(g) * max(cache.lengths[v] for v in g))
        self.assertIn(padded, groups)
        self.assertTrue(any(3 in g for g in groups))                       # the many-questions visit
        self.assertTrue(any(2 in g for g in groups))                       # the many-lines visit


    def test_adversarial_groups_respect_the_caps_and_gather_the_heaviest_visits(self) -> None:
        lengths = [100] * 20
        group = s1.packed(sorted(range(20), key=lambda v: -v), lengths, 450, 3)
        self.assertEqual(group, [19, 18, 17])                              # max_visits binds
        group = s1.packed(list(range(20)), [100, 500, 100, 100, 100] + [100] * 15, 450, 10)
        self.assertNotIn(1, group)                                         # a visit that breaks max_tokens is left out
        self.assertLessEqual(len(group) * max([100, 500][v == 1] for v in group), 450)


class HelperTest(unittest.TestCase):
    def test_to_cpu_keeps_types_metadata_and_detaches(self) -> None:
        """Seventh review, finding 7: a plain dict lost the state dict's `_metadata` (module versions)."""
        import collections
        model = PremonitionMini(tiny_config())
        state = model.state_dict()
        copied = s1.to_cpu(state)
        self.assertIsInstance(copied, collections.OrderedDict)
        self.assertEqual(copied._metadata, state._metadata)
        self.assertEqual(list(copied), list(state))
        key = next(iter(state))
        self.assertIsNot(copied[key], state[key])
        copied[key].add_(1.0)                                              # a copy, not an alias
        self.assertFalse(torch.equal(copied[key], state[key]))
        PremonitionMini(tiny_config()).load_state_dict(s1.to_cpu(state))
        Pair = collections.namedtuple("Pair", "a b")
        tree = {3: Pair(torch.ones(2), [torch.zeros(1), 1.5]), "lr": 1e-3}
        out = s1.to_cpu(tree)
        self.assertIsInstance(out[3], Pair)
        self.assertEqual(out["lr"], 1e-3)
        self.assertTrue(torch.equal(out[3].a, torch.ones(2)))

    def test_dev_eval_flags_an_unscored_question(self) -> None:
        """Seventh review, finding 1: an unscored question must make the record `aligned: false` (the run then ends
        failed), and the bits keep the cache's order with the ids digest."""
        model = PremonitionMini(tiny_config()).eval()
        batch = synthetic_batch(visits=2, lines=16, seed=3)
        ids = [f"q{i}" for i in range(batch.q_visit.shape[0])]
        batch.question_ids = ids
        args = types.SimpleNamespace(max_tokens=10_000, max_visits=8)
        original = pdata.batches
        pdata.batches = lambda *a, **k: iter([batch])
        try:
            full = s1.dev_eval(model, types.SimpleNamespace(question_ids=ids), None, None, [], args)
            short = s1.dev_eval(model, types.SimpleNamespace(question_ids=ids + ["never-scored"]), None, None, [],
                                args)
        finally:
            pdata.batches = original
        self.assertTrue(full["aligned"])
        self.assertEqual(full["scored"], len(ids))
        self.assertFalse(short["aligned"])
        self.assertEqual(short["questions"], len(ids) + 1)
        self.assertFalse(s1.unbits(short["correct_bits"], short["questions"])[-1])
        self.assertNotEqual(full["ids_sha256"], short["ids_sha256"])


class RungTest(unittest.TestCase):
    def test_a_go_rung_may_never_be_larger_than_the_fitted_one(self) -> None:
        self.assertTrue(s1.rung_allowed(s1.LADDER[1], s1.LADDER[1]))
        self.assertTrue(s1.rung_allowed(s1.LADDER[2], s1.LADDER[1]))      # smaller: fine
        self.assertFalse(s1.rung_allowed(s1.LADDER[0], s1.LADDER[1]))     # larger than measured: refused
        self.assertFalse(s1.rung_allowed((55_000, 47), s1.LADDER[0]))      # outside the ladder

    def run_preflight(self, outputs):
        """`preflight` with the child processes replaced by `outputs` (one (returncode, stdout) per call)."""
        calls = iter(outputs)
        original = s1.subprocess.run
        s1.subprocess.run = lambda *a, **k: types.SimpleNamespace(returncode=(o := next(calls))[0], stdout=o[1],
                                                                  stderr="trace")
        args = types.SimpleNamespace(seed=0, visits="tiny", size="tiny", workers=1)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                return s1.preflight(args)
        finally:
            s1.subprocess.run = original

    @staticmethod
    def child(arm, peak, oom=False):
        return 0, "PREFLIGHT " + json.dumps({"arm": arm, "oom": oom, "peak_reserved_gb": None if oom else peak})

    def test_an_oom_or_over_limit_arm_moves_down_the_ladder(self) -> None:
        out = self.run_preflight([self.child("LINE", 9.0), self.child("SPAN", 9.0, oom=True),
                                  self.child("LINE", 9.0), self.child("SPAN", 13.5), self.child("SPAN-stress", 14.5),
                                  self.child("LINE", 8.0), self.child("SPAN", 9.0), self.child("SPAN-stress", 9.5)])
        self.assertEqual(out["chosen"], {"max_tokens": s1.LADDER[2][0], "max_visits": s1.LADDER[2][1]})
        self.assertEqual([r["fits"] for r in out["rungs"]], [False, False, True])

    def test_a_child_fault_stops_instead_of_shrinking_the_batch(self) -> None:
        """Review finding 2: any child failure counted as 'does not fit', so a bug would quietly shrink the batch."""
        with self.assertRaises(SystemExit) as stop:
            self.run_preflight([self.child("LINE", 9.0), (1, "")])
        self.assertIn("other than memory", str(stop.exception))
        self.assertIsNone(self.run_preflight([self.child("LINE", 99.0)] * 4)["chosen"])   # nothing fits: no rung



class RobustnessTest(unittest.TestCase):
    def test_decode_skips_cut_and_garbled_lines(self) -> None:
        """Second review, finding 4: a cut line crashed the whole readout."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            s1.emit("a", {"x": 1})
            s1.emit("b", {"y": "z" * 1000})
            s1.emit("c", {"w": 2})
        lines = out.getvalue().splitlines()
        cut = [lines[0][:15], "S1 eval", "S1 eval 1/1", "S1 x a/b {}", "S1 bad 1/1 {not json"] + lines[1:]
        self.assertEqual([k for k, _ in s1.decode(cut)], ["b", "c"])
        b_lines = [line for line in lines if line.startswith("S1 b#")]
        mixed = [b_lines[0], "S1 b#2 2/2 " + b_lines[1].split(" ", 3)[3]]   # chunk 2 of a record with another total
        self.assertEqual(s1.decode(mixed), [])                             # fifth review: no spliced record
        with contextlib.redirect_stdout(io.StringIO()) as again:
            s1.emit("b", {"y": "q" * 1000})                                # another b record, same chunk count
        other = again.getvalue().splitlines()
        spliced = [b_lines[0]] + other[1:]                                 # eighth review: same kind and total
        self.assertEqual(s1.decode(spliced), [])                           # but another record: not joined

    def test_a_malformed_go_file_is_refused_and_waited_on(self) -> None:
        """Second review, finding 5: a go file without the rung (or not a dict) was accepted and then crashed."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "go.json"
            args = types.SimpleNamespace(go_file=str(path), go_url=None, go_poll_seconds=0.01, go_wait_hours=0.0002,
                                         seed=0)
            for bad in ({"go": True, "seeds": [0], "N": 1}, ["go"], {"go": True, "seeds": 0, "N": 1,
                                                                     "max_tokens": 1, "max_visits": 1}):
                path.write_text(json.dumps(bad))
                out = io.StringIO()
                with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as stop:
                    s1.wait_for_go(args, {"N": 1}, s1.LADDER[0])
                self.assertIn("deadline", str(stop.exception))
                self.assertIn("go_refused", out.getvalue())

    def test_library_oom_errors_count_as_memory(self) -> None:
        """Second review, finding 2: an out-of-memory raised as a plain RuntimeError stopped the box."""
        self.assertTrue(s1.is_oom(RuntimeError("CUDA error: out of memory")))
        self.assertTrue(s1.is_oom(RuntimeError("cuBLAS: CUBLAS_STATUS_ALLOC_FAILED when calling cublasCreate")))
        self.assertFalse(s1.is_oom(RuntimeError("shape mismatch")))

    def test_the_code_digest_covers_every_module(self) -> None:
        """Second review, finding 1: a hand-kept list left out modules the run imports."""
        files = s1.code_files()
        for name in ("learnlab/core.py", "learnlab/policy.py", "premonition/pointer.py", "memorylab/storage.py",
                     "learnlab/village/shards.py", "scripts/span_stage0.py", "scripts/span_stage1.py"):
            self.assertIn(name, files)


    def test_a_go_rung_larger_than_the_fit_is_refused_and_waited_on(self) -> None:
        """Third review, finding 4: a larger rung killed the box instead of being refused like any mismatch."""
        expected = {"N": 1}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "go.json"
            args = types.SimpleNamespace(go_file=str(path), go_url=None, go_poll_seconds=0.01, go_wait_hours=0.0002,
                                         seed=0)
            base = {"go": True, "seeds": [0], "N": 1}
            path.write_text(json.dumps({**base, "max_tokens": s1.LADDER[0][0], "max_visits": s1.LADDER[0][1]}))
            out = io.StringIO()
            with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as stop:
                s1.wait_for_go(args, expected, s1.LADDER[1])
            self.assertIn("deadline", str(stop.exception))
            self.assertIn('"rung"', out.getvalue())
            path.write_text(json.dumps({**base, "max_tokens": s1.LADDER[1][0], "max_visits": s1.LADDER[1][1]}))
            self.assertEqual(s1.wait_for_go(args, expected, s1.LADDER[1])["max_tokens"], s1.LADDER[1][0])

    def test_a_timed_out_child_with_bytes_output_is_a_clean_fault(self) -> None:
        """Third review, finding 1: TimeoutExpired carries bytes even with text=True; it crashed the box."""
        original = s1.subprocess.run

        def hang(*a, **k):
            raise s1.subprocess.TimeoutExpired("child", 1, output=b"stuck in economy", stderr=b"loading caches")
        s1.subprocess.run = hang
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as stop:
                s1.preflight(types.SimpleNamespace(seed=0, visits="tiny", size="tiny", workers=1))
            self.assertIn("other than memory", str(stop.exception))
            record = dict(s1.decode(out.getvalue().splitlines()))["preflight_error"]
            self.assertIn("loading caches", record["stderr"])                # the child's own tails are reported
            self.assertIn("stuck in economy", record["stderr"])
        finally:
            s1.subprocess.run = original



@unittest.skipUnless(os.environ.get("SPAN_STAGE1_SMOKE"), "set SPAN_STAGE1_SMOKE=1: builds tiny data (about 3 min)")
class SmokeTest(unittest.TestCase):
    def test_the_box_runs_end_to_end_on_tiny_data(self) -> None:
        """Fifth review, finding 10: the whole box flow (data, slices, pre-flight, go, parent, branch, arms, DEV bits
        aligned with the slice masks) on the tiny preset, in a subprocess, as a box runs it."""
        import subprocess
        import sys
        script = str(Path(s1.__file__).resolve())
        with tempfile.TemporaryDirectory() as tmp:
            common = ["--seed", "0", "--visits", "tiny", "--size", "tiny", "--workers", "2"]
            data = subprocess.run([sys.executable, script, "data", *common], capture_output=True, text=True,
                                  timeout=900)
            found = dict(s1.decode(data.stdout.splitlines()))
            self.assertIn("data", found, f"exit {data.returncode}: {data.stderr[-2000:]}")
            record = found["data"]
            go = {"go": True, "seeds": [0], "script_sha256": s1.script_sha256(), "code_sha256": s1.code_sha256(),
                  "size": "tiny",
                  "train_cache_sha256": record["train_cache"]["sha256"],
                  "validation_cache_sha256": record["validation_cache"]["sha256"], "N": record["N"],
                  "flop_budget": 3e12, "max_tokens": s1.LADDER[0][0], "max_visits": s1.LADDER[0][1]}
            path = Path(tmp) / "go.json"
            path.write_text(json.dumps(go))
            try:
                run = subprocess.run([sys.executable, script, "box", *common, "--flop-budget", "3e12", "--go-file",
                                      str(path), "--go-poll-seconds", "1", "--go-wait-hours", "0.02"],
                                     capture_output=True, text=True, timeout=1500)
            except subprocess.TimeoutExpired as expired:                   # keep the records for the cleanup
                run = types.SimpleNamespace(stdout=s1.as_text(expired.stdout), stderr=s1.as_text(expired.stderr))
            import shutil
            for kind, record in s1.decode(run.stdout.splitlines()):         # whatever the outcome, remove the
                if kind.endswith("_ckpt"):                                   # run's checkpoints
                    self.addCleanup(shutil.rmtree, Path(s1.ROOT) / Path(record["path"]).parents[1], True)
            self.assertIn("S1-DONE ok", run.stdout, run.stdout[-2000:] + run.stderr[-2000:])
            records = s1.decode(run.stdout.splitlines())
            kinds = [k for k, _ in records]
            for kind in ("slices", "preflight", "go", "parent", "branch", "arm_ckpt", "arm_dev", "arm_economy"):
                self.assertIn(kind, kinds)
            slices = dict(records)["slices"]
            far = s1.unbits(slices["masks"]["far"], slices["questions"])
            devs = [r["dev"] for k, r in records if k in ("parent_dev", "arm_dev")]
            self.assertEqual(len(devs), 3)                                 # P_s, LINE and SPAN
            for dev in devs:
                self.assertTrue(dev["aligned"])
                self.assertEqual(dev["questions"], slices["questions"])
                self.assertEqual(dev["ids_sha256"], slices["ids_sha256"])   # the bits use the masks' order
                correct = s1.unbits(dev["correct_bits"], dev["questions"])
                hits = sum(c for c, f in zip(correct, far) if f)
                self.assertAlmostEqual(dev["slices"]["far"]["accuracy"] or 0.0, hits / max(sum(far), 1), places=9)



class ExactNTest(unittest.TestCase):
    def test_n_is_exact_and_matches_the_sealed_definition(self) -> None:
        """Eighth review, finding 1: a float32 mean can differ in the last bit between boxes; N is exact instead."""
        offsets = torch.tensor([0, 10, 21, 30, 41, 55], dtype=torch.int32)
        cache = types.SimpleNamespace(line_offsets=offsets, line_is_question=torch.tensor([False, False, True,
                                                                                           False, False]))
        self.assertEqual(s1.exact_n(cache), round((10 + 11 + 11 + 14) / 4, 6))
        self.assertAlmostEqual(s1.exact_n(cache), span_cards.tokens_per_line(cache), places=5)


if __name__ == "__main__":
    unittest.main()
