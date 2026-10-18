"""The Stage 1 run script (scripts/span_stage1.py): the log protocol, the branch from P_s (both arms restore the
parent exactly; SPAN's optimizer state is matched by name), the parent's stop at the end of the gold phase and the
arms' stream position, the heavy-batch selection of the memory pre-flight, and the go-file gate. CPU, tiny."""
from __future__ import annotations

import io
import contextlib
import copy
import itertools
import json
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
              "names": s1.optimizer_names(model), "consumed": steps}
    return trainer, parent, batches


def arm(parent: dict, kind: str, budget: float):
    torch.manual_seed(5)                                   # a different global seed: restore must override it
    if kind == "LINE":
        model = PremonitionMini(tiny_config())
        model.load_state_dict(parent["model"])
        trainer = MiniTrainer(model, s1.train_config(), "cpu", flop_budget=budget, seed=0)
    else:
        model = span_cards.build_model(tiny_config(), span_config())
        model.load_state_dict(parent["model"], strict=False)
        model.writer.init_gate()
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
            a = trainer._train_step(batch, teacher, loops, False)
            ckpt.set_rng_state(ckpt.rng_state())
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
        names = s1.optimizer_names(span.model)
        gate = {"writer.gate.weight", "writer.gate.bias", "writer.newline_weight"}
        self.assertEqual(set(names) - set(s1.optimizer_names(line.model)), gate)
        self.assertTrue(all(i not in span.optimizer.state_dict()["state"] for i, n in enumerate(names) if n in gate))
        batch = batches[2]
        loops = planned_loops(batch, "gold", line.model.config)
        line._train_step(batch, GOLD, loops, False)
        span._train_step(batch, GOLD, loops, False)
        shared = dict(line.model.named_parameters())
        moved = 0
        for name, p in span.model.named_parameters():
            if name in gate:
                continue
            torch.testing.assert_close(p, shared[name], rtol=0, atol=1e-6, msg=name)
            moved += int(not torch.equal(p, dict((n, q) for n, q in arm(parent, "LINE", 1.0).model.named_parameters())
                                         [name]))
        self.assertGreater(moved, 10)                                      # the step really updated weights

    @staticmethod
    def moments_by_name(trainer) -> dict:
        state = trainer.optimizer.state_dict()["state"]
        return {name: state[i] for i, name in enumerate(s1.optimizer_names(trainer.model)) if i in state}

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
    def test_the_parent_stops_at_the_branch_and_the_arms_take_the_next_batch(self) -> None:
        trainer, _, _ = parent_of(0)
        stream = iter([synthetic_batch(seed=s) for s in range(30)])
        counter = [0]

        def plan() -> Plan:
            return Plan("gold", "gold", 0.0) if counter[0] < 7 else Plan("teacher", "teacher", 0.0)
        trainer.plan = plan
        taken = list(s1.gold_only(trainer, stream, counter))
        self.assertEqual(counter[0], 7)
        self.assertEqual(len(taken), 7)

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
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "go.json"
            path.write_text(json.dumps({"go": True, "seeds": [1], **expected, "max_tokens": 55000}))
            self.assertEqual(s1.wait_for_go(self.args(path), expected)["max_tokens"], 55000)
            for wrong in ({"N": 11.2}, {"seeds": [0]}, {"go": None}):
                path.write_text(json.dumps({"go": True, "seeds": [1], **expected, **wrong}))
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                    s1.wait_for_go(self.args(path), expected)
            path.write_text(json.dumps({"go": False}))
            with self.assertRaises(SystemExit) as stop:
                s1.wait_for_go(self.args(path), expected)
            self.assertIn("stop", str(stop.exception))


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


if __name__ == "__main__":
    unittest.main()
